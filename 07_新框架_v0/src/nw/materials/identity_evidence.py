"""Recover accepted identity and chapter progress checks from the frozen draft review."""
from dataclasses import asdict
import json
import re

from nw.materials.action_review import review_result
from nw.models import Draft
from nw.store import Store
from nw.story_delta import draft_ref, paragraph_evidence
from nw.story_models import StateDelta
from nw.tasks import read_input_manifest

_IDENTITY_KEY = re.compile(r'ID[1-3]\.(?:[1-9]|1[0-9]|20)')


def _identity_sources(rule: dict) -> list[dict]:
    if rule.get('source_applicability', 'applies') != 'applies':
        return []
    if rule['profile'] == 'anchor':
        key = rule.get('source_contract', {}).get('key')
        return [{**ref, 'key': key} for ref in rule.get('source_refs', [])
                if ref['id'] == rule['id'] and _IDENTITY_KEY.fullmatch(key or '')]
    return [ref for item in rule.get('method_sources', [])
            if (ref := item['source']).get('profile') == 'anchor'
            and _IDENTITY_KEY.fullmatch(ref.get('key', ''))]


def _paragraphs(draft: Draft, spans: list[dict]) -> list[dict]:
    return paragraph_evidence(draft, [{'draft_id': span['id'], 'text_sha256': span['sha256'],
                                       'start': span['start'], 'end': span['end']}
                                      for span in spans])


def _source_proof(draft: Draft, rule: dict, review: dict, source: dict) -> dict | None:
    direct = rule['profile'] == 'anchor'
    obligations = {item['id']: item for item in rule['source_contract'].get('obligations', [])
                   if direct or item.get('source_id') == source['id']}
    clauses = []
    for check in review.get('source_checks', []):
        if check['id'] not in obligations or check['status'] != 'pass':
            continue
        spans = [span for span in check['evidence'] if span['id'] == draft.id]
        clauses.append({'obligation': obligations[check['id']], 'reason': check['reason'],
                        'evidence': spans, 'paragraph_evidence': _paragraphs(draft, spans)})
    if not direct and not clauses:
        return None
    spans = ([span for span in review['evidence'] if span['id'] == draft.id] if direct else
             [span for clause in clauses for span in clause['evidence']])
    return {'source': source, 'check_id': rule['id'], 'reason': review['reason'],
            'source_checks': clauses, 'evidence': spans, 'paragraph_evidence': _paragraphs(draft, spans)}


def accepted_scene_checks(store: Store, draft: Draft, delta: StateDelta, *, identity: bool,
                          cast_work: list[dict] | None = None) -> tuple[list[dict], list[dict]]:
    """Read proof from the accepted delta without consulting today's design or catalog."""
    manifest, package = read_input_manifest(store, delta.manifest_id)
    run_id = package.get('material_review_run')
    if not run_id:
        return [], []
    run = store.get('run', run_id)
    snapshot = json.loads(run.input_snapshot_json)
    payload = json.loads(snapshot['messages'][-1]['content'])
    contract = payload.get('material_review')
    if not contract:
        return [], []
    sources = {rule['id']: (rule, refs) for rule in contract['checks'] if identity and (refs := _identity_sources(rule))}
    progress = {rule['id']: rule for rule in contract['checks'] if rule['id'].startswith('work:progress:')}
    from nw.materials.cast_fulfillment import PREFIX
    roles = {rule['id']: rule for rule in contract['checks'] if cast_work is not None and rule['id'].startswith(PREFIX)}
    if not sources and not progress and not roles:
        return [], []
    reviewed, context = read_input_manifest(store, snapshot['manifest_id'])
    ref = asdict(draft_ref(draft))
    scope = ('branch_id', 'state_revision', 'story_order', 'disclosure_order', 'candidate_delta_refs', 'novel_job_id')
    if (run.kind != 'review' or run.scene_id != draft.scene_id or run.id == draft.run_id
            or run.finish_reason != 'complete' or not run.ended_at or reviewed['purpose'] != 'review'
            or contract['draft'] != ref or ref not in reviewed['dependency_refs']
            or any(reviewed[key] != manifest[key] for key in scope)
            or payload['draft'] != asdict(draft) or payload['context'] != context):
        raise ValueError('MATERIAL_EVIDENCE: scene check does not match the accepted draft and frozen review input')
    comparison = None
    if prior := contract.get('comparison'):
        comparison = store.get('draft', prior['ref']['id'])
        if prior['ref'] != asdict(draft_ref(comparison)):
            raise ValueError('MATERIAL_EVIDENCE: identity review comparison draft has changed')
    result = review_result(run, contract, draft, comparison)
    if result['recommendation'] != 'pass':
        raise ValueError('MATERIAL_EVIDENCE: scene check does not come from a passing review')
    proofs = []
    advances = []
    for check in result['material_checks']:
        if check['id'] in roles:
            from nw.materials.cast_fulfillment import performance
            design = performance(roles[check['id']], contract['checks'])
            cast_work.append({'scene_id': draft.scene_id, 'draft_ref': ref, 'delta_id': delta.id,
                'review_run_id': run.id, 'disclosure_order': manifest['disclosure_order'],
                'actor': design['actor'], 'demand': design['demand'], 'event': design['event'],
                'action_ref': design['action_ref'], 'step_index': design['step_index'],
                'designed_action': design['action'], 'designed_result': design['candidate_result'],
                'review_reason': check['reason'], 'evidence': [s for s in check['evidence'] if s['id'] == draft.id]})
        if check['id'] in progress:
            design = progress[check['id']]['method_artifact']
            advances.append({'scene_id': draft.scene_id, 'draft_ref': ref, 'delta_id': delta.id, 'review_run_id': run.id,
                'disclosure_order': manifest['disclosure_order'],
                'change': design['change'], 'review_reason': check['reason'],
                'evidence': [span for span in check['evidence'] if span['id'] == draft.id],
                'possible_next_pressure': design['next_pressure']})
        if check['id'] in sources:
            rule, refs = sources[check['id']]
            for source in refs:
                if proof := _source_proof(draft, rule, check, source):
                    proofs.append({'scene_id': draft.scene_id, 'draft_ref': ref, 'review_run_id': run.id, **proof})
    return proofs, advances


def accepted_identity_checks(store: Store, draft: Draft, delta: StateDelta) -> list[dict]:
    return accepted_scene_checks(store, draft, delta, identity=True)[0]
