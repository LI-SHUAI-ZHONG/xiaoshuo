"""Only actually adopted upstream methods can schedule their later references."""
import pytest

from nw.materials.phase_dependencies import deferred_source_ids


class MetadataOnlyDesk:
    def __init__(self, rows: list[dict]) -> None:
        self.by_id = {row['id']: row for row in rows}

    @property
    def rows(self) -> list[dict]:
        raise AssertionError('dependency discovery must not scan the source library')

    def read(self, ident: str) -> dict:
        raise AssertionError('dependency discovery must not read source originals')

    def search(self, query: str, **kwargs) -> dict:
        raise AssertionError('dependency discovery must follow known IDs only')


def metadata(ident: str, key: str, profile: str = 'type_transition') -> dict:
    return {'id': ident, 'key': key, 'profile': profile, 'state': 'reference'}


def studied(ident: str, related: list[str]) -> dict:
    return {'source': {'id': ident, 'key': ident, 'profile': 'type_combination', 'path': 'fake.txt',
                       'file_sha256': 'a' * 64, 'sha256': 'b' * 64},
            'source_state': 'blocked', 'original_text': '[FAKE] 已研读的组合原文与确切引用。',
            'original_text_sha256': 'c' * 64, 'application_layers': [],
            'source_issues': {'missing': [], 'conflicts': []}, 'related_sources': related,
            'use_mode': 'project_method', 'authority': 'project_candidate_only', 'boundary': '[FAKE] 项目方法'}


def product(stage: str, used: list[str], excluded: list[str] = ()) -> dict:
    return {'stage': stage, 'task_id': '[FAKE] ' + stage, 'sha256': 'd' * 64, 'inputs': [],
            'source_ids': [*used, *excluded],
            'products': {'_uses': [{'source_id': ident, 'operation': '[FAKE] 按原文构造当前项目实际产物',
                                    'output_refs': ['adaptations']} for ident in used],
                         '_excluded': [{'source_id': ident, 'reason': '[FAKE] 本次不适用'} for ident in excluded]}}


@pytest.mark.parametrize(('stage', 'expected'), [
    ('state_propagation', ['tdr-001']),
    ('state_transition', ['tdr-003']),
    ('event_design', ['tdr-004']),
    ('action_design', ['tdr-005']),
    ('type_adaptation', []),
    ('world_design', []),
])
def test_adopted_combination_defers_each_template_to_its_own_later_step(stage: str, expected: list[str]) -> None:
    desk = MetadataOnlyDesk([metadata(f'tdr-{number:03}', f'TDR_TEMPLATE_{number:03}') for number in range(1, 6)])
    sources = [studied('combination', ['tdr-001', 'tdr-002', 'tdr-003', 'tdr-004', 'tdr-005'])]
    products = {'type_adaptation': product('type_adaptation', ['combination'])}
    assert deferred_source_ids(desk, stage, products, sources) == expected


def test_excluded_or_delivered_but_unused_sources_do_not_expand_references() -> None:
    desk = MetadataOnlyDesk([metadata(ident, 'TDR_TEMPLATE_004') for ident in ('used-ref', 'excluded-ref', 'unused-ref')])
    sources = [studied('used', ['used-ref']), studied('excluded', ['excluded-ref']), studied('unused', ['unused-ref'])]
    record = product('type_adaptation', ['used'], ['excluded'])
    record['source_ids'].append('unused')
    assert deferred_source_ids(desk, 'event_design', {'type_adaptation': record}, sources) == ['used-ref']


def test_same_step_and_future_products_cannot_schedule_a_reference_backwards() -> None:
    desk = MetadataOnlyDesk([metadata(ident, 'TDR_TEMPLATE_004') for ident in ('prior-ref', 'same-ref', 'future-ref')])
    sources = [studied('prior', ['prior-ref']), studied('same', ['same-ref']), studied('future', ['future-ref'])]
    products = {stage: product(stage, [ident]) for stage, ident in (
        ('type_adaptation', 'prior'), ('event_design', 'same'), ('scene_design', 'future'))}
    assert deferred_source_ids(desk, 'event_design', products, sources) == ['prior-ref']


def test_references_are_deduplicated_in_use_order_without_recursive_expansion() -> None:
    rows = [metadata(ident, 'TDR_TEMPLATE_004') for ident in ('event-a', 'event-b', 'event-c', 'recursive-ref')]
    rows[1]['related_sources'] = ['recursive-ref']
    desk = MetadataOnlyDesk(rows)
    sources = [studied('first', ['event-a', 'event-c']),
               studied('second', ['event-b', 'event-a', 'event-b']), studied('event-b', ['recursive-ref'])]
    products = {'type_adaptation': product('type_adaptation', ['second', 'first'])}
    assert deferred_source_ids(desk, 'event_design', products, sources) == ['event-b', 'event-a', 'event-c']


def test_missing_studied_originals_or_metadata_ids_are_not_invented() -> None:
    desk = MetadataOnlyDesk([metadata('real-event-id', 'TDR_TEMPLATE_004')])
    desk.by_id['not-studied'] = {**metadata('not-studied', 'STATIC_COMBO'), 'related_sources': ['real-event-id']}
    no_id = studied('removed-id', ['real-event-id'])
    no_id['source'].pop('id')
    no_related = studied('no-related', [])
    no_related.pop('related_sources')
    sources = [studied('known', ['missing-id', 'TDR_TEMPLATE_004']), no_id, no_related]
    products = {'type_adaptation': product('type_adaptation', ['known', 'not-studied', 'removed-id', 'no-related'])}
    assert deferred_source_ids(desk, 'event_design', products, sources) == []
def test_sources_reader_actually_delivers_the_deferred_method_without_a_search_hit():
    from types import SimpleNamespace
    from nw.materials.phase_flow import _sources
    meta={'id':'t1','key':'TDR_TEMPLATE_001','profile':'type_transition'}
    reads=[]
    def read(ident):
        reads.append(ident)
        return {'source':meta,'use_mode':'project_method'}
    desk=SimpleNamespace(by_id={'t1':meta},rows=[meta],read=read,
        search=lambda *args,**kwargs:{'items':[],'next_cursor':None})
    products={'type_adaptation':{'products':{'_uses':[{'source_id':'combo'}]}}}
    originals=[{'source':{'id':'combo'},'related_sources':['t1']}]
    package={'brief':{'text':'本场调查','constraints':''}}
    result=_sources(desk,'state_propagation',package,products,originals)
    assert [s['source']['id'] for s in result]==['t1']
    assert reads==['t1']
