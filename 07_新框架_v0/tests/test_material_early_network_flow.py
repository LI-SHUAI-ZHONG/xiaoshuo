"""Exercise early network prerequisites through the actual book design entry point."""
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


STATIC_KEY = '1.5_缺席者 / 32.7_未写明的历史 / 绑定'
DYNAMIC_KEY = 'C00014'
HISTORY = '[FAKE] 退任档案官的任期与旧卷改封记录相互对应'
PLOT_CONDITION = 'input:static_relations:/relations/0/condition'
EARLY_POLICY = 'network-early-prerequisites-v1'


def _catalog(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, str]:
    edge = {'source': '1.5_缺席者', 'target': '32.7_未写明的历史', 'type': '绑定',
            'condition': '关联历史'}
    dynamic = {'id': DYNAMIC_KEY, **edge, 'condition': '关联历史；且当前故事明确采用该静态关系',
               'effect': '当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。',
               'generated_from_static': True, 'valid_types': ['悬疑']}
    genre = {'type_id': 'GENRE_XUANYI', 'canonical_name': '悬疑', 'type_kind': 'GENRE', 'parent_id': None,
             'definition': '通过可观察的事实与证据推动人物调查', 'status': 'active'}
    entries = [
        ('library.txt', 'library', '### 1.5_缺席者\n【定义】需要通过其遗留物理解的离场人物。\n'
                                   '### 32.7_未写明的历史\n【定义】留有可观察痕迹的过去事件。\n'),
        ('types.txt', 'types', 'SOURCE: 主类型.json\n=====\n' + json.dumps([genre], ensure_ascii=False)),
        ('links.txt', 'type_links', 'SOURCE: 类型连接.json\n=====\n{"definition":"查验旧卷"}\n'),
        ('static.txt', 'static', json.dumps({'connections': [edge]}, ensure_ascii=False)),
        ('dynamic.txt', 'dynamic', json.dumps({'connections': [dynamic]}, ensure_ascii=False)),
        ('anchor.txt', 'anchors', '| A1.1 | 旧卷调查 | 查看封条 | 发现边角松动时 | 基础 |\n'),
    ]
    original = workspace / 'isolated_sources'
    manifest = _manifest(original, workspace, [(name, family, raw.encode('utf-8')) for name, family, raw in entries])
    build_catalog(workspace, original, manifest)
    aliases = workspace / 'aliases.json'
    migrations = workspace / 'migrations.json'
    aliases.write_text('{}', encoding='utf-8')
    migrations.write_text('{"migrations":[]}', encoding='utf-8')
    audit = audit_identities(workspace, aliases, migrations)
    (workspace / 'materials/F2_网络身份对账.json').write_text(json.dumps(audit), encoding='utf-8')
    index_units(workspace, None)
    selected = [{'id': row['source_id'], 'path': row['path'], 'family': row['family'], 'file_sha256': row['file_sha256']}
                for row in list_catalog(workspace, None, None)['sources']]
    version = {'policy': SOURCE_SET_POLICY, 'version_name': '[FAKE] 隔离六源剧情前置', 'sources': selected}
    version['sha256'] = content_sha256(version)
    (workspace / 'materials/active_source_set.json').write_text(json.dumps(version, ensure_ascii=False), encoding='utf-8')
    with sqlite3.connect(workspace / 'materials/catalog.db') as db:
        db.execute('CREATE TABLE source_set_selection (singleton INTEGER PRIMARY KEY, policy TEXT, sha256 TEXT)')
        db.execute('INSERT INTO source_set_selection VALUES (1,?,?)', (SOURCE_SET_POLICY, version['sha256']))
    for family, var in [('static', '_STATIC_NETWORK_SHA256'), ('dynamic', '_DYNAMIC_NETWORK_SHA256')]:
        pin = next(row['file_sha256'] for row in selected if row['family'] == family)
        monkeypatch.setattr(phase_routes, var, pin)
    for stage in phase_routes.phase_order('book'):
        if stage != 'plot_design':
            monkeypatch.setitem(STAGE_MATERIALS, stage, '')
    monkeypatch.setitem(STAGE_MATERIALS, 'plot_design', f'### {STATIC_KEY}\n【本步用法】\n'
                        '核对缺席的退任档案官与未写明的旧卷改封历史。\n'
                        f'### {DYNAMIC_KEY}\n【本步用法】\n根据已落实的关系设计旧卷调查与剧情选择。\n')
    build_adjudications(workspace)
    install_review_fixtures(workspace)
    desk = SourceDesk(workspace)
    [static] = [row['id'] for row in desk.rows if row['key'] == STATIC_KEY and row['state'] == 'design_ready']
    [derived] = [row['id'] for row in desk.rows if row['key'] == DYNAMIC_KEY and row['state'] == 'design_ready']
    assert desk.dynamic_rules()[derived]['static_id'] == static
    reviews_path = workspace / 'materials/workflow_binding_reviews.json'
    reviews = json.loads(reviews_path.read_text(encoding='utf-8'))
    # Leave this source eligible as an exact original instead of inventing a fixture review for the new stage.
    reviews['reviews'] = [row for row in reviews['reviews'] if row['source']['id'] != static]
    reviews_path.write_text(json.dumps(reviews, ensure_ascii=False), encoding='utf-8')
    return static, derived


class EarlyNetworkModel(Model):
    def __init__(self, static: str, dynamic: str, bind: bool) -> None:
        super().__init__()
        self.static, self.dynamic, self.bind = static, dynamic, bind

    def generate(self, messages: list[dict], **params) -> GenResult:
        result = super().generate(messages, **params)
        if '[MATERIAL_STEP]' not in messages[0]['content']:
            return result
        payload = json.loads(messages[-1]['content'])
        raw = json.loads(result.text)
        products = raw['products']
        stage = payload['stage']
        offered = {row['source']['id'] for row in payload['sources']}
        relation = {'id': 'archive-history', 'source': 'archivist', 'target': 'archive_history',
                    'relation': '绑定', 'condition': HISTORY}
        if stage == 'type_selection':
            products['selection'][0].update(id='GENRE_XUANYI', label='悬疑')
            products['concepts'][0]['type_refs'] = ['GENRE_XUANYI']
        elif stage == 'static_relations':
            assert self.static in payload['prepared_static_sources']
            assert offered == {self.static}
            if self.bind:
                products.update(relations=[relation], _excluded=[], _uses=[{
                    'source_id': self.static, 'operation': '[FAKE] 按两份项目设定落实失踪档案官与旧卷历史的关系',
                    'output_refs': ['relation:archive-history']}])
                products['_criteria'] = criteria_for(payload, products)
                for clause in products['_criteria'][0]['clauses']:
                    if clause['applicability'] == 'applies':
                        clause.update(input_refs=['approved:archivist:/body/background',
                                                  'approved:archive_history:/body/rule'],
                                      output_refs=['/relations/0/condition'])
        elif stage == 'plot_design':
            assert payload['inputs']['static_relations']['products']['relations'] == ([relation] if self.bind else [])
            assert (self.dynamic in offered) == self.bind
            expected = {self.dynamic: ['input:static_relations:/relations/0']} if self.bind else {}
            assert payload.get('dynamic_relation_inputs', {}) == expected
            if self.static in offered:
                products['_uses'] = [row for row in products['_uses'] if row['source_id'] != self.static]
                products['_excluded'].append({'source_id': self.static,
                    'reason': '[FAKE] 当前剧情仅承接静网已有设计，不新增历史关系'})
                products['_criteria'] = criteria_for(payload, products)
            if self.bind:
                products['directions'][0]['choice'] = '[FAKE] 按前任档案官的签印对照两代旧卷改封记录'
                for use in products['_uses']:
                    if use['source_id'] == self.dynamic:
                        use['output_refs'] = ['direction:0']
                for criterion in products['_criteria']:
                    if criterion['source_id'] != self.dynamic:
                        continue
                    for clause in criterion['clauses']:
                        if clause['applicability'] == 'applies':
                            clause.update(input_refs=[PLOT_CONDITION], output_refs=['/directions/0/choice'])
        result.text = json.dumps(raw, ensure_ascii=False)
        return result


@pytest.mark.parametrize('bind', [True, False], ids=['adopted-relation', 'unadopted-relation'])
def test_plot_dynamic_source_requires_an_adopted_early_relation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                              bind: bool) -> None:
    static, dynamic = _catalog(tmp_path, monkeypatch)
    path = tmp_path / 'project'
    provider = EarlyNetworkModel(static, dynamic, bind)
    with Store(path, create=True, test_mode=True) as store:
        store.init_project('旧卷与缺席的档案官')
        store.add_brief('调查缺席的退任档案官与旧卷改封历史，用悬疑剧情选择反映双方的真实关系')
        refs = []
        for key, kind, body in (
            ('archivist', 'character', {'name': '退任档案官', 'role': '缺席证人', 'want': '让旧卷可核验',
                                       'background': '曾在旧卷上保留改封时的私章', 'visibility': 'public'}),
            ('archive_history', 'world', {'title': '旧卷改封史', 'rule': '两次改封日期可以仔细核对',
                                         'limits': '见证人缺席', 'visibility': 'public'}),
        ):
            ref = save_card(store, {'card_id': key, 'kind': kind, 'origin': 'author', 'body': body}, None)
            decision = decide_card(store, ref, 'approved', '核对实际关系双方')
            refs.append({**asdict(ref), 'decision_id': decision.id})
        adopt_story(store, baseline(card_refs=refs), {})
        job = start_job(store, JobRequest('design', design_scope='book', budget=Budget(18, 90000, 4500))).id
        result = resume_job(store, job, provider, config(store), choose)
        assert result.status == 'DONE', result.reason
        proposal = result.outputs['proposal_id']

    with Store(path, test_mode=True) as store:
        call = store.connection.execute('SELECT manifest_id FROM task_calls WHERE id=?', (proposal,)).fetchone()
        _, frozen = read_input_manifest(store, call['manifest_id'])
        session = frozen['material_work']
        assert session['context']['early_network_policy'] == EARLY_POLICY
        assert static in session['context']['early_static_sources']
        stages = {record['stage']: record for record in session['stages']}
        assert static in stages['static_relations']['prepared_static_sources']
        assert (dynamic in stages['plot_design']['source_ids']) == bind
        if bind:
            [adoption] = [item for item in stages['plot_design']['products']['_criteria'] if item['source_id'] == dynamic]
            applied = [clause for clause in adoption['clauses'] if clause['applicability'] == 'applies']
            assert applied and all(PLOT_CONDITION in clause['input_refs'] for clause in applied)
        else:
            [waiting] = stages['plot_design']['source_selection']['network_waiting']['examples']
            assert waiting == {'key': DYNAMIC_KEY, 'static_key': STATIC_KEY, 'reason': '上游未落实本项目的对应静网关系'}
        verify_chain(session)
