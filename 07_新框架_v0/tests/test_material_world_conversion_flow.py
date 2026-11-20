"""Carry an approved energy conversion from live source screening into a saved plot."""
from contextlib import closing
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
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
from nw.materials.stage_input import step_uses
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


SELECTED_GENRE = ('GENRE_XUANHUAN', '玄幻')
OTHER_GENRE = ('GENRE_ERCIYUAN', '二次元')
CARD_ID = 'approved-world-rule'
APPROVED_RULE = '湿雾井中的游离态灵雾，经滤晶匣在封闭条件下摄取，转化为可储存的凝聚态灵液。'
APPROVED_LIMITS = '仅在井内封印完好且滤晶匣验标后使用，松封时停止摄取。'
MISMATCHED_START = '湿雾井中的固化态灵盐，经滤晶匣在封闭条件下摄取，转化为可储存的凝聚态灵液。'
MISSING_PRODUCT = '湿雾井中的游离态灵雾，经滤晶匣在封闭条件下摄取，具体转化产物待核。'
TYPE_REF = 'input:type_selection:/selection/0/basis'
RULE_REF = f'approved:{CARD_ID}:/body/rule'
LIMITS_REF = f'approved:{CARD_ID}:/body/limits'
OUTPUT_RULE = '/members/0/body/rule'
OUTPUT_LIMITS = '/members/0/body/limits'


@dataclass(frozen=True)
class WorldRuleCase:
    kind: str
    policy_key: str
    policy: str
    dynamic_key: str
    static_key: str
    condition: str
    effect: str
    rule: str
    limits: str
    waiting_reason: str
    choice: str
    observable: str
    check: str
    changed_rule: str
    changed_limits: str
    expected_evidence: tuple[tuple[str, str], ...] = ()
    title: str = '湿雾井的灵液来源'


CONVERSION = WorldRuleCase(
    kind='conversion', policy_key='world_conversion_policy', policy='world-conversion-prerequisites-v1',
    dynamic_key='C00050', static_key='11.1_游离态 / 11.4_转化路径 / 转化', condition='游离态可转化',
    effect='当起点成立并满足转化条件时，将起点状态转为终点状态。',
    rule=APPROVED_RULE, limits=APPROVED_LIMITS, waiting_reason='游离态',
    choice='[FAKE] 主角先核对井内封印和滤晶匣验标，再验证灵雾能否转成可储存的灵液。',
    observable='[FAKE] 主角用已验标的滤晶匣在密封井内寻找可储存的凝聚态灵液',
    check='[FAKE] 核对剧情在密封与验标条件成立后才使用滤晶匣',
    changed_rule=APPROVED_RULE.replace('凝聚态灵液', '固化态晶片'), changed_limits='松封时停止摄取。',
)


def _catalog(workspace: Path, monkeypatch: pytest.MonkeyPatch,
             cases: tuple[WorldRuleCase, ...]) -> dict[str, tuple[str, str]]:
    edges, rules, definitions = [], [], {}
    for case in cases:
        source, target, relation = case.static_key.split(' / ')
        edge = {'source': source, 'target': target, 'type': relation, 'condition': case.condition}
        edges.append(edge)
        rules.append({
            'id': case.dynamic_key, **edge, 'condition': case.condition + '；且当前故事明确采用该静态关系',
            'effect': case.effect, 'generated_from_static': True,
            'valid_types': ['玄幻', '仙侠', '科幻', '游戏', '军事', '悬疑', '都市', '历史', '言情', '奇幻'],
        })
        for term in (source, target):
            definitions[term] = f'### {term}\n【定义】本步核对的世界规则端点。\n'
    genres = [{'type_id': ident, 'canonical_name': label, 'type_kind': 'GENRE', 'parent_id': None,
               'definition': f'{label}项目按作者明确选择的故事类型处理世界规则', 'status': 'active'}
              for ident, label in (SELECTED_GENRE, OTHER_GENRE)]
    entries = [
        ('library.txt', 'library', ''.join(definitions.values())),
        ('types.txt', 'types', 'SOURCE: 主类型.json\n=====\n' + json.dumps(genres, ensure_ascii=False)),
        ('links.txt', 'type_links', 'SOURCE: 类型连接.json\n=====\n{"definition":"核对项目采用的世界规则"}\n'),
        ('静态网络.txt', 'static', json.dumps({'connections': edges}, ensure_ascii=False)),
        ('动态网络.txt', 'dynamic', json.dumps({'connections': rules}, ensure_ascii=False)),
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
    version = {'policy': SOURCE_SET_POLICY, 'version_name': '[FAKE] 隔离六源世界规则', 'sources': selected}
    version['sha256'] = content_sha256(version)
    (workspace / 'materials/active_source_set.json').write_text(json.dumps(version, ensure_ascii=False), encoding='utf-8')
    with closing(sqlite3.connect(workspace / 'materials/catalog.db')) as database, database:
        database.execute('CREATE TABLE source_set_selection (singleton INTEGER PRIMARY KEY, policy TEXT, sha256 TEXT)')
        database.execute('INSERT INTO source_set_selection VALUES (1,?,?)', (SOURCE_SET_POLICY, version['sha256']))
    for family, variable in [('static', '_STATIC_NETWORK_SHA256'), ('dynamic', '_DYNAMIC_NETWORK_SHA256')]:
        pin = next(row['file_sha256'] for row in selected if row['family'] == family)
        monkeypatch.setattr(phase_routes, variable, pin)
    original_uses = step_uses(STAGE_MATERIALS['world_design'])
    for stage in phase_routes.phase_order('book'):
        monkeypatch.setitem(STAGE_MATERIALS, stage, '')
    world_uses = ''.join(f'### {key}\n【本步用法】\n{original_uses[key]}\n'
                         for case in cases for key in (case.static_key, case.dynamic_key))
    monkeypatch.setitem(STAGE_MATERIALS, 'world_design', world_uses)
    build_adjudications(workspace)
    install_review_fixtures(workspace)
    desk = SourceDesk(workspace)
    pairs = {}
    for case in cases:
        [static] = [row['id'] for row in desk.rows if row['key'] == case.static_key and row['state'] == 'design_ready']
        [derived] = [row['id'] for row in desk.rows if row['key'] == case.dynamic_key and row['state'] == 'design_ready']
        assert desk.dynamic_rules()[derived]['static_id'] == static
        pairs[case.dynamic_key] = static, derived
    return pairs


def _approved_card(store: Store, rule: str, limits: str, title: str) -> dict:
    card = save_card(store, {'card_id': CARD_ID, 'kind': 'world', 'origin': 'author', 'body': {
        'title': title, 'rule': rule, 'limits': limits, 'visibility': 'public'}}, None)
    decision = decide_card(store, card, 'approved', '已核对本项目采用的世界规则与适用范围')
    return {**asdict(card), 'decision_id': decision.id}


def _freeze_legacy_plan(store: Store, brief_version: int, job: str, provider: Model,
                        monkeypatch: pytest.MonkeyPatch, case: WorldRuleCase) -> None:
    freeze = planning.freeze_manifest

    def freeze_without_new_policy(project: Store, inputs: InputManifest, package: dict) -> str:
        old_package = {key: value for key, value in package.items() if key != case.policy_key}
        assert package[case.policy_key] == case.policy
        return freeze(project, replace(inputs, context_sha256=content_sha256(old_package)), old_package)

    ident = call_id(job, 'plan:book:propose', 1)
    with monkeypatch.context() as patch:
        patch.setattr(planning, 'freeze_manifest', freeze_without_new_policy)
        planning.prepare_plan_task(store, brief_version, 'book', provider, config(store), job, ident)
    _, checkpoint = read_input_manifest(store, f'plan:{ident}')
    assert case.policy_key not in checkpoint


class ApprovedWorldModel(Model):
    def __init__(self, case: WorldRuleCase, static: str, derived: str, *, genre: tuple[str, str], eligible: bool,
                 waiting: bool, lookup: bool = False) -> None:
        super().__init__()
        self.case = case
        self.static = static
        self.derived = derived
        self.genre = genre
        self.eligible = eligible
        self.waiting = waiting
        self.lookup = lookup
        self.adopted = {derived: case} if eligible else {}

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
            action = {'action': 'search', 'query': self.case.dynamic_key}
            if self.lookup and self.derived in payload['readable_source_ids']:
                action = {'action': 'read', 'id': self.derived}
            result.text = json.dumps({'stage': 'world_design', 'requests': [action]})
            return result
        elif payload['stage'] == 'plot_design':
            handoffs = [row for row in payload['semantic_requirements'] if row['source_id'] == self.derived]
            assert bool(handoffs) == self.eligible
            if self.eligible:
                delivered = {(item['path'], item['value']) for row in handoffs for item in row['actual_inputs']}
                assert delivered == {(OUTPUT_RULE, self.case.rule), (OUTPUT_LIMITS, self.case.limits)}
                for ident in self.adopted:
                    entries = [row for row in payload['semantic_requirements'] if row['source_id'] == ident]
                    assert {(item['path'], item['value']) for row in entries for item in row['actual_inputs']} == delivered
                products['directions'][0]['choice'] = ' '.join(method.choice for method in self.adopted.values())
                products['_receipts'] = [{
                    'id': row['id'], 'operation': self.adopted[row['source_id']].choice,
                    'output_refs': ['/directions/0/choice'],
                } for row in payload['semantic_requirements']]
        result.text = json.dumps(body, ensure_ascii=False)
        return result

    def _world_products(self, payload: dict, products: dict) -> bool:
        offered = {item['source']['id'] for item in payload['sources']}
        prerequisites = payload.get('world_network_prerequisites', {})
        if self.case.kind in ('resource', 'market'):
            available = payload.get(f'world_{self.case.kind}_matches', [])
            matches = [row for row in available if row['key'] == self.case.dynamic_key]
            for ident, method in self.adopted.items():
                if method.kind == self.case.kind:
                    assert any(row['key'] == method.dynamic_key and row['source_id'] == ident for row in available)
            assert [row['source_id'] for row in matches] == ([self.derived] if self.eligible else [])
        if self.lookup and self.derived not in offered:
            assert self.derived not in prerequisites
            if payload['responses']:
                assert any(row['id'] == self.derived for response in payload['responses'] for row in response['items'])
                assert self.derived in payload['readable_source_ids']
            return True
        assert (self.derived in offered) == (self.derived in prerequisites) == self.eligible
        if not self.eligible:
            assert self.derived not in payload['readable_source_ids']
            if self.waiting:
                [waiting] = [item for item in payload['network_waiting']['examples'] if item['key'] == self.case.dynamic_key]
                assert waiting['static_key'] == self.case.static_key and self.case.waiting_reason in waiting['reason']
            if not payload['responses']:
                return True
            assert all(row['id'] != self.derived for response in payload['responses'] for row in response['items'])

        products['_uses'] = []
        products['_excluded'] = [{'source_id': ident, 'reason': '[FAKE] 本任务无需独立采用此辅助原义'}
                                 for ident in sorted(offered - self.adopted.keys())]
        if self.eligible:
            evidence = prerequisites[self.derived]
            assert evidence['kind'] == self.case.kind and evidence['type_ids'] == [self.genre[0]]
            assert evidence['static_source']['static_id'] == self.static
            assert evidence['static_source']['source']['key'] == self.case.static_key
            assert evidence['static_source']['edge']['condition'] == self.case.condition
            [card] = evidence['cards']
            assert card['card_id'] == CARD_ID and card['version'] == 1
            assert card['rule_ref'] == RULE_REF and card['limits_ref'] == LIMITS_REF
            assert card['rule'] == self.case.rule and card['limits'] == self.case.limits
            for field, expected_text in self.case.expected_evidence:
                assert card['evidence'][field] == expected_text
            products['members'] = [{'key': 'verified-world-rule', 'kind': 'world', 'body': {
                'title': '[FAKE] ' + self.case.title, 'rule': self.case.rule, 'limits': self.case.limits,
                'visibility': 'public'}}]
            for ident, method in self.adopted.items():
                basis = prerequisites[ident]
                assert basis['kind'] == method.kind and basis['static_source']['source']['key'] == method.static_key
                [same_card] = basis['cards']
                assert same_card['card_id'] == card['card_id'] and same_card['version'] == card['version']
                assert (same_card['rule'], same_card['limits']) == (card['rule'], card['limits'])
                products['_uses'].append({'source_id': ident, 'operation': method.choice,
                                          'output_refs': ['member:verified-world-rule']})
        products['_criteria'] = criteria_for(payload, products)
        for criterion in products['_criteria']:
            for clause in criterion['clauses']:
                if clause['applicability'] == 'applies':
                    method = self.adopted[criterion['source_id']]
                    clause.update(input_refs=[TYPE_REF, RULE_REF, LIMITS_REF], output_refs=[OUTPUT_RULE, OUTPUT_LIMITS],
                                  consumer='plot_design', operation=method.choice,
                                  observable=method.observable, check=method.check)
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
    assert_world_flow(tmp_path, monkeypatch, CONVERSION, rule, genre, legacy)


def assert_world_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: WorldRuleCase,
                      rule: str, genre: tuple[str, str], legacy: bool, *, lookup: bool = False,
                      also_adopt: tuple[WorldRuleCase, ...] = (), input_limits: str | None = None,
                      rejection: str | None = None, altered_plot: tuple[str, str] | None = None) -> None:
    pairs = _catalog(tmp_path, monkeypatch, (case, *also_adopt))
    static, derived = pairs[case.dynamic_key]
    supported = genre == SELECTED_GENRE and not legacy
    limits = case.limits if input_limits is None else input_limits
    eligible = supported and rule == case.rule and limits == case.limits
    provider = ApprovedWorldModel(case, static, derived, genre=genre, eligible=eligible, waiting=supported and not eligible, lookup=lookup)
    provider.adopted.update({pairs[other.dynamic_key][1]: other for other in also_adopt})
    path = tmp_path / 'project'
    with Store(path, create=True, test_mode=True) as store:
        store.init_project(case.title)
        brief = store.add_brief(f'作者已选{genre[1]}，按已批准世界卡调查{case.title}。')
        adopt_story(store, baseline(card_refs=[_approved_card(store, rule, limits, case.title)]), {})
        job = start_job(store, JobRequest('design', design_scope='book', budget=Budget(18, 90000, 4500))).id
        if legacy:
            _freeze_legacy_plan(store, brief.version, job, provider, monkeypatch, case)
        result = resume_job(store, job, provider, config(store), choose)
        if rejection is not None:
            assert result.status != 'DONE' and rejection in str(result.reason), (result.status, result.reason)
            return
        assert result.status == 'DONE', result.reason
        proposal = result.outputs['proposal_id']

    with Store(path, test_mode=True) as store:
        call = store.connection.execute('SELECT manifest_id FROM task_calls WHERE id=?', (proposal,)).fetchone()
        _, frozen = read_input_manifest(store, call['manifest_id'])
        session = frozen['material_work']
        assert session['context'].get(case.policy_key) == (None if legacy else case.policy)
        stages = {record['stage']: record for record in session['stages']}
        world = stages['world_design']
        assert (derived in world['source_ids']) == eligible
        if lookup:
            [reading] = [entry for entry in world['source_selection']['read'] if entry['source']['id'] == derived]
            assert reading['execution_admitted'] and reading['step_material_delivered']
        plot = stages['plot_design']['products']
        if eligible:
            [criterion] = [row for row in world['products']['_criteria'] if row['source_id'] == derived]
            adopted = [clause for clause in criterion['clauses'] if clause['applicability'] == 'applies']
            assert adopted and all(clause['input_refs'] == [TYPE_REF, RULE_REF, LIMITS_REF]
                                   and clause['output_refs'] == [OUTPUT_RULE, OUTPUT_LIMITS] for clause in adopted)
        uses = {row['source_id']: row['output_refs'] for row in world['products']['_uses']}
        assert uses == {ident: ['member:verified-world-rule'] for ident in provider.adopted}
        handoffs = handoffs_for('plot_design', {'world_design': world})
        assert {item['source_id'] for item in handoffs} == provider.adopted.keys()
        receipts = {entry['id']: entry for entry in plot.get('_receipts', [])}
        for row in handoffs:
            receipt = receipts[row['id']]
            assert receipt['operation'] == provider.adopted[row['source_id']].choice
            assert receipt['output_refs'] == ['/directions/0/choice']
        verify_chain(session)
        verify_session_bindings(session, tmp_path, test_mode=True)
        if altered_plot:
            altered = deepcopy(session)
            changed = next(row for row in altered['stages'] if row['stage'] == 'plot_design')
            changed['products']['directions'][0]['choice'] = altered_plot[0]
            changed['sha256'] = content_sha256(changed['products'])
            with pytest.raises(ValueError, match=altered_plot[1]):
                verify_chain(altered)
        if eligible:
            changed_fields = {
                'rule': case.changed_rule,
                'limits': case.changed_limits,
            }
            for field, changed_value in changed_fields.items():
                altered = deepcopy(session)
                revised = next(row for row in altered['stages'] if row['stage'] == 'world_design')
                revised['products']['members'][0]['body'][field] = changed_value
                revised['sha256'] = content_sha256(revised['products'])
                admitted_kinds = '|'.join(method.kind for method in provider.adopted.values())
                with pytest.raises(ValueError, match=f'world ({admitted_kinds}) must preserve the complete approved'):
                    verify_chain(altered)
