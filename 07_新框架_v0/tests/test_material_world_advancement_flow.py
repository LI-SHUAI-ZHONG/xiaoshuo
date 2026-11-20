"""Run a world advancement prerequisite against an isolated six-source catalog."""
from contextlib import closing
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
from typing import Any

import pytest

from fake_binding_reviews import install_review_fixtures
from fake_semantic_clauses import criteria_for
from nw.cards import decide_card, save_card
from nw.llm.base import GenResult
from nw.materials import phase_routes
from nw.materials.adjudication import build_adjudications
from nw.materials.binding_reviews import verify_session_bindings
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


STATIC_KEY = '12.10_临界值 / 15.1_进阶条件 / 约束'
DYNAMIC_KEY = 'C00099'
SELECTED_GENRE = ('GENRE_XUANHUAN', '玄幻')
OTHER_GENRE = ('GENRE_ERCIYUAN', '二次元')
POLICY = 'world-advancement-prerequisites-v1'
CARD_ID = 'apprentice-advancement'
APPROVED_RULE = '灵压达到 30 灵格才可进入凝印期。'
APPROVED_LIMITS = '还须通过验标，门槛只适用于持证衡灵者。'
PHYSICAL_RULE = '灵压临界值为 30 灵格。灵压达到 30 灵格时仅启动装置校准。'
PHYSICAL_LIMITS = '该阈值只用于装置校准。凝印期的准入另以导师核验为准。'
TYPE_REF = 'input:type_selection:/selection/0/basis'
RULE_REF = f'approved:{CARD_ID}:/body/rule'
LIMITS_REF = f'approved:{CARD_ID}:/body/limits'
OUTPUT_RULE = '/members/0/body/rule'
OUTPUT_LIMITS = '/members/0/body/limits'


def _catalog(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, str]:
    edge = {'source': '12.10_临界值', 'target': '15.1_进阶条件', 'type': '约束', 'condition': '临界值是进阶条件'}
    dynamic = {'id': DYNAMIC_KEY, **edge, 'condition': '临界值是进阶条件；且当前故事明确采用该静态关系',
               'effect': '当起点成立时，限制终点可采取的状态或行为范围。',
               'generated_from_static': True, 'valid_types': ['玄幻']}
    genres = [{'type_id': ident, 'canonical_name': label, 'type_kind': 'GENRE', 'parent_id': None,
               'definition': f'{label}项目按作者明确选择的故事类型处理世界规则', 'status': 'active'}
              for ident, label in (SELECTED_GENRE, OTHER_GENRE)]
    entries = [
        ('library.txt', 'library', '### 12.10_临界值\n【定义】以设定中的实际量和单位核对的临界门槛。\n'
                                   '### 15.1_进阶条件\n【定义】作者确立的相应阶段晋升所需条件。\n'),
        ('types.txt', 'types', 'SOURCE: 主类型.json\n=====\n' + json.dumps(genres, ensure_ascii=False)),
        ('links.txt', 'type_links', 'SOURCE: 类型连接.json\n=====\n{"definition":"核对项目的实际进阶条件"}\n'),
        ('静态网络.txt', 'static', json.dumps({'connections': [edge]}, ensure_ascii=False)),
        ('动态网络.txt', 'dynamic', json.dumps({'connections': [dynamic]}, ensure_ascii=False)),
        ('anchor.txt', 'anchors', '| A1.1 | 衡灵装置 | 查看刻度 | 以灵值显示时 | 基础 |\n'),
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
    version = {'policy': SOURCE_SET_POLICY, 'version_name': '[FAKE] 隔离六源进阶条件', 'sources': selected}
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
    monkeypatch.setitem(STAGE_MATERIALS, 'world_design', f'### {STATIC_KEY}\n【本步用法】\n'
                        '已采用进阶规则时，明确实际阈值对应哪项门槛，并保留其余已定条件。\n'
                        f'### {DYNAMIC_KEY}\n【本步用法】\n核对项目实际门槛的值、单位、适用阶段及并列条件。\n')
    build_adjudications(workspace)
    install_review_fixtures(workspace)
    desk = SourceDesk(workspace)
    [static] = [row['id'] for row in desk.rows if row['key'] == STATIC_KEY and row['state'] == 'design_ready']
    [derived] = [row['id'] for row in desk.rows if row['key'] == DYNAMIC_KEY and row['state'] == 'design_ready']
    assert desk.dynamic_rules()[derived]['static_id'] == static
    return static, derived


def _approved_card(store: Store, rule: str, limits: str) -> dict:
    card = save_card(store, {'card_id': CARD_ID, 'kind': 'world', 'origin': 'author', 'body': {
        'title': '凝印期门槛与衡灵判据', 'rule': rule, 'limits': limits, 'visibility': 'public'}}, None)
    decision = decide_card(store, card, 'approved', '已核对当前项目的门槛和保留条件')
    return {**asdict(card), 'decision_id': decision.id}


class AdvancementModel(Model):
    def __init__(self, static: str, derived: str, *, genre: tuple[str, str], advancement: bool) -> None:
        super().__init__()
        self.static = static
        self.derived = derived
        self.genre = genre
        self.eligible = advancement and genre == SELECTED_GENRE

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
        elif payload['stage'] == 'world_design':
            if self._world_products(payload, products):
                result.text = json.dumps({'stage': 'world_design',
                                          'requests': [{'action': 'search', 'query': DYNAMIC_KEY}]})
                return result
        elif payload['stage'] == 'plot_design':
            handoffs = [row for row in payload['semantic_requirements'] if row['source_id'] == self.derived]
            assert bool(handoffs) == self.eligible
            if self.eligible:
                delivered = {(item['path'], item['value']) for row in handoffs for item in row['actual_inputs']}
                assert delivered == {(OUTPUT_RULE, APPROVED_RULE), (OUTPUT_LIMITS, APPROVED_LIMITS)}
                products['directions'][0]['choice'] = (
                    '[FAKE] 主角先确认灵压是否达到三十灵格，再核对验标和持证条件，等候正式进阶认定')
                products['_receipts'] = [{'id': row['id'], 'operation': '[FAKE] 剧情按实际门槛、验标和持证条件推进认定',
                                          'output_refs': ['/directions/0/choice']}
                                         for row in payload['semantic_requirements']]
        result.text = json.dumps(body, ensure_ascii=False)
        return result

    def _world_products(self, payload: dict, products: dict) -> bool:
        offered = {item['source']['id'] for item in payload['sources']}
        prerequisites = payload.get('world_network_prerequisites', {})
        assert (self.derived in offered) == (self.derived in prerequisites) == self.eligible
        if not self.eligible:
            assert self.derived not in payload['readable_source_ids']
            if self.genre == SELECTED_GENRE:
                [waiting] = [item for item in payload['network_waiting']['examples'] if item['key'] == DYNAMIC_KEY]
                assert waiting['static_key'] == STATIC_KEY and '进阶' in waiting['reason']
            if not payload['responses']:
                return True
            assert all(row['id'] != self.derived for response in payload['responses'] for row in response['items'])

        products['_uses'] = []
        products['_excluded'] = [{'source_id': ident, 'reason': '[FAKE] 本任务无需独立采用此辅助原义'}
                                 for ident in sorted(offered - ({self.derived} if self.eligible else set()))]
        if self.eligible:
            evidence = prerequisites[self.derived]
            assert evidence['kind'] == 'advancement' and evidence['type_ids'] == [self.genre[0]]
            assert evidence['static_source']['static_id'] == self.static
            assert evidence['static_source']['source']['key'] == STATIC_KEY
            [card] = evidence['cards']
            assert card['card_id'] == CARD_ID and card['version'] == 1
            assert card['rule_ref'] == RULE_REF and card['limits_ref'] == LIMITS_REF
            assert card['rule'] == APPROVED_RULE and card['limits'] == APPROVED_LIMITS
            assert card['evidence']['threshold'] == '灵压达到 30 灵格'
            assert card['evidence']['gate'] == APPROVED_RULE.removesuffix('。')
            products['members'] = [{'key': 'verification-advancement', 'kind': 'world', 'body': {
                'title': '[FAKE] 凝印期的认定', 'rule': APPROVED_RULE, 'limits': APPROVED_LIMITS,
                'visibility': 'public'}}]
            products['_uses'].append({'source_id': self.derived,
                'operation': '[FAKE] 保留现有灵压门槛与验标、持证条件', 'output_refs': ['member:verification-advancement']})
        products['_criteria'] = criteria_for(payload, products)
        for criterion in products['_criteria']:
            for clause in criterion['clauses']:
                if clause['applicability'] == 'applies':
                    clause.update(input_refs=[TYPE_REF, RULE_REF, LIMITS_REF], output_refs=[OUTPUT_RULE, OUTPUT_LIMITS],
                                  consumer='plot_design', operation='[FAKE] 落实已批准的进阶门槛和另需满足的条件',
                                  observable='[FAKE] 主角到达灵压门槛后仍等候验标和持证核对',
                                  check='[FAKE] 核对剧情没有把达到门槛直接写成认定完成')
        return False


@pytest.mark.parametrize(('advancement', 'genre'), [(True, SELECTED_GENRE), (False, SELECTED_GENRE), (True, OTHER_GENRE)],
                         ids=['approved-advancement-gate', 'physical-threshold-only', 'wrong-type'])
def test_world_advancement_preserves_approved_threshold_through_design_and_replay(tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch, advancement: bool, genre: tuple[str, str]) -> None:
    static, derived = _catalog(tmp_path, monkeypatch)
    provider = AdvancementModel(static, derived, advancement=advancement, genre=genre)
    path = tmp_path / 'project'
    with Store(path, create=True, test_mode=True) as store:
        store.init_project('衡灵与凝印期门槛')
        store.add_brief(f'作者已选{genre[1]}，项目拟按已批准世界卡核对灵压及凝印期认定。')
        rule, limits = (APPROVED_RULE, APPROVED_LIMITS) if advancement else (PHYSICAL_RULE, PHYSICAL_LIMITS)
        adopt_story(store, baseline(card_refs=[_approved_card(store, rule, limits)]), {})
        job = start_job(store, JobRequest('design', design_scope='book', budget=Budget(18, 90000, 4500))).id
        result = resume_job(store, job, provider, config(store), choose)
        assert result.status == 'DONE', result.reason
        proposal = result.outputs['proposal_id']

    with Store(path, test_mode=True) as store:
        call = store.connection.execute('SELECT manifest_id FROM task_calls WHERE id=?', (proposal,)).fetchone()
        _, frozen = read_input_manifest(store, call['manifest_id'])
        session = frozen['material_work']
        assert session['context']['world_advancement_policy'] == POLICY
        stages = {record['stage']: record for record in session['stages']}
        design = stages['world_design']
        assert (derived in design['source_ids']) == provider.eligible
        if provider.eligible:
            [criterion] = [row for row in design['products']['_criteria'] if row['source_id'] == derived]
            adopted = [clause for clause in criterion['clauses'] if clause['applicability'] == 'applies']
            assert adopted and all(clause['input_refs'] == [TYPE_REF, RULE_REF, LIMITS_REF]
                                   and clause['output_refs'] == [OUTPUT_RULE, OUTPUT_LIMITS] for clause in adopted)
            assert stages['plot_design']['products']['_receipts']
        verify_chain(session)
        verify_session_bindings(session, tmp_path, test_mode=True)
