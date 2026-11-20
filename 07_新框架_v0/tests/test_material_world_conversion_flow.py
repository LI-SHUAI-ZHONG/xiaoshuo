"""Carry an approved energy conversion from live source screening into a saved plot."""
from contextlib import closing
from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
import sqlite3
from typing import Any

import pytest

from fake_binding_reviews import install_review_fixtures
from fake_semantic_clauses import criteria_for
from nw import planning
from nw.cards import decide_card, save_card
from nw.llm.base import GenResult
from nw.materials import phase_routes
from nw.materials.adjudication import build_adjudications
from nw.materials.binding_reviews import verify_session_bindings
from nw.materials.catalog import build_catalog, list_catalog
from nw.materials.identity_catalog import audit_identities
from nw.materials.phase_flow import STAGE_MATERIALS
from nw.materials.phase_projection import verify_chain
from nw.materials.semantic_handoff import handoffs_for
from nw.materials.source_set import POLICY as SOURCE_SET_POLICY
from nw.materials.unit_catalog import index_units
from nw.materials.work_catalog import SourceDesk
from nw.novel_calls import call_id
from nw.novel_flow import JobRequest, resume_job, start_job
from nw.store import Store
from nw.story_state import adopt_story
from nw.task_models import Budget, InputManifest, content_sha256
from nw.tasks import read_input_manifest
from story_fixture import baseline
from test_material_catalog import _manifest
from test_material_workflow import choose
from test_novel_flow import Model, config


STATIC_KEY = '11.1_游离态 / 11.4_转化路径 / 转化'
DYNAMIC_KEY = 'C00050'
SELECTED_GENRE = ('GENRE_XUANHUAN', '玄幻')
OTHER_GENRE = ('GENRE_ERCIYUAN', '二次元')
POLICY = 'world-conversion-prerequisites-v1'
POLICY_KEY = 'world_conversion_policy'
CARD_ID = 'fog-well-conversion'
APPROVED_RULE = '湿雾井中的游离态灵雾，经滤晶匣在封闭条件下摄取，转化为可储存的凝聚态灵液。'
APPROVED_LIMITS = '仅在井内封印完好且滤晶匣验标后使用，松封时停止摄取。'
MISMATCHED_START = '湿雾井中的固化态灵盐，经滤晶匣在封闭条件下摄取，转化为可储存的凝聚态灵液。'
MISSING_PRODUCT = '湿雾井中的游离态灵雾，经滤晶匣在封闭条件下摄取，具体转化产物待核。'
TYPE_REF = 'input:type_selection:/selection/0/basis'
RULE_REF = f'approved:{CARD_ID}:/body/rule'
LIMITS_REF = f'approved:{CARD_ID}:/body/limits'
OUTPUT_RULE = '/members/0/body/rule'
OUTPUT_LIMITS = '/members/0/body/limits'


def _catalog(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, str]:
    edge = {'source': '11.1_游离态', 'target': '11.4_转化路径', 'type': '转化', 'condition': '游离态可转化'}
    dynamic = {
        'id': DYNAMIC_KEY, **edge, 'condition': '游离态可转化；且当前故事明确采用该静态关系',
        'effect': '当起点成立并满足转化条件时，将起点状态转为终点状态。',
        'generated_from_static': True,
        'valid_types': ['玄幻', '仙侠', '科幻', '游戏', '军事', '悬疑', '都市', '历史', '言情', '奇幻'],
    }
    genres = [{'type_id': ident, 'canonical_name': label, 'type_kind': 'GENRE', 'parent_id': None,
               'definition': f'{label}项目按作者明确选择的故事类型处理世界规则', 'status': 'active'}
              for ident, label in (SELECTED_GENRE, OTHER_GENRE)]
    entries = [
        ('library.txt', 'library', '### 11.1_游离态\n【定义】以游离形态存在的能量。\n'
                                   '### 11.4_转化路径\n【定义】能量由初始形态转为目的形态的过程。\n'),
        ('types.txt', 'types', 'SOURCE: 主类型.json\n=====\n' + json.dumps(genres, ensure_ascii=False)),
        ('links.txt', 'type_links', 'SOURCE: 类型连接.json\n=====\n{"definition":"核对项目采用的能量转化条件"}\n'),
        ('静态网络.txt', 'static', json.dumps({'connections': [edge]}, ensure_ascii=False)),
        ('动态网络.txt', 'dynamic', json.dumps({'connections': [dynamic]}, ensure_ascii=False)),
        ('anchor.txt', 'anchors', '| A1.1 | 滤晶匣 | 查看印记 | 条件成立时 | 基础 |\n'),
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
    version = {'policy': SOURCE_SET_POLICY, 'version_name': '[FAKE] 隔离六源能量转化', 'sources': selected}
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
                        '为项目已有的游离态转化记录环境来源、提取或吸收的中间步骤以及输出形态。\n'
                        f'### {DYNAMIC_KEY}\n【本步用法】\n核对项目采用的游离态转化条件、中间环节、产出及适用限制。\n')
    build_adjudications(workspace)
    install_review_fixtures(workspace)
    desk = SourceDesk(workspace)
    [static] = [row['id'] for row in desk.rows if row['key'] == STATIC_KEY and row['state'] == 'design_ready']
    [derived] = [row['id'] for row in desk.rows if row['key'] == DYNAMIC_KEY and row['state'] == 'design_ready']
    assert desk.dynamic_rules()[derived]['static_id'] == static
    return static, derived


def _approved_card(store: Store, rule: str) -> dict:
    card = save_card(store, {'card_id': CARD_ID, 'kind': 'world', 'origin': 'author', 'body': {
        'title': '湿雾井的灵液来源', 'rule': rule, 'limits': APPROVED_LIMITS, 'visibility': 'public'}}, None)
    decision = decide_card(store, card, 'approved', '已核对本项目采用的转化规则与适用范围')
    return {**asdict(card), 'decision_id': decision.id}


def _freeze_legacy_plan(store: Store, brief_version: int, job: str, provider: Model,
                        monkeypatch: pytest.MonkeyPatch) -> None:
    freeze = planning.freeze_manifest

    def freeze_without_new_policy(project: Store, inputs: InputManifest, package: dict) -> str:
        old_package = {key: value for key, value in package.items() if key != POLICY_KEY}
        assert package[POLICY_KEY] == POLICY
        return freeze(project, replace(inputs, context_sha256=content_sha256(old_package)), old_package)

    ident = call_id(job, 'plan:book:propose', 1)
    with monkeypatch.context() as patch:
        patch.setattr(planning, 'freeze_manifest', freeze_without_new_policy)
        planning.prepare_plan_task(store, brief_version, 'book', provider, config(store), job, ident)
    _, checkpoint = read_input_manifest(store, f'plan:{ident}')
    assert POLICY_KEY not in checkpoint


class ConversionModel(Model):
    def __init__(self, static: str, derived: str, *, genre: tuple[str, str], eligible: bool,
                 waiting: bool) -> None:
        super().__init__()
        self.static = static
        self.derived = derived
        self.genre = genre
        self.eligible = eligible
        self.waiting = waiting

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
        elif payload['stage'] == 'world_design' and self._world_products(payload, products):
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
                    '[FAKE] 主角先核对井内封印和滤晶匣验标，再验证灵雾能否转成可储存的灵液。')
                products['_receipts'] = [{
                    'id': row['id'], 'operation': '[FAKE] 调查先核验密封和验标，再追查井中灵液的来路。',
                    'output_refs': ['/directions/0/choice'],
                } for row in payload['semantic_requirements']]
        result.text = json.dumps(body, ensure_ascii=False)
        return result

    def _world_products(self, payload: dict, products: dict) -> bool:
        offered = {item['source']['id'] for item in payload['sources']}
        prerequisites = payload.get('world_network_prerequisites', {})
        assert (self.derived in offered) == (self.derived in prerequisites) == self.eligible
        if not self.eligible:
            assert self.derived not in payload['readable_source_ids']
            if self.waiting:
                [waiting] = [item for item in payload['network_waiting']['examples'] if item['key'] == DYNAMIC_KEY]
                assert waiting['static_key'] == STATIC_KEY and '游离态' in waiting['reason']
            if not payload['responses']:
                return True
            assert all(row['id'] != self.derived for response in payload['responses'] for row in response['items'])

        products['_uses'] = []
        products['_excluded'] = [{'source_id': ident, 'reason': '[FAKE] 本任务无需独立采用此辅助原义'}
                                 for ident in sorted(offered - ({self.derived} if self.eligible else set()))]
        if self.eligible:
            evidence = prerequisites[self.derived]
            assert evidence['kind'] == 'conversion' and evidence['type_ids'] == [self.genre[0]]
            assert evidence['static_source']['static_id'] == self.static
            assert evidence['static_source']['source']['key'] == STATIC_KEY
            assert evidence['static_source']['edge']['condition'] == '游离态可转化'
            [card] = evidence['cards']
            assert card['card_id'] == CARD_ID and card['version'] == 1
            assert card['rule_ref'] == RULE_REF and card['limits_ref'] == LIMITS_REF
            assert card['rule'] == APPROVED_RULE and card['limits'] == APPROVED_LIMITS
            products['members'] = [{'key': 'verified-conversion', 'kind': 'world', 'body': {
                'title': '[FAKE] 湿雾井的灵液来源', 'rule': APPROVED_RULE, 'limits': APPROVED_LIMITS,
                'visibility': 'public'}}]
            products['_uses'].append({
                'source_id': self.derived, 'operation': '[FAKE] 保留已批准的摄取方式、产物和适用条件',
                'output_refs': ['member:verified-conversion'],
            })
        products['_criteria'] = criteria_for(payload, products)
        for criterion in products['_criteria']:
            for clause in criterion['clauses']:
                if clause['applicability'] == 'applies':
                    clause.update(input_refs=[TYPE_REF, RULE_REF, LIMITS_REF], output_refs=[OUTPUT_RULE, OUTPUT_LIMITS],
                                  consumer='plot_design', operation='[FAKE] 按已批准的形态和路径安排调查',
                                  observable='[FAKE] 主角用已验标的滤晶匣在密封井内寻找可储存的凝聚态灵液',
                                  check='[FAKE] 核对剧情在密封与验标条件成立后才使用滤晶匣')
        return False


@pytest.mark.parametrize(
    ('rule', 'genre', 'legacy'),
    [(APPROVED_RULE, SELECTED_GENRE, False), (MISMATCHED_START, SELECTED_GENRE, False),
     (MISSING_PRODUCT, SELECTED_GENRE, False), (APPROVED_RULE, OTHER_GENRE, False),
     (APPROVED_RULE, SELECTED_GENRE, True)],
    ids=['approved-path', 'wrong-starting-state', 'missing-output', 'wrong-type', 'checkpoint-without-policy'],
)
def test_world_conversion_flows_through_live_selection_and_reopened_plot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, rule: str, genre: tuple[str, str], legacy: bool,
) -> None:
    static, derived = _catalog(tmp_path, monkeypatch)
    supported = genre == SELECTED_GENRE and not legacy
    eligible = supported and rule == APPROVED_RULE
    provider = ConversionModel(static, derived, genre=genre, eligible=eligible, waiting=supported and not eligible)
    path = tmp_path / 'project'
    with Store(path, create=True, test_mode=True) as store:
        store.init_project('湿雾井的灵雾转化')
        brief = store.add_brief(f'作者已选{genre[1]}，按已批准世界卡调查湿雾井中灵液的来源。')
        adopt_story(store, baseline(card_refs=[_approved_card(store, rule)]), {})
        job = start_job(store, JobRequest('design', design_scope='book', budget=Budget(18, 90000, 4500))).id
        if legacy:
            _freeze_legacy_plan(store, brief.version, job, provider, monkeypatch)
        result = resume_job(store, job, provider, config(store), choose)
        assert result.status == 'DONE', result.reason
        proposal = result.outputs['proposal_id']

    with Store(path, test_mode=True) as store:
        call = store.connection.execute('SELECT manifest_id FROM task_calls WHERE id=?', (proposal,)).fetchone()
        _, frozen = read_input_manifest(store, call['manifest_id'])
        session = frozen['material_work']
        assert session['context'].get(POLICY_KEY) == (None if legacy else POLICY)
        stages = {record['stage']: record for record in session['stages']}
        world = stages['world_design']
        assert (derived in world['source_ids']) == eligible
        plot = stages['plot_design']['products']
        if eligible:
            [criterion] = [row for row in world['products']['_criteria'] if row['source_id'] == derived]
            adopted = [clause for clause in criterion['clauses'] if clause['applicability'] == 'applies']
            assert adopted and all(clause['input_refs'] == [TYPE_REF, RULE_REF, LIMITS_REF]
                                   and clause['output_refs'] == [OUTPUT_RULE, OUTPUT_LIMITS] for clause in adopted)
        handoffs = [item for item in handoffs_for('plot_design', {'world_design': world})
                    if item['source_id'] == derived]
        assert bool(handoffs) == eligible
        receipts = {entry['id']: entry for entry in plot.get('_receipts', [])}
        assert all(receipts[row['id']]['output_refs'] == ['/directions/0/choice'] for row in handoffs)
        verify_chain(session)
        verify_session_bindings(session, tmp_path, test_mode=True)
        if eligible:
            changed_fields = {
                'rule': APPROVED_RULE.replace('凝聚态灵液', '固化态晶片'),
                'limits': '松封时停止摄取。',
            }
            for field, changed_value in changed_fields.items():
                altered = deepcopy(session)
                revised = next(row for row in altered['stages'] if row['stage'] == 'world_design')
                revised['products']['members'][0]['body'][field] = changed_value
                revised['sha256'] = content_sha256(revised['products'])
                with pytest.raises(ValueError, match='world conversion must preserve the complete approved'):
                    verify_chain(altered)
