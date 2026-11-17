"""Isolated source-contract checks; no model, project or production catalog writes."""
from hashlib import sha256
import json
from pathlib import Path
import sqlite3

import pytest

from nw.materials.catalog import build_catalog
from nw.materials.route_catalog import _UNITS
from nw.materials.type_adjudication import TypeAdjudicator
from nw.materials.type_hierarchy import TYPE_TABLE, type_children
from nw.materials.unit_catalog import index_units


def catalog(tmp_path: Path, blocks: dict) -> tuple:
    data = '\n'.join('SOURCE: '+key+'\n=====\n'+json.dumps(value, ensure_ascii=False)
                     for key, value in blocks.items()).encode('utf-8')
    (tmp_path/'types.txt').write_bytes(data)
    manifest = tmp_path/'manifest.json'
    manifest.write_text(json.dumps(dict(schema_version=1, catalog_inputs=[dict(path='types.txt',
        family='types', layer='baseline', sha256=sha256(data).hexdigest(), bytes=len(data))])), encoding='utf-8')
    workspace = tmp_path/'workspace'
    build_catalog(workspace, tmp_path, manifest)
    index_units(workspace, None)
    connection = sqlite3.connect(workspace/'materials'/'catalog.db')
    connection.row_factory = sqlite3.Row
    rows = [dict(x) for x in connection.execute(_UNITS)]
    return connection, rows, TypeAdjudicator(connection)


def genre(**extra: object) -> dict:
    return dict(type_id='GENRE_ONE', canonical_name='类型一', type_kind='GENRE', parent_id=None,
                definition='围绕明确的世界规则与人物选择展开的类型定义', status='active',
                confidence=.8, not_guaranteed=['不保证人物必然成功'], **extra)


def root(rows: list, block: str) -> dict:
    return next(r for r in rows if r['fragment_key'] == block and r['kind'] == 'record')


def test_original_root_child_and_upgrade_boundaries(tmp_path: Path) -> None:
    value = genre(运行层升级={'definition': 'UPGRADE_MUST_NOT_LEAK', 'model_input_eligible': True})
    connection, rows, adjudicator = catalog(tmp_path, {'主类型.json': value})
    try:
        record = root(rows, '主类型.json')
        result = adjudicator.review(record)
        assert result['state'] == 'design_ready'
        assert 'UPGRADE_MUST_NOT_LEAK' not in json.dumps(result)
        child = next(r for r in rows if r['kind'] == 'definition')
        assert adjudicator.review(child)['owner_id'] == record['id']
        assert adjudicator.review(child)['state'] == 'context'
        upgrade = next(r for r in rows if r['origin'] == 'upgrade')
        assert not adjudicator.review(upgrade)['can_offer_for_design']
    finally:
        connection.close()


def test_reverse_hierarchy_keeps_exact_source_scope_and_flags_conflicts(tmp_path: Path) -> None:
    main = genre(level=1, ancestor_ids=[], child_ids=[])
    valid = {**genre(), 'type_id': 'SUB_ONE', 'type_kind': 'SUBGENRE', 'parent_id': 'GENRE_ONE',
             'ancestor_ids': ['GENRE_ONE'], 'level': 2}
    invalid = {**valid, 'type_id': 'SUB_CONFLICT', 'ancestor_ids': ['OTHER_PARENT']}
    other_table = {**valid, 'type_id': 'SUB_OTHER_TABLE'}
    connection, _, _ = catalog(tmp_path, {TYPE_TABLE: [main, valid, invalid],
                                          '子类型.json': [other_table]})
    connection.close()

    result = type_children(tmp_path / 'workspace', 'GENRE_ONE')
    assert result['declared_child_ids'] == []
    subtype, = result['subtypes']
    assert subtype['type_id'] == 'SUB_ONE'
    assert subtype['parent_id'] == result['type_id']
    assert subtype['ancestor_ids'] == ['GENRE_ONE']
    assert subtype['source_ref']['fragment_key'] == TYPE_TABLE
    proof = subtype['source_ref']
    assert sha256((tmp_path / 'types.txt').read_bytes()[proof['byte_start']:proof['byte_end']]).hexdigest() == proof['sha256']
    assert [row['type_id'] for row in result['issues']] == ['SUB_CONFLICT']
    with pytest.raises(ValueError, match='missing or ambiguous'):
        type_children(tmp_path / 'workspace', 'SUB_OTHER_TABLE')


def test_pending_identity_and_invalid_confidence_cannot_be_ready(tmp_path: Path) -> None:
    value = genre()
    value.update(status='pending', confidence=999)
    connection, rows, adjudicator = catalog(tmp_path, {'主类型.json': [value]})
    try:
        result = adjudicator.review(root(rows, '主类型.json'))
        assert result['state'] == 'blocked'
        assert not result['can_offer_for_design']
        assert any('999' in issue for issue in result['conflicts'])
        assert any('pending' in issue for issue in result['missing'])
    finally:
        connection.close()


def test_conflicting_same_scoped_id_blocks_both_records(tmp_path: Path) -> None:
    left, right = genre(), genre()
    right['definition'] = '同一ID在同一来源表中却有另一个定义'
    connection, rows, adjudicator = catalog(tmp_path, {'主类型.json': [left, right]})
    try:
        results = [adjudicator.review(r) for r in rows if r['kind'] == 'record']
        assert all(x['state'] == 'blocked' for x in results)
        assert all(any('2 个不同原始定义' in p for p in x['conflicts']) for x in results)
    finally:
        connection.close()


def test_one_genre_plus_mechanism_is_multi_dimension_combination(tmp_path: Path) -> None:
    mechanism = dict(mechanism_id='MECH_ONE', canonical_name='机制一', definition='积累证据后才能解锁选择的机制', status='active')
    combo = dict(combination_id='COMBO_ONE', primary_type_id='GENRE_ONE', type_ids=['GENRE_ONE'],
                 mechanism_ids=['MECH_ONE'], description='类型一与机制一的组合用途', status='active')
    connection, rows, adjudicator = catalog(tmp_path, {'主类型.json': [genre()], '爽文机制.json': [mechanism],
                                                     '类型组合总表.json': [combo]})
    try:
        result = adjudicator.review(root(rows, '类型组合总表.json'))
        assert result['profile'] == 'type_combination'
        assert result['state'] == 'design_ready'
        assert len(result['related']) == 2
        assert result['contract']['project_completion_required']
    finally:
        connection.close()


def test_orphan_constituent_names_exact_missing_id(tmp_path: Path) -> None:
    combo = dict(combination_id='COMBO_ONE', primary_type_id='GENRE_ONE', type_ids=['GENRE_ONE'],
                 dynamic_rule_ids=['TDR_ORPHAN'], status='active', description='需验证规则引用的组合')
    connection, rows, adjudicator = catalog(tmp_path, {'主类型.json': [genre()], '类型组合总表.json': [combo]})
    try:
        result = adjudicator.review(root(rows, '类型组合总表.json'))
        assert result['state'] == 'blocked'
        assert any('TDR_ORPHAN' in p for p in result['missing'])
        ref = next(r for r in result['contract']['constituents'] if r['original_id'] == 'TDR_ORPHAN')
        assert ref['root_ids'] == []
    finally:
        connection.close()


def test_changed_catalog_payload_is_rejected(tmp_path: Path) -> None:
    connection, rows, _ = catalog(tmp_path, {'主类型.json': [genre()]})
    try:
        connection.execute("update fragments set payload=?", (b'changed',))
        with pytest.raises(ValueError, match='hash mismatch'):
            TypeAdjudicator(connection).review(root(rows, '主类型.json'))
    finally:
        connection.close()


def test_resolved_effect_id_still_requires_its_owner_rule(tmp_path: Path) -> None:
    combo = dict(combination_id='COMBO_ONE', primary_type_id='GENRE_ONE', type_ids=['GENRE_ONE'],
                 dynamic_rule_ids=['RULE_ONE'], candidate_effect_ids=['EFFECT_ONE'], status='active', description='组合')
    connection, rows, adjudicator = catalog(tmp_path, {'主类型.json': [genre()],
        '类型组合总表.json': [combo], '类型动态规则总表.json': [dict(rule_id='RULE_ONE', status='active')],
        '类型动态候选效果.json': [dict(effect_id='EFFECT_ONE', rule_id='RULE_OTHER', status='active')]})
    try:
        result = adjudicator.review(root(rows, '类型组合总表.json'))
        assert result['state'] == 'blocked'
        assert any('EFFECT_ONE' in p and 'RULE_OTHER' in p for p in result['conflicts'])
        assert all(c['root_ids'] for c in result['contract']['constituents'])
    finally:
        connection.close()


def test_divergent_link_id_is_not_merged_across_source_tables(tmp_path: Path) -> None:
    child = genre()
    child.update(type_id='SUB_ONE', type_kind='SUBGENRE', parent_id='GENRE_ONE')
    link = dict(connection_id='TSC_ONE', source_id='SUB_ONE', source_kind='subgenre',
                target_id='GENRE_ONE', target_kind='genre', connection_type='TYPE_REFINES', status='active')
    other = dict(link, target_id='GENRE_OTHER')
    connection, rows, adjudicator = catalog(tmp_path, {'主类型.json': [genre()], '子类型.json': [child],
        '类型兼容关系.json': [link], '类型静态连接总表.json': [other]})
    try:
        result = adjudicator.review(root(rows, '类型兼容关系.json'))
        assert result['state'] == 'blocked'
        assert any('类型静态连接总表.json' in p for p in result['conflicts'])
    finally:
        connection.close()


@pytest.mark.parametrize(('focus', 'replacement_status', 'applied'), [
    (True, 'active', True), (False, 'active', False), (True, 'pending', False)])
def test_source_repair_requires_active_unique_focus_evidence(tmp_path: Path, focus: bool,
                                                           replacement_status: str, applied: bool) -> None:
    old = dict(connection_id='TSC_OLD', source_id='GENRE_OLD', source_kind='genre', target_id='CONCEPT_ONE',
               target_kind='concept', connection_type='TYPE_SUPPORTS_CONCEPT', direction='directed',
               relation_scope='genre_level', status='pending', limitations=['仅可选表达'], not_guaranteed=['不保证发生'])
    new = dict(old, connection_id='TSC_NEW', source_id='GENRE_ONE', status=replacement_status)
    combo = dict(combination_id='COMBO_ONE', primary_type_id='GENRE_ONE', type_ids=['GENRE_ONE'],
                 concept_ids=['CONCEPT_ONE'] if focus else [], static_connection_ids=['TSC_OLD'],
                 status='active', description='有具体焦点的类型组合')
    connection, rows, adjudicator = catalog(tmp_path, {'主类型.json': [genre()],
        '类型组合总表.json': [combo], '类型静态连接总表.json': [old, new]})
    try:
        record = root(rows, '类型组合总表.json')
        result = adjudicator.review(record)
        assert bool(result['source_repair']) is applied
        assert result['contract']['constituent_fields']['static_connection_ids'] == ['TSC_OLD']
        expected = ['TSC_NEW'] if applied else ['TSC_OLD']
        assert result['contract']['effective_constituent_fields']['static_connection_ids'] == expected
        assert result['state'] == ('design_ready' if applied else 'blocked')
        assert adjudicator.records[record['id']][1]['static_connection_ids'] == ['TSC_OLD']
        if applied:
            repair = result['source_repair'][0]
            assert repair['exact_comparison_fields']['target_id'] == 'CONCEPT_ONE'
            assert repair['focus_evidence'] == {'concept_ids': ['CONCEPT_ONE']}
            assert repair['original_unchanged']
    finally:
        connection.close()


def test_same_type_id_is_scoped_for_hierarchy_and_components(tmp_path: Path) -> None:
    from collections import defaultdict

    from nw.materials.type_adjudication import _ref
    from nw.materials.type_hierarchy import selection_hierarchy

    ontology_parent = genre(level=1, ancestor_ids=[], child_ids=[])
    a_parent = {**ontology_parent, 'canonical_name': '分表类型一'}
    a_peer = {**a_parent, 'type_id': 'GENRE_TWO'}
    ontology_peer = {**ontology_parent, 'type_id': 'GENRE_TWO'}
    ontology_child = {**genre(), 'type_id': 'SUB_ONE', 'type_kind': 'SUBGENRE', 'parent_id': 'GENRE_ONE',
                      'ancestor_ids': ['GENRE_ONE'], 'level': 2}
    a_child = {**ontology_child, 'type_id': 'SUBGENRE_ONE'}
    hybrid = {**genre(), 'type_id': 'HYBRID_TEST', 'type_kind': 'HYBRID_GENRE',
              'component_type_ids': ['GENRE_ONE', 'GENRE_TWO']}
    connection, rows, adjudicator = catalog(tmp_path, {
        TYPE_TABLE: [ontology_parent, ontology_peer, ontology_child, hybrid],
        '主类型.json': [a_parent, a_peer], '子类型.json': [a_child],
        '混合类型.json': [hybrid],
    })
    try:
        indexed = defaultdict(dict)
        for row in rows:
            if row['kind'] == 'record':
                indexed[row['fragment_key']][row['key']] = row
        a = indexed['主类型.json']
        b = indexed[TYPE_TABLE]
        for block, ident, expected in (
            (TYPE_TABLE,'SUB_ONE',[b['GENRE_ONE']['id']]),
            ('子类型.json','SUBGENRE_ONE',[a['GENRE_ONE']['id']]),
            (TYPE_TABLE,'HYBRID_TEST',[b['GENRE_ONE']['id'],b['GENRE_TWO']['id']]),
            ('混合类型.json','HYBRID_TEST',[a['GENRE_ONE']['id'],a['GENRE_TWO']['id']]),
        ):
            result = adjudicator.review(indexed[block][ident])
            assert sorted(result['related']) == sorted(expected)
        workspace = tmp_path / 'workspace'
        def source(row: dict, value: dict) -> dict:
            return {'source': {**_ref(row), 'profile': 'type_identity'},
                    'original_text': json.dumps(value, ensure_ascii=False)}
        given = [source(b['GENRE_ONE'], ontology_parent), source(a['GENRE_ONE'], a_parent)]
        hierarchy = selection_hierarchy(workspace, given)
        assert {entry['parent_source_id']: entry['subtype_ids'] for entry in hierarchy} == {
            b['GENRE_ONE']['id']: ['SUB_ONE'], a['GENRE_ONE']['id']: ['SUBGENRE_ONE'],
        }
        assert selection_hierarchy(workspace, [source(indexed['子类型.json']['SUBGENRE_ONE'], a_child)]) == hierarchy[1:]
        stale = {**given[1], 'source': {**given[1]['source'], 'sha256': '0' * 64}}
        assert not selection_hierarchy(workspace, [stale])
    finally:
        connection.close()


def test_source_mappings_use_only_exact_target_and_keep_original_and_current_roles(tmp_path: Path) -> None:
    from nw.materials.type_sources import mapping_evidence

    a = {**genre(), 'schema_version': 'TYPE_A-1.0.0'}
    b = {**genre(), 'schema_version': 'TYPE_H1A-1.0.0'}
    mapping = {'mapping_id': 'MAP_0001', 'source_name': '来源名', 'source_type': 'genre_standard',
               'target_id': 'GENRE_ONE', 'mapping_type': 'normalized', 'evidence_type': 'template',
               'status': 'active', 'source_refs': ['web_novel_taxonomy_standard']}
    connection, rows, _ = catalog(tmp_path, {
        TYPE_TABLE: [b], '主类型.json': [a], '类型来源映射.json': {'mappings': [mapping]},
    })
    connection.close()
    ref_a, ref_b, ref_m = (root(rows, name) for name in ('主类型.json', TYPE_TABLE, '类型来源映射.json'))
    workspace = tmp_path / 'workspace'
    qualifications = {ref_m['id']: {'state': 'reference', 'sha256': ref_m['sha256'],
                                   'file_sha256': ref_m['file_sha256']}}
    [match] = mapping_evidence(workspace, [ref_a, ref_b], qualifications)
    assert match['target']['source_ref']['id'] == ref_a['id']
    assert match['target']['schema_version'] == 'TYPE_A-1.0.0'
    assert match['original'] == mapping
    assert match['qualification'] == 'reference'
    assert match['source_ref']['id'] == ref_m['id']
    assert not mapping_evidence(workspace, [ref_b], qualifications)
    assert not mapping_evidence(workspace, [ref_a], {})
    assert not mapping_evidence(workspace, [{**ref_a, 'sha256': '0' * 64}], qualifications)


def test_split_hierarchy_and_mapping_do_not_join_separate_source_files(tmp_path: Path) -> None:
    from contextlib import closing
    from nw.materials.catalog import _connect
    from nw.materials.type_hierarchy import selection_hierarchy
    from nw.materials.type_sources import mapping_evidence
    from test_material_catalog import _manifest

    parent = genre(level=1, ancestor_ids=[], child_ids=[], schema_version='TYPE_A-1.0.0')
    child = {**parent, 'type_id': 'SUBGENRE_ONE', 'type_kind': 'SUBGENRE',
             'parent_id': 'GENRE_ONE', 'ancestor_ids': ['GENRE_ONE'], 'level': 2}
    mapping = {'mapping_id': 'MAP_0001','source_type': 'genre_standard','target_id': 'GENRE_ONE'}
    raw_a = ('SOURCE: 主类型.json\n=====\n' + json.dumps([parent], ensure_ascii=False)).encode('utf-8')
    raw_b = ('SOURCE: 子类型.json\n=====\n'+json.dumps([child], ensure_ascii=False)
             +'\nSOURCE: 类型来源映射.json\n=====\n'+json.dumps({'mappings':[mapping]})).encode('utf-8')
    manifest = _manifest(tmp_path/'sources', tmp_path, [('main.txt','types',raw_a), ('other.txt','types',raw_b)])
    build_catalog(tmp_path, tmp_path/'sources', manifest)
    index_units(tmp_path, None)
    with closing(_connect(tmp_path, write=False)) as db:
        records = [dict(r) for r in db.execute(_UNITS)]
        root_a = root(records, '主类型.json')
        root_b = root(records, '子类型.json')
        root_map = root(records, '类型来源映射.json')
        pin = {**root_b, 'profile': 'type_identity'}
        original = {'source': pin, 'original_text': json.dumps(child)}
        assert not selection_hierarchy(tmp_path, [original])
        assert TypeAdjudicator(db).review(root_b)['contract']['constituents'][0]['root_ids'] == []
        qualification = {root_map['id']: {**root_map,'state':'reference'}}
        assert not mapping_evidence(tmp_path, [root_a], qualification)


def test_type_name_evidence_preserves_separate_roles_and_alias_source(tmp_path: Path) -> None:
    from nw.materials.type_sources import ontology_name_evidence

    main = genre(level=1, ancestor_ids=[], child_ids=[], schema_version='TYPE_H1A-1.0.0')
    child = {**main, 'type_id': 'SUB_ONE_TEST', 'type_kind': 'SUBGENRE', 'parent_id': 'GENRE_ONE',
             'ancestor_ids': ['GENRE_ONE'], 'level': 2, 'canonical_name': '穿越'}
    tag = {**main, 'type_id': 'SUBJECT_TAG_TEST', 'type_kind': 'SUBJECT_TAG', 'canonical_name': '穿越'}
    mechanism = {**main,'type_id':'PLOT_MECHANISM_TEST','type_kind':'PLOT_MECHANISM','canonical_name':'穿越机制'}
    alias_block = r'类型本体\类型别名表.json'
    connection, rows, _ = catalog(tmp_path, {
        TYPE_TABLE: [main, child, tag, mechanism],
        alias_block: {'aliases': [{'alias': '穿越', 'canonical': 'GENRE_ONE'}]},
    })
    connection.close()
    w = tmp_path/'workspace'
    [e] = ontology_name_evidence(w, '作者仅明确穿越题材', related_mechanisms={'穿越':'PLOT_MECHANISM_TEST'})
    assert e['term'] == '穿越'
    assert {item['type_id']: item['type_kind'] for item in e['alternatives']} == {
        'GENRE_ONE':'GENRE', 'SUB_ONE_TEST':'SUBGENRE', 'SUBJECT_TAG_TEST':'SUBJECT_TAG',
        'PLOT_MECHANISM_TEST':'PLOT_MECHANISM',
    }
    assert e['aliases'] == [{'target_id':'GENRE_ONE','source_ref':e['aliases'][0]['source_ref']}]
    assert e['aliases'][0]['source_ref']['fragment_key'] == alias_block
    child_actual = next(item for item in e['alternatives'] if item['type_id']=='SUB_ONE_TEST')
    assert child_actual['parent']['type_id']=='GENRE_ONE'
    assert child_actual['parent']['source_ref']['id']==root(rows,TYPE_TABLE)['id']
    assert next(item for item in e['alternatives'] if item['type_id']=='PLOT_MECHANISM_TEST')['related_name_only']
    assert not ontology_name_evidence(w, '', selected_terms=['其他项目'])
    assert [v['term'] for v in ontology_name_evidence(w, '', selected_terms=['SUBJECT_TAG_TEST'])]==['穿越']
