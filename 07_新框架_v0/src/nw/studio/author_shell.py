"""Read-only Author Shell: Error-to-Action Catalog, Unified Glossary, and 3-Second Review Author View.

Design principle (Engineering Kernel + Author Shell):
  - NEVER weakens a single SQLite/POV/validation invariant in the kernel.
  - Translates raw internal error codes (`STALE_HEAD`, `CONTEXT_TOO_LARGE`, `OPEN_DESIGN_QUESTIONS`, ...)
    into plain author language: what happened, why it blocked, and the exact 1-click next action.
  - Compiles Lens 0 (0-token script gate) + Lens 1 (fact/state) + Lens 2 (craft/structure) +
    Lens 3 (blind stranger cold read, always non-blocking) into a 3-second verdict card.
"""
from __future__ import annotations

from typing import Any

MAX_TOP_ACTIONS = 3

# Author Glossary (maps engineering terms to plain Chinese author vocabulary)
AUTHOR_GLOSSARY: dict[str, str] = {
    'branch': '候选草稿分支',
    'main': '正式主线',
    'StateDelta': '本章状态变更记录',
    'delta': '状态变更记录',
    'InputManifest': '本场冻结写作依据',
    'CardRef': '设定卡片版本',
    'holder': '知情视角',
    'disclosure_order': '章节披露顺序',
    'story_order': '故事发生时间',
    'method_guidance': '本场写作技法要求',
    'craft_spec': '本书工艺基座',
    'override_ledger': '显式豁免记录',
    'rhythm_debt': '节奏债',
}

# Prefix-ordered error translation catalog: (prefix_or_substring, metadata)
_ERROR_CATALOG: tuple[tuple[str, dict[str, Any]], ...] = (
    ('STALE_HEAD', {
        'code': 'STALE_HEAD',
        'title': '当前分支进度已有更新',
        'summary': '在你刚才操作期间，本书当前分支已经保存了新的稿件或设定进度。',
        'impact': '为了防止旧页面覆盖新写好的内容，系统安全拦截了这次提交。',
        'action_label': '刷新制作台后重试',
        'action_hint': '请刷新当前页面同步最新进度，确认后再继续。',
        'overridable': False,
    }),
    ('STALE_PLAN_PARENT', {
        'code': 'STALE_PLAN_PARENT',
        'title': '上级大纲已更新，当前细化方案已过期',
        'summary': '你修改或重新批准了上级全书/卷纲，当前这份下级方案基于旧版生成。',
        'impact': '继续沿用旧方案会导致章节设定和上级大纲打架。',
        'action_label': '按最新上级大纲重建本级设计',
        'action_hint': '请重新发起本级设计，系统会自动对齐最新已批准的大纲。',
        'overridable': False,
    }),
    ('STALE_PLAN', {
        'code': 'STALE_PLAN',
        'title': '该场景对应的规划已被新版方案替代',
        'summary': '当前分支已经采用了更新的规划方案，这个旧场景位已退休。',
        'impact': '不能把旧方案下的草稿直接并入新版章节结构。',
        'action_label': '切换到新版章节场景继续写作',
        'action_hint': '在左侧章节列表中选择最新生效的场景继续制作。',
        'overridable': False,
    }),
    ('STALE_MATERIAL', {
        'code': 'STALE_MATERIAL',
        'title': '本场已绑定的写作资料发生了变更',
        'summary': '在审稿或写作期间，本场引用的方法卡或设计资料被修改了。',
        'impact': '继续使用旧草稿会导致正文与最新确认的设计要求不一致。',
        'action_label': '重新生成本场写作任务',
        'action_hint': '请重新发起本场写作，让系统冻结最新资料版本。',
        'overridable': False,
    }),
    ('STALE_DRAFT', {
        'code': 'STALE_DRAFT',
        'title': '草稿版本已变化',
        'summary': '正在提取状态或审稿的草稿已不是最新保存的版本。',
        'impact': '必须针对最新稿件重新核验，避免状态账本和正文脱节。',
        'action_label': '针对最新草稿重新审稿',
        'action_hint': '点击重新执行独立审稿与状态提取。',
        'overridable': False,
    }),
    ('OPEN_DESIGN_QUESTIONS', {
        'code': 'OPEN_DESIGN_QUESTIONS',
        'title': '还有未敲定的设定待补齐',
        'summary': '本场依赖的核心设定卡里还留着“待定/未知”问题未填写。',
        'impact': '带着空洞设定直接开写，AI 极易临场胡编并与后文冲突。',
        'action_label': '补齐设定卡中的待定项',
        'action_hint': '打开对应设定卡把待定问题填清并保存，即可继续起草。',
        'overridable': False,
    }),
    ('NUMERIC_LEDGER_MISMATCH', {
        'code': 'NUMERIC_LEDGER_MISMATCH',
        'title': '数值资源双边平账失败',
        'summary': '本章正文中资源的期初数值、增减消耗与期末剩余不匹配（期初 + 增减 ≠ 期末）。',
        'impact': '带错账入库会导致后续章节货币/灵石/寿元/人数彻底紊乱。',
        'action_label': '核对并修平正文与状态数值',
        'action_hint': '检查正文中的消耗/收益数字，修正后重新执行状态提取即可。',
        'overridable': False,
    }),
    ('NUMERIC_LEDGER_NEGATIVE', {
        'code': 'NUMERIC_LEDGER_NEGATIVE',
        'title': '数值资源跌破零下限',
        'summary': '物理资源（如灵石、金币、寿元、人数等）结算后出现负数。',
        'impact': '违反基础物理与世界规则设定。',
        'action_label': '修正消耗量或补充透支设定',
        'action_hint': '调整正文消耗数值或明确交代借贷/透支机制后重试。',
        'overridable': False,
    }),
    ('PROMISE_LIFECYCLE', {
        'code': 'PROMISE_LIFECYCLE',
        'title': '伏笔/承诺生命周期流转不合法',
        'summary': '尝试废止已兑现的历史伏笔，或废止承诺时未给出明确依据说明。',
        'impact': '已兑现的伏笔属于不可篡改的既成历史；废弃旧线必须留存审计依据。',
        'action_label': '补充废止说明或核对伏笔状态',
        'action_hint': '只对未兑现伏笔登记 superseded，并写明大纲变更依据。',
        'overridable': False,
    }),
    ('MODEL_EMPTY_AFTER_THINK', {
        'code': 'MODEL_EMPTY_AFTER_THINK',
        'title': '模型仅输出了思考过程而无正文',
        'summary': '推理模型输出了 <think> 思考块但未生成实际正文内容，已自动重试仍为空。',
        'impact': '无法得到可审稿的正文或结构化结果。',
        'action_label': '调高输出上限或稍后重试',
        'action_hint': '在模型设置中调大 max_tokens（给思考与正文留足空间）或切换非思考模型后重试。',
        'overridable': False,
    }),
    ('CONTEXT_TOO_LARGE', {
        'code': 'CONTEXT_TOO_LARGE',
        'title': '本场上下文超出预算上限',
        'summary': '本场关联的设定、前文或审稿资料总量超过了当前单次调用字数上限。',
        'impact': '强行发送会被模型截断，导致遗忘关键约束。',
        'action_label': '拆分本场或调高调用预算',
        'action_hint': '建议将大场拆成两个自然小场，或在右上角预算设置中适当提高上下文字符上限。',
        'overridable': False,
    }),
    ('WORD_BUDGET', {
        'code': 'WORD_BUDGET',
        'title': '本场篇幅超出或不足约定字数区间',
        'summary': '当前草稿字数偏离了你在章场篇幅方案里确认的字数范围。',
        'impact': '单场严重超字或欠字会打乱整章与全卷的节奏配比。',
        'action_label': '按字数提示局部扩写/精简，或调整篇幅方案',
        'action_hint': '可根据审稿反馈补足场景展开，或在“篇幅与节奏”面板调整本场预算。',
        'overridable': True,
    }),
    ('HARD_FACT_FINDINGS', {
        'code': 'HARD_FACT_FINDINGS',
        'title': '发现事实/时间线/视角硬冲突',
        'summary': '状态核验发现正文与已确认的世界规则、时间线、人物生死或视角知情范围矛盾。',
        'impact': '硬事实冲突会污染后续几百章的故事记忆，不可直接豁免放行。',
        'action_label': '按事实冲突清单定点修改正文',
        'action_hint': '查看下方的事实镜头冲突明细，修改矛盾处后重新核验。',
        'overridable': False,
    }),
    ('MATERIAL_PRECONDITION', {
        'code': 'MATERIAL_PRECONDITION',
        'title': '前置章节或前置条件尚未就绪',
        'summary': '本场依赖的上一章正文或前置事件尚未完成并接受入库。',
        'impact': '缺少前文实证依据时，跨章承接与状态校验无法准确执行。',
        'action_label': '先完成并接受上一章正文',
        'action_hint': '先回到上一章完成审稿并点击接受入库，再继续本场。',
        'overridable': False,
    }),
    ('MATERIAL_EVIDENCE', {
        'code': 'MATERIAL_EVIDENCE',
        'title': '本场必达演出点尚未全部过审',
        'summary': '自动修订已达上限，但本场绑定的核心演出或披露检查仍未全部通过。',
        'impact': '直接入库会导致规划好的关键伏笔、动作或信息落点遗漏。',
        'action_label': '手改补足未通过的演出点后重新审稿',
        'action_hint': '对照审稿意见里的未通过条目手动补全几句关键细节，再点独立审稿。',
        'overridable': False,
    }),
    ('MISSING_MANDATORY_INPUT', {
        'code': 'MISSING_MANDATORY_INPUT',
        'title': '缺少本场必需的人物或设定卡',
        'summary': '本场引用的人物、禁忌或上游设定卡片在当前视角或分支下不可用。',
        'impact': '缺核心卡片开写会导致人设漂移或违背全书禁忌。',
        'action_label': '检查并批准缺失的设定卡',
        'action_hint': '在卡片列表中确认本场出场人物和核心禁忌卡均已批准生效。',
        'overridable': False,
    }),
    ('CHAPTER_OUTLINE_REQUIRED', {
        'code': 'CHAPTER_OUTLINE_REQUIRED',
        'title': '尚未确认本章章纲',
        'summary': '请先确认本章的章纲骨架，再拆解具体场景设计。',
        'impact': '跳过章纲直接写场景容易偏离本卷主线和节奏。',
        'action_label': '先审核并确认章纲',
        'action_hint': '在待确认门禁中审阅并批准本章章纲。',
        'overridable': False,
    }),
    ('CONFIG_CHANGED', {
        'code': 'CONFIG_CHANGED',
        'title': '模型配置在任务中途发生了变化',
        'summary': '当前正在继续的任务与创建时冻结的模型路由或参数不一致。',
        'impact': '同一写作任务中途切换模型容易造成上下文口径不一致。',
        'action_label': '恢复原模型设置，或取消后用新模型重开任务',
        'action_hint': '可在“模型与配置”切回原模型，或取消当前旧任务后重新启动。',
        'overridable': False,
    }),
    ('PROVIDER_OUTCOME_UNKNOWN', {
        'code': 'PROVIDER_OUTCOME_UNKNOWN',
        'title': '模型网络请求中断，尚未收到完整回复',
        'summary': '与模型接口的连接超时或中断，本次生成结果尚未落盘。',
        'impact': '已安全保留既有稿件和进度，不会丢失之前的内容。',
        'action_label': '检查网络后点击重试',
        'action_hint': '确认网络/代理通畅后直接点击“重试当前步骤”，系统会从断点续跑。',
        'overridable': False,
    }),
    ('CONTEXT_PROVIDER_REQUIRED', {
        'code': 'CONTEXT_PROVIDER_REQUIRED',
        'title': '本场尚未接入正式状态管理',
        'summary': '该场景还未绑定当前分支已批准的场景卡版本。',
        'impact': '脱离版本绑定无法保证视角隔离与长篇一致性。',
        'action_label': '先完成本卷/本章设计并批准场景卡',
        'action_hint': '在设计流程中批准本章方案后再进入写作。',
        'overridable': False,
    }),
    ('BUDGET_REQUIRED', {
        'code': 'BUDGET_REQUIRED',
        'title': '未设置本次写作调用预算',
        'summary': '为避免失控消耗，受控写作与审稿必须携带明确的调用次数和字数预算。',
        'impact': '系统已暂停发起模型调用以保护你的额度。',
        'action_label': '在制作台确认预算后重试',
        'action_hint': '打开预算设置保持默认或自定义上限后重试即可。',
        'overridable': False,
    }),
    ('PRE_VERBATIM_REPEAT', {
        'code': 'PRE_VERBATIM_REPEAT',
        'title': '检测到正文复读退化',
        'summary': '模型连续输出了完全相同的句子或段落。',
        'impact': '带复读退化的草稿不可进入审稿或入库。',
        'action_label': '删除复读句或重新生成本场',
        'action_hint': '手动删除重复行或点击重写本场，系统已自动阻断复读入库。',
        'overridable': False,
    }),
    ('PRE_MARKDOWN_BOLD_LEAK', {
        'code': 'PRE_MARKDOWN_BOLD_LEAK',
        'title': '正文混入 Markdown 加粗星号',
        'summary': '草稿中残留了 **加粗** 等 Markdown 格式符号。',
        'impact': '直接上架会在阅读器中裸露星号符号。',
        'action_label': '清除星号标记后重试',
        'action_hint': '删去正文中的 ** 标记，或在「上架体检」中一键清扫。',
        'overridable': False,
    }),
    ('PRE_CENSORED_PINYIN', {
        'code': 'PRE_CENSORED_PINYIN',
        'title': '正文残留敏感词拼音代写',
        'summary': '草稿中混入了“身ti/杀si/尸ti”等半中文半拼音谐音。',
        'impact': '严重破坏阅读沉浸感且易触发平台质量降权。',
        'action_label': '改回自然中文表达',
        'action_hint': '替换为自然中文或隐晦实写，或如确属刻意玩梗请登记签收豁免。',
        'overridable': True,
    }),
    ('PRE_OUTLINE_COPY', {
        'code': 'PRE_OUTLINE_COPY',
        'title': '正文疑似逐字抄写大纲/场景卡',
        'summary': '检测到正文与场景卡或节拍存在连续 16 字以上逐字重合。',
        'impact': '把大纲摘要直接贴进正文会失去现场展开与真实读感。',
        'action_label': '改写成现场动作、心理与对白',
        'action_hint': '核对标红片段并展开为真实场景；如属指定原话请在大纲标注「原话：」。',
        'overridable': True,
    }),
    ('PUBLISH_PREFLIGHT_BLOCKED', {
        'code': 'PUBLISH_PREFLIGHT_BLOCKED',
        'title': '平台发书上架合规体检未通过',
        'summary': '书名、简介、标签或章节正文存在平台硬性违规项（如超字、含禁用符号、乱码或未清理元信息）。',
        'impact': '直接提交到番茄/起点/七猫/晋江大概率会被驳回或触发签约风险。',
        'action_label': '按上架体检清单逐项修复',
        'action_hint': '打开「发书上架体检」抽屉查看标红项，使用一键标点退化清扫后重新校验。',
        'overridable': False,
    }),
    ('已有正文后的追加设计需先建立候选分支', {
        'code': 'CANDIDATE_BRANCH_REQUIRED',
        'title': '已有正式正文，追加设计需先开候选分支',
        'summary': '正式主线已经存在接受入库的正文，为防新设计意外破坏旧稿，系统要求先开候选分支。',
        'impact': '你的主线成稿受到保护，可在候选分支安全试改并复核后再一键合并。',
        'action_label': '点击「建立候选分支」',
        'action_hint': '打开右上角“候选分支”创建分支后，即可继续设计下一卷或修改设定。',
        'overridable': False,
    }),
)


def translate_error(raw_error: str | Exception) -> dict[str, Any]:
    """Translate any kernel error message into a structured Author Shell card."""
    text = str(raw_error or '').strip()
    for needle, meta in _ERROR_CATALOG:
        if needle in text:
            return {
                **meta,
                'technical_detail': text,
            }
    return {
        'code': 'GENERAL_ERROR',
        'title': '操作暂时无法完成',
        'summary': text or '执行过程中遇到未预期的拦截。',
        'impact': '当前稿件和已保存数据保持完整，未被破坏。',
        'action_label': '按提示检查后重试',
        'action_hint': '如反复出现，可打开“项目体检 Doctor”排查具体原因。',
        'technical_detail': text,
        'overridable': False,
    }


def _priority_tuple(item: dict[str, Any]) -> tuple[int, int]:
    sev_rank = {'hard': 0, 'blocking': 0, 'review_required': 1, 'warning': 2, 'medium': 3, 'info': 4}
    ovr_rank = 0 if not item.get('overridable') else 1
    return (sev_rank.get(str(item.get('severity') or 'warning'), 3), ovr_rank)


def build_unified_review_view(
    *,
    pre_review: dict[str, Any] | None = None,
    review: dict[str, Any] | None = None,
    fact_findings: list[dict[str, Any]] | None = None,
    cold_read: dict[str, Any] | None = None,
    overrides: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the 3-second Author Review Verdict Card combining all 4 orthogonal lenses:
      - Lens 0: 0-Token Script Gate (`pre_review`)
      - Lens 1: Fact & State Lens (`fact_findings` + `review.core_changes`)
      - Lens 2: Craft & Structure Lens (`review.material_checks` / `length_feedback` / `chapter_break` / `notes`)
      - Lens 3: Blind Stranger Reader Lens (`cold_read` — ALWAYS non-blocking!)
    """
    active_override_codes = {
        str(row.get('constraint_code') or '')
        for row in (overrides or ())
        if isinstance(row, dict) and row.get('status', 'active') == 'active'
    }

    action_items: list[dict[str, Any]] = []

    # ── Lens 0: 0-Token Deterministic Script Gate ──
    l0_issues = list((pre_review or {}).get('issues') or ())
    l0_hard = 0
    l0_warn = 0
    for row in l0_issues:
        code = str(row.get('code') or 'PRE_CHECK')
        overridden = bool(row.get('overridable')) and code in active_override_codes
        sev = str(row.get('severity') or 'warning')
        if overridden:
            continue
        if sev == 'hard':
            l0_hard += 1
        else:
            l0_warn += 1
        action_items.append({
            'lens': 'script_gate',
            'lens_label': '机检闸门',
            'severity': 'hard' if sev == 'hard' else ('review_required' if sev == 'review_required' else 'warning'),
            'tier': str(row.get('tier') or ('blocking' if sev == 'hard' else 'advisory')),
            'overridable': bool(row.get('overridable')),
            'constraint_code': code,
            'title': str(row.get('message') or ''),
            'detail': str(row.get('quote') or ''),
            'location': str(row.get('location') or ''),
            'fix_hint': str(row.get('fix_hint') or ''),
        })

    # ── Lens 1: Fact & State Lens (Never overridable for hard findings!) ──
    findings = [f for f in (fact_findings or ()) if isinstance(f, dict)]
    l1_hard = 0
    l1_warn = 0
    for f in findings:
        sev = 'hard' if f.get('severity') == 'hard' else 'warning'
        if sev == 'hard':
            l1_hard += 1
        else:
            l1_warn += 1
        action_items.append({
            'lens': 'fact_lens',
            'lens_label': '事实与视角镜头',
            'severity': sev,
            'overridable': False,
            'constraint_code': str(f.get('code') or 'FACT_FINDING'),
            'title': str(f.get('explanation') or f.get('code') or '事实一致性冲突'),
            'detail': '',
            'location': '',
            'fix_hint': '核对已批准设定、时间线与视角知情范围，修正矛盾后重新提取状态。',
        })
    core_changes = list((review or {}).get('core_changes') or ())
    for cc in core_changes[:3]:
        l1_hard += 1
        action_items.append({
            'lens': 'fact_lens',
            'lens_label': '事实与视角镜头',
            'severity': 'hard',
            'overridable': False,
            'constraint_code': 'CORE_CHANGE',
            'title': f'涉及核心设定变动：{cc}',
            'detail': '',
            'location': '',
            'fix_hint': '此类变更会影响后续全书主线，请人工确认是否批准变更或改回原设定。',
        })

    # ── Lens 2: Craft & Structure Lens ──
    l2_hard = 0
    l2_warn = 0
    rec = (review or {}).get('recommendation')
    length_fb = list((review or {}).get('length_feedback') or ())
    for msg in length_fb:
        code = 'WORD_BUDGET'
        if code in active_override_codes:
            continue
        l2_warn += 1
        action_items.append({
            'lens': 'craft_lens',
            'lens_label': '结构与工艺镜头',
            'severity': 'warning',
            'overridable': True,
            'constraint_code': code,
            'title': str(msg),
            'detail': '',
            'location': '',
            'fix_hint': '局部扩充关键细节/压实废笔，或对本次轻微浮动做显式豁免。',
        })
    mat_checks = [c for c in ((review or {}).get('material_checks') or ()) if isinstance(c, dict)]
    failed_mats = [c for c in mat_checks if c.get('status') not in ('pass', 'ok', None)]
    for mc in failed_mats[:4]:
        l2_hard += 1
        action_items.append({
            'lens': 'craft_lens',
            'lens_label': '结构与工艺镜头',
            'severity': 'hard',
            'overridable': False,
            'constraint_code': str(mc.get('id') or 'MATERIAL_CHECK'),
            'title': f"本场演出点未达标：{mc.get('reason') or mc.get('id')}",
            'detail': '',
            'location': '',
            'fix_hint': '按场景卡与绑定演出要求补齐具体动作或披露细节。',
        })
    if rec == 'revise' and not failed_mats and not length_fb:
        notes = str((review or {}).get('notes') or '独立审稿建议修订后再接受入库。').strip()
        if 'SOFT_REVIEW_REVISE' not in active_override_codes:
            l2_warn += 1
            action_items.append({
                'lens': 'craft_lens',
                'lens_label': '结构与工艺镜头',
                'severity': 'warning',
                'overridable': True,
                'constraint_code': 'SOFT_REVIEW_REVISE',
                'title': notes[:180],
                'detail': '',
                'location': '',
                'fix_hint': '按审稿意见微调表达，或若为作者刻意艺术处理可登记显式豁免。',
            })

    # ── Lens 3: Blind Stranger Reader Lens (ALWAYS non-blocking!) ──
    l3_signals = 0
    latest_cr = (cold_read or {}).get('latest_for_draft') if isinstance(cold_read, dict) else None
    cr_parsed = (latest_cr or {}).get('parsed') if isinstance(latest_cr, dict) else None
    reader_summary = ''
    want_next = 'unknown'
    if isinstance(cr_parsed, dict):
        reader_summary = str(cr_parsed.get('verdict_summary') or '').strip()
        want_next = str((cr_parsed.get('keep_reading') or {}).get('want_next') or 'unknown')
        for sk in (cr_parsed.get('skip_zones') or ())[:2]:
            l3_signals += 1
            action_items.append({
                'lens': 'reader_lens',
                'lens_label': '陌生读者冷读',
                'severity': 'info',
                'overridable': True,
                'constraint_code': 'COLD_READ_SKIP_ZONE',
                'title': f"读者此处想划走：{sk.get('reason') or '信息密度偏低'}",
                'detail': str(sk.get('quote') or ''),
                'location': str(sk.get('location') or ''),
                'fix_hint': '压缩铺垫或提前抛出冲突与具体动作（冷读仅供参考，永不阻断）。',
            })
        for cf in (cr_parsed.get('confusion_or_mismatch') or ())[:2]:
            l3_signals += 1
            action_items.append({
                'lens': 'reader_lens',
                'lens_label': '陌生读者冷读',
                'severity': 'info',
                'overridable': True,
                'constraint_code': 'COLD_READ_CONFUSION',
                'title': f"陌生读者误读风险：{cf.get('misread_risk') or '衔接不清晰'}",
                'detail': str(cf.get('quote') or ''),
                'location': str(cf.get('location') or ''),
                'fix_hint': '补一句自然交代让没看过大纲的读者也能一眼看懂。',
            })

    sorted_actions = sorted(action_items, key=_priority_tuple)
    total_hard = l0_hard + l1_hard + l2_hard
    total_warn = l0_warn + l1_warn + l2_warn

    if total_hard > 0:
        verdict, status = '⛔ 必须先改', 'must_fix'
    elif total_warn > 0:
        verdict, status = '⚠️ 建议改', 'suggest_fix'
    else:
        verdict, status = '✅ 可以继续', 'can_continue'

    top_actions = sorted_actions[:MAX_TOP_ACTIONS]
    if not top_actions and status == 'can_continue':
        top_actions = [{
            'lens': 'summary',
            'lens_label': '综合结论',
            'severity': 'info',
            'overridable': True,
            'constraint_code': 'ALL_CLEAR',
            'title': '机检、事实与工艺均未发现阻断项，可以继续下一步或接受入库。',
            'detail': reader_summary,
            'location': '',
            'fix_hint': '',
        }]

    return {
        'verdict': verdict,
        'status': status,
        'hard_count': total_hard,
        'warning_count': total_warn,
        'overridden_count': len(active_override_codes),
        'top_actions': top_actions,
        'all_actions_count': len(sorted_actions),
        'lenses': {
            'script_gate': {
                'label': '机检闸门（0 Token）',
                'status': 'fail' if l0_hard else ('warn' if l0_warn else 'pass'),
                'hard': l0_hard,
                'warnings': l0_warn,
                'ran': pre_review is not None,
            },
            'fact_lens': {
                'label': '事实与视角镜头',
                'status': 'fail' if l1_hard else ('warn' if l1_warn else 'pass'),
                'hard': l1_hard,
                'warnings': l1_warn,
                'ran': bool(fact_findings is not None or review is not None),
            },
            'craft_lens': {
                'label': '结构与工艺镜头',
                'status': 'fail' if l2_hard else ('warn' if l2_warn else 'pass'),
                'hard': l2_hard,
                'warnings': l2_warn,
                'ran': review is not None,
            },
            'reader_lens': {
                'label': '陌生读者冷读（非阻断）',
                'status': 'warn' if (want_next == 'no' or l3_signals) else ('pass' if cr_parsed else 'not_run'),
                'want_next': want_next,
                'signals': l3_signals,
                'summary': reader_summary,
                'ran': cr_parsed is not None,
            },
        },
    }
