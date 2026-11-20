"""Exercise the type-adaptation dynamic prerequisite in an isolated book plan."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from typing import Any

import pytest

from fake_binding_reviews import install_review_fixtures
from fake_semantic_clauses import criteria_for
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


STATIC_KEY = '114.1_类型必备元素 / 124.1_小说种类 / 嵌套'
DYNAMIC_KEY = 'C00077'
SELECTED_GENRE = ('GENRE_XUANYI', '悬疑')
OTHER_GENRE = ('GENRE_ERCIYUAN', '二次元')
POLICY = 'type-network-prerequisites-v1'
PROMISE = '读者先看到两份证词与旧印的矛盾，再用已经揭示的证据核对嫌疑人。'
SELECTION_PATH = 'input:type_selection:/selection/0/basis'
PROMISE_PATH = 'input:type_selection:/adaptation_inputs/reader_promise/quote'
OUTPUT_PATH = '/adaptations/0/parameters/evidence_sequence'


def _catalog(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, str]:
    edge = {'source': '114.1_类型必备元素', 'target': '124.1_小说种类', 'type': '嵌套', 'condition': '必备元素=种类'}
    dynamic = {'id': DYNAMIC_KEY, **edge, 'condition': '必备元素=种类；且当前故事明确采用该静态关系',
               'effect': '当起点成立时，终点作为起点的一部分参与当前状态。',
               'generated_from_static': True, 'valid_types': ['悬疑']}
    genres = [{'type_id': ident, 'canonical_name': label, 'type_kind': 'GENRE', 'parent_id': None,
               'definition': f'{label}项目按作者明确的阅读目标确定基础类型', 'status': 'active'}
              for ident, label in (SELECTED_GENRE, OTHER_GENRE)]
    entries = [
        ('library.txt', 'library', '### 114.1_类型必备元素\n【定义】按作者确认的阅读需求选用的核心要素。\n'
                                   '### 124.1_小说种类\n【定义】作者选择的项目类型类别。\n'),
        ('types.txt', 'types', 'SOURCE: 主类型.json\n=====\n' + json.dumps(genres, ensure_ascii=False)),
        ('links.txt', 'type_links', 'SOURCE: 类型连接.json\n=====\n{"definition":"核验读者能够查到的事实"}\n'),
        ('静态网络.txt', 'static', json.dumps({'connections': [edge]}, ensure_ascii=False)),
        ('动态网络.txt', 'dynamic', json.dumps({'connections': [dynamic]}, ensure_ascii=False)),
        ('anchor.txt', 'anchors', '| A1.1 | 印章调查 | 查看落款 | 找到对应印章时 | 基础 |\n'),
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
    selected = [{**{key: row[key] for key in ('path', 'family', 'file_sha256')}, 'id': row['source_id']}
                for row in list_catalog(workspace, None, None)['sources']]
    version = {'policy': SOURCE_SET_POLICY, 'version_name': '[FAKE] 隔离六源类型适配', 'sources': selected}
    version['sha256'] = content_sha256(version)
    (workspace / 'materials/active_source_set.json').write_text(json.dumps(version, ensure_ascii=False), encoding='utf-8')
    with closing(sqlite3.connect(workspace / 'materials/catalog.db')) as database, database:
        database.execute('CREATE TABLE source_set_selection (singleton INTEGER PRIMARY KEY, policy TEXT, sha256 TEXT)')
        database.execute('INSERT INTO source_set_selection VALUES (1,?,?)', (SOURCE_SET_POLICY, version['sha256']))
    for family, variable in [('static', '_STATIC_NETWORK_SHA256'), ('dynamic', '_DYNAMIC_NETWORK_SHA256')]:
        pin = next(row['file_sha256'] for row in selected if row['family'] == family)
        monkeypatch.setattr(phase_routes, variable, pin)
    for stage in phase_routes.phase_order('book'):
        monkeypatch.setitem(STAGE_MATERIALS, stage, '')
    monkeypatch.setitem(STAGE_MATERIALS, 'type_adaptation', f'### {STATIC_KEY}\n【本步用法】\n'
                        '以已选类型和作者确认的读者承诺确定核心要素。\n'
                        f'### {DYNAMIC_KEY}\n【本步用法】\n确定核心要素及其在实际作品中的作用和适用范围。\n')
    build_adjudications(workspace)
    install_review_fixtures(workspace)
    desk = SourceDesk(workspace)
    [static] = [row['id'] for row in desk.rows if row['key'] == STATIC_KEY and row['state'] == 'design_ready']
    [derived] = [row['id'] for row in desk.rows if row['key'] == DYNAMIC_KEY and row['state'] == 'design_ready']
    assert desk.dynamic_rules()[derived]['static_id'] == static
    return static, derived


class TypeNetworkModel(Model):
    def __init__(self, static: str, derived: str, *, promise: bool, genre: tuple[str, str]) -> None:
        super().__init__()
        self.static = static
        self.derived = derived
        self.promise = promise
        self.genre = genre
        self.eligible = promise and genre == SELECTED_GENRE

    def generate(self, messages: list[dict], **params: Any) -> GenResult:
        result = super().generate(messages, **params)
        if '[MATERIAL_STEP]' not in messages[0]['content']:
            return result
        payload = json.loads(messages[-1]['content'])
        body = json.loads(result.text)
        products = body['products']
        if payload['stage'] == 'type_selection':
            ident, label = self.genre
            products['selection'][0].update(id=ident, label=label, basis='[FAKE] 依据作者明确选定的项目类型')
            products['concepts'][0]['type_refs'] = [ident]
            if self.promise:
                products['adaptation_inputs'] = {'reader_promise': {'ref': 'brief:/constraints', 'quote': PROMISE}}
        elif payload['stage'] == 'type_adaptation':
            offered = {item['source']['id'] for item in payload['sources']}
            assert (self.derived in offered) == self.eligible
            prerequisites = payload.get('type_network_prerequisites', {})
            assert (self.derived in prerequisites) == self.eligible
            if not self.eligible:
                assert self.derived not in payload['readable_source_ids']
                if self.genre == SELECTED_GENRE:
                    [waiting] = [item for item in payload['network_waiting']['examples'] if item['key'] == DYNAMIC_KEY]
                    assert waiting['static_key'] == STATIC_KEY and '读者承诺' in waiting['reason']
                if not payload['responses']:
                    result.text = json.dumps({'stage': 'type_adaptation',
                                              'requests': [{'action': 'search', 'query': DYNAMIC_KEY}]})
                    return result
                assert all(row['id'] != self.derived for response in payload['responses'] for row in response['items'])
            products['_uses'] = []
            products['_excluded'] = [{'source_id': ident, 'reason': '[FAKE] 本任务无需独立采用此辅助原义'}
                                     for ident in sorted(offered - ({self.derived} if self.eligible else set()))]
            if self.eligible:
                evidence = prerequisites[self.derived]
                assert evidence['type_ids'] == [self.genre[0]]
                assert evidence['inputs']['reader_promise'] == PROMISE_PATH
                assert evidence['output'] == 'adaptations'
                assert evidence['static_source']['static_id'] == self.static
                assert evidence['static_source']['source']['key'] == STATIC_KEY
                assert payload['inputs']['type_selection']['products']['adaptation_inputs']['reader_promise']['quote'] == PROMISE
                products['adaptations'][0]['parameters']['evidence_sequence'] = (
                    '[FAKE] 先显露两份证词对旧印年代的矛盾，再按已展示的证据逐段排除嫌疑人')
                products['_uses'].append({'source_id': self.derived,
                    'operation': '[FAKE] 把作者确立的类型必备元素落实为证词和旧印的揭示顺序',
                    'output_refs': ['adaptation:' + products['adaptations'][0]['id']]})
            products['_criteria'] = criteria_for(payload, products)
            for criterion in products['_criteria']:
                for clause in criterion['clauses']:
                    if clause['applicability'] == 'applies':
                        clause.update(input_refs=[SELECTION_PATH, PROMISE_PATH], output_refs=[OUTPUT_PATH],
                                      consumer='plot_design',
                                      operation='[FAKE] 以悬疑的实际阅读承诺设计证词及旧印揭示顺序',
                                      observable='[FAKE] 读者先见到旧印引起的证词矛盾，再逐段排除嫌疑人',
                                      check='[FAKE] 核对剧情方案是否仅用先前展示过的证据排除嫌疑')
        elif payload['stage'] == 'plot_design':
            handoffs = [row for row in payload['semantic_requirements'] if row['source_id'] == self.derived]
            assert bool(handoffs) == self.eligible
            if self.eligible:
                products['directions'][0]['choice'] = '[FAKE] 用已向读者披露的旧印和证词相互校验，而后排出调查顺序'
                products['_receipts'] = [{'id': row['id'], 'operation': '[FAKE] 在剧情选择承接证词与旧印的实际揭示顺序',
                                          'output_refs': ['/directions/0/choice']}
                                         for row in payload['semantic_requirements']]
        result.text = json.dumps(body, ensure_ascii=False)
        return result


@pytest.mark.parametrize(('promise', 'genre'), [(True, SELECTED_GENRE), (False, SELECTED_GENRE), (True, OTHER_GENRE)],
                         ids=['selected-type-and-promise', 'missing-promise', 'wrong-type'])
def test_type_adaptation_derives_only_from_actual_type_and_author_promise(tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch, promise: bool, genre: tuple[str, str]) -> None:
    static, derived = _catalog(tmp_path, monkeypatch)
    provider = TypeNetworkModel(static, derived, promise=promise, genre=genre)
    path = tmp_path / 'project'
    with Store(path, create=True, test_mode=True) as store:
        store.init_project('旧印与证词')
        store.add_brief(f'作者已选{genre[1]}，本作以旧印和证词展开。', PROMISE if promise else '')
        adopt_story(store, baseline(), {})
        job = start_job(store, JobRequest('design', design_scope='book', budget=Budget(18, 90000, 4500))).id
        result = resume_job(store, job, provider, config(store), choose)
        assert result.status == 'DONE', result.reason
        proposal = result.outputs['proposal_id']

    with Store(path, test_mode=True) as store:
        call = store.connection.execute('SELECT manifest_id FROM task_calls WHERE id=?', (proposal,)).fetchone()
        _, frozen = read_input_manifest(store, call['manifest_id'])
        session = frozen['material_work']
        assert session['context']['type_network_policy'] == POLICY
        stages = {record['stage']: record for record in session['stages']}
        adaptation = stages['type_adaptation']
        assert (derived in adaptation['source_ids']) == provider.eligible
        if provider.eligible:
            assert session['context']['type_network_bases'][derived]['static_id'] == static
            [criterion] = [row for row in adaptation['products']['_criteria'] if row['source_id'] == derived]
            adopted = [clause for clause in criterion['clauses'] if clause['applicability'] == 'applies']
            assert adopted and all(clause['input_refs'] == [SELECTION_PATH, PROMISE_PATH]
                                   and clause['output_refs'] == [OUTPUT_PATH] for clause in adopted)
            assert stages['plot_design']['products']['_receipts']
        verify_chain(session)
