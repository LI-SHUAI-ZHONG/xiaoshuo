from dataclasses import asdict
from hashlib import sha256
import json
import sqlite3

import pytest

from nw.materials.adjudication import build_adjudications
from nw.materials.binding import resolve_materials, validate_bindings
from nw.materials import library_adjudication
from nw.materials.catalog import build_catalog, list_catalog
from nw.materials.route_catalog import audit_routes, route
from nw.materials.unit_catalog import index_units
from nw.novel_flow import JobRequest, resume_job, start_job
from nw.store import Store
from nw.story_state import adopt_story
from nw.task_models import Budget
from story_fixture import baseline
from test_material_catalog import _manifest
from test_material_workflow import choose
from test_novel_flow import Model, author, config


def compiled_source(tmp_path, monkeypatch):
    text = ('### 1.1_行动动机\n'
            '【定义】人物的关键行动必须由具体目标驱动，并承担选择造成的后果。\n'
            '【调用条件】人物作出本场关键决定时。\n'
            '【设计指令】在决定前展示具体目标，在决定后兑现选择造成的代价。\n'
            '【判定标准】检查目标、选择和后果是否形成可定位的因果链。\n'
            '【例外处理】信息尚未公开时，仅按该人物已经知道的内容核查。\n')
    data = text.encode()
    monkeypatch.setitem(library_adjudication._PINNED, 'library', sha256(data).hexdigest())
    manifest = _manifest(tmp_path / 'source', tmp_path, [('library.txt', 'library', data)])
    build_catalog(tmp_path, tmp_path / 'source', manifest)
    index_units(tmp_path, None)
    root = list_catalog(tmp_path, None, '1.1_行动动机')['fragments'][0]
    summary = build_adjudications(tmp_path)
    from fake_binding_reviews import install_review_fixtures
    install_review_fixtures(tmp_path)
    result = route(tmp_path, root['fragment_id'])
    assert result['interpretation'] == 'adjudicated'
    audit = audit_routes(tmp_path)
    assert audit['adjudication']['status'] == 'current'
    assert audit['adjudication']['summary'] == summary
    return root, result, summary


class AdjudicatedModel(Model):
    def __init__(self, *, omit_obligation=False):
        super().__init__()
        self.omit_obligation = omit_obligation

    def generate(self, messages, **params):
        prompt = messages[0]['content']
        data = json.loads(messages[-1]['content'])
        if 'candidate_cards' in prompt:
            output = super().generate(messages, **params)
            proposed = json.loads(output.text)
            if data['scope'] != 'book':
                ident = data['materials'][0]['source']['id']
                obligations = data['materials'][0]['review']['contract']['obligations']
                for item in proposed['candidate_cards']:
                    item['material_bindings'] = {'scene': {ident: {
                        'function': '以行动调查', 'parameter': '沈砚要查封条',
                        'observable': '因调查目标举灯，承受烧伤并看清印记', 'check': '目标、选择、代价相连',
                        'source_scope': {field['id']: {'disposition': 'required', 'reason': '本场采用'}
                                         for field in obligations}}}}
            output.text = json.dumps(proposed, ensure_ascii=False)
            return output
        if '{"recommendation"' in prompt:
            self.calls.append(messages)
            draft, contract = data['draft'], data['material_review']
            assert 'source_contract' in contract['checks'][0]
            assert '后果' in json.dumps(contract['checks'][0]['source_contract'], ensure_ascii=False)
            text = draft['text']
            evidence = {**contract['draft'], 'start': text.index('沈'), 'end': len(text),
                        'quote': text[text.index('沈'):]}
            checks = []
            for check in contract['checks']:
                source_checks = [{'id': field['id'], 'status': 'pass',
                                  'reason': '目标促成举灯行动，烧伤和看清旧印构成后果', 'evidence': [evidence]}
                                 for field in check.get('source_contract',{}).get('obligations',[])]
                if self.omit_obligation and source_checks:
                    source_checks.pop()
                checks.append({'id': check['id'], 'status': 'pass', 'reason': '行动具有原文要求的因果顺序',
                               'evidence': [evidence], 'source_checks': source_checks})
                if 'source_contract' not in check:checks[-1].pop('source_checks')
                if check.get('layer_contract') and check['id'].startswith('work:'):
                    checks[-1]['layer_check']={'status':'pass','reason':'[FAKE] 对照本场实际转译的调查行动与后果',
                                               'evidence':[evidence]}
            from nw.llm.base import GenResult
            return GenResult(json.dumps({'recommendation': 'pass', 'notes': '核对原合同', 'core_changes': [],
                                          'material_checks': checks}, ensure_ascii=False), 'complete', {}, 'fake', {})
        if '{"operations"' in prompt:
            self.calls.append(messages)
            from nw.llm.base import GenResult
            return GenResult('{"operations":[]}', 'complete', {}, 'fake', {})
        if '只输出正文' in prompt:
            self.calls.append(messages)
            assert any(item['source'].startswith('material:') for item in data['items'])
            from nw.llm.base import GenResult
            return GenResult('[FAKE] 沈砚要查清封条来历，便举灯检查。他烧伤了手背，却看清了旧印。',
                             'complete', {}, 'fake', {})
        return super().generate(messages, **params)


def test_all_candidate_fields_have_a_full_contract_and_context_cannot_be_adopted(tmp_path, monkeypatch):
    root, result, summary = compiled_source(tmp_path, monkeypatch)
    assert summary['candidate_positions'] >= 5
    assert summary['source_contracts'] == 1 and summary['contracts'] == {'design_ready': 1}
    assert len(result['adjudication']['contract']['obligations']) == 5
    from nw.materials.unit_catalog import list_units
    fields = list_units(tmp_path, source_id=None, fragment_id=root['fragment_id'], key=None,
                        kind='condition', limit=20, offset=0)
    child = route(tmp_path, fields['units'][0]['unit_id'])
    assert child['adjudication']['state'] == 'context'
    assert child['adjudication']['owner_id'] == root['fragment_id']
    assert child['interpretation'] != 'adjudicated'


def test_failed_rebuild_preserves_the_previous_complete_ledger(tmp_path, monkeypatch):
    root, _, _ = compiled_source(tmp_path, monkeypatch)
    ledger = tmp_path / 'materials' / 'adjudication.db'
    original = ledger.read_bytes()
    with sqlite3.connect(tmp_path / 'materials' / 'catalog.db') as db:
        db.execute('UPDATE fragments SET payload=? WHERE id=?', (b'corrupted', root['fragment_id']))
    with pytest.raises(ValueError, match='hash mismatch'):
        build_adjudications(tmp_path)
    assert ledger.read_bytes() == original
    assert not list(ledger.parent.glob('adjudication-*.tmp'))


def test_catalog_growth_stales_the_adjudication_instead_of_inheriting_readiness(tmp_path, monkeypatch):
    root, _, _ = compiled_source(tmp_path, monkeypatch)
    manifest = _manifest(tmp_path / 'extra', tmp_path, [('new.txt', 'support', b'new source')])
    build_catalog(tmp_path, tmp_path / 'extra', manifest)
    index_units(tmp_path, None)
    current = route(tmp_path, root['fragment_id'])
    assert current['adjudication']['state'] == 'stale'
    assert current['interpretation'] != 'adjudicated'


def test_manual_read_without_qualification_does_not_become_a_ready_contract(tmp_path, monkeypatch):
    from nw.materials.reviews import Review, _REVIEWS
    root, result, _ = compiled_source(tmp_path, monkeypatch)
    pin = result['source']
    monkeypatch.setitem(_REVIEWS, root['fragment_id'], Review(
        pin['file_sha256'], pin['sha256'], 'character', '已核读，仍缺少原文依据',
        '保留待补状态', '完整原义与证据', can_offer_for_design=False))
    summary = build_adjudications(tmp_path)
    assert summary['manual_reviewed_positions'] == 1
    assert summary['contracts'] == {'blocked': 1}
    current = route(tmp_path, root['fragment_id'])
    assert current['interpretation'] != 'reviewed'
    assert current['adjudication']['state'] == 'blocked'
    with pytest.raises(ValueError, match='MATERIAL_UNQUALIFIED'):
        resolve_materials(tmp_path, [{**{key: pin[key] for key in ('id','file_sha256','sha256')},
                                     'disposition':'required', 'reason':'尝试采用未通过的核读条目'}])


def test_hybrid_ids_conditions_and_originals_work_without_upgrade_authority(tmp_path):
    from nw.materials.unit_catalog import list_units

    definitions = [
        {'type_id': ident, 'canonical_name': name, 'type_kind': 'GENRE', 'definition': meaning,
         'status': 'active', 'confidence': .8, 'scope': '主类型'}
        for ident, name, meaning in [('GENRE_A', '规则谜团', '由规则限制和证据发现推动谜团'),
                                     ('GENRE_B', '关系成长', '通过关系选择及代价展现人物成长')]
    ]
    hybrid = {'hybrid_id': 'HYBRID_A_B', 'type_kind': 'HYBRID_GENRE', 'canonical_name': '谜团与关系',
              'definition': '在关系选择中承担代价并发现规则证据', 'component_type_ids': ['GENRE_A','GENRE_B'],
              'status': 'active', 'confidence': .8, 'required_context': ['MUST_VERIFY_CONTEXT'],
              'exclusions': ['UNSUPPORTED_GOAL'], 'scope': '混合类型',
              '运行层升级': {'model_input_eligible': True, 'definition': 'UPGRADE_MUST_NOT_LEAK'}}
    combination = {'combination_id': 'COMBO_A_B', 'primary_type_id': 'GENRE_A',
                   'component_type_ids': ['GENRE_A','GENRE_B'], 'status': 'active',
                   'description': '让规则谜团中的证据改变关系选择', 'not_guaranteed': ['不能保证角色获益']}
    data = ('SOURCE: 主类型.json\n=====\n' + json.dumps(definitions, ensure_ascii=False) +
            '\nSOURCE: 混合类型.json\n=====\n' + json.dumps([hybrid], ensure_ascii=False) +
            '\nSOURCE: 类型组合总表.json\n=====\n' + json.dumps([combination], ensure_ascii=False)).encode()
    manifest = _manifest(tmp_path / 'source', tmp_path, [('types.txt','types',data)])
    build_catalog(tmp_path, tmp_path / 'source', manifest)
    index_units(tmp_path, None)
    records = list_units(tmp_path, source_id=None, fragment_id=None, key=None, kind='record', limit=100, offset=0)['units']
    target = next(row for row in records if row['key'] == 'HYBRID_A_B')
    with sqlite3.connect(tmp_path / 'materials' / 'catalog.db') as db:
        db.execute('UPDATE material_units SET key=? WHERE id=?', ('混合类型.json',target['unit_id']))
    build_adjudications(tmp_path)
    current = route(tmp_path, target['unit_id'])
    from nw.materials.adjudication import inspect_adjudications
    found = inspect_adjudications(tmp_path, key='HYBRID_A_B', roots_only=True)
    assert target['unit_id'] in {row['id'] for row in found['positions']}
    source = current['source']
    pin = {key: source[key] for key in ('id','sha256','file_sha256')}
    resolved = resolve_materials(tmp_path, [{**pin, 'disposition':'required', 'reason':'选用混合类型'}])[0]
    assert resolved['original']['hybrid_id'] == 'HYBRID_A_B'
    assert 'UPGRADE_MUST_NOT_LEAK' not in json.dumps(resolved)
    assert {'required_context','exclusions','scope'} <= {
        item['label'] for item in resolved['review']['contract']['obligations']}
    combo = next(row for row in records if row['key'] == 'COMBO_A_B')
    routed = route(tmp_path, combo['unit_id'])
    descriptor = {key: routed['source'][key] for key in ('id','sha256','file_sha256')}
    adopted = resolve_materials(tmp_path, [{**descriptor, 'disposition':'required','reason':'选用组合'}])
    record = adopted[0]
    roots = sorted({root for group in record['review']['contract']['constituents'] for root in group['root_ids']})
    value = {'function':'组织谜团与关系', 'parameter':'规则证据改变关系',
             'observable':'人物依据证据作出关系选择', 'check':'选择产生明确代价',
             'constituents': roots, 'mechanism':'证据影响信任', 'trigger':'新证据出现',
             'choice':'依据证据选择', 'cost':'承担关系代价', 'failure':'证据不足时保留怀疑',
             'source_scope':{item['id']:{'disposition':'required','reason':'采用该原条目'}
                             for item in record['review']['contract']['obligations']}}
    validate_bindings({'material_bindings':{record['source']['id']:value}}, 'book', {}, {}, adopted)


@pytest.mark.parametrize('omit', [False, True])
def test_adjudicated_original_contract_reaches_normal_design_review_and_acceptance(tmp_path, monkeypatch, omit):
    _, source, _ = compiled_source(tmp_path, monkeypatch)
    pin = {key: source['source'][key] for key in ('id','file_sha256','sha256')}
    pin.update(disposition='required', reason='按原始行动动机合同设计本场')
    provider = AdjudicatedModel(omit_obligation=omit)
    with Store(tmp_path / 'demo', create=True, test_mode=True) as store:
        store.init_project('原合同执行')
        store.add_brief('沈砚查封条并承担行动后果')
        adopt_story(store, baseline(), {})
        job = start_job(store, JobRequest('design', budget=Budget(32, 60000, 3000), materials=[pin])).id
        assert resume_job(store, job, provider, config(store)).step == 'plan:book:confirm'
        assert resume_job(store, job, provider, config(store), choose).step == 'plan:chapter:confirm'
        designed = resume_job(store, job, provider, config(store), choose)
        assert designed.status == 'DONE', designed.reason
        scene = designed.outputs['application']['chapters'][0]['scenes'][0]['scene_id']
        write = start_job(store, JobRequest('write', scene_ids=[scene], budget=Budget(8, 60000, 3000, 0))).id
        result = resume_job(store, write, provider, config(store), author())
        if omit:
            assert result.status == 'BLOCKED' and 'every original source obligation' in result.reason
            assert not store.list('accepted')
        else:
            assert result.status == 'DONE', result.reason
            assert len(store.list('accepted')) == 1

