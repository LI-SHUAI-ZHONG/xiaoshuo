from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from nw.cli import main


def _manifest(root: Path, tmp: Path, entries: list[tuple[str, str, bytes]]) -> Path:
    files = []
    root.mkdir(exist_ok=True)
    for path, family, data in entries:
        (root / path).write_bytes(data)
        files.append(dict(path=path, family=family, layer='baseline',
                          sha256=sha256(data).hexdigest(), bytes=len(data)))
    manifest = tmp / 'manifest.json'
    manifest.write_text(json.dumps(dict(schema_version=1, catalog_inputs=files)), encoding='utf-8')
    return manifest


def _run(tmp: Path, capsys, action: str, *options: str, code: int = 0):
    result = main(['--workspace', str(tmp / 'workspace'), 'materials', action, *options])
    output = capsys.readouterr()
    assert result == code, output.err
    return json.loads(output.out) if code == 0 else output.err


def test_placement_links_recovered_exact_version_without_promoting_it(tmp_path, capsys):
    root = tmp_path / 'sources'
    intact = b'{"baseline_bindings": 4, "files":{"library":{"runtime_fields":4}}}'
    manifest = _manifest(root, tmp_path, [
        ('original.json', 'provenance', b'\0' * len(intact)),
        ('archive.json', 'support', intact),
    ])
    data = json.loads(manifest.read_text(encoding='utf-8'))
    archive, damaged = data['catalog_inputs'][1], data['catalog_inputs'][0]
    archive['layer'] = 'historical'
    data['file_registry'] = [
        {**row, 'usage': usage, 'role': 'fusion provenance', 'physical_status': physical}
        for row, usage, physical in [(archive, 'version_review', 'nonempty'), (damaged, 'quarantined', 'all_nul')]
    ]
    data['recovery_candidates'] = [{
        'damaged': 'original.json', 'damaged_sha256': damaged['sha256'],
        'candidate': 'archive.json', 'candidate_sha256': archive['sha256'],
        'decision': 'verified_historical_recovery',
    }]
    manifest.write_text(json.dumps(data), encoding='utf-8')
    _run(tmp_path, capsys, 'build', '--source-root', str(root), '--manifest', str(manifest))
    _run(tmp_path, capsys, 'index-units')
    placement = _run(tmp_path, capsys, 'audit-placement', '--manifest', str(manifest),
                     '--source-root', str(root), '--details')
    assert placement['summary']['by_placement'] == {'source_quarantined': 1, 'recovery_source': 1}
    assert placement['summary']['by_live_status'] == {'verified': 2}
    original = next(row for row in placement['files'] if row['path'] == 'original.json')
    assert original['catalog'][0]['status'] == 'NUL'
    assert original['recovery_links'][0]['candidate_sha256'] == archive['sha256']
    frozen = next(row for row in placement['files'] if row['path'] == 'archive.json')
    positions = _run(tmp_path, capsys, 'units', '--source-id', frozen['catalog'][0]['source_id'])
    item = next(row for row in positions['units'] if row['locator'] == '/files/library/runtime_fields')
    route = _run(tmp_path, capsys, 'route', item['unit_id'])
    assert route['eligibility'] == 'reference_only' and route['execution_allowed'] is False
    (root / 'archive.json').write_bytes(intact.replace(b'4', b'5'))
    changed = _run(tmp_path, capsys, 'audit-placement', '--manifest', str(manifest),
                   '--path', 'archive.json', '--source-root', str(root))
    assert changed['files'][0]['live_status'] == 'version_changed'


def test_embedded_library_metadata_preserves_original_fragment_and_exposes_own_fields(tmp_path, capsys):
    root = tmp_path / 'sources'
    data = ('### 119.10_读者自反时刻\r\n**定义**：反思。\r\n'
            '- **条目类型**：概念型\r\n- **板块**：120.1\r\n'
            '**定义**：视角切换的层级。\r\n**调用条件**：需要切换时。\r\n'
            '**调用标签**：#概念·视角切换类型\r\n'
            '## 固定视角切换节奏\r\n\r\n- **条目类型**：概念型\r\n- **板块**：120.2\r\n'
            '**定义**：按既定顺序轮换。\r\n**设计指令**：在章边界切换。\r\n').encode()
    manifest = _manifest(root, tmp_path, [('library.txt', 'library', data)])
    _run(tmp_path, capsys, 'build', '--source-root', str(root), '--manifest', str(manifest))
    fragment = _run(tmp_path, capsys, 'list', '--key', '119.10_读者自反时刻')['fragments'][0]
    _run(tmp_path, capsys, 'index-units')
    first = _run(tmp_path, capsys, 'units', '--fragment-id', fragment['fragment_id'])
    nested = [item for item in first['units'] if item['kind'] == 'embedded_entry']
    assert [item['key'] for item in nested] == ['120.1_视角切换类型', '120.2_固定视角切换节奏']
    reading = _run(tmp_path, capsys, 'show', nested[0]['unit_id'])['text']
    assert '需要切换时' in reading and '按既定顺序' not in reading
    refreshed = _run(tmp_path, capsys, 'index-units', '--fragment-id', fragment['fragment_id'])
    assert refreshed['added_units'] == 0
    assert _run(tmp_path, capsys, 'show', fragment['fragment_id'])['text'].encode() == data


def test_materials_cli_preserves_duplicate_labels_and_old_source_versions(tmp_path, capsys):
    root = tmp_path / 'sources'
    source = 'library.txt'
    v1 = ('\ufeff# 板块\r\n### 1.1_条件\r\n【定义】甲\r\n'
          '#### 运行层升级\r\n{}\r\n### 1.1_条件\r\n【定义】乙\r\n').encode()
    mf = _manifest(root, tmp_path, [(source, 'library', v1)])
    args = ['--source-root', str(root), '--manifest', str(mf)]
    first = _run(tmp_path, capsys, 'build', *args)
    assert first['imported'] == 1
    ref = first['sources'][0]['source_id']
    result = _run(tmp_path, capsys, 'list', '--source-id', ref)
    entries = [row for row in result['fragments'] if row['kind'] == 'library_entry']
    assert len(entries) == 2
    assert entries[0]['key'] == entries[1]['key'] == '1.1_条件'
    assert entries[0]['fragment_id'] != entries[1]['fragment_id']
    assert sum(row['byte_end']-row['byte_start'] for row in result['fragments']) == len(v1)
    assert any(row['kind'] == 'library_upgrade' for row in result['fragments'])
    assert _run(tmp_path, capsys, 'build', *args)['reused'] == 1
    (root / source).write_bytes(b'changed')
    assert 'SHA-256' in _run(tmp_path, capsys, 'build', *args, code=1)
    _manifest(root, tmp_path, [(source, 'library', b'### 1.1_second\n')])
    second = _run(tmp_path, capsys, 'build', *args)
    assert second['sources'][0]['source_id'] != ref
    old = _run(tmp_path, capsys, 'show', entries[0]['fragment_id'])
    assert old['text'] == '### 1.1_条件\r\n【定义】甲\r\n'
    assert old['sha256'] == sha256(old['text'].encode()).hexdigest()


def test_network_exact_fragments_and_quarantine_are_visible(tmp_path, capsys):
    root = tmp_path / 'sources'
    dynamic = json.dumps({'dynamic': {'connections': [
        {'id': 'C1', 'effect': 'text ] }, {', 'id_copy': [1, 2]},
        {'id': 'C1', 'effect': 'next'},
    ]}}).encode()
    static = b'{"connections":[{"source":"A","target":"B","type":"constraint"}]}'
    sources = [('dynamic.txt','dynamic',dynamic),('static.txt','static',static),
               ('broken.json','static',b'{"connections":[bad]}'),
               ('null.txt','anchors',b'abc\0'),
               ('encoding.txt','library',b'\xc2\x01')]
    mf = _manifest(root, tmp_path, sources)
    built = _run(tmp_path,capsys,'build','--source-root',str(root),'--manifest',str(mf))
    reports = {row['path']:row for row in built['sources']}
    assert reports['broken.json']['status'] == 'INVALID_JSON'
    assert reports['null.txt']['status'] == 'NUL'
    assert reports['encoding.txt']['status'] == 'INVALID_ENCODING'
    ref = reports['dynamic.txt']['source_id']
    result = _run(tmp_path,capsys,'list','--source-id',ref)
    fragments = result['fragments']
    assert [row['key'] for row in fragments if row['kind']=='network_edge'] == ['C1','C1']
    assert [row['byte_start'] for row in fragments] == [0]+[row['byte_end'] for row in fragments[:-1]]
    assert fragments[-1]['byte_end'] == len(dynamic)
    first = next(row for row in fragments if row['kind']=='network_edge')
    assert json.loads(_run(tmp_path,capsys,'show',first['fragment_id'])['text'])['effect'] == 'text ] }, {'
    db = tmp_path / 'workspace' / 'materials' / 'catalog.db'
    with sqlite3.connect(db) as con:
        con.execute('UPDATE fragments SET payload=? WHERE id=?',(b'modified',first['fragment_id']))
    assert 'hash mismatch' in _run(tmp_path,capsys,'show',first['fragment_id'],code=1)


def test_manifest_paths_do_not_escape_source_root(tmp_path, capsys):
    root = tmp_path / 'sources'
    mf = _manifest(root,tmp_path,[('../outside.txt','library',b'outside')])
    result = _run(tmp_path,capsys,'build','--source-root',str(root),'--manifest',str(mf),code=1)
    assert 'outside the source root' in result


def test_historical_network_separates_fenced_original_and_appended_upgrade(tmp_path, capsys):
    root = tmp_path / 'sources'
    edge = '{"id":"C1","effect":"原文"}'
    source = ('旧说明\r\n\r\n```json\r\n{"动态网络连接_完整版":{"连接列表":[' + edge + ']}}\r\n'
              '```\r\n===== 缺失升级资料吸收开始 =====\r\n升级对象\r\n'
              '===== 缺失升级资料吸收结束 =====\r\n').encode()
    manifest = _manifest(root, tmp_path, [('dynamic.txt', 'dynamic', source)])
    result = _run(tmp_path, capsys, 'build', '--source-root', str(root), '--manifest', str(manifest))
    version = result['sources'][0]
    fragments = _run(tmp_path, capsys, 'list', '--source-id', version['source_id'])['fragments']
    network = next(row for row in fragments if row['kind'] == 'network_edge')
    upgrade = next(row for row in fragments if row['kind'] == 'network_upgrade')
    assert _run(tmp_path, capsys, 'show', network['fragment_id'])['text'] == edge
    assert '升级对象' in _run(tmp_path, capsys, 'show', upgrade['fragment_id'])['text']
    assert b''.join(
        _run(tmp_path, capsys, 'show', row['fragment_id'])['text'].encode() for row in fragments
    ) == source


def test_nested_type_records_keep_exact_locations_and_upgrade_separate(tmp_path, capsys):
    root = tmp_path / 'sources'
    prefix = 'SOURCE: 类型关系.json\r\n============\r\n'
    base = '{"容器":{"分/组":[{"connection_id":"D1","conditions":["甲"],"not_guaranteed":["乙"]},' \
           '{"connection_id":"D1","effects":["丙"]}],"empty":[]},"运行层升级":{"conditions":["升级"]}}'
    append = '\r\n## 原版条目补全\r\n### D1\r\n【运行层升级】\r\n{"after":true}\r\n'
    mf = _manifest(root, tmp_path, [('links.txt', 'type_links', (prefix+base+append).encode())])
    _run(tmp_path, capsys, 'build', '--source-root', str(root), '--manifest', str(mf))
    (root / 'links.txt').unlink()
    indexed = _run(tmp_path, capsys, 'index-units')
    assert indexed['indexed'] == 1
    refs = _run(tmp_path, capsys, 'units', '--key', 'D1')['units']
    records = [r for r in refs if r['kind'] == 'record']
    assert [r['locator'] for r in records] == ['/容器/分~1组/0', '/容器/分~1组/1']
    assert records[0]['unit_id'] != records[1]['unit_id']
    data = _run(tmp_path, capsys, 'show', records[0]['unit_id'])
    assert data['text'] == '{"connection_id":"D1","conditions":["甲"],"not_guaranteed":["乙"]}'
    assert data['byte_start'] == len((prefix + base[:base.index('{"connection_id"')]).encode())
    assert data['line_start'] == 3
    condition = _run(tmp_path, capsys, 'units', '--kind', 'condition')['units']
    assert [r['locator'] for r in condition] == ['/容器/分~1组/0/conditions']
    assert _run(tmp_path, capsys, 'show', condition[0]['unit_id'])['text'] == '["甲"]'
    upgrade = _run(tmp_path, capsys, 'units', '--kind', 'upgrade')['units']
    assert len(upgrade) == 2
    assert all(row['origin'] == 'upgrade' for row in upgrade)
    assert _run(tmp_path, capsys, 'units', '--kind', 'empty_collection')['units'][0]['locator'] == '/容器/empty'
    assert _run(tmp_path, capsys, 'index-units')['reused'] == 1


def test_library_fields_keep_conditions_exceptions_and_examples_as_source_spans(tmp_path, capsys):
    root = tmp_path / 'sources'
    source = ('### 128.4_调取\r\n【定义】\r\n三层筛选\r\n【调用条件）当前目标已确认\r\n'
              '**写作指令**：转为动作。\r\n**例外处理**：缺条件先停。\r\n'
              '【判定标准】有证据\r\n【反面案例】只有关键词\r\n'
              '【运行层升级】\r\n{"指令":"别覆盖定义"}\r\n').encode()
    mf = _manifest(root,tmp_path,[('library.txt','library',source)])
    _run(tmp_path,capsys,'build','--source-root',str(root),'--manifest',str(mf))
    _run(tmp_path,capsys,'index-units')
    units = _run(tmp_path,capsys,'units','--key','128.4_调取')['units']
    by_kind = {r['kind']:r for r in units}
    assert set(by_kind) == {'definition','condition','instruction','exception','check','counterexample','upgrade'}
    cond = _run(tmp_path,capsys,'show',by_kind['condition']['unit_id'])
    assert cond['text'] == '【调用条件）当前目标已确认\r\n'
    assert cond['label'] == '调用条件'
    assert cond['line_start'] == 4
    assert by_kind['upgrade']['origin'] == 'upgrade'


def test_malformed_json_and_nonjson_attachments_have_explicit_disposition(tmp_path, capsys):
    root = tmp_path / 'sources'
    source = ('SOURCE: broken.json\n=====\n{"bad":}\n'
              'SOURCE: guide.md\n=====\n## 规则说明\n按当前条件选用。\n'
              'SOURCE: other.json\n=====\n{"items":[{"type_id":"T1"}]}\n尾部未识别内容\n').encode()
    mf = _manifest(root,tmp_path,[('types.txt','types',source)])
    _run(tmp_path,capsys,'build','--source-root',str(root),'--manifest',str(mf))
    _run(tmp_path,capsys,'index-units')
    rows = _run(tmp_path,capsys,'units')['units']
    assert len([r for r in rows if r['kind'] == 'invalid_json']) == 1
    assert len([r for r in rows if r['kind'] == 'attachment']) == 1
    assert len([r for r in rows if r['kind'] == 'residual']) == 1
    assert len([r for r in rows if r['key'] == 'T1' and r['kind'] == 'record']) == 1


def test_type_profiles_and_inline_anchor_upgrades_stay_findable(tmp_path, capsys):
    root = tmp_path / 'sources'
    profiles = ('SOURCE: 类型总表.json\r\n=====\r\n{}\r\n---\r\n# 类型画像补全\r\n'
                '## 玄幻\r\n【读者期待】选择有代价。\r\n'
                '【篇幅适配】长篇。\r\n## 类型系统原版条目补全\r\n'
                '### 玄幻\r\n【运行层升级】\r\n{"rev":1}\r\n').encode()
    anchor = ('| ID1.1 | 学徒 | 学习 | 进门 | 身份 | '
              '<details><summary>运行层升级</summary><code>{"id":1}</code></details>\r\n'
              '### ID1.1\r\n【运行层升级】\r\n{"id":1}\r\n').encode()
    mf = _manifest(root,tmp_path,[('types.txt','types',profiles),('anchors.txt','anchors',anchor)])
    _run(tmp_path,capsys,'build','--source-root',str(root),'--manifest',str(mf))
    _run(tmp_path,capsys,'index-units')
    typed = _run(tmp_path,capsys,'units','--key','玄幻')['units']
    assert {r['kind'] for r in typed} == {'type_profile','reader_expectation','length_guidance','upgrade'}
    original = next(r for r in typed if r['kind']=='reader_expectation')
    assert _run(tmp_path,capsys,'show',original['unit_id'])['text'] == '【读者期待】选择有代价。\r\n'
    units = _run(tmp_path,capsys,'units','--key','ID1.1')['units']
    assert len([r for r in units if r['kind']=='upgrade']) == 2
    assert len([r for r in units if r['kind']=='condition']) == 1
    assert _run(tmp_path,capsys,'units','--kind','residual')['units'] == []


def test_route_keeps_conditions_and_exceptions_with_the_same_source_record(tmp_path, capsys):
    root = tmp_path / 'sources'
    library = ('### 128.4_板块调用的三层筛选法\n【定义】先定章节功能。\n'
               '【调用条件】已明确章节任务。\n【例外处理】信息不足时待定。\n'
               '【示例】只选第一次抉择。\n【运行层升级】\n{"approved":true}\n'
               '### 106.1_全篇语言风格统一\n【指令】观察身体信号。\n'
               '### 108.1_写作前检查\n【判定标准】视角人物已确认。\n').encode()
    mf = _manifest(root,tmp_path,[('library.txt','library',library)])
    _run(tmp_path,capsys,'build','--source-root',str(root),'--manifest',str(mf))
    _run(tmp_path,capsys,'index-units')
    units = _run(tmp_path,capsys,'units')['units']
    original = next(u for u in units if u['kind']=='definition')
    route = _run(tmp_path,capsys,'route',original['unit_id'])
    assert route['profile'] == 'material_selection'
    assert route['stage'] == '资料装配'
    assert route['interpretation'] == 'needs_review'
    assert route['eligibility'] == 'candidate'
    assert route['execution_allowed'] is False
    assert route['source']['sha256'] == original['sha256']
    assert set(x['kind'] for x in route['supporting_fields']) == {'condition','exception'}
    preflight = next(u for u in units if u['kind']=='check')
    assert _run(tmp_path, capsys, 'route', preflight['unit_id'])['stage'] == '写作前检查'
    for kind, expected in [('example','reference_only'),('upgrade','reference_only'),('instruction','suspended')]:
        unit = next(u for u in units if u['kind']==kind)
        found = _run(tmp_path,capsys,'route',unit['unit_id'])
        assert found['eligibility']==expected
        assert found['execution_allowed'] is False


def test_routing_audit_counts_every_fragment_and_unit_without_promoting_fixtures(tmp_path, capsys):
    root = tmp_path / 'sources'
    types = ('SOURCE: 作品知识库\\测试夹具\\T.json\n====\n[{"id":"T1","conditions":[]}]\n'
             'SOURCE: 类型总表.json\n====\n[{"id":"T2","conditions":["x"]}]\n').encode()
    mf = _manifest(root,tmp_path,[('types.txt','types',types),
                                 ('static.txt','static',b'{"connections":[{"source":"A","target":"B","condition":"C"}]}')])
    built = _run(tmp_path,capsys,'build','--source-root',str(root),'--manifest',str(mf))
    assert 'index-units' in _run(tmp_path,capsys,'audit-routes',code=1)
    _run(tmp_path,capsys,'index-units')
    audit = _run(tmp_path,capsys,'audit-routes')
    unit_count = len(_run(tmp_path,capsys,'units')['units'])
    assert audit['coverage']['unit'] == unit_count
    assert audit['coverage']['fragment'] == sum(sum(s['counts'].values()) for s in built['sources'])
    assert audit['execution_allowed'] == 0
    assert audit['profiles']['test_fixture'] > 0
    assert audit['profiles']['static_binding'] > 0
    fixture = _run(tmp_path,capsys,'units','--key','T1','--kind','record')['units'][0]
    item = _run(tmp_path,capsys,'route',fixture['unit_id'])
    assert item['stage'] == '回归测试'
    assert item['eligibility'] == 'reference_only'
    assert item['source']['fragment_key'].endswith('T.json')


def test_endpoint_identity_requires_exact_text_and_preserves_migration_evidence(tmp_path, capsys):
    root = tmp_path/'sources'
    library = ('### 5.1_甲\n【定义】甲是原文。\n'
               '### 板块156 审美\n【定义】审美。\n\n**156.1 用词审美**\n\n【定义】字词。\n').encode()
    old = '### 7.1_旧词\n【定义】旧定义。\n'.encode()
    network = json.dumps({'connections':[
        {'id':'C00001','source':'5.1_甲','target':'156.1_用词审美','type':'约束'},
        {'id':'C00002','source':'5.1_乙','target':'7.1_旧词','type':'约束'},
        {'id':'C00003','source':'5.1_丙','target':'8.1_失踪','type':'约束'},
    ]},ensure_ascii=False).encode()
    mf = _manifest(root,tmp_path,[('library.txt','library',library),('old.txt','library',old),
                                 ('network.json','dynamic',network)])
    value=json.loads(mf.read_text(encoding='utf-8'))
    value['catalog_inputs'][1]['layer']='historical'
    mf.write_text(json.dumps(value),encoding='utf-8')
    _run(tmp_path,capsys,'build','--source-root',str(root),'--manifest',str(mf))
    aliases = tmp_path/'aliases.json'
    aliases.write_text(json.dumps({'exact_alias':{'5.1_乙':'5.1_甲'},'unresolved_similar':[]}),encoding='utf-8')
    migrations=tmp_path/'migrations.json'
    migrations.write_text(json.dumps({'migrations':[
        {'old_id':'C00002','new_id':'C00001','source':'5.1_甲','target':'156.1_用词审美','type':'约束'},
        {'old_id':'C09999','new_id':'C00002','source':'5.1_乙','target':'wrong','type':'约束'},
    ]}),encoding='utf-8')
    report=_run(tmp_path,capsys,'audit-identities','--legacy-aliases',str(aliases),'--dynamic-migrations',str(migrations))
    nodes={x['label']:x for x in report['endpoints']}
    assert {k:v['status'] for k,v in nodes.items()}=={
        '5.1_甲':'current_heading','156.1_用词审美':'current_subheading',
        '5.1_乙':'alias_review','7.1_旧词':'historical_heading',
        '5.1_丙':'number_review','8.1_失踪':'missing',
    }
    ref=nodes['156.1_用词审美']['locations'][0]
    exact=library[ref['byte_start']:ref['byte_end']]
    assert exact.startswith('**156.1 用词审美**'.encode())
    assert ref['sha256']==sha256(exact).hexdigest()
    assert report['migration_counts']=={'target_verified':1,'signature_conflict':1}
    assert report['migrations'][0]['old_id_reused'] is True
    assert all(x['execution_allowed'] is False for x in nodes.values())
    cached=tmp_path/'workspace'/'materials'/'F2_网络身份对账.json'
    cached.write_text(json.dumps(report),encoding='utf-8')
    _run(tmp_path,capsys,'index-units')
    edge=nodes['5.1_甲']['edge_references'][0]['fragment_id']
    decision=_run(tmp_path,capsys,'route',edge)
    assert {x['side']:x['status'] for x in decision['network_identity']}=={
        'source':'current_heading','target':'current_subheading',
    }

