"""Deterministic periodic metrics and feedback from actually accepted drafts."""
from collections import Counter
import json

from nw.cards import read_card
from nw.story_models import CardRef
from nw.story_state import baseline_for, replay, revision_state, selected_operations
from nw.tasks import read_input_manifest


def stage_metrics(check: dict, drafts: list[dict], promise_states: dict) -> dict:
    profile, artifact = check['profile'], check.get('process_artifact', {})
    scope = check.get('source_contract', {}).get('evidence_scope', {})
    if scope.get('metric') == 'third_scene_length':
        chapters = check['binding']['review_scope']['chapters']
        counts = {row['scene_index']: len(''.join(row['text'].split())) for row in drafts
                  if row['chapter_index'] in chapters and row['scene_index'] in scope['scene_indices']}
        return {'scene_character_counts': [counts[index] for index in scope['scene_indices']]}
    if profile == 'pov_process':
        chapters = check['binding']['review_scope']['chapters']
        counts = Counter()
        for row in drafts:
            if row['chapter_index'] in chapters:
                counts[row.get('pov')] += len(''.join(row['text'].split()))
        protagonist = check.get('process_ids', {}).get(artifact['protagonist'], artifact['protagonist'])
        total = sum(counts.values())
        return {'due': max(chapters) % artifact['review_interval'] == 0,
                'total_chars': total, 'protagonist_chars': counts[protagonist],
                'unknown_pov_chars': counts[None],
                'protagonist_share': counts[protagonist]/total if total else None}
    if profile == 'promise_process':
        counts = Counter(promise_states.values())
        total = sum(counts[v] for v in ('planted','sleeping','awake','paid_off'))
        return {'closing': artifact['closing'], 'registered': total, 'paid_off': counts['paid_off'],
                'payoff_ratio': counts['paid_off']/total if total else None}
    return {}


def metric_failure(check: dict, metrics: dict) -> str | None:
    scope = check.get('source_contract', {}).get('evidence_scope', {})
    if scope.get('metric') == 'third_scene_length':
        first, second, third = metrics['scene_character_counts']
        if 5 * third <= 6 * max(first, second):
            return f'前三场非空白字符分别为 {first}、{second}、{third}，第三场须分别严格大于前两场的 1.2 倍'
    if check['profile'] == 'pov_process' and check.get('actual_switch_mismatches'):
        return '前视角声明与冻结的实际前场不符，须重新规划切换并核对读者重置'
    if check['profile'] == 'pov_process' and metrics.get('due'):
        if metrics['unknown_pov_chars'] or metrics['protagonist_share'] is None:
            return '周期视角比例缺少完整的实际正文或视角依据'
        if metrics['protagonist_share'] < check['process_artifact']['min_share']:
            return f"实际主角视角占比 {metrics['protagonist_share']:.1%}，未达到采用的原文下限"
    if check['profile'] == 'promise_process' and metrics.get('closing'):
        if metrics['payoff_ratio'] is None or metrics['payoff_ratio'] < check['process_artifact']['payoff_min']:
            return '全量已埋设伏笔状态的回收率未达到采用的原文下限'
    return None


def viewpoint_mismatches(check: dict, drafts: list[dict]) -> list[dict]:
    ids = check.get('process_ids', {})
    switches = {ids.get(r['scene'],r['scene']):r for r in check['process_artifact']['switches']}
    ordered = sorted(drafts,key=lambda r:(r['chapter_index'],r['scene_index']))
    mismatches = []
    for index,row in enumerate(ordered):
        if row['chapter_index'] not in check['binding']['review_scope']['chapters']:
            continue
        switch = switches.get(row['scene_card_id'])
        if switch is None:
            continue
        actual = ordered[index-1]['pov'] if index else None
        declared = ids.get(switch['from_pov'],switch['from_pov'])
        if declared != actual:
            mismatches.append({'scene_id':row['scene_id'],'declared':declared,'actual':actual})
    return mismatches


def enrich_scope(store, checks: list[dict], drafts: list[dict], head, deltas: list) -> None:
    if not any(r['profile'] in {'pov_process','promise_process'} for r in checks):
        for check in checks:
            if metrics := stage_metrics(check, drafts, {}):
                check['stage_metrics'] = metrics
        return
    for row in drafts:
        scene = store.get('scene', row['scene_id'])
        reference = json.loads(scene.card_json).get('story', {}).get('scene_ref')
        row['pov'] = read_card(store, CardRef(**reference))['body'].get('pov') if reference else None
    facts = replay(baseline_for(store, head.branch_id), selected_operations(store, revision_state(store, head)))
    states = {f.entity_id:f.value for f in facts if f.predicate == 'promise_stage' and f.holder == 'WORLD' and f.claim == 'fact'}
    operations = sorted((op for delta in deltas for op in delta.operations),
                        key=lambda op: (op['story_order'], op['disclosure_order']))
    for op in operations:
        if op['predicate'] == 'promise_stage' and op['holder'] == 'WORLD' and op['claim'] == 'fact':
            states[op['entity_id']] = op['new_value']
    for check in checks:
        if check['profile'] == 'pov_process':
            check['actual_switch_mismatches'] = viewpoint_mismatches(check, drafts)
        metrics = stage_metrics(check, drafts, states)
        if metrics:
            check['stage_metrics'] = metrics


def accepted_feedback(store, head, limit: int = 20) -> list[dict]:
    result = []
    for scene, slot in list(revision_state(store, head)['slots'].items())[-limit:]:
        if not slot.get('delta_id'):
            continue
        from nw.story_delta import read_delta
        delta = read_delta(store, slot['delta_id'])
        _, package = read_input_manifest(store, delta.manifest_id)
        run_id = package.get('material_review_run')
        if not run_id:
            continue
        review = store.get('run', run_id)
        output = json.loads(review.output_text)
        for check in output.get('material_checks', []):
            result.append({'source_id': check['id'], 'scene_id': scene, 'draft_id': slot['draft_id'],
                           'status': check['status'], 'reason': check['reason'], 'evidence': check['evidence'],
                           'authority': 'accepted_draft_review_feedback_not_a_new_story_fact'})
    return result[-limit:]
