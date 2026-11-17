"""Batch 31 regression tests for full material delivery, routing, anchor prose/review, and story continuity."""
import json
from dataclasses import asdict
from pathlib import Path

from nw.acceptance import accept_batch
from nw.cards import decide_card
from nw.context.story import StoryScope, build_story_context
from nw.materials.phase_flow import DEFAULT_STAGE_MATERIALS, STAGE_MATERIALS
from nw.materials.phase_routes import (
    _ANCHOR_TABLE_SHA256,
    _DYNAMIC_NETWORK_SHA256,
    _LIBRARY_SHA256,
    _STATIC_NETWORK_SHA256,
    _TYPE_SYSTEM_SHA256,
    _in_step_anchor_routes,
    route_method,
)
from nw.materials.stage_input import extract_step_keys, model_package, step_material_prompt
from nw.materials.steps.review import MATERIAL as REVIEW_MATERIAL
from nw.materials.steps.writing import MATERIAL as WRITING_MATERIAL
from nw.store import Store
from nw.story_models import StateHead
from nw.story_state import adopt_story, current_head
from story_fixture import baseline, draft_for, operation, proposal, seed_book
from test_selection import add_card


def test_step_material_prompt_parses_all_in_step_formats_without_leakage() -> None:
    sample = (
        '【测试步骤的资料】\n本步总体说明。\n\n'
        '### 6.2_复合情感\n【定义】复合定义\n【本步用法】\n第一段用法。\n\n第二段跨空行用法。\n\n'
        '### 6.2_复合情感\n【原文位置】同键补充\n【本步用法】\n同键第二处补充用法。\n\n'
        '100｜{"id":"C00002","source":"A","target":"B"}\n【本步用法】动态边无标题用法。\n\n'
        '200｜design_ready｜{"state_adaptation_id":"TSA_001"}\n【本步用法】状态适配无标题用法。\n\n'
        '300｜| M1.1 | 道具_完整 | 道具处于完整状态 | 未被损坏 | 物质 |\n【本步用法】无标题锚点用法。\n\n'
        '400｜1｜1.1_主角｜41.1_主线｜绑定｜高｜强｜必选｜0.9｜静态边第十列内联用法。\n\n'
        '500|SUB_XUANHUAN_01|东方玄幻：主类型子项\n【本步用法】分组子类型共用用法。\n\n'
        '#### AUDIENCE_EASY_READ 轻松阅读\n【本步用法】读者标签ASCII前缀标题用法。\n\n'
        '【原文行 469139】{"mechanism_id":"MECHANISM_GROWTH","canonical_name":"成长机制"}\n【本条用法】机制原文行用法。\n'
    )
    wanted = {
        '6.2_复合情感', 'C00002', 'TSA_001', 'M1.1',
        '1.1_主角 / 41.1_主线 / 绑定', 'SUB_XUANHUAN_01',
        'AUDIENCE_EASY_READ', 'MECHANISM_GROWTH',
    }
    prompt = step_material_prompt('当前步骤', sample, wanted)
    for key in wanted:
        assert prompt.splitlines().count('### ' + key) == 1, key
    assert '第二段跨空行用法。' in prompt
    assert '同键第二处补充用法。' in prompt
    assert '静态边第十列内联用法。' in prompt
    assert '原表定义：东方玄幻：主类型子项' in prompt
    assert '【原文位置】' not in prompt

    # Unselected keys never leak
    only_one = step_material_prompt('当前步骤', sample, {'M1.1'})
    assert only_one.splitlines().count('### M1.1') == 1
    assert '动态边无标题用法' not in only_one


def test_type_connection_records_deliver_usage_only_in_owning_stage() -> None:
    prompt_adapt = step_material_prompt('当前步骤', DEFAULT_STAGE_MATERIALS['type_adaptation'], {'TSC_000001'})
    assert prompt_adapt.splitlines().count('### TSC_000001') == 1
    assert 'focuses' in prompt_adapt

    prompt_world = step_material_prompt('当前步骤', DEFAULT_STAGE_MATERIALS['world_design'], {'TSC_000001'})
    assert '### TSC_000001' not in prompt_world


def test_newly_completed_emotion_and_compound_library_headings_deliver_cleanly() -> None:
    for idx, name in [
        ('6.2_复合情感', '身体信号组合'),
        ('6.3_社会情感', '目光、话语或礼数差距'),
        ('6.11_生存情感', '本能戒备'),
    ]:
        out = step_material_prompt('当前步骤', DEFAULT_STAGE_MATERIALS['expression_design'], {idx})
        assert out.splitlines().count('### ' + idx) == 1
        assert name in out

    for key, phrase in [
        ('1.3_次要配角', '言行前后差异'),
        ('1.5_缺席者', '不重复前文已披露内容'),
        ('5.7_信息不对称', '严守当前POV边界'),
        ('6.2_复合情感', '两层以上身体或动作信号组合'),
        ('8.1_身体状态', '步态、呼吸、发力或动作幅度'),
        ('15.2_进阶三阶段', '临界点变化'),
        ('16.4_透支后遗症', '分步恢复限制'),
        ('板块46 场景结构#场景视角', ''),
        ('板块86 社会交互#交易', ''),
        ('板块88 写手模式#输入', ''),
    ]:
        out = step_material_prompt('当前步骤', WRITING_MATERIAL, {key})
        assert out.splitlines().count('### ' + key) == 1, key
        if phrase:
            assert phrase in out


def test_all_anchor_prefixes_route_and_deliver_across_design_writing_and_review() -> None:
    anchor_routes = _in_step_anchor_routes()
    assert len(anchor_routes) >= 1780

    sample_anchors = [
        'M1.1', 'M2.1', 'M3.1', 'M4.1', 'M5.1', 'M7.1', 'M8.1', 'M9.1',
        'P1.1', 'P2.1', 'P3.1', 'P4.1', 'P5.1',
        'B1.1', 'B2.1', 'B3.1', 'B4.1',
        'E1.1', 'E2.1', 'E3.1', 'E4.1',
        'A1.1', 'A2.1', 'A3.1', 'A4.1', 'A5.1',
        'S1.1', 'S2.1', 'S3.1', 'S4.1',
        'L1.1', 'L2.1', 'L3.1',
        'C1.1', 'C2.1', 'C3.1', 'C4.1',
        'T1.1', 'T2.1', 'T3.1',
        'D1.1', 'D2.1', 'D3.1', 'D4.1',
        'ID1.1', 'ID2.1', 'ID3.1',
        'U1.1', 'U2.1', 'U3.1',
    ]
    write_keys = extract_step_keys(WRITING_MATERIAL)
    review_keys = extract_step_keys(REVIEW_MATERIAL)
    for aid in sample_anchors:
        assert aid in anchor_routes, aid
        stage = anchor_routes[aid]
        src = {'profile': 'anchor', 'key': aid, 'file_sha256': _ANCHOR_TABLE_SHA256}
        assert route_method(src)['stages'][0] == stage
        assert route_method({**src, 'file_sha256': '0' * 64})['stages'] == ['anchor_design']
        assert aid in write_keys, f'{aid} missing from WRITING_MATERIAL'
        assert aid in review_keys, f'{aid} missing from REVIEW_MATERIAL'


def test_network_and_type_in_step_routing_is_pinned_to_active_sha256() -> None:
    dyn = {'profile': 'dynamic_relation', 'key': 'C00002', 'file_sha256': _DYNAMIC_NETWORK_SHA256}
    assert route_method(dyn)['stages'] == ['action_design']
    assert route_method({**dyn, 'file_sha256': '0' * 64})['stages'] == ['state_transition']

    stat = {'profile': 'static_relation', 'key': '58.3_第三人称有限 / 59.1_主角POV / 转化',
            'file_sha256': _STATIC_NETWORK_SHA256}
    assert 'scene_design' in route_method(stat)['stages']
    assert 'static_relations' not in route_method(stat)['stages']
    assert route_method({**stat, 'file_sha256': '0' * 64})['stages'] == ['static_relations', 'plot_design']

    hyb = {'profile': 'type_identity', 'key': 'HYBRID_CHUANYUE_LISHI', 'file_sha256': _TYPE_SYSTEM_SHA256}
    assert route_method(hyb)['stages'][0] == 'type_adaptation'

    lib = {'profile': 'plot', 'key': '板块48 章节结构#结尾规则', 'file_sha256': _LIBRARY_SHA256}
    assert 'scene_design' in route_method(lib)['stages']


def test_story_context_attaches_same_pov_predecessor_prose_without_cross_pov_leakage(tmp_path: Path) -> None:
    with Store(tmp_path, create=True, test_mode=True) as store:
        s1, s2, s3 = seed_book(store, 3)
        store.add_brief('寒潮封港查验封条', '受限第三人称')
        approvals = []
        for ident, kind, body in [
            ('yan', 'character', {'name': '沈砚', 'role': '主角', 'want': '查封条', 'visibility': 'public'}),
            ('lu', 'character', {'name': '陆昭', 'role': '搭档', 'want': '护账册', 'visibility': 'public'}),
            ('sc-1', 'scene', {'title': '场一', 'goal': '摸到刻痕', 'pov': 'yan',
                               'characters': ['yan'], 'story_time': '1', 'visibility': 'public'}),
            ('sc-2', 'scene', {'title': '场二', 'goal': '复核封泥', 'pov': 'yan',
                               'characters': ['yan'], 'story_time': '2', 'visibility': 'public'}),
            ('sc-3', 'scene', {'title': '场三', 'goal': '陆昭独处', 'pov': 'lu',
                               'characters': ['lu'], 'story_time': '3', 'visibility': 'public'}),
        ]:
            ref = add_card(store, ident, kind, body)
            dec = decide_card(store, ref, 'approved', '确认')
            approvals.append({**asdict(ref), 'decision_id': dec.id})

        for scene_obj, card_id, order in [(s1, 'sc-1', 1), (s2, 'sc-2', 2), (s3, 'sc-3', 3)]:
            store.connection.execute(
                'UPDATE scenes SET card_json=? WHERE id=?',
                (json.dumps({'story': {'story_order': order, 'scene_ref': {'card_id': card_id, 'version': 1}}}), scene_obj.id),
            )
        store.connection.commit()
        adopt_story(store, baseline(card_refs=approvals, facts=[]), {})

        d1 = draft_for(store, s1.id, '沈砚吹熄油灯，指腹在井栏第七道刻痕上停住。SAME_POV_TAIL_MARKER')
        head = current_head(store)
        p1 = proposal(store, head, d1, [
            operation(d1, time=1, order=(1, 1, 0), holder='yan', claim='fact',
                      entity='well', predicate='mark', new='第七道刻痕'),
        ])
        accept_batch(store, [p1], head, 'accept-s1')

        head = current_head(store)
        work_s2 = build_story_context(
            store, s2.id, StoryScope('main', head.revision, 2, {'card_id': 'sc-2', 'version': 1}), 20000
        )
        sources_s2 = {item['source']: item['text'] for item in work_s2.package['items']}
        assert f'previous:{s1.id}' in sources_s2
        assert 'SAME_POV_TAIL_MARKER' in sources_s2[f'previous:{s1.id}']
        assert 'quote' in sources_s2['prior-evidence']

        # Accept s2 in yan POV with private monologue, then verify s3 (lu POV) does NOT receive s2 raw prose
        d2 = draft_for(store, s2.id, '沈砚把残封收入内袋，暗忖绝不能让旁人知晓。YAN_PRIVATE_PROSE_SECRET')
        p2 = proposal(store, head, d2, [])
        accept_batch(store, [p2], head, 'accept-s2')

        head = current_head(store)
        work_s3 = build_story_context(
            store, s3.id, StoryScope('main', head.revision, 3, {'card_id': 'sc-3', 'version': 1}), 20000
        )
        serialized_s3 = json.dumps(work_s3.package, ensure_ascii=False)
        assert f'previous:{s2.id}' not in serialized_s3
        assert 'YAN_PRIVATE_PROSE_SECRET' not in serialized_s3


def test_model_package_compacts_parent_material_work_audit_snapshots_without_mutating_frozen_package() -> None:
    raw_stage = {
        'stage': 'character_design',
        'task_id': 't-1',
        'sha256': 'a' * 64,
        'source_ids': ['src-1'],
        'inputs': {'world_design': {'sha256': 'b' * 64}},
        'products': {'members': [{'key': 'yan'}], '_uses': [], '_criteria': [{'huge_audit': 'x' * 5000}]},
        'semantic_contracts': [{'obligations': ['y' * 5000]}],
        'binding_reviews': [{'clauses': ['z' * 5000]}],
        'source_selection': {'queries': ['q' * 3000]},
    }
    pkg = {
        'scope': 'chapter',
        'parent_material_work': {
            'application': {'stage_uses': [{'stage': 'character_design'}]},
            'stages': [raw_stage],
            'work_plan': [],
        },
    }
    sent = model_package(pkg)
    sent_stage = sent['parent_material_work']['stages'][0]
    assert 'semantic_contracts' not in sent_stage
    assert 'binding_reviews' not in sent_stage
    assert 'source_selection' not in sent_stage
    assert '_criteria' not in sent_stage['products']
    assert sent_stage['products']['members'] == [{'key': 'yan'}]
    # Original frozen package remains untouched for parent integrity verification
    assert 'semantic_contracts' in pkg['parent_material_work']['stages'][0]
    assert '_criteria' in pkg['parent_material_work']['stages'][0]['products']

