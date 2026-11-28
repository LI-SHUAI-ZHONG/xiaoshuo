"""End-to-end verification for the Creative Novel Workflow (creative-workflow-v1).

Proves:
1. Book, Volume, and Chapter scopes skip redundant LLM calls for already-decided
   type_selection / type_adaptation (and empty volume bind_scope) by compiling/inheriting
   them programmatically while still passing all chain, governance, and binding checks.
2. Creative deliverables are strictly enforced and handed off downstream:
   - book_directions: opening_hook, story_arcs, protagonist_arc, design_needs
   - book plot_design: opening_plan, character_arcs (existing entity keys), story_segments
   - volume plot_design: chapter_splits (unique positive chapter indexes + handoffs)
   - chapter plot_design: receives creative_handoff.assigned_chapter_split & opening_plan
3. Studio ProductionViews.progress() exposes the real working novel-creation steps,
   moves auto-compiled/inherited type contracts into auto_contracts, and groups chapter
   steps under creative working phases.
4. Frontend JS modules and blueprints expose the updated creative workflow consistently.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nw.llm.base import GenResult
from nw.materials.creative_workflow import POLICY, validate_plot_deliverables, workflow_overview
from nw.studio.api import StudioService
from nw.studio.library import LibraryService
from nw.studio.production import ProductionService
from test_novel_direction_flow import OPTIONS
from test_studio_project_methods import client  # noqa: F401


CREATIVE_OPTIONS = [
    {
        **row,
        'opening_hook': f'[FAKE] 第一章开篇即在渡口查账现场撞破篡改墨迹（方案{idx}）',
        'story_arcs': f'[FAKE] 起势发现假账→升级查权限链→中段遭反咬停职→危机孤证翻盘→终局制度清算（方案{idx}）',
        'protagonist_arc': f'[FAKE] 盲信旧规→目睹制度包庇→选择越权留证→失去庇护代价→成为新规立证者（方案{idx}）',
        'design_needs': f'[FAKE] 需落实渡口封存权限规则、查验代价及档案员与执事双线人物（方案{idx}）',
    }
    for idx, row in enumerate(OPTIONS, start=1)
]


def test_creative_workflow_deliverables_validation_enforces_book_and_volume_contracts():
    products = {
        'character_design': {'products': {'members': [{'key': 'char_shen', 'kind': 'character', 'body': {}}]}},
    }
    book_ctx = {'creative_workflow_policy': POLICY, 'scope': 'book', 'approved_cards': []}

    # Missing opening_plan fails
    with pytest.raises(ValueError, match='opening_plan'):
        validate_plot_deliverables({}, products, book_ctx)

    # Bad character key in character_arcs fails
    with pytest.raises(ValueError, match='人物弧光'):
        validate_plot_deliverables({
            'opening_plan': {
                'hook_moment': '雨夜封港发现账页被换',
                'first_chapter_promise': '底层书吏靠旧印追查制度黑账',
                'golden_three_beats': ['第1章发现两册日期冲突', '第2章查调换权限被阻', '第3章拿到第一份旁证'],
                'reader_expectation': '幕后是谁拥有双印封存权',
            },
            'character_arcs': [{
                'character': 'ghost_unknown',
                'start_state': '循规蹈矩', 'trigger_event': '账册被调包',
                'choice': '私留副本', 'cost': '被调离核心库', 'new_state': '主动破局', 'target_span': '第1卷',
            }],
            'story_segments': [{
                'id': 'seg_1', 'title': '假账初露', 'entry_condition': '入库对账',
                'core_events': '比对双册日期', 'turning_choice': '偷抄底账',
                'ending_state': '身份暴露风险', 'next_driver': '追查谁有改账权限',
            }],
        }, products, book_ctx)

    # Valid book deliverables pass
    validate_plot_deliverables({
        'opening_plan': {
            'hook_moment': '雨夜封港发现账页被换',
            'first_chapter_promise': '底层书吏靠旧印追查制度黑账',
            'golden_three_beats': ['第1章发现两册日期冲突', '第2章查调换权限被阻', '第3章拿到第一份旁证'],
            'reader_expectation': '幕后是谁拥有双印封存权',
        },
        'character_arcs': [{
            'character': 'char_shen',
            'start_state': '循规蹈矩', 'trigger_event': '账册被调包',
            'choice': '私留副本', 'cost': '被调离核心库', 'new_state': '主动破局', 'target_span': '第1卷第1-5章',
        }],
        'story_segments': [{
            'id': 'seg_1', 'title': '假账初露', 'entry_condition': '入库对账',
            'core_events': '比对双册日期', 'turning_choice': '偷抄底账',
            'ending_state': '身份暴露风险', 'next_driver': '追查谁有改账权限',
        }],
    }, products, book_ctx)

    # Volume missing chapter_splits fails; duplicate chapter_index fails
    vol_ctx = {'creative_workflow_policy': POLICY, 'scope': 'volume', 'approved_cards': []}
    with pytest.raises(ValueError, match='chapter_splits'):
        validate_plot_deliverables({}, products, vol_ctx)
    split_row = {
        'chapter_index': 1, 'title': '旧印日期差', 'mission': '发现两册登记日期矛盾',
        'entering_state': '主角接手核验', 'key_turn': '对照外抄本排除笔误',
        'ending_change': '坐实人为调包', 'handoff_to_next': '追查谁有封存室钥匙',
        'hook_or_foreshadow': '埋下旧印缺角伏笔',
    }
    with pytest.raises(ValueError, match='唯一正整数章号'):
        validate_plot_deliverables({'chapter_splits': [split_row, dict(split_row)]}, products, vol_ctx)
    validate_plot_deliverables({'chapter_splits': [split_row]}, products, vol_ctx)


@pytest.mark.parametrize('client', ['world'], indirect=True)
def test_creative_workflow_skips_redundant_type_calls_and_delivers_working_steps_end_to_end(client):
    from ai_world_method_fixture import BRIEF, TAXON, WorldModel

    send, settled, server, _ = client
    config, _ = server.production._runtime()
    llm_stages_called: list[tuple[str, str]] = []
    chapter_plot_handoffs: list[dict] = []

    class CreativeModel(WorldModel):
        def generate(self, messages, **params):
            if '[BOOK_DIRECTIONS]' in messages[0]['content']:
                self.calls.append(messages)
                llm_stages_called.append(('book', 'book_directions'))
                return GenResult(json.dumps({'candidates': CREATIVE_OPTIONS}, ensure_ascii=False), 'complete', {}, 'test', {})
            packet = json.loads(messages[-1]['content'])
            stage = packet.get('stage')
            scope = packet.get('scope')
            if stage:
                llm_stages_called.append((scope, stage))
            if stage == 'world_design' and packet.get('production_methods'):
                # Programmatic type_adaptation supplies real parameters (primary_drive / story_premise),
                # so bind design_basis to the actual parameter key instead of WorldModel's hardcoded 'investigation'.
                from project_methods_fixture import ProjectModel
                from ai_world_method_fixture import RULE, LIMIT
                base_res = ProjectModel.generate(self, messages, **params)
                raw = json.loads(base_res.text)
                products = raw['products']
                spec = packet['production_methods'][0]
                adapt_params = spec['inputs']['approach']['value']['adaptations'][0]['parameters']
                param_key = 'primary_drive' if 'primary_drive' in adapt_params else next(iter(adapt_params))
                world = products['members'][0]
                world['body'].update(title='[FAKE] 临川渡通行门槛', rule=RULE, limits=LIMIT)
                places = [{'path': ['members', 0, 'body', k], 'value': world['body'][k]} for k in ('rule', 'limits')]
                products['_method_applications'] = [{
                    'method_id': spec['method']['id'],
                    'design_basis': [{'kind': 'type_adaptation', 'path': ['adaptations', 0, 'parameters', param_key]}],
                    'operations': [{'key': 'design', 'explanation': '[FAKE] 按渡口可见证据与调包疑点设计两方核验与失败记录。'}],
                    'outputs': [{'key': 'gate', 'placements': places, 'scene_guidance': []}],
                }]
                base_res.text = json.dumps(raw, ensure_ascii=False)
                return base_res
            response = super().generate(messages, **params)
            if stage != 'plot_design':
                return response
            raw = json.loads(response.text)
            products = raw['products']
            products['directions'] = products['directions'][:1]
            for row in products.get('_method_receipts', []):
                row['placements'] = [p for p in row['placements'] if p['path'][:2] != ['directions', 1]]
            chars = [m['key'] for m in packet.get('inputs', {}).get('character_design', {}).get('products', {}).get('members', [])]
            if not chars:
                chars = [c['card_id'] for c in packet.get('approved_cards', []) if c.get('kind') == 'character']
            lead = chars[0] if chars else 'protagonist'
            if scope == 'book':
                products['opening_plan'] = {
                    'hook_moment': '[FAKE] 渡口夜检时发现两册通关账印痕日期不符',
                    'first_chapter_promise': '[FAKE] 以严密物证与制度博弈撕开封港黑幕',
                    'golden_three_beats': ['[FAKE] 第1章发现日期差', '[FAKE] 第2章排除笔误并遭遇阻拦', '[FAKE] 第3章获取外抄孤证'],
                    'reader_expectation': '[FAKE] 究竟谁有权调换封存渡口登记册',
                }
                products['character_arcs'] = [{
                    'character': lead,
                    'start_state': '[FAKE] 相信按章办事就能明哲保身',
                    'trigger_event': '[FAKE] 发现上级授意覆写渡口登记',
                    'choice': '[FAKE] 暗中留存外抄印痕对照本',
                    'cost': '[FAKE] 被排挤出核心核验岗位并遭监视',
                    'new_state': '[FAKE] 转为以制度缝隙反制幕后掌印者',
                    'target_span': '[FAKE] 第一卷第1至第3章',
                }]
                products['story_segments'] = [{
                    'id': 'seg_1',
                    'title': '[FAKE] 假账初现与权限封锁',
                    'entry_condition': '[FAKE] 主角例行复核渡口旧册',
                    'core_events': '[FAKE] 发现日期涂改、排查经手人并留存外抄本',
                    'turning_choice': '[FAKE] 拒绝上交原册而是留下可验副本',
                    'ending_state': '[FAKE] 幕后势力警觉并收紧审批权限',
                    'next_driver': '[FAKE] 必须追查谁掌握更早一次调包的双印权',
                }]
            elif scope == 'volume':
                others = [m for m in products['members'] if m['kind'] not in ('volume', 'chapter')]
                products['members'] = [*others, {'key': 'current_volume', 'kind': 'volume', 'body': {
                    'title': '[FAKE] 第一卷·渡口旧印', 'goal': '[FAKE] 核实被调换登记记录的依据',
                    'turn': '[FAKE] 复核印痕发现更早一次调包',
                    'ending_direction': '[FAKE] 留下可核对的外抄本，将更早调包交给后续追查'}}]
                products['chapter_splits'] = [
                    {
                        'chapter_index': 1, 'title': '[FAKE] 覆写之印',
                        'mission': '[FAKE] 发现两册渡口登记日期矛盾并排除抄录笔误',
                        'entering_state': '[FAKE] 主角在夜检时接手新旧渡口册',
                        'key_turn': '[FAKE] 比对压痕确认有人持印重录',
                        'ending_change': '[FAKE] 坐实人为调包并取得外抄证据',
                        'handoff_to_next': '[FAKE] 追查当夜谁曾进入封存档案室',
                        'hook_or_foreshadow': '[FAKE] 埋下旧印边缘缺口伏笔',
                    },
                    {
                        'chapter_index': 2, 'title': '[FAKE] 封存之钥',
                        'mission': '[FAKE] 排查封存室准入名单并遭遇执事阻挠',
                        'entering_state': '[FAKE] 主角持有外抄证据暗查权限',
                        'key_turn': '[FAKE] 档案员在压力下泄露出入记录缺页',
                        'ending_change': '[FAKE] 锁定两名有权开封的实权人物',
                        'handoff_to_next': '[FAKE] 设局迫使其中一人暴露真实动机',
                        'hook_or_foreshadow': '[FAKE] 回收旧印缺口指向前任主簿',
                    },
                ]
            elif scope == 'chapter':
                if packet.get('creative_handoff'):
                    chapter_plot_handoffs.append(packet['creative_handoff'])
            response.text = json.dumps(raw, ensure_ascii=False)
            return response

    model = CreativeModel()
    server.production.runtime_factory = lambda: (config, model)
    status, created = send('POST', '/api/novels', {
        'title': '[FAKE] 创作工作流实测', 'idea': BRIEF,
        'genre_ids': [TAXON], 'design_mode': 'manual',
        'direction_review': True, 'planning_hierarchy': True, 'creative_workflow': True,
    })
    assert status == 201, created
    novel_id = created['novel']['id']
    base = f'/api/novels/{novel_id}'

    def approve(gate, root=None):
        body = {'action': 'approve', 'token': gate['token'], 'reason': '[FAKE] 核对本级创作交付'}
        if root is not None:
            body['root'] = root
        st, reply = send('POST', f"{base}/gates/{gate['id']}", body)
        assert st == 200, reply
        return settled(novel_id)

    # 1. Book direction -> approve -> Book plan
    prog0 = settled(novel_id)
    assert prog0['creative_workflow'] is True
    direction_gate = prog0['gates'][0]
    assert 'opening_hook' in direction_gate['target']['candidates'][0]
    assert 'story_arcs' in direction_gate['target']['candidates'][0]
    assert 'protagonist_arc' in direction_gate['target']['candidates'][0]
    assert 'design_needs' in direction_gate['target']['candidates'][0]

    after_dir = approve(direction_gate, direction_gate['target']['candidates'][0]['id'])
    book_gate = after_dir['gates'][0]
    book_done = approve(book_gate, book_gate['target']['candidates'][0]['root']['card_id'])
    assert book_done['status'] == 'DONE' and book_done['next_design']['scope'] == 'volume'

    # Verify 0 LLM calls on book type_selection & type_adaptation (single-genre auto-compiled!)
    book_llm = [st for sc, st in llm_stages_called if sc == 'book']
    assert 'type_selection' not in book_llm
    assert 'type_adaptation' not in book_llm
    assert {'book_directions', 'world_design', 'character_design', 'static_relations', 'plot_design'} <= set(book_llm)

    # Verify book UI tree shows creative step labels and hides auto type stages in auto_contracts
    book_entry = next(n for n in book_done['tree'] if n.get('scope') == 'book')
    assert book_entry.get('creative_workflow') is True
    assert not any(ch.get('stage') in ('type_selection', 'type_adaptation') for ch in book_entry['children'])
    assert {c['stage'] for c in book_entry.get('auto_contracts', [])} == {'type_selection', 'type_adaptation'}
    assert any(ch['label'] == '全书主线、开篇承诺与分卷大纲' for ch in book_entry['children'])

    # 2. Volume design -> 0 LLM calls for type_selection, type_adaptation, AND bind_scope!
    st, reply = send('POST', base + '/run', {})
    assert st == 200, reply
    vol_wait = settled(novel_id)
    assert vol_wait['status'] == 'WAITING', vol_wait['reason']
    vol_llm = [st for sc, st in llm_stages_called if sc == 'volume']
    assert 'type_selection' not in vol_llm
    assert 'type_adaptation' not in vol_llm
    assert 'bind_scope' not in vol_llm
    assert 'plot_design' in vol_llm

    vol_entry = next(n for n in vol_wait['tree'] if n.get('scope') == 'volume')
    assert vol_entry['label'] == '卷纲与逐章切分'
    assert not any(ch.get('stage') in ('type_selection', 'type_adaptation', 'bind_scope') for ch in vol_entry['children'])
    assert {c['stage'] for c in vol_entry.get('auto_contracts', [])} == {'type_selection', 'type_adaptation', 'bind_scope'}

    vol_gate = vol_wait['gates'][0]
    vol_done = approve(vol_gate, vol_gate['target']['candidates'][0]['root']['card_id'])
    assert vol_done['status'] == 'DONE' and vol_done['next_design']['scope'] == 'chapter'

    # 3. Chapter design -> 0 LLM calls for type_selection & type_adaptation, receives volume chapter_splits!
    st, reply = send('POST', base + '/run', {})
    assert st == 200, reply
    ch_wait = settled(novel_id)
    assert ch_wait['status'] == 'WAITING', ch_wait['reason']
    assert ch_wait['gates'][0]['target']['kind'] == 'chapter_outline_approval'

    ch_llm = [st for sc, st in llm_stages_called if sc == 'chapter']
    assert 'type_selection' not in ch_llm
    assert 'type_adaptation' not in ch_llm
    assert chapter_plot_handoffs, 'Chapter plot_design must receive creative_handoff from parent volume'
    assert chapter_plot_handoffs[0]['assigned_chapter_split']['chapter_index'] == 1
    assert '发现两册渡口登记日期矛盾' in chapter_plot_handoffs[0]['assigned_chapter_split']['mission']

    ch_entry = next(n for n in ch_wait['tree'] if n.get('scope') == 'chapter')
    assert ch_entry['label'] == '章细纲与可写场景包'
    assert not any(ch.get('stage') in ('type_selection', 'type_adaptation') for ch in ch_entry['children'])
    assert {c['stage'] for c in ch_entry.get('auto_contracts', [])} == {'type_selection', 'type_adaptation'}
    group_labels = {ch.get('group_label') for ch in ch_entry['children'] if ch.get('group_label')}
    assert {'一、本章承接与章纲确认', '二、场景节拍与行动状态', '三、写前表现与场景工作包'} <= group_labels


def test_creative_workflow_blueprints_and_frontend_assets():
    ov = workflow_overview()
    assert ov['policy'] == POLICY
    assert len(ov['tiers']) == 4

    studio = StudioService(Path('workspace').resolve(), config_path=Path('studio.config.toml').resolve())
    bp = studio.pipeline_blueprint('chapter')
    assert bp['creative_workflow']['policy'] == POLICY
    assert all('creative_label' in row for row in bp['design_steps'])

    js_root = Path(__file__).resolve().parents[1] / 'src' / 'nw' / 'studio' / 'static' / 'js'
    assert 'creative_workflow:true' in (js_root / 'pages' / 'wizard.js').read_text(encoding='utf-8')
    assert 'data-auto-contracts' in (js_root / 'components' / 'ProgressTree.js').read_text(encoding='utf-8')
    for marker in ('openingPlanCard', 'characterArcsCard', 'storySegmentsCard', 'chapterSplitsCard'):
        assert marker in (js_root / 'components' / 'PlanArtifacts.js').read_text(encoding='utf-8')
    assert 'creativeWorkflowRoadmap' in (js_root / 'pages' / 'studio.js').read_text(encoding='utf-8')
    assert 'creativeWorkflowOverviewPanel' in (js_root / 'pages' / 'prerequisites.js').read_text(encoding='utf-8')
