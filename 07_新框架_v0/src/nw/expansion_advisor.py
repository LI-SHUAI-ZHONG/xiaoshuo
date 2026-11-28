"""Diagnostic Anti-Padding Expansion Advisor, 7/13 Opener-Hook Matrix & Commercial Title Workshop (Fusion P & Q).

Fuses craft craftsmanship from `chinese-novelist-skill` (`content-expansion.md`, `hook-techniques.md`,
`title-guide.md`) with our empirical prose stats (`pre_review_gate`), 6-platform publish specs
(`publish_preflight`), and Market Radar `title_bigrams` (`chart_radar`):
  1. `diagnose_and_advise_expansion`: 0-token diagnostic on short drafts -> targeted anti-padding expansion plan.
  2. `OPENING_MODES_7` & `HOOK_MODES_13` & `HOOK_INTENSITY_5`: structured opener/hook variety matrix.
  3. `generate_title_candidates`: 5 distinct-technique commercial title workshop validated live against
     target platform length limits, anti-AI cliché guards, and live Radar title bigrams.
"""
from __future__ import annotations

import json
import re
from typing import Any

from nw.call_control import send_model
from nw.llm.base import LLMProvider
from nw.pre_review_gate import compute_prose_stats
from nw.publish_preflight import PLATFORM_SPECS, validate_publish_package

# ── 7-Mode Chapter Opener Matrix (章首引子七式) ────────────────────────────────
OPENING_MODES_7: tuple[dict[str, str], ...] = (
    {'id': 'shock_dialogue', 'name': '悬念对话引子', 'cue': '用一句高冲击力或暗藏矛盾的对话直接起笔，不先解释前因后果。'},
    {'id': 'flash_forward', 'name': '闪前碎片', 'cue': '截取本章真实高潮的半格瞬间提前亮相，隐去关键因果，正文再回扣兑现。'},
    {'id': 'countdown', 'name': '倒计时引子', 'cue': '直接给出紧迫时限与资源/信息缺口（如“距截止只剩三小时，关键证物却不见了”）。'},
    {'id': 'secret_monologue', 'name': '神秘独白', 'cue': '贴紧主角口吻亮出一个他未曾示人的隐秘算盘或异常感知，须在本章产生实质影响。'},
    {'id': 'contrast_montage', 'name': '反差场景并列', 'cue': '并置两个明暗/喜悲/安危反差强烈的画面，靠剪辑本身生张力，不加旁白说教。'},
    {'id': 'interrupted_action', 'name': '未完成动作引子', 'cue': '从明确指向的行动半途骤然被打断切入，把“为何停住/接下来怎样”抛给读者。'},
    {'id': 'motif_shift', 'name': '意象伏笔异变', 'cue': '让前文铺垫过的具象物件/常态发生微妙异常（如枯花抽芽、空锁自合），不解释直接进戏。'},
)

# ── 13-Mode Closing Hook Matrix (悬念钩子十三式) ───────────────────────────────
HOOK_MODES_13: tuple[dict[str, Any], ...] = (
    {'id': 'sudden_reveal', 'name': '突然揭示', 'intensity': 4, 'cue': '章末抛出颠覆当前认知的具体信息或物证，逼读者追问“为什么”。'},
    {'id': 'urgent_crisis', 'name': '紧急危机', 'intensity': 4, 'cue': '迫在眉睫的生死/破产/败露威胁当场压顶，下章必须立刻拆招。'},
    {'id': 'interrupted_beat', 'name': '未完成动作', 'intensity': 3, 'cue': '关键出招、开门或签字瞬间被新变量打断，留足悬置张力。'},
    {'id': 'identity_twist', 'name': '身份反转', 'intensity': 5, 'cue': '揭露某人的真实立场或身份错位，重定义既有盟友/敌对关系。'},
    {'id': 'dilemma_choice', 'name': '两难抉择', 'intensity': 4, 'cue': '两个选项各有惨痛代价，章节停在主角伸手落子前的一刻。'},
    {'id': 'mystery_object', 'name': '神秘物品线索', 'intensity': 2, 'cue': '出现意义不明却直指要害的异常物件/字条/账册。'},
    {'id': 'time_deadline', 'name': '时间倒计时', 'intensity': 3, 'cue': '立下明确死线而主角筹码明显不足，制造紧迫追读压力。'},
    {'id': 'threat_promise', 'name': '承诺或威胁', 'intensity': 3, 'cue': '对手或盟友亮出明确期限的威胁/赌约，改写局势预期。'},
    {'id': 'vanishing', 'name': '离奇消失', 'intensity': 3, 'cue': '关键人证、筹码或原本安全之物突然不翼而飞，安全感瞬间归零。'},
    {'id': 'subtext_bomb', 'name': '言外之意', 'intensity': 2, 'cue': '一句表面正常的话暗藏致命破绽或信息差，让读者自己反应过来。'},
    {'id': 'motif_hook', 'name': '意象变化钩', 'intensity': 2, 'cue': '呼应本章前段铺垫的具象意象，在末段以微妙异变暗示风云突变。'},
    {'id': 'echo_hook', 'name': '首尾回声钩', 'intensity': 3, 'cue': '用与本章开篇高度对称却改写关键词的一句话收尾，放大转变反差。'},
    {'id': 'silence_blank', 'name': '留白反应钩', 'intensity': 2, 'cue': '不直接说破秘密内容，只写人物读完/听完后的失态动作与沉默留白。'},
)

HOOK_INTENSITY_WAVE: tuple[int, ...] = (3, 2, 4, 2, 3, 4, 2, 5)


def recommend_chapter_opener_and_hook(
    chapter_index: int,
    *,
    recent_hooks: list[str] | tuple[str, ...] = (),
    scale: str = 'long',
) -> dict[str, Any]:
    """Deterministically pick a non-repeating opener + closing hook + wave intensity for a chapter."""
    idx = max(1, int(chapter_index or 1))
    recent = {str(h).strip() for h in (recent_hooks or ())[-3:] if str(h).strip()}
    opener = OPENING_MODES_7[(idx - 1) % len(OPENING_MODES_7)]

    target_intensity = HOOK_INTENSITY_WAVE[(idx - 1) % len(HOOK_INTENSITY_WAVE)]
    if scale == 'micro_short':
        # Short-fiction monetization (Zhihu Yanyan / Fanqie short) needs high-intensity hooks every section!
        target_intensity = 4 if idx <= 2 else (5 if idx >= 5 else 4)

    candidates = [h for h in HOOK_MODES_13 if h['id'] not in recent and h['name'] not in recent]
    if not candidates:
        candidates = list(HOOK_MODES_13)
    # Prefer hooks matching target wave intensity, rotating deterministically by chapter_index
    same_tier = [h for h in candidates if h['intensity'] >= target_intensity - 1]
    pool = same_tier or candidates
    hook = pool[(idx * 3 - 1) % len(pool)]

    return {
        'chapter_index': idx,
        'opener': opener,
        'hook': hook,
        'wave_intensity': target_intensity,
        'anti_fatigue_note': (
            f'本章建议开篇用「{opener["name"]}」（{opener["cue"]}），'
            f'章末用「{hook["name"]}·强度{target_intensity}/5」（{hook["cue"]}），'
            '独立短段收束（≤2句/≤140字），避免与近 3 章钩子同质。'
        ),
    }


# ── 0-Token Diagnostic Anti-Padding Expansion Engine ───────────────────────────

ANTI_PADDING_PRINCIPLE = '【防注水铁律】删掉新增段落后，若事件因果、人物关系或情绪张力没有变差，即判定为注水，严禁添加无意义风景/寒暄/复述已知信息！'


def diagnose_and_advise_expansion(
    draft_text: str,
    *,
    min_words: int = 0,
    target_words: int = 0,
) -> dict[str, Any]:
    """Diagnose WHY a draft is thin (0-token) and return concrete anti-padding expansion instructions."""
    text = (draft_text or '').strip()
    stats = compute_prose_stats(text)
    cur_words = len(re.sub(r'\s+', '', text))
    gap = max(0, (target_words or min_words) - cur_words)

    diagnoses: list[dict[str, str]] = []
    if stats['dialogue_ratio'] < 0.16:
        diagnoses.append({
            'dimension': '对话干瘪/偏稀',
            'strategy': '对话层次扩充',
            'instruction': (
                f'当前对白仅占 {round(stats["dialogue_ratio"]*100)}%。围绕眼下核心利害补足角色交锋：'
                '加入「动作中断（喝水/停手/避开视线）+ 潜台词绕弯 + 权力博弈（谁提问、谁回避、谁打断）」，禁用寒暄凑字。'
            ),
        })
    if stats['body_action_sentence_ratio'] < 0.14:
        diagnoses.append({
            'dimension': '关键过程一笔带过',
            'strategy': '关键时刻子弹时间放慢',
            'instruction': (
                '将本场核心冲突/出手/发现真相的一瞬拆细为「准备 → 执行 → 意外受阻 → 临场调整 → 物理结果」，'
                '补足角色当下最关心的空间距离与具体触觉/听觉反馈。'
            ),
        })
    if stats['causal_thought_sentence_ratio'] < 0.08:
        diagnoses.append({
            'dimension': '应对过程与代价缺失',
            'strategy': '内心权衡与尝试受阻展开',
            'instruction': (
                '不要从问题直接跳到结果：展开主角面对阻碍时的真实利害算账、一次试探或备选方案受挫，'
                '以及做出抉择必须付出的具象代价。'
            ),
        })
    para_count = len([ln for ln in text.splitlines() if ln.strip()])
    if para_count <= 4 or stats.get('avg_paragraph_chars', 0) > 140:
        diagnoses.append({
            'dimension': '场景肌理与呼吸单一',
            'strategy': '场景肌理与次要暗线穿插',
            'instruction': (
                '在行动缝隙里自然切入 1 处与剧情相关的空间/物件感官细节，或顺手带出一笔配角暗线/前文伏笔呼应，'
                '切忌大段孤立环境描写。'
            ),
        })

    if not diagnoses:
        diagnoses.append({
            'dimension': '事件转折节点可深化',
            'strategy': '展开因果中间拍',
            'instruction': '检查本场是否有重要选择或对手反应被概述带过，把概述改写成当场演出的具体互动与后果余波。',
        })

    lines = [
        f'【诊断式定向扩充指令】（当前约 {cur_words} 字' + (f'，缺口约 {gap} 字' if gap else '') + '）',
        *[f'{i}. [{d["dimension"]} → {d["strategy"]}] {d["instruction"]}' for i, d in enumerate(diagnoses[:3], start=1)],
        ANTI_PADDING_PRINCIPLE,
    ]
    return {
        'current_words': cur_words,
        'word_gap': gap,
        'diagnoses': diagnoses[:3],
        'prompt_block': '\n'.join(lines),
    }


# ── 5-Technique Commercial Title Workshop (6-Platform Validated) ──────────────

_AI_TITLE_CLICHE_RE = re.compile(
    r'(?:之道$|的觉醒$|纪元$|崛起$|传奇$|逆天归来|震惊|必看|免费全本|无敌爽文)'
)

_TITLE_TECHNIQUES: tuple[tuple[str, str], ...] = (
    ('核心冲突提炼法', '直指故事核心矛盾或死局筹码，读者一眼看懂核心冲突'),
    ('主角身份反差法', '突出主角独特身份/职业与处境张力，避免枯燥人名传记'),
    ('意象隐喻法', '用贯穿全书的具体物件或场景意象承载主题与辨识度'),
    ('认知反差法', '并置两个看似矛盾的商业卖点元素，瞬间触发好奇心'),
    ('悬念留白法', '指向一个具体事件/物品/数字却不剧透答案，拉高点击欲'),
)


def _extract_short_noun(text: str, fallback: str, max_len: int = 4) -> str:
    tokens = re.findall(r'[\u4e00-\u9fff]{2,6}', str(text or ''))
    stop = {'主角', '故事', '小说', '一个', '自己', '发现', '开始', '世界', '因为', '所以', '必须', '通过'}
    for tok in tokens:
        if tok not in stop:
            return tok[:max_len]
    return fallback


def generate_title_candidates(
    *,
    genre_name: str = '',
    idea: str = '',
    protagonist: str = '',
    conflict: str = '',
    platform: str = 'fanqie',
    radar_bigrams: list[str] | tuple[str, ...] = (),
    provider: LLMProvider | None = None,
    model: str = '',
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate 5 distinct-technique commercial titles checked live against platform publish specs."""
    pid = str(platform or 'fanqie').strip().lower()
    if pid not in PLATFORM_SPECS:
        pid = 'fanqie'
    spec = PLATFORM_SPECS[pid]
    max_u = int(spec['max_title_units'])

    g_kw = _extract_short_noun(genre_name, '异闻', 2)
    c_kw = _extract_short_noun(conflict or idea, '困局', 4)
    p_kw = _extract_short_noun(protagonist, '守夜人', 3)
    i_kw = _extract_short_noun(idea, '旧账', 3)
    hot_hint = next((str(b).strip() for b in (radar_bigrams or ()) if 2 <= len(str(b).strip()) <= 4), '')

    # Deterministic 0-token 5-technique baseline candidates tailored to platform & length cap
    if pid == 'zhihu_yanyan':
        raw_cands = [
            (f'{c_kw}当夜，我把所有底牌拍在了桌上', _TITLE_TECHNIQUES[0]),
            (f'身为{p_kw}，我决定不再替他们善后', _TITLE_TECHNIQUES[1]),
            (f'那本{i_kw}翻开后，所有人都慌了', _TITLE_TECHNIQUES[2]),
            (f'他们逼我退场，却不知我才是真正庄家', _TITLE_TECHNIQUES[3]),
            (f'第三份{i_kw}里，写着全家的秘密', _TITLE_TECHNIQUES[4]),
        ]
    elif pid == 'jjwxc':
        raw_cands = [
            (f'{c_kw}之后', _TITLE_TECHNIQUES[0]),
            (f'我是{p_kw}', _TITLE_TECHNIQUES[1]),
            (f'{i_kw}有声', _TITLE_TECHNIQUES[2]),
            (f'反派的{p_kw}', _TITLE_TECHNIQUES[3]),
            (f'第三封{i_kw}', _TITLE_TECHNIQUES[4]),
        ]
    else:
        raw_cands = [
            (f'{c_kw}：从{i_kw}开始掀桌', _TITLE_TECHNIQUES[0]),
            (f'我在{g_kw}世界做{p_kw}', _TITLE_TECHNIQUES[1]),
            (f'{i_kw}与{g_kw}录', _TITLE_TECHNIQUES[2]),
            (f'都以为我是废柴，其实我管{c_kw}', _TITLE_TECHNIQUES[3]),
            (f'第七次{c_kw}：别回头', _TITLE_TECHNIQUES[4]),
        ]

    # Optional LLM commercial title generation (strictly 5 distinct techniques + anti-cliché + platform limit)
    mode = 'deterministic_workshop'
    if provider is not None and model:
        bg_note = f'近期{spec["name"]}榜单高频书名热词参考：{"、".join(list(radar_bigrams)[:8])}' if radar_bigrams else ''
        sys_p = (
            f'你是顶级商业网文起名专家。为目标平台「{spec["name"]}」（书名硬上限 {max_u} 字，禁空格/表情/促销括号）'
            '生成 5 个风格互斥的商业书名，分别严格对应 5 种技巧：'
            '核心冲突提炼法、主角身份反差法、意象隐喻法、认知反差法、悬念留白法。\n'
            '严禁 AI 套路词（XX之道/XX的觉醒/XX纪元/XX崛起/震惊/必看）。\n'
            '严格输出 JSON：{"candidates":[{"title":"...","technique":"...","reason":"一句话说明为何吸睛"}]}'
        )
        usr_p = (
            f'题材：{genre_name or "商业网文"}\n核心构想：{idea or "无"}\n'
            f'主角特征：{protagonist or "未指定"}\n核心冲突：{conflict or "未指定"}\n{bg_note}'
        )
        try:
            gen = send_model(provider, [{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': usr_p}],
                             model, dict(params or {}), allow_continuation=False, max_empty_retries=0)
            m = re.search(r'\{[\s\S]*\}', gen.text or '')
            if m:
                parsed = json.loads(m.group(0))
                llm_items = parsed.get('candidates') if isinstance(parsed, dict) else None
                if isinstance(llm_items, list) and llm_items:
                    raw_cands = [
                        (
                            str(it.get('title') or '').strip(),
                            (str(it.get('technique') or _TITLE_TECHNIQUES[i % 5][0]), str(it.get('reason') or 'AI商业深化命名')),
                        )
                        for i, it in enumerate(llm_items[:5])
                        if isinstance(it, dict) and str(it.get('title') or '').strip()
                    ]
                    mode = 'llm_workshop'
        except Exception:
            pass

    evaluated: list[dict[str, Any]] = []
    bigram_set = [str(b).strip() for b in (radar_bigrams or ()) if str(b).strip()]
    for raw_title, (tech_name, tech_why) in raw_cands:
        clean_t = raw_title.strip('《》「」 ').replace(' ', '') if not spec['allow_title_spaces'] else raw_title.strip('《》「」 ')
        # Trim gently if deterministic candidate slightly exceeds tight cap
        if len(clean_t) > max_u:
            clean_t = clean_t[:max_u]
        chk = validate_publish_package(
            pid,
            title=clean_t,
            synopsis='这是用于校验书名长度与合规性的占位简介文本，确保仅独立评估书名是否符合平台规范。',
            tags=['合规校验'],
            category=genre_name or '商业网文',
        )
        title_issues = [i['message'] for i in chk['blocking_issues'] if i['field'] == 'title']
        cliche_hit = _AI_TITLE_CLICHE_RE.search(clean_t)
        if cliche_hit:
            title_issues.append(f'命中 AI 套路书名结构「{cliche_hit.group(0)}」')
        matched_hot = [bg for bg in bigram_set if bg in clean_t]
        evaluated.append({
            'title': clean_t,
            'technique': tech_name,
            'reason': tech_why,
            'weighted_length': chk['weighted_title_length'],
            'max_length': chk['max_title_length'],
            'passed': len(title_issues) == 0,
            'issues': title_issues,
            'radar_hot_hits': matched_hot,
        })

    return {
        'mode': mode,
        'platform': pid,
        'platform_name': spec['name'],
        'max_title_length': spec['max_title_units'],
        'radar_bigrams_checked': bigram_set[:10],
        'hot_hint': hot_hint,
        'candidates': evaluated,
    }
