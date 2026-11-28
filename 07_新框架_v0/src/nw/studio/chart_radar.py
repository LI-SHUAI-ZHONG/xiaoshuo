"""Multi-Platform Chart Radar, Universal Rank Importer, Trend Diff & Topic Decision Engine.

Fuses the strongest chart-scanning architectures from:
  - InkOS (`RadarSource` pluggable source protocol + Fanqie public JSON API + evidence-grounded recommendations)
  - oh-story-claudecode (`story-long-scan` + `aggregate-rank` cross-list dedup, sparse guards,
    title bigrams, new-book vs legacy separation, strict feasibility caps & `待拆文验证` backfill)
  - Our Type KB (35 main / 425 sub genre mapping) & New Novel Wizard bridge.

Safety & Compliance Discipline:
  - Uses ONLY public SSR/JSON HTTP endpoints (stdlib `urllib.request`).
  - NEVER attempts to solve, evade, or bypass CAPTCHAs, WAF challenges, anti-spider fonts, or paywalls.
  - When a platform blocks direct HTTP access, reports a transparent `blocked` status and offers
    the Universal Paste / File Importer (Markdown, CSV/TSV, JSON, or raw browser copy-paste).
"""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
from html import unescape
import io
import json
import re
import sqlite3
from statistics import median
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from nw.call_control import send_model
from nw.llm.base import LLMProvider
from nw.platform_playbooks import get_platform_playbook, list_platform_playbooks, platform_monetization_brief
from nw.studio import catalog
from nw.studio.library_util import encode, timestamp

CHART_RADAR_SCHEMA = '''
CREATE TABLE IF NOT EXISTS chart_snapshots (
 id TEXT PRIMARY KEY,
 platform TEXT NOT NULL,
 platform_name TEXT NOT NULL,
 list_name TEXT NOT NULL,
 source_mode TEXT NOT NULL DEFAULT 'live_http',
 source_url TEXT NOT NULL DEFAULT '',
 captured_date TEXT NOT NULL,
 entry_count INTEGER NOT NULL DEFAULT 0,
 quality_status TEXT NOT NULL DEFAULT '[OK]',
 quality_notes_json TEXT NOT NULL DEFAULT '[]',
 signature_sha256 TEXT NOT NULL DEFAULT '',
 meta_json TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS chart_snapshots_platform_date ON chart_snapshots(platform,captured_date,created_at);

CREATE TABLE IF NOT EXISTS chart_entries (
 id TEXT PRIMARY KEY,
 snapshot_id TEXT NOT NULL REFERENCES chart_snapshots(id) ON DELETE CASCADE,
 rank INTEGER NOT NULL,
 title TEXT NOT NULL,
 author TEXT NOT NULL DEFAULT '',
 genre_raw TEXT NOT NULL DEFAULT '',
 mapped_type_ids_json TEXT NOT NULL DEFAULT '[]',
 status_text TEXT NOT NULL DEFAULT '',
 words INTEGER,
 metric_name TEXT NOT NULL DEFAULT '',
 metric_value REAL,
 metrics_json TEXT NOT NULL DEFAULT '{}',
 tags_json TEXT NOT NULL DEFAULT '[]',
 desc_text TEXT NOT NULL DEFAULT '',
 book_url TEXT NOT NULL DEFAULT '',
 book_key TEXT NOT NULL DEFAULT '',
 extra_json TEXT NOT NULL DEFAULT '{}');
CREATE INDEX IF NOT EXISTS chart_entries_snapshot ON chart_entries(snapshot_id,rank);
CREATE INDEX IF NOT EXISTS chart_entries_book_key ON chart_entries(book_key);

CREATE TABLE IF NOT EXISTS topic_decisions (
 id TEXT PRIMARY KEY,
 title TEXT NOT NULL,
 platforms_json TEXT NOT NULL DEFAULT '[]',
 snapshot_ids_json TEXT NOT NULL DEFAULT '[]',
 primary_genre_id TEXT NOT NULL DEFAULT '',
 genre_tags_json TEXT NOT NULL DEFAULT '[]',
 target_reader TEXT NOT NULL DEFAULT '',
 core_hook TEXT NOT NULL DEFAULT '',
 why_it_works TEXT NOT NULL DEFAULT '',
 differentiation TEXT NOT NULL DEFAULT '',
 feasibility TEXT NOT NULL DEFAULT 'medium' CHECK(feasibility IN ('high','medium','low')),
 feasibility_reason TEXT NOT NULL DEFAULT '',
 risks TEXT NOT NULL DEFAULT '',
 validation_action TEXT NOT NULL DEFAULT '',
 benchmark_books_json TEXT NOT NULL DEFAULT '[]',
 verification_status TEXT NOT NULL DEFAULT 'pending_deconstruction'
   CHECK(verification_status IN ('pending_deconstruction','verified','unconfirmed')),
 verified_by_book_id TEXT NOT NULL DEFAULT '',
 verification_note TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL);
'''

PLATFORMS: dict[str, dict[str, Any]] = {
    'qidian': {
        'id': 'qidian',
        'name': '起点',
        'full_name': '起点中文网',
        'primary_metric': '总推荐',
        'sparse_threshold': 15,
        'live_lists': [
            {'id': 'hotsales', 'label': '畅销榜', 'path': '/rank/hotsales/'},
            {'id': 'yuepiao', 'label': '月票榜', 'path': '/rank/yuepiao/'},
            {'id': 'signnewbook', 'label': '签约新书榜', 'path': '/rank/sign/'},
            {'id': 'pubnewbook', 'label': '公众新书榜', 'path': '/rank/newbook/'},
            {'id': 'newauthor', 'label': '新人作者新书榜', 'path': '/rank/newauthor/'},
            {'id': 'recom', 'label': '原创推荐榜', 'path': '/rank/rec/'},
            {'id': 'readindex', 'label': '阅读指数榜', 'path': '/rank/readindex/'},
            {'id': 'sanjiang', 'label': '三江推荐', 'path': '/sanjiang/'},
        ],
    },
    'fanqie': {
        'id': 'fanqie',
        'name': '番茄',
        'full_name': '番茄小说',
        'primary_metric': '在读',
        'sparse_threshold': 15,
        'live_lists': [
            {'id': 'hot', 'label': '热门榜', 'side_type': 10},
            {'id': 'darkhorse', 'label': '黑马新书榜', 'side_type': 13},
        ],
    },
    'qimao': {
        'id': 'qimao',
        'name': '七猫',
        'full_name': '七猫免费小说',
        'primary_metric': '热度',
        'sparse_threshold': 15,
        'live_lists': [
            {'id': 'library_new', 'label': '全站书库点击新书', 'pages': 2},
        ],
    },
    'jjwxc': {
        'id': 'jjwxc',
        'name': '晋江',
        'full_name': '晋江文学城',
        'primary_metric': '收藏',
        'sparse_threshold': 15,
        'live_lists': [
            {'id': '12', 'label': '收入金榜'},
            {'id': '7', 'label': '月榜'},
            {'id': '15', 'label': '新手金榜'},
        ],
    },
    'ciweimao': {
        'id': 'ciweimao',
        'name': '刺猬猫',
        'full_name': '刺猬猫阅读',
        'primary_metric': '榜单值',
        'sparse_threshold': 10,
        'live_lists': [
            {'id': 'monthly', 'label': '月票榜'},
            {'id': 'newbook', 'label': '新书榜'},
            {'id': 'subscribe', 'label': '订阅榜'},
        ],
    },
    'zhihu_yanyan': {
        'id': 'zhihu_yanyan',
        'name': '知乎盐言',
        'full_name': '知乎盐言故事（盐选短篇 / 中篇）',
        'primary_metric': '赞同',
        'sparse_threshold': 10,
        'live_lists': [],
    },
    'short': {
        'id': 'short',
        'name': '短篇榜单',
        'full_name': '番茄短故事 / 点众 / 黑岩等综合短篇榜',
        'primary_metric': '热度',
        'sparse_threshold': 10,
        'live_lists': [],
    },
}

_PLATFORM_ALIAS_MAP: dict[str, str] = {
    '起点': 'qidian', '起点中文网': 'qidian', '起点读书': 'qidian', 'qidian': 'qidian',
    '番茄': 'fanqie', '番茄小说': 'fanqie', '番茄免费小说': 'fanqie', 'fanqie': 'fanqie',
    '七猫': 'qimao', '七猫免费小说': 'qimao', '七猫小说': 'qimao', 'qimao': 'qimao',
    '晋江': 'jjwxc', '晋江文学城': 'jjwxc', 'jjwxc': 'jjwxc',
    '刺猬猫': 'ciweimao', '刺猬猫阅读': 'ciweimao', 'ciweimao': 'ciweimao',
    '知乎': 'zhihu_yanyan', '知乎盐言': 'zhihu_yanyan', '知乎盐言故事': 'zhihu_yanyan', '盐言': 'zhihu_yanyan', 'zhihu_yanyan': 'zhihu_yanyan',
    '点众': 'short', '黑岩': 'short', '番茄短篇': 'short', '番茄短故事': 'short', '短篇': 'short', 'short': 'short',
}

_METRIC_PRIORITY = ('在读', '热度', '收藏', '赞同', '点赞', '阅读', '月票', '总推荐', '榜单值', '营养液', '积分', '评分')
_NEW_LIST_RE = re.compile(r'(?:新书|新人|新手|新作|潜力|黑马)')
_CAPTCHA_HINTS = ('人机验证', '安全验证', '滑块验证', 'captcha', 'cloudflare', 'access denied', '异常请求', '请完成验证')
_MIN_HEAT_KNOWN = 3

# Non-webnovel published categories to filter out when crawling Qimao library
_QIMAO_PUBLISHED_CATEGORIES = frozenset({
    '人文社科', '出版小说', '少儿教育', '文学艺术', '经典文学', '经管励志', '出版',
    '出版物', '文学', '社科', '传记', '科普', '医学', '生活', '工具书', '散文随笔',
    '健康养生', '科普读物', '成功有道', '少儿读物', '人物传记', '励志鸡汤', '企业管理',
    '心理读物', '外国文学', '亲子教育', '理财经济', '中国文学', '诗词歌赋',
})

# Platform genre keyword -> canonical Type KB ID mapping
_GENRE_KEYWORD_MAP: tuple[tuple[tuple[str, ...], str], ...] = (
    (('玄幻', '东方玄幻', '异世大陆', '高武世界', '玄幻脑洞'), 'GENRE_XUANHUAN'),
    (('仙侠', '修真', '修仙', '洪荒', '古典仙侠', '幻想修仙'), 'GENRE_XIANXIA'),
    (('武侠', '国术', '传统武侠'), 'GENRE_WUXIA'),
    (('奇幻', '西幻', '西方奇幻', '剑与魔法', '领主'), 'GENRE_QIHUAN'),
    (('都市', '都市脑洞', '都市日常', '都市修真', '神豪', '都市种田', '都市高武'), 'GENRE_DUSHI'),
    (('历史', '架空历史', '历史脑洞', '历史古代', '秦汉', '两宋', '大明', '清穿'), 'GENRE_LISHI'),
    (('军事', '抗战', '谍战', '军旅'), 'GENRE_JUNSHI'),
    (('游戏', '游戏体育', '网游', '虚拟网游'), 'GENRE_YOUXI'),
    (('电竞', '电子竞技'), 'GENRE_DIANJING'),
    (('体育', '竞技', '足球', '篮球'), 'GENRE_TIYU'),
    (('科幻', '星际', '机甲', '未来世界', '科幻末世'), 'GENRE_KEHUAN'),
    (('末世', '丧尸', '天灾', '囤货', '废土'), 'GENRE_MOSHI'),
    (('赛博', '赛博朋克', '克苏鲁'), 'GENRE_SAIBO'),
    (('悬疑', '悬疑脑洞', '悬疑灵异', '刑侦', '探案', '推理', '规则怪谈'), 'GENRE_XUANYI'),
    (('灵异', '诡异', '诡秘', '恐怖', '惊悚', '民俗'), 'GENRE_LINGYI'),
    (('轻小说', '二次元', '动漫衍生', '衍生', '同人'), 'GENRE_QINGXIAOSHUO'),
    (('诸天', '无限', '快穿', '万界'), 'GENRE_ZHUTIAN'),
    (('古代言情', '古言', '宅斗', '宫斗', '古风世情', '穿越', '现代言情', '现言', '豪门', '甜宠', '言情', '纯爱', '女频'), 'GENRE_YANQING'),
    (('青春', '校园', '暗恋'), 'GENRE_QINGCHUN'),
    (('种田', '经商', '年代', '乡村', '基建'), 'GENRE_ZHONGDIAN'),
    (('商战', '职场', '官场', '娱乐明星', '文娱'), 'GENRE_SHANGZHAN'),
    (('权谋', '朝堂', '争霸'), 'GENRE_QUANMOU'),
    (('现实', '现实百态', '时代叙事'), 'GENRE_XIANSHI'),
    (('搞笑', '沙雕', '迪化', '反套路'), 'GENRE_GAOXIAO'),
)

_MOBILE_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
        'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}
_DESKTOP_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}


def ensure_chart_radar_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(CHART_RADAR_SCHEMA)


def normalize_platform_id(raw: str) -> str:
    key = str(raw or '').strip().lower()
    if key in _PLATFORM_ALIAS_MAP:
        return _PLATFORM_ALIAS_MAP[key]
    for alias, pid in _PLATFORM_ALIAS_MAP.items():
        if alias and alias in key:
            return pid
    return 'custom'


def platform_display_name(platform_id: str, fallback: str = '') -> str:
    if platform_id in PLATFORMS:
        return PLATFORMS[platform_id]['name']
    return fallback.strip() or platform_id or '自定义平台'


def norm_book_key(title: str, author: str = '') -> str:
    def _clean(s: str) -> str:
        return re.sub(r'[\s《》「」“”"\'·・:：]', '', str(s or '')).lower()
    return f'{_clean(title)}|{_clean(author)}'


def parse_cn_number(raw: Any) -> int | None:
    """Parse Chinese numbers like '12.3万', '1,234', '2.5亿' -> integer or None."""
    if raw is None or raw == '':
        return None
    if isinstance(raw, (int, float)):
        return int(round(raw))
    text = re.sub(r'[,，\s]', '', str(raw))
    m = re.search(r'(\d+(?:\.\d+)?)(万|亿)?', text)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2)
    if unit == '万':
        val *= 10_000
    elif unit == '亿':
        val *= 100_000_000
    return int(round(val))


def format_cn_number(val: float | int | None) -> str:
    if val is None:
        return '—'
    n = float(val)
    if abs(n) >= 100_000_000:
        return f'{n / 100_000_000:.1f}'.rstrip('0').rstrip('.') + '亿'
    if abs(n) >= 10_000:
        return f'{n / 10_000:.1f}'.rstrip('0').rstrip('.') + '万'
    return str(int(round(n)))


def map_platform_genre_to_type_ids(genre_raw: str, tags: list[str] | tuple[str, ...] = ()) -> list[str]:
    """Map platform genre names and tags onto canonical Type KB IDs (35 main / 425 sub)."""
    blob = ' '.join([str(genre_raw or ''), *(str(t or '') for t in tags)])
    matched: list[str] = []
    valid_map = catalog.type_map()
    for keywords, gid in _GENRE_KEYWORD_MAP:
        if gid not in valid_map:
            continue
        if any(kw in blob for kw in keywords):
            if gid not in matched:
                matched.append(gid)
    # Also try direct name match against Type KB main genres
    if not matched:
        for tid, meta in valid_map.items():
            if not meta.get('parent_id'):
                nm = str(meta.get('name') or '')
                if len(nm) >= 2 and nm in blob and tid not in matched:
                    matched.append(tid)
    return matched[:3]


def _clean_html_text(html: str) -> str:
    stripped = re.sub(r'<!--[\s\S]*?(?:-->|$)', '', str(html or ''))
    stripped = re.sub(r'<[^>]+>', ' ', stripped)
    return re.sub(r'\s+', ' ', unescape(stripped)).strip()


def _detect_captcha_block(html: str) -> str:
    sample = (html or '')[:4000].lower()
    for kw in _CAPTCHA_HINTS:
        if kw in sample:
            return f'目标站点返回风控/验证提示（{kw}）'
    return ''


def _http_get_bytes(url: str, *, headers: dict[str, str], timeout: int = 15) -> tuple[int, str, bytes]:
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        return int(getattr(resp, 'status', 200)), str(resp.geturl()), resp.read(5 * 1024 * 1024)


# ─────────────────────────────────────────────────────────────────────────────
# Mode 1: Direct Public HTTP / SSR / JSON Fetchers (Zero CAPTCHA Bypass!)
# ─────────────────────────────────────────────────────────────────────────────

def parse_qidian_mobile_ssr_html(html: str, *, list_label: str = '畅销榜', url: str = '') -> dict[str, Any]:
    """Parse Qidian mobile SSR `vite-plugin-ssr_pageContext` JSON cleanly."""
    if block := _detect_captcha_block(html):
        return {'ok': False, 'blocked': True, 'reason': block, 'entries': []}
    m = re.search(
        r'<script[^>]+id=["\']vite-plugin-ssr_pageContext["\'][^>]*>([\s\S]*?)</script>',
        html or '',
        re.IGNORECASE,
    )
    if not m:
        return {'ok': False, 'blocked': True, 'reason': '页面未包含移动端 SSR 数据块（可能改版或触发风控）', 'entries': []}
    try:
        ctx = json.loads(m.group(1))
    except ValueError as exc:
        return {'ok': False, 'blocked': False, 'reason': f'SSR JSON 解析失败: {exc}', 'entries': []}

    records = (
        ctx.get('pageContext', {})
        .get('pageProps', {})
        .get('pageData', {})
        .get('records')
    ) or []
    entries: list[dict[str, Any]] = []
    for idx, rec in enumerate(records, start=1):
        if not isinstance(rec, dict):
            continue
        title = str(rec.get('bName') or rec.get('bookName') or '').strip()
        if not title:
            continue
        bid = str(rec.get('bid') or rec.get('bookId') or '').strip()
        cat = str(rec.get('cat') or '').strip()
        sub = str(rec.get('subCat') or '').strip()
        genre_raw = cat or sub or '未分类'
        tags = [sub] if sub and sub != cat else []
        words = parse_cn_number(rec.get('cnt') or rec.get('wordCount') or rec.get('words'))
        metrics: dict[str, float] = {}
        tot_rec = parse_cn_number(rec.get('totalRecommend') or rec.get('totalRecommendations') or rec.get('recommendCount'))
        rank_val = parse_cn_number(rec.get('rankCnt') or rec.get('rankValue'))
        if tot_rec is not None:
            metrics['总推荐'] = float(tot_rec)
        if rank_val is not None:
            metrics['榜单值'] = float(rank_val)
        primary_name, primary_val = ('总推荐', metrics['总推荐']) if '总推荐' in metrics else (
            ('榜单值', metrics['榜单值']) if '榜单值' in metrics else ('', None)
        )
        entries.append({
            'rank': int(rec.get('rankNum') or idx),
            'title': title,
            'author': str(rec.get('bAuth') or rec.get('author') or '').strip(),
            'genre_raw': genre_raw,
            'mapped_type_ids': map_platform_genre_to_type_ids(genre_raw, tags),
            'status_text': str(rec.get('status') or rec.get('bookStatus') or '').strip(),
            'words': words,
            'metric_name': primary_name,
            'metric_value': primary_val,
            'metrics': metrics,
            'tags': tags,
            'desc_text': re.sub(r'\s+', ' ', str(rec.get('desc') or '')).strip()[:200],
            'book_url': f'https://m.qidian.com/book/{bid}/' if bid else '',
            'book_key': norm_book_key(title, str(rec.get('bAuth') or rec.get('author') or '')),
            'extra': {'bid': bid, 'sub_cat': sub},
        })

    if not entries:
        return {'ok': False, 'blocked': False, 'reason': '起点移动端 SSR 解析到 0 条榜单数据', 'entries': []}
    return {
        'ok': True,
        'blocked': False,
        'platform': 'qidian',
        'platform_name': '起点',
        'list_name': list_label,
        'source_url': url,
        'entries': entries,
    }


def parse_fanqie_api_json(payload: dict[str, Any], *, list_label: str = '热门榜', url: str = '') -> dict[str, Any]:
    """Parse Fanqie public channel rank JSON response (adopted cleanly from InkOS RadarSource)."""
    records = ((payload or {}).get('data') or {}).get('result') or []
    if not isinstance(records, list) or not records:
        return {'ok': False, 'blocked': False, 'reason': '番茄公开接口未返回榜单条目', 'entries': []}
    entries: list[dict[str, Any]] = []
    for idx, rec in enumerate(records, start=1):
        if not isinstance(rec, dict):
            continue
        title = str(rec.get('book_name') or rec.get('bookName') or '').strip()
        if not title:
            continue
        author = str(rec.get('author') or '').strip()
        genre_raw = str(rec.get('category') or rec.get('sub_category') or '未分类').strip()
        desc = re.sub(r'\s+', ' ', str(rec.get('abstract') or rec.get('desc') or '')).strip()
        tags: list[str] = []
        if bm := re.search(r'[【\[]([^】\]]{2,40})[】\]]', desc):
            tags.extend([t.strip() for t in re.split(r'[+、,/／\s]+', bm.group(1)) if t.strip()][:6])
        if rec.get('tags') and isinstance(rec['tags'], str):
            tags.extend([t.strip() for t in re.split(r'[,，、\s]+', rec['tags']) if t.strip()][:6])
        tags = list(dict.fromkeys(tags))[:8]
        reads = parse_cn_number(rec.get('read_count') or rec.get('readCount'))
        words = parse_cn_number(rec.get('word_number') or rec.get('wordNumber'))
        metrics = {'在读': float(reads)} if reads is not None else {}
        bid = str(rec.get('book_id') or rec.get('bookId') or '').strip()
        entries.append({
            'rank': idx,
            'title': title,
            'author': author,
            'genre_raw': genre_raw,
            'mapped_type_ids': map_platform_genre_to_type_ids(genre_raw, tags),
            'status_text': '连载中' if str(rec.get('creation_status', '')) == '1' else (
                '已完结' if str(rec.get('creation_status', '')) in ('0', '2') else ''
            ),
            'words': words,
            'metric_name': '在读' if reads is not None else '',
            'metric_value': float(reads) if reads is not None else None,
            'metrics': metrics,
            'tags': tags,
            'desc_text': desc[:200],
            'book_url': f'https://fanqienovel.com/page/{bid}' if bid else '',
            'book_key': norm_book_key(title, author),
            'extra': {'book_id': bid},
        })
    return {
        'ok': bool(entries),
        'blocked': False,
        'platform': 'fanqie',
        'platform_name': '番茄',
        'list_name': list_label,
        'source_url': url,
        'entries': entries,
    }


def parse_qimao_shuku_html(html: str, *, list_label: str = '全站书库点击新书', url: str = '') -> dict[str, Any]:
    """Parse Qimao SSR library page (`li.qm-cover-text-item`), excluding published non-webnovel titles."""
    if block := _detect_captcha_block(html):
        return {'ok': False, 'blocked': True, 'reason': block, 'entries': []}
    chunks = re.findall(r'<li\b[^>]*class=["\'][^"\']*\bqm-cover-text-item\b[^"\']*["\'][^>]*>([\s\S]*?)</li>', html or '', re.IGNORECASE)
    if not chunks:
        return {'ok': False, 'blocked': True, 'reason': '七猫书库页未匹配到作品列表（可能页面改版或触发风控）', 'entries': []}
    entries: list[dict[str, Any]] = []
    excluded = 0
    for chunk in chunks:
        tit_m = re.search(r'class=["\'][^"\']*\bs-tit\b[^"\']*["\'][^>]*>[\s\S]*?<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>', chunk, re.IGNORECASE)
        if not tit_m:
            continue
        href, raw_title = tit_m.group(1), _clean_html_text(tit_m.group(2))
        if not raw_title:
            continue
        id_m = re.search(r'/shuku/(\d+)', href)
        book_id = id_m.group(1) if id_m else ''

        def _cls_text(cname: str) -> str:
            m = re.search(rf'class=["\'][^"\']*\b{cname}\b[^"\']*["\'][^>]*>([\s\S]*?)</[a-zA-Z]+>', chunk, re.IGNORECASE)
            return _clean_html_text(m.group(1)) if m else ''

        author = _cls_text('s-author')
        sub_genre = _cls_text('s-category')
        if sub_genre in _QIMAO_PUBLISHED_CATEGORIES:
            excluded += 1
            continue
        status_text = _cls_text('s-status')
        words = parse_cn_number(_cls_text('s-words-num'))
        desc = _cls_text('s-desc')
        genre_raw = sub_genre or '未分类'
        entries.append({
            'rank': len(entries) + 1,
            'title': raw_title,
            'author': author,
            'genre_raw': genre_raw,
            'mapped_type_ids': map_platform_genre_to_type_ids(genre_raw, [sub_genre] if sub_genre else []),
            'status_text': status_text,
            'words': words,
            'metric_name': '',
            'metric_value': None,
            'metrics': {},
            'tags': [sub_genre] if sub_genre else [],
            'desc_text': desc[:200],
            'book_url': f'https://www.qimao.com/shuku/{book_id}/' if book_id else '',
            'book_key': norm_book_key(raw_title, author),
            'extra': {'book_id': book_id, 'excluded_published': excluded},
        })
    return {
        'ok': bool(entries),
        'blocked': False,
        'platform': 'qimao',
        'platform_name': '七猫',
        'list_name': list_label,
        'source_url': url,
        'entries': entries,
        'excluded_published': excluded,
    }


def fetch_live_chart(
    platform: str,
    rank_type: str = '',
    *,
    timeout: int = 15,
    pages: int = 2,
    fetcher: Any | None = None,
) -> dict[str, Any]:
    """Fetch a live public ranking list via stdlib HTTP without bypassing any CAPTCHA or WAF.

    An optional `fetcher(url, headers, timeout)` callable may be passed for deterministic unit testing.
    """
    pid = normalize_platform_id(platform)
    if pid not in PLATFORMS:
        raise ValueError(f'暂不支持实时采集该平台: {platform}')
    pmeta = PLATFORMS[pid]
    http_get = fetcher or (lambda u, h, t: _http_get_bytes(u, headers=h, timeout=t))

    try:
        if pid == 'qidian':
            lists = pmeta['live_lists']
            rt = next((x for x in lists if x['id'] == (rank_type or 'hotsales')), lists[0])
            url = f'https://m.qidian.com{rt["path"]}'
            status, final_url, raw = http_get(url, _MOBILE_HEADERS, timeout)
            if status != 200:
                return {'ok': False, 'blocked': True, 'reason': f'HTTP {status}', 'source_url': final_url, 'entries': []}
            return parse_qidian_mobile_ssr_html(raw.decode('utf-8', errors='replace'), list_label=rt['label'], url=final_url)

        if pid == 'fanqie':
            lists = pmeta['live_lists']
            rt = next((x for x in lists if x['id'] == (rank_type or 'hot')), lists[0])
            url = f'https://api-lf.fanqiesdk.com/api/novel/channel/homepage/rank/rank_list/v2/?aid=13&limit=25&offset=0&side_type={rt["side_type"]}'
            status, final_url, raw = http_get(url, _DESKTOP_HEADERS, timeout)
            if status != 200:
                return {'ok': False, 'blocked': True, 'reason': f'HTTP {status}', 'source_url': final_url, 'entries': []}
            try:
                data = json.loads(raw.decode('utf-8', errors='replace'))
            except ValueError as exc:
                return {'ok': False, 'blocked': True, 'reason': f'番茄接口返回非 JSON: {exc}', 'source_url': final_url, 'entries': []}
            return parse_fanqie_api_json(data, list_label=rt['label'], url=final_url)

        if pid == 'qimao':
            max_p = max(1, min(5, int(pages or 2)))
            all_entries: list[dict[str, Any]] = []
            seen: set[str] = set()
            first_url = 'https://www.qimao.com/shuku/a-a-a-1-1-a-0-click-1/'
            for p in range(1, max_p + 1):
                url = f'https://www.qimao.com/shuku/a-a-a-1-1-a-0-click-{p}/'
                status, final_url, raw = http_get(url, _DESKTOP_HEADERS, timeout)
                if status != 200:
                    if not all_entries:
                        return {'ok': False, 'blocked': True, 'reason': f'HTTP {status}', 'source_url': final_url, 'entries': []}
                    break
                parsed = parse_qimao_shuku_html(raw.decode('utf-8', errors='replace'), url=final_url)
                if not parsed['ok']:
                    if not all_entries:
                        return parsed
                    break
                for e in parsed['entries']:
                    if e['book_key'] not in seen:
                        seen.add(e['book_key'])
                        all_entries.append({**e, 'rank': len(all_entries) + 1})
            return {
                'ok': bool(all_entries),
                'blocked': not bool(all_entries),
                'platform': 'qimao',
                'platform_name': '七猫',
                'list_name': '全站书库点击新书',
                'source_url': first_url,
                'entries': all_entries,
            }

        if pid in ('jjwxc', 'ciweimao'):
            if pid == 'jjwxc':
                lists = pmeta['live_lists']
                rt = next((x for x in lists if x['id'] == (rank_type or '12')), lists[0])
                url = f'https://www.jjwxc.net/topten.php?orderstr={rt["id"]}&t=0'
                status, final_url, raw = http_get(url, _DESKTOP_HEADERS, timeout)
                if status != 200:
                    return {'ok': False, 'blocked': True, 'reason': f'HTTP {status}', 'source_url': final_url, 'entries': []}
                html = raw.decode('gb18030', errors='replace')
                if block := _detect_captcha_block(html):
                    return {'ok': False, 'blocked': True, 'reason': block, 'source_url': final_url, 'entries': []}
                entries: list[dict[str, Any]] = []
                seen_ids: set[str] = set()
                for m in re.finditer(r'href=["\'][^"\']*onebook\.php\?novelid=(\d+)["\'][^>]*>([^<]{1,40})</a>', html, re.IGNORECASE):
                    nid, title = m.group(1), _clean_html_text(m.group(2))
                    if not title or '向《' in title or nid in seen_ids:
                        continue
                    seen_ids.add(nid)
                    entries.append({
                        'rank': len(entries) + 1,
                        'title': title,
                        'author': '',
                        'genre_raw': '言情/纯爱',
                        'mapped_type_ids': ['GENRE_YANQING'],
                        'status_text': '',
                        'words': None,
                        'metric_name': '',
                        'metric_value': None,
                        'metrics': {},
                        'tags': [],
                        'desc_text': '',
                        'book_url': f'https://www.jjwxc.net/onebook.php?novelid={nid}',
                        'book_key': norm_book_key(title, ''),
                        'extra': {'novelid': nid},
                    })
                    if len(entries) >= 40:
                        break
                return {
                    'ok': bool(entries),
                    'blocked': not bool(entries),
                    'reason': '' if entries else '未解析到晋江榜条目，请改用粘贴导入模式',
                    'platform': 'jjwxc',
                    'platform_name': '晋江',
                    'list_name': rt['label'],
                    'source_url': final_url,
                    'entries': entries,
                }
            else:
                url = 'https://www.ciweimao.com/rank-index'
                status, final_url, raw = http_get(url, _DESKTOP_HEADERS, timeout)
                if status != 200:
                    return {'ok': False, 'blocked': True, 'reason': f'HTTP {status}', 'source_url': final_url, 'entries': []}
                html = raw.decode('utf-8', errors='replace')
                if block := _detect_captcha_block(html):
                    return {'ok': False, 'blocked': True, 'reason': block, 'source_url': final_url, 'entries': []}
                entries = []
                seen_ids = set()
                for m in re.finditer(r'href=["\'][^"\']*/book/(\d+)["\'][^>]*>([^<]{2,40})</a>', html, re.IGNORECASE):
                    bid, title = m.group(1), _clean_html_text(m.group(2))
                    title = re.sub(r'^\d+\[[^\]]*\]', '', title).strip()
                    if not title or bid in seen_ids:
                        continue
                    seen_ids.add(bid)
                    entries.append({
                        'rank': len(entries) + 1,
                        'title': title,
                        'author': '',
                        'genre_raw': '轻小说',
                        'mapped_type_ids': ['GENRE_QINGXIAOSHUO'],
                        'status_text': '',
                        'words': None,
                        'metric_name': '',
                        'metric_value': None,
                        'metrics': {},
                        'tags': [],
                        'desc_text': '',
                        'book_url': f'https://www.ciweimao.com/book/{bid}',
                        'book_key': norm_book_key(title, ''),
                        'extra': {'book_id': bid},
                    })
                    if len(entries) >= 30:
                        break
                return {
                    'ok': bool(entries),
                    'blocked': not bool(entries),
                    'reason': '' if entries else '未解析到刺猬猫榜条目，请改用粘贴导入模式',
                    'platform': 'ciweimao',
                    'platform_name': '刺猬猫',
                    'list_name': '刺猬猫排行榜',
                    'source_url': final_url,
                    'entries': entries,
                }

        return {'ok': False, 'blocked': True, 'reason': '该平台请使用粘贴/文件导入模式', 'entries': []}
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return {
            'ok': False,
            'blocked': True,
            'reason': f'网络采集受限或被站点拦截（{exc}）。系统严格不绕过验证码，请直接复制网页榜单文本或上传 Markdown/CSV/JSON 导入。',
            'entries': [],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Mode 2: Universal Multi-Format Paste / File Importer
# ─────────────────────────────────────────────────────────────────────────────

_MD_HEADER_RE = re.compile(r'^#\s+(.+?)\s*[·\-—]\s*(.+?)\s*$')
_MD_ENTRY_RE = re.compile(r'^#{2,3}\s+#?(\d+)\s+(.+)$')
_MD_SECTION_RE = re.compile(r'^##\s+(.+?)\s+[—\-]\s+(.+)$')
_STATUS_TOKEN_RE = re.compile(r'^(?:连载中?|已?完结|完本|暂停|断更|已完本)$')
_WORDS_TOKEN_RE = re.compile(r'^(?:字数\s*)?([\d.,]+)\s*(万)?\s*字$')
_HEAT_POST_RE = re.compile(r'^([\d.,]+)\s*(万)?\s*(在读|热度|月票|收藏|赞同|点赞|阅读|总推荐)$')
_HEAT_PRE_RE = re.compile(r'^(收藏|营养液|积分|月票|在读|热度|总推荐)\s*([\d.,]+)\s*(万)?$')


def _classify_meta_segments(segments: list[str]) -> dict[str, Any]:
    status_text = ''
    words: int | None = None
    metrics: dict[str, float] = {}
    rest: list[str] = []
    for raw in segments:
        s = raw.strip()
        if not s or s in ('[待补]', '未知', 'VIP', '免费', '签约', '已签约'):
            continue
        if _STATUS_TOKEN_RE.match(s):
            status_text = s
        elif m := _WORDS_TOKEN_RE.match(s):
            words = parse_cn_number(m.group(1) + (m.group(2) or ''))
        elif m := _HEAT_POST_RE.match(s):
            v = parse_cn_number(m.group(1) + (m.group(2) or ''))
            if v is not None:
                metrics[m.group(3)] = float(v)
        elif m := _HEAT_PRE_RE.match(s):
            v = parse_cn_number(m.group(2) + (m.group(3) or ''))
            if v is not None:
                metrics[m.group(1)] = float(v)
        else:
            rest.append(s)
    return {'status_text': status_text, 'words': words, 'metrics': metrics, 'rest': rest}


def _pick_primary_metric(metrics: dict[str, float]) -> tuple[str, float | None]:
    for key in _METRIC_PRIORITY:
        if key in metrics:
            return key, float(metrics[key])
    if metrics:
        k = next(iter(metrics))
        return k, float(metrics[k])
    return '', None


def parse_chart_import(
    raw_text: str,
    *,
    platform: str = '',
    list_name: str = '',
    fmt: str = 'auto',
) -> dict[str, Any]:
    """Parse pasted or uploaded ranking data in Markdown, JSON, CSV/TSV, or free-form copy-paste text."""
    text = (raw_text or '').lstrip('\ufeff').strip()
    if not text:
        raise ValueError('榜单导入内容不能为空')

    chosen_fmt = str(fmt or 'auto').strip().lower()
    if chosen_fmt == 'auto':
        if text.startswith(('{', '[')):
            chosen_fmt = 'json'
        elif re.search(r'^#{2,3}\s+#?\d+\s+', text, re.MULTILINE):
            chosen_fmt = 'markdown'
        elif ',' in text.splitlines()[0] and any(h in text.splitlines()[0] for h in ('书名', 'title', '作品')):
            chosen_fmt = 'csv'
        else:
            chosen_fmt = 'paste'

    inferred_platform = platform
    inferred_list = list_name
    entries: list[dict[str, Any]] = []

    if chosen_fmt == 'json':
        obj = json.loads(text)
        if isinstance(obj, dict):
            inferred_platform = inferred_platform or str(obj.get('platform') or obj.get('platform_name') or '')
            inferred_list = inferred_list or str(obj.get('list_name') or obj.get('list') or '导入榜单')
            rows = obj.get('entries') or obj.get('books') or obj.get('items') or []
        elif isinstance(obj, list):
            rows = obj
        else:
            raise ValueError('JSON 榜单必须是对象或数组')
        for idx, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                continue
            title = str(row.get('title') or row.get('book_name') or row.get('书名') or '').strip()
            if not title:
                continue
            author = str(row.get('author') or row.get('作者') or '').strip()
            genre_raw = str(row.get('genre') or row.get('genre_raw') or row.get('category') or row.get('题材') or '未分类').strip()
            raw_tags = row.get('tags') or row.get('标签') or []
            if isinstance(raw_tags, str):
                tags = [t.strip() for t in re.split(r'[、,，+/／|\s]+', raw_tags) if t.strip()]
            elif isinstance(raw_tags, list):
                tags = [str(t).strip() for t in raw_tags if str(t).strip()]
            else:
                tags = []
            metrics: dict[str, float] = {}
            if isinstance(row.get('metrics'), dict):
                for k, v in row['metrics'].items():
                    nv = parse_cn_number(v)
                    if nv is not None:
                        metrics[str(k)] = float(nv)
            for mk, alias in (('在读', 'reads'), ('热度', 'heat'), ('收藏', 'collect'), ('总推荐', 'recommend'), ('月票', 'yuepiao')):
                val = row.get(mk) if row.get(mk) is not None else row.get(alias)
                nv = parse_cn_number(val)
                if nv is not None:
                    metrics[mk] = float(nv)
            pname, pval = _pick_primary_metric(metrics)
            entries.append({
                'rank': int(row.get('rank') or row.get('排名') or idx),
                'title': title,
                'author': author,
                'genre_raw': genre_raw,
                'mapped_type_ids': map_platform_genre_to_type_ids(genre_raw, tags),
                'status_text': str(row.get('status') or row.get('状态') or '').strip(),
                'words': parse_cn_number(row.get('words') or row.get('字数')),
                'metric_name': pname,
                'metric_value': pval,
                'metrics': metrics,
                'tags': tags,
                'desc_text': str(row.get('desc') or row.get('desc_text') or row.get('简介') or '').strip()[:240],
                'book_url': str(row.get('url') or row.get('book_url') or '').strip(),
                'book_key': norm_book_key(title, author),
                'extra': {},
            })

    elif chosen_fmt == 'csv':
        reader = csv.DictReader(io.StringIO(text))
        for idx, row in enumerate(reader, start=1):
            title = str(row.get('书名') or row.get('title') or row.get('作品') or '').strip()
            if not title:
                continue
            author = str(row.get('作者') or row.get('author') or '').strip()
            genre_raw = str(row.get('题材') or row.get('分类') or row.get('genre') or '未分类').strip()
            tags_raw = str(row.get('标签') or row.get('tags') or '').strip()
            tags = [t.strip() for t in re.split(r'[、,，+/／|\s]+', tags_raw) if t.strip()]
            metrics = {}
            for col, mname in (('在读', '在读'), ('热度', '热度'), ('收藏', '收藏'), ('总推荐', '总推荐'), ('月票', '月票'), ('heat', '热度')):
                if row.get(col):
                    nv = parse_cn_number(row[col])
                    if nv is not None:
                        metrics[mname] = float(nv)
            pname, pval = _pick_primary_metric(metrics)
            entries.append({
                'rank': parse_cn_number(row.get('排名') or row.get('rank')) or idx,
                'title': title,
                'author': author,
                'genre_raw': genre_raw,
                'mapped_type_ids': map_platform_genre_to_type_ids(genre_raw, tags),
                'status_text': str(row.get('状态') or row.get('status') or '').strip(),
                'words': parse_cn_number(row.get('字数') or row.get('words')),
                'metric_name': pname,
                'metric_value': pval,
                'metrics': metrics,
                'tags': tags,
                'desc_text': str(row.get('简介') or row.get('desc') or '').strip()[:240],
                'book_url': str(row.get('链接') or row.get('url') or '').strip(),
                'book_key': norm_book_key(title, author),
                'extra': {},
            })

    elif chosen_fmt == 'markdown':
        lines = text.splitlines()
        section = ''
        current: dict[str, Any] | None = None

        def _flush() -> None:
            nonlocal current
            if not current:
                return
            cls = _classify_meta_segments(current['meta_segs'])
            metrics = {**cls['metrics'], **current['metrics']}
            words = current['words'] if current['words'] is not None else cls['words']
            rest = cls['rest']
            author = rest[0] if len(rest) >= 1 else ''
            meta_genre = rest[1] if len(rest) >= 2 else ''
            tags = list(current['tags'])
            for ex in rest[2:]:
                tags.extend([t.strip() for t in re.split(r'[、,，+/／|\s]+', ex) if t.strip()])
            if '·' in meta_genre:
                parts = [p.strip() for p in meta_genre.split('·') if p.strip()]
                meta_genre = parts[0]
                tags.extend(parts[1:])
            genre_raw = meta_genre or (section if section and not section.startswith('全部') else '') or '未分类'
            tags = list(dict.fromkeys(tags))[:10]
            pname, pval = _pick_primary_metric(metrics)
            entries.append({
                'rank': current['rank'],
                'title': current['title'],
                'author': author,
                'genre_raw': genre_raw,
                'mapped_type_ids': map_platform_genre_to_type_ids(genre_raw, tags),
                'status_text': cls['status_text'],
                'words': words,
                'metric_name': pname,
                'metric_value': pval,
                'metrics': metrics,
                'tags': tags,
                'desc_text': ' '.join(current['desc']).strip()[:240],
                'book_url': current['url'],
                'book_key': norm_book_key(current['title'], author),
                'extra': {'section': section},
            })
            current = None

        in_desc = False
        for raw_ln in lines:
            ln = raw_ln.strip()
            if not ln or ln == '---':
                continue
            if not inferred_platform or not inferred_list:
                if hm := _MD_HEADER_RE.match(ln):
                    inferred_platform = inferred_platform or hm.group(1).strip()
                    inferred_list = inferred_list or hm.group(2).strip()
                    continue
            if em := _MD_ENTRY_RE.match(ln):
                _flush()
                in_desc = False
                current = {
                    'rank': int(em.group(1)),
                    'title': em.group(2).strip(),
                    'meta_segs': [],
                    'tags': [],
                    'metrics': {},
                    'words': None,
                    'desc': [],
                    'url': '',
                }
                continue
            if sm := _MD_SECTION_RE.match(ln):
                _flush()
                section = sm.group(1).strip()
                in_desc = False
                continue
            if current is None:
                continue
            if not current['meta_segs'] and ln.startswith('*') and ln.endswith('*') and len(ln) > 2:
                current['meta_segs'] = [s.strip() for s in re.split(r'\s+·\s+', ln[1:-1])]
            elif tm := re.match(r'^\*\*标签[：:]\*\*\s*(.+)$', ln):
                current['tags'].extend([t.strip() for t in re.split(r'[、,，+/／|\s]+', tm.group(1)) if t.strip()])
                in_desc = False
            elif wm := re.match(r'^\*\*字数[：:]\s*(.+?)\*\*$', ln):
                current['words'] = parse_cn_number(wm.group(1))
            elif mm := re.match(r'^\*\*(总推荐|榜单值|月票|收藏|在读|热度)[：:]\s*(.+?)\*\*$', ln):
                nv = parse_cn_number(mm.group(2))
                if nv is not None:
                    current['metrics'][mm.group(1)] = float(nv)
            elif ln == '**简介**':
                in_desc = True
            elif um := re.search(r'\[作品页\]\((https?://[^)]+)\)', ln):
                current['url'] = um.group(1)
                in_desc = False
            elif ln.startswith('>'):
                current['desc'].append(ln.lstrip('> ').strip())
            elif in_desc and not ln.startswith('**'):
                current['desc'].append(ln)
        _flush()

    else:
        # Free-form copy-paste parser (handles raw numbered lines copied from Qidian/Fanqie/Qimao/JJWXC)
        blocks: list[list[str]] = []
        cur_block: list[str] = []
        for raw_ln in text.splitlines():
            ln = raw_ln.strip()
            if not ln:
                if cur_block:
                    blocks.append(cur_block)
                    cur_block = []
                continue
            if re.match(r'^(?:#?\d{1,3}[\.、\s]|第\d{1,3}名|\d{1,2}$)', ln) and cur_block:
                blocks.append(cur_block)
                cur_block = [ln]
            else:
                cur_block.append(ln)
        if cur_block:
            blocks.append(cur_block)

        for idx, blk in enumerate(blocks, start=1):
            joined = ' | '.join(blk)
            first = blk[0]
            rank_val = idx
            title_cand = first
            if rm := re.match(r'^(?:#?(\d{1,3})[\.、\s]+|第(\d{1,3})名\s*)(.+)$', first):
                rank_val = int(rm.group(1) or rm.group(2))
                title_cand = rm.group(3).strip()
            elif re.fullmatch(r'\d{1,2}', first) and len(blk) >= 2:
                rank_val = int(first)
                title_cand = blk[1]
                blk = blk[1:]
            # Split inline separators `·` / `|` / `\t`
            segs = [s.strip() for s in re.split(r'\s*[|｜\t·/]\s*', title_cand) if s.strip()]
            title = segs[0].strip('《》「」') if segs else title_cand
            if not title or len(title) > 60:
                continue
            extra_segs = segs[1:] + [s.strip() for ln in blk[1:] for s in re.split(r'\s*[|｜\t·]\s*', ln) if s.strip()]
            cls = _classify_meta_segments(extra_segs)
            rest = cls['rest']
            author = rest[0][:24] if rest and len(rest[0]) <= 24 else ''
            genre_raw = rest[1][:20] if len(rest) >= 2 and len(rest[1]) <= 20 else '未分类'
            desc = ' '.join(r for r in rest[2:] if len(r) >= 12)[:220]
            tags: list[str] = []
            if bm := re.search(r'[【\[]([^】\]]{2,40})[】\]]', joined):
                tags.extend([t.strip() for t in re.split(r'[+、,/／\s]+', bm.group(1)) if t.strip()][:6])
            pname, pval = _pick_primary_metric(cls['metrics'])
            entries.append({
                'rank': rank_val,
                'title': title,
                'author': author,
                'genre_raw': genre_raw,
                'mapped_type_ids': map_platform_genre_to_type_ids(genre_raw, tags),
                'status_text': cls['status_text'],
                'words': cls['words'],
                'metric_name': pname,
                'metric_value': pval,
                'metrics': cls['metrics'],
                'tags': tags,
                'desc_text': desc,
                'book_url': '',
                'book_key': norm_book_key(title, author),
                'extra': {},
            })

    if not entries:
        raise ValueError('未能从输入中解析出有效榜单条目，请检查格式（支持 Markdown / CSV / JSON / 网页复制文本）')

    pid = normalize_platform_id(inferred_platform or 'custom')
    pname = platform_display_name(pid, fallback=inferred_platform)
    return {
        'ok': True,
        'platform': pid,
        'platform_name': pname,
        'list_name': (inferred_list or '导入榜单').strip(),
        'source_mode': f'manual_{chosen_fmt}',
        'source_url': '',
        'entries': entries,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SQLite Persistence & Deterministic Multi-List Aggregation / Trend Diff
# ─────────────────────────────────────────────────────────────────────────────

def _snapshot_signature(platform: str, entries: list[dict[str, Any]]) -> str:
    body = platform + '\n' + '\n'.join(f"{e['rank']}|{e['book_key']}" for e in entries)
    return hashlib.sha256(body.encode('utf-8')).hexdigest()


def save_chart_snapshot(
    conn: sqlite3.Connection,
    parsed: dict[str, Any],
    *,
    captured_date: str = '',
) -> dict[str, Any]:
    """Persist a crawled or imported chart snapshot + entries into `library.db`."""
    ensure_chart_radar_tables(conn)
    entries = list(parsed.get('entries') or ())
    if not entries:
        raise ValueError('榜单快照条目为空，无法入库')
    ts = timestamp()
    day = (captured_date or ts[:10]).strip()[:10]
    sid = f'csnp-{uuid4().hex[:12]}'
    pid = normalize_platform_id(parsed.get('platform') or 'custom')
    pname = platform_display_name(pid, fallback=str(parsed.get('platform_name') or ''))
    list_name = str(parsed.get('list_name') or '榜单').strip()[:100]
    sig = _snapshot_signature(pid, entries)

    quality_notes: list[str] = []
    missing_genre = sum(1 for e in entries if not e.get('genre_raw') or e.get('genre_raw') == '未分类')
    if missing_genre > len(entries) * 0.5:
        quality_notes.append(f'题材缺失 {missing_genre}/{len(entries)} 条')
    sparse_cap = PLATFORMS.get(pid, {}).get('sparse_threshold', 15)
    if len(entries) < sparse_cap:
        quality_notes.append(f'样本偏少（仅 {len(entries)} 条，门槛 {sparse_cap} 条）')
    quality_status = '[存在问题]' if quality_notes else '[OK]'

    conn.execute(
        '''INSERT INTO chart_snapshots
           (id, platform, platform_name, list_name, source_mode, source_url, captured_date,
            entry_count, quality_status, quality_notes_json, signature_sha256, meta_json, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (
            sid, pid, pname, list_name,
            str(parsed.get('source_mode') or 'live_http'),
            str(parsed.get('source_url') or ''),
            day, len(entries), quality_status, encode(quality_notes), sig,
            encode({'excluded_published': parsed.get('excluded_published', 0)}), ts,
        ),
    )
    for e in entries:
        eid = f'cent-{uuid4().hex[:12]}'
        conn.execute(
            '''INSERT INTO chart_entries
               (id, snapshot_id, rank, title, author, genre_raw, mapped_type_ids_json,
                status_text, words, metric_name, metric_value, metrics_json, tags_json,
                desc_text, book_url, book_key, extra_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (
                eid, sid, int(e.get('rank') or 0), str(e['title'])[:120], str(e.get('author') or '')[:80],
                str(e.get('genre_raw') or '未分类')[:60], encode(e.get('mapped_type_ids') or []),
                str(e.get('status_text') or '')[:30], e.get('words'),
                str(e.get('metric_name') or '')[:30], e.get('metric_value'),
                encode(e.get('metrics') or {}), encode(e.get('tags') or []),
                str(e.get('desc_text') or '')[:300], str(e.get('book_url') or '')[:300],
                str(e.get('book_key') or norm_book_key(e['title'], str(e.get('author') or ''))),
                encode(e.get('extra') or {}),
            ),
        )
    return get_chart_snapshot(conn, sid)


def list_chart_snapshots(
    conn: sqlite3.Connection,
    *,
    platform: str = '',
    limit: int = 50,
) -> list[dict[str, Any]]:
    ensure_chart_radar_tables(conn)
    if platform:
        pid = normalize_platform_id(platform)
        rows = conn.execute(
            'SELECT * FROM chart_snapshots WHERE platform=? ORDER BY captured_date DESC, created_at DESC LIMIT ?',
            (pid, max(1, int(limit))),
        ).fetchall()
    else:
        rows = conn.execute(
            'SELECT * FROM chart_snapshots ORDER BY captured_date DESC, created_at DESC LIMIT ?',
            (max(1, int(limit)),),
        ).fetchall()
    return [
        {
            'id': r['id'],
            'platform': r['platform'],
            'platform_name': r['platform_name'],
            'list_name': r['list_name'],
            'source_mode': r['source_mode'],
            'source_url': r['source_url'],
            'captured_date': r['captured_date'],
            'entry_count': int(r['entry_count']),
            'quality_status': r['quality_status'],
            'quality_notes': json.loads(r['quality_notes_json'] or '[]'),
            'signature_sha256': r['signature_sha256'],
            'created_at': r['created_at'],
        }
        for r in rows
    ]


def get_chart_snapshot(conn: sqlite3.Connection, snapshot_id: str) -> dict[str, Any]:
    ensure_chart_radar_tables(conn)
    row = conn.execute('SELECT * FROM chart_snapshots WHERE id=?', (snapshot_id,)).fetchone()
    if row is None:
        raise FileNotFoundError(f'榜单快照不存在: {snapshot_id}')
    entries = conn.execute(
        'SELECT * FROM chart_entries WHERE snapshot_id=? ORDER BY rank ASC, rowid ASC', (snapshot_id,)
    ).fetchall()
    return {
        'id': row['id'],
        'platform': row['platform'],
        'platform_name': row['platform_name'],
        'list_name': row['list_name'],
        'source_mode': row['source_mode'],
        'source_url': row['source_url'],
        'captured_date': row['captured_date'],
        'entry_count': int(row['entry_count']),
        'quality_status': row['quality_status'],
        'quality_notes': json.loads(row['quality_notes_json'] or '[]'),
        'signature_sha256': row['signature_sha256'],
        'created_at': row['created_at'],
        'entries': [
            {
                'id': e['id'],
                'rank': int(e['rank']),
                'title': e['title'],
                'author': e['author'],
                'genre_raw': e['genre_raw'],
                'mapped_type_ids': json.loads(e['mapped_type_ids_json'] or '[]'),
                'status_text': e['status_text'],
                'words': e['words'],
                'metric_name': e['metric_name'],
                'metric_value': e['metric_value'],
                'metrics': json.loads(e['metrics_json'] or '{}'),
                'tags': json.loads(e['tags_json'] or '[]'),
                'desc_text': e['desc_text'],
                'book_url': e['book_url'],
                'book_key': e['book_key'],
            }
            for e in entries
        ],
    }


def _title_bigrams(titles: list[str], min_count: int = 2) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for t in titles:
        clean = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', str(t or ''))
        seen = {clean[i:i + 2] for i in range(max(0, len(clean) - 1))}
        for g in seen:
            counts[g] += 1
    return [
        {'gram': gram, 'count': cnt}
        for gram, cnt in counts.most_common(20)
        if cnt >= min_count
    ]


def _quantile(sorted_vals: list[float], q: float) -> float | None:
    if not sorted_vals:
        return None
    idx = min(len(sorted_vals) - 1, int(q * (len(sorted_vals) - 1) + 0.5))
    return round(sorted_vals[idx], 1)


def aggregate_chart_snapshots(
    conn: sqlite3.Connection,
    *,
    snapshot_ids: list[str] | tuple[str, ...] | None = None,
    platform: str = '',
    top_reps: int = 3,
) -> dict[str, Any]:
    """Deterministically aggregate multi-list chart snapshots (oh-story `aggregate-rank` philosophy).

    - Deduplicates identical mirror lists (`signature_sha256`) so overlap is never inflated.
    - Deduplicates books per platform by `book_key` (`norm(title)|norm(author)`).
    - Separates `new_book` lists from legacy million-word lists.
    - Computes genre counts, shares, heat median & quartiles, word buckets, title bigrams,
      multi-list dark horses, and maps genres onto our 35-main/425-sub Type KB!
    """
    ensure_chart_radar_tables(conn)
    if snapshot_ids:
        snaps = [get_chart_snapshot(conn, sid) for sid in snapshot_ids]
    else:
        meta_list = list_chart_snapshots(conn, platform=platform, limit=30)
        snaps = [get_chart_snapshot(conn, m['id']) for m in meta_list]

    # Mark duplicate lists by exact signature
    seen_sigs: dict[str, str] = {}
    active_snaps: list[dict[str, Any]] = []
    skipped_duplicates: list[dict[str, str]] = []
    for snap in snaps:
        sig = snap.get('signature_sha256') or ''
        if sig and sig in seen_sigs:
            skipped_duplicates.append({'snapshot_id': snap['id'], 'list_name': snap['list_name'], 'duplicate_of': seen_sigs[sig]})
            continue
        if sig:
            seen_sigs[sig] = snap['list_name']
        active_snaps.append(snap)

    by_platform: dict[str, list[dict[str, Any]]] = {}
    for snap in active_snaps:
        by_platform.setdefault(snap['platform'], []).append(snap)

    word_buckets_def = (
        ('10万字以下', 0, 100_000),
        ('10-30万字', 100_000, 300_000),
        ('30-50万字', 300_000, 500_000),
        ('50-100万字', 500_000, 1_000_000),
        ('100-200万字', 1_000_000, 2_000_000),
        ('200万字以上', 2_000_000, 10**12),
    )

    platforms_out: list[dict[str, Any]] = []
    for pid, p_snaps in by_platform.items():
        pname = p_snaps[0]['platform_name']
        sparse_min = PLATFORMS.get(pid, {}).get('sparse_threshold', 15)
        books: dict[str, dict[str, Any]] = {}
        has_new_list = False
        has_other_list = False

        for snap in p_snaps:
            is_new = bool(_NEW_LIST_RE.search(snap['list_name']))
            if is_new:
                has_new_list = True
            else:
                has_other_list = True
            for e in snap['entries']:
                bk = e['book_key'] or norm_book_key(e['title'], e['author'])
                existing = books.get(bk)
                if existing is None:
                    books[bk] = {
                        **e,
                        'lists': [snap['list_name']],
                        'best_rank': e['rank'],
                        'in_new_list': is_new,
                        'in_other_list': not is_new,
                        'metrics': dict(e.get('metrics') or {}),
                        'tags': list(e.get('tags') or []),
                        'mapped_type_ids': list(e.get('mapped_type_ids') or []),
                    }
                else:
                    if snap['list_name'] not in existing['lists']:
                        existing['lists'].append(snap['list_name'])
                    existing['best_rank'] = min(existing['best_rank'], e['rank'])
                    existing['in_new_list'] = existing['in_new_list'] or is_new
                    existing['in_other_list'] = existing['in_other_list'] or (not is_new)
                    for k, v in (e.get('metrics') or {}).items():
                        if k not in existing['metrics'] or float(v) > float(existing['metrics'][k]):
                            existing['metrics'][k] = float(v)
                    for t in (e.get('tags') or ()):
                        if t not in existing['tags']:
                            existing['tags'].append(t)
                    for tid in (e.get('mapped_type_ids') or ()):
                        if tid not in existing['mapped_type_ids']:
                            existing['mapped_type_ids'].append(tid)
                    if existing['words'] is None and e['words'] is not None:
                        existing['words'] = e['words']
                    if not existing['desc_text'] and e['desc_text']:
                        existing['desc_text'] = e['desc_text']
                    if existing['genre_raw'] == '未分类' and e['genre_raw'] != '未分类':
                        existing['genre_raw'] = e['genre_raw']

        uniq = list(books.values())
        metric_counts: Counter[str] = Counter()
        for b in uniq:
            for k in b['metrics']:
                metric_counts[k] += 1
        chosen_metric = ''
        for k in _METRIC_PRIORITY:
            if metric_counts.get(k, 0) >= max(1, int(len(uniq) * 0.25)):
                chosen_metric = k
                break
        if not chosen_metric and metric_counts:
            chosen_metric = metric_counts.most_common(1)[0][0]

        def _heat_of(book: dict[str, Any]) -> float | None:
            if chosen_metric and chosen_metric in book['metrics']:
                return float(book['metrics'][chosen_metric])
            return None

        # Per-genre aggregation
        by_genre: dict[str, list[dict[str, Any]]] = {}
        for b in uniq:
            by_genre.setdefault(b['genre_raw'] or '未分类', []).append(b)

        genres_rows: list[dict[str, Any]] = []
        for gname, gbooks in by_genre.items():
            gbooks_sorted = sorted(gbooks, key=lambda b: (-(_heat_of(b) or -1.0), b['best_rank']))
            heats = [_heat_of(b) for b in gbooks if _heat_of(b) is not None]
            words_list = [int(b['words']) for b in gbooks if isinstance(b.get('words'), int)]
            show_heat = len(heats) == len(gbooks) or len(heats) >= _MIN_HEAT_KNOWN
            tag_counts = Counter(t for b in gbooks for t in b['tags'])
            type_counts = Counter(tid for b in gbooks for tid in b['mapped_type_ids'])
            genres_rows.append({
                'genre': gname,
                'count': len(gbooks),
                'share': round(len(gbooks) / max(1, len(uniq)), 3),
                'new_count': sum(1 for b in gbooks if b['in_new_list']),
                'heat_median': round(float(median(heats)), 1) if (heats and show_heat) else None,
                'heat_median_label': format_cn_number(median(heats)) if (heats and show_heat) else '—',
                'heat_known': len(heats),
                'words_median': int(median(words_list)) if words_list else None,
                'words_median_label': format_cn_number(median(words_list)) if words_list else '—',
                'top_tags': [t for t, _ in tag_counts.most_common(4)],
                'mapped_type_ids': [tid for tid, _ in type_counts.most_common(2)],
                'sparse': len(gbooks) < sparse_min,
                'representatives': [
                    {
                        'title': b['title'],
                        'author': b['author'],
                        'best_rank': b['best_rank'],
                        'heat': _heat_of(b),
                        'heat_label': format_cn_number(_heat_of(b)),
                        'words': b['words'],
                        'words_label': format_cn_number(b['words']),
                        'tags': b['tags'][:4],
                        'lists': b['lists'],
                        'desc_text': b['desc_text'][:90],
                        'book_url': b['book_url'],
                    }
                    for b in gbooks_sorted[:top_reps]
                ],
            })
        genres_rows.sort(key=lambda r: (-r['count'], -(r['heat_median'] or 0.0), r['genre']))

        all_heats = sorted(_heat_of(b) for b in uniq if _heat_of(b) is not None)
        all_words = [int(b['words']) for b in uniq if isinstance(b.get('words'), int)]
        buckets = [
            {'label': lbl, 'count': sum(1 for w in all_words if lo <= w < hi)}
            for lbl, lo, hi in word_buckets_def
        ]
        overlaps = [
            {
                'title': b['title'],
                'author': b['author'],
                'genre': b['genre_raw'],
                'lists': b['lists'],
                'list_count': len(b['lists']),
                'in_new_list': b['in_new_list'],
                'heat_label': format_cn_number(_heat_of(b)),
            }
            for b in sorted(
                (b for b in uniq if len(b['lists']) >= 2),
                key=lambda x: (-len(x['lists']), -(_heat_of(x) or 0.0), x['best_rank']),
            )[:15]
        ]

        platforms_out.append({
            'platform': pid,
            'platform_name': pname,
            'snapshot_ids': [s['id'] for s in p_snaps],
            'lists': [s['list_name'] for s in p_snaps],
            'book_count': len(uniq),
            'sparse_threshold': sparse_min,
            'primary_metric': chosen_metric,
            'compare_new': has_new_list and has_other_list,
            'heat_distribution': (
                {
                    'known': len(all_heats),
                    'p25': _quantile(all_heats, 0.25),
                    'p50': _quantile(all_heats, 0.50),
                    'p75': _quantile(all_heats, 0.75),
                    'max': _quantile(all_heats, 1.0),
                    'p50_label': format_cn_number(_quantile(all_heats, 0.50)),
                    'p75_label': format_cn_number(_quantile(all_heats, 0.75)),
                }
                if all_heats else None
            ),
            'words_distribution': {
                'known': len(all_words),
                'median': int(median(all_words)) if all_words else None,
                'median_label': format_cn_number(median(all_words)) if all_words else '—',
                'buckets': buckets,
            },
            'genres': genres_rows,
            'hot_tags': [{'tag': t, 'count': c} for t, c in Counter(t for b in uniq for t in b['tags']).most_common(25)],
            'title_bigrams': _title_bigrams([b['title'] for b in uniq], min_count=2),
            'multi_list_overlaps': overlaps,
        })

    platforms_out.sort(key=lambda p: (-p['book_count'], p['platform']))
    return {
        'snapshot_count': len(active_snaps),
        'skipped_duplicates': skipped_duplicates,
        'platforms': platforms_out,
    }


def diff_chart_snapshots(
    conn: sqlite3.Connection,
    *,
    current_snapshot_ids: list[str],
    baseline_snapshot_ids: list[str],
) -> dict[str, Any]:
    """Period-over-period trend diff between current chart snapshots and earlier baseline snapshots."""
    cur_agg = aggregate_chart_snapshots(conn, snapshot_ids=current_snapshot_ids)
    base_agg = aggregate_chart_snapshots(conn, snapshot_ids=baseline_snapshot_ids)

    base_by_plat = {p['platform']: p for p in base_agg['platforms']}
    diffs: list[dict[str, Any]] = []

    for cp in cur_agg['platforms']:
        pid = cp['platform']
        bp = base_by_plat.get(pid)
        if not bp:
            continue
        base_genres = {g['genre']: g for g in bp['genres']}
        genre_trends: list[dict[str, Any]] = []
        for g in cp['genres']:
            bg = base_genres.get(g['genre'])
            base_share = bg['share'] if bg else 0.0
            share_delta = round(g['share'] - base_share, 3)
            heat_delta_pct = None
            if bg and bg['heat_median'] and g['heat_median']:
                heat_delta_pct = round(((g['heat_median'] - bg['heat_median']) / max(1.0, bg['heat_median'])) * 100, 1)
            trend = 'rising' if (share_delta >= 0.03 or (heat_delta_pct is not None and heat_delta_pct >= 15.0)) else (
                'cooling' if (share_delta <= -0.03 or (heat_delta_pct is not None and heat_delta_pct <= -15.0)) else 'stable'
            )
            genre_trends.append({
                'genre': g['genre'],
                'current_count': g['count'],
                'baseline_count': bg['count'] if bg else 0,
                'share_delta': share_delta,
                'heat_delta_pct': heat_delta_pct,
                'trend': trend,
            })
        genre_trends.sort(key=lambda r: (-r['share_delta'], -(r['heat_delta_pct'] or 0.0)))

        base_tags = {t['tag']: t['count'] for t in bp['hot_tags']}
        rising_tags = [
            {'tag': t['tag'], 'current': t['count'], 'delta': t['count'] - base_tags.get(t['tag'], 0)}
            for t in cp['hot_tags']
            if t['count'] > base_tags.get(t['tag'], 0)
        ][:10]

        base_keys = {
            e['book_key']
            for sid in baseline_snapshot_ids
            for e in get_chart_snapshot(conn, sid)['entries']
        }
        new_entrants = []
        seen_new: set[str] = set()
        for sid in current_snapshot_ids:
            snap = get_chart_snapshot(conn, sid)
            if snap['platform'] != pid:
                continue
            for e in snap['entries']:
                if e['book_key'] not in base_keys and e['book_key'] not in seen_new:
                    seen_new.add(e['book_key'])
                    new_entrants.append({
                        'title': e['title'],
                        'author': e['author'],
                        'genre': e['genre_raw'],
                        'rank': e['rank'],
                        'list_name': snap['list_name'],
                    })

        new_entrants.sort(key=lambda x: (x['rank'], x['title']))
        diffs.append({
            'platform': pid,
            'platform_name': cp['platform_name'],
            'genre_trends': genre_trends,
            'rising_tags': rising_tags,
            'new_entrants': new_entrants[:15],
        })
    return {'diffs': diffs, 'has_baseline': bool(diffs)}


# ─────────────────────────────────────────────────────────────────────────────
# Evidence-Grounded Topic Decision Generator & Verification Backfill
# ─────────────────────────────────────────────────────────────────────────────

def _row_to_topic(row: sqlite3.Row) -> dict[str, Any]:
    return {
        'id': row['id'],
        'title': row['title'],
        'platforms': json.loads(row['platforms_json'] or '[]'),
        'snapshot_ids': json.loads(row['snapshot_ids_json'] or '[]'),
        'primary_genre_id': row['primary_genre_id'],
        'genre_tags': json.loads(row['genre_tags_json'] or '[]'),
        'target_reader': row['target_reader'],
        'core_hook': row['core_hook'],
        'why_it_works': row['why_it_works'],
        'differentiation': row['differentiation'],
        'feasibility': row['feasibility'],
        'feasibility_reason': row['feasibility_reason'],
        'risks': row['risks'],
        'validation_action': row['validation_action'],
        'benchmark_books': json.loads(row['benchmark_books_json'] or '[]'),
        'verification_status': row['verification_status'],
        'verified_by_book_id': row['verified_by_book_id'],
        'verification_note': row['verification_note'],
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
    }


def list_topic_decisions(conn: sqlite3.Connection, *, limit: int = 30) -> list[dict[str, Any]]:
    ensure_chart_radar_tables(conn)
    rows = conn.execute(
        'SELECT * FROM topic_decisions ORDER BY updated_at DESC LIMIT ?', (max(1, int(limit)),)
    ).fetchall()
    return [_row_to_topic(r) for r in rows]


def generate_topic_decisions(
    conn: sqlite3.Connection,
    *,
    snapshot_ids: list[str] | tuple[str, ...] | None = None,
    platform: str = '',
    author_focus: str = '',
    provider: LLMProvider | None = None,
    model: str = '',
    params: dict[str, Any] | None = None,
    max_topics: int = 3,
) -> dict[str, Any]:
    """Generate 2–3 evidence-grounded topic decisions strictly obeying sample & feasibility caps."""
    agg = aggregate_chart_snapshots(conn, snapshot_ids=snapshot_ids, platform=platform)
    if not agg['platforms']:
        raise ValueError('当前没有可用于选题决策的榜单快照，请先采集或导入至少一份榜单')

    candidates: list[dict[str, Any]] = []
    for p in agg['platforms']:
        p50 = (p.get('heat_distribution') or {}).get('p50')
        overlaps_by_genre = Counter(o['genre'] for o in p.get('multi_list_overlaps', ()))
        for g in p['genres']:
            if g['genre'] == '未分类' and len(p['genres']) > 1:
                continue
            cross_list = overlaps_by_genre.get(g['genre'], 0) > 0 or (p['compare_new'] and g['new_count'] > 0)
            above_median = (g['heat_median'] is not None and p50 is not None and g['heat_median'] >= p50)
            # Strict feasibility cap rule (adopted from oh-story topic-decision rubric)
            if not g['sparse'] and cross_list and (above_median or not p['primary_metric']):
                feasibility = 'high'
                feas_reason = (
                    f'{p["platform_name"]}「{g["genre"]}」样本充足（{g["count"]} 本，占 {int(g["share"]*100)}%），'
                    f'具备新书榜/多榜跨榜印证且热度达到同批中位以上。'
                )
            else:
                feasibility = 'medium'
                cap_reasons = []
                if g['sparse']:
                    cap_reasons.append(f'当前样本仅 {g["count"]} 本（低于门槛 {p["sparse_threshold"]} 本）')
                if not cross_list:
                    cap_reasons.append('缺少新书榜/多榜跨榜印证或上期对比')
                if not above_median and p['primary_metric'] and g['heat_median'] is not None:
                    cap_reasons.append('热度中位低于全批中位线')
                feas_reason = f'上限压至「中」：{"；".join(cap_reasons) or "单期首扫建议小成本试水"}。'

            reps = g['representatives']
            top_tags = g['top_tags'] or [t['tag'] for t in p['hot_tags'][:2]]
            tag_str = ' + '.join(top_tags[:3]) if top_tags else '强冲突切入'
            primary_gid = g['mapped_type_ids'][0] if g['mapped_type_ids'] else ''
            benchmarks = [
                {'title': r['title'], 'author': r['author'], 'platform': p['platform_name'], 'heat': r['heat_label']}
                for r in reps[:2]
            ]
            candidates.append({
                'score': (2 if feasibility == 'high' else 1, g['new_count'], g['count'], g['heat_median'] or 0.0),
                'title': f'{g["genre"]} · {tag_str}差异化方向（{p["platform_name"]}）',
                'platforms': [p['platform_name']],
                'snapshot_ids': list(p['snapshot_ids']),
                'primary_genre_id': primary_gid,
                'genre_tags': list(g['mapped_type_ids']) or ([primary_gid] if primary_gid else []),
                'target_reader': f'{p["platform_name"]}「{g["genre"]}」追读读者（高频偏好：{tag_str}）',
                'core_hook': f'以「{g["genre"]}」高频刚需为底座，叠加「{tag_str}」反差开局，前 3 章必须落地核心卖点与首次小回报。',
                'why_it_works': (
                    f'本次 {p["platform_name"]} 扫榜共聚合 {g["count"]} 本同类样本（新书信号 {g["new_count"]} 本，'
                    f'热度中位 {g["heat_median_label"]}，字数中位 {g["words_median_label"]}）。'
                    '【待拆文验证：需拆解 1–2 本新书对标验证黄金三章节奏与爽点引擎。】'
                ),
                'differentiation': (
                    f'避开榜上头部老书的百万字套路堆叠，结合自身优势（{author_focus or "更贴身的真实利害博弈与高辨识人设"}）做切入点与代价机制差异化。'
                ),
                'feasibility': feasibility,
                'feasibility_reason': feas_reason,
                'risks': f'若直接沿用榜上头部老书模板极易同质化；须避开空洞开篇设定说明与前 3 章无兑现风险。',
                'validation_action': (
                    '先挑下方 1–2 本对标新书送入「预存库」做黄金三章与情绪模块拆解，再试写前 3 章测追读留存。'
                    + (f' {platform_monetization_brief(p["platform"])}' if platform_monetization_brief(p['platform']) else '')
                )[:380],
                'benchmark_books': benchmarks,
            })

    candidates.sort(key=lambda c: c['score'], reverse=True)
    picked = candidates[:max(1, min(5, int(max_topics or 3)))]

    # Optional LLM polish (strictly grounded in aggregated facts, preserving feasibility caps!)
    if provider is not None and model and picked:
        prompt_summary = json.dumps(
            [{'title': c['title'], 'why': c['why_it_works'], 'feasibility': c['feasibility'], 'benchmarks': c['benchmark_books']} for c in picked],
            ensure_ascii=False,
        )
        messages = [
            {
                'role': 'system',
                'content': (
                    '你是资深网文选题策划。仅基于提供的真实扫榜统计，为每个选题方向提炼更具商业辨识度的'
                    '核心卖点（core_hook）、差异化定位（differentiation）与最大失败风险（risks）。'
                    '严禁虚构数据、严禁照搬对标书名或角色配置。严格输出 JSON：{"items":[{"core_hook":"...","differentiation":"...","risks":"..."}]}'
                ),
            },
            {'role': 'user', 'content': f'作者偏好/限制：{author_focus or "无特殊限制"}\n候选方向：{prompt_summary}'},
        ]
        try:
            gen = send_model(provider, messages, model, dict(params or {}), allow_continuation=False, max_empty_retries=0)
            m = re.search(r'\{[\s\S]*\}', gen.text or '')
            if m:
                parsed_llm = json.loads(m.group(0))
                items_llm = parsed_llm.get('items') if isinstance(parsed_llm, dict) else None
                if isinstance(items_llm, list):
                    for idx, patch in enumerate(items_llm[:len(picked)]):
                        if isinstance(patch, dict):
                            for k in ('core_hook', 'differentiation', 'risks'):
                                if str(patch.get(k) or '').strip():
                                    picked[idx][k] = str(patch[k]).strip()[:260]
        except Exception:
            pass

    ts = timestamp()
    saved_topics: list[dict[str, Any]] = []
    for cand in picked:
        tid = f'tdec-{uuid4().hex[:12]}'
        conn.execute(
            '''INSERT INTO topic_decisions
               (id, title, platforms_json, snapshot_ids_json, primary_genre_id, genre_tags_json,
                target_reader, core_hook, why_it_works, differentiation, feasibility,
                feasibility_reason, risks, validation_action, benchmark_books_json,
                verification_status, verified_by_book_id, verification_note, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'pending_deconstruction','','',?,?)''',
            (
                tid, cand['title'][:140], encode(cand['platforms']), encode(cand['snapshot_ids']),
                cand['primary_genre_id'], encode(cand['genre_tags']), cand['target_reader'][:180],
                cand['core_hook'][:300], cand['why_it_works'][:400], cand['differentiation'][:300],
                cand['feasibility'], cand['feasibility_reason'][:300], cand['risks'][:260],
                cand['validation_action'][:380], encode(cand['benchmark_books']), ts, ts,
            ),
        )
        row = conn.execute('SELECT * FROM topic_decisions WHERE id=?', (tid,)).fetchone()
        saved_topics.append(_row_to_topic(row))

    return {'aggregation': agg, 'topics': saved_topics}


def backfill_topic_verification(
    conn: sqlite3.Connection,
    *,
    book_id: str,
    book_title: str,
    confirmed_types: list[str] | tuple[str, ...],
    evidence_summary: str,
    verified: bool = True,
) -> list[dict[str, Any]]:
    """Close the Scan -> Deconstruct loop: backfill matching `pending_deconstruction` topics!"""
    ensure_chart_radar_tables(conn)
    norm_types = set(catalog.canonical_types(list(confirmed_types))) if confirmed_types else set()
    rows = conn.execute(
        "SELECT * FROM topic_decisions WHERE verification_status='pending_deconstruction'"
    ).fetchall()
    updated: list[dict[str, Any]] = []
    ts = timestamp()
    clean_title = norm_book_key(book_title, '').split('|')[0]
    for row in rows:
        t_genres = set(json.loads(row['genre_tags_json'] or '[]'))
        if row['primary_genre_id']:
            t_genres.add(row['primary_genre_id'])
        benchmarks = json.loads(row['benchmark_books_json'] or '[]')
        bench_match = any(
            clean_title and clean_title in norm_book_key(str(b.get('title') or ''), '').split('|')[0]
            for b in benchmarks if isinstance(b, dict)
        )
        genre_match = bool(norm_types and t_genres and (norm_types & t_genres))
        if not (bench_match or genre_match):
            continue
        new_status = 'verified' if verified else 'unconfirmed'
        note = f'已由预存库《{book_title}》拆解回填验证：{evidence_summary[:260]}'
        conn.execute(
            '''UPDATE topic_decisions
               SET verification_status=?, verified_by_book_id=?, verification_note=?, updated_at=?
               WHERE id=?''',
            (new_status, book_id, note, ts, row['id']),
        )
        refreshed = conn.execute('SELECT * FROM topic_decisions WHERE id=?', (row['id'],)).fetchone()
        updated.append(_row_to_topic(refreshed))
    return updated
