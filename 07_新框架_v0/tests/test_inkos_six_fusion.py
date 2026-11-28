"""Comprehensive verification suite for the 6 InkOS-inspired Dimensional Fusion Upgrades.

Covers:
  - SQLite Schema v13 (`narrative_forecasts`, `manuscript_imports`)
  - Fusion D: LLM Resilience (`strip_leading_think_blocks`, `merge_exact_continuation`,
              empty/thinking-only retry, hard network failure non-retry, Gemini param sanitization)
  - Fusion A: Host-Bounded Spot-Fix Local Revision + Episode-Baseline Diff-Aware Re-Review
  - Fusion C: Strict Promise Lifecycle (`mention != advance`, `superseded` archival,
              `PromiseArbiter` canonical deduplication, 0-Token Numeric Resource Ledger)
  - Fusion B: Non-Canonical Multi-Branch Narrative Forecast Sandbox + Staleness + Real Branch Fork
  - Fusion E: Fact-Frozen Semantic Deslop x Living VoiceSpec + Entity Preservation Guard
  - Fusion F: Step 17 Automatic State Reconciliation + `pinned/compressible` Compression Fallback
              + Evidence-Driven Half-Written Manuscript Import -> SQLite `_baseline`
"""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

import pytest

from nw.cards import decide_card, save_card
from nw.config import Config
from nw.context.memory_orchestrator import classify_memory_protection, compress_memory_layers_if_overflow
from nw.llm.base import GenResult
from nw.llm.resilience import (
    apply_think_stripping,
    merge_exact_continuation,
    resilient_generate,
    sanitize_provider_params,
    strip_leading_think_blocks,
)
from nw.manuscript_import import (
    analyze_manuscript,
    apply_manuscript_import_to_baseline,
    save_manuscript_import,
    split_manuscript_chapters,
)
from nw.materials.evidence import review_result as evidence_review_result
from nw.models import Draft, Run
from nw.narrative_forecast import (
    active_adopted_forecast_constraint,
    create_narrative_forecast,
    get_narrative_forecast,
    select_forecast_branch,
)
from nw.novel_calls import JobCalls
from nw.novel_scene import scene_delta
from nw.novel_store import JobRequest, Journal, start_job
from nw.promise_arbiter import (
    arbitrate_promise_operations,
    check_numeric_resource_ledger,
    parse_promise_op_semantics,
)
from nw.semantic_deslop import analyze_deslop_targets, run_semantic_deslop, verify_fact_preservation
from nw.serial_health import compute_promise_rhythm_debt
from nw.spot_fix import (
    apply_spot_fix_edits,
    compute_revision_diff,
    route_repair_scope,
    select_spot_fix_ranges,
)
from nw.store import Store, now
from nw.story_delta import check_delta, draft_digest, draft_ref, save_delta
from nw.story_state import adopt_story, apply_settings, current_head, revision_state
from nw.studio.author_shell import translate_error
from nw.task_models import Budget, InputManifest, canonical, content_sha256
from nw.tasks import freeze_manifest


class _ScriptedProvider:
    name = 'fake'

    def __init__(self, responses: list[GenResult | str]) -> None:
        self.responses = list(responses)
        self.calls: list[list[dict[str, Any]]] = []

    def generate(self, messages: list[dict[str, Any]], **params: Any) -> GenResult:
        self.calls.append(messages)
        if not self.responses:
            raise AssertionError('No scripted response left')
        nxt = self.responses.pop(0)
        if isinstance(nxt, GenResult):
            return nxt
        return GenResult(nxt, 'complete', {'prompt_tokens': 50, 'completion_tokens': 40}, f'req-{len(self.calls)}', {})


def _add_and_approve(store: Store, card_id: str, kind: str, body: dict):
    ref = save_card(store, {'card_id': card_id, 'kind': kind, 'origin': 'author', 'body': body, 'source_refs': []}, None)
    dec = decide_card(store, ref, 'approved', 'ok')
    return ref, dec.id


def _make_managed_store(tmp_path: Path, *, with_promise: bool = True, with_resource: bool = False) -> tuple[Store, str, str]:
    store = Store(tmp_path / 'demo_book', create=True, test_mode=True)
    store.init_project('测试长篇')
    store.add_brief('写出严密连载故事', '禁止机械降神')
    ch1 = store.add_chapter(1, '第一章 起始')
    _, char_dec = _add_and_approve(store, 'char-lin', 'character', {
        'name': '林川', 'role': '主角', 'want': '查明古玉来历', 'visibility': 'public',
    })
    _, scene_dec = _add_and_approve(store, 'sc-card-1', 'scene', {
        'title': '旧港交易',
        'pov': 'char-lin',
        'goal': '在旧港换取情报并守住底牌',
        'conflict': '对方试探灵石余额',
        'planned_result': '完成交易离开',
        'allowed_disclosure': '仅披露林川所见所闻',
        'characters': ['char-lin'],
        'visibility': 'public',
    })
    sc1 = store.add_scene(ch1.id, 1, json.dumps({
        'title': '旧港交易', 'pov': 'char-lin',
        'story': {'scene_ref': {'card_id': 'sc-card-1', 'version': 1}, 'story_order': 1},
    }, ensure_ascii=False))

    card_refs = [
        {'card_id': 'char-lin', 'version': 1, 'decision_id': char_dec},
        {'card_id': 'sc-card-1', 'version': 1, 'decision_id': scene_dec},
    ]
    facts: list[dict[str, Any]] = []
    entities = ['char-lin']
    predicates = ['life_status']

    if with_promise:
        _, p_dec = _add_and_approve(store, 'prom-jade', 'promise', {
            'title': '古玉裂纹的真正来历', 'setup': '古玉缺了一角', 'payoff': '揭晓十年前真相', 'visibility': 'public',
        })
        card_refs.append({'card_id': 'prom-jade', 'version': 1, 'decision_id': p_dec})
        entities.append('prom-jade')
        predicates.append('promise_stage')
        facts.append({
            'entity_id': 'prom-jade',
            'predicate': 'promise_stage',
            'holder': 'WORLD',
            'claim': 'fact',
            'story_order': 1,
            'disclosure_order': [1, 1, 0],
            'value': 'planted',
        })

    if with_resource:
        predicates.append('spirit_stones')
        facts.append({
            'entity_id': 'char-lin',
            'predicate': 'spirit_stones',
            'holder': 'WORLD',
            'claim': 'fact',
            'story_order': 0,
            'disclosure_order': [0, 0, 0],
            'value': 300,
        })

    baseline = {
        'as_of_story_order': 1 if with_promise else 0,
        'disclosure_order': [1, 1, 0] if with_promise else [0, 0, 0],
        'coverage': {'entities': entities, 'predicates': predicates},
        'facts': facts,
        'card_refs': card_refs,
    }
    adopt_story(store, baseline, {})
    return store, ch1.id, sc1.id


# ── 1. Schema v13 & Author Shell ──

def test_schema_v13_and_author_shell_translations(tmp_path: Path) -> None:
    store = Store(tmp_path / 'v13_check', create=True, test_mode=True)
    version = store.connection.execute('PRAGMA user_version').fetchone()[0]
    assert version == 13
    tables = {r[0] for r in store.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert 'narrative_forecasts' in tables
    assert 'manuscript_imports' in tables
    store.connection.close()

    for code in ('NUMERIC_LEDGER_MISMATCH', 'NUMERIC_LEDGER_NEGATIVE', 'PROMISE_LIFECYCLE', 'MODEL_EMPTY_AFTER_THINK'):
        t = translate_error(f'{code}: detail')
        assert t['code'] == code
        assert t['overridable'] is False
        assert t['action_hint']


# ── 2. Fusion D: Production LLM Resilience ──

def test_fusion_d_think_stripping_continuation_and_empty_retry() -> None:
    # Leading complete think blocks stripped; mid-prose and unclosed preserved!
    cleaned, thought = strip_leading_think_blocks('  <think>先想一下人物动机</think>\n<think>再理一理顺序</think>\n夜雨敲打窗棂。')
    assert cleaned == '夜雨敲打窗棂。'
    assert '先想一下人物动机' in thought and '再理一理顺序' in thought

    mid_text = '林川开口说：“<think>这是正文里故意写的标签</think>。”'
    c2, t2 = strip_leading_think_blocks(mid_text)
    assert c2 == mid_text and t2 == ''

    unclosed = '<think>尚未闭合的推理片段，绝不可静默删空'
    c3, t3 = strip_leading_think_blocks(unclosed)
    assert c3 == unclosed and t3 == ''

    # Thinking-only result flagged as MODEL_EMPTY_AFTER_THINK
    only_think, empty_flag = apply_think_stripping(GenResult('<think>只有思考没有正文</think>', 'complete', {}, 'r1', {}))
    assert empty_flag is True
    assert only_think.finish_reason == 'error'
    assert only_think.raw['_resilience_reason'] == 'MODEL_EMPTY_AFTER_THINK'

    # Exact-overlap continuation dedup
    stitched = merge_exact_continuation('林川推开木门，雨水灌进衣领。他盯着柜台后的掌柜。', '他盯着柜台后的掌柜。掌柜缓缓抬起头。')
    assert stitched == '林川推开木门，雨水灌进衣领。他盯着柜台后的掌柜。掌柜缓缓抬起头。'

    # Resilient generate: retries thinking-only empty output once, then seamlessly stitches truncated continuation!
    seq = [
        GenResult('<think>纯思考漏正文</think>', 'complete', {'completion_tokens': 10}, 'r1', {}),
        GenResult('<think>计划好了</think>第一段正文落雨无声。他摸向腰间。', 'truncated', {'completion_tokens': 30}, 'r2', {}),
        GenResult('他摸向腰间。铜钥冰凉，门外传来脚步声。', 'complete', {'completion_tokens': 25}, 'r3', {}),
    ]
    res = resilient_generate(lambda _msgs: seq.pop(0), [{'role': 'user', 'content': '写'}], allow_continuation=True, max_empty_retries=2)
    assert res.finish_reason == 'complete'
    assert res.text == '第一段正文落雨无声。他摸向腰间。铜钥冰凉，门外传来脚步声。'
    assert res.usage['completion_tokens'] == 65
    assert res.raw['_empty_retries'] == 1
    assert res.raw['_continuation_passes'] == 1

    # Hard HTTP/network failures NEVER retry!
    net_calls = 0

    def fail_net(_msgs: list[dict[str, Any]]) -> GenResult:
        nonlocal net_calls
        net_calls += 1
        return GenResult('', 'error', {}, None, {'http_status': 401})

    net_res = resilient_generate(fail_net, [{'role': 'user', 'content': 'hi'}], max_empty_retries=2)
    assert net_calls == 1
    assert net_res.finish_reason == 'error'

    # Gemini OpenAI-compat param sanitization strips `store`
    g_params = sanitize_provider_params('https://generativelanguage.googleapis.com/v1beta/openai', {'temperature': 0.7, 'store': True})
    assert 'store' not in g_params and g_params['temperature'] == 0.7


# ── 3. Fusion A: Host-Bounded Spot-Fix + Diff-Aware Review ──

def test_fusion_a_spot_fix_byte_protection_and_diff_review(tmp_path: Path) -> None:
    original = (
        '第一段：林川独自站在雨幕下，石阶湿滑发亮，远处的灯笼在风里晃动。\n\n'
        '第二段：他内心瞬间掀起了惊涛骇浪，一股寒意顺着脊背窜起，嘴角勾起一抹冷笑。\n\n'
        '第三段：掌柜低头算账，拨珠声清脆，自始至终没有看他一眼。'
    )
    plan = select_spot_fix_ranges(original, [1], max_ranges=3, max_affected_ratio=0.45)
    assert plan['eligible'] is True
    assert len(plan['ranges']) == 1

    # Oversized target (> 45%) cleanly escalates to structural!
    too_big = select_spot_fix_ranges(original, [0, 1, 2], max_ranges=3, max_affected_ratio=0.45)
    assert too_big['eligible'] is False

    # Apply spot-fix replacement -> P0 & P2 MUST be 100% byte-for-byte identical!
    model_json = json.dumps({'edits': [{'range_id': 'R1', 'replacement': '第二段：林川喉结滚了一下，手指慢慢收紧在伞柄上。'}]}, ensure_ascii=False)
    spliced = apply_spot_fix_edits(original, plan, model_json)
    assert spliced['protected_intact'] is True
    assert spliced['text'].startswith('第一段：林川独自站在雨幕下，石阶湿滑发亮，远处的灯笼在风里晃动。\n\n')
    assert spliced['text'].endswith('\n\n第三段：掌柜低头算账，拨珠声清脆，自始至终没有看他一眼。')
    assert '惊涛骇浪' not in spliced['text']

    # Diff-aware check catches unauthorized scope drift!
    drifted = spliced['text'].replace('掌柜低头算账', '店小二胡乱算账')
    diff_clean = compute_revision_diff(original, spliced['text'], authorized_paragraphs=[1])
    assert diff_clean['has_scope_drift'] is False
    assert diff_clean['changed_indices'] == [1]

    diff_drift = compute_revision_diff(original, drifted, authorized_paragraphs=[1])
    assert diff_drift['has_scope_drift'] is True
    assert 2 in diff_drift['scope_drift_paragraphs']

    # Review parser accepts optional repair_scope & target_paragraphs while staying backward compatible
    dummy_draft = Draft('d1', 'sc-1', 'run-1', 1, original, 'complete', now())
    run_enriched = Run(
        'r-rev', 'sc-1', 'review', 'fake', 'm', '{}', '{}', '{}',
        json.dumps({'recommendation': 'revise', 'notes': 'P1 有套话', 'core_changes': [], 'repair_scope': 'local', 'target_paragraphs': [1]}, ensure_ascii=False),
        'complete', '{}', now(), now(),
    )
    parsed = evidence_review_result(run_enriched, None, dummy_draft, None)
    assert parsed['repair_scope'] == 'local'
    assert parsed['target_paragraphs'] == [1]

    route = route_repair_scope(parsed, draft_text=original)
    assert route['scope'] == 'local'

    # End-to-end `scene_delta` with Spot-Fix + Diff-Aware Re-Review!
    store, _, sc_id = _make_managed_store(tmp_path, with_promise=False)
    job = start_job(store, JobRequest(mode='write', branch_id='main', scene_ids=[sc_id], budget=Budget(20, 200000, 4096, max_revisions=2)))
    journal = Journal(store, job.id)
    cfg = Config('fake', '', 'fake-model', '', 30.0, {}, tmp_path)
    setattr(cfg, 'enable_spot_fix', True)
    setattr(cfg, 'enable_diff_review', True)

    provider = _ScriptedProvider([
        # 1. Write initial draft
        original,
        # 2. Review round 0 -> request local Spot-Fix on paragraph 1
        json.dumps({'recommendation': 'revise', 'notes': '请去掉第2段AI套话', 'core_changes': [], 'repair_scope': 'local', 'target_paragraphs': [1]}, ensure_ascii=False),
        # 3. Spot-Fix JSON replacement for R1 only
        model_json,
        # 4. Diff-Aware Re-Review round 1 -> pass!
        json.dumps({'recommendation': 'pass', 'notes': '局部修改到位且保护段零改动', 'core_changes': []}, ensure_ascii=False),
        # 5. State extract -> empty ops
        json.dumps({'operations': []}),
        # 6. Fact review -> empty findings
        json.dumps({'findings': []}),
    ])
    calls = JobCalls(journal, provider, cfg, retry_failed=False)
    delta = scene_delta(calls, sc_id, (), lambda _k, _t: {'action': 'approve', 'reason': 'ok'})
    revised_draft = store.get('draft', delta.draft_id)
    assert '惊涛骇浪' not in revised_draft.text
    assert '第一段：林川独自站在雨幕下' in revised_draft.text
    assert '第三段：掌柜低头算账' in revised_draft.text
    # Verify round-1 review received the episode-baseline diff summary in its system prompt!
    review_r1_sys = provider.calls[3][0]['content']
    assert '版本差异对照' in review_r1_sys
    store.connection.close()


# ── 4. Fusion C: Mention != Advance, Superseded, PromiseArbiter, Numeric Ledger ──

def test_fusion_c_promise_semantics_arbiter_and_numeric_ledger(tmp_path: Path) -> None:
    # 1. `mention` != `advance`, `defer` != `advance`, `superseded` forbidden on `paid_off`
    sem_m = parse_promise_op_semantics({'op': 'advance_promise', 'expected_old': 'planted', 'new_value': {'stage': 'planted', 'action_kind': 'mention', 'note': '顺口想起古玉'}})
    assert sem_m['advances_progress'] is False and sem_m['is_mention_only'] is True

    sem_d = parse_promise_op_semantics({'op': 'advance_promise', 'expected_old': 'planted', 'new_value': {'stage': 'sleeping', 'action_kind': 'defer'}})
    assert sem_d['advances_progress'] is False and sem_d['is_deferred'] is True

    sem_a = parse_promise_op_semantics({'op': 'advance_promise', 'expected_old': 'planted', 'new_value': {'stage': 'awake', 'action_kind': 'advance', 'note': '查到旧港玉匠名录'}})
    assert sem_a['advances_progress'] is True

    with pytest.raises(ValueError, match='PROMISE_LIFECYCLE'):
        parse_promise_op_semantics({'op': 'advance_promise', 'expected_old': 'paid_off', 'new_value': {'stage': 'superseded', 'reason': '想删历史'}})
    with pytest.raises(ValueError, match='PROMISE_LIFECYCLE'):
        parse_promise_op_semantics({'op': 'advance_promise', 'expected_old': 'planted', 'new_value': {'stage': 'superseded'}})

    # 2. PromiseArbiter prevents ghost duplicate promise IDs
    existing = [{'card_id': 'prom-jade', 'title': '古玉裂纹的真正来历', 'accepted_stage': 'planted'}]
    ghost_ops = [{
        'op': 'introduce_promise',
        'entity_id': 'prom-ghost-99',
        'predicate': 'promise_stage',
        'holder': 'WORLD',
        'expected_old': None,
        'new_value': {'stage': 'planted', 'title': '古玉裂纹真正来历'},
    }]
    fixed_ops, arb_notes = arbitrate_promise_operations(existing, ghost_ops)
    assert fixed_ops[0]['entity_id'] == 'prom-jade'
    assert fixed_ops[0]['op'] == 'advance_promise'
    assert arb_notes[0]['action'] == 'deduplicated_to_canonical'

    # 3. `serial_health.compute_promise_rhythm_debt`: mention at ch 12 MUST NOT clear stalled debt from ch 1!
    store, _, sc_id = _make_managed_store(tmp_path, with_promise=True)
    # Record a draft & delta with a `mention`-only op at chapter 12
    ch12 = store.add_chapter(12, '第十二章 回响')
    sc12 = store.add_scene(ch12.id, 1, json.dumps({
        'title': '茶馆闲聊', 'pov': 'char-lin',
        'story': {'scene_ref': {'card_id': 'sc-card-1', 'version': 1}, 'story_order': 12},
    }, ensure_ascii=False))
    mention_text = '林川抿了口茶，忽然想起袖中那枚古玉。'
    store.add_run(Run('run-12', sc12.id, 'write', 'author', 'manual', '{}', canonical({'source': 'manual'}), '{}', '', 'error', '{}', now(), ''))
    _, draft12 = store.finish_run('run-12', GenResult(mention_text, 'complete', {}, 'run-12', {}))
    assert draft12 is not None
    head = current_head(store, 'main')
    m_pkg = {'draft_id': draft12.id, 'draft_sha256': draft_digest(draft12), 'facts': [], 'settings': []}
    freeze_manifest(store, InputManifest(
        'man-12', 'state_extract',
        {'provider': 'author', 'model': 'manual', 'params': {}, 'prompt_version': 'state-extract-v1', 'base_url': None, 'timeout': None, 'stream': False},
        content_sha256(m_pkg), branch_id='main', state_revision=head.revision, story_order=12, disclosure_order=(12, 1, 0),
    ), m_pkg)
    mention_op = {
        'op': 'advance_promise',
        'entity_id': 'prom-jade',
        'predicate': 'promise_stage',
        'holder': 'WORLD',
        'claim': 'fact',
        'story_order': 12,
        'disclosure_order': [12, 1, 0],
        'expected_old': 'planted',
        'new_value': {'stage': 'planted', 'action_kind': 'mention', 'note': '顺口想起'},
        'evidence': [{'draft_id': draft12.id, 'text_sha256': draft_digest(draft12), 'start': 0, 'end': len(mention_text)}],
    }
    delta12 = save_delta(store, 'delta-12', draft12.id, 'man-12', [mention_op])
    snap = revision_state(store, head)
    snap['slots'][sc12.id] = {'draft_id': draft12.id, 'delta_id': delta12.id}

    debt = compute_promise_rhythm_debt(store, head, snap, current_chapter=12, stall_limit=10)
    assert len(debt['stalled']) == 1
    assert debt['stalled'][0]['last_advanced_chapter'] == 1
    assert debt['stalled'][0]['last_mentioned_chapter'] == 12
    assert debt['stalled'][0]['mention_without_advance'] is True

    # 4. Superseding the promise removes it cleanly from rhythm debt without erasing history!
    sup_op = {
        **mention_op,
        'new_value': {'stage': 'superseded', 'action_kind': 'supersede', 'reason': '第二卷改纲取消古玉支线'},
    }
    delta12_sup = save_delta(store, 'delta-12-sup', draft12.id, 'man-12', [sup_op])
    snap_sup = revision_state(store, head)
    snap_sup['slots'][sc12.id] = {'draft_id': draft12.id, 'delta_id': delta12_sup.id}
    debt_sup = compute_promise_rhythm_debt(store, head, snap_sup, current_chapter=12, stall_limit=10)
    assert debt_sup['rhythm_debt_count'] == 0
    assert 'prom-jade' in debt_sup['superseded']
    store.connection.close()

    # 5. Numeric resource double-entry ledger check
    prose = '林川从袋里摸出灵石，当场花了120块灵石买下残图。'
    bad_op = {
        'entity_id': 'char-lin',
        'predicate': 'spirit_stones',
        'expected_old': 300,
        'new_value': 280,  # Should be 180!
        'evidence': [{'start': 0, 'end': len(prose)}],
    }
    bad_findings = check_numeric_resource_ledger([bad_op], prose, {'kind': 'draft', 'id': 'd1'})
    assert any(f['code'] == 'NUMERIC_LEDGER_MISMATCH' for f in bad_findings)

    neg_op = {
        'entity_id': 'char-lin',
        'predicate': '灵石',
        'expected_old': 50,
        'new_value': -20,
        'evidence': [{'start': 0, 'end': len(prose)}],
    }
    neg_findings = check_numeric_resource_ledger([neg_op], prose, {'kind': 'draft', 'id': 'd1'})
    assert any(f['code'] == 'NUMERIC_LEDGER_NEGATIVE' for f in neg_findings)

    good_op = {**bad_op, 'new_value': 180}
    assert check_numeric_resource_ledger([good_op], prose, {'kind': 'draft', 'id': 'd1'}) == []


# ── 5. Fusion B: Non-Canonical Multi-Branch Narrative Forecast Sandbox ──

def test_fusion_b_narrative_forecast_isolation_staleness_and_fork(tmp_path: Path) -> None:
    store, _, _ = _make_managed_store(tmp_path)
    commits_before = store.connection.execute('SELECT COUNT(*) FROM story_commits').fetchone()[0]

    fc = create_narrative_forecast(
        store,
        divergence='拍卖会结束后长老逼宫交出古玉，林川如何应对',
        branch_id='main',
        branch_count=3,
        horizon=5,
        offline_preview=True,
    )
    assert fc['status'] == 'active'
    assert fc['stale'] is False
    assert len(fc['branches']) == 3
    assert len(fc['branches'][0]['beats']) == 5
    # Zero canonical mutation!
    assert store.connection.execute('SELECT COUNT(*) FROM story_commits').fetchone()[0] == commits_before

    # Adopt branch-2 as non-canonical planning constraint
    adopted = select_forecast_branch(store, fc['id'], 'branch-2', mode='adopt_constraint')
    assert adopted['status'] == 'adopted'
    assert adopted['selected_branch_id'] == 'branch-2'
    assert store.connection.execute('SELECT COUNT(*) FROM story_commits').fetchone()[0] == commits_before
    constraint = active_adopted_forecast_constraint(store, branch_id='main')
    assert constraint is not None and constraint['branch_id'] == 'branch-2'

    # Fork a REAL isolated candidate branch from branch-1
    forked = select_forecast_branch(store, fc['id'], 'branch-1', mode='fork_branch', new_branch_id='cand-auction-fight')
    assert forked['status'] == 'forked'
    assert forked['forked_branch_id'] == 'cand-auction-fight'
    assert current_head(store, 'cand-auction-fight').branch_id == 'cand-auction-fight'

    # Create another forecast, then advance canonical main -> auto-marks stale!
    fc2 = create_narrative_forecast(store, divergence='次日潜入禁地路线', offline_preview=True)
    _, dec_id = _add_and_approve(store, 'world-forbidden', 'world', {
        'title': '北渊禁地', 'rule': '子时封山', 'limits': '违者重罚', 'visibility': 'public',
    })
    apply_settings(store, current_head(store, 'main'), [dec_id], 'commit-advance-main')
    reloaded = get_narrative_forecast(store, fc2['id'])
    assert reloaded['stale'] is True
    assert reloaded['status'] == 'stale'
    store.connection.close()


# ── 6. Fusion E: Fact-Frozen Semantic Deslop ──

def test_fusion_e_semantic_deslop_and_entity_preservation(tmp_path: Path) -> None:
    store, _, _ = _make_managed_store(tmp_path)
    prose = (
        '林川推开旧港木门，咸腥的海风灌进袖口。\n\n'
        '林川紧握双拳，心中满是愤怒，嘴角勾起一抹冷笑。围观众人瞬间倒吸一口凉气。\n\n'
        '“众所周知，我们旧港向来只认灵石不认人。”摊主压低了帽檐。'
    )
    analysis = analyze_deslop_targets(prose)
    assert analysis['needs_deslop'] is True
    assert 1 in analysis['recommended_target_paragraphs']
    assert 2 in analysis['recommended_target_paragraphs']

    deslop_reply = json.dumps({
        'edits': [
            {
                'range_id': 'R1',
                'replacement': (
                    '林川指节攥得发白，只把茶碗重重磕在桌上。靠门两个船夫停了筷子，彼此递了个眼色。\n\n'
                    '“旧港只认现石。”摊主把帽檐往下按了半寸，“赊账的骨头都在海沟里。”'
                ),
            }
        ]
    }, ensure_ascii=False)
    prov = _ScriptedProvider([deslop_reply])
    res = run_semantic_deslop(store, prose, prov, 'fake-model', target_paragraphs=[1, 2], max_affected_ratio=0.8)
    assert res['status'] == 'ok'
    assert res['protected_intact'] is True
    assert res['fact_preservation']['passed'] is True
    assert res['after_slop_hits'] < res['before_slop_hits']
    assert res['polished_text'].startswith('林川推开旧港木门，咸腥的海风灌进袖口。\n\n')

    # Entity preservation guard catches accidental character drop!
    bad_pres = verify_fact_preservation(prose, '有人推开木门走了进来。', canonical_names=['林川'])
    assert bad_pres['passed'] is False
    assert '林川' in bad_pres['dropped_entities']
    store.connection.close()


# ── 7. Fusion F1: Step 17 Automatic State-Settlement Reconciliation ──

def test_fusion_f1_step17_auto_reconciliation_recovers_without_modifying_prose(tmp_path: Path) -> None:
    store, _, sc_id = _make_managed_store(tmp_path, with_promise=False, with_resource=True)
    approved_prose = '林川走进旧港铺子，数出灵石，当场花了120块灵石买下一张海图。'
    job = start_job(store, JobRequest(mode='write', branch_id='main', scene_ids=[sc_id], budget=Budget(20, 200000, 4096)))
    journal = Journal(store, job.id)
    cfg = Config('fake', '', 'fake-model', '', 30.0, {}, tmp_path)
    setattr(cfg, 'auto_reconcile_state', True)

    # Scripted provider:
    #   1. write -> approved_prose
    #   2. review -> pass
    #   3. state_extract #1 -> WRONG balance 280 (300 - 120 != 280) -> triggers NUMERIC_LEDGER_MISMATCH hard finding!
    #   4. fact_review #1 -> empty findings (the 0-token numeric ledger catches the bad balance!)
    #   5. state_extract #2 (reconcile1) -> corrected balance 180!
    #   6. fact_review #2 -> empty findings -> reconciled cleanly!
    def _extract_json(draft_id: str, closing_val: int) -> str:
        return json.dumps({
            'operations': [{
                'op': 'set',
                'entity_id': 'char-lin',
                'predicate': 'spirit_stones',
                'holder': 'WORLD',
                'claim': 'fact',
                'story_order': 1,
                'disclosure_order': [1, 1, 0],
                'expected_old': 300,
                'new_value': closing_val,
                'evidence': [{'draft_id': draft_id, 'text_sha256': content_sha256(approved_prose), 'start': 0, 'end': len(approved_prose)}],
            }]
        })

    # Dynamic wrapper since draft_id and text_sha256 are known after write runs
    class _ReconcileProvider:
        name = 'fake'

        def __init__(self) -> None:
            self.step = 0
            self.reconcile_prompt_seen = ''

        def generate(self, messages: list[dict[str, Any]], **params: Any) -> GenResult:
            self.step += 1
            if self.step == 1:
                return GenResult(approved_prose, 'complete', {}, 'r1', {})
            if self.step == 2:
                return GenResult(json.dumps({'recommendation': 'pass', 'notes': 'ok', 'core_changes': []}), 'complete', {}, 'r2', {})
            if self.step in (3, 5):
                payload = json.loads(messages[-1]['content'])
                d = payload['draft']
                ev = payload['evidence_format']
                if self.step == 5:
                    self.reconcile_prompt_seen = messages[0]['content']
                val = 280 if self.step == 3 else 180
                return GenResult(json.dumps({
                    'operations': [{
                        'op': 'set',
                        'entity_id': 'char-lin',
                        'predicate': 'spirit_stones',
                        'holder': 'WORLD',
                        'claim': 'fact',
                        'story_order': 1,
                        'disclosure_order': [1, 1, 0],
                        'expected_old': 300,
                        'new_value': val,
                        'evidence': [ev],
                    }]
                }), 'complete', {}, f'r{self.step}', {})
            return GenResult(json.dumps({'findings': []}), 'complete', {}, f'r{self.step}', {})

    prov = _ReconcileProvider()
    calls = JobCalls(journal, prov, cfg, retry_failed=False)
    delta = scene_delta(calls, sc_id, (), lambda _k, _t: {'action': 'approve', 'reason': 'ok'})
    assert delta.operations[0]['new_value'] == 180
    assert 'NUMERIC_LEDGER_MISMATCH' in prov.reconcile_prompt_seen
    assert store.get('draft', delta.draft_id).text == approved_prose
    rec_step = journal.latest(f'scene:{sc_id}:reconcile')
    assert rec_step is not None and rec_step['output']['status'] == 'reconciled'
    store.connection.close()


# ── 8. Fusion F2 & F3: Compression Fallback + Half-Written Manuscript Import ──

def test_fusion_f2_memory_compression_and_f3_manuscript_import(tmp_path: Path) -> None:
    # F2: pinned vs compressible classification + zero-token passthrough + overflow compression
    assert classify_memory_protection('pov:char-lin') == 'pinned'
    assert classify_memory_protection('voice-spec') == 'pinned'
    assert classify_memory_protection('memory-layers') == 'compressible'

    small_layers = {'volume_summaries': [{'volume_index': 1, 'title': '第一卷', 'summary_text': '林川初入旧港。'}], 'recent_chapter_summaries': []}
    untouched = compress_memory_layers_if_overflow(small_layers, char_budget=1000)
    assert untouched['compression_applied'] is False

    huge_layers = {
        'volume_summaries': [
            {'volume_index': i, 'title': f'第{i}卷', 'summary_text': f'林川在第{i}卷调查古玉真相。' + '详细经过' * 80}
            for i in range(1, 7)
        ],
        'recent_chapter_summaries': [{'chapter_index': 99, 'summary': '近期总结' * 50}],
    }
    compressed = compress_memory_layers_if_overflow(huge_layers, char_budget=500, pinned_entity_ids=['林川', '古玉'])
    assert compressed['compression_applied'] is True
    assert compressed['protection_mode'] == 'deterministic_compressible_only'
    assert len(compressed['volume_summaries']) <= 4

    # F3: Evidence-driven half-written manuscript import with dual-evidence contradiction preservation!
    raw_ms = (
        '第一章 雨夜旧港\n'
        '林川冷冷道：“古玉的秘密终究藏不住。”\n'
        '账房老周已经死了，倒在码头仓库里。\n\n'
        '第二章 栈桥交锋\n'
        '林川问道：“这批货究竟是谁运走的？”\n'
        '老周站起身拍了拍衣袖，笑道：“货已经入库了。”'
    )
    chapters = split_manuscript_chapters(raw_ms)
    assert len(chapters) == 2
    report = analyze_manuscript(raw_ms, title='旧港半成品')
    assert report['chapter_count'] == 2
    assert any(c['name'] == '林川' for c in report['characters'])
    assert report['has_conflicts'] is True
    conflict = report['conflicts'][0]
    assert conflict['entity'] == '老周'
    assert conflict['evidence_a']['chapter'] == 1
    assert conflict['evidence_b']['chapter'] == 2

    # Save & verify unresolved contradiction BLOCKS silent baseline adoption!
    store = Store(tmp_path / 'import_book', create=True, test_mode=True)
    store.init_project('旧港半成品')
    store.add_brief('导入已有前两章续写', '保持连贯')
    saved = save_manuscript_import(store, report)
    with pytest.raises(ValueError, match='自相矛盾'):
        apply_manuscript_import_to_baseline(store, saved['id'])

    # Once author resolves contradiction explicitly -> cleanly wakes up SQLite `_baseline`!
    applied = apply_manuscript_import_to_baseline(
        store,
        saved['id'],
        resolved_conflicts={conflict['id']: 'alive'},
    )
    assert applied['chapters_imported'] == 2
    assert applied['next_chapter_index'] == 3
    assert store.managed_story() is True
    assert current_head(store, 'main').revision == 0
    store.connection.close()
