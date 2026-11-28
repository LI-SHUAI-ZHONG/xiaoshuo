"""Tests for fast 4-track targeted corpus decomposition, stall fixes, and 4-step/unlocked wizard."""
from __future__ import annotations

import http.client
import json
import threading
import time
from types import SimpleNamespace

import pytest

from nw.llm.base import GenResult
from nw.production_methods.sources import MethodReader
from nw.studio.api import StudioService
from nw.studio.corpus_calls import _diagnose_raw_failure
from nw.studio.corpus_direct import (
    DEFAULT_TRACK_IDS,
    TARGETED_TRACKS,
    classify_story_units,
    estimate_targeted_calls,
    select_targeted_spans,
)
from nw.studio.corpus_index import source_units
from nw.studio.corpus_jobs import DECOMPOSE_MIN_TIMEOUT
from nw.studio.downstream_handoff import audit_downstream_handoff
from nw.studio.library import LibraryService
from nw.studio.library_util import encode
from nw.studio.production_inputs import freeze_wizard, governance
from nw.studio.server import create_studio_server
from nw.studio.wizard_setup import AUTO_ENFORCED_CAPABILITIES, auto_select_genre_preferences, setup_profile_for_types


WEB_NOVEL_WITH_BLURB = (
    '书籍信息\n\n书名：测试异骨录\n作者：测试作者\n连载状态：连载中\n字数：60.0 万字\n'
    '章节数：200 章\n书籍 ID：999999\n阅读量：12345\n最后更新时间：2026-11-28 05:00\n\n'
    '【简介】\n世间生灵体生异骨，可铭刻灵法。\n\n————————————————\n\n'
    + '\n\n'.join(
        f'第{i}章 骨纹觉醒之夜{i}\n'
        f'林渊握紧腰间裂开半寸的青铜短刃，石阶下的执事沉声道：“凡入内院者，必以本命灵骨铭刻戒律，违者断脉逐出。”\n'
        f'众弟子鸦雀无声，唯有站在廊柱阴影里的赵无极冷笑一声，抬手亮出三道金纹令牌，逼迫林渊在三息之内交出残缺古骨。\n'
        f'林渊没有抬头，只盯着对方指节上未干的暗红朱砂，忽然把短刃横在自己腕脉上，低声反问：“执事可敢当众验一验赵师兄令牌背面的裂痕？”\n'
        f'话音未落，大殿铜钟突鸣三声，原本沉寂的古骨在林渊掌心骤然灼烫，照出赵无极袖口藏着的一角禁符。'
        for i in range(1, 11)
    )
    + '\n\n上架感言\n感谢各位书友支持，求订阅求月票！\n'
)


class FakeTargetedProvider:
    name = 'openai_compat'

    def __init__(self, *, fail_first_timeout: bool = False) -> None:
        self.fail_first_timeout = fail_first_timeout
        self.calls: list[dict] = []

    def generate(self, messages: list[dict], **params) -> GenResult:
        idx = len(self.calls) + 1
        user_payload = json.loads(messages[-1]['content'])
        self.calls.append({'idx': idx, 'payload': user_payload, 'params': params})
        if self.fail_first_timeout and idx == 1:
            return GenResult(
                text='',
                finish_reason='error',
                usage={},
                request_id=None,
                raw={'error_type': 'URLError', 'network_failure': 'timeout'},
            )
        if 'source_text' in user_payload:
            src = user_payload['source_text']
            q_world = '凡入内院者，必以本命灵骨铭刻戒律，违者断脉逐出。'
            q_char = '林渊没有抬头，只盯着对方指节上未干的暗红朱砂'
            q_hook = '大殿铜钟突鸣三声，原本沉寂的古骨在林渊掌心骤然灼烫，照出赵无极袖口藏着的一角禁符。'
            assert q_world in src and q_char in src and q_hook in src
            reply = {
                'chapter_summary': f"第{user_payload['chapter_index']}章立下宗门戒律并借反问揭露对手禁符",
                'key_characters': [
                    {'name': '林渊', 'role': '处于劣势却以反证破局的主角', 'quote': q_char},
                    {'name': '赵无极', 'role': '持牌压迫却暗藏破绽的对立者', 'quote': '唯有站在廊柱阴影里的赵无极冷笑一声'},
                ],
                'observations': [
                    {
                        'track': 'genre_world_rules',
                        'title': '准入戒律绑定身体代价',
                        'what_happened': '宗门准入硬性要求铭刻戒律，违背即承受不可逆的断脉驱逐代价。',
                        'function_effect': '让主角无法用廉价方式逃避公开规矩，只能利用规则条款反制对手。',
                        'reusable_pattern': '在开篇确立一项带不可逆生理或身份代价的组织铁律，迫使冲突双方都在规则缝隙里博弈。',
                        'boundary': '适用于宗门/制度压迫明显的幻想或职场题材，不适用于无硬规则束缚的轻松日常。',
                        'quotes': [q_world],
                    },
                    {
                        'track': 'character_conflict',
                        'title': '劣势方以细节观察反将一军',
                        'what_happened': '主角在权力压迫下克制不抬头，锁定对手指节异常痕迹并拿自身风险换取公开验物机会。',
                        'function_effect': '瞬间立住主角冷静隐忍且敢赌命的辨识度，避免口嗨式嘴炮反击。',
                        'reusable_pattern': '让弱势主角通过单一细节发现强势对手的软肋，以付出可见风险作为公开对质的筹码。',
                        'boundary': '需要前文给出可观察的物理破绽，禁止主角凭空猜心。',
                        'quotes': [q_char],
                    },
                    {
                        'track': 'opening_plot_hooks',
                        'title': '当场反问叠加异象留章末悬念',
                        'what_happened': '主角提出验物反问后，器物异象意外照出对手隐藏禁符，在真相揭晓前戛然而止。',
                        'function_effect': '同时回应本章危机并抛出“对手藏禁符意图何在”的新追读问题。',
                        'reusable_pattern': '在章末冲突尚未口头吵完时，用客观物证异象曝光更高层秘密，自然切章。',
                        'boundary': '异象触发须与前文设定器物属性呼应，不可无因机械降神。',
                        'quotes': [q_hook],
                    },
                    {
                        'track': 'scene_prose_craft',
                        'title': '受限视角微动作替代心理直述',
                        'what_happened': '不写主角内心紧张，而是写不抬头、盯住指节朱砂和横刃腕脉的具象动作。',
                        'function_effect': '在严格受限视角下让读者直观感到压迫与决绝，杜绝“他心想”式说明文。',
                        'reusable_pattern': '高压对峙场禁用抽象情绪总结，改用视线落点、器物抓握和反常小细节传递人物判断。',
                        'boundary': '仅限当前 POV 可亲眼观察到的微动作，不得越界描写对方未露出的内心。',
                        'quotes': [q_char],
                    },
                ],
            }
            return GenResult(encode(reply), 'complete', {'total_tokens': 500}, f'req-{idx}', {'id': f'req-{idx}'})

        # Synthesis phase
        obs = user_payload['observations']
        by_track: dict[str, list[str]] = {}
        for row in obs:
            by_track.setdefault(row['track'], []).append(row['obs_id'])
        synth = {
            'book_overview': {
                'central_question': '弱势主角如何在严苛组织铁律下借规则与细节反杀强敌。',
                'mainline': '开篇借公开规则对质曝光对手隐秘，逐步卷入更大势力暗流。',
                'character_arcs': '冷静隐忍的主角借高风险反证打破底层压迫格局。',
                'information_payoffs': '章末借客观物证异象曝光暗线秘密并制造下章追读钩子。',
                'structure': '开篇快节奏入场、规则压迫与细节破局紧密交替。',
            },
            'methods': [
                {
                    'track': 'genre_world_rules',
                    'task': 'world_rules',
                    'title': '不可逆代价组织铁律博弈法',
                    'obs_ids': by_track['genre_world_rules'][:2],
                    'applicability': ['玄幻或仙侠宗门入场冲突', '需要借外部制度限制角色选择的开篇'],
                    'non_applicability': ['无硬性制度约束的纯日常轻松文'],
                    'operation': '在世界卡明确一条带不可逆生理或身份惩罚的准入铁律，写明执行机构与违规代价，并让后续行动利用规则核验条款反制强敌。',
                    'output_desc': '带执行主体、适用条件与不可逆惩罚的世界规则卡',
                    'acceptance_check': '正文须明确呈现规则条款及其对人物当下选择的真实限制',
                    'evidence_required': '正文包含规则宣告与角色依据规则做出受限抉择的具体段落',
                },
                {
                    'track': 'character_conflict',
                    'task': 'character_arc',
                    'title': '弱势方高风险反证立人设法',
                    'obs_ids': by_track['character_conflict'][:2],
                    'applicability': ['权力不对等对峙中快速立住主角冷静与果决'],
                    'non_applicability': ['主角已占绝对武力碾压的爽局'],
                    'operation': '人物卡写明主角在高压下先观察物理细节再出手的习惯，并设定必须付出可见风险才能撬动公审的博弈底线。',
                    'output_desc': '含高压行为习惯、独立目标与反证筹码的人物设计卡',
                    'acceptance_check': '正文须通过具体细节观察与付代价动作而非空话立住角色',
                    'evidence_required': '正文呈现角色捕捉物理破绽并承担风险反击的连续动作',
                },
                {
                    'track': 'opening_plot_hooks',
                    'task': 'hook',
                    'title': '客观物证异象章末翻面留钩法',
                    'obs_ids': by_track['opening_plot_hooks'][:2],
                    'applicability': ['开篇黄金三章及关键对峙章末制造强追读悬念'],
                    'non_applicability': ['需要彻底舒缓收尾的卷末休整轻章'],
                    'operation': '在章末对质高点不直接给出最终胜负，而是借前文伏笔器物触发客观异常，暴露对手更深一层隐秘作为下章开场问题。',
                    'output_desc': '明确读者情绪转向与章末悬念问题的 reader_plan 节拍',
                    'acceptance_check': '正文结尾须落在一个具体可追问的新发现上而非空喊悬念',
                    'evidence_required': '章末出现可引用的物证异常与暴露新疑点的正文原句',
                },
                {
                    'track': 'scene_prose_craft',
                    'task': 'narration',
                    'title': '受限视角微动作与视线落点写法',
                    'obs_ids': by_track['scene_prose_craft'][:2],
                    'applicability': ['高压对峙或隐秘试探场景的受限 POV 表达'],
                    'non_applicability': ['需要上帝视角宏观概述的大场面战报'],
                    'operation': '表达指导明确本场禁用“他心想/意识到”，改用 POV 视线锁定对方身体微异常与自身器物动作呈现心理博弈。',
                    'output_desc': '指定视线落点、动作节拍与禁直述心理的表达指导条目',
                    'acceptance_check': '正文严守受限视角，用具体视觉与动作描写传递紧张判断',
                    'evidence_required': '正文包含至少两处 POV 可见微动作或物件细节原句',
                },
                {
                    'track': 'scene_prose_craft',
                    'task': 'pacing',
                    'title': '静默蓄压后骤然鸣响提速法',
                    'obs_ids': by_track['scene_prose_craft'][:1],
                    'applicability': ['对峙场景从压抑铺垫切换到爆发转折'],
                    'non_applicability': ['全程平缓叙事的日常过渡场景'],
                    'operation': '前半段用克制长句与静默环境积蓄压迫感，在反问落地瞬间以突发声响与短句引爆局势转向。',
                    'output_desc': '包含蓄压→触发→骤然提速三拍节奏控制的表达指导',
                    'acceptance_check': '正文呈现由慢到快的清晰句式与声音节奏转折',
                    'evidence_required': '正文包含蓄压描写与突发声响转折的相邻段落',
                },
            ],
        }
        return GenResult(encode(synth), 'complete', {'total_tokens': 700}, f'req-{idx}', {'id': f'req-{idx}'})


def _wait_corpus_job(library: LibraryService, book_id: str, job_id: str, timeout: float = 15.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = library.get_corpus_job(book_id, job_id)
        if job['status'] not in ('pending', 'running'):
            return job
        time.sleep(0.05)
    raise AssertionError('Targeted corpus job timed out')


def test_paratext_filtering_and_smart_sampling_skip_blurb_and_author_notes():
    units = source_units(WEB_NOVEL_WITH_BLURB)
    story, paratext = classify_story_units(units, WEB_NOVEL_WITH_BLURB)
    assert len(story) == 10
    assert len(paratext) >= 1  # Book metadata/blurb chunk skipped!
    assert all('书籍信息' not in WEB_NOVEL_WITH_BLURB[u['start']:u['end']] for u in story)

    spans, skipped, total = select_targeted_spans(units, WEB_NOVEL_WITH_BLURB, sample_mode='key_chapters', sample_count=5)
    assert total == 10 and len(spans) == 5 and len(skipped) >= 1
    # Always includes Golden-3 opening chapters (1, 2, 3) plus later turning chapters
    indices = [s['story_chapter_index'] for s in spans]
    assert indices[:3] == [1, 2, 3] and indices[-1] == 10

    est = estimate_targeted_calls(units, WEB_NOVEL_WITH_BLURB, sample_mode='key_chapters', sample_count=5)
    assert est['story_chapters'] == 10
    assert est['skipped_paratext_count'] >= 1
    assert est['minimum_targeted_calls'] == 6  # 5 extract + 1 synthesize


def test_failure_diagnosis_reports_clear_chinese_timeout_and_http_causes():
    msg, transient = _diagnose_raw_failure({
        'finish_reason': 'error', 'raw': {'error_type': 'URLError', 'network_failure': 'timeout'},
    })
    assert '超时' in msg and transient is True

    msg429, transient429 = _diagnose_raw_failure({'finish_reason': 'error', 'raw': {'http_status': 429}})
    assert '429' in msg429 and transient429 is True

    msg401, transient401 = _diagnose_raw_failure({'finish_reason': 'error', 'raw': {'http_status': 401}})
    assert '401' in msg401 and transient401 is False


def test_targeted_decomposition_retries_timeout_and_auto_publishes_verified_methods(tmp_path, monkeypatch):
    lib = LibraryService(tmp_path / 'ws')
    book = lib.import_book({'title': '测试异骨录', 'filename': 'yigu.txt', 'text': WEB_NOVEL_WITH_BLURB})
    lib.review_book(book['id'], {'decision': 'approve', 'types': ['GENRE_XUANHUAN'], 'grade': 'A', 'decompose': True})

    provider = FakeTargetedProvider(fail_first_timeout=True)
    fake_cfg = SimpleNamespace(
        provider='openai_compat', model='gpt-6.2-sol', base_url='https://api.example.test/v1',
        params={'temperature': 0.2}, timeout=DECOMPOSE_MIN_TIMEOUT,
    )
    monkeypatch.setattr(lib, '_corpus_runtime', lambda: (fake_cfg, provider))

    started = lib.start_corpus_job(book['id'], {
        'kind': 'targeted',
        'options': {
            'extent': 'complete',
            'note': '测试完整正文章节',
            'sample_mode': 'key_chapters',
            'sample_count': 4,
            'tracks': list(DEFAULT_TRACK_IDS),
            'auto_approve': True,
            'max_calls': 12,
        },
    })
    finished = _wait_corpus_job(lib, book['id'], started['id'])
    assert finished['status'] == 'completed', finished['error']
    # Attempt 1 timed out and auto-retried seamlessly -> 1 failed + 4 extract + 1 synthesize = 6 calls
    assert finished['calls_used'] == 6
    assert finished['progress']['published_version'] == 1
    assert len(finished['progress']['published_methods']) == 5

    # Structure and all 5 methods are immediately live, approved, and receivable by downstream steps!
    corpus = lib.get_corpus(book['id'])
    assert corpus['available'] is True and corpus['approved_version'] == 1
    assert corpus['coverage']['targeted_mode'] is True

    reader = MethodReader(lib.workspace)
    live_methods = reader.current_methods()
    assert len(live_methods) == 5
    world_methods = [m for m in live_methods if 'world_rules' in m['body']['tasks']]
    assert len(world_methods) == 1
    assert reader.world_source(world_methods[0], ['GENRE_XUANHUAN']) is not None

    audit = audit_downstream_handoff(lib, types=['GENRE_XUANHUAN'], book_id=book['id'])
    assert audit['summary']['receivable_methods'] == 5
    assert audit['summary']['book_world_ready'] is True
    assert lib.get_staging(book['id'])['status'] == 'archived'


def test_wizard_setup_profile_excludes_mandatory_character_and_world_basics(tmp_path):
    lib = LibraryService(tmp_path / 'ws')
    profile = setup_profile_for_types(['GENRE_DUSHI'], library=lib)
    assert len(profile['auto_enforced_capabilities']) == len(AUTO_ENFORCED_CAPABILITIES)
    assert any('配角' in c['title'] for c in profile['auto_enforced_capabilities'])

    all_keys = {item['key'] for items in profile['sections'].values() for item in items}
    # Mandatory universal character/supporting-cast/relation/world-foundation items MUST NOT appear as manual options
    for forbidden_prefix in (
        'character.1.', 'character.2.', 'character.3.', 'character.4.',
        'character.121.', 'character.rel.',
        'world.31.', 'world.33.', 'world.34.', 'world.125.',
        'hook.123.', 'hook.block.45', 'hook.ev.',
        'narration.anc.', 'narration.expr.',
    ):
        assert not any(k.startswith(forbidden_prefix) for k in all_keys), f'Mandatory craft leaked into manual options: {forbidden_prefix}'

    # Real differentiating choices MUST be present flat inline
    assert 'structure.NARRATIVE_STRUCTURE_LINEAR' in all_keys
    assert 'hook.PLOT_MECHANISM_TRADE' in all_keys
    assert 'tone.TONE_LIGHT' in all_keys
    assert 'style.STYLE_REALISTIC' in all_keys
    # Special mechanisms exist cleanly and cross-genre ones are marked out_of_scope for pure urban
    special_by_id = {item['id']: item for item in profile['sections']['special_mechanisms']}
    assert special_by_id['PLOT_MECHANISM_BLOODLINE']['relevance'] == 'out_of_scope'
    assert special_by_id['PLOT_MECHANISM_DUNGEON']['relevance'] == 'out_of_scope'


def test_ai_auto_and_manual_builtin_enhanced_launch_without_corpus_deadlock(tmp_path):
    lib = LibraryService(tmp_path / 'ws')

    # 1) AI Auto with 0 corpus books MUST succeed in builtin_enhanced mode and auto-fill genre defaults
    auto_wizard = freeze_wizard({
        'genre_ids': ['GENRE_XUANHUAN'],
        'design_mode': 'auto',
        'creative_workflow': True,
        'method_policy_mode': 'builtin_enhanced',
        'planning_hierarchy': True,
    }, lib)
    assert auto_wizard['idea_origin'] == 'auto_brief'
    assert auto_wizard['method_policy_mode'] == 'builtin_enhanced'
    assert auto_wizard['structure_ids'] and auto_wizard['mechanism_ids']
    assert auto_wizard['tone_ids'] and auto_wizard['style_ids']
    assert 'production_methods' not in auto_wizard  # No deadlocked world_selection='ai' forced!
    plan = auto_wizard['creation_plan']
    assert plan['creative_workflow'] is True and len(plan['preferences']) >= 4
    gov = governance(auto_wizard, library=lib)
    assert gov['world_design']['creation_plan']['genre_scope']['preferred_resources']

    # 2) Manual creative_workflow with 0 corpus books MUST NOT force deadlocked world_selection='ai'
    manual_wizard = freeze_wizard({
        'title': '无参考直开测试',
        'idea': '底层少年靠半块裂骨撬动宗门规则。',
        'genre_ids': ['GENRE_XUANHUAN'],
        'design_mode': 'manual',
        'creative_workflow': True,
        'method_policy_mode': 'builtin_enhanced',
        'structure_ids': ['NARRATIVE_STRUCTURE_LEVEL'],
        'mechanism_ids': ['PLOT_MECHANISM_UPGRADE'],
        'tone_ids': ['TONE_EPIC'],
        'style_ids': ['STYLE_ACTION'],
    }, lib)
    assert 'production_methods' not in manual_wizard
    assert manual_wizard['creation_plan']['creative_workflow'] is True

    # 3) Legacy strict_corpus auto mode STILL enforces AUTO_RECOMMENDATIONS_MISSING when 0 methods exist
    with pytest.raises(ValueError, match='AUTO_RECOMMENDATIONS_MISSING'):
        freeze_wizard({
            'genre_ids': ['GENRE_XUANHUAN'],
            'design_mode': 'auto',
            'auto_recommendations': True,
            'method_policy_mode': 'strict_corpus',
        }, lib)


def test_ai_auto_builtin_enhanced_auto_attaches_targeted_methods_when_available(tmp_path, monkeypatch):
    lib = LibraryService(tmp_path / 'ws')
    book = lib.import_book({'title': '测试异骨录', 'filename': 'yigu.txt', 'text': WEB_NOVEL_WITH_BLURB})
    lib.review_book(book['id'], {'decision': 'approve', 'types': ['GENRE_XUANHUAN'], 'grade': 'A', 'decompose': True})
    provider = FakeTargetedProvider()
    fake_cfg = SimpleNamespace(
        provider='openai_compat', model='gpt-6.2-sol', base_url='https://api.example.test/v1',
        params={'temperature': 0.2}, timeout=DECOMPOSE_MIN_TIMEOUT,
    )
    monkeypatch.setattr(lib, '_corpus_runtime', lambda: (fake_cfg, provider))
    job = lib.start_corpus_job(book['id'], {
        'kind': 'targeted',
        'options': {'extent': 'complete', 'note': '完整文本', 'sample_count': 3, 'auto_approve': True, 'max_calls': 10},
    })
    assert _wait_corpus_job(lib, book['id'], job['id'])['status'] == 'completed'

    # Now AI Auto automatically attaches those 5 verified targeted methods without failing on missing 2 boards!
    auto_wizard = freeze_wizard({
        'genre_ids': ['GENRE_XUANHUAN'],
        'design_mode': 'auto',
        'creative_workflow': True,
        'method_policy_mode': 'builtin_enhanced',
        'planning_hierarchy': True,
    }, lib)
    pm = auto_wizard['production_methods']
    assert pm['recommendation_mode'] == 'auto'
    assert pm['world_selection'] == 'ai'
    assert len(pm['preferred_methods']) == 5
    assert 'world_rules' in pm['tasks'] and 'hook' in pm['tasks']


def test_http_endpoints_serve_setup_profile_and_targeted_estimate(tmp_path):
    studio = StudioService(tmp_path / 'ws', config_path=tmp_path / 'missing.toml')
    server = create_studio_server(studio, port=0)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()

    def req(method: str, path: str, body: dict | None = None):
        conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=10)
        conn.request(method, path, json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None,
                     {'Content-Type': 'application/json'})
        resp = conn.getresponse()
        raw = resp.read().decode('utf-8')
        conn.close()
        return resp.status, json.loads(raw)

    try:
        st, prof = req('GET', '/api/wizard/setup-profile?types=GENRE_XUANHUAN')
        assert st == 200 and prof['version'] == 2
        assert len(prof['auto_enforced_capabilities']) == 4
        assert prof['ai_auto_defaults']['structure_ids']

        st, cat = req('GET', '/api/corpus/catalog')
        assert st == 200 and len(cat['targeted_tracks']) == 4

        book = server.library.import_book({'title': '测试异骨录', 'filename': 'yigu.txt', 'text': WEB_NOVEL_WITH_BLURB})
        server.library.review_book(book['id'], {'decision': 'approve', 'types': ['GENRE_XUANHUAN'], 'grade': 'A', 'decompose': True})
        st, est = req('POST', f"/api/staging/{book['id']}/corpus/estimate", {'kind': 'targeted', 'sample_count': 4})
        assert st == 200 and est['targeted']['story_chapters'] == 10
        assert est['targeted']['skipped_paratext_count'] >= 1
        assert est['targeted']['minimum_targeted_calls'] == 5
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
