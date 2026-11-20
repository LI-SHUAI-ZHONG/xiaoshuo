"""Exercise the static relationship checkpoint and its derived rule through book design."""
from contextlib import closing
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3

import pytest

from fake_binding_reviews import install_review_fixtures
from fake_semantic_clauses import criteria_for
from nw.cards import decide_card, save_card
from nw.llm.base import GenResult
from nw.materials import phase_routes
from nw.materials.adjudication import build_adjudications
from nw.materials.catalog import build_catalog, list_catalog
from nw.materials.identity_catalog import audit_identities
from nw.materials.phase_flow import STAGE_MATERIALS
from nw.materials.phase_projection import verify_chain
from nw.materials.source_set import POLICY as SOURCE_SET_POLICY
from nw.materials.unit_catalog import index_units
from nw.materials.work_catalog import SourceDesk
from nw.novel_flow import JobRequest, resume_job, start_job
from nw.store import Store
from nw.story_state import adopt_story
from nw.task_models import Budget, content_sha256
from nw.tasks import read_input_manifest
from story_fixture import baseline
from test_material_catalog import _manifest
from test_material_workflow import choose
from test_novel_flow import Model, config


STATIC_KEY = '1.2_重要配角 / 5.1_亲缘 / 嵌套'
DYNAMIC_KEY = 'C00006'
RELATION = {'id': 'kinship', 'source': 'witness', 'target': 'relative', 'relation': '嵌套',
            'condition': '[FAKE] 只有双方确认同一家谱，证人才愿意为长辈出示旧契'}
BASIS_PATH = 'input:static_relations_basis:/relations/0/condition'
POLICY = 'network-static-followup-v1'


def _network_catalog(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, str]:
    edge = {'source': '1.2_重要配角', 'target': '5.1_亲缘', 'type': '嵌套', 'condition': '关系连接'}
    dynamic = {'id': DYNAMIC_KEY, **edge, 'condition': '关系连接；且当前故事明确采用该静态关系',
               'effect': '当起点成立时，终点作为起点的一部分参与当前状态。',
               'generated_from_static': True, 'valid_types': ['悬疑']}
    genre = {'type_id': 'GENRE_XUANYI', 'canonical_name': '悬疑', 'type_kind': 'GENRE', 'parent_id': None,
             'definition': '通过事实与证据推动调查', 'status': 'active'}
    entries = [
        ('library.txt', 'library', '### 1.2_重要配角\n【定义】有独立任务并对调查结果产生实质作用的配角。\n'
                                   '### 5.1_亲缘\n【定义】经过双方或可信凭据确认的亲属连接。\n'),
        ('types.txt', 'types', 'SOURCE: 主类型.json\n=====\n' + json.dumps([genre], ensure_ascii=False)),
        ('links.txt', 'type_links', 'SOURCE: 类型连接.json\n=====\n{"definition":"查验家谱"}\n'),
        ('static.txt', 'static', json.dumps({'connections': [edge]}, ensure_ascii=False)),
        ('dynamic.txt', 'dynamic', json.dumps({'connections': [dynamic]}, ensure_ascii=False)),
        ('anchor.txt', 'anchors', '| A1.1 | 家谱调查 | 查看落款 | 找到对应姓氏时 | 基础 |\n'),
    ]
    originals = workspace / 'isolated_sources'
    manifest = _manifest(originals, workspace, [(name, family, text.encode('utf-8')) for name, family, text in entries])
    build_catalog(workspace, originals, manifest)
    aliases, migrations = workspace / 'aliases.json', workspace / 'migrations.json'
    aliases.write_text('{}', encoding='utf-8')
    migrations.write_text('{"migrations":[]}', encoding='utf-8')
    audit = audit_identities(workspace, aliases, migrations)
    (workspace / 'materials/F2_网络身份对账.json').write_text(json.dumps(audit), encoding='utf-8')
    index_units(workspace, None)
    selected = [{**{key: item[key] for key in ('path', 'family', 'file_sha256')}, 'id': item['source_id']}
                for item in list_catalog(workspace, None, None)['sources']]
    version = {'policy': SOURCE_SET_POLICY, 'version_name': '[FAKE] 隔离六源静网检查点', 'sources': selected}
    version['sha256'] = content_sha256(version)
    (workspace / 'materials/active_source_set.json').write_text(json.dumps(version, ensure_ascii=False), encoding='utf-8')
    with closing(sqlite3.connect(workspace / 'materials/catalog.db')) as database, database:
        database.execute('CREATE TABLE source_set_selection (singleton INTEGER PRIMARY KEY, policy TEXT, sha256 TEXT)')
        database.execute('INSERT INTO source_set_selection VALUES (1,?,?)', (SOURCE_SET_POLICY, version['sha256']))
    for family, variable in [('static', '_STATIC_NETWORK_SHA256'), ('dynamic', '_DYNAMIC_NETWORK_SHA256')]:
        pin = next(item['file_sha256'] for item in selected if item['family'] == family)
        monkeypatch.setattr(phase_routes, variable, pin)
    for stage in phase_routes.phase_order('book'):
        monkeypatch.setitem(STAGE_MATERIALS, stage, '')
    monkeypatch.setitem(STAGE_MATERIALS, 'static_relations', f'### {STATIC_KEY}\n【本步用法】\n'
                        '从原有真实人物卡核对重要配角及其亲缘对象。\n'
                        f'### {DYNAMIC_KEY}\n【本步用法】\n已确认亲缘时考察持契证人作证所受的具体约束。\n')
    build_adjudications(workspace)
    install_review_fixtures(workspace)
    desk = SourceDesk(workspace)
    [static] = [row['id'] for row in desk.rows if row['key'] == STATIC_KEY and row['state'] == 'design_ready']
    [dynamic_rule] = [row['id'] for row in desk.rows if row['key'] == DYNAMIC_KEY and row['state'] == 'design_ready']
    assert desk.dynamic_rules()[dynamic_rule]['static_id'] == static
    return static, dynamic_rule


def _add_project(store: Store) -> None:
    store.init_project('家谱与证人')
    store.add_brief('重要配角出示旧契作证。核对家谱、家人关系和取证必须满足的条件。')
    approvals = []
    for key, name, role, background in (
        ('witness', '顾闻', '重要配角兼证人', '保存两份盖章家谱和一份未公开旧契'),
        ('relative', '顾琴', '家谱上的长辈', '守着家谱并能辨别其中歪掉的朱印'),
    ):
        ref = save_card(store, {'card_id': key, 'kind': 'character', 'origin': 'author',
            'body': {'name': name, 'role': role, 'want': '凭有据的家谱厘清旧契归属',
                     'background': background, 'visibility': 'public'}}, None)
        decision = decide_card(store, ref, 'approved', '核对实际亲缘两端')
        approvals.append({**asdict(ref), 'decision_id': decision.id})
    adopt_story(store, baseline(card_refs=approvals), {})


class SameStageModel(Model):
    def __init__(self, static: str, dynamic: str, bind: bool, *, fail_once: bool = False) -> None:
        super().__init__()
        self.static, self.dynamic, self.bind = static, dynamic, bind
        self.fail_once = fail_once
        self.first_rounds: list[dict] = []
        self.followups: list[dict] = []

    def generate(self, messages: list[dict], **params) -> GenResult:
        payload = json.loads(messages[-1]['content'])
        stage = payload.get('stage')
        if stage == 'static_relations' and 'static_relations_basis' in payload:
            self.calls.append(messages)
            self.followups.append(payload)
            if self.fail_once and len(self.followups) == 1:
                return GenResult('invalid fixture JSON', 'complete', {}, 'test', {'isolated_test': True})
            return self._derived_requirement(payload)

        result = super().generate(messages, **params)
        if '[MATERIAL_STEP]' not in messages[0]['content']:
            return result
        body = json.loads(result.text)
        products = body['products']
        if stage == 'type_selection':
            products['selection'][0].update(id='GENRE_XUANYI', label='悬疑')
            products['concepts'][0]['type_refs'] = ['GENRE_XUANYI']
        if stage == 'static_relations':
            self.first_rounds.append(payload)
            assert {item['source']['id'] for item in payload['sources']} == {self.static}
            if self.bind:
                products.update(relations=[RELATION], _excluded=[], _uses=[
                    {'source_id': self.static, 'operation': '[FAKE] 核实双方真实身份，并落实亲缘成立的调查条件',
                     'output_refs': ['relation:kinship']},
                ], requirements=[{'id': 'kinship-source', 'source_id': self.static,
                    'target_stage': 'plot_design', 'constraint': '[FAKE] 保留确认双方身份的家谱记录',
                    'project_refs': ['member:witness', 'member:relative']}])
                products['_criteria'] = criteria_for(payload, products)
                for clause in products['_criteria'][0]['clauses']:
                    if clause['applicability'] == 'applies':
                        clause.update(input_refs=['approved:witness:/body/background', 'approved:relative:/body/background'],
                                      output_refs=['/relations/0/condition'])
        if stage == 'plot_design':
            requirements = payload['method_requirements']
            assert [item['id'] for item in requirements] == (['kinship-source', 'kinship-testimony'] if self.bind else [])
            if self.bind:
                assert all(handoff['source_id'] == self.dynamic for handoff in payload['semantic_requirements'])
                assert payload['semantic_requirements']
                products['directions'][0]['choice'] = '[FAKE] 先核家谱朱印和旧契落款，再询问配角愿不愿作证'
                products['_requirements'] = [{
                    'id': item['id'], 'operation': '[FAKE] 把核实亲缘的条件落实到调查选择',
                    'output_refs': ['direction:0'],
                } for item in requirements]
                products['_receipts'] = [{
                    'id': item['id'], 'operation': '[FAKE] 剧情在亲缘条件成立后才提出旧契作证',
                    'output_refs': ['/directions/0/choice'],
                } for item in payload['semantic_requirements']]
        result.text = json.dumps(body, ensure_ascii=False)
        return result

    def _derived_requirement(self, payload: dict) -> GenResult:
        assert self.bind
        assert {item['source']['id'] for item in payload['sources']} == {self.dynamic}
        basis = payload['static_relations_basis']
        assert basis['relations'] == [RELATION]
        assert basis['requirement_offset'] == 1
        assert payload['dynamic_relation_inputs'] == {self.dynamic: ['input:static_relations_basis:/relations/0']}
        output_path = f"/requirements/{basis['requirement_offset']}/constraint"
        products = {'requirements': [{'id': 'kinship-testimony', 'source_id': self.dynamic,
                    'target_stage': 'plot_design', 'constraint': '[FAKE] 先比对家谱朱印和落款，确认亲缘后才让证人出示旧契',
                    'project_refs': ['member:witness', 'member:relative']}],
                    '_uses': [{'source_id': self.dynamic, 'operation': '[FAKE] 把已经记录的亲缘成立条件用于实际取证次序',
                               'output_refs': ['requirement:kinship-testimony']}], '_excluded': []}
        products['_criteria'] = criteria_for(payload, products)
        for clause in products['_criteria'][0]['clauses']:
            if clause['applicability'] == 'applies':
                clause.update(input_refs=[BASIS_PATH], output_refs=[output_path], consumer='plot_design',
                              observable='[FAKE] 两枚家谱朱印核对后才出示保管的旧契',
                              check='[FAKE] 两个可见证据被核对后，证人才选择回应调查')
        return GenResult(json.dumps({'stage': 'static_relations', 'products': products}, ensure_ascii=False),
                         'complete', {}, 'test', {'isolated_test': True})


def _stage_tasks(store: Store) -> list[tuple[dict, dict]]:
    rows = store.connection.execute(
        "SELECT id, root_id, manifest_id, validation, attempt FROM task_calls WHERE kind='material_work' ORDER BY rowid"
    )
    tasks = []
    for row in rows:
        _, data = read_input_manifest(store, row['manifest_id'])
        payload = data['study_input']
        if payload.get('stage') == 'static_relations':
            tasks.append((dict(row), payload))
    return tasks


@pytest.mark.parametrize(('bind', 'fail_once'), [(False, False), (True, False), (True, True)],
                         ids=['without-relationship', 'relationship-and-handoff', 'reopened-retry'])
def test_same_stage_dynamic_rule_uses_only_the_frozen_first_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                               bind: bool, fail_once: bool) -> None:
    static, dynamic = _network_catalog(tmp_path, monkeypatch)
    provider = SameStageModel(static, dynamic, bind, fail_once=fail_once)
    path = tmp_path / 'project'
    with Store(path, create=True, test_mode=True) as store:
        _add_project(store)
        job = start_job(store, JobRequest('design', design_scope='book', budget=Budget(22, 90000, 4500))).id
        result = resume_job(store, job, provider, config(store), choose)
        if fail_once:
            assert result.status == 'BLOCKED', result.reason
            first_tasks = _stage_tasks(store)
            assert len(first_tasks) == 2
            assert first_tasks[0][0]['validation'] == 'VALID'
            assert first_tasks[1][0]['validation'] != 'VALID'

    with Store(path, test_mode=True) as store:
        if fail_once:
            result = resume_job(store, job, provider, config(store), choose, retry_failed=True)
        assert result.status == 'DONE', result.reason
        proposal = result.outputs['proposal_id']
        call = store.connection.execute('SELECT manifest_id FROM task_calls WHERE id=?', (proposal,)).fetchone()
        _, frozen = read_input_manifest(store, call['manifest_id'])
        session = frozen['material_work']
        assert session['context']['same_stage_network_policy'] == POLICY
        records = {row['stage']: row for row in session['stages']}
        stage = records['static_relations']
        tasks = _stage_tasks(store)
        assert len(provider.first_rounds) == 1
        assert len(provider.followups) == (2 if fail_once else int(bind))
        assert len(tasks) == 1 + len(provider.followups)
        if bind:
            basis = stage['static_relations_basis']
            followup = stage['static_relations_followup']
            assert basis['task_id'] == tasks[0][0]['id']
            assert basis['products']['relations'] == stage['products']['relations'] == [RELATION]
            assert followup['task_id'] == tasks[-1][0]['id']
            assert followup['manifest_id'] == tasks[-1][0]['manifest_id']
            assert followup['source_ids'] == [dynamic]
            assert followup['sha256'] == content_sha256(followup['products'])
            assert dynamic in stage['source_ids']
            assert [item['id'] for item in stage['products']['requirements']] == ['kinship-source', 'kinship-testimony']
            assert records['plot_design']['products']['_receipts']
        else:
            assert not stage.get('static_relations_followup')
            assert dynamic not in stage['source_ids']
            assert stage['products']['relations'] == stage['products']['requirements'] == []
        if fail_once:
            assert tasks[:2] == first_tasks
            assert tasks[-1][0]['root_id'] == first_tasks[1][0]['root_id']
            assert tasks[-1][0]['attempt'] == 2
            assert tasks[-1][1] == first_tasks[1][1]
        verify_chain(session)
