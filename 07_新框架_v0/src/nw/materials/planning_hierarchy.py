"""Scope responsibilities and the durable handoff from chapter outline to scenes."""
from copy import deepcopy
import json
from typing import Callable

from nw.materials.phase_routes import product_ref
from nw.store import Store
from nw.story_state import approved_scene_positions


INSTRUCTIONS = {
    'book': '全书确定主线、主角走向、关键转折、读者承诺与结局兑现。较早的伏笔保留预计回收方向。分卷走向可以用文字提出，卷、章和场景的独立卡片由后续环节建立。',
    'volume': '卷纲承接已批准书纲。卷卡的 goal 是本卷目标，turn 是改变局面的转折，ending_direction 写卷末状态和交给下卷的具体任务。每部书可以只设一卷。',
    'chapter': '章纲承接已批准卷纲。章卡的 goal 和 consequence 分别写本章承接的问题和章末的实际变化，事件节点写出由目标和障碍引发的行动条件。章纲批准后再将这些条件落实为场景。',
    'scene': '场景用具体视角、目标、阻碍、选择和代价落实已批准章纲的一段推进。结果要能引发下一步事件。',
}
INHERITED_TYPE_FIELDS = {
    'type_selection': ('selection', 'concepts', 'boundaries'),
    'type_adaptation': ('adaptations', 'focuses', 'boundaries'),
}
OUT_OF_SCOPE_ARTIFACTS = {
    'book': {'volume', 'chapter', 'scene'},
    'volume': {'chapter', 'scene'},
    'chapter': {'volume'},
}


def volume_outline(scope: str, enabled: bool) -> bool:
    return enabled and scope == 'volume'


def inherited_types(plan: dict) -> dict:
    if not plan.get('planning_hierarchy') or plan.get('scope') == 'book':
        return {}
    result = {}
    for record in (plan.get('parent_material_work') or {}).get('stages', []):
        if fields := INHERITED_TYPE_FIELDS.get(record['stage']):
            result[record['stage']] = {key: record['products'][key] for key in fields}
    return result


def validate_types(stage: str, value: dict, context: dict) -> None:
    if expected := context.get('hierarchy_inherited_types', {}).get(stage):
        if any(value.get(key) != content for key, content in expected.items()):
            raise ValueError('分级制作须沿用已批准类型和适配结果，变动须先返回上级重做')


def incompatible_method(body: dict, stage: str, context: dict) -> bool:
    excluded = OUT_OF_SCOPE_ARTIFACTS.get(context.get('scope'), ()) if context.get('planning_hierarchy') else ()
    return any(out['stage'] == stage and out.get('artifact_kind') in excluded for out in body['outputs'])


def validate_plot(value: dict, scope: str) -> None:
    if scope == 'book' and any(row['kind'] in ('volume', 'chapter', 'scene') for row in value['members']):
        raise ValueError('全书方案确定总路线，卷、章与场景的卡片须在相应步骤产生')
    if scope == 'volume':
        cards = [row for row in value['members'] if row['kind'] == 'volume']
        if len(cards) != 1 or any(row['kind'] in ('chapter', 'scene') for row in value['members']):
            raise ValueError('卷纲须交付一张卷卡，章和场景由后续步骤安排')
        if not (isinstance(ending := cards[0]['body'].get('ending_direction'), str) and ending.strip()):
            raise ValueError('卷纲须给出卷末结果及交给下一级或下一卷的具体任务')
    if scope == 'chapter':
        cards = [row for row in value['members'] if row['kind'] == 'chapter']
        if len(cards) != 1 or any(row['kind'] == 'volume' for row in value['members']):
            raise ValueError('本次推进须交付一张章卡，沿用上游已批准卷纲')
        if not value.get('event_nodes'):
            raise ValueError('章纲须用实际事件节点说明本章如何推进')


def next_chapter_index(store: Store, snapshot: dict) -> int:
    positions = approved_scene_positions(store, snapshot)
    if positions.keys() - snapshot['slots'].keys():
        raise ValueError('CHAPTER_CONTINUATION_REQUIRED: 已批准章节尚有未接受场景，请完成前章后再续章')
    return max((chapter for chapter, _ in positions.values()), default=0) + 1


def chapter_target(record: dict, lineage: list[dict], chapter_index: int | None = None) -> dict:
    value = record['products']
    validate_plot(value, 'chapter')
    if len(value['directions']) != 1:
        raise ValueError('章纲只确认一份剧情推进设计')
    return deepcopy({'kind': 'chapter_outline_approval',
                     'chapter': next(row for row in value['members'] if row['kind'] == 'chapter'),
                     'plot_ref': product_ref(record), 'direction': value['directions'][0],
                     'event_nodes': value['event_nodes'], 'outline_lineage': lineage,
                     **({'chapter_index': chapter_index} if chapter_index is not None else {})})


def validate_scene_handoff(value: dict, context: dict) -> None:
    if context.get('planning_hierarchy') and context.get('scope') == 'chapter':
        approved = context.get('approved_chapter')
        chapter = approved['target']['chapter'] if approved else None
        if not chapter or len(value['chapters']) != 1 or value['chapters'][0]['card'] != chapter['key']:
            raise ValueError('场景须落到本轮已批准章纲对应的同一章卡')
        index = context.get('chapter_target_index')
        if index is not None and value['chapters'][0]['index'] != index:
            raise ValueError(f'场景须使用已批准的第 {index} 章编号')


def _verify_decision(store: Store, approved: dict) -> None:
    row = store.connection.execute(
        'SELECT action,targets_json FROM story_decisions WHERE id=?', (approved['decision_id'],)).fetchone()
    payload = json.loads(row['targets_json']) if row else {}
    if (row is None or row['action'] != 'novel_confirm'
            or payload.get('choice') != approved['choice'] or payload.get('target') != approved['target']
            or payload.get('choice', {}).get('action') != 'approve'):
        raise ValueError('STALE_CHAPTER_OUTLINE: 已批准章纲与作者决定记录不同')


def approve_chapter(store: Store, record: dict, context: dict, decide: Callable | None) -> dict:
    if decide is None:
        raise ValueError('CHAPTER_OUTLINE_APPROVAL_REQUIRED: 请在制作台先确认章纲')
    target = chapter_target(record, context['outline_lineage'], context.get('chapter_target_index'))
    decision = decide(target)
    approval = {'target': target, 'decision_id': decision['decision_id'], 'choice': decision['choice']}
    _verify_decision(store, approval)
    return approval


def verify_chapter(session: dict, store: Store | None = None) -> None:
    context = session['context']
    if not (context.get('planning_hierarchy') and session['scope'] == 'chapter'):
        return
    approved = context.get('approved_chapter')
    plot = next(row for row in session['stages'] if row['stage'] == 'plot_design')
    if not approved or approved['target'] != chapter_target(
            plot, context['outline_lineage'], context.get('chapter_target_index')):
        raise ValueError('STALE_CHAPTER_OUTLINE: 场景采用的章纲与批准的剧情步骤产物不同')
    if store is not None:
        from nw.tasks import read_input_manifest

        _verify_decision(store, approved)
        for stage in session['stages'][session['stages'].index(plot) + 1:]:
            receipt = stage.get('approved_chapter_receipt')
            if (not receipt or receipt not in session['calls'] or receipt['task_id'] != stage['task_id']):
                raise ValueError('STALE_CHAPTER_OUTLINE: 场景步骤缺少实际章纲交接记录')
            _, manifest = read_input_manifest(store, receipt['manifest_id'])
            packet = manifest.get('study_input', {})
            if (packet.get('approved_chapter') != approved or packet.get('scope') != 'chapter'
                    or packet.get('outline_lineage') != context['outline_lineage']
                    or packet.get('stage') != stage['stage']):
                raise ValueError('STALE_CHAPTER_OUTLINE: 下游实际调用使用了不同版本的章纲')
