"""Non-Canonical Multi-Branch Narrative Forecast Sandbox (Fusion B x Story Branches).

Allows authors to project 2-5 divergent futures (default 3 branches x 5 chapters) from any
mid-book point BEFORE mutating canonical state or creating heavy DB branches:
  - Strictly non-canonical: create / get / adopt NEVER write `story_commits`, `drafts`, or `cards`.
  - Context-fingerprint staleness: computes `context_sha256` from branch head + serial health +
    active cards; if canonical story advances, old forecasts are automatically marked `stale`.
  - Dual landing actions:
      1. `adopt_constraint`: freezes the chosen branch into `selected_plan_json` as upcoming
         planning guidance (zero canon mutation).
      2. `fork_branch`: one-click spawns a REAL isolated candidate branch via `fork_story`
         seeded with the adopted forecast plan!
"""
from __future__ import annotations

import json
import re
from typing import Any
from uuid import uuid4

from nw.call_control import send_model
from nw.cards import read_card
from nw.craft_specs import load_all_craft_specs
from nw.llm.base import LLMProvider
from nw.serial_health import build_serial_health_board
from nw.store import Store, now
from nw.story_models import CardRef, StateHead
from nw.story_state import current_head, fork_story, revision_state
from nw.task_models import canonical, content_sha256

DEFAULT_BRANCH_COUNT = 3
DEFAULT_HORIZON = 5
_JSON_FENCE_RE = re.compile(r'```(?:json)?\s*(\{.*?\})\s*```', re.DOTALL | re.IGNORECASE)


def build_forecast_context(store: Store, *, branch_id: str = 'main', target_words: int | None = None) -> dict[str, Any]:
    """Assemble read-only canonical snapshot + serial health board + SHA256 staleness fingerprint."""
    if not store.managed_story():
        raise ValueError('当前作品尚未初始化正史分支，无法运行剧情沙盘推演')
    head = current_head(store, branch_id)
    snapshot = revision_state(store, head)
    specs = load_all_craft_specs(store)
    board = build_serial_health_board(
        store,
        branch=branch_id,
        plot_spec=specs.get('plot_pacing'),
        target_words=target_words,
    )

    characters: list[dict[str, Any]] = []
    world_rules: list[str] = []
    active_promises: list[dict[str, Any]] = []
    for row in snapshot.get('settings') or ():
        try:
            card = read_card(store, CardRef(row['card_id'], row['version']))
        except Exception:
            continue
        body = card.get('body') or {}
        if card['kind'] == 'character':
            characters.append({
                'id': card['card_id'],
                'name': str(body.get('name') or body.get('title') or card['card_id']),
                'role': str(body.get('role') or '')[:48],
                'goal': str(body.get('goal') or body.get('desire') or '')[:90],
            })
        elif card['kind'] == 'world':
            title = str(body.get('title') or body.get('name') or card['card_id'])
            rule = str(body.get('rule') or body.get('summary') or '')[:100]
            world_rules.append(f'{title}：{rule}' if rule else title)

    for p in (board.get('promise_debt') or {}).get('items') or ():
        if p.get('accepted_stage') not in ('paid_off', 'superseded'):
            active_promises.append({
                'id': p.get('card_id'),
                'title': p.get('title'),
                'stage': p.get('accepted_stage'),
                'priority': p.get('priority'),
                'stalled_chapters': p.get('stalled_chapters', 0),
            })

    base_chapter = int(board.get('latest_chapter') or 0)
    fingerprint_payload = {
        'branch_id': branch_id,
        'head_revision': head.revision,
        'base_chapter': base_chapter,
        'slots': sorted((k, v.get('draft_id'), v.get('delta_id')) for k, v in (snapshot.get('slots') or {}).items()),
        'settings': sorted((s['card_id'], s['version']) for s in (snapshot.get('settings') or ())),
    }
    ctx_sha = content_sha256(fingerprint_payload)

    return {
        'branch_id': branch_id,
        'base_revision': head.revision,
        'base_chapter': base_chapter,
        'context_sha256': ctx_sha,
        'characters': characters[:12],
        'world_rules': world_rules[:8],
        'active_promises': active_promises[:10],
        'serial_health_status': board.get('status', 'healthy'),
        'next_chapter_corrections': list(board.get('next_chapter_corrections') or ())[:4],
        'strand_profile': board.get('strand_profile') or {},
    }


def _offline_forecast_branches(ctx: dict[str, Any], divergence: str, branch_count: int, horizon: int) -> list[dict[str, Any]]:
    """Deterministic zero-token structural sandbox archetypes grounded in live book state."""
    base_ch = ctx['base_chapter']
    lead_char = ctx['characters'][0]['name'] if ctx['characters'] else '主角'
    second_char = ctx['characters'][1]['name'] if len(ctx['characters']) > 1 else '关键对手/盟友'
    top_promise = ctx['active_promises'][0]['title'] if ctx['active_promises'] else '核心悬念线索'
    corrections = ctx.get('next_chapter_corrections') or []

    archetypes = [
        {
            'label': '破局强攻线（高压直撞）',
            'premise': f'围绕「{divergence}」，{lead_char}拒绝退让，主动掀桌逼迫对手提前暴露底牌，拉满爽感与短期冲突烈度。',
            'strands': ['quest', 'quest', 'fire', 'quest', 'constellation'],
            'decision': f'{lead_char}选择冒暴露身份/资源损耗之险正面破局，迫使{second_char}被迫表态。',
            'ripples': {
                'characters': [f'{lead_char}声望与仇恨值同步飙升'],
                'relationships': [f'{lead_char}与{second_char}从试探转为正面交锋'],
                'world': ['局部势力平衡被提前打破，幕后阵营开始介入'],
                'promises': [f'提前推进「{top_promise}」的核心证据链'],
            },
            'risks': ['短期爽感释放过快，若后续新压迫感衔接不紧易导致中段泄气', *(corrections[:1])],
            'uncertainties': ['对手提前底牌耗尽后，下一卷反派压迫源需要及时补位'],
            'intent_rationale': '适合追读承压、需要立刻给读者强反馈与高燃反转的连载窗口。',
        },
        {
            'label': '暗度权谋线（设局反杀）',
            'premise': f'围绕「{divergence}」，{lead_char}表面顺势示弱让出小利，暗中利用信息差借刀杀人，留足后续大回收张力。',
            'strands': ['quest', 'fire', 'constellation', 'quest', 'quest'],
            'decision': f'{lead_char}隐忍不发，暗线联络{second_char}或第三方势力交换筹码，等待对手自露破绽。',
            'ripples': {
                'characters': [f'{lead_char}掌握额外暗牌，但背负秘密误解压力'],
                'relationships': [f'{lead_char}与{second_char}形成脆弱利益同盟'],
                'world': ['更大格局的规则漏洞与幕后各方势力版图浮出水面'],
                'promises': [f'为「{top_promise}」叠加新悬疑层并埋入反杀钩子'],
            },
            'risks': ['若连续 2 章以上缺乏微回报，读者容易产生憋屈感'],
            'uncertainties': ['同盟方的真实立场在未兑现前随时可能反水'],
            'intent_rationale': '适合悬疑推理、权谋暗战或长篇中段需要兼顾三线平衡（Quest/Fire/Constellation）的阶段。',
        },
        {
            'label': '代价翻转线（意外变量）',
            'premise': f'围绕「{divergence}」，突发外部变量打乱原计划，{lead_char}被迫付出可见代价保住核心底线，换来意外的破局契机。',
            'strands': ['fire', 'quest', 'constellation', 'fire', 'quest'],
            'decision': f'{lead_char}在保利益还是保人/底线之间做出痛苦取舍，促使人物弧光跃迁。',
            'ripples': {
                'characters': [f'{lead_char}承受明确损失/伤势，人物信念完成一次升级'],
                'relationships': [f'{lead_char}与核心羁绊角色信任加深或产生裂痕'],
                'world': ['世界规则的硬性代价被读者亲眼见证，体系可信度大增'],
                'promises': [f'旧线索「{top_promise}」意外转向更高层级谜团'],
            },
            'risks': ['代价若缺乏清晰的补偿/希望锚点，可能令偏好无敌爽文的读者流失'],
            'uncertainties': ['新引入的意外变量需在 8–12 章内给出交代，避免新增悬空伏笔'],
            'intent_rationale': '适合卷末高潮前夕或人物弧光转折期，显著提升长篇厚重感与人物立体度。',
        },
    ]

    result: list[dict[str, Any]] = []
    for idx in range(branch_count):
        tpl = archetypes[idx % len(archetypes)]
        beats = []
        for step in range(1, horizon + 1):
            strand = tpl['strands'][(step - 1) % len(tpl['strands'])]
            beats.append({
                'chapter': base_ch + step,
                'dominant_strand': strand,
                'summary': (
                    f'第{base_ch + step}章（{strand}）：'
                    + (f'围绕「{divergence}」抛出直接后果与第一轮博弈' if step == 1 else
                       f'承接前章后果，兑现阶段性回报并引出新一层悬念' if step == horizon else
                       f'推进第 {step} 步因果连锁，校正人物关系与信息差')
                ),
            })
        result.append({
            'branch_id': f'branch-{idx + 1}',
            'label': tpl['label'],
            'premise': tpl['premise'],
            'beats': beats,
            'character_decisions': [tpl['decision']],
            'projected_ripples': tpl['ripples'],
            'risks': tpl['risks'],
            'uncertainties': tpl['uncertainties'],
            'intent_rationale': tpl['intent_rationale'],
        })
    return result


def _parse_forecast_json(raw_text: str, branch_count: int) -> list[dict[str, Any]]:
    text = (raw_text or '').strip()
    try:
        data = json.loads(text)
    except ValueError:
        m = _JSON_FENCE_RE.search(text)
        if m:
            data = json.loads(m.group(1))
        else:
            s, e = text.find('{'), text.rfind('}')
            if s >= 0 and e > s:
                data = json.loads(text[s:e + 1])
            else:
                raise ValueError('剧情推演模型输出不是合法 JSON') from None
    branches = data.get('branches') if isinstance(data, dict) else None
    if not isinstance(branches, list) or not branches:
        raise ValueError('剧情推演 JSON 缺少 branches 列表')
    normalized: list[dict[str, Any]] = []
    for idx, br in enumerate(branches[:branch_count], 1):
        if not isinstance(br, dict) or not str(br.get('premise') or '').strip():
            raise ValueError(f'推演分支 #{idx} 缺少 premise')
        beats = br.get('beats') if isinstance(br.get('beats'), list) else []
        ripples = br.get('projected_ripples') if isinstance(br.get('projected_ripples'), dict) else {}
        normalized.append({
            'branch_id': f'branch-{idx}',
            'label': str(br.get('label') or f'推演方案 {idx}').strip()[:60],
            'premise': str(br.get('premise') or '').strip(),
            'beats': beats[:12],
            'character_decisions': [str(x) for x in (br.get('character_decisions') or ()) if str(x).strip()][:6],
            'projected_ripples': {
                'characters': [str(x) for x in (ripples.get('characters') or ()) if str(x).strip()][:5],
                'relationships': [str(x) for x in (ripples.get('relationships') or ()) if str(x).strip()][:5],
                'world': [str(x) for x in (ripples.get('world') or ()) if str(x).strip()][:5],
                'promises': [str(x) for x in (ripples.get('promises') or ()) if str(x).strip()][:5],
            },
            'risks': [str(x) for x in (br.get('risks') or ()) if str(x).strip()][:5],
            'uncertainties': [str(x) for x in (br.get('uncertainties') or ()) if str(x).strip()][:5],
            'intent_rationale': str(br.get('intent_rationale') or '').strip(),
        })
    return normalized


def create_narrative_forecast(
    store: Store,
    *,
    divergence: str,
    branch_id: str = 'main',
    branch_count: int = DEFAULT_BRANCH_COUNT,
    horizon: int = DEFAULT_HORIZON,
    provider: LLMProvider | None = None,
    model: str = '',
    params: dict[str, Any] | None = None,
    offline_preview: bool = False,
    target_words: int | None = None,
) -> dict[str, Any]:
    """Generate and persist a strictly non-canonical multi-branch narrative forecast."""
    clean_div = str(divergence or '').strip()
    if not clean_div:
        raise ValueError('请描述希望推演的关键剧情分歧点（divergence）')
    b_count = max(2, min(5, int(branch_count or DEFAULT_BRANCH_COUNT)))
    hor = max(1, min(10, int(horizon or DEFAULT_HORIZON)))

    ctx = build_forecast_context(store, branch_id=branch_id, target_words=target_words)
    used_mode = 'offline'
    if provider is not None and not offline_preview:
        sys_prompt = (
            '你是长篇小说剧情沙盘推演顾问。基于当前正史状态、连载健康盘面与人物底色，'
            f'围绕指定剧情分歧点，推演 {b_count} 条彼此截然不同、各自延伸未来 {hor} 章的候选走向。'
            '本推演为非正史沙盘，严禁捏造已违背现有世界规则的设定。'
            '只输出严格 JSON：{"branches":[{"label":"方案名","premise":"核心走法",'
            '"beats":[{"chapter":章号,"dominant_strand":"quest|fire|constellation","summary":"本章节拍"}],'
            '"character_decisions":["关键角色抉择及动因"],'
            '"projected_ripples":{"characters":[],"relationships":[],"world":[],"promises":[]},'
            '"risks":["潜在风险"],"uncertainties":["待解不确定项"],"intent_rationale":"适合何种连载意图"}]}。'
        )
        user_payload = {
            'divergence': clean_div,
            'base_chapter': ctx['base_chapter'],
            'horizon': hor,
            'branch_count': b_count,
            'characters': ctx['characters'],
            'world_rules': ctx['world_rules'],
            'active_promises': ctx['active_promises'],
            'serial_health_status': ctx['serial_health_status'],
            'next_chapter_corrections': ctx['next_chapter_corrections'],
        }
        live = provider.name != 'fake'
        gen = send_model(
            provider,
            [{'role': 'system', 'content': sys_prompt}, {'role': 'user', 'content': canonical(user_payload)}],
            model or 'forecast',
            dict(params or {}),
            allow_continuation=False,
            max_empty_retries=(2 if live else 0),
        )
        if gen.finish_reason != 'complete' or not gen.text.strip():
            raise ValueError(f'剧情沙盘推演调用失败（{gen.finish_reason}）')
        branches = _parse_forecast_json(gen.text, b_count)
        used_mode = 'model'
    else:
        branches = _offline_forecast_branches(ctx, clean_div, b_count, hor)

    fid = f'fc-{uuid4().hex[:10]}'
    ts = now()
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        store.connection.execute(
            '''INSERT INTO narrative_forecasts(
                id, branch_id, base_revision, base_chapter, divergence, horizon,
                context_sha256, status, branches_json, selected_branch_id,
                selected_plan_json, forked_branch_id, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (
                fid, branch_id, ctx['base_revision'], ctx['base_chapter'], clean_div, hor,
                ctx['context_sha256'], 'active', json.dumps(branches, ensure_ascii=False),
                None, '{}', None, ts, ts,
            ),
        )
    return {
        'id': fid,
        'branch_id': branch_id,
        'base_revision': ctx['base_revision'],
        'base_chapter': ctx['base_chapter'],
        'divergence': clean_div,
        'horizon': hor,
        'context_sha256': ctx['context_sha256'],
        'status': 'active',
        'stale': False,
        'mode': used_mode,
        'branches': branches,
        'selected_branch_id': None,
        'selected_plan': {},
        'forked_branch_id': None,
        'created_at': ts,
        'updated_at': ts,
    }


def _row_to_forecast(store: Store, row: Any, *, current_sha_cache: dict[str, str] | None = None) -> dict[str, Any]:
    b_id = row['branch_id']
    cache = current_sha_cache if current_sha_cache is not None else {}
    if b_id not in cache:
        try:
            cache[b_id] = build_forecast_context(store, branch_id=b_id)['context_sha256']
        except Exception:
            cache[b_id] = row['context_sha256']
    stale = cache[b_id] != row['context_sha256']
    status = row['status']
    if stale and status == 'active':
        status = 'stale'
        try:
            with store.connection:
                store.connection.execute(
                    "UPDATE narrative_forecasts SET status='stale', updated_at=? WHERE id=? AND status='active'",
                    (now(), row['id']),
                )
        except Exception:
            pass
    return {
        'id': row['id'],
        'branch_id': b_id,
        'base_revision': row['base_revision'],
        'base_chapter': row['base_chapter'],
        'divergence': row['divergence'],
        'horizon': row['horizon'],
        'context_sha256': row['context_sha256'],
        'status': status,
        'stale': stale or status == 'stale',
        'branches': json.loads(row['branches_json']),
        'selected_branch_id': row['selected_branch_id'],
        'selected_plan': json.loads(row['selected_plan_json'] or '{}'),
        'forked_branch_id': row['forked_branch_id'],
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
    }


def list_narrative_forecasts(store: Store, *, branch_id: str | None = None, limit: int = 12) -> list[dict[str, Any]]:
    if branch_id:
        rows = store.connection.execute(
            'SELECT * FROM narrative_forecasts WHERE branch_id=? ORDER BY created_at DESC LIMIT ?',
            (branch_id, max(1, int(limit))),
        ).fetchall()
    else:
        rows = store.connection.execute(
            'SELECT * FROM narrative_forecasts ORDER BY created_at DESC LIMIT ?',
            (max(1, int(limit)),),
        ).fetchall()
    cache: dict[str, str] = {}
    return [_row_to_forecast(store, r, current_sha_cache=cache) for r in rows]


def get_narrative_forecast(store: Store, forecast_id: str) -> dict[str, Any]:
    row = store.connection.execute('SELECT * FROM narrative_forecasts WHERE id=?', (forecast_id,)).fetchone()
    if row is None:
        raise ValueError(f'未找到剧情沙盘推演记录：{forecast_id}')
    return _row_to_forecast(store, row)


def select_forecast_branch(
    store: Store,
    forecast_id: str,
    branch_choice_id: str,
    *,
    mode: str = 'adopt_constraint',
    new_branch_id: str = '',
) -> dict[str, Any]:
    """Adopt a forecast branch as non-canonical planning guidance OR fork a real `story_branches` branch."""
    fc = get_narrative_forecast(store, forecast_id)
    chosen = next((b for b in fc['branches'] if b.get('branch_id') == branch_choice_id), None)
    if chosen is None:
        avail = ', '.join(str(b.get('branch_id')) for b in fc['branches'])
        raise ValueError(f'推演分支 {branch_choice_id} 不存在，可选：{avail}')

    plan_payload = {
        'forecast_id': fc['id'],
        'divergence': fc['divergence'],
        'branch_id': chosen['branch_id'],
        'label': chosen.get('label', ''),
        'premise': chosen.get('premise', ''),
        'beats': chosen.get('beats', []),
        'character_decisions': chosen.get('character_decisions', []),
        'projected_ripples': chosen.get('projected_ripples', {}),
        'risks': chosen.get('risks', []),
        'stale_at_selection': bool(fc['stale']),
        'selected_at': now(),
    }

    forked_id = fc.get('forked_branch_id')
    new_status = 'adopted'
    if mode == 'fork_branch':
        head = current_head(store, fc['branch_id'])
        target_name = str(new_branch_id or '').strip() or f'sandbox-{fc["id"][-6:]}-{chosen["branch_id"]}'
        fork_story(store, head, target_name)
        forked_id = target_name
        new_status = 'forked'
    elif mode != 'adopt_constraint':
        raise ValueError(f'不支持的推演采纳模式：{mode}')

    ts = now()
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        store.connection.execute(
            '''UPDATE narrative_forecasts
               SET status=?, selected_branch_id=?, selected_plan_json=?, forked_branch_id=?, updated_at=?
               WHERE id=?''',
            (new_status, chosen['branch_id'], json.dumps(plan_payload, ensure_ascii=False), forked_id, ts, fc['id']),
        )
    return get_narrative_forecast(store, fc['id'])


def active_adopted_forecast_constraint(store: Store, *, branch_id: str = 'main') -> dict[str, Any] | None:
    """Return the latest non-stale adopted forecast plan for automatic injection into upcoming planning."""
    rows = store.connection.execute(
        '''SELECT * FROM narrative_forecasts
           WHERE (branch_id=? OR forked_branch_id=?) AND status IN ('adopted','forked')
           ORDER BY updated_at DESC LIMIT 3''',
        (branch_id, branch_id),
    ).fetchall()
    cache: dict[str, str] = {}
    for r in rows:
        fc = _row_to_forecast(store, r, current_sha_cache=cache)
        if not fc['stale'] and fc.get('selected_plan'):
            return fc['selected_plan']
    return None
