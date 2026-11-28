"""One-Click Project Health Doctor (Read-Only Diagnostic + Optional Safe Cache Maintenance).

Inspects 8 health pillars of a novel project in SQLite without mutating canon:
  1. SQLite integrity, foreign keys & schema version
  2. Candidate branch & promotion readiness
  3. Stuck / blocked / waiting novel jobs (translated via Author Shell)
  4. Chapter summaries & periodic review backlog
  5. Serial Rhythm Debt & Strand balance (`serial_health.py`)
  6. Style fingerprint drift monitor (`craft_evolution.py`)
  7. Recurring override/rejection rule-promotion opportunities
  8. 4-Pillar Craft Spec coverage & derived replay cache status
"""
from __future__ import annotations

import json
from typing import Any

from nw.context.memory_orchestrator import clear_replay_cache, list_volume_summaries
from nw.craft_evolution import check_style_drift, list_promotion_proposals
from nw.craft_specs import load_all_craft_specs
from nw.craft_specs_base import CRAFT_DOMAINS, DOMAIN_META
from nw.override_ledger import list_overrides
from nw.schema import VERSION
from nw.serial_health import build_serial_health_board
from nw.store import Store
from nw.story_state import current_head, revision_state
from nw.studio.author_shell import translate_error


def _check_item(
    check_id: str,
    category: str,
    status: str,
    title: str,
    detail: str,
    *,
    repair_hint: str = '',
    action_target: str = '',
) -> dict[str, Any]:
    return {
        'id': check_id,
        'category': category,
        'status': status,  # 'ok' | 'warning' | 'error'
        'title': title,
        'detail': detail,
        'repair_hint': repair_hint,
        'action_target': action_target,
    }


def run_project_doctor(
    store: Store,
    *,
    branch: str = 'main',
    wizard: dict[str, Any] | None = None,
    repair_cache: bool = False,
) -> dict[str, Any]:
    """Run comprehensive 8-pillar project health diagnostics and return an Author-friendly report."""
    checks: list[dict[str, Any]] = []
    cache_cleared = 0
    if repair_cache:
        cache_cleared = clear_replay_cache(store)

    # 1. SQLite integrity & schema version
    integrity = [r[0] for r in store.connection.execute('PRAGMA integrity_check').fetchall()]
    fk_issues = store.connection.execute('PRAGMA foreign_key_check').fetchall()
    uv = int(store.connection.execute('PRAGMA user_version').fetchone()[0])
    if integrity == ['ok'] and not fk_issues and uv == VERSION:
        checks.append(_check_item(
            'db_integrity', '存储健康', 'ok',
            f'SQLite 单一真源完整（Schema v{uv}）',
            '完整性校验与外键约束全部通过，无数据损坏。',
        ))
    else:
        checks.append(_check_item(
            'db_integrity', '存储健康', 'error',
            '数据库完整性或版本异常',
            f'integrity={integrity}, fk_issues={len(fk_issues)}, user_version={uv}（期望 v{VERSION}）。',
            repair_hint='请先备份 nw.db 后检查最近一次升级或从自动生成的 nw.v*.bak 快照恢复。',
        ))

    # 2. Managed story & branch health
    managed = store.managed_story()
    branches = [
        dict(r)
        for r in store.connection.execute(
            'SELECT id, parent_branch_id, head_revision, enabled FROM story_branches WHERE enabled=1 ORDER BY rowid'
        ).fetchall()
    ]
    candidate_branches = [b for b in branches if b['id'] != 'main']
    if not managed:
        checks.append(_check_item(
            'branch_health', '状态与分支', 'warning',
            '作品尚未接入正式状态管理',
            '当前处于初始状态，尚未建立主线状态基线。',
            repair_hint='完成立项或执行故事采纳后即可启用双时钟 POV 状态管理。',
        ))
    elif candidate_branches and branch == 'main':
        checks.append(_check_item(
            'branch_health', '状态与分支', 'warning',
            f'存在 {len(candidate_branches)} 个未合并候选分支',
            f'候选分支：{", ".join(b["id"] for b in candidate_branches[:4])}。',
            repair_hint='若修改已完成，请在右上角「候选分支」复核并合并到正式主线，避免长期分叉。',
            action_target='branches',
        ))
    else:
        checks.append(_check_item(
            'branch_health', '状态与分支', 'ok',
            f'当前分支「{branch}」状态正常',
            f'已启用分支数：{len(branches)}。',
        ))

    # 3. Stuck / Blocked / Waiting jobs
    stuck_rows = store.connection.execute(
        "SELECT id, status, step_key, reason FROM novel_jobs WHERE branch_id=? AND status IN ('BLOCKED','STALE','WAITING') ORDER BY rowid DESC LIMIT 5",
        (branch,),
    ).fetchall()
    blocked_jobs = [r for r in stuck_rows if r['status'] in ('BLOCKED', 'STALE')]
    waiting_jobs = [r for r in stuck_rows if r['status'] == 'WAITING']
    if blocked_jobs:
        first_err = translate_error(blocked_jobs[0]['reason'] or '')
        checks.append(_check_item(
            'jobs_health', '任务流状态', 'error',
            f'有 {len(blocked_jobs)} 个任务处于受阻/过期状态：{first_err["title"]}',
            first_err['summary'],
            repair_hint=first_err['action_hint'],
            action_target='studio',
        ))
    elif waiting_jobs:
        checks.append(_check_item(
            'jobs_health', '任务流状态', 'warning',
            f'有 {len(waiting_jobs)} 个待作者拍板的门禁',
            f'当前停在步骤：{waiting_jobs[0]["step_key"] or "待确认"}。',
            repair_hint='打开制作台处理待确认门禁即可继续推进。',
            action_target='gates',
        ))
    else:
        checks.append(_check_item(
            'jobs_health', '任务流状态', 'ok',
            '无阻塞或卡死任务',
            '当前分支所有设计/写作任务状态清晰。',
        ))

    # 4. Chapter summaries & volume summaries coverage
    summary_missing = 0
    total_completed_chapters = 0
    vol_summaries: list[dict[str, Any]] = []
    if managed:
        head = current_head(store, branch)
        snapshot = revision_state(store, head)
        slots = snapshot.get('slots') or {}
        chapters = {c.id: c.index for c in store.list('chapter')}
        accepted_chs = sorted({
            chapters[sc.chapter_id]
            for sc in store.list('scene')
            if sc.id in slots and sc.chapter_id in chapters
        })
        total_completed_chapters = len(accepted_chs)
        recorded_chs = {
            int(r['idx'])
            for r in store.connection.execute(
                '''SELECT DISTINCT c."index" AS idx FROM chapter_records cr
                   JOIN chapters c ON c.id=cr.chapter_id
                   WHERE cr.branch_id=? AND cr.kind='summary' ''',
                (branch,),
            ).fetchall()
        }
        summary_missing = sum(1 for ch in accepted_chs if ch not in recorded_chs)
        vol_summaries = list_volume_summaries(store, branch_id=branch)
        if summary_missing > 0:
            checks.append(_check_item(
                'chapter_summaries', '长程记忆覆盖', 'warning',
                f'有 {summary_missing} 个已接受章节尚未记录章摘要',
                f'已接受 {total_completed_chapters} 章，其中 {summary_missing} 章缺少章摘要（章摘要是近章工作记忆的源头）。',
                repair_hint='在「章节续写与复盘」面板补录缺失章摘要，防止长篇记忆断层。',
                action_target='continuation',
            ))
        else:
            checks.append(_check_item(
                'chapter_summaries', '长程记忆覆盖', 'ok',
                f'章摘要齐全（已接受 {total_completed_chapters} 章，卷摘要 {len(vol_summaries)} 份）',
                '长程工作记忆与卷级情节记忆源头完备。',
            ))

    # 5. Serial Rhythm Debt & Strand balance
    tw = (wizard or {}).get('target_words') if isinstance((wizard or {}).get('target_words'), int) else None
    all_specs = load_all_craft_specs(store, wizard=wizard)
    serial_board = build_serial_health_board(store, branch=branch, plot_spec=all_specs.get('plot_pacing'), target_words=tw)
    if serial_board['status'] == 'alert':
        checks.append(_check_item(
            'serial_rhythm', '连载节奏健康', 'error',
            f'连载节奏债偏高（风险分 {serial_board["rhythm_debt_score"]}）',
            '；'.join(serial_board['next_chapter_corrections'][:3]) or '存在承诺逾期/停滞或连续弱钩。',
            repair_hint='规划下一章时优先兑现逾期承诺、切换 Strand 线轴并设置强钩子。',
            action_target='serial_board',
        ))
    elif serial_board['status'] == 'watch':
        checks.append(_check_item(
            'serial_rhythm', '连载节奏健康', 'warning',
            f'检测到 {len(serial_board["next_chapter_corrections"])} 条连载节奏提醒',
            '；'.join(serial_board['next_chapter_corrections'][:2]),
            repair_hint='系统已自动将纠偏建议注入下一章剧情策划，写前扫一眼盘面即可。',
            action_target='serial_board',
        ))
    else:
        checks.append(_check_item(
            'serial_rhythm', '连载节奏健康', 'ok',
            '三线配比、钩子与承诺节奏健康',
            f'已追踪 {serial_board.get("chapters_tracked", 0)} 章，无显著节奏债。',
        ))

    # 6. Style Drift Monitor
    drift = check_style_drift(store, branch=branch)
    if drift['status'] == 'drift_detected':
        checks.append(_check_item(
            'style_drift', '文体漂移监测', 'warning',
            f'检测到 {len(drift["drifts"])} 项文体指纹漂移',
            ' '.join(d['message'] for d in drift['drifts'][:2]),
            repair_hint='可在「工艺基座 · 活体演化」查看详情，决定加强语感回拉或更新文体基线。',
            action_target='craft_evolution',
        ))
    else:
        checks.append(_check_item(
            'style_drift', '文体漂移监测', 'ok',
            '文体指纹稳定' if drift['status'] == 'stable' else '文体基线待积累',
            drift['summary'],
        ))

    # 7. Recurring Override / Rejection Rule-Promotion Opportunities
    proposals = list_promotion_proposals(store, branch=branch, min_count=3)
    active_overrides = list_overrides(store, branch_id=branch, status='active', limit=100)
    if proposals:
        checks.append(_check_item(
            'evolution_proposals', '活体规则升格', 'warning',
            f'发现 {len(proposals)} 条高频校准规律可升格为本书红线',
            f'最高频项：{proposals[0]["proposed_redline"]}（已累计 {proposals[0]["count"]} 次）。',
            repair_hint='打开「工艺基座 · 活体演化」一键同意升格，以后 AI 不会再重复犯同类错。',
            action_target='craft_evolution',
        ))
    else:
        checks.append(_check_item(
            'evolution_proposals', '活体规则升格', 'ok',
            f'暂无待升格红线（当前生效软豁免 {len(active_overrides)} 条）',
            '系统会持续聚类你的打回与豁免记录，同类满 3 次自动提议固化规则。',
        ))

    # 8. 4-Pillar Craft Specs coverage & replay cache stats
    enabled_domains = [d for d in CRAFT_DOMAINS if isinstance(all_specs.get(d), dict) and all_specs[d].get('enabled', True)]
    missing_domains = [DOMAIN_META[d]['name'] for d in CRAFT_DOMAINS if d not in enabled_domains]
    cache_rows = int(store.connection.execute('SELECT COUNT(*) FROM state_replay_cache').fetchone()[0])
    if len(enabled_domains) == len(CRAFT_DOMAINS):
        checks.append(_check_item(
            'craft_specs', '四维工艺基座', 'ok',
            '四维可执行工艺基座已全部启用',
            f'世界/人物/剧情节奏/语感全部在线；派生状态重放缓存 {cache_rows} 条。',
        ))
    else:
        checks.append(_check_item(
            'craft_specs', '四维工艺基座', 'warning',
            f'已启用 {len(enabled_domains)}/4 个工艺基座',
            f'尚未启用：{"、".join(missing_domains)}；派生缓存 {cache_rows} 条。',
            repair_hint='建议在「本书工艺基座」抽屉中启用全部四维基座以获得完整约束闭环。',
            action_target='craft_specs',
        ))

    error_cnt = sum(1 for c in checks if c['status'] == 'error')
    warn_cnt = sum(1 for c in checks if c['status'] == 'warning')
    score = max(0, 100 - error_cnt * 22 - warn_cnt * 8)
    overall = 'blocked' if error_cnt else ('attention' if warn_cnt else 'healthy')
    summary = (
        f'体检完成：发现 {error_cnt} 项需优先处理的问题、{warn_cnt} 项优化提醒（健康分 {score}/100）。'
        if (error_cnt or warn_cnt)
        else f'体检全部通过！项目结构、状态机、连载节奏与文体指纹均处于最佳状态（健康分 {score}/100）。'
    )

    return {
        'branch_id': branch,
        'overall_status': overall,
        'score': score,
        'summary': summary,
        'error_count': error_cnt,
        'warning_count': warn_cnt,
        'checks': checks,
        'cache_cleared': cache_cleared,
        'stats': {
            'schema_version': uv,
            'completed_chapters': total_completed_chapters,
            'missing_summaries': summary_missing,
            'volume_summaries_count': len(vol_summaries),
            'active_overrides_count': len(active_overrides),
            'promotion_proposals_count': len(proposals),
            'replay_cache_rows': cache_rows,
            'rhythm_debt_score': serial_board['rhythm_debt_score'],
        },
    }
