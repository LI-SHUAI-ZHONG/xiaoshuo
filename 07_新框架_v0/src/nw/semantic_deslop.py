"""Fact-Frozen Semantic Deslop & Polish Engine (Fusion E x Living VoiceSpec).

Unlike keyword-only banned-word replacement or full structural rewriting:
  1. Scores every paragraph for BOTH lexical AI-cliche density AND functional slop signals
     (redundant emotion explanation after physical action, interchangeable generic scene-fillers,
     disguised-exposition dialogue, synchronized crowd reactions).
  2. Uses Host-Bounded Spot-Fix (`nw.spot_fix`) to physically lock untouched paragraphs
     byte-for-byte while injecting live `VoiceSpec` + Author-Edit Golden Contrasts (`learned_contrasts`).
  3. Runs a post-polish Fact & Canonical-Entity Zero-Drift Guard verifying that approved
     character names, length envelope, and protected paragraphs did not drift.
"""
from __future__ import annotations

import json
import re
from typing import Any

from nw.call_control import send_model
from nw.craft_specs import load_all_craft_specs
from nw.llm.base import LLMProvider
from nw.pre_review_gate import _AI_CLICHE_PATTERNS, compute_prose_stats
from nw.spot_fix import apply_spot_fix_edits, build_spot_fix_messages, compute_revision_diff, segment_prose, select_spot_fix_ranges
from nw.store import Store

# Functional AI-slop detectors (function-based, NOT mechanical word banning)
_FUNCTIONAL_SLOP_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    (
        'redundant_emotion_label',
        '动作/神态后冗余贴情绪标签（已用动作表现，却再用旁白解释心情）',
        re.compile(r'(?:紧握双拳|咬紧牙关|脸色发白|指节发白|深吸一口气|浑身一颤)[^。\n]{0,20}(?:心中(?:满是|充满了|涌起)|内心(?:无比|一阵))(?:愤怒|恐惧|悲伤|委屈|震惊|不甘|绝望)'),
    ),
    (
        'synchronized_crowd',
        '群演同步反应套路（围观众人齐刷刷倒吸凉气/脸色大变）',
        re.compile(r'(?:众人|全场|四周(?:的人)?|围观(?:者|群众)?)(?:瞬间|顿时|齐刷刷|无不)(?:倒吸一口凉气|面色大变|哗然|鸦雀无声|目瞪口呆)'),
    ),
    (
        'disguised_exposition_dialogue',
        '伪装成对话的设定宣讲（“你应该知道/众所周知/要知道我们这片大陆……”）',
        re.compile(r'[“「"](?:[^”」"\n]{0,12})(?:你(?:应该|可|也)知道|众所周知|要知道(?:咱们|我们|这)|毕竟(?:按照|依照)规矩)[^”」"\n]{8,120}[”」"]'),
    ),
    (
        'generic_narrator_summary',
        '万金油旁白总结句（脱离具体人物感官的空泛感叹）',
        re.compile(r'(?:这一刻[，,]?一切都(?:改变了|不再一样)|命运(?:从来|总是)(?:不会|喜欢)|谁也没有想到[，,]?这(?:只是|将会))'),
    ),
    (
        'abstract_atmosphere_filler',
        '空洞氛围套话（无具体物象支撑的“压抑/肃杀/诡异”宣言）',
        re.compile(r'(?:整个(?:房间|大厅|街道|院子)里?)(?:弥漫着|笼罩着)(?:一股|一层)(?:说不出的|令人窒息的|诡异的|压抑的)(?:气息|氛围|沉默)'),
    ),
)

SEMANTIC_CLEANUP_RUBRIC = (
    '【语义去 AI 味七问准则】对每个待修区间逐句自检：'
    '1. 动作或眼神已体现的情绪，删掉冗余的旁白情绪标签；'
    '2. 抽掉人名放进任何小说都成立的万金油过渡句，换成与当前人物处境绑定的具体物象/感官；'
    '3. 围观群演不要齐声倒吸凉气，只给 1–2 个具体人分化的反应；'
    '4. 对话不要借人物之口宣讲背景设定，改回带利害与潜台词的真实交锋；'
    '5. 严禁机械删除正常衔接词、贴切比喻或刻意节奏排比。'
)


def analyze_deslop_targets(text: str, *, max_targets: int = 4) -> dict[str, Any]:
    """Score every paragraph for lexical + functional AI-slop density (0 tokens)."""
    paras = segment_prose(text or '')
    scored: list[dict[str, Any]] = []
    total_hits = 0

    for p in paras:
        p_text = p['text']
        hits: list[dict[str, str]] = []
        for code, desc, pat in _AI_CLICHE_PATTERNS:
            for m in pat.finditer(p_text):
                hits.append({'code': code, 'kind': 'lexical', 'label': desc, 'match': m.group(0)})
        for code, desc, pat in _FUNCTIONAL_SLOP_PATTERNS:
            for m in pat.finditer(p_text):
                hits.append({'code': code, 'kind': 'functional', 'label': desc, 'match': m.group(0)})
        if hits:
            total_hits += len(hits)
            score = sum(2 if h['kind'] == 'functional' else 1 for h in hits)
            scored.append({
                'paragraph': p['index'],
                'score': score,
                'hit_count': len(hits),
                'hits': hits[:6],
                'preview': p_text[:120],
            })

    scored.sort(key=lambda r: (-r['score'], -r['hit_count'], r['paragraph']))
    recommended = sorted(item['paragraph'] for item in scored[:max_targets])
    stats = compute_prose_stats(text)
    return {
        'paragraph_count': len(paras),
        'flagged_paragraphs': scored,
        'recommended_target_paragraphs': recommended,
        'total_slop_hits': total_hits,
        'stats': stats,
        'needs_deslop': bool(scored),
    }


def _voice_guidance_block(store: Store) -> str:
    specs = load_all_craft_specs(store)
    voice = specs.get('voice') or {}
    lines: list[str] = [SEMANTIC_CLEANUP_RUBRIC]
    if voice.get('base_name'):
        lines.append(f'本书语感基座：{voice.get("base_name")}')
    redlines = [str(r) for r in (voice.get('anti_drift_redlines') or ()) if str(r).strip()][:5]
    learned_redlines = [
        str(r.get('rule') or '')
        for r in (voice.get('learned_redlines') or ())
        if isinstance(r, dict) and str(r.get('rule') or '').strip()
    ][:4]
    if redlines or learned_redlines:
        lines.append('防漂移红线：' + '；'.join([*learned_redlines, *redlines][:6]))
    contrasts = list(voice.get('learned_contrasts') or ())[:2]
    if contrasts:
        lines.append('作者亲改语感黄金对照（优先贴近作者写法）：')
        for c in contrasts:
            lines.append(f'  ❌ {str(c.get("bad_ai") or "")[:90]} -> ✅ {str(c.get("target_voice") or "")[:90]}')
    return '\n'.join(lines)


def verify_fact_preservation(
    before_text: str,
    after_text: str,
    *,
    canonical_names: list[str] | set[str] | None = None,
    max_length_drift_ratio: float = 0.25,
) -> dict[str, Any]:
    """Verify that fact-frozen polishing did not drop canonical entities or distort scene length."""
    before_len = max(1, len(before_text or ''))
    after_len = len(after_text or '')
    length_drift = abs(after_len - before_len) / before_len

    dropped_entities: list[str] = []
    for name in (canonical_names or ()):
        clean = str(name or '').strip()
        if len(clean) >= 2 and clean in before_text and clean not in after_text:
            dropped_entities.append(clean)

    issues: list[str] = []
    if dropped_entities:
        issues.append(f'润色后丢失原稿已出场/提及的规范实体：{"、".join(dropped_entities[:6])}')
    if length_drift > max_length_drift_ratio:
        issues.append(f'润色篇幅漂移 {round(length_drift * 100, 1)}% 超过冻结阈值 {round(max_length_drift_ratio * 100)}%')
    return {
        'passed': not issues,
        'dropped_entities': dropped_entities,
        'length_drift_ratio': round(length_drift, 3),
        'issues': issues,
    }


def _active_canonical_names(store: Store) -> list[str]:
    names: set[str] = set()
    try:
        rows = store.connection.execute(
            "SELECT body_json FROM cards WHERE kind IN ('character','world') ORDER BY rowid DESC LIMIT 40"
        ).fetchall()
        for row in rows:
            body = json.loads(row['body_json'])
            for k in ('name', 'title'):
                nm = str(body.get(k) or '').strip()
                if 2 <= len(nm) <= 8:
                    names.add(nm)
    except Exception:
        pass
    return sorted(names)


def run_semantic_deslop(
    store: Store,
    draft_text: str,
    provider: LLMProvider,
    model: str,
    params: dict[str, Any] | None = None,
    *,
    target_paragraphs: list[int] | None = None,
    max_ranges: int = 3,
    max_affected_ratio: float = 0.55,
    extra_instruction: str = '',
) -> dict[str, Any]:
    """Run a host-bounded, fact-frozen semantic deslop/polish pass on a draft."""
    analysis = analyze_deslop_targets(draft_text)
    chosen = list(target_paragraphs) if target_paragraphs is not None else list(analysis['recommended_target_paragraphs'])
    if not chosen:
        return {
            'status': 'clean',
            'changed': False,
            'analysis': analysis,
            'polished_text': draft_text,
            'message': '当前正文未检测到高密度 AI 套话或功能性注水，无需额外去 AI 味润色。',
        }

    plan = select_spot_fix_ranges(
        draft_text,
        chosen,
        max_ranges=max_ranges,
        max_affected_ratio=max_affected_ratio,
    )
    if not plan['eligible']:
        # Trim targets to the top-ranked paragraphs that fit cleanly within Spot-Fix bounds
        trimmed = chosen[:max(1, min(2, len(chosen)))]
        plan = select_spot_fix_ranges(
            draft_text,
            trimmed,
            max_ranges=max_ranges,
            max_affected_ratio=max_affected_ratio,
        )
    if not plan['eligible']:
        return {
            'status': 'ineligible',
            'changed': False,
            'analysis': analysis,
            'polished_text': draft_text,
            'message': plan.get('fallback_reason') or '所选段落超过局部去 AI 味边界，请缩小勾选范围。',
        }

    flagged_notes = []
    flagged_by_p = {item['paragraph']: item for item in analysis['flagged_paragraphs']}
    for r in plan['ranges']:
        for idx in range(r['start_paragraph'], r['end_paragraph'] + 1):
            info = flagged_by_p.get(idx)
            if info:
                labels = '、'.join(dict.fromkeys(h['label'] for h in info['hits']))
                flagged_notes.append(f'P{idx}：{labels}')

    instruction = (
        '对下列指定区间执行【事实冻结型语义去 AI 味润色】。\n'
        + ('检测到的主要 AI 味问题：\n- ' + '\n- '.join(flagged_notes) + '\n' if flagged_notes else '')
        + (f'作者补充要求：{extra_instruction.strip()}\n' if extra_instruction.strip() else '')
        + '保留所有人物姓名、动作因果、道具状态与 POV 信息边界不变，只重写僵硬表达、冗余情绪标签与套路句式。'
    )
    voice_guidance = _voice_guidance_block(store)
    messages = build_spot_fix_messages(
        draft_text,
        plan,
        instruction=instruction,
        mode='deslop',
        voice_guidance=voice_guidance,
    )
    live = provider.name != 'fake'
    gen = send_model(
        provider,
        messages,
        model,
        dict(params or {}),
        allow_continuation=False,
        max_empty_retries=(2 if live else 0),
    )
    if gen.finish_reason != 'complete' or not gen.text.strip():
        raise ValueError(f'语义去 AI 味调用失败（{gen.finish_reason}）')

    spliced = apply_spot_fix_edits(draft_text, plan, gen.text)
    polished_text = spliced['text']
    canonical_names = _active_canonical_names(store)
    preservation = verify_fact_preservation(draft_text, polished_text, canonical_names=canonical_names)
    auth_paras = [
        idx
        for r in plan['ranges']
        for idx in range(r['start_paragraph'], r['end_paragraph'] + 1)
    ]
    diff = compute_revision_diff(draft_text, polished_text, authorized_paragraphs=auth_paras)
    after_analysis = analyze_deslop_targets(polished_text)

    return {
        'status': 'ok' if preservation['passed'] else 'drift_warning',
        'changed': polished_text != draft_text,
        'polished_text': polished_text,
        'applied_ranges': spliced['applied_ranges'],
        'protected_intact': spliced['protected_intact'],
        'fact_preservation': preservation,
        'diff': diff,
        'before_slop_hits': analysis['total_slop_hits'],
        'after_slop_hits': after_analysis['total_slop_hits'],
        'usage': gen.usage,
    }
