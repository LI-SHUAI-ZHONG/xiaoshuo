import {esc, readable} from '../ui.js';

const scopes = {book:'全书', volume:'卷纲', chapter:'章纲', scene:'场景', replan:'改案', world:'世界卡', character:'人物卡', plot:'剧情卡', promise:'伏笔/承诺卡'};
const fields = {
  world:{rule:'世界规则', limits:'适用限制与代价', visibility:'可见范围'},
  character:{role:'表面身份/定位', want:'核心欲望', goal:'核心目标', scene_function:'本轮剧情职责', independent_goal:'角色独立目标',
    creation_reason:'建卡依据', traits:'特征与习惯', background:'关键背景经历', behavior:'立场与压力反应', voice:'声线与口吻',
    capabilities:'能力与边界', boundaries:'知情与隐私边界', limits:'局限与代价', visibility:'可见范围', casting:'出场与身份配置'},
  plot:{premise:'剧情前提', conflict:'核心冲突', choice:'关键选择', cost:'代价', consequence:'后果', ending_direction:'收束方向'},
  promise:{plant:'埋设方式', expectation:'读者预期', payoff:'回收安排'},
  volume:{goal:'阶段目标', turn:'卷末转折', ending_direction:'卷末交接'},
  chapter:{goal:'本章目标', consequence:'章末变化', reader_promise:'读者期待'},
  scene:{function:'本场职责', goal:'本场目标', location:'地点', story_time:'故事时间',
    pov:'视角人物', characters:'在场人物', character_goals:'在场人物目标',
    entering_state:'进入状态', conflict:'本场冲突', choice:'人物选择', planned_result:'本场结果',
    allowed_disclosure:'可披露的信息'},
};
const eventFields = {goal:'事件目标', setting:'发生处境', obstacle:'阻碍', completion_condition:'完成条件'};

function definitionList(data, labels) {
  const entries = Object.entries(labels).filter(([key]) => data[key] != null && data[key] !== '' && (!Array.isArray(data[key]) || data[key].length));
  const renderVal = value => typeof value === 'string'
    ? esc(value)
    : Array.isArray(value) && value.every(item => typeof item === 'string')
      ? esc(value.join('、'))
      : readable(value);
  return entries.length ? `<dl class="selection-summary">${entries.map(([key, label]) =>
    `<dt>${label}</dt><dd>${renderVal(data[key])}</dd>`).join('')}</dl>` : '';
}

export function scopeName(scope) {
  return scopes[scope] || '';
}

export function approvedParent(parent) {
  const scope = scopeName(parent?.scope);
  if (!scope || !parent.title) return '';
  const number = parent.artifact?.ref?.version ?? parent.version ?? parent.root?.version;
  const version = Number.isInteger(number) && number > 0 ? ` · 第 ${number} 版` : '';
  return `<section class="design-card"><h3>上一级已批准方案</h3>
    <p>${scope}${version}</p><strong>${esc(parent.title)}</strong>
    ${parent.artifact?.kind === 'volume' ? definitionList(parent.artifact.body || {}, fields.volume) : ''}</section>`;
}

function scopeArtifact(member) {
  const {kind, body} = member;
  const {title, name, ...other} = body;
  for (const key of Object.keys(fields[kind])) delete other[key];
  return `<section class="design-card">
    <p class="muted">${scopeName(kind)}</p><h3>${esc(title || name || member.key || scopeName(kind))}</h3>
    ${definitionList(body, fields[kind])}
    ${Object.keys(other).length ? `<details class="details"><summary>更多${scopeName(kind)}字段</summary>${readable(other)}</details>` : ''}
    </section>`;
}

export function approvedChapter(chapter) {
  if (!chapter) return '';
  const body = chapter.body || chapter.chapter?.body;
  if (!body?.title && !chapter.title) return '';
  return `<details class="details" open><summary>本章已批准章纲</summary>
    ${body ? scopeArtifact({kind:'chapter',body}) : `<p>${esc(chapter.title)}</p>`}</details>`;
}

export function chapterOutline(chapter, events = [], direction = {}) {
  if (!chapter?.body) return '';
  const choice = definitionList(direction, {conflict:'本章矛盾', choice:'人物选择', cost:'选择代价'});
  return scopeArtifact({kind:'chapter',body:chapter.body})
    + (choice ? `<section class="design-card"><h3>本章关键选择</h3>${choice}</section>` : '')
    + (events.length ? `<section><h3>本章计划推进的事件</h3>${events.map(event =>
      `<div class="design-card">${definitionList(event, eventFields)}</div>`).join('')}</section>` : '');
}

function methodApplicationsSection(apps = [], receipts = []) {
  const parts = [];
  if (Array.isArray(apps) && apps.length) {
    parts.push(`<section class="design-card"><h3>本步实际采用的拆解方法与产物落点（${apps.length}）</h3>${apps.map(app => `<div class="method-section">
      <p><strong>方法</strong>：<code>${esc(app.method_id)}</code></p>
      ${(app.operations || []).map(op => `<p><strong>操作（${esc(op.key)}）</strong>：${esc(op.explanation)}</p>`).join('')}
      ${(app.outputs || []).map(out => `<div><small class="muted">落点（${esc(out.key)}）</small><ul>${(out.placements || []).map(p => `<li><code>/${esc((p.path || []).join('/'))}</code>：${esc(typeof p.value === 'string' ? p.value : JSON.stringify(p.value))}</li>`).join('')}</ul>${(out.scene_guidance || []).length ? `<small class="muted">写审交接：${out.scene_guidance.map(g => `${esc(g.scene)} · ${esc(g.observable)}`).join('；')}</small>` : ''}</div>`).join('')}
    </div>`).join('')}</section>`);
  }
  if (Array.isArray(receipts) && receipts.length) {
    parts.push(`<section class="design-card"><h3>本步承接的上游方法交接回执（${receipts.length}）</h3>${receipts.map(r => `<div class="method-section">
      <p><strong>交接</strong>：<code>${esc(r.id)}</code></p>
      <p>${esc(r.operation)}</p>
      <ul>${(r.placements || []).map(p => `<li><code>/${esc((p.path || []).join('/'))}</code>：${esc(typeof p.value === 'string' ? p.value : JSON.stringify(p.value))}</li>`).join('')}</ul>
    </div>`).join('')}</section>`);
  }
  return parts.join('');
}

function worldStageExtras(rest, stage) {
  const parts = [];
  if (stage === 'world_design') {
    parts.push(`<section class="card stack" id="worldStageHandoffBanner" style="margin-bottom:14px">
      <div class="row spread wrap"><strong>世界规则与限制定稿 · 上下游职责贯通</strong><span class="tag blue">只立外部规则与边界</span></div>
      <p class="muted"><strong>承接上游</strong>：立项自动冻结的类型契约 + 全书方向设计需求 + 同类型世界规则方法 ｜ <strong>交付下游</strong>：人物定位与能力上限 → 势力与关系张力 → 主线大纲与矛盾 → 行动代价 → 场景可见性。</p>
    </section>`);
  }
  if (Array.isArray(rest.limitations) && rest.limitations.length) {
    parts.push(`<section class="design-card"><h3>世界硬限制与代价（${rest.limitations.length}）</h3><ul>${rest.limitations.map(item => `<li>${esc(typeof item === 'string' ? item : JSON.stringify(item))}</li>`).join('')}</ul></section>`);
    delete rest.limitations;
  }
  if (Array.isArray(rest.unknowns) && rest.unknowns.length) {
    parts.push(`<section class="design-card"><h3>待作者确认或刻意留白的世界边界（${rest.unknowns.length}）</h3><ul>${rest.unknowns.map(item => `<li>${esc(typeof item === 'string' ? item : JSON.stringify(item))}</li>`).join('')}</ul></section>`);
    delete rest.unknowns;
  }
  if (Array.isArray(rest.cast_demands) && rest.cast_demands.length) {
    parts.push(`<section class="design-card"><h3>交接给 04 人物设计的阵容需求（${rest.cast_demands.length}）</h3>${rest.cast_demands.map(d => `<div class="method-section">
      <p><strong>${esc(d.id || d.slot || '需求')}</strong>${d.reuse_actor ? ` · 建议复用 <code>${esc(d.reuse_actor)}</code>` : ''}</p>
      ${d.event ? `<p><strong>事件/情境</strong>：${esc(d.event)}</p>` : ''}
      ${d.obstacle ? `<p><strong>阻力</strong>：${esc(d.obstacle)}</p>` : ''}
      ${d.reason ? `<p class="muted">${esc(d.reason)}</p>` : ''}
    </div>`).join('')}</section>`);
    delete rest.cast_demands;
  }
  if (rest.world_method_gap && typeof rest.world_method_gap === 'object') {
    const gap = rest.world_method_gap;
    parts.push(`<section class="design-card"><h3>世界规则拆解方法缺口</h3>
      <p>${esc(gap.missing || '当前候选世界方法与本书需求不匹配，建议前往预存库补充同类型参考作品的世界规则拆解。')}</p>
      ${Array.isArray(gap.exclusions) && gap.exclusions.length ? `<ul>${gap.exclusions.map(e => `<li><code>${esc(e.method_id || '')}</code>：${esc(e.reason || '')}</li>`).join('')}</ul>` : ''}
    </section>`);
    delete rest.world_method_gap;
  }
  return parts.join('');
}

function characterAndRelationsStageExtras(rest, stage) {
  const parts = [];
  if (stage === 'character_design') {
    parts.push(`<section class="card stack" id="characterStageHandoffBanner" style="margin-bottom:14px">
      <div class="row spread wrap"><strong>04 人物动机与弧线 · 上下游职责贯通</strong><span class="tag blue">复用优先 · 暗身份隔离</span></div>
      <p class="muted"><strong>承接上游</strong>：03 世界制度/限制 + cast_demands + 同类型人物分布样本 ｜ <strong>交付下游</strong>：05 静态关系实体端点 → 06 剧情动力 → 08 行动能力门槛 → 09 场景入场披露 → 13 声线外化。</p>
    </section>`);
  }
  if (stage === 'static_relations') {
    parts.push(`<section class="card stack" id="staticRelationsStageHandoffBanner" style="margin-bottom:14px">
      <div class="row spread wrap"><strong>05 静态关系与张力 · 上下游职责贯通</strong><span class="tag blue">真实实体端点 · 独立配角网</span></div>
      <p class="muted"><strong>承接上游</strong>：03 世界阶层/势力/资源流 + 04 已确立人物实体 ｜ <strong>交付下游</strong>：06 剧情矛盾升级 → 07 事件候选 → 08 博弈不对称 → 09 场景知情与错位 → 10–11 状态变化与传播。</p>
    </section>`);
  }
  if (Array.isArray(rest.cast_assignments) && rest.cast_assignments.length) {
    parts.push(`<section class="design-card"><h3>阵容需求分派（${rest.cast_assignments.length}）</h3><ul>${rest.cast_assignments.map(a => `<li>需求 <code>${esc(a.demand || '')}</code> → 演员 <code>${esc(a.actor || '')}</code></li>`).join('')}</ul></section>`);
    delete rest.cast_assignments;
  }
  if (Array.isArray(rest.capabilities) && rest.capabilities.length) {
    parts.push(`<section class="design-card"><h3>人物能力清单与硬限制（${rest.capabilities.length}）</h3>${rest.capabilities.map(c => `<div class="method-section">
      <p><strong><code>${esc(c.entity || '')}</code></strong> <span class="tag ${c.can_act === false ? '' : 'green'}">${c.can_act === false ? '当前受限' : '可行动'}</span></p>
      ${Array.isArray(c.abilities) && c.abilities.length ? `<p><strong>能力</strong>：${esc(c.abilities.join('、'))}</p>` : ''}
      ${c.basis ? `<p><strong>依据</strong>：${esc(c.basis)}</p>` : ''}
      ${Array.isArray(c.limits) && c.limits.length ? `<p class="muted"><strong>限制</strong>：${esc(c.limits.join('；'))}</p>` : ''}
    </div>`).join('')}</section>`);
    delete rest.capabilities;
  }
  if (Array.isArray(rest.states) && rest.states.length) {
    parts.push(`<section class="design-card"><h3>人物初始候选状态（${rest.states.length}）</h3>${rest.states.map(s => `<div class="method-section">
      <p><strong><code>${esc(s.entity || '')}</code></strong>${s.status ? ` <span class="tag">${esc(s.status)}</span>` : ''}</p>
      ${s.state ? readable(s.state) : ''}
    </div>`).join('')}</section>`);
    delete rest.states;
  }
  if (Array.isArray(rest.relations) && rest.relations.length) {
    parts.push(`<section class="design-card"><h3>静态关系网络与张力（${rest.relations.length} 条）</h3>${rest.relations.map(r => `<div class="method-section">
      <p><strong><code>${esc(r.source || '')}</code> → <code>${esc(r.target || '')}</code></strong> · <span class="tag blue">${esc(r.relation || '')}</span>${r.id ? ` <small class="faint">${esc(r.id)}</small>` : ''}</p>
      ${r.condition ? `<p class="muted"><strong>成立条件/依据</strong>：${esc(r.condition)}</p>` : ''}
    </div>`).join('')}</section>`);
    delete rest.relations;
  }
  if (Array.isArray(rest.requirements) && rest.requirements.length) {
    parts.push(`<section class="design-card"><h3>交接给下游的关系设计约束（${rest.requirements.length} 条）</h3>${rest.requirements.map(req => `<div class="method-section">
      <p><strong>目标步骤</strong>：<code>${esc(req.target_stage || '')}</code>${req.source_id ? ` · 来源 <code>${esc(req.source_id)}</code>` : ''}</p>
      <p>${esc(req.constraint || '')}</p>
      ${Array.isArray(req.project_refs) && req.project_refs.length ? `<small class="muted">关联项目引用：${esc(req.project_refs.join('、'))}</small>` : ''}
    </div>`).join('')}</section>`);
    delete rest.requirements;
  }
  return parts.join('');
}

function plotAndEventStageExtras(rest, stage) {
  const parts = [];
  if (stage === 'plot_design') {
    parts.push(`<section class="card stack" id="plotStageHandoffBanner" style="margin-bottom:14px">
      <div class="row spread wrap"><strong>故事大纲、人物弧光与卷章任务切分</strong><span class="tag blue">主支线 · 开篇承诺 · 人物弧 · 逐章切分</span></div>
      <p class="muted"><strong>承接上游</strong>：立项类型契约 + 世界硬规则 + 核心人物与关系网 + 篇幅计划 ｜ <strong>交付下游</strong>：全书交付开篇黄金三章/剧情段/人物弧 → 卷纲交付逐章任务切分表 → 章纲交付事件节点与场景节拍。</p>
    </section>`);
  }
  if (rest.opening_plan && typeof rest.opening_plan === 'object') {
    const op = rest.opening_plan;
    parts.push(`<section class="design-card" id="openingPlanCard"><h3>开篇抢跑与黄金三章设计</h3>
      ${definitionList(op, {hook_moment:'开篇切入瞬间', first_chapter_promise:'第一章核心承诺', reader_expectation:'前三章追更期待'})}
      ${Array.isArray(op.golden_three_beats) && op.golden_three_beats.length ? `<div style="margin-top:8px"><small class="muted">黄金三章节拍</small><ol>${op.golden_three_beats.map(b => `<li>${esc(b)}</li>`).join('')}</ol></div>` : ''}
    </section>`);
    delete rest.opening_plan;
  }
  if (Array.isArray(rest.character_arcs) && rest.character_arcs.length) {
    parts.push(`<section class="design-card" id="characterArcsCard"><h3>关键人物弧光变化链（${rest.character_arcs.length} 条）</h3>${rest.character_arcs.map(arc => `<div class="method-section">
      <p><strong>人物 <code>${esc(arc.character || '')}</code></strong>${arc.target_span ? ` · <span class="tag blue">${esc(arc.target_span)}</span>` : ''}</p>
      ${definitionList(arc, {start_state:'原状态与盲点', trigger_event:'触发事件', choice:'自主抉择', cost:'付出代价', new_state:'变化后新状态'})}
    </div>`).join('')}</section>`);
    delete rest.character_arcs;
  }
  if (Array.isArray(rest.story_segments) && rest.story_segments.length) {
    parts.push(`<section class="design-card" id="storySegmentsCard"><h3>全书可拆分因果剧情段（${rest.story_segments.length} 段）</h3>${rest.story_segments.map((seg, idx) => `<div class="method-section">
      <p><strong>第 ${idx + 1} 段 · ${esc(seg.title || seg.id || '')}</strong> <small class="faint">${esc(seg.id || '')}</small></p>
      ${definitionList(seg, {entry_condition:'进入局面', core_events:'核心事件', turning_choice:'关键转折抉择', ending_state:'段末新局面', next_driver:'推动下一段的原因'})}
    </div>`).join('')}</section>`);
    delete rest.story_segments;
  }
  if (Array.isArray(rest.chapter_splits) && rest.chapter_splits.length) {
    parts.push(`<section class="design-card" id="chapterSplitsCard"><h3>本卷逐章任务切分与交接表（${rest.chapter_splits.length} 章）</h3>${rest.chapter_splits.map(ch => `<div class="method-section">
      <p><strong>第 ${esc(ch.chapter_index ?? '')} 章 · ${esc(ch.title || '未命名章节')}</strong></p>
      ${definitionList(ch, {mission:'本章核心剧情任务', entering_state:'承接的进入局面', key_turn:'本章关键转折', ending_change:'章末实际变化', handoff_to_next:'留给下一章的问题/钩子', hook_or_foreshadow:'钩子或伏笔安排'})}
    </div>`).join('')}</section>`);
    delete rest.chapter_splits;
  }
  if (stage === 'event_design') {
    parts.push(`<section class="card stack" id="eventStageHandoffBanner" style="margin-bottom:14px">
      <div class="row spread wrap"><strong>07 事件链与候选分支 · 上下游职责贯通</strong><span class="tag blue">前驱完成门 · 条件预案</span></div>
      <p class="muted"><strong>承接上游</strong>：06 event_nodes 及 completion_condition + 03/05 自动运转与势力互动 ｜ <strong>交付下游</strong>：08 行动博弈 → 09 显式选中入场（selected_events），未触发候选绝不冒充既成事实。</p>
    </section>`);
  }
  if (Array.isArray(rest.directions) && rest.directions.length) {
    parts.push(`<section class="design-card"><h3>剧情方向（${rest.directions.length}）</h3>${rest.directions.map((d, i) => `<div class="method-section">
      <h4>${esc(d.title || `方向 ${i + 1}`)}</h4>
      ${definitionList(d, {protagonist_want:'主角欲望', conflict:'核心冲突', resistance:'主要阻力', choice:'关键抉择', cost:'不可逆代价', consequence:'后果', reader_promise:'读者承诺', ending_direction:'收束方向'})}
    </div>`).join('')}</section>`);
    delete rest.directions;
  }
  if (Array.isArray(rest.event_nodes) && rest.event_nodes.length) {
    parts.push(`<section class="design-card"><h3>计划事件节点 · 交付 07 完成门（${rest.event_nodes.length}）</h3>${rest.event_nodes.map(ev => `<div class="method-section">
      <p><strong><code>${esc(ev.id || '')}</code></strong>${Array.isArray(ev.actors) && ev.actors.length ? ` · 参与者：${esc(ev.actors.join('、'))}` : ''}${ev.status ? ` <span class="tag">${esc(ev.status)}</span>` : ''}</p>
      ${definitionList(ev, {goal:'事件目标', setting:'处境', obstacle:'阻碍', completion_condition:'完成条件（07 完成门）'})}
    </div>`).join('')}</section>`);
    delete rest.event_nodes;
  }
  if (Array.isArray(rest.promise_plan) && rest.promise_plan.length) {
    parts.push(`<section class="design-card"><h3>伏笔与承诺窗口计划（${rest.promise_plan.length}）</h3>${rest.promise_plan.map(p => `<div class="method-section">
      <p><strong><code>${esc(p.promise || p.id || '')}</code></strong> · 埋设章：${p.plant_chapter != null ? `第 ${esc(p.plant_chapter)} 章` : '待定'} · 回收章：${p.payoff_chapter != null ? `第 ${esc(p.payoff_chapter)} 章` : '远期待定（null）'}${p.payoff_window ? ` · 窗口 ${esc(p.payoff_window.min_offset)}–${esc(p.payoff_window.max_offset)} 章` : ''}</p>
      ${definitionList(p, {setup:'埋设内容', expected_meaning:'读者预期', payoff:'回收兑现', check:'核验口径'})}
    </div>`).join('')}</section>`);
    delete rest.promise_plan;
  }
  if (Array.isArray(rest.reader_plan) && rest.reader_plan.length) {
    parts.push(`<section class="design-card"><h3>读者信息顺序与情绪轨迹（${rest.reader_plan.length}）</h3>${rest.reader_plan.map(r => `<div class="method-section">
      <p><strong>#${esc(r.order ?? '')}</strong> · 事件 <code>${esc(r.event || '')}</code> · 情绪：${esc(r.before_emotion || '—')} → ${esc(r.after_emotion || '—')}</p>
      ${definitionList(r, {information:'披露信息', trigger:'触发依据', intended_effect:'预期读感', check:'核验口径'})}
    </div>`).join('')}</section>`);
    delete rest.reader_plan;
  }
  if (Array.isArray(rest.continuations) && rest.continuations.length) {
    parts.push(`<section class="design-card"><h3>承接前章已核验遗留问题（${rest.continuations.length}）</h3><ul>${rest.continuations.map(c => `<li><code>${esc(c.ref || '')}</code> → 事件 <code>${esc(c.event || '')}</code>：${esc(c.reason || '')}</li>`).join('')}</ul></section>`);
    delete rest.continuations;
  }
  if (Array.isArray(rest.static_bindings) && rest.static_bindings.length) {
    parts.push(`<section class="design-card"><h3>补绑剧情端点关系（${rest.static_bindings.length}）</h3><ul>${rest.static_bindings.map(b => `<li><code>${esc(b.source || '')}</code> → <code>${esc(b.target || '')}</code>（${esc(b.relation || '')}）：${esc(b.condition || '')}</li>`).join('')}</ul></section>`);
    delete rest.static_bindings;
  }
  if (stage === 'event_design' && Array.isArray(rest.candidates) && rest.candidates.length) {
    parts.push(`<section class="design-card"><h3>条件后继事件候选（${rest.candidates.length}）</h3>${rest.candidates.map(c => `<div class="method-section">
      <p><strong><code>${esc(c.id || '')}</code></strong> · 前驱 <code>${esc(c.predecessor || '')}</code> <span class="tag blue">${esc(c.status || 'conditional_candidate')}</span></p>
      ${Array.isArray(c.actors) && c.actors.length ? `<p class="muted"><strong>参与者</strong>：${esc(c.actors.join('、'))}</p>` : ''}
      ${c.completion_gate ? `<p><strong>完成门（沿用前事件）</strong>：${esc(c.completion_gate)}</p>` : ''}
      ${c.event ? `<p><strong>后继候选事件</strong>：${esc(typeof c.event === 'string' ? c.event : JSON.stringify(c.event))}</p>` : ''}
    </div>`).join('')}</section>`);
    delete rest.candidates;
  }
  return parts.join('');
}

function executionStageExtras(rest, stage) {
  const parts = [];
  if (stage === 'action_design') {
    parts.push(`<section class="card stack" id="actionStageHandoffBanner" style="margin-bottom:14px">
      <div class="row spread wrap"><strong>08 行动博弈与试错代价 · 上下游职责贯通</strong><span class="tag blue">能力门槛 · 完整步骤链 · 试错代价</span></div>
      <p class="muted"><strong>承接上游</strong>：04 人物能力与限制 + 06/07 事件节点 + accepted_state ｜ <strong>交付下游</strong>：09 场景显式选用（selected_actions）→ 10 状态变化外部因果 → 12 具象节拍（action_ref / step_index）。</p>
    </section>`);
    if (Array.isArray(rest.candidates) && rest.candidates.length) {
      parts.push(`<section class="design-card"><h3>行动博弈候选（${rest.candidates.length}）</h3>${rest.candidates.map(c => `<div class="method-section">
        <p><strong><code>${esc(c.id || '')}</code></strong> · 行动者 <code>${esc(c.actor || '')}</code> · 对应事件 <code>${esc(c.event || '')}</code> <span class="tag blue">${esc(c.status || 'candidate')}</span></p>
        ${c.action ? `<p><strong>行动选择</strong>：${esc(c.action)}</p>` : ''}
        ${Array.isArray(c.requires) && c.requires.length ? `<p class="muted"><strong>最低能力门槛</strong>：${esc(c.requires.join('、'))}</p>` : ''}
        ${Array.isArray(c.steps) && c.steps.length ? `<div><small class="muted">完整动作步骤链（对象 → 动作 → 阻碍 → 应对 → 结果）</small><ol>${c.steps.map(st => `<li><strong>${esc(st.object || '对象')}</strong>：${esc(st.action || '')} ｜ 阻碍：${esc(st.obstacle || '—')} ｜ 应对：${esc(st.response || '—')} ｜ 结果：${esc(st.result || '—')}</li>`).join('')}</ol></div>` : ''}
        ${definitionList(c, {cost:'真实代价', limits:'适用限制'})}
      </div>`).join('')}</section>`);
      delete rest.candidates;
    }
  }
  if (stage === 'scene_design') {
    parts.push(`<section class="card stack" id="sceneStageHandoffBanner" style="margin-bottom:14px">
      <div class="row spread wrap"><strong>09 场景结构与POV边界 · 上下游职责贯通</strong><span class="tag blue">事件/动作绑定 · 受限POV · 前态快照</span></div>
      <p class="muted"><strong>承接上游</strong>：06/07 事件节点 + 08 行动候选 + 04 入场披露边界 ｜ <strong>交付下游</strong>：10 原样核对 events.before_state → 12 具象锚点 → 13 表达指导 → 15 受限视角正文。</p>
    </section>`);
    const selEvents = Array.isArray(rest.selected_events) ? rest.selected_events : [];
    const selActions = Array.isArray(rest.selected_actions) ? rest.selected_actions : [];
    if (selEvents.length || selActions.length) {
      parts.push(`<section class="design-card"><h3>本场显式选用的上游事件与行动（事件 ${selEvents.length} · 行动 ${selActions.length}）</h3>
        ${selEvents.length ? `<p><strong>选用事件</strong>：${selEvents.map(e => `<code>${esc(e.scene || '')}</code> ← <code>${esc(e.event || '')}</code>`).join('；')}</p>` : ''}
        ${selActions.length ? `<p><strong>选用行动</strong>：${selActions.map(a => `<code>${esc(a.scene || '')}</code> ← <code>${esc(a.action || '')}</code>`).join('；')}</p>` : ''}
      </section>`);
      delete rest.selected_events;
      delete rest.selected_actions;
    }
    if (Array.isArray(rest.chapters) && rest.chapters.length) {
      parts.push(`<section class="design-card"><h3>章场排布与故事时序（${rest.chapters.length} 章）</h3>${rest.chapters.map(ch => `<div class="method-section">
        <p><strong>第 ${esc(ch.index ?? '')} 章</strong>${ch.card ? ` · 章卡 <code>${esc(ch.card)}</code>` : ''}</p>
        ${Array.isArray(ch.scenes) && ch.scenes.length ? `<ul>${ch.scenes.map(sc => `<li>第 ${esc(sc.index ?? '')} 场 <code>${esc(sc.card || '')}</code>（story_order=${esc(sc.story_order ?? '')}）</li>`).join('')}</ul>` : ''}
      </div>`).join('')}</section>`);
      delete rest.chapters;
    }
    if (Array.isArray(rest.events) && rest.events.length) {
      parts.push(`<section class="design-card"><h3>交付 10 状态变化的场内事件与前态快照（${rest.events.length}）</h3>${rest.events.map(ev => `<div class="method-section">
        <p><strong><code>${esc(ev.id || '')}</code></strong> · 场景 <code>${esc(ev.scene || '')}</code> · 实体 <code>${esc(ev.entity || '')}</code></p>
        ${ev.trigger ? `<p><strong>触发事件</strong>：${esc(typeof ev.trigger === 'string' ? ev.trigger : JSON.stringify(ev.trigger))}</p>` : ''}
        ${ev.before_state ? `<div><small class="muted">before_state（10 步必须原样核对）</small>${readable(ev.before_state)}</div>` : ''}
      </div>`).join('')}</section>`);
      delete rest.events;
    }
    if (Array.isArray(rest.scene_progress) && rest.scene_progress.length) {
      parts.push(`<section class="design-card"><h3>章场实质推进记录（${rest.scene_progress.length}）</h3>${rest.scene_progress.map(sp => `<div class="method-section">
        <p><strong>场景 <code>${esc(sp.scene || '')}</code></strong></p>
        ${definitionList(sp, {entry:'进入局面', turn:'关键转向', shift:'局势/认知变化', next_pressure:'遗留压力'})}
      </div>`).join('')}</section>`);
      delete rest.scene_progress;
    }
    if (Array.isArray(rest.cast_payoffs) && rest.cast_payoffs.length) {
      parts.push(`<section class="design-card"><h3>人物本场职责落实（${rest.cast_payoffs.length}）</h3><ul>${rest.cast_payoffs.map(cp => `<li>场景 <code>${esc(cp.scene || '')}</code> · <code>${esc(cp.actor || '')}</code>：${esc(cp.payoff || cp.duty || JSON.stringify(cp))}</li>`).join('')}</ul></section>`);
      delete rest.cast_payoffs;
    }
    if (rest.cast_distribution_plan && typeof rest.cast_distribution_plan === 'object') {
      parts.push(`<section class="design-card"><h3>人物出场分布规划</h3>${readable(rest.cast_distribution_plan)}</section>`);
      delete rest.cast_distribution_plan;
    }
  }
  if (stage === 'state_transition') {
    parts.push(`<section class="card stack" id="stateTransitionStageHandoffBanner" style="margin-bottom:14px">
      <div class="row spread wrap"><strong>10 状态变化与外部因果 · 上下游职责贯通</strong><span class="tag blue">前态核对 · 外部行动触发 · 代价延续</span></div>
      <p class="muted"><strong>承接上游</strong>：09 events.before_state + 08 外部行动与限制 ｜ <strong>交付下游</strong>：11 状态传播根变化（planned_change）→ 12 可见节拍 → 17 正文状态提取与连续性验收。</p>
    </section>`);
    if (Array.isArray(rest.patches) && rest.patches.length) {
      parts.push(`<section class="design-card"><h3>回写场景的抉择与结果补丁（${rest.patches.length}）</h3>${rest.patches.map(p => `<div class="method-section">
        <p><strong>场景 <code>${esc(p.scene || '')}</code></strong></p>
        ${definitionList(p, {choice:'最终抉择', planned_result:'一致化结果'})}
      </div>`).join('')}</section>`);
      delete rest.patches;
    }
    if (Array.isArray(rest.transitions) && rest.transitions.length) {
      parts.push(`<section class="design-card"><h3>状态迁移与代价连续性台账（${rest.transitions.length}）</h3>${rest.transitions.map(t => `<div class="method-section">
        <p><strong>场景 <code>${esc(t.scene || '')}</code></strong> · 实体 <code>${esc(t.entity || '')}</code> · 事件 <code>${esc(t.event || '')}</code></p>
        ${t.action ? `<p><strong>触发外部行动</strong>：${esc(t.action)}</p>` : ''}
        <div class="row wrap" style="gap:12px">
          ${t.before_state ? `<div style="flex:1;min-width:180px"><small class="muted">前态（before_state）</small>${readable(t.before_state)}</div>` : ''}
          ${t.after_state ? `<div style="flex:1;min-width:180px"><small class="muted">后态（after_state）</small>${readable(t.after_state)}</div>` : ''}
        </div>
        ${definitionList(t, {cost:'持续代价与限制', failure:'失败情形与应对', continuity:'后场连续性延续'})}
      </div>`).join('')}</section>`);
      delete rest.transitions;
    }
  }
  if (stage === 'state_propagation') {
    parts.push(`<section class="card stack" id="statePropagationStageHandoffBanner" style="margin-bottom:14px">
      <div class="row spread wrap"><strong>11 状态传播与连锁感知 · 上下游职责贯通</strong><span class="tag blue">非全知载体 · 三门条件候选</span></div>
      <p class="muted"><strong>承接上游</strong>：10 planned_change / accepted_fact + 05 实体通道 ｜ <strong>交付下游</strong>：12 锚点显式选用（selected_propagations），未选保留后续预案，绝不直接改写 WORLD 事实。</p>
    </section>`);
    if (Array.isArray(rest.candidates) && rest.candidates.length) {
      parts.push(`<section class="design-card"><h3>条件状态传播候选（${rest.candidates.length}）</h3>${rest.candidates.map(c => {
        const g = c.gates || {};
        return `<div class="method-section">
          <p><strong><code>${esc(c.id || '')}</code></strong> · <code>${esc(c.source_entity || '')}</code> → <code>${esc(c.target_entity || '')}</code> <span class="tag blue">${esc(c.status || 'conditional_candidate')}</span></p>
          <p class="muted"><strong>根变化</strong>：${esc(c.root_kind || '')}（<code>${esc(c.root_id || '')}</code>）${c.scene ? ` · 落场 <code>${esc(c.scene)}</code>` : ' · 暂不限定当前场'}</p>
          ${definitionList(c, {external_action:'传播载体/外部行动', activation_condition:'三门激活条件', continuity:'连续性衔接'})}
          ${c.proposed_effect ? `<div><small class="muted">候选影响（proposed_effect）</small>${readable(c.proposed_effect)}</div>` : ''}
          <div class="row wrap" style="margin-top:6px">
            <span class="tag ${g.require_root_confirmation ? 'green' : ''}">根变化确认:${g.require_root_confirmation ? '开' : '未设'}</span>
            <span class="tag ${g.require_external_action_selection ? 'green' : ''}">外部行动选定:${g.require_external_action_selection ? '开' : '未设'}</span>
            <span class="tag ${g.require_continuity_validation ? 'green' : ''}">连续性校验:${g.require_continuity_validation ? '开' : '未设'}</span>
          </div>
        </div>`;
      }).join('')}</section>`);
      delete rest.candidates;
    }
  }
  if ((stage === 'action_design' || stage === 'state_propagation') && Array.isArray(rest.waiting) && rest.waiting.length) {
    parts.push(`<section class="design-card"><h3>前置缺失待核项（${rest.waiting.length}）</h3><ul>${rest.waiting.map(w => `<li>来源 <code>${esc(w.source_id || '')}</code> · 缺失：${esc(Array.isArray(w.missing) ? w.missing.join('、') : (w.missing || '—'))} · 原因：${esc(w.reason || '')}</li>`).join('')}</ul></section>`);
    delete rest.waiting;
  }
  return parts.join('');
}

function craftAndBindStageExtras(rest, stage) {
  const parts = [];
  if (stage === 'anchor_design') {
    parts.push(`<section class="card stack" id="anchorStageHandoffBanner" style="margin-bottom:14px">
      <div class="row spread wrap"><strong>12 具象锚点与身体节拍 · 上下游职责贯通</strong><span class="tag blue">POV观察者 · 动作节拍 · 传播落场</span></div>
      <p class="muted"><strong>承接上游</strong>：08 行动步骤 + 09 场景 POV 与空间 + 10 状态代价 + 11 条件传播候选 ｜ <strong>交付下游</strong>：13 表达指导 → 14 范围绑定 → 15 正文写作（绝不跳过节拍写空洞形容词）。</p>
    </section>`);
    if (Array.isArray(rest.selected_propagations) && rest.selected_propagations.length) {
      parts.push(`<section class="design-card"><h3>本场采纳的状态传播候选（${rest.selected_propagations.length}）</h3><ul>${rest.selected_propagations.map(p => `<li>场景 <code>${esc(p.scene || '')}</code> ← 传播候选 <code>${esc(p.propagation || '')}</code></li>`).join('')}</ul></section>`);
      delete rest.selected_propagations;
    }
    if (Array.isArray(rest.beats) && rest.beats.length) {
      parts.push(`<section class="design-card"><h3>具象可见节拍清单（${rest.beats.length} 拍）</h3>${rest.beats.map((b, i) => `<div class="method-section">
        <p><strong>#${i + 1}</strong> · 场景 <code>${esc(b.scene || '')}</code> · 观察者 POV <code>${esc(b.observer || '')}</code>${b.timing ? ` <span class="tag blue">${esc(b.timing)}</span>` : ''}${b.action_ref ? ` · 动作 <code>${esc(b.action_ref)}</code>${b.step_index != null ? `[step ${esc(b.step_index)}]` : ''}` : ''}</p>
        ${definitionList(b, {object:'观察对象/物件', action:'触发动作', observable:'POV 可见节拍', trigger_basis:'触发依据', check:'效果判据'})}
      </div>`).join('')}</section>`);
      delete rest.beats;
    }
  }
  if (stage === 'expression_design') {
    parts.push(`<section class="card stack" id="expressionStageHandoffBanner" style="margin-bottom:14px">
      <div class="row spread wrap"><strong>13 叙述距离与表达设计 · 上下游职责贯通</strong><span class="tag blue">可写可核指导 · 偏好协调 · 段落技法</span></div>
      <p class="muted"><strong>承接上游</strong>：09 披露边界 + 12 具象节拍 + 写法/语气/文风偏好 ｜ <strong>交付下游</strong>：14 绑定汇总 → 15 正文落笔（observable）→ 16 独立审稿逐条引文核验（check）。</p>
    </section>`);
    if (Array.isArray(rest.preference_resolutions) && rest.preference_resolutions.length) {
      parts.push(`<section class="design-card"><h3>竞争立项偏好协调落点（${rest.preference_resolutions.length}）</h3>${rest.preference_resolutions.map(pr => `<div class="method-section">
        <p><strong><code>${esc(pr.key || '')}</code></strong> <span class="tag ${pr.status === 'applied' ? 'green' : ''}">${pr.status === 'applied' ? '已落场' : '暂缓延后'}</span>${pr.output_ref ? ` · 落点 <code>${esc(pr.output_ref)}</code>` : ''}</p>
        ${pr.reason ? `<p class="muted">${esc(pr.reason)}</p>` : ''}
      </div>`).join('')}</section>`);
      delete rest.preference_resolutions;
    }
    if (Array.isArray(rest.guidance) && rest.guidance.length) {
      parts.push(`<section class="design-card"><h3>分场景表达指导与审稿判据（${rest.guidance.length}）</h3>${rest.guidance.map((g, i) => `<div class="method-section">
        <p><strong>#${i}</strong> · 场景 <code>${esc(g.scene || '')}</code></p>
        ${definitionList(g, {observable:'本场具体动作/情绪/对白表现', check:'独立审稿核验判据'})}
      </div>`).join('')}</section>`);
      delete rest.guidance;
    }
    if (Array.isArray(rest.passage_sequences) && rest.passage_sequences.length) {
      parts.push(`<section class="design-card"><h3>段落连续技法编排（${rest.passage_sequences.length}）</h3>${readable(rest.passage_sequences)}</section>`);
      delete rest.passage_sequences;
    }
    if (Array.isArray(rest.craft_applications) && rest.craft_applications.length) {
      parts.push(`<section class="design-card"><h3>单项段落技法应用（${rest.craft_applications.length}）</h3>${readable(rest.craft_applications)}</section>`);
      delete rest.craft_applications;
    }
  }
  if (stage === 'bind_scope') {
    parts.push(`<section class="card stack" id="bindScopeStageHandoffBanner" style="margin-bottom:14px">
      <div class="row spread wrap"><strong>14 范围绑定与检验收口 · 上下游职责贯通</strong><span class="tag blue">零改写上游 · 写审验收清账</span></div>
      <p class="muted"><strong>承接上游</strong>：01–13 全部已采用资料与拆解方法 ｜ <strong>交付下游</strong>：15 正文写作逐场落实 <code>method_guidance.observable</code> → 16 独立审稿按 <code>check</code> 引文核验 → 17 状态提取与批次接受。</p>
    </section>`);
    if (Array.isArray(rest.method_guidance) && rest.method_guidance.length) {
      parts.push(`<section class="design-card"><h3>交付 15 写手与 16 审稿的方法落场清单（${rest.method_guidance.length}）</h3>${rest.method_guidance.map(mg => `<div class="method-section">
        <p><strong>场景 <code>${esc(mg.scene || '')}</code></strong>${Array.isArray(mg.source_ids) && mg.source_ids.length ? ` · 方法/资料 <code>${esc(mg.source_ids.join(', '))}</code>` : ''}</p>
        ${definitionList(mg, {observable:'POV 可见表现要求', check:'原义独立审稿判据'})}
      </div>`).join('')}</section>`);
      delete rest.method_guidance;
    }
    if (rest.material_bindings && typeof rest.material_bindings === 'object' && Object.keys(rest.material_bindings).length) {
      parts.push(`<section class="design-card"><h3>资料到项目成员绑定</h3>${readable(rest.material_bindings)}</section>`);
      delete rest.material_bindings;
    }
    if (rest.process_bindings && typeof rest.process_bindings === 'object' && Object.keys(rest.process_bindings).length) {
      parts.push(`<section class="design-card"><h3>制作过程绑定</h3>${readable(rest.process_bindings)}</section>`);
      delete rest.process_bindings;
    }
  }
  return parts.join('');
}

export function planArtifacts(output, context = {}) {
  if (!output || typeof output !== 'object') return readable(output);
  const {members, _method_applications: apps, _method_receipts: receipts, ...rest} = output;
  const visible = [], other = [];
  if (Array.isArray(members)) {
    for (const member of members) {
      if (fields[member?.kind] && member.body) visible.push(member);
      else other.push(member);
    }
    if (other.length) rest.members = other.map(member => member?.body || member);
  }
  const stage = context.stage || '';
  const extras = worldStageExtras(rest, stage) + characterAndRelationsStageExtras(rest, stage) + plotAndEventStageExtras(rest, stage) + executionStageExtras(rest, stage) + craftAndBindStageExtras(rest, stage);
  return extras
    + methodApplicationsSection(apps, receipts)
    + visible.map(scopeArtifact).join('')
    + (Object.keys(rest).length ? readable(rest) : '');
}
