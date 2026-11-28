"""Zero-token deterministic 5-section Natural-Language Writer Briefing Compiler.

Compiles the frozen structured `StoryProvider` context package (plus optional tiered
long-term memory layers) into a clean, zero-JSON-jargon Chinese writing briefing for
Step 15 drafting:
  1. 本场硬约束与眼前处境
  2. 此人此刻所知与认知边界
  3. 本场出场人物与世界规则印象
  4. 本书语感规范与本场微对照
  5. 前文紧邻承接与近期脉络

Internal audit manifests (`input_manifests`) continue to freeze the exact structured
JSON package & SHA256; real writer LLMs receive distraction-free natural Chinese prose
with 0 extra LLM calls and 0 secondary summarization hallucination.
"""
from __future__ import annotations

import json
from typing import Any


def _safe_json(text: str) -> Any:
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return text


def _format_value(value: Any, max_len: int = 180) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return '是' if value else '否'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value.strip()[:max_len]
    if isinstance(value, list):
        parts = [_format_value(v, 60) for v in value[:6] if v is not None]
        return '、'.join(p for p in parts if p)[:max_len]
    if isinstance(value, dict):
        if 'identity' in value:
            ident = value.get('identity') or '已解除'
            perms = _format_value(value.get('permissions') or [], 80)
            return f'{ident}' + (f'（权限/后果：{perms}）' if perms else '')
        parts = [f'{k}:{_format_value(v, 50)}' for k, v in list(value.items())[:5]
                 if k not in ('card_id', 'version', 'sha256', 'decision_id', 'source_refs') and v not in (None, '', [], {})]
        return '；'.join(parts)[:max_len]
    return str(value)[:max_len]


def _human_entity_label(entity_id: str, name_map: dict[str, str]) -> str:
    return name_map.get(entity_id, entity_id)


def should_use_natural_briefing(provider_name: str, config: Any | None = None, *, store: Any | None = None) -> bool:
    """Enable zero-token natural Chinese briefing for real production LLM providers by default.

    Isolated test doubles (`provider='fake'`, `store.test_mode=True`, or mock `model='test'`)
    continue to receive raw JSON `canonical(work.package)` unless explicitly opted in via
    `config.natural_briefing = True`.
    """
    explicit = getattr(config, 'natural_briefing', None) if config is not None else None
    if explicit is True:
        return True
    if explicit is False:
        return False
    if str(provider_name or '').strip().lower() == 'fake':
        return False
    if store is not None and bool(getattr(store, 'test_mode', False)):
        return False
    model_name = str(getattr(config, 'model', '') or '').strip().lower()
    if model_name == 'test':
        return False
    return True


def compile_writer_briefing(
    package: dict[str, Any],
    *,
    memory_layers: dict[str, Any] | None = None,
    char_limit: int | None = None,
) -> str:
    """Deterministically compile a frozen StoryProvider package into a 5-section Chinese briefing."""
    items = package.get('items') if isinstance(package, dict) else ()
    if not isinstance(items, list):
        items = []

    brief_data: dict[str, Any] | None = None
    scene_data: dict[str, Any] | None = None
    length_data: dict[str, Any] | None = None
    situation_data: dict[str, Any] | None = None
    voice_data: dict[str, Any] | None = None
    scene_beat_data: dict[str, Any] | None = None
    style_ref_data: dict[str, Any] | None = None
    author_memory_data: dict[str, Any] | None = None
    verified_excerpts_data: dict[str, Any] | None = None
    previous_prose = ''
    pov_holder = ''
    pov_facts: list[dict[str, Any]] = []
    reader_facts: list[dict[str, Any]] = []
    prior_evidence: list[dict[str, Any]] = []
    char_cards: list[tuple[str, dict[str, Any]]] = []
    world_cards: list[tuple[str, dict[str, Any]]] = []
    taboo_cards: list[tuple[str, dict[str, Any]]] = []
    other_cards: list[tuple[str, dict[str, Any]]] = []
    material_checks: list[dict[str, Any]] = []
    rules: list[dict[str, Any]] = []
    tiered_memory_data: dict[str, Any] | None = dict(memory_layers) if isinstance(memory_layers, dict) else None

    name_map: dict[str, str] = {}

    for item in items:
        if not isinstance(item, dict):
            continue
        src = str(item.get('source') or '')
        raw_text = str(item.get('text') or '')
        parsed = _safe_json(raw_text)
        if src == 'brief' and isinstance(parsed, dict):
            brief_data = parsed
        elif src.startswith('scene:') and isinstance(parsed, dict):
            scene_data = parsed
        elif src == 'chapter:length' and isinstance(parsed, dict):
            length_data = parsed
        elif src.startswith('situation:') and isinstance(parsed, dict):
            situation_data = parsed
        elif src == 'voice-spec' and isinstance(parsed, dict):
            voice_data = parsed
        elif src == 'scene-beat' and isinstance(parsed, dict):
            scene_beat_data = parsed
        elif src == 'style-reference' and isinstance(parsed, dict):
            style_ref_data = parsed
        elif src == 'author-memory' and isinstance(parsed, dict):
            author_memory_data = parsed
        elif src == 'verified-excerpts' and isinstance(parsed, dict):
            verified_excerpts_data = parsed
        elif src.startswith('previous:'):
            previous_prose = raw_text.strip()
        elif src.startswith('pov:'):
            pov_holder = src[4:]
            if isinstance(parsed, list):
                pov_facts = [row for row in parsed if isinstance(row, dict)]
        elif src == 'reader' and isinstance(parsed, list):
            reader_facts = [row for row in parsed if isinstance(row, dict)]
        elif src == 'prior-evidence' and isinstance(parsed, list):
            prior_evidence = [row for row in parsed if isinstance(row, dict)]
        elif src == 'memory-layers' and isinstance(parsed, dict):
            tiered_memory_data = parsed
        elif src.startswith('card:') and isinstance(parsed, dict):
            cid = src[5:]
            nm = str(parsed.get('name') or parsed.get('title') or '').strip()
            if nm:
                name_map[cid] = nm
            if 'role' in parsed or 'voice' in parsed or 'casting' in parsed:
                char_cards.append((cid, parsed))
            elif 'taboo' in cid.lower() or 'forbidden' in parsed or 'prohibitions' in parsed:
                taboo_cards.append((cid, parsed))
            elif 'rules' in parsed or 'setting' in parsed or 'premise' in parsed or 'world' in cid.lower():
                world_cards.append((cid, parsed))
            else:
                other_cards.append((cid, parsed))
        elif src.startswith('material:') and isinstance(parsed, dict):
            material_checks.append(parsed)
        elif src.startswith('rule:') and isinstance(parsed, dict):
            rules.append(parsed)

    pov_name = _human_entity_label(pov_holder, name_map) if pov_holder else '当前视角人物'

    # ── Section 1: 本场硬约束与眼前处境 ──
    s1: list[str] = ['## 一、本场硬约束与眼前处境']
    if scene_data:
        title = str(scene_data.get('title') or '').strip()
        if title:
            s1.append(f'- 本场标题：{title}')
        s1.append(f'- 叙述视角（POV）：{pov_name}' + (f'（{scene_data["narrative_person"]}）' if scene_data.get('narrative_person') else ''))
        for key, label in (
            ('location', '场景地点'),
            ('goal', '本场目标'),
            ('conflict', '核心阻力与冲突'),
            ('allowed_disclosure', '允许披露边界'),
            ('outcome', '本场候选推进落点'),
        ):
            val = _format_value(scene_data.get(key), 240)
            if val:
                s1.append(f'- {label}：{val}')
        if isinstance(scene_data.get('character_goals'), dict) and scene_data['character_goals']:
            for actor, goal in scene_data['character_goals'].items():
                s1.append(f'- {_human_entity_label(actor, name_map)}当下意图：{_format_value(goal, 180)}')
        wb = scene_data.get('word_budget') or scene_data.get('scene_length_estimate')
        if isinstance(wb, dict):
            lo, hi = wb.get('min_words'), wb.get('max_words')
            est = wb.get('target_words') or wb.get('estimated_words')
            if lo and hi:
                s1.append(f'- 本场篇幅预算：{lo}–{hi} 字' + (f'（参考 {est} 字）' if est else ''))
            elif est:
                s1.append(f'- 本场建议篇幅：约 {est} 字')
    if length_data:
        fmin, fmax = length_data.get('feasible_min_words'), length_data.get('feasible_max_words')
        if fmin and fmax:
            s1.append(f'- 按本章已写与余场动态换算的可写区间：{fmin}–{fmax} 字' + ('（本场为章末收束场）' if length_data.get('chapter_end') else ''))
    if situation_data:
        for key, label in (
            ('scene_frame', '眼前现场处境'),
            ('immediate_pressure', '当下逼近的压力'),
            ('playable_beats', '自然推进节拍'),
            ('anti_checklist_note', '写前提醒'),
        ):
            val = _format_value(situation_data.get(key), 240)
            if val:
                s1.append(f'- {label}：{val}')
    if brief_data:
        constraints = str(brief_data.get('constraints') or '').strip()
        if constraints:
            s1.append(f'- 作者硬约束：{constraints[:360]}')
    for cid, body in taboo_cards:
        txt = _format_value(body.get('rules') or body.get('prohibitions') or body.get('text') or body, 220)
        if txt:
            s1.append(f'- 本书禁忌：{txt}')

    # ── Section 2: 此人此刻所知与认知边界 ──
    s2: list[str] = ['## 二、此人此刻所知与认知边界']
    known_facts = [f for f in pov_facts if f.get('claim') == 'fact']
    beliefs = [f for f in pov_facts if f.get('claim') in ('belief', 'suspicion')]
    plans = [f for f in pov_facts if f.get('claim') in ('plan', 'utterance')]
    if known_facts:
        s2.append(f'- {pov_name}此刻确知事实：')
        for f in known_facts[:18]:
            ent = _human_entity_label(str(f.get('entity_id') or ''), name_map)
            pred = str(f.get('predicate') or '').replace('identity_status:', '身份:')
            s2.append(f'  · {ent} · {pred} = {_format_value(f.get("value"), 140)}')
    if beliefs:
        s2.append(f'- {pov_name}当前的判断与猜疑（可能有误，写作时不可当既定真相写死）：')
        for f in beliefs[:10]:
            ent = _human_entity_label(str(f.get('entity_id') or ''), name_map)
            tag = '怀疑' if f.get('claim') == 'suspicion' else '误信/认为'
            s2.append(f'  · [{tag}] {ent} · {f.get("predicate")} → {_format_value(f.get("value"), 140)}')
    if plans:
        s2.append(f'- {pov_name}近期计划或已说出口的话：')
        for f in plans[:8]:
            ent = _human_entity_label(str(f.get('entity_id') or ''), name_map)
            s2.append(f'  · {ent} · {f.get("predicate")} → {_format_value(f.get("value"), 140)}')
    if reader_facts:
        s2.append('- 读者此前也已得知（无需重复科普，自然承接即可）：')
        for f in reader_facts[:10]:
            ent = _human_entity_label(str(f.get('entity_id') or ''), name_map)
            s2.append(f'  · {ent} · {f.get("predicate")} = {_format_value(f.get("value"), 120)}')
    if len(s2) == 1:
        s2.append(f'- 本场严格坚守 {pov_name} 当前视角可见范围，不越界写出他尚未获知的幕后真相。')

    # ── Section 3: 本场出场人物与世界规则 ──
    s3: list[str] = ['## 三、本场出场人物与世界规则']
    for cid, body in char_cards[:12]:
        nm = str(body.get('name') or cid)
        role = str(body.get('role') or '').strip()
        voice = _format_value(body.get('voice') or body.get('speech_style'), 140)
        traits = _format_value(body.get('traits') or body.get('summary') or body.get('appearance'), 140)
        line = f'- 人物「{nm}」'
        if role:
            line += f'（{role}）'
        details = [x for x in (f'声线与口吻：{voice}' if voice else '', f'可见特征：{traits}' if traits else '') if x]
        if details:
            line += '：' + '；'.join(details)
        s3.append(line)
    for cid, body in world_cards[:6]:
        title = str(body.get('name') or body.get('title') or '世界规则')
        summary = _format_value(body.get('rules') or body.get('summary') or body.get('setting') or body, 220)
        if summary:
            s3.append(f'- 设定「{title}」：{summary}')
    for cid, body in other_cards[:4]:
        title = str(body.get('name') or body.get('title') or '')
        summary = _format_value(body, 160)
        if summary:
            s3.append(f'- 补充设定{("「" + title + "」") if title else ""}：{summary}')

    # ── Section 4: 本书语感规范与本场微对照 ──
    s4: list[str] = ['## 四、本书语感规范与本场微对照']
    if voice_data:
        vname = str(voice_data.get('voice_name') or voice_data.get('base_voice_name') or '').strip()
        if vname:
            s4.append(f'- 本书语感基座：{vname}')
        dims = voice_data.get('six_dimensions') or voice_data.get('dimensions')
        if isinstance(dims, dict):
            dim_labels = {
                'register': '语体用词', 'cadence': '句式呼吸', 'psychic_distance': '内心距离',
                'dialogue_texture': '对白质地', 'imagery_budget': '意象克制', 'pacing_payoff': '节奏落点',
            }
            for dk, dv in dims.items():
                if dv:
                    s4.append(f'  · {dim_labels.get(dk, dk)}：{str(dv).strip()[:160]}')
        for red in (voice_data.get('drift_redlines') or ())[:8]:
            if red:
                s4.append(f'  · 防漂移红线：{str(red).strip()[:160]}')
        contrasts_list = list(voice_data.get('micro_contrasts') or ())
        if not contrasts_list and isinstance(voice_data.get('scene_micro_contrast'), dict):
            contrasts_list = [voice_data['scene_micro_contrast']]
        for contrast in contrasts_list[:2]:
            if not isinstance(contrast, dict):
                continue
            bad = str(contrast.get('avoid_ai') or contrast.get('bad_ai') or '').strip()
            good = str(contrast.get('target_voice') or '').strip()
            if bad or good:
                lbl = contrast.get('label') or '本场正反微对照'
                src_tag = '（作者亲改示范）' if contrast.get('source') == 'author_edit' else ''
                s4.append(f'- {lbl}{src_tag}：')
                if bad:
                    s4.append(f'  ❌ 避免写法：{bad[:200]}')
                if good:
                    s4.append(f'  ✅ 目标语感：{good[:200]}')
                if contrast.get('why'):
                    s4.append(f'  💡 要领：{str(contrast["why"]).strip()[:140]}')
        notes = voice_data.get('author_voice_notes') or voice_data.get('custom_notes')
        if notes:
            s4.append(f'- 作者语感补充：{str(notes).strip()[:200]}')
    if scene_beat_data:
        for k, lbl in (
            ('beat_hint', '本场节拍与收束提示'),
            ('pacing_hint', '本场节拍提示'),
            ('hook_hint', '本场收束与钩子提示'),
            ('aftermath_hint', '承上启下提醒'),
            ('beat_summary', '节拍要点'),
        ):
            if scene_beat_data.get(k):
                s4.append(f'- {lbl}：{str(scene_beat_data[k]).strip()[:180]}')
    if style_ref_data and style_ref_data.get('excerpt'):
        s4.append(f'- 写前语感参照（只学呼吸与口吻，严禁照搬设定/人名）：\n  {str(style_ref_data["excerpt"]).strip()[:500]}')
    if author_memory_data and author_memory_data.get('lines'):
        s4.append('- 作者显式创作偏好（2KB 预算内最高优先级规则）：')
        for ln in (author_memory_data.get('lines') or ())[:16]:
            cleaned_ln = str(ln or '').strip()
            if cleaned_ln:
                s4.append(f'  {cleaned_ln}')
        if author_memory_data.get('omission_notice'):
            s4.append(f'  （注：{str(author_memory_data["omission_notice"]).strip()[:240]}）')
    if verified_excerpts_data and verified_excerpts_data.get('excerpts'):
        s4.append('- 三检实文匿名范例（只学行文呼吸与节奏，严禁照搬桥段）：')
        for ex in (verified_excerpts_data.get('excerpts') or ())[:2]:
            if not isinstance(ex, dict) or not ex.get('text'):
                continue
            learn = str(ex.get('learn_what') or '').strip()
            s4.append(f'  · [{ex.get("scene_function") or "实文示范"}] {learn}')
            s4.append(f'    {str(ex["text"]).strip()[:360]}')

    # ── Section 5: 前文紧邻承接、近期脉络与本场写法约束 ──
    s5: list[str] = ['## 五、前文紧邻承接与近期脉络']
    if previous_prose:
        s5.append(f'- 紧邻前场正文衔接：\n{previous_prose[-1200:]}')
    if tiered_memory_data:
        rec_sum = tiered_memory_data.get('recent_chapter_summaries') or []
        if rec_sum:
            s5.append('- 近章剧情脉络（工作记忆）：')
            for row in rec_sum[:3]:
                s5.append(f'  · 第{row.get("chapter_index")}章：{str(row.get("summary") or "").strip()[:200]}')
        vol_sum = tiered_memory_data.get('volume_summaries') or []
        if vol_sum:
            s5.append('- 前卷脉络压缩（情节记忆）：')
            for row in vol_sum[:4]:
                s5.append(f'  · 第{row.get("volume_index")}卷《{row.get("title") or ""}》：{str(row.get("summary") or "").strip()[:240]}')
        archived_count = int(tiered_memory_data.get('omitted_distant_facts_count') or 0)
        if archived_count > 0:
            s5.append(f'- （其余 {archived_count} 条与本场无直接交集的远期背景事实已折叠存档，不影响本场冲突）')
    if prior_evidence:
        quotes = [
            str(sp.get('quote') or '').strip()
            for row in prior_evidence[:6]
            for sp in (row.get('spans') or ())
            if isinstance(sp, dict) and sp.get('quote')
        ]
        if quotes:
            s5.append('- 前文支撑本场人物认知的关键原文片段：')
            for q in quotes[:4]:
                s5.append(f'  · “{q[:160]}”')
    if material_checks:
        s5.append('- 本场已绑定的具体演出要求：')
        for chk in material_checks[:8]:
            obs = chk.get('observable') or chk.get('instruction') or chk.get('description') or chk.get('binding')
            txt = _format_value(obs, 180)
            if txt:
                s5.append(f'  · {txt}')
    if rules:
        s5.append('- 本场适用的写法检验要点：')
        for r in rules[:6]:
            txt = _format_value(r.get('guidance') or r.get('problem') or r.get('rule') or r, 160)
            if txt:
                s5.append(f'  · {txt}')

    sections = [s1, s2, s3, s4, s5]
    rendered = '\n\n'.join('\n'.join(sec) for sec in sections if len(sec) > 1 or sec is s1)
    if char_limit and len(rendered) > char_limit:
        rendered = rendered[:max(200, char_limit - 18)].rstrip() + '\n（后续次要参考已按预算截断）'
    return rendered
