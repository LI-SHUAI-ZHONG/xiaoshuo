"""P0 writing-craft prompt layering, POV-safe situation cards, and style reference anchors.

Separates pre-writing creative release (situation card + style anchor + concise craft principles)
from post-draft anti-AI-flavor self-check and revision guardrails (with an explicit
preserve-humanity list so revisions never turn natural prose cold or choppy).
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from nw.store import Store, now
from nw.task_models import canonical, content_sha256

STYLE_REFERENCE_FILENAME = 'style_reference.json'
STYLE_REFERENCE_MODES = frozenset({'off', 'author_sample', 'auto_book_prose'})
STYLE_EXCERPT_STORE_LIMIT = 4000
STYLE_EXCERPT_PROMPT_LIMIT = 2200
AUTO_BOOK_PROSE_LIMIT = 900

_RICH_SCENE_FIELDS = frozenset({
    'conflict', 'allowed_disclosure', 'entering_state', 'planned_result',
    'character_goals', 'ending_change', 'turning_point', 'beats',
})

PRE_WRITE_CRAFT_GUIDE = (
    '叙事生命力原则（写前减负·按处境推演）：'
    '1. 紧扣本场处境卡（谁在场、此刻要什么怕什么、知情差、必达结果与最值得展开的一场戏），'
    '让人物按当下处境自然行动与接话，不要照着检查表逐步报点；工作包中的资料约束按情境自然融入，细碎打磨留给 16 步审稿。'
    '2. 先写人物此刻最强烈的真实冲击与情绪反应，再写动作与台词；大事发生要像天塌了，小事不必人人如临大敌；'
    '关键交锋、核心转折与能力亮相给足一整拍当场展开，不挪到场外转述。'
    '3. 后台状态机负责记账，正文绝不报账：用完物件的去向、钱数进出、本事不能做什么，读者当下不关心就不要在正文逐项清点防挑刺。'
    '4. 保持真人网文语流与呼吸感：句子按意思一路说完整，保留有效的人物心里话、对白语气词与贴合题材的正常连接词，'
    '不刻意切碎成电报体，也严禁在正文出现方法名、锚点编号或内部检查术语。'
    '5. 若附带写前语感参照（style-reference），只学习其行文呼吸、长短句节奏与对白脾气，严禁照搬其中人名、设定、事件或原句。'
)

ANTI_AI_REVIEW_GUIDE = (
    '【写后去 AI 味五维自检与保护红线】在核对事实、POV 与资料约束之外，逐一排查以下五项真实读感问题：'
    '1. 人物动机与硬阻力：角色是否按各自利害行动？在场强者若未直接解决麻烦，理由是否立得住？配角有无自身关切而非配合主角走流程。'
    '2. 对白与第一反应：遇坏消息或冲突时，是先有贴合处境的情绪冲击与第一反应，还是平静通报后再贴“他很害怕”标签？'
    '排查明知故问、喂话式一问一答短对白、对白重复旁白刚讲过的道理、情绪与动作错配的摆姿势台词。'
    '3. 当场展开与不报账：关键发现、交锋或能力亮相是否当场写足？是否把背景大段堆在开头，或把钱物去向与能力限制写进正文清点防挑刺？'
    '4. 高频 AI 套式与多余解释：排查破坏读感的套式（揭晓式冒号抖包袱、连续否定排比、高频“先立后翻”、置身事外的转述俏皮话、'
    '无依据凑整数字、连续电报体碎短句收尾、替读者把已显而易见的推论或悬念提前说破）；仅在确实生硬或重复时指正，不按禁词表一刀切。'
    '5. 读感力度与【不要动保护清单】：核对核心情绪是否写足、场面有无力量、章尾有无自然追读力；'
    '但严禁为追求去 AI 味而要求删掉有效的人物心里话、正常重复词、句首“但/不过/可是”、段首“他/她”、对白语气词（呢/啊/都…了）'
    '或网文常用连接词与对白标签（便/却/只见/不料/冷笑道），防止把活人稿改冷改碎。'
)

ANTI_AI_REVISE_GUIDE = (
    '【去 AI 味定向修订指引】先按审稿意见定位根因（反应链、信息先后、当场展开不足、套式重复或事实错位），针对具体问题增删调整，'
    '该展开的场面补足过程与感受，不只减不加。严格遵守【不要动保护清单】：保留有作用的人物心里话、对白语气词（呢/啊/都…了）、'
    '正常主语和网文常用连接词，不靠切碎短句、滥换同义词或删光心理描写制造假“人味”；修订后连读前后文确保承接顺畅且不泄底。'
)


def _clip(value: Any, limit: int = 160) -> str:
    text = str(value or '').strip()
    if not text:
        return ''
    return text if len(text) <= limit else text[:limit - 1] + '…'


def _has_rich_scene_body(scene_body: dict[str, Any]) -> bool:
    return any(bool(scene_body.get(k)) for k in _RICH_SCENE_FIELDS)


def build_situation_card(
    scene_body: dict[str, Any],
    pov: str,
    filtered_settings: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    *,
    has_design: bool = False,
) -> dict[str, Any] | None:
    """Compile a POV-safe, non-scripted situation card strictly from already-filtered writer inputs.

    Never reads author-only secrets or unfiltered cards; every field comes exclusively from
    the POV-filtered scene_body, filtered_settings, and view.facts.
    """
    if not has_design and not _has_rich_scene_body(scene_body):
        return None

    cards_by_id = {c['card_id']: c for c in filtered_settings if isinstance(c, dict) and c.get('card_id')}
    pov_card = cards_by_id.get(pov, {}).get('body', {}) if pov else {}
    pov_name = str(pov_card.get('name') or pov or '当前视角人物').strip()

    pov_stance: dict[str, Any] = {'id': pov, 'name': pov_name}
    own_goal = None
    if isinstance(scene_body.get('character_goals'), dict):
        own_goal = scene_body['character_goals'].get(pov)
    if own_goal:
        pov_stance['immediate_goal'] = _clip(own_goal, 140)
    elif pov_card.get('want'):
        pov_stance['want'] = _clip(pov_card['want'], 120)
    for field, out_key in (
        ('wound', 'fear_or_wound'),
        ('fear', 'fear_or_wound'),
        ('need', 'deep_need'),
        ('flaw', 'pressure_point'),
        ('boundaries', 'bottom_line'),
        ('voice', 'voice'),
    ):
        if pov_card.get(field) and out_key not in pov_stance:
            pov_stance[out_key] = _clip(pov_card[field], 100)

    present_ids = [cid for cid in (scene_body.get('characters') or ()) if isinstance(cid, str) and cid != pov]
    present_characters: list[dict[str, str]] = []
    for cid in present_ids[:6]:
        body = cards_by_id.get(cid, {}).get('body', {})
        entry: dict[str, str] = {'id': cid, 'name': str(body.get('name') or cid)}
        if body.get('role'):
            entry['role'] = _clip(body['role'], 60)
        if body.get('voice'):
            entry['voice'] = _clip(body['voice'], 80)
        present_characters.append(entry)

    known_items: list[str] = []
    belief_items: list[str] = []
    for fact in facts[:14]:
        if not isinstance(fact, dict):
            continue
        ent = str(fact.get('entity_id') or '').strip()
        pred = str(fact.get('predicate') or '').strip()
        val = fact.get('value')
        val_text = val if isinstance(val, str) else canonical(val)
        summary = _clip(f'{ent}.{pred}={val_text}', 84)
        claim = str(fact.get('claim') or 'fact').lower()
        if claim in ('belief', 'suspicion', 'plan'):
            belief_items.append(f'[{claim}] {summary}')
        else:
            known_items.append(summary)

    spotlight = _clip(
        scene_body.get('conflict')
        or scene_body.get('turning_point')
        or scene_body.get('goal')
        or scene_body.get('title'),
        180,
    )
    outcome = _clip(
        scene_body.get('planned_result')
        or scene_body.get('ending_change')
        or scene_body.get('goal'),
        180,
    )

    card: dict[str, Any] = {
        'scene': _clip(scene_body.get('title') or '本场', 80),
        'pov_stance': pov_stance,
        'present_characters': present_characters,
        'spotlight_to_expand': spotlight,
        'target_outcome_and_stop': outcome,
        'craft_reminder': (
            '按处境让人物自然行动与接话，不照剧本逐步报点；'
            '重点展开本场最抓人的核心交锋/转变，钱物去向与能力禁区由后台记账、不在正文清点。'
        ),
    }
    if scene_body.get('location') or scene_body.get('story_time'):
        card['setting'] = {
            **({'location': _clip(scene_body['location'], 80)} if scene_body.get('location') else {}),
            **({'story_time': str(scene_body['story_time'])} if scene_body.get('story_time') is not None else {}),
        }
    if scene_body.get('entering_state'):
        card['entering_state'] = _clip(scene_body['entering_state'], 160)
    if scene_body.get('allowed_disclosure'):
        card['allowed_disclosure'] = _clip(scene_body['allowed_disclosure'], 180)
    if known_items:
        card['pov_known'] = known_items[:8]
    if belief_items:
        card['pov_beliefs_may_err'] = belief_items[:6]
    return card


def package_uses_craft_layers(package: dict[str, Any] | None) -> bool:
    """Return True when the frozen writing package carries P0 situation/style craft items or design materials."""
    if not isinstance(package, dict):
        return False
    for item in package.get('items', ()):
        if not isinstance(item, dict):
            continue
        src = str(item.get('source') or '')
        if src.startswith(('situation:', 'style-reference', 'voice-spec', 'scene-beat', 'material:')):
            return True
    return False


# ---------- Per-project Style Reference Anchor ----------

def default_style_reference() -> dict[str, Any]:
    return {
        'enabled': False,
        'mode': 'off',
        'title': '',
        'source_note': '',
        'excerpt': '',
        'style_notes': '',
        'updated_at': None,
    }


def _style_reference_path(store: Store) -> Path:
    return store.data_file(STYLE_REFERENCE_FILENAME)


def load_style_reference(store: Store) -> dict[str, Any]:
    path = _style_reference_path(store)
    if not path.is_file():
        return default_style_reference()
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default_style_reference()
    if not isinstance(raw, dict):
        return default_style_reference()
    mode = str(raw.get('mode') or 'off')
    if mode not in STYLE_REFERENCE_MODES:
        mode = 'off'
    enabled = bool(raw.get('enabled', mode != 'off')) and mode != 'off'
    return {
        'enabled': enabled,
        'mode': mode if enabled else 'off',
        'title': str(raw.get('title') or '').strip()[:120],
        'source_note': str(raw.get('source_note') or '').strip()[:160],
        'excerpt': str(raw.get('excerpt') or '').strip()[:STYLE_EXCERPT_STORE_LIMIT],
        'style_notes': str(raw.get('style_notes') or '').strip()[:800],
        'updated_at': raw.get('updated_at'),
    }


def save_style_reference(store: Store, body: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise ValueError('无效的写前语感参照配置')
    mode = str(body.get('mode') or ('author_sample' if body.get('enabled') else 'off')).strip()
    if mode not in STYLE_REFERENCE_MODES:
        raise ValueError('参照模式须为 off、author_sample 或 auto_book_prose')
    enabled = bool(body.get('enabled', mode != 'off'))
    if not enabled:
        mode = 'off'
    excerpt = str(body.get('excerpt') or '').strip()
    if len(excerpt) > STYLE_EXCERPT_STORE_LIMIT:
        raise ValueError(f'参照样段不能超过 {STYLE_EXCERPT_STORE_LIMIT} 字，请精选最具代表性的 1–2 段或单章片段')
    if mode == 'author_sample' and not excerpt and not str(body.get('style_notes') or '').strip():
        raise ValueError('启用「作者参照样段」时，请至少提供样段正文或具体语感说明')
    record = {
        'enabled': enabled and mode != 'off',
        'mode': mode,
        'title': str(body.get('title') or '').strip()[:120],
        'source_note': str(body.get('source_note') or '').strip()[:160],
        'excerpt': excerpt,
        'style_notes': str(body.get('style_notes') or '').strip()[:800],
        'updated_at': now(),
        'excerpt_sha256': content_sha256({'excerpt': excerpt}) if excerpt else None,
    }
    path = _style_reference_path(store)
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = NamedTemporaryFile('w', encoding='utf-8', newline='', dir=path.parent,
                                prefix='.style-ref-', suffix='.tmp', delete=False)
    tmp = Path(staged.name)
    try:
        with staged:
            staged.write(json.dumps(record, ensure_ascii=False, indent=2))
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)
    return record


def resolve_style_reference_item(
    store: Store,
    snapshot: dict[str, Any],
    *,
    pov: str,
    story_order: int,
    disclosure: tuple[int, int, int],
    adjacent_scene_id: str | None = None,
    excerpt_loader: Any = None,
) -> dict[str, Any] | None:
    """Resolve the active pre-writing style anchor payload (POV-safe, spoiler-free, budget-bounded)."""
    cfg = load_style_reference(store)
    if not cfg['enabled'] or cfg['mode'] == 'off':
        return None

    if cfg['mode'] == 'author_sample':
        payload: dict[str, Any] = {
            'mode': 'author_sample',
            'usage_rule': '动笔前紧贴此语感参照校准句式呼吸、叙述口吻与对白脾气；严禁照搬其中任何人物、设定、情节或原句。',
        }
        if cfg['title']:
            payload['title'] = cfg['title']
        if cfg['source_note']:
            payload['source_note'] = cfg['source_note']
        if cfg['style_notes']:
            payload['style_notes'] = cfg['style_notes']
        if cfg['excerpt']:
            payload['excerpt'] = cfg['excerpt'][:STYLE_EXCERPT_PROMPT_LIMIT]
        return payload

    if cfg['mode'] == 'auto_book_prose':
        # Pull a safe opening prose excerpt from the earliest accepted scene strictly before this scene
        # and not duplicating adjacent_previous, scrubbed via prior_prose() to prevent flash-forward/reader_only leaks.
        earlier_slots: list[tuple[tuple[int, int], str, str]] = []
        for cand_scene_id, slot in (snapshot.get('slots') or {}).items():
            if not slot.get('draft_id') or cand_scene_id == adjacent_scene_id:
                continue
            cand_scene = store.get('scene', cand_scene_id)
            cand_order = (store.get('chapter', cand_scene.chapter_id).index, cand_scene.index)
            if cand_order < disclosure[:2]:
                earlier_slots.append((cand_order, cand_scene_id, slot['draft_id']))
        earlier_slots.sort(key=lambda row: row[0])
        for cand_order, cand_scene_id, cand_draft_id in earlier_slots:
            if excerpt_loader is not None:
                text, hidden = excerpt_loader(cand_draft_id)
            else:
                from nw.context.prior_prose import prior_prose
                text, hidden = prior_prose(
                    store, store.get('draft', cand_draft_id), snapshot['slots'][cand_scene_id], pov,
                    at_story_order=story_order,
                )
            # Extract first visible slice outside any hidden reader_only/flash-forward spans.
            visible_parts: list[str] = []
            cursor = 0
            for start, end in sorted(hidden):
                if start > cursor:
                    visible_parts.append(text[cursor:start])
                cursor = max(cursor, end)
            if cursor < len(text):
                visible_parts.append(text[cursor:])
            safe_text = '\n'.join(part.strip() for part in visible_parts if part.strip()).strip()
            if len(safe_text) >= 30:
                payload = {
                    'mode': 'auto_book_prose',
                    'source_chapter': cand_order[0],
                    'source_scene_index': cand_order[1],
                    'usage_rule': '承接本书已采用开篇章节的叙述口吻、句式呼吸与对白质感，保持全书统一声线，不重复开篇桥段。',
                    'excerpt': safe_text[:AUTO_BOOK_PROSE_LIMIT],
                }
                if cfg['style_notes']:
                    payload['style_notes'] = cfg['style_notes']
                return payload
        # Fallback to style_notes if author hasn't accepted Chapter 1 yet.
        if cfg['style_notes']:
            return {
                'mode': 'auto_book_prose',
                'usage_rule': '本书尚无可用开篇已接受稿，暂按以下本书写法要求定调。',
                'style_notes': cfg['style_notes'],
            }
    return None


def style_reference_overview(store: Store, *, branch: str = 'main') -> dict[str, Any]:
    """Summary returned to Studio UI for editing & inspecting the book's style anchor."""
    cfg = load_style_reference(store)
    accepted_chapters: list[int] = []
    if store.managed_story():
        from nw.story_state import current_head, revision_state
        try:
            snap = revision_state(store, current_head(store, branch))
            seen = set()
            for sid, slot in (snap.get('slots') or {}).items():
                if slot.get('draft_id'):
                    sc = store.get('scene', sid)
                    ch = store.get('chapter', sc.chapter_id)
                    seen.add(ch.index)
            accepted_chapters = sorted(seen)
        except Exception:
            accepted_chapters = []
    return {
        **cfg,
        'accepted_chapters': accepted_chapters,
        'can_use_auto_book_prose': bool(accepted_chapters),
        'max_excerpt_chars': STYLE_EXCERPT_STORE_LIMIT,
        'prompt_excerpt_chars': STYLE_EXCERPT_PROMPT_LIMIT,
    }
