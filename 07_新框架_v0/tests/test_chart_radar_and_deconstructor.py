"""Tests for Multi-Platform Chart Radar & Upgraded Book Deconstruction System.

Covers:
  1. Safe public HTTP parsers (Qidian mobile SSR, Fanqie public JSON API, Qimao SSR filtering published titles)
     + strict non-bypass CAPTCHA / HTTP-403 detection.
  2. Universal Multi-Format Chart Importer (Markdown, CSV, JSON, free-form paste) + Type KB genre mapping.
  3. Deterministic Multi-List Aggregation (mirror duplicate-list suppression, per-platform book dedup,
     new-book vs legacy separation, heat quartiles, word buckets, title bigrams, multi-list overlaps).
  4. Period-over-period Trend Diff (rising/cooling genres, rising tags, new entrants).
  5. Evidence-grounded Topic Decisions (strict feasibility caps `medium` vs `high`, optional LLM polish).
  6. Upgraded 0-Token Quantitative Medical Exam (long Golden-3 + short-fiction lead detection + benchmark deviations).
  7. 0-Token Verified Excerpt Harvester (verbatim slicing + anonymization + 3-check zero-alert admission).
  8. Full Closed Loop: Radar Topic (`pending_deconstruction`) -> Book Deconstruct Pack (0-token & LLM deep
     Golden-3 / RH-TR / EM-card) -> Automatic Topic Backfill (`verified`).
  9. Studio HTTP Routes (`/radar`, `/radar/import`, `/radar/diff`, `/radar/topics`, `/staging/<id>/anatomy`).
"""
from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest

from nw.llm.base import GenResult, LLMProvider
from nw.studio.book_deconstructor import (
    analyze_book_quantitative_metrics,
    get_book_deconstruct_artifact,
    harvest_verified_excerpts_from_book,
    run_book_deconstruct_pack,
)
from nw.studio.chart_radar import (
    aggregate_chart_snapshots,
    backfill_topic_verification,
    diff_chart_snapshots,
    fetch_live_chart,
    generate_topic_decisions,
    list_topic_decisions,
    map_platform_genre_to_type_ids,
    parse_chart_import,
    parse_fanqie_api_json,
    parse_qidian_mobile_ssr_html,
    parse_qimao_shuku_html,
    save_chart_snapshot,
)
from nw.studio.library import LibraryService
from nw.studio.production_routes import ProductionRoutes


class _ScriptedProvider(LLMProvider):
    name = 'fake'

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls: list[list[dict]] = []

    def generate(self, messages: list[dict], **params: Any) -> GenResult:
        self.calls.append(messages)
        return GenResult(
            text=self.reply,
            finish_reason='complete',
            usage={'prompt_tokens': 120, 'completion_tokens': 240},
            request_id='req-fake',
            raw=None,
        )


class _StubHandler:
    def __init__(self) -> None:
        self.status = 0
        self.payload: Any = None

    def _send_json(self, status: int, data: Any) -> None:
        self.status = status
        self.payload = data


class _StubProduction:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self._prov = provider

    def _runtime(self) -> tuple[Any, LLMProvider]:
        class _Cfg:
            model = 'fake-model'
            params: dict[str, Any] = {}
        assert self._prov is not None
        return _Cfg(), self._prov


def _sample_long_novel() -> tuple[str, list[dict[str, Any]]]:
    ch1 = (
        '第一章 典当行的欠条\n'
        '“把账本交出来，不然明天你就别想开门。”\n'
        '陆寒把擦柜台的抹布甩在木桌上，手指扣住抽屉底下的铁尺。\n'
        '柜台外站着三个穿黑夹克的壮汉，领头的刀疤脸往地上吐了口烟灰，冷笑着把一张泛黄的欠条拍在玻璃板上。\n'
        '“你爹去年借了三十万，连本带利九十万。今天不签字画押，这间老当铺就改姓周。”\n'
        '陆寒没看那张欠条，只盯着刀疤脸左手虎口那道新结痂的烫伤。\n'
        '他抬手按下柜台内侧的铜铃，声音不大：“周管事，去年七月我爹早就出车祸走了，这手印是谁替他按的？”\n'
        '话音未落，叮！一行半透明的冰冷字体骤然浮现在玻璃柜面上：【鉴伪系统已激活：检测到伪造指纹与隐蔽债务陷阱，拆穿即可获得启动资金】。'
        '刀疤脸脸色骤变，猛地伸手去抓那张欠条，可门外却突然响起了刺耳的警笛声！\n'
        '【作者有话说】新书启航求收藏求月票！'
    )
    ch2 = (
        '第二章 当场反杀\n'
        '“谁报的警？”刀疤脸猛地回头，手掌死死按住抽屉边缘。\n'
        '陆寒退后半步，顺手把柜台下的老式录音笔亮在灯光下，嘴角微微一扬。\n'
        '“周管事进门前不是嫌监控碍眼，专门叫人剪了门口的电线吗？可惜啊，电线断了，电池可没断。”\n'
        '两名壮汉下意识停住脚步，面面相觑。\n'
        '刀疤脸咬着牙压低声音：“小子，别给脸不要脸，真把事情闹大，你这铺子明天照样开不成！”\n'
        '陆寒没退，反而上前一步，指尖敲了敲玻璃面：“那正好，请进来的两位片警同志顺便验一验，这欠条上的印泥到底产自哪个厂。”\n'
        '玻璃门被人从外猛地推开，带队的赵队长扫了一眼满桌狼藉，视线径直落在了刀疤脸藏在身后的那只手上。\n'
        '刀疤脸额角渗出冷汗，正要强辩，角落里却突然传来一声急促的手机铃响，来电显示赫然是幕后老板的名字！\n'
    )
    ch3 = (
        '第三章 第二份账簿\n'
        '“陆老板，这回算你狠，咱们走着瞧。”\n'
        '刀疤脸被带走前，阴鸷的目光死死剜了陆寒一眼。\n'
        '等店里终于安静下来，陆寒拉下卷帘门，从抽屉夹层里摸出父亲临终前留下的铜钥匙。\n'
        '老当铺后墙的暗格应声弹开，里面没有金条，只有一本用油纸包得严严实实的蓝皮旧账。\n'
        '他翻开第一页，呼吸猛地一滞。\n'
        '账本最上方记着的根本不是什么高利贷，而是一笔三年前寄往城北拍卖行的押品清单，担保人签名处赫然写着全市首富的名字。\n'
        '陆寒指尖摩挲过泛黄的纸角，低声念出那行批注：“物主若在三年内未赎，当铺后人可凭玉印接管名下全部抵押股权。”\n'
        '就在这时，卷帘门外忽然响起三下极其克制的敲门声，一张烫金名片从门缝里悄无声息地滑了进来！\n'
    )
    parts = [ch1, ch2, ch3]
    full = ''
    chapters: list[dict[str, Any]] = []
    for idx, part in enumerate(parts, start=1):
        start = len(full)
        full += part + '\n\n'
        chapters.append({'title': part.splitlines()[0], 'start': start, 'end': len(full) - 2})
    return full, chapters


# ── 1. Public HTTP Parsers & Strict Non-Bypass CAPTCHA Detection ──────────────

def test_qidian_fanqie_qimao_parsers_and_captcha_block() -> None:
    # Qidian mobile SSR HTML
    ssr_payload = {
        'pageContext': {
            'pageProps': {
                'pageData': {
                    'records': [
                        {
                            'rankNum': 1, 'bid': '1001', 'bName': '诡秘新纪元', 'bAuth': '星河',
                            'cat': '悬疑', 'subCat': '诡秘悬疑', 'status': '连载', 'cnt': '45.2万',
                            'totalRecommend': '8.6万', 'desc': '在迷雾之城破译禁书秘密。',
                        },
                        {
                            'rankNum': 2, 'bid': '1002', 'bName': '大明税务官', 'bAuth': '清风',
                            'cat': '历史', 'subCat': '两宋元明', 'status': '连载', 'cnt': '120万',
                            'totalRecommend': '15.4万', 'desc': '穿越大明查账改税制。',
                        },
                    ],
                },
            },
        },
    }
    html = f'<html><script id="vite-plugin-ssr_pageContext">{json.dumps(ssr_payload, ensure_ascii=False)}</script></html>'
    qd = parse_qidian_mobile_ssr_html(html, list_label='畅销榜', url='https://m.qidian.com/rank/hotsales/')
    assert qd['ok'] is True and len(qd['entries']) == 2
    assert qd['entries'][0]['words'] == 452_000
    assert qd['entries'][0]['metric_value'] == 86_000.0
    assert 'GENRE_XUANYI' in qd['entries'][0]['mapped_type_ids']

    # CAPTCHA / WAF block must be reported cleanly without bypass
    blocked_res = fetch_live_chart(
        'qidian', 'hotsales',
        fetcher=lambda u, h, t: (200, u, '<html>请完成安全验证 / 滑块验证</html>'.encode('utf-8')),
    )
    assert blocked_res['ok'] is False and blocked_res['blocked'] is True
    assert '风控/验证' in blocked_res['reason']

    http403_res = fetch_live_chart(
        'fanqie', 'hot',
        fetcher=lambda u, h, t: (403, u, b'Forbidden'),
    )
    assert http403_res['ok'] is False and http403_res['blocked'] is True

    # Fanqie public JSON API
    fq_json = {
        'data': {
            'result': [
                {
                    'book_id': '7001', 'book_name': '我在末日开超市', 'author': '白鹿',
                    'category': '科幻末世', 'read_count': '28.5万', 'word_number': '52万',
                    'creation_status': '1', 'abstract': '【囤货+基建+不圣母】天灾降临前买下整座仓储基地。',
                },
            ],
        },
    }
    fq = parse_fanqie_api_json(fq_json, list_label='黑马新书榜')
    assert fq['ok'] is True and len(fq['entries']) == 1
    assert fq['entries'][0]['metric_name'] == '在读' and fq['entries'][0]['metric_value'] == 285_000.0
    assert '囤货' in fq['entries'][0]['tags']
    assert 'GENRE_KEHUAN' in fq['entries'][0]['mapped_type_ids'] or 'GENRE_MOSHI' in fq['entries'][0]['mapped_type_ids']

    # Qimao SSR HTML filters out published non-webnovel categories!
    qm_html = '''
    <ul>
      <li class="qm-cover-text-item">
        <span class="s-tit"><a href="/shuku/9001/">大明锦衣卫</a></span>
        <span class="s-author">墨客</span><span class="s-category">架空历史</span>
        <span class="s-status">连载中</span><span class="s-words-num">32万字</span>
        <p class="s-desc">穿越明初查奇案。</p>
      </li>
      <li class="qm-cover-text-item">
        <span class="s-tit"><a href="/shuku/9002/">经济学原理精讲</a></span>
        <span class="s-author">教授</span><span class="s-category">经管励志</span>
        <span class="s-status">完结</span><span class="s-words-num">40万字</span>
      </li>
    </ul>'''
    qm = parse_qimao_shuku_html(qm_html)
    assert qm['ok'] is True
    assert len(qm['entries']) == 1 and qm['entries'][0]['title'] == '大明锦衣卫'
    assert qm['excluded_published'] == 1


# ── 2. Universal Multi-Format Importer ────────────────────────────────────────

def test_universal_importer_markdown_csv_json_and_paste() -> None:
    md_text = '''# 番茄 · 黑马新书榜

### #1 规则怪谈：我能看见隐藏提示
*北辰 · 悬疑脑洞 · 连载中 · 26.5万字 · 18.2万在读*
**标签：** 规则怪谈、推理、无女主
**简介**
> 别人靠命试错，我能看见规则背面的血字批注。
[作品页](https://fanqienovel.com/page/9991)

### #2 诡秘当铺老板
*青衫 · 悬疑脑洞 · 连载中 · 19万字 · 11.4万在读*
**标签：** 民俗、悬疑、反转
'''
    parsed_md = parse_chart_import(md_text)
    assert parsed_md['platform'] == 'fanqie' and parsed_md['source_mode'] == 'manual_markdown'
    assert len(parsed_md['entries']) == 2
    assert parsed_md['entries'][0]['metric_name'] == '在读' and parsed_md['entries'][0]['metric_value'] == 182_000.0
    assert 'GENRE_XUANYI' in parsed_md['entries'][0]['mapped_type_ids']

    csv_text = '排名,书名,作者,题材,字数,在读,标签\n1,星海领主,阿明,科幻,45万,9.5万,星际、基建\n2,深渊巡夜人,林夕,悬疑,22万,14万,诡异、推理\n'
    parsed_csv = parse_chart_import(csv_text, platform='番茄', list_name='热门榜')
    assert parsed_csv['source_mode'] == 'manual_csv' and len(parsed_csv['entries']) == 2
    assert parsed_csv['entries'][1]['words'] == 220_000

    json_text = json.dumps({
        'platform': '起点', 'list_name': '月票榜',
        'books': [{'rank': 1, 'title': '仙道长青', 'author': '青云', 'genre': '仙侠', 'words': '150万', '月票': '2.3万', 'tags': ['凡人流', '稳健']}],
    }, ensure_ascii=False)
    parsed_json = parse_chart_import(json_text)
    assert parsed_json['platform'] == 'qidian' and parsed_json['entries'][0]['metric_name'] == '月票'
    assert 'GENRE_XIANXIA' in map_platform_genre_to_type_ids('古典仙侠', ['凡人流'])

    paste_text = (
        '1. 《重生年代搞基建》 | 铁牛 | 都市种田 | 连载 | 35万字 | 12万在读 | 【年代+种田+致富】\n'
        '2. 《大唐小县令》 | 长安客 | 架空历史 | 连载 | 50万字 | 9万在读\n'
    )
    parsed_paste = parse_chart_import(paste_text, platform='番茄', list_name='粘贴榜')
    assert parsed_paste['source_mode'] == 'manual_paste' and len(parsed_paste['entries']) == 2
    assert parsed_paste['entries'][0]['title'] == '重生年代搞基建'
    assert parsed_paste['entries'][0]['words'] == 350_000


# ── 3 & 4 & 5. Aggregation, Duplicate Suppression, Diff & Feasibility Caps ───

def test_aggregation_dedup_diff_and_feasibility_caps(tmp_path: Path) -> None:
    lib = LibraryService(tmp_path / 'library')

    # Build 16 urban-suspense books + 2 history books across hot list & new-book list
    # so 悬疑脑洞 exceeds sparse threshold (15), has cross-list overlap, and beats median -> feasibility == 'high'!
    hot_entries = [
        {
            'rank': i, 'title': f'怪谈档案第{i}号', 'author': f'作者{i}',
            'genre': '悬疑脑洞', 'words': f'{20 + i}万', '在读': f'{15 + i}万',
            'tags': ['规则怪谈', '智斗'],
        }
        for i in range(1, 17)
    ] + [
        {'rank': 17, 'title': '大明账房', 'author': '老墨', 'genre': '架空历史', 'words': '80万', '在读': '5万', 'tags': ['权谋']},
        {'rank': 18, 'title': '两宋风云', 'author': '古道', 'genre': '架空历史', 'words': '95万', '在读': '4万', 'tags': ['朝堂']},
    ]
    new_entries = [
        {
            'rank': 1, 'title': '怪谈档案第1号', 'author': '作者1',
            'genre': '悬疑脑洞', 'words': '21万', '在读': '18万', 'tags': ['规则怪谈', '微恐'],
        },
        {
            'rank': 2, 'title': '怪谈新规守夜人', 'author': '新人A',
            'genre': '悬疑脑洞', 'words': '12万', '在读': '22万', 'tags': ['规则怪谈', '微恐'],
        },
    ]
    baseline_entries = [
        {'rank': 1, 'title': '旧都市神豪', 'author': '老王', 'genre': '都市日常', 'words': '180万', '在读': '10万', 'tags': ['神豪']},
        {'rank': 2, 'title': '大明账房', 'author': '老墨', 'genre': '架空历史', 'words': '70万', '在读': '6万', 'tags': ['权谋']},
        {'rank': 3, 'title': '怪谈档案第1号', 'author': '作者1', 'genre': '悬疑脑洞', 'words': '10万', '在读': '8万', 'tags': ['规则怪谈']},
    ]

    with lib.connect() as conn:
        s_hot = save_chart_snapshot(conn, parse_chart_import(json.dumps({'platform': '番茄', 'list_name': '热门榜', 'entries': hot_entries}, ensure_ascii=False)), captured_date='2026-11-28')
        # Save an exact duplicate mirror snapshot to verify signature dedup!
        s_hot_dup = save_chart_snapshot(conn, parse_chart_import(json.dumps({'platform': '番茄', 'list_name': '热门榜镜像', 'entries': hot_entries}, ensure_ascii=False)), captured_date='2026-11-28')
        s_new = save_chart_snapshot(conn, parse_chart_import(json.dumps({'platform': '番茄', 'list_name': '黑马新书榜', 'entries': new_entries}, ensure_ascii=False)), captured_date='2026-11-28')
        s_base = save_chart_snapshot(conn, parse_chart_import(json.dumps({'platform': '番茄', 'list_name': '热门榜', 'entries': baseline_entries}, ensure_ascii=False)), captured_date='2026-11-01')

        agg = aggregate_chart_snapshots(conn, snapshot_ids=[s_hot['id'], s_hot_dup['id'], s_new['id']])
        assert len(agg['skipped_duplicates']) == 1
        assert agg['skipped_duplicates'][0]['snapshot_id'] == s_hot_dup['id']
        fp = agg['platforms'][0]
        assert fp['book_count'] == 19  # 18 from hot + 1 unique new book (怪谈档案第1号 deduped!)
        assert fp['compare_new'] is True
        assert any(o['title'] == '怪谈档案第1号' and o['list_count'] == 2 for o in fp['multi_list_overlaps'])
        assert any(bg['gram'] == '怪谈' for bg in fp['title_bigrams'])

        # Diff current vs baseline
        diff = diff_chart_snapshots(conn, current_snapshot_ids=[s_hot['id'], s_new['id']], baseline_snapshot_ids=[s_base['id']])
        assert diff['has_baseline'] is True
        gt = {g['genre']: g for g in diff['diffs'][0]['genre_trends']}
        assert gt['悬疑脑洞']['trend'] == 'rising'
        assert any(ne['title'] == '怪谈新规守夜人' for ne in diff['diffs'][0]['new_entrants'])

        # Topic decisions: 悬疑脑洞 -> high; 架空历史 (only 2 books < 15) -> capped at medium!
        prov = _ScriptedProvider(json.dumps({
            'items': [
                {'core_hook': '以规则批注反杀压迫者，前三章即破局获利。', 'differentiation': '规避纯吓人套路，主打硬核逻辑博弈。', 'risks': '规则设定不可自相矛盾。'},
            ],
        }, ensure_ascii=False))
        res_topics = generate_topic_decisions(
            conn, snapshot_ids=[s_hot['id'], s_new['id']],
            author_focus='强逻辑推理', provider=prov, model='fake-model', max_topics=2,
        )
        topics = res_topics['topics']
        assert len(topics) == 2
        assert topics[0]['feasibility'] == 'high'
        assert topics[0]['primary_genre_id'] == 'GENRE_XUANYI'
        assert topics[0]['core_hook'] == '以规则批注反杀压迫者，前三章即破局获利。'
        assert topics[0]['verification_status'] == 'pending_deconstruction'
        # Sparse genre MUST be capped at medium
        assert topics[1]['feasibility'] == 'medium'
        assert '上限压至「中」' in topics[1]['feasibility_reason']


# ── 6 & 7 & 8. Deconstructor Exam, Excerpt Harvest & Full Closed-Loop Backfill ─

def test_book_deconstructor_exam_short_lead_harvest_and_topic_backfill(tmp_path: Path) -> None:
    lib = LibraryService(tmp_path / 'library')

    # 6a. Long-novel quantitative medical exam
    long_text, long_chapters = _sample_long_novel()
    q_long = analyze_book_quantitative_metrics(long_text, long_chapters, title='诡秘典当行')
    assert q_long['story_chapters_count'] == 3
    assert q_long['golden_three_chapters'][0]['stripped_author_note'] is True
    assert q_long['golden_three_chapters'][0]['dialogue']['first_dialogue_char'] == 1
    assert q_long['golden_finger_signal_chapter'] == 1
    assert q_long['golden_three_cliffhanger_rate'] == '3/3'
    assert q_long['golden_three_summary']['dialogue']['ratio'] > 0.2

    # 6b. Short-fiction lead detection (<25k chars + separator)
    short_text = (
        '第一章 离婚协议\n'
        '我拿着化验单推开包厢门时，顾深正把那枚婚戒戴在苏瑶手上。\n'
        '“她比你懂事。”他说。\n'
        '我没哭，只是把股权转让协议拍在了香槟塔旁边。\n'
        '……\n'
        '三天前，顾深还以为我只是一个离了他就活不下去的全职太太。\n'
        '“明天去民政局把字签了，房子留给你，别再纠缠。”他在电话里语气不耐。\n'
        '我挂断电话，转身拨通了律师的内线。\n'
    )
    q_short = analyze_book_quantitative_metrics(short_text, title='离婚后的千亿账单')
    assert q_short['book_scale'] == 'short'
    assert q_short['short_lead'] is not None
    assert q_short['short_lead']['placement'] == 'ch1-top-embedded'
    assert q_short['golden_three_summary']['pov']['label'] == '第一人称「我」'

    # 7 & 8. Full closed loop: Import Radar Topic -> Import Staging Book -> Run Deep Deconstruct Pack
    # -> Verified Excerpts harvested into library.db AND Topic Decision auto-backfilled to `verified`!
    imported_book = lib.import_book({
        'title': '怪谈典当铺',
        'text': long_text,
    })
    book_id = imported_book['id']
    lib.review_book(book_id, {'decision': 'approve', 'confirmed_types': ['GENRE_XUANYI']})

    with lib.connect() as conn:
        snap = save_chart_snapshot(conn, parse_chart_import(json.dumps({
            'platform': '番茄', 'list_name': '黑马新书榜',
            'entries': [
                {'rank': 1, 'title': '怪谈典当铺', 'author': '墨雨', 'genre': '悬疑脑洞', 'words': '25万', '在读': '16万', 'tags': ['民俗', '智斗']},
            ],
        }, ensure_ascii=False)))
        gen_t = generate_topic_decisions(conn, snapshot_ids=[snap['id']], max_topics=1)
        topic_id = gen_t['topics'][0]['id']
        assert gen_t['topics'][0]['verification_status'] == 'pending_deconstruction'

        deep_reply = json.dumps({
            'golden_three': {
                'overall_verdict': '首章首句即抛催债冲突，章末亮系统+警笛双转折，留存驱动强。',
                'golden_finger_chapter': 1,
                'opening_hook_type': '正面冲突压迫 + 系统亮牌',
                'chapters': [
                    {'chapter': 1, 'core_event': '讨债逼签欠条触发鉴伪系统', 'hook_method': '开篇对话冲突', 'payoff_type': '识破伪造证据反制', 'reaction_layers': ['打手慌乱'], 'cliffhanger': '门外响起警笛', 'transferable': '前50字抛出具象筹码与时限'},
                ],
            },
            'rhythm_registry': {
                'story_framework': '悬疑反杀升级流',
                'core_engine': '鉴伪拆局获取资产与追查旧账真相双线驱动',
                'rh_loops': [
                    {'id': 'RH-001', 'chapters': '第1-2章', 'setup': '恶霸持伪造欠条逼夺祖业', 'release': '断电不灭录音笔+警察现身反杀', 'reaction': '打手冷汗直流不敢妄动', 'next_hook': '幕后老板来电与暗格旧账', 'escalation': '由街头混混升格至城市资本势力'},
                ],
                'tr_triggers': [
                    {'id': 'TR-001', 'chapter': 2, 'event': '亮出电池供电的录音笔反将一军', 'target_emotion': '爽/解气', 'peak': '警察推门盯住伪证', 'aftermath': '引出更大对手', 'reuse_tip': '保留提前留后手的智商碾压链条'},
                ],
            },
            'emotion_modules': [
                {
                    'id': 'EM-001', 'name': '弱势守业反杀伪证局',
                    'reader_want': '看被欺上门的弱势方凭冷静观察与预埋证据当场掀桌',
                    'emotion_chain': '威逼压迫 → 冷静察觉破绽 → 亮底牌反制 → 对手失态 → 牵出更大暗线',
                    'dramatic_unit': '强弱失衡的凭证争夺场中，以第三方公权/公证介入实现反转',
                    'replaceable_slots': ['被夺标的物', '伪造凭证类型', '预埋反证道具'],
                    'do_not_copy': ['典当行欠条', '录音笔具体台词', '周管事与陆寒人名'],
                    'failure_conditions': '若主角纯靠口炮无实质反证，读者会觉得反派降智',
                    'related_rhythm': 'RH-001 / TR-001',
                },
            ],
        }, ensure_ascii=False)
        prov = _ScriptedProvider(deep_reply)

        decon = run_book_deconstruct_pack(
            conn,
            book_id=book_id,
            book_title='怪谈典当铺',
            raw_text=long_text,
            chapters=long_chapters,
            confirmed_types=['GENRE_XUANYI'],
            harvest_excerpts=True,
            provider=prov,
            model='fake-model',
        )
        assert decon['golden_three']['mode'] == 'llm_deep'
        assert decon['rhythm_registry']['rh_loops'][0]['id'] == 'RH-001'
        assert decon['emotion_modules'][0]['id'] == 'EM-001'
        assert len(decon['harvested_excerpts']) >= 1
        # Verify harvested excerpts really landed in verified_corpus_excerpts and anonymized character names!
        ex_list = lib.list_verified_excerpts(types=['GENRE_XUANYI'])
        assert len(ex_list) >= 1
        assert all('陆寒' not in ex['anonymized_text'] for ex in ex_list)

        # Verify Topic Decision was automatically backfilled to verified!
        assert len(decon['backfilled_topics']) == 1
        refreshed_topics = list_topic_decisions(conn)
        matched = next(t for t in refreshed_topics if t['id'] == topic_id)
        assert matched['verification_status'] == 'verified'
        assert matched['verified_by_book_id'] == book_id
        assert '怪谈典当铺' in matched['verification_note']

        # Verify persistence round-trip
        stored = get_book_deconstruct_artifact(conn, book_id)
        assert stored is not None and stored['emotion_modules'][0]['id'] == 'EM-001'


# ── 9. Studio HTTP Routes Integration ─────────────────────────────────────────

def test_studio_radar_and_anatomy_http_routes(tmp_path: Path) -> None:
    lib = LibraryService(tmp_path / 'library')
    routes = ProductionRoutes(_StubProduction(), lib)

    # POST /radar/import
    h = _StubHandler()
    assert routes.post(h, ['radar', 'import'], {
        'platform': '起点', 'list_name': '签约新书榜', 'format': 'csv',
        'text': '排名,书名,作者,题材,字数,总推荐,标签\n1,诡道仙途,云起,仙侠,18万,4.2万,凡人流、诡秘\n2,长生问道,青灯,仙侠,25万,3.8万,稳健、种田\n',
    })
    assert h.status == 201
    snap_id = h.payload['saved']['id']

    # GET /radar & GET /radar/snapshots/<id>
    h_get = _StubHandler()
    assert routes.get(h_get, ['radar'], {})
    assert h_get.status == 200 and len(h_get.payload['snapshots']) == 1

    h_det = _StubHandler()
    assert routes.get(h_det, ['radar', 'snapshots', snap_id], {})
    assert h_det.status == 200 and len(h_det.payload['entries']) == 2

    # POST /radar/topics (0-token without requiring LLM runtime!)
    h_top = _StubHandler()
    assert routes.post(h_top, ['radar', 'topics'], {'use_llm': False, 'max_topics': 2})
    assert h_top.status == 200 and len(h_top.payload['topics']) >= 1

    # Import staging book + GET/POST /staging/<id>/anatomy (0-token)
    long_text, _ = _sample_long_novel()
    book = lib.import_book({'title': '诡道仙途', 'text': long_text})
    lib.review_book(book['id'], {'decision': 'approve', 'confirmed_types': ['GENRE_XIANXIA']})
    h_anat_get = _StubHandler()
    assert routes.get(h_anat_get, ['staging', book['id'], 'anatomy'], {})
    assert h_anat_get.status == 200 and h_anat_get.payload['quantitative']['story_chapters_count'] == 3

    h_anat_post = _StubHandler()
    assert routes.post(h_anat_post, ['staging', book['id'], 'anatomy'], {'use_llm': False, 'harvest_excerpts': True})
    assert h_anat_post.status == 200 and len(h_anat_post.payload['harvested_excerpts']) >= 1
    assert len(h_anat_post.payload['backfilled_topics']) >= 1


# ── 10. Verified 2025-2026 Multi-Platform Monetization & Chart Playbooks ──────

def test_platform_playbooks_recommendations_preflight_and_radar_route(tmp_path: Path) -> None:
    from nw.platform_playbooks import (
        PLATFORM_PLAYBOOKS,
        get_platform_playbook,
        list_platform_playbooks,
        recommend_monetization_platforms,
    )
    from nw.publish_preflight import PLATFORM_SPECS, validate_publish_package

    # Must cover all 6 major monetizable platforms with full ladders & rank list rules
    expected_ids = {'fanqie', 'qidian', 'qimao', 'jjwxc', 'zhihu_yanyan', 'ciweimao'}
    assert expected_ids.issubset(set(PLATFORM_PLAYBOOKS.keys()))
    assert expected_ids.issubset(set(PLATFORM_SPECS.keys()))
    for pb in list_platform_playbooks():
        assert pb['monetization']['model']
        assert pb['signing']['threshold']
        assert len(pb['progression_ladder']) >= 3
        assert len(pb['rank_lists']) >= 2
        assert len(pb['craft_requirements']['redlines']) >= 2

    assert get_platform_playbook('知乎盐言')['id'] == 'zhihu_yanyan'
    assert get_platform_playbook('番茄')['id'] == 'fanqie'

    # Short-fiction beginner -> 知乎盐言 & 番茄短故事 top 2
    short_recs = recommend_monetization_platforms(scale='short', experience='beginner')
    assert {r['platform_id'] for r in short_recs[:2]} == {'zhihu_yanyan', 'fanqie'}

    # Long-fiction beginner -> 七猫保底/训练营 #1, with 2026 Fanqie完本签约 caution
    long_beg = recommend_monetization_platforms(scale='long', experience='beginner')
    assert long_beg[0]['platform_id'] == 'qimao'
    fq_rec = next(r for r in long_beg if r['platform_id'] == 'fanqie')
    assert any('完本签约' in c for c in fq_rec['cautions'])

    # Experienced xuanhuan author -> Qidian & Fanqie near top
    exp_recs = recommend_monetization_platforms(scale='long', experience='experienced', genre_ids=['GENRE_XUANHUAN'])
    assert {'qidian', 'fanqie'} & {r['platform_id'] for r in exp_recs[:2]}

    # Preflight enforces Zhihu Yanyan redline (no BL/纯爱) & attaches playbook_summary
    bad_zhihu = validate_publish_package(
        'zhihu_yanyan',
        title='大婚当夜我在牌位前掀桌了',
        synopsis='这是一篇三万字强反转短篇故事，讲述女主在婚礼当天识破未婚夫与白月光阴谋并当场反杀夺回全部家族资产。',
        tags=['纯爱', '反转'],
        category='古代言情',
    )
    assert bad_zhihu['passed'] is False
    assert any(i['code'] == 'PLATFORM_REDLINE_ZHIHU' for i in bad_zhihu['blocking_issues'])
    assert bad_zhihu['playbook_summary']['monetization_model']

    ok_cwm = validate_publish_package(
        'ciweimao',
        title='东京怪谈观察日记',
        synopsis='穿越平行世界东京，拥有规则怪谈解析面板的普通高中生靠吐槽与推理解决异闻的轻小说冒险日常。',
        tags=['轻小说', '脑洞'],
        category='二次元',
    )
    assert ok_cwm['passed'] is True
    assert '60%' in ok_cwm['playbook_summary']['revenue_split']

    # Studio HTTP route GET /radar/playbooks + monetization_hint inside Topic Decisions
    lib = LibraryService(tmp_path / 'library')
    routes = ProductionRoutes(_StubProduction(), lib)
    h_pb = _StubHandler()
    assert routes.get(h_pb, ['radar', 'playbooks'], {'scale': ['short'], 'experience': ['beginner']})
    assert h_pb.status == 200
    assert len(h_pb.payload['playbooks']) == 6
    assert h_pb.payload['recommendations'][0]['platform_id'] == 'zhihu_yanyan'

    h_imp = _StubHandler()
    assert routes.post(h_imp, ['radar', 'import'], {
        'platform': '番茄', 'list_name': '黑马新书榜', 'format': 'csv',
        'text': '排名,书名,作者,题材,字数,在读,标签\n1,规则怪谈之书,星海,悬疑脑洞,22万,15万,规则怪谈、智斗\n',
    })
    h_top = _StubHandler()
    assert routes.post(h_top, ['radar', 'topics'], {'use_llm': False, 'max_topics': 1})
    assert '番茄小说变现指引' in h_top.payload['topics'][0]['validation_action']

