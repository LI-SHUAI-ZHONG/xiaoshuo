"""Exercise per-field network layer evidence through the actual novel workflow."""
from hashlib import sha256
import json
from pathlib import Path
import sqlite3

import pytest

from fake_binding_reviews import install_review_fixtures
from nw.context.story import build_story_context, scene_scope
from nw.llm.base import GenResult
from nw.materials import library_adjudication
from nw.materials.adjudication import build_adjudications
from nw.materials.catalog import build_catalog, list_catalog
from nw.materials.phase_flow import STAGE_MATERIALS
from nw.materials.source_set import POLICY as SOURCE_SET_POLICY
from nw.materials.unit_catalog import index_units
from nw.materials.work_catalog import SourceDesk
from nw.novel_flow import JobRequest, resume_job, start_job
from nw.store import Store
from nw.story_state import adopt_story
from nw.task_models import Budget, content_sha256
from story_fixture import baseline
from test_material_catalog import _manifest
from test_material_workflow import choose
from test_novel_flow import Model, author, config


ANCHOR_KEY = 'A1.99'
ORIGINAL_EFFECT = '木片托起纸角后旧印在灯下显出半枚字形'
TRIGGER = 'input:action_design:/candidates/0/steps/0/response'
PROJECT_EFFECT = '[FAKE] 灯光下旧印显出半枚字形'
PROJECT_ACTION = '[FAKE] 将灯移近抬起的封条纸角'
PROJECT_TRIGGER = '[FAKE] 木片压低绕过铜丝后才托起纸角'
RESULT_VALUES = {'/beats/0/observable': PROJECT_EFFECT, '/beats/0/action': PROJECT_ACTION}
LAYER_POLICY = 'network-layer-fields-v1'


def _catalog(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    layer = {'canonical_source_id': ANCHOR_KEY, 'runtime_calling_layer': [{
        'source_id': ANCHOR_KEY, 'binding_id': 'anchor-check',
        'semantic_interpretation': {'source_semantic_anchor': ORIGINAL_EFFECT,
                                    'operational_meaning': ORIGINAL_EFFECT},
    }]}
    anchor = (f'| {ANCHOR_KEY} | 封条旧印 | {ORIGINAL_EFFECT} | 木片绕过铜丝且灯光照向封条时 | 物质 | '
              '<details><summary>运行层升级</summary>' + json.dumps(layer, ensure_ascii=False) + '</details>\n')
    files = [
        ('library.txt', 'library', '### 1.92_现场封条\n【定义】查看封条后保留印痕。\n'),
        ('types.txt', 'types', 'SOURCE: 类型.json\n=====\n{"definition":"查验现场"}\n'),
        ('links.txt', 'type_links', 'SOURCE: 类型连接.json\n=====\n{"definition":"查验印痕"}\n'),
        ('static.txt', 'static', '{"connections":[]}'),
        ('dynamic.txt', 'dynamic', '{"connections":[]}'),
        ('锚点网络.txt', 'anchors', anchor),
    ]
    original = workspace / 'isolated_sources'
    manifest = _manifest(original, workspace, [(name, family, text.encode('utf-8')) for name, family, text in files])
    monkeypatch.setitem(library_adjudication._PINNED, 'anchors', sha256(anchor.encode('utf-8')).hexdigest())
    build_catalog(workspace, original, manifest)
    index_units(workspace, None)
    selected = [{'id': row['source_id'], 'path': row['path'], 'family': row['family'],
                 'file_sha256': row['file_sha256']} for row in list_catalog(workspace, None, None)['sources']]
    selection = {'policy': SOURCE_SET_POLICY, 'version_name': '[FAKE] 隔离六源运行层', 'sources': selected}
    selection['sha256'] = content_sha256(selection)
    (workspace / 'materials/active_source_set.json').write_text(json.dumps(selection, ensure_ascii=False), encoding='utf-8')
    with sqlite3.connect(workspace / 'materials/catalog.db') as db:
        db.execute('CREATE TABLE source_set_selection (singleton INTEGER PRIMARY KEY, policy TEXT, sha256 TEXT)')
        db.execute('INSERT INTO source_set_selection VALUES (1,?,?)', (SOURCE_SET_POLICY, selection['sha256']))
    build_adjudications(workspace)
    install_review_fixtures(workspace)
    # The pinned production TDF_001 type file is outside this isolated anchor fixture.
    monkeypatch.setattr('nw.materials.dynamic_screening.load_dynamic_screening', lambda _: None)
    monkeypatch.setitem(STAGE_MATERIALS, 'anchor_design', f'### {ANCHOR_KEY}\n【本步用法】\n'
                        '封条旧印调查时，按实际动作与观察时点设计看到旧印的锚点。\n')
    desk = SourceDesk(workspace)
    [row] = [item for item in desk.rows if item['key'] == ANCHOR_KEY and item['state'] == 'design_ready']
    source = desk.read(row['id'])
    [pair] = desk.semantic_contract(source)['application_guidance']
    assert [field['value'] for field in pair['aligned_fields']] == [ORIGINAL_EFFECT]
    return row


class AnchorLayerModel(Model):
    def __init__(self) -> None:
        super().__init__()
        self.field_bindings: list[dict] = []
        self.checked: list[list[dict]] = []

    def generate(self, messages: list[dict], **params) -> GenResult:
        prompt = messages[0]['content']
        data = json.loads(messages[-1]['content'])
        if '只输出正文' in prompt or '修订本场' in prompt:
            self.calls.append(messages)
            suffix = '他记下残缺的笔画。' if self.checked else ''
            return GenResult('[FAKE] 沈砚把木片压低绕过铜丝，托起纸角。灯下露出了半枚旧印。' + suffix,
                             'complete', {}, 'test', {'isolated_test': True})
        output = super().generate(messages, **params)
        if data.get('stage') == 'anchor_design':
            assert data['scope'] == 'chapter'
            [offered] = data['sources']
            assert offered['source']['key'] == ANCHOR_KEY
            [source_contract] = data['source_contracts']
            assert source_contract['network_layer_fields'] is True
            assert 'trigger_ref' in messages[0]['content']
            raw = json.loads(output.text)
            products = raw['products']
            [beat] = products['beats']
            beat.update(observable=PROJECT_EFFECT, action=PROJECT_ACTION, trigger_basis=PROJECT_TRIGGER, timing='after')
            [criterion] = products['_criteria']
            upstream = data['inputs']['action_design']['products']['candidates'][0]
            self.trigger_value = upstream['steps'][0]['response']
            self.action_ref = upstream['id']
            for clause in criterion['clauses']:
                if clause['applicability'] == 'applies':
                    # The first clause uses two distinct fields of the same beat.
                    results = list(RESULT_VALUES) if not self.field_bindings else ['/beats/0/observable']
                    clause.update(input_refs=[TRIGGER], output_refs=results,
                                  operation='[FAKE] 用绕过铜丝的既定动作引出纸角抬起的可见变化',
                                  observable=PROJECT_EFFECT, check='[FAKE] 核对移开纸角后旧印才在本场视角里显露')
                    self.field_bindings.extend({'clause_id': clause['id'], 'trigger_ref': TRIGGER, 'result_ref': path}
                                               for path in results)
            assert len(self.field_bindings) >= 2
            criterion['layer_application'] = {'bindings': self.field_bindings}
            output.text = json.dumps(raw, ensure_ascii=False)
        if 'material_review' in data:
            assert 'result.path' in messages[0]['content']
            raw = json.loads(output.text)
            layer_checks = [row for row in data['material_review']['checks'] if row['id'].startswith('work:layer:')]
            assert {row['id'] for row in layer_checks} and len(layer_checks) == len(self.field_bindings)
            projected = []
            for row in layer_checks:
                layer = row['layer_contract']
                assert layer['policy'] == LAYER_POLICY
                application = layer['layer_application']
                assert application['trigger'] == {'path': TRIGGER, 'value': self.trigger_value}
                result = application['result']
                assert result['value'] == RESULT_VALUES[result['path']]
                projected.append((layer['original_clause']['id'], result['path']))
                assert row['action_ref'] == self.action_ref
                assert PROJECT_EFFECT in row['binding']['observable']
                assert '本场视角' in row['binding']['check']
            assert set(projected) == {(row['clause_id'], row['result_ref']) for row in self.field_bindings}
            if not self.checked:
                ident = layer_checks[0]['id']
                next(row for row in raw['material_checks'] if row['id'] == ident)['layer_check']['status'] = 'unverified'
            self.checked.append(layer_checks)
            output.text = json.dumps(raw, ensure_ascii=False)
        return output


def test_current_network_layer_fields_survive_reopen_review_revision_and_acceptance(tmp_path, monkeypatch) -> None:
    source = _catalog(tmp_path, monkeypatch)
    path = tmp_path / 'project'
    provider = AnchorLayerModel()
    with Store(path, create=True, test_mode=True) as store:
        store.init_project('检查封条旧印')
        store.add_brief('调查封条时借灯检查旧印，木片压低绕过铜丝')
        adopt_story(store, baseline(), {})
        job = start_job(store, JobRequest('design', budget=Budget(40, 90000, 4500))).id
        book = resume_job(store, job, provider, config(store))
        assert book.step == 'plan:book:confirm', book.reason
        chapter = resume_job(store, job, provider, config(store), choose)
        assert chapter.step == 'plan:chapter:confirm', chapter.reason
        design = resume_job(store, job, provider, config(store), choose)
        assert design.status == 'DONE', design.reason
        scene = design.outputs['application']['chapters'][0]['scenes'][0]['scene_id']

    with Store(path, test_mode=True) as store:
        from nw.materials.evidence import scene_materials

        session = scene_materials(store, scene)['work_session']
        assert session['context']['network_layer_policy'] == LAYER_POLICY
        anchor = next(row for row in session['stages'] if row['stage'] == 'anchor_design')
        [criterion] = anchor['products']['_criteria']
        assert criterion['source_id'] == source['id']
        assert criterion['layer_application'] == {'bindings': provider.field_bindings}
        context = build_story_context(store, scene, scene_scope(store, scene), 90000).package
        written_checks = {row['source'].removeprefix('material:'): json.loads(row['text'])
                          for row in context['items'] if row['source'].startswith('material:work:layer:')}
        assert len(written_checks) == len(provider.field_bindings)
        assert all(PROJECT_EFFECT in row['observable'] for row in written_checks.values())
        job = start_job(store, JobRequest('write', scene_ids=[scene], budget=Budget(16, 90000, 4500, 1))).id
        result = resume_job(store, job, provider, config(store))
        assert result.step == 'batch:confirm', result.reason
        assert not store.list('accepted')
        assert len(provider.checked) == len(store.drafts(scene)) == 2
        assert all({row['id'] for row in checks} == written_checks.keys() for checks in provider.checked)
        [writing] = [json.loads(messages[-1]['content']) for messages in provider.calls
                     if '只输出正文' in messages[0]['content']]
        assert written_checks == {row['source'].removeprefix('material:'): json.loads(row['text'])
                                  for row in writing['items']
                                  if row['source'].startswith('material:work:layer:')}
        [revision] = [json.loads(messages[-1]['content']) for messages in provider.calls
                      if '只输出完整修订正文' in messages[0]['content']]
        assert {'id': provider.checked[0][0]['id'], 'status': 'unverified'} in revision['review']['material_checks']

    with Store(path, test_mode=True) as store:
        accepted = resume_job(store, job, provider, config(store), author())
        assert accepted.status == 'DONE', accepted.reason
        [record] = store.list('accepted')
        assert store.get('draft', record.draft_id).text.endswith('他记下残缺的笔画。')
