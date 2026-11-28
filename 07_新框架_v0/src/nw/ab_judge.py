"""Scene-vs-Summary Coverage Evaluator & Position-Swapped Blind A/B Judge (Fusion L2).

Two high-leverage evaluation upgrades:
  1. `evaluate_scene_vs_summary`: Strictly classifies every planned outline beat as
     `scene` (dramatized on-stage with concrete sensory/dialogue/action unfolding),
     `summary` (compressed telling/glossed over in 1–2 summarizing lines), or
     `missing` (absent from draft), citing verbatim prose evidence.
  2. `run_position_swapped_ab_judge`: Eliminates LLM position bias in pairwise prose
     comparison by executing BOTH anonymous orderings `(A, B)` and `(B, A)`. Declares
     a winner ONLY when both swapped rounds agree on the same draft; otherwise `tie`!
"""
from __future__ import annotations

import json
import re
from typing import Any

from nw.call_control import send_model
from nw.llm.base import LLMProvider

_JSON_FENCE_RE = re.compile(r'```(?:json)?\s*(\{.*\})\s*```', re.DOTALL)

SCENE_VS_SUMMARY_PROMPT = (
    '你是一名严格的商业网文场景展开核查员。请对照下方【规划节拍列表】与【实际正文】，'
    '逐条判定每个节拍在正文中的落地形态，严格区分三种状态：\n'
    '- "scene"：当场展开演出——有具体动作过程、对话交锋、现场感官或真实情绪拉扯；\n'
    '- "summary"：只做了概述带过——仅用一两句旁白总结“于是他们谈妥了/经过一番激战赢了”而没演现场；\n'
    '- "missing"：正文中完全未出现或被遗漏。\n'
    '只输出严格 JSON：\n'
    '{"beats":[{"index":1,"beat":"原节拍摘要","status":"scene|summary|missing","evidence":"正文原句短引（missing为空）","reason":"一句判定理由"}],"summary":"一句话总评"}'
)

BLIND_AB_JUDGE_PROMPT = (
    '你是一名公正的资深网文主编，正在对同一场景的两份匿名草稿（【稿一】与【稿二】）做双盲对比裁决。'
    '两份稿件顺序已随机打乱，请严格依据正文现场感、人物活人感与动机可信度、对白脾气、'
    '节奏推进与去 AI 套话程度做判断，不要受稿件摆放先后顺序或长度影响。\n'
    '只输出严格 JSON：\n'
    '{"winner":"1|2|tie","evidence_1":"稿一最关键的一句原文优缺点短引","evidence_2":"稿二最关键的一句原文优缺点短引","rationale":"2-3句具体对比裁决理由（指出关键差距）"}'
)


def _extract_json_obj(raw: str) -> dict[str, Any] | None:
    text = (raw or '').strip()
    if not text:
        return None
    if m := _JSON_FENCE_RE.search(text):
        text = m.group(1).strip()
    else:
        lo, hi = text.find('{'), text.rfind('}')
        if lo >= 0 and hi > lo:
            text = text[lo:hi + 1]
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except ValueError:
        cleaned = re.sub(r',\s*([}\]])', r'\1', text)
        try:
            obj = json.loads(cleaned)
            return obj if isinstance(obj, dict) else None
        except ValueError:
            return None


def evaluate_scene_vs_summary(
    outline_beats: list[str] | tuple[str, ...],
    draft_text: str,
    provider: LLMProvider,
    model: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate each planned beat strictly as `scene` (dramatized), `summary` (told), or `missing`."""
    beats = [str(b or '').strip() for b in (outline_beats or ()) if str(b or '').strip()]
    prose = (draft_text or '').strip()
    if not beats or not prose:
        return {
            'parsed_ok': True,
            'beats': [],
            'scene_count': 0,
            'summary_count': 0,
            'missing_count': 0,
            'all_dramatized': True,
            'summary': '无待核查节拍或正文为空。',
            'usage': {},
        }

    beat_lines = '\n'.join(f'{i}. {b}' for i, b in enumerate(beats, start=1))
    user_payload = f'【规划节拍列表】\n{beat_lines}\n\n【实际正文】\n{prose[:16000]}'
    messages = [
        {'role': 'system', 'content': SCENE_VS_SUMMARY_PROMPT},
        {'role': 'user', 'content': user_payload},
    ]
    live = provider.name != 'fake'
    gen = send_model(
        provider, messages, model, dict(params or {}),
        allow_continuation=False, max_empty_retries=(2 if live else 0),
    )
    parsed = _extract_json_obj(gen.text)
    rows: list[dict[str, Any]] = []
    if parsed and isinstance(parsed.get('beats'), list):
        for idx, item in enumerate(parsed['beats'], start=1):
            if not isinstance(item, dict):
                continue
            st = str(item.get('status') or 'missing').strip().lower()
            if st not in ('scene', 'summary', 'missing'):
                st = 'summary'
            rows.append({
                'index': int(item.get('index') or idx),
                'beat': str(item.get('beat') or (beats[idx - 1] if idx - 1 < len(beats) else ''))[:180],
                'status': st,
                'evidence': str(item.get('evidence') or '').strip()[:200],
                'reason': str(item.get('reason') or '').strip()[:220],
            })
    else:
        for idx, b in enumerate(beats, start=1):
            rows.append({
                'index': idx,
                'beat': b[:180],
                'status': 'summary',
                'evidence': '',
                'reason': '模型未返回标准 JSON，请人工复核该节拍是否充分展开。',
            })

    scene_cnt = sum(1 for r in rows if r['status'] == 'scene')
    summary_cnt = sum(1 for r in rows if r['status'] == 'summary')
    missing_cnt = sum(1 for r in rows if r['status'] == 'missing')
    return {
        'parsed_ok': parsed is not None,
        'beats': rows,
        'scene_count': scene_cnt,
        'summary_count': summary_cnt,
        'missing_count': missing_cnt,
        'all_dramatized': (len(rows) > 0 and summary_cnt == 0 and missing_cnt == 0),
        'summary': str((parsed or {}).get('summary') or f'共 {len(rows)} 拍：当场展开 {scene_cnt}、概述带过 {summary_cnt}、遗漏 {missing_cnt}。')[:300],
        'usage': gen.usage,
    }


def _run_single_blind_round(
    first_text: str,
    second_text: str,
    *,
    first_key: str,
    second_key: str,
    outline_text: str,
    criteria: str,
    provider: LLMProvider,
    model: str,
    params: dict[str, Any] | None,
) -> dict[str, Any]:
    parts: list[str] = []
    if outline_text.strip():
        parts.append(f'【本场任务参考】\n{outline_text.strip()[:2000]}')
    if criteria.strip():
        parts.append(f'【重点评审维度】\n{criteria.strip()[:600]}')
    parts.append(f'【稿一】\n{first_text.strip()[:12000]}')
    parts.append(f'【稿二】\n{second_text.strip()[:12000]}')

    messages = [
        {'role': 'system', 'content': BLIND_AB_JUDGE_PROMPT},
        {'role': 'user', 'content': '\n\n'.join(parts)},
    ]
    live = provider.name != 'fake'
    gen = send_model(
        provider, messages, model, dict(params or {}),
        allow_continuation=False, max_empty_retries=(2 if live else 0),
    )
    parsed = _extract_json_obj(gen.text)
    raw_pick = str((parsed or {}).get('winner') or 'tie').strip().lower()
    if raw_pick in ('1', 'first', '稿一', 'a'):
        slot_pick = '1'
        mapped = first_key
    elif raw_pick in ('2', 'second', '稿二', 'b'):
        slot_pick = '2'
        mapped = second_key
    else:
        slot_pick = 'tie'
        mapped = 'tie'

    return {
        'order': [first_key, second_key],
        'raw_slot_winner': slot_pick,
        'mapped_winner': mapped,
        'parsed_ok': parsed is not None,
        'evidence_first': str((parsed or {}).get('evidence_1') or '').strip()[:240],
        'evidence_second': str((parsed or {}).get('evidence_2') or '').strip()[:240],
        'rationale': str((parsed or {}).get('rationale') or gen.text[:240]).strip()[:500],
        'usage': gen.usage,
    }


def run_position_swapped_ab_judge(
    draft_a_text: str,
    draft_b_text: str,
    *,
    provider: LLMProvider,
    model: str,
    params: dict[str, Any] | None = None,
    outline_text: str = '',
    criteria: str = '',
    label_a: str = '稿件 A',
    label_b: str = '稿件 B',
) -> dict[str, Any]:
    """Execute position-swapped blind pairwise judging: (A, B) AND (B, A).

    A winner is declared ONLY when both swapped rounds agree on the same draft!
    Disagreement (e.g., always picking slot 1 due to LLM position bias) cleanly resolves to `tie`.
    """
    a_txt = (draft_a_text or '').strip()
    b_txt = (draft_b_text or '').strip()
    if not a_txt or not b_txt:
        raise ValueError('双盲对比需要同时提供两份非空草稿正文')

    round_ab = _run_single_blind_round(
        a_txt, b_txt,
        first_key='A', second_key='B',
        outline_text=outline_text, criteria=criteria,
        provider=provider, model=model, params=params,
    )
    round_ba = _run_single_blind_round(
        b_txt, a_txt,
        first_key='B', second_key='A',
        outline_text=outline_text, criteria=criteria,
        provider=provider, model=model, params=params,
    )

    pick1 = round_ab['mapped_winner']
    pick2 = round_ba['mapped_winner']
    position_bias = (pick1 in ('A', 'B') and pick2 in ('A', 'B') and pick1 != pick2)

    if pick1 == pick2 and pick1 in ('A', 'B'):
        winner = pick1
        consensus = True
        winner_label = label_a if winner == 'A' else label_b
        summary = f'双向换位双盲评审达成一致：胜出者为「{winner_label}」（正序与反序均一致判胜，已排除位置偏见）。'
    else:
        winner = 'tie'
        consensus = (pick1 == 'tie' and pick2 == 'tie')
        winner_label = '平局 / 需作者拍板'
        if position_bias:
            summary = (
                f'检测到裁判模型存在位置偏见（正序判 {pick1} 胜、换位后判 {pick2} 胜），'
                '系统自动裁定为「平局」，避免误选，请结合两轮证据由作者拍板。'
            )
        else:
            summary = f'两轮换位评审未达成单边一致（轮1={pick1}，轮2={pick2}），裁定为「平局 / 旗鼓相当」。'

    return {
        'winner': winner,
        'winner_label': winner_label,
        'label_a': label_a,
        'label_b': label_b,
        'consensus': consensus,
        'position_bias_detected': position_bias,
        'rounds': [round_ab, round_ba],
        'summary': summary,
    }
