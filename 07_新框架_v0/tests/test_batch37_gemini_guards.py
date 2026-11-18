"""Tests for Batch 37: Gemini-strength guards (character voice/OOC, foreshadow tracking, multi-character ensemble, plot/scene quality)."""
from __future__ import annotations

from pathlib import Path
import pytest

from nw.materials.phase_routes import REQUIRES
from nw.materials.step_guard import (
    build_continuity_ledger,
    build_multi_character_coordination,
    validate_cross_step_consistency,
)
from nw.studio import StudioService


def _sample_products() -> dict:
    return {
        'type_selection': {
            'products': {
                'selection': [{'id': 'TYPE_INSTITUTIONAL_SUSPENSE', 'label': '制度悬疑'}],
                'boundaries': ['单视角受限知情，禁全知上帝视角'],
            }
        },
        'world_design': {
            'products': {
                'members': [
                    {
                        'key': 'world_tide_lock',
                        'kind': 'world',
                        'body': {
                            'title': '子时封港铁律',
                            'rule': '子时涨潮后暗渠水闸彻底锁死，私开者留铜印痕',
                            'limits': '无掌印副牌无法从内侧开启',
                            'visibility': 'holders',
                            'holders': ['char_yan'],
                        },
                    }
                ],
                'limitations': ['夜雨视线受阻'],
                'unknowns': ['前任掌印失踪真相'],
            }
        },
        'character_design': {
            'products': {
                'members': [
                    {
                        'key': 'char_yan',
                        'kind': 'character',
                        'body': {
                            'name': '沈砚',
                            'role': '主角',
                            'want': '查明旧印掉包真相',
                            'voice': '语速偏慢、停顿冷峻、少用修饰词',
                            'behavior': '遇压先核查器物痕迹再开口质询',
                            'boundaries': '绝不伪造卷宗构陷无辜',
                            'change_conditions': '唯有亲见师门亲笔密令铁证才会动摇师徒信任',
                            'visibility': 'public',
                        },
                    },
                    {
                        'key': 'char_lu',
                        'kind': 'character',
                        'body': {
                            'name': '陆巡检',
                            'role': '重要配角',
                            'want': '保住巡检司辖区体面',
                            'voice': '官腔急促、习惯反问打断',
                            'behavior': '好面子但畏惧上峰追责',
                            'change_conditions': '辖区命案牵连自身乌纱时被迫吐露实情',
                            'visibility': 'public',
                        },
                    },
                    {
                        'key': 'archive_statue',
                        'kind': 'character',
                        'body': {
                            'name': '镇库石兽',
                            'role': '机关陈设',
                            'want': '无',
                            'visibility': 'public',
                        },
                    },
                ],
                'states': [{'entity': 'char_yan', 'state': {'hand': '完好'}, 'status': 'candidate'}],
                'capabilities': [
                    {'entity': 'char_yan', 'can_act': True, 'abilities': ['勘验印痕'], 'basis': '案牍出身', 'limits': ['不擅重兵刃']},
                    {'entity': 'char_lu', 'can_act': True, 'abilities': ['调阅巡防簿'], 'basis': '巡检职权', 'limits': ['无权入内库']},
                    {'entity': 'archive_statue', 'can_act': False, 'abilities': [], 'basis': '死物陈设', 'limits': ['不可行动或开口']},
                ],
            }
        },
        'static_relations': {
            'products': {
                'relations': [
                    {
                        'id': 'rel_yan_lu',
                        'source': 'char_yan',
                        'target': 'char_lu',
                        'relation': '同僚互相试探且权责互卡',
                        'condition': '未拿到实据前维持表面客套',
                    }
                ],
                'requirements': [],
            }
        },
        'plot_design': {
            'products': {
                'promise_plan': [
                    {
                        'id': 'prom_1',
                        'promise': 'prom_copper_seal',
                        'plant_event': 'ev_plant',
                        'payoff_event': 'ev_payoff',
                        'plant_chapter': 1,
                        'payoff_chapter': 3,
                        'payoff_window': {'min_offset': 1, 'max_offset': 2},
                        'setup': '封条背面残留半枚旧铜印',
                        'payoff': '核对内库旧档确认换印人身份',
                    },
                    {
                        'id': 'prom_2',
                        'promise': 'prom_missing_ledger',
                        'plant_event': 'ev_plant',
                        'payoff_event': None,
                        'plant_chapter': 1,
                        'payoff_chapter': None,
                        'payoff_window': {'min_offset': 1, 'max_offset': 2},
                        'setup': '戌时值守簿缺页三张',
                        'payoff': '找回残页还原入库时刻',
                    },
                    {
                        'id': 'prom_3',
                        'promise': 'prom_old_key',
                        'plant_event': 'ev_0',
                        'payoff_event': 'ev_0_done',
                        'status': 'paid_off',
                        'setup': '生锈暗锁',
                        'payoff': '已开启',
                    },
                ],
                'reader_plan': [],
                'event_nodes': [
                    {
                        'id': 'ev_plant',
                        'actors': ['char_yan'],
                        'goal': '检查封条',
                        'setting': '外库门口',
                        'obstacle': '夜雨昏暗',
                        'completion_condition': '发现半枚旧铜印',
                        'status': 'planned',
                    },
                    {
                        'id': 'ev_payoff',
                        'actors': ['char_yan', 'char_lu'],
                        'goal': '当面对质换印记录',
                        'setting': '值房',
                        'obstacle': '陆巡检推诿掩饰',
                        'completion_condition': '确认换印经手人',
                        'status': 'planned',
                    },
                ],
            }
        },
        'scene_design': {
            'products': {
                'members': [
                    {
                        'key': 'sc_confront',
                        'kind': 'scene',
                        'body': {
                            'title': '值房夜审',
                            'goal': '当面对质值守记录',
                            'pov': 'char_yan',
                            'characters': ['char_yan', 'char_lu'],
                            'character_goals': {'char_yan': '逼问缺页去向', 'char_lu': '撇清失职责任'},
                        },
                    }
                ],
                'chapters': [{'index': 4, 'card': None, 'scenes': [{'index': 1, 'card': 'sc_confront', 'story_order': 4}]}],
                'selected_events': [{'scene': 'sc_confront', 'event': 'ev_payoff'}],
                'selected_actions': [],
                'events': [],
            }
        },
    }


# ==================== Task 1: Character Voice & Consistency Guards ====================

def test_character_voice_guard_injected_across_mid_and_late_steps() -> None:
    products = _sample_products()
    for stage in ('event_design', 'action_design', 'scene_design', 'state_transition', 'anchor_design', 'expression_design', 'writing'):
        deps = list(REQUIRES.get(stage, ()))
        ledger = build_continuity_ledger(stage, products, deps, {})
        assert ledger is not None and 'character_voice_guard' in ledger
        profiles = {p['entity']: p for p in ledger['character_voice_guard']['profiles']}
        assert 'char_yan' in profiles and 'char_lu' in profiles
        assert 'archive_statue' not in profiles  # no voice/personality traits on inanimate prop
        assert '语速偏慢' in profiles['char_yan']['voice_traits']
        assert '唯有亲见师门亲笔密令铁证' in profiles['char_yan']['change_conditions']


def test_character_voice_drift_and_unmotivated_personality_shift_rejected() -> None:
    products = _sample_products()

    # 1. Unmotivated personality/stance shift in state_transition rejected
    with pytest.raises(ValueError, match='personality/stance change'):
        validate_cross_step_consistency(
            'state_transition',
            {
                'transitions': [
                    {
                        'scene': 'sc_confront',
                        'entity': 'char_yan',
                        'event': '无事件',
                        'action': '突然改变',
                        'before_state': {'stance': '坚守程序'},
                        'after_state': {'stance': '同流合污'},
                    }
                ]
            },
            products,
            {},
        )

    # Motivated stance shift with real event & action passes
    validate_cross_step_consistency(
        'state_transition',
        {
            'transitions': [
                {
                    'scene': 'sc_confront',
                    'entity': 'char_yan',
                    'event': 'ev_payoff',
                    'action': '查验师父亲笔密令原件后被迫重估旧案',
                    'before_state': {'stance': '笃信师门清白'},
                    'after_state': {'stance': '怀疑师门涉案'},
                }
            ]
        },
        products,
        {},
    )

    # 2. Unmotivated voice drift in expression_design / writing rejected
    with pytest.raises(ValueError, match='voice drifted'):
        validate_cross_step_consistency(
            'expression_design',
            {
                'dialogues': [
                    {
                        'scene': 'sc_confront',
                        'speaker': 'char_yan',
                        'voice_style': '嬉皮笑脸连珠炮',
                        'text': '哈哈这有什么大不了的！',
                    }
                ]
            },
            products,
            {},
        )

    # Voice change backed by an explicit trigger_event passes
    validate_cross_step_consistency(
        'expression_design',
        {
            'dialogues': [
                {
                    'scene': 'sc_confront',
                    'speaker': 'char_yan',
                    'voice_style': '吸入浓烟后嗓音沙哑低哑',
                    'trigger_event': 'ev_fire_smoke',
                    'text': '把账册拿出来。',
                }
            ]
        },
        products,
        {},
    )


def test_character_knowledge_boundary_violations_rejected() -> None:
    products = _sample_products()

    # char_lu is NOT in holders of world_tide_lock (holders=['char_yan'])
    with pytest.raises(ValueError, match='knowledge boundary'):
        validate_cross_step_consistency(
            'writing',
            {
                'scene': 'sc_confront',
                'dialogues': [
                    {
                        'speaker': 'char_lu',
                        'references_restricted': ['world_tide_lock'],
                        'text': '我早知道子时涨潮水闸会留铜印痕！',
                    }
                ],
            },
            products,
            {},
        )

    # Writing POV=char_lu leaking holders-restricted rule text verbatim
    with pytest.raises(ValueError, match='leaks restricted card'):
        validate_cross_step_consistency(
            'writing',
            {
                'pov': 'char_lu',
                'text': '陆巡检心里清楚：子时涨潮后暗渠水闸彻底锁死，私开者留铜印痕。',
            },
            products,
            {},
        )

    # Writing POV=char_yan (who IS a holder) referencing the rule passes
    validate_cross_step_consistency(
        'writing',
        {
            'pov': 'char_yan',
            'text': '沈砚心知子时涨潮后暗渠水闸彻底锁死，私开者留铜印痕。',
        },
        products,
        {},
    )


# ==================== Task 2: Foreshadowing Tracking & Payoff Reminders ====================

def test_foreshadow_reminder_three_states_due_payoff_and_overdue_warnings() -> None:
    products = _sample_products()
    # Chapter is 4 (from scene_design.chapters), selected event is ev_payoff:
    # - prom_copper_seal: payoff_event == 'ev_payoff' -> due_this_scene, AND plant_chapter=1, window max=2, ch=4 (elapsed 3 > 2) -> overdue!
    # - prom_missing_ledger: plant_chapter=1, window max=2, ch=4 -> still_open + overdue!
    # - prom_old_key: status == 'paid_off' -> counted in paid_off, excluded from open/due
    ledger = build_continuity_ledger(
        'writing',
        products,
        [],
        {'current_scene': 'sc_confront', 'hinted_promises': ['prom_missing_ledger']},
    )
    assert ledger is not None and 'foreshadow_reminder' in ledger
    rem = ledger['foreshadow_reminder']
    assert rem['lifecycle_counts'] == {'planted': 1, 'hinted': 1, 'paid_off': 1}
    assert len(rem['due_this_scene']) == 1
    assert rem['due_this_scene'][0]['promise'] == 'prom_copper_seal'
    assert 'prom_missing_ledger' in rem['still_open']
    overdue_ids = {w['promise'] for w in rem['overdue_warnings']}
    assert 'prom_missing_ledger' in overdue_ids


def test_writing_foreshadow_due_enforcement_and_contradiction_guard() -> None:
    products = _sample_products()

    # 1. Due promise dropped (neither resolved nor deferred) -> rejected
    with pytest.raises(ValueError, match='due foreshadowing promise prom_copper_seal'):
        validate_cross_step_consistency(
            'writing',
            {'text': '两人只寒暄了几句便各自散去。', 'resolved_promises': []},
            products,
            {'current_scene': 'sc_confront'},
        )

    # 2. Due promise explicitly deferred -> passes
    validate_cross_step_consistency(
        'writing',
        {'text': '值房突生火情，查档被迫中断。', 'resolved_promises': [], 'deferred_promises': ['prom_copper_seal']},
        products,
        {'current_scene': 'sc_confront'},
    )

    # 3. Newly planted promise without plant_scene -> rejected
    with pytest.raises(ValueError, match='requires promise ID and plant_scene'):
        validate_cross_step_consistency(
            'writing',
            {'planted_promises': [{'promise': 'prom_new_dagger', 'setup': '袖中短匕'}]},
            products,
            {},
        )

    # 4. Contradicting established promise setup -> rejected
    with pytest.raises(ValueError, match='contradicts established setup'):
        validate_cross_step_consistency(
            'writing',
            {
                'planted_promises': [
                    {'promise': 'prom_copper_seal', 'plant_scene': 'sc_confront', 'setup': '封条背面完全空白无印痕'}
                ]
            },
            products,
            {},
        )


# ==================== Task 3: Multi-Character Ensemble Coordination ====================

def test_multi_character_coordination_isolates_voices_relations_and_asymmetry() -> None:
    products = _sample_products()
    accepted_state = [
        {'entity_id': 'ledger_01', 'predicate': 'hidden_spot', 'holder': 'char_yan', 'claim': 'fact', 'value': '梁上暗格'},
    ]
    coord = build_multi_character_coordination('writing', products, {'accepted_state': accepted_state})
    assert coord is not None
    assert coord['active_characters'] == ['char_yan', 'char_lu']
    assert coord['non_acting_entities'] == ['archive_statue']
    assert coord['inter_character_relations'][0]['pair'] == 'char_yan->char_lu'

    asym_items = {row['item']: row for row in coord['information_asymmetry']}
    assert 'world_tide_lock' in asym_items
    assert asym_items['world_tide_lock']['known_by'] == ['char_yan']
    assert asym_items['world_tide_lock']['hidden_from'] == ['char_lu']
    assert 'ledger_01.hidden_spot' in asym_items
    assert asym_items['ledger_01.hidden_spot']['hidden_from'] == ['char_lu']


def test_multi_character_non_actor_and_absent_speaker_rejected() -> None:
    products = _sample_products()

    # Inanimate / can_act=False entity speaking dialogue -> rejected
    with pytest.raises(ValueError, match='non-acting entity archive_statue'):
        validate_cross_step_consistency(
            'writing',
            {'scene': 'sc_confront', 'dialogues': [{'speaker': 'archive_statue', 'text': '我看见了凶手'}]},
            products,
            {},
        )

    # Extra character who is NOT in sc_confront participants speaking in sc_confront -> rejected
    products['character_design']['products']['members'].append(
        {'key': 'char_outsider', 'kind': 'character', 'body': {'name': '场外掌柜', 'role': '配角', 'want': '看热闹', 'visibility': 'public'}}
    )
    with pytest.raises(ValueError, match='not in scene sc_confront participants'):
        validate_cross_step_consistency(
            'writing',
            {'scene': 'sc_confront', 'dialogues': [{'speaker': 'char_outsider', 'text': '我也插一句嘴'}]},
            products,
            {},
        )


# ==================== Task 4: Plot & Scene Candidate Quality Guards ====================

def test_plot_design_quality_guards_reject_loops_non_actors_and_broken_causality() -> None:
    products = _sample_products()

    # 1. Non-acting entity assigned as event_node actor
    with pytest.raises(ValueError, match='non-acting entity archive_statue'):
        validate_cross_step_consistency(
            'plot_design',
            {
                'directions': [{'conflict': '封港', 'choice': '夜探', 'cost': '负伤', 'consequence': '拿到旧印'}],
                'event_nodes': [
                    {'id': 'n1', 'actors': ['archive_statue'], 'goal': '巡逻', 'setting': '外库', 'obstacle': '锁链', 'completion_condition': '抓人'}
                ],
                'promise_plan': [],
            },
            products,
            {},
        )

    # 2. Unclosed causal chain (consequence repeats conflict)
    with pytest.raises(ValueError, match='unclosed causal chain'):
        validate_cross_step_consistency(
            'plot_design',
            {
                'directions': [{'conflict': '守卫阻拦', 'choice': '强闯', 'cost': '暴露', 'consequence': '守卫阻拦'}],
                'event_nodes': [],
                'promise_plan': [],
            },
            products,
            {},
        )

    # 3. Duplicate event_nodes causing plot loop
    node_a = {'id': 'n1', 'actors': ['char_yan'], 'goal': '查封条', 'setting': '库门', 'obstacle': '铜丝', 'completion_condition': '见旧印'}
    node_b = {**node_a, 'id': 'n2'}
    with pytest.raises(ValueError, match='causes plot loop'):
        validate_cross_step_consistency('plot_design', {'event_nodes': [node_a, node_b]}, products, {})

    # 4. Promise payoff_event preceding plant_event in causal order
    n1 = {'id': 'ev_early', 'actors': ['char_yan'], 'goal': '入库', 'setting': '内库', 'obstacle': '暗锁', 'completion_condition': '开锁'}
    n2 = {'id': 'ev_late', 'actors': ['char_yan'], 'goal': '出库', 'setting': '外门', 'obstacle': '巡卫', 'completion_condition': '脱身'}
    with pytest.raises(ValueError, match='precedes plant_event'):
        validate_cross_step_consistency(
            'plot_design',
            {
                'event_nodes': [n1, n2],
                'promise_plan': [
                    {'promise': 'p_inv', 'plant_event': 'ev_late', 'payoff_event': 'ev_early', 'setup': '埋设', 'payoff': '回收'}
                ],
            },
            products,
            {},
        )


def test_scene_design_quality_guards_participants_handoff_and_timeline() -> None:
    products = _sample_products()

    # 1. Event on character absent from scene participants
    with pytest.raises(ValueError, match='not in scene sc_solo participants'):
        validate_cross_step_consistency(
            'scene_design',
            {
                'members': [{'key': 'sc_solo', 'kind': 'scene', 'body': {'pov': 'char_yan', 'characters': ['char_yan']}}],
                'chapters': [{'index': 1, 'card': None, 'scenes': [{'index': 1, 'card': 'sc_solo', 'story_order': 1}]}],
                'events': [{'id': 'e1', 'scene': 'sc_solo', 'entity': 'char_lu', 'trigger': '闯入', 'before_state': {'mood': 'calm'}}],
            },
            products,
            {},
        )

    # 2. Simultaneous conflicting locations at identical story_order
    with pytest.raises(ValueError, match='conflicting locations'):
        validate_cross_step_consistency(
            'scene_design',
            {
                'members': [
                    {'key': 's1', 'kind': 'scene', 'body': {'pov': 'char_yan', 'characters': ['char_yan'], 'location': '城北码头'}},
                    {'key': 's2', 'kind': 'scene', 'body': {'pov': 'char_lu', 'characters': ['char_yan', 'char_lu'], 'location': '城南地牢'}},
                ],
                'chapters': [
                    {
                        'index': 1,
                        'card': None,
                        'scenes': [
                            {'index': 1, 'card': 's1', 'story_order': 1},
                            {'index': 2, 'card': 's2', 'story_order': 1},
                        ],
                    }
                ],
                'events': [],
            },
            products,
            {},
        )

    # 3. Unexplained timeline jump (story_order 1 -> 6 without time transition cue)
    with pytest.raises(ValueError, match='unexplained timeline jump'):
        validate_cross_step_consistency(
            'scene_design',
            {
                'members': [
                    {'key': 's1', 'kind': 'scene', 'body': {'pov': 'char_yan', 'characters': ['char_yan'], 'entering_state': '站在门外'}},
                    {'key': 's2', 'kind': 'scene', 'body': {'pov': 'char_yan', 'characters': ['char_yan'], 'entering_state': '推门而入'}},
                ],
                'chapters': [
                    {
                        'index': 1,
                        'card': None,
                        'scenes': [
                            {'index': 1, 'card': 's1', 'story_order': 1},
                            {'index': 2, 'card': 's2', 'story_order': 6},
                        ],
                    }
                ],
                'events': [],
            },
            products,
            {},
        )

    # 4. Explained timeline jump ('三日后' in entering_state) passes cleanly
    validate_cross_step_consistency(
        'scene_design',
        {
            'members': [
                {'key': 's1', 'kind': 'scene', 'body': {'pov': 'char_yan', 'characters': ['char_yan'], 'entering_state': '站在门外'}},
                {'key': 's2', 'kind': 'scene', 'body': {'pov': 'char_yan', 'characters': ['char_yan'], 'entering_state': '三日后重返值房'}},
            ],
            'chapters': [
                {
                    'index': 1,
                    'card': None,
                    'scenes': [
                        {'index': 1, 'card': 's1', 'story_order': 1},
                        {'index': 2, 'card': 's2', 'story_order': 6},
                    ],
                }
            ],
            'events': [],
        },
        products,
        {},
    )

    # 5. Cross-scene state handoff contradiction without transition rejected
    with pytest.raises(ValueError, match='conflicts with prior scene state'):
        validate_cross_step_consistency(
            'scene_design',
            {
                'members': [
                    {'key': 's1', 'kind': 'scene', 'body': {'pov': 'char_yan', 'characters': ['char_yan']}},
                ],
                'chapters': [{'index': 2, 'card': None, 'scenes': [{'index': 1, 'card': 's1', 'story_order': 2}]}],
                'events': [{'id': 'e1', 'scene': 's1', 'entity': 'char_yan', 'trigger': '抬手', 'before_state': {'hand': '完好无损'}}],
            },
            products,
            {'prior_scene_states': {'char_yan': {'hand': '右手划伤包扎'}}},
        )


def test_studio_dry_run_exposes_batch37_guards(tmp_path: Path) -> None:
    svc = StudioService(workspace=tmp_path / 'ws', config_path=tmp_path / 'config.toml')
    bp = svc.pipeline_blueprint('chapter')
    scene_step = next(s for s in bp['design_steps'] if s['stage'] == 'scene_design')
    notes_blob = ' '.join(scene_step['anti_forgetting_guards'])
    assert 'character_voice_guard' in notes_blob
    assert 'foreshadow_reminder' in notes_blob
    assert 'multi_char_guard' in notes_blob

    sim = svc.simulate_step_materials(scope='chapter', stage='anchor_design')
    ledger = sim['continuity_ledger']
    assert ledger is not None
    assert 'character_voice_guard' in ledger
    assert 'foreshadow_reminder' in ledger
    assert ledger['foreshadow_reminder']['due_this_scene'][0]['promise'] == 'promise_watch'
    assert sim['multi_character_coordination'] is not None
    assert sim['multi_character_coordination']['active_characters'] == ['char_lin', 'char_informant']


# ==================== Additional Edge-Case & Branch Coverage Tests ====================

def test_approved_cards_character_voice_and_holders_fallback() -> None:
    approved = [
        {
            'card_id': 'canon_mentor',
            'kind': 'character',
            'body': {
                'name': '周案牍长',
                'role': '核心配角',
                'want': '封存旧档',
                'voice': '慢条斯理、句尾微扬',
                'visibility': 'holders',
                'holders': ['char_yan'],
            },
        }
    ]
    ledger = build_continuity_ledger('expression_design', {}, [], {'approved_cards': approved})
    assert ledger is not None and 'character_voice_guard' in ledger
    prof = ledger['character_voice_guard']['profiles'][0]
    assert prof['entity'] == 'canon_mentor'
    assert '慢条斯理' in prof['voice_traits']
    assert '仅限知情者:char_yan' in prof['knowledge_boundary']


def test_foreshadow_scene_index_overdue_and_resolved_override() -> None:
    products = {
        'plot_design': {
            'products': {
                'promise_plan': [
                    {
                        'id': 'p_ring',
                        'promise': 'prom_jade_ring',
                        'plant_event': 'e1',
                        'plant_scene_index': 1,
                        'setup': '断指扳指',
                        'payoff': '认出幕后主使',
                    },
                    {
                        'id': 'p_done',
                        'promise': 'prom_lamp_oil',
                        'plant_event': 'e1',
                        'setup': '桐油味',
                        'payoff': '识破纵火',
                    },
                ]
            }
        }
    }
    ledger = build_continuity_ledger(
        'writing',
        products,
        [],
        {
            'current_scene_index': 8,
            'foreshadow_overdue_limit': 5,
            'resolved_promises': ['prom_lamp_oil'],
        },
    )
    assert ledger is not None
    rem = ledger['foreshadow_reminder']
    assert rem['lifecycle_counts'] == {'planted': 1, 'hinted': 0, 'paid_off': 1}
    assert len(rem['overdue_warnings']) == 1
    assert rem['overdue_warnings'][0]['promise'] == 'prom_jade_ring'
    assert '连续7场未回收' in rem['overdue_warnings'][0]['reason']


def test_event_design_guards_reject_non_actors_placeholders_and_duplicate_candidates() -> None:
    products = _sample_products()
    with pytest.raises(ValueError, match='non-acting entity archive_statue'):
        validate_cross_step_consistency(
            'event_design',
            {'candidates': [{'id': 'c1', 'predecessor': 'ev_plant', 'event': '石兽追击', 'actors': ['archive_statue']}]},
            products,
            {},
        )

    with pytest.raises(ValueError, match='unfilled placeholder'):
        validate_cross_step_consistency(
            'event_design',
            {'candidates': [{'id': 'c1', 'predecessor': 'ev_plant', 'event': 'TODO', 'actors': ['char_yan']}]},
            products,
            {},
        )

    cand = {'id': 'c1', 'predecessor': 'ev_plant', 'event': '调取卷宗比对印泥', 'actors': ['char_yan']}
    with pytest.raises(ValueError, match='causes plot loop'):
        validate_cross_step_consistency(
            'event_design',
            {'candidates': [cand, {**cand, 'id': 'c2'}]},
            products,
            {},
        )


def test_plot_design_causal_cycle_missing_predecessor_and_completed_event_loop() -> None:
    products = _sample_products()
    n_a = {'id': 'na', 'predecessor': 'nb', 'actors': ['char_yan'], 'goal': '甲', 'setting': '库', 'obstacle': '锁', 'completion_condition': '开甲'}
    n_b = {'id': 'nb', 'predecessor': 'na', 'actors': ['char_yan'], 'goal': '乙', 'setting': '堂', 'obstacle': '卫', 'completion_condition': '开乙'}
    with pytest.raises(ValueError, match='causal cycle'):
        validate_cross_step_consistency('plot_design', {'event_nodes': [n_a, n_b]}, products, {})

    n_missing = {'id': 'nc', 'cause_event': 'ghost_ev', 'actors': ['char_yan'], 'goal': '丙', 'setting': '巷', 'obstacle': '雨', 'completion_condition': '达丙'}
    with pytest.raises(ValueError, match='missing cause_event'):
        validate_cross_step_consistency('plot_design', {'event_nodes': [n_missing]}, products, {})

    with pytest.raises(ValueError, match='repeats an already completed event'):
        validate_cross_step_consistency(
            'plot_design',
            {'event_nodes': [{'id': 'done_ev_1', 'actors': ['char_yan'], 'goal': '丁', 'setting': '港', 'obstacle': '雾', 'completion_condition': '达丁'}]},
            products,
            {'completed_events': ['done_ev_1']},
        )

    with pytest.raises(ValueError, match='cannot plant and pay off in the same event'):
        validate_cross_step_consistency(
            'plot_design',
            {
                'event_nodes': [],
                'promise_plan': [
                    {
                        'promise': 'p_same',
                        'plant_event': 'ev_same',
                        'payoff_event': 'ev_same',
                        'payoff_window': {'min_offset': 2, 'max_offset': 5},
                        'setup': '埋设',
                        'payoff': '回收',
                    }
                ],
            },
            products,
            {},
        )


def test_scene_design_story_time_mismatch_and_selected_event_actor_mismatch() -> None:
    products = _sample_products()

    # story_time='9' vs story_order=1 -> rejected
    with pytest.raises(ValueError, match='story_time .* conflicts with story_order'):
        validate_cross_step_consistency(
            'scene_design',
            {
                'members': [{'key': 's1', 'kind': 'scene', 'body': {'pov': 'char_yan', 'characters': ['char_yan'], 'story_time': '9'}}],
                'chapters': [{'index': 1, 'card': None, 'scenes': [{'index': 1, 'card': 's1', 'story_order': 1}]}],
                'events': [],
            },
            products,
            {},
        )

    # ev_payoff requires actors ['char_yan', 'char_lu'], but scene only includes ['char_yan'] -> rejected
    with pytest.raises(ValueError, match='selected event actor char_lu is absent'):
        validate_cross_step_consistency(
            'scene_design',
            {
                'members': [{'key': 's1', 'kind': 'scene', 'body': {'pov': 'char_yan', 'characters': ['char_yan']}}],
                'chapters': [{'index': 1, 'card': None, 'scenes': [{'index': 1, 'card': 's1', 'story_order': 1}]}],
                'selected_events': [{'scene': 's1', 'event': 'ev_payoff'}],
                'events': [],
            },
            products,
            {},
        )


def test_unmotivated_emotion_shift_and_forbidden_knowledge_token_rejected() -> None:
    products = _sample_products()
    with pytest.raises(ValueError, match='emotional shift lacks driving event'):
        validate_cross_step_consistency(
            'writing',
            {
                'scene': 'sc_confront',
                'dialogues': [{'speaker': 'char_yan', 'emotion_shift': '温和->暴怒拍案', 'trigger_event': '无', 'text': '混账！'}],
            },
            products,
            {},
        )

    with pytest.raises(ValueError, match='uttered forbidden knowledge'):
        validate_cross_step_consistency(
            'writing',
            {
                'scene': 'sc_confront',
                'dialogues': [{'speaker': 'char_lu', 'text': '密室口令是玄武七星！'}],
            },
            products,
            {'forbidden_knowledge': {'char_lu': ['玄武七星']}},
        )


def test_legacy_replay_bypasses_new_cross_step_guards() -> None:
    products = _sample_products()
    validate_cross_step_consistency(
        'state_transition',
        {'transitions': [{'scene': 's', 'entity': 'char_yan', 'after_state': {'hand': 'TODO'}}]},
        products,
        {'legacy_replay': True},
    )


def test_single_character_scene_omits_multi_char_guard() -> None:
    solo_products = {
        'character_design': {
            'products': {
                'members': [{'key': 'char_yan', 'kind': 'character', 'body': {'name': '沈砚', 'visibility': 'public'}}],
                'capabilities': [{'entity': 'char_yan', 'can_act': True}],
            }
        },
        'scene_design': {
            'products': {
                'members': [{'key': 's_solo', 'kind': 'scene', 'body': {'pov': 'char_yan', 'characters': ['char_yan']}}],
            }
        },
    }
    assert build_multi_character_coordination('writing', solo_products, {}) is None
