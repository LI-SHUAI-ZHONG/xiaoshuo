"""End-to-end tests for P0 writing-craft layering, POV-safe situation cards,
style reference anchors, anti-AI review/revise guardrails, and blind cold-read reader.
"""
from __future__ import annotations

from dataclasses import asdict
import json
import threading
from urllib.request import Request, urlopen

from nw.acceptance import accept_batch
from nw.cards import decide_card
from nw.cold_read import cold_read_summary, list_cold_reads, run_cold_read
from nw.config import Config
from nw.context.story import StoryScope, build_story_context
from nw.llm.base import GenResult
from nw.scene_messages import draft_messages
from nw.store import Store
from nw.story_models import StateHead
from nw.story_state import adopt_story
from nw.studio.api import StudioService
from nw.studio.server import create_studio_server
from nw.writing_craft import (
    ANTI_AI_REVIEW_GUIDE,
    ANTI_AI_REVISE_GUIDE,
    PRE_WRITE_CRAFT_GUIDE,
    load_style_reference,
    save_style_reference,
)
from story_fixture import baseline, draft_for, proposal, seed_book
from test_selection import add_card


class CapturingColdReadProvider:
    name = 'fake'

    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    def generate(self, messages, *, model='', params=None, **kwargs):
        self.calls.append(messages)
        user_obj = json.loads(messages[-1]['content'])
        is_arc = user_obj.get('mode') == 'consecutive_arc_cold_read'
        reply = {
            'hook_moment': {
                'found': True,
                'quote': '门闩刚落下，院外便响起一阵急促的敲门声。',
                'reason': '一上来就有紧迫感，让人想知道门外是谁。',
            },
            'skip_zones': [],
            'underwritten_spots': [
                {'location': '中段对峙', 'quote': '两人对视一眼便各自散开', 'reason': '交锋过程过快，缺少来回试探。'}
            ],
            'keep_reading': {
                'want_next': 'yes',
                'lingering_question': '门外那封无名信究竟是谁送来的？',
                'reason': '结尾悬念自然，想看主角怎么应对。',
            },
            'confusion_or_mismatch': [],
            'verdict_summary': '整体读感顺畅，开场抓人，但中段对手戏可以再展开半拍。',
        }
        if is_arc:
            reply['repetitive_beats'] = [
                {'chapters': [1, 2], 'pattern': '连续两章都用半夜敲门开场，节奏略重复。'}
            ]
        return GenResult(
            text=json.dumps(reply, ensure_ascii=False),
            finish_reason='complete',
            usage={'prompt_tokens': 100, 'completion_tokens': 120},
            request_id='cold-read-mock',
            raw={},
        )


def _seed_rich_story(tmp_path):
    store = Store(tmp_path, create=True, test_mode=True)
    [s1, s2] = seed_book(store, 2)
    scene1, scene2 = s1.id, s2.id
    store.add_brief('AUTHOR_SECRET_ENDING_PLAN：最终揭晓师父才是幕后黑手', '单章单POV；不准提前泄底')
    approvals = []
    cards = [
        ('lin', 'character', {
            'name': '林舟', 'role': '主角', 'want': '查清旧账簿去向', 'wound': '最怕连累阿妹',
            'voice': '克制但带点讽刺', 'visibility': 'public',
        }),
        ('zhou', 'character', {
            'name': '周掌柜', 'role': '当铺掌柜', 'voice': '圆滑客气',
            'want': 'HIDDEN_TRAUMA_999：暗中销毁密信', 'visibility': 'public',
        }),
        ('secret_world', 'world', {
            'title': '幕后铁律', 'rule': 'SECRET_WORLD_RULE_XYZ', 'limits': '仅作者可见',
            'visibility': 'author_only',
        }),
        ('scene1-card', 'scene', {
            'title': '雨夜当铺',
            'goal': 'SCENE_GOAL_SECRET_888：林舟试探周掌柜口风',
            'conflict': '周掌柜拒认旧账簿，还暗示官差正在外头巡夜',
            'entering_state': '林舟淋雨赶到当铺，衣袖里藏着半页残账',
            'planned_result': '林舟摸清账簿已转手，却被迫留下玉佩作押',
            'allowed_disclosure': '只允许暴露周掌柜神色慌乱与账簿转手线索，禁止暴露幕后主使',
            'character_goals': {
                'lin': '逼周掌柜吐露账簿下落',
                'zhou': 'ANTAGONIST_PRIVATE_GOAL_777：稳住林舟直到杀手赶到',
            },
            'pov': 'lin',
            'characters': ['lin', 'zhou'],
            'story_time': '1',
            'visibility': 'public',
        }),
        ('scene2-card', 'scene', {
            'title': '暗巷截杀',
            'goal': '林舟摆脱追踪',
            'conflict': '雨巷出口被堵，身上旧伤裂开',
            'planned_result': '林舟借水道脱身',
            'pov': 'lin',
            'characters': ['lin'],
            'story_time': '2',
            'visibility': 'public',
        }),
    ]
    for ident, kind, body in cards:
        ref = add_card(store, ident, kind, body)
        dec = decide_card(store, ref, 'approved', '已确认')
        approvals.append({**asdict(ref), 'decision_id': dec.id})
    facts = [
        {'entity_id': 'ledger', 'predicate': 'holder', 'holder': 'WORLD', 'claim': 'fact',
         'value': 'SECRET_LEDGER_OWNER', 'story_order': 0, 'disclosure_order': [0, 0, 0]},
        {'entity_id': 'ledger', 'predicate': 'rumor', 'holder': 'lin', 'claim': 'belief',
         'value': '林舟误以为账簿还在当铺暗格', 'story_order': 0, 'disclosure_order': [0, 0, 0]},
        {'entity_id': 'lin', 'predicate': 'injury', 'holder': 'lin', 'claim': 'fact',
         'value': '左肩有未愈刀伤', 'story_order': 0, 'disclosure_order': [0, 0, 0]},
    ]
    adopt_story(store, baseline(card_refs=approvals, facts=facts), {})
    store.connection.execute(
        'UPDATE scenes SET card_json=? WHERE id=?',
        (json.dumps({'story': {'scene_ref': {'card_id': 'scene1-card', 'version': 1}, 'story_order': 1}}), scene1),
    )
    store.connection.execute(
        'UPDATE scenes SET card_json=? WHERE id=?',
        (json.dumps({'story': {'scene_ref': {'card_id': 'scene2-card', 'version': 1}, 'story_order': 2}}), scene2),
    )
    store.connection.commit()
    return store, scene1, scene2


def test_situation_card_is_pov_safe_and_enables_pre_write_craft_guide(tmp_path):
    store, scene1, _ = _seed_rich_story(tmp_path)
    try:
        work = build_story_context(
            store, scene1, StoryScope('main', 0, 1, {'card_id': 'scene1-card', 'version': 1}), 24000,
        )
        assert PRE_WRITE_CRAFT_GUIDE in work.prompt
        assert '叙事生命力原则' in work.prompt
        assert '后台状态机负责记账，正文绝不报账' in work.prompt

        sit_items = [it for it in work.package['items'] if it['source'] == 'situation:scene1-card']
        assert len(sit_items) == 1
        sit = json.loads(sit_items[0]['text'])
        assert sit['pov_stance']['name'] == '林舟'
        assert sit['pov_stance']['immediate_goal'] == '逼周掌柜吐露账簿下落'
        assert any(p['name'] == '周掌柜' for p in sit['present_characters'])
        assert 'pov_beliefs_may_err' in sit and any('误以为' in x for x in sit['pov_beliefs_may_err'])
        assert '周掌柜拒认旧账簿' in sit['spotlight_to_expand']

        # Strict POV firewall: author secrets & non-POV private goals must NEVER appear anywhere in package.
        serialized = json.dumps(work.package, ensure_ascii=False)
        assert 'SECRET_WORLD_RULE_XYZ' not in serialized
        assert 'HIDDEN_TRAUMA_999' not in serialized
        assert 'ANTAGONIST_PRIVATE_GOAL_777' not in serialized
        assert 'SECRET_LEDGER_OWNER' not in serialized
    finally:
        store.connection.close()


def test_style_reference_author_sample_auto_book_prose_and_budget_drop(tmp_path):
    store, scene1, scene2 = _seed_rich_story(tmp_path)
    try:
        assert load_style_reference(store)['mode'] == 'off'
        sample_text = '雨珠砸在青砖上溅起细白水花，掌柜头也不抬，算盘珠子拨得噼啪作响。' * 12
        saved = save_style_reference(store, {
            'enabled': True,
            'mode': 'author_sample',
            'title': '作者自写语感样段',
            'source_note': '作者试笔',
            'excerpt': sample_text,
            'style_notes': '句子按意思一路说完，对白带点市井锋芒。',
        })
        assert saved['enabled'] is True and saved['mode'] == 'author_sample'

        work = build_story_context(
            store, scene1, StoryScope('main', 0, 1, {'card_id': 'scene1-card', 'version': 1}), 24000,
        )
        ref_items = [it for it in work.package['items'] if it['source'] == 'style-reference']
        assert len(ref_items) == 1
        ref_body = json.loads(ref_items[0]['text'])
        assert ref_body['mode'] == 'author_sample'
        assert '雨珠砸在青砖上' in ref_body['excerpt']
        assert '严禁照搬' in ref_body['usage_rule']

        # Tight budget gracefully omits style_reference without failing mandatory context.
        mandatory_plus_small = len(work.prompt) + len(json.dumps(work.package, ensure_ascii=False)) - len(ref_items[0]['text']) + 40
        tight = build_story_context(
            store, scene1, StoryScope('main', 0, 1, {'card_id': 'scene1-card', 'version': 1}), mandatory_plus_small,
        )
        assert 'style_reference' in tight.omitted_optional_groups
        assert not any(it['source'] == 'style-reference' for it in tight.package['items'])

        # Auto book prose mode pulls safe Chapter 1 accepted prose for a later scene (not duplicating immediate previous)
        # and never leaks a flash-forward scene.
        ch2 = store.add_chapter(2, '第二章')
        scene3 = store.add_scene(ch2.id, 1, json.dumps({
            'story': {'scene_ref': {'card_id': 'scene2-card', 'version': 1}, 'story_order': 3},
        }))
        ch3 = store.add_chapter(3, '第三章')
        scene_later = store.add_scene(ch3.id, 1, json.dumps({
            'story': {'scene_ref': {'card_id': 'scene2-card', 'version': 1}, 'story_order': 2},
        }))
        d1 = draft_for(
            store, scene1,
            '第一章开篇安全正文：青石巷口灯笼在雨风里晃荡，林舟按住衣襟走进当铺，木门吱呀一声合拢，空气里全是陈年樟脑和霉纸的味道。柜台后算盘声一停，周掌柜眯着眼抬起头来。',
        )
        d2 = draft_for(store, scene2, '第一卷第二场衔接段：雨越下越大，林舟收好残页转身离开。')
        head = StateHead('main', 0)
        head = accept_batch(store, [proposal(store, head, d1, []), proposal(store, head, d2, [])], head, 'accept-1-2')

        save_style_reference(store, {
            'enabled': True,
            'mode': 'auto_book_prose',
            'style_notes': '保持开篇克制冷峻的雨夜腔调。',
        })
        work3 = build_story_context(
            store, scene_later.id, StoryScope('main', head.revision, 2, {'card_id': 'scene2-card', 'version': 1}), 24000,
        )
        auto_ref = next(it for it in work3.package['items'] if it['source'] == 'style-reference')
        auto_body = json.loads(auto_ref['text'])
        assert auto_body['mode'] == 'auto_book_prose'
        assert auto_body['source_chapter'] == 1
        assert '青石巷口灯笼' in auto_body['excerpt']
        assert scene3.id != scene_later.id
    finally:
        store.connection.close()


def test_review_and_revise_messages_include_anti_ai_and_protect_humanity(tmp_path):
    store, scene1, _ = _seed_rich_story(tmp_path)
    try:
        work = build_story_context(
            store, scene1, StoryScope('main', 0, 1, {'card_id': 'scene1-card', 'version': 1}), 24000,
        )
        draft = draft_for(store, scene1, '林舟推开门，雨气灌进大堂。')

        review_msgs, review_ver = draft_messages(work.package, 'review', draft, None, None, '', ())
        assert review_ver == 'novel-review-v1'
        assert ANTI_AI_REVIEW_GUIDE in review_msgs[0]['content']
        assert '不要动保护清单' in review_msgs[0]['content']

        revise_msgs, revise_ver = draft_messages(
            work.package, 'revise', draft, {'recommendation': 'revise', 'notes': '补足情绪反应'}, None, '', (),
        )
        assert revise_ver == 'novel-revise-v1'
        assert ANTI_AI_REVISE_GUIDE in revise_msgs[0]['content']
        assert '不要动保护清单' in revise_msgs[0]['content']

        # Bare legacy package without craft items/contract/genre_ids stays untouched for tight capacity tests.
        bare_pkg = {'items': [{'source': 'brief', 'text': 'x', 'reason': 'r'}]}
        bare_review, _ = draft_messages(bare_pkg, 'review', draft, None, None, '', ())
        assert ANTI_AI_REVIEW_GUIDE not in bare_review[0]['content']
    finally:
        store.connection.close()


def test_blind_cold_read_strictly_isolates_all_author_design_and_secrets(tmp_path):
    store, scene1, scene2 = _seed_rich_story(tmp_path)
    try:
        ch2 = store.add_chapter(2, '暗巷')
        scene_ch2 = store.add_scene(ch2.id, 1, '{}')
        d1 = draft_for(store, scene1, '门闩刚落下，院外便响起一阵急促的敲门声。林舟收起残账，抬眼看向屏风后。')
        d2 = draft_for(store, scene2, '两人对视一眼便各自散开，雨声盖过了外头的脚步。')
        d3 = draft_for(store, scene_ch2.id, '次日雨歇，林舟在茶摊外又听见有人提起旧账簿的下落。')

        cfg = Config('fake', 'http://localhost', 'mock-reader', '', 60.0, {}, tmp_path, True, {})
        prov = CapturingColdReadProvider()

        # Before cold read: Chapter 1 triggers Golden-3 recommendation.
        pre_sum = cold_read_summary(store, scene_id=scene1, draft_id=d1.id, chapter_index=1)
        assert pre_sum['recommended'] is True and pre_sum['is_golden_three'] is True

        # 1. Single-scene blind cold read
        rep_scene = run_cold_read(store, cfg, prov, scope='scene', scene_id=scene1, draft_id=d1.id)
        assert rep_scene['parsed']['parsed_ok'] is True
        assert rep_scene['parsed']['keep_reading']['want_next'] == 'yes'
        assert rep_scene['isolated_input_keys'] == ['mode', 'target_label', 'target_prose']

        # CRITICAL ISOLATION ASSERTION: ZERO outline / card / world / brief / secret leaks!
        sent_text = json.dumps(prov.calls[-1], ensure_ascii=False)
        for forbidden in (
            'AUTHOR_SECRET_ENDING_PLAN',
            'SECRET_WORLD_RULE_XYZ',
            'HIDDEN_TRAUMA_999',
            'SCENE_GOAL_SECRET_888',
            'ANTAGONIST_PRIVATE_GOAL_777',
            'SECRET_LEDGER_OWNER',
            '单章单POV',
        ):
            assert forbidden not in sent_text, f'Blind cold read leaked forbidden context: {forbidden}'

        # After cold read: draft is untouched and recommendation clears for this draft.
        assert store.get('draft', d1.id).text == d1.text
        post_sum = cold_read_summary(store, scene_id=scene1, draft_id=d1.id, chapter_index=1)
        assert post_sum['recommended'] is False
        assert post_sum['latest_for_draft']['id'] == rep_scene['id']

        # 2. Multi-chapter consecutive cold read (range)
        rep_range = run_cold_read(store, cfg, prov, scope='range', chapter_start=1, chapter_end=2)
        assert rep_range['scope'] == 'range'
        assert rep_range['chapter_indices'] == [1, 2]
        assert len(rep_range['parsed']['repetitive_beats']) == 1
        assert d3.text[:10] in json.dumps(prov.calls[-1], ensure_ascii=False)

        # Persisted on disk and listable
        all_reports = list_cold_reads(store, limit=10)
        assert len(all_reports) == 2
        assert (store.data_file('审读') / f"{rep_scene['id']}.json").is_file()
    finally:
        store.connection.close()


def test_p0_studio_http_endpoints_style_reference_and_cold_read(tmp_path):
    workspace = tmp_path / 'ws'
    cfg_path = tmp_path / 'studio.config.toml'
    cfg_path.write_text(
        '[model]\nprovider="ollama"\nbase_url="http://127.0.0.1:11434"\nmodel="mock"\ntimeout=60\n',
        encoding='utf-8',
    )
    service = StudioService(workspace, config_path=cfg_path)
    server = create_studio_server(service, host='127.0.0.1', port=0)

    # Inject our capturing mock provider into ProductionService runtime for offline HTTP verification.
    mock_prov = CapturingColdReadProvider()
    mock_cfg = Config('fake', 'http://localhost', 'mock-reader', '', 60.0, {}, workspace, True, {})
    server.production.test_mode = True
    server.production.runtime_factory = lambda: (mock_cfg, mock_prov)

    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def call(method: str, path: str, body: dict | None = None):
        data = json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None
        headers = {'Content-Type': 'application/json'} if data is not None else {}
        req = Request(f'http://127.0.0.1:{port}{path}', data=data, headers=headers, method=method)
        with urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))

    try:
        # Seed a project in ProductionStore with 1 chapter & 1 scene & 1 manual draft.
        prod = server.production
        ident = 'p0-http-novel'
        proj_dir = 'novel-p0http'
        prod.db.add(ident, proj_dir, '雨夜当铺测试', {'title': '雨夜当铺测试', 'genre_ids': ['XUANYI']})
        with prod.open_store({'project_dir': proj_dir}, create=True) as store:
            project = store.init_project('雨夜当铺测试')
            prod.db.update(ident, project_id=project.id)
            store.add_brief('查清旧账簿失踪案', '禁止提前揭晓幕后黑手')
            ch = store.add_chapter(1, '雨夜当铺')
            sc_card = add_card(store, 'sc1', 'scene', {
                'title': '当铺试探', 'goal': '林舟打听账簿', 'conflict': '掌柜装傻推诿',
                'pov': 'lin', 'characters': ['lin'], 'story_time': '1', 'visibility': 'public',
            })
            ch_card = add_card(store, 'lin', 'character', {'name': '林舟', 'role': '主角', 'want': '查清旧账簿', 'visibility': 'public'})
            d_sc = decide_card(store, sc_card, 'approved', 'ok')
            d_ch = decide_card(store, ch_card, 'approved', 'ok')
            adopt_story(store, baseline(card_refs=[
                {**asdict(sc_card), 'decision_id': d_sc.id},
                {**asdict(ch_card), 'decision_id': d_ch.id},
            ]), {})
            sc = store.add_scene(ch.id, 1, json.dumps({
                'story': {'scene_ref': asdict(sc_card), 'story_order': 1},
            }))
            scene_id = sc.id

        # Save manual prose draft
        status, _ = call('POST', f'/api/projects/{proj_dir}/scenes/{scene_id}/draft', {
            'text': '门闩刚落下，院外便响起一阵急促的敲门声。林舟盯着门槛下的水渍，心里猛地一沉。',
            'branch': 'main',
        })
        assert status == 200

        # 1. Style reference GET -> POST -> inspect context
        status, sr0 = call('GET', f'/api/novels/{ident}/style-reference')
        assert status == 200 and sr0['mode'] == 'off'

        status, sr1 = call('POST', f'/api/novels/{ident}/style-reference', {
            'enabled': True,
            'mode': 'author_sample',
            'title': '雨夜试笔',
            'excerpt': '烛火一晃，茶碗底映出半张冷脸。他没急着开口，先听外头雨声落定。',
            'style_notes': '克制凝练，少废话。',
        })
        assert status == 200 and sr1['enabled'] is True and sr1['mode'] == 'author_sample'

        status, ctx_data = call('GET', f'/api/projects/{proj_dir}/scenes/{scene_id}/context?branch=main')
        assert status == 200
        assert ctx_data['has_situation_card'] is True
        assert ctx_data['has_style_reference'] is True

        # 2. Quality shows Golden-3 cold-read recommendation & active style reference
        status, q0 = call('GET', f'/api/novels/{ident}/quality?scene={scene_id}')
        assert status == 200
        assert q0['style_reference']['enabled'] is True
        assert q0['cold_read']['recommended'] is True

        # 3. Run blind cold read via HTTP
        status, cr_res = call('POST', f'/api/novels/{ident}/cold-reads', {
            'scope': 'scene',
            'scene_id': scene_id,
            'branch': 'main',
            'custom_focus': '重点看开头抓不抓人',
        })
        assert status == 200
        assert cr_res['report']['parsed']['keep_reading']['want_next'] == 'yes'
        assert cr_res['summary']['recommended'] is False

        # 4. List saved cold reads & re-check quality
        status, cr_list = call('GET', f'/api/novels/{ident}/cold-reads?scene={scene_id}')
        assert status == 200 and len(cr_list['reports']) == 1

        status, q1 = call('GET', f'/api/novels/{ident}/quality?scene={scene_id}')
        assert status == 200 and q1['cold_read']['latest_for_draft']['id'] == cr_res['report']['id']
    finally:
        server.shutdown()
        server.server_close()
