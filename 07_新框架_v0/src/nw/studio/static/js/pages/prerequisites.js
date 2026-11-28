import {api, enc} from '../api.js';
import {$, esc, empty, loading} from '../ui.js';

const stageNames = {
  type_selection: '01. 类型选择', type_adaptation: '02. 类型适配',
  world_design: '03. 世界设计', character_design: '04. 人物设计',
  static_relations: '05. 静态关系', plot_design: '06. 剧情设计',
  event_design: '07. 事件设计', action_design: '08. 行动设计',
  scene_design: '09. 场景设计', state_transition: '10. 状态变化',
  state_propagation: '11. 状态传播', anchor_design: '12. 锚点设计',
  expression_design: '13. 表达设计', bind_scope: '14. 绑定汇总',
  writer: '15. 正文写作', review: '16. 独立审稿', acceptance: '17. 状态提取与验收',
};

const scopeLabels = {book: '全书', volume: '卷纲', chapter: '章纲', scene: '场景'};

function ruleDetails(rule) {
  const fields = [
    ['原条条件', rule.condition],
    ['需要的前置', rule.needs],
    ['本步操作', rule.operation],
    ['核对前置的步骤', stageNames[rule.basis_stage] || rule.basis_stage],
    ['交接步骤', rule.status === 'unresolved' ? '待原义核清后再决定' : rule.consumers.map(key => stageNames[key] || key).join('、')],
    ['验收方法', rule.check],
  ];
  if (rule.blocked_reason) fields.push(['原义待核原因', rule.blocked_reason]);
  return `<details class="details" data-rule-key="${esc(rule.key)}">
    <summary><strong>${esc(rule.key)}</strong> · ${esc(rule.source)} → ${esc(rule.target)}
      <span class="muted">（${esc(rule.relation)}）</span>
      ${rule.status === 'unresolved' ? '<span class="tag">待核原义</span>' : ''}</summary>
    <dl>${fields.map(([name, value]) => `<dt><strong>${name}</strong></dt><dd>${esc(value)}</dd>`).join('')}</dl>
  </details>`;
}

function worldCategoriesHtml(step, worldProfile = null) {
  const categories = worldProfile?.categories || step.world_categories || [];
  if (step.step_id !== 'world_design' || !categories.length) return '';
  const boundary = worldProfile?.step_boundary || step.step_boundary || {};
  const rp = worldProfile?.resource_profile || null;
  return `<div class="card stack" id="worldBlueprintCategories">
    <div class="row spread wrap">
      <strong>03 世界设计 · 9 类世界资料细分域与题材适用边界</strong>
      <span class="muted">${worldProfile?.has_genre_binding ? `已按「${esc((worldProfile.main_types || []).map(t => t.name).join(' / '))}」排序与隔离` : '选择上方类型可按题材自动区隔核心与跨类型项'}</span>
    </div>
    <div class="stack" style="gap:8px">${categories.map(cat => {
      const badgeCls = cat.relevance === 'primary' ? 'green' : cat.relevance === 'optional' ? 'blue' : '';
      return `<div class="method-section">
        <div class="row spread wrap">
          <strong>${esc(cat.name)}</strong>
          <div class="row wrap">
            ${cat.relevance_label ? `<span class="tag ${badgeCls}">${esc(cat.relevance_label)}</span>` : ''}
            ${cat.receivable_count != null ? `<span class="tag ${cat.receivable_count ? 'green' : ''}">可接收方法 ${cat.receivable_count} 条</span>` : ''}
          </div>
        </div>
        <p class="muted">${esc(cat.boundary_note || cat.usage_mode || cat.description || '')}</p>
        ${cat.source_files?.length ? `<small class="faint">原工作流资料来源：${esc(cat.source_files.join('；'))}</small>` : ''}
      </div>`;
    }).join('')}</div>
    ${rp?.preferred_resources?.length ? `<p class="muted"><strong>本类型典型资源口径</strong>：核心资源（${esc(rp.preferred_resources.join('、'))}）｜交换媒介（${esc((rp.exchange_media || []).join('、'))}）｜长期制约（${esc((rp.long_term_constraints || []).join('、'))}）</p>` : ''}
    ${worldProfile?.decomposition_focus ? `<p class="muted"><strong>拆解该类型世界规则重点</strong>：${esc(worldProfile.decomposition_focus)}</p>` : ''}
    ${boundary.out_of_scope?.length ? `<details class="details"><summary>03 世界设计严格禁止越界事项（${boundary.out_of_scope.length} 条）</summary><ul>${boundary.out_of_scope.map(item => `<li>${esc(item)}</li>`).join('')}</ul></details>` : ''}
  </div>`;
}

function characterCategoriesHtml(step, charProfile = null) {
  if (step.step_id !== 'character_design' && step.step_id !== 'static_relations') return '';
  const isChar = step.step_id === 'character_design';
  const categories = isChar
    ? (charProfile?.character_categories || step.character_categories || [])
    : (charProfile?.relation_categories || step.relation_categories || []);
  if (!categories.length) return '';
  const boundary = charProfile?.step_boundaries?.[step.step_id] || step.step_boundary || {};
  const cp = charProfile?.cast_profile || null;
  const panelId = isChar ? 'characterBlueprintCategories' : 'staticRelationsBlueprintCategories';
  const heading = isChar ? '04 人物设计 · 6 类人物资料细分域与题材边界' : '05 静态关系 · 4 类关系张力细分域与题材边界';
  return `<div class="card stack" id="${panelId}">
    <div class="row spread wrap">
      <strong>${heading}</strong>
      <span class="muted">${charProfile?.has_genre_binding ? `已按「${esc((charProfile.main_types || []).map(t => t.name).join(' / '))}」排序与隔离` : '选择上方类型可按题材自动区隔核心与跨类型项'}</span>
    </div>
    <div class="stack" style="gap:8px">${categories.map(cat => {
      const badgeCls = cat.relevance === 'primary' ? 'green' : cat.relevance === 'optional' ? 'blue' : '';
      return `<div class="method-section">
        <div class="row spread wrap">
          <strong>${esc(cat.name)}</strong>
          <div class="row wrap">
            ${cat.relevance_label ? `<span class="tag ${badgeCls}">${esc(cat.relevance_label)}</span>` : ''}
            ${cat.receivable_count != null ? `<span class="tag ${cat.receivable_count ? 'green' : ''}">可接收方法 ${cat.receivable_count} 条</span>` : ''}
          </div>
        </div>
        <p class="muted">${esc(cat.boundary_note || cat.usage_mode || cat.description || '')}</p>
        ${cat.source_files?.length ? `<small class="faint">原工作流资料来源：${esc(cat.source_files.join('；'))}</small>` : ''}
      </div>`;
    }).join('')}</div>
    ${cp ? `<p class="muted"><strong>本类型重点</strong>：${esc(isChar ? cp.archetype_focus : cp.relation_focus)}${isChar && cp.antagonist_pattern ? ` ｜ <strong>反派模式</strong>：${esc(cp.antagonist_pattern)}` : ''}</p>` : ''}
    ${charProfile?.decomposition_focus ? `<p class="muted"><strong>拆解该类型重点</strong>：${esc(charProfile.decomposition_focus)}</p>` : ''}
    ${boundary.out_of_scope?.length ? `<details class="details"><summary>${isChar ? '04 人物设计' : '05 静态关系'}严格禁止越界事项（${boundary.out_of_scope.length} 条）</summary><ul>${boundary.out_of_scope.map(item => `<li>${esc(item)}</li>`).join('')}</ul></details>` : ''}
  </div>`;
}

function plotEventCategoriesHtml(step, plotProfile = null) {
  if (step.step_id !== 'plot_design' && step.step_id !== 'event_design') return '';
  const isPlot = step.step_id === 'plot_design';
  const categories = isPlot
    ? (plotProfile?.plot_categories || step.plot_categories || [])
    : (plotProfile?.event_categories || step.event_categories || []);
  if (!categories.length) return '';
  const boundary = plotProfile?.step_boundaries?.[step.step_id] || step.step_boundary || {};
  const pp = plotProfile?.plot_profile || null;
  const panelId = isPlot ? 'plotBlueprintCategories' : 'eventBlueprintCategories';
  const heading = isPlot ? '06 剧情设计 · 10 类结构/卖点/伏笔细分域与题材边界' : '07 事件设计 · 2 类事件链与危机机制细分域与题材边界';
  return `<div class="card stack" id="${panelId}">
    <div class="row spread wrap">
      <strong>${heading}</strong>
      <span class="muted">${plotProfile?.has_genre_binding ? `已按「${esc((plotProfile.main_types || []).map(t => t.name).join(' / '))}」排序与隔离` : '选择上方类型可按题材自动区隔核心与跨类型项'}</span>
    </div>
    <div class="stack" style="gap:8px">${categories.map(cat => {
      const badgeCls = cat.relevance === 'primary' ? 'green' : cat.relevance === 'optional' ? 'blue' : '';
      return `<div class="method-section">
        <div class="row spread wrap">
          <strong>${esc(cat.name)}</strong>
          <div class="row wrap">
            ${cat.relevance_label ? `<span class="tag ${badgeCls}">${esc(cat.relevance_label)}</span>` : ''}
            ${cat.receivable_count != null ? `<span class="tag ${cat.receivable_count ? 'green' : ''}">可接收方法 ${cat.receivable_count} 条</span>` : ''}
          </div>
        </div>
        <p class="muted">${esc(cat.boundary_note || cat.usage_mode || cat.description || '')}</p>
        ${cat.source_files?.length ? `<small class="faint">原工作流资料来源：${esc(cat.source_files.join('；'))}</small>` : ''}
      </div>`;
    }).join('')}</div>
    ${pp ? `<p class="muted"><strong>本类型重点</strong>：${esc(isPlot ? `${pp.arc_pattern} ｜ ${pp.hook_foreshadow_pattern}` : pp.event_trigger_pattern)}</p>` : ''}
    ${plotProfile?.decomposition_focus ? `<p class="muted"><strong>拆解该类型重点</strong>：${esc(plotProfile.decomposition_focus)}</p>` : ''}
    ${boundary.out_of_scope?.length ? `<details class="details"><summary>${isPlot ? '06 剧情设计' : '07 事件设计'}严格禁止越界事项（${boundary.out_of_scope.length} 条）</summary><ul>${boundary.out_of_scope.map(item => `<li>${esc(item)}</li>`).join('')}</ul></details>` : ''}
  </div>`;
}

function executionCategoriesHtml(step, execProfile = null) {
  const cfg = {
    action_design: {
      panelId: 'actionBlueprintCategories',
      heading: '08 行动设计 · 4 类行动博弈与试错代价细分域与题材边界',
      profileKey: 'action_categories',
      stepKey: 'action_categories',
      focusKey: 'action_style',
      label: '08 行动设计',
    },
    scene_design: {
      panelId: 'sceneBlueprintCategories',
      heading: '09 场景设计 · 3 类视角边界与场景结构细分域与题材边界',
      profileKey: 'scene_categories',
      stepKey: 'scene_categories',
      focusKey: 'scene_pov_focus',
      label: '09 场景设计',
    },
    state_transition: {
      panelId: 'stateTransitionBlueprintCategories',
      heading: '10 状态变化 · 3 类外部因果与代价守恒细分域与题材边界',
      profileKey: 'transition_categories',
      stepKey: 'transition_categories',
      focusKey: 'state_cost_focus',
      label: '10 状态变化',
    },
    state_propagation: {
      panelId: 'statePropagationBlueprintCategories',
      heading: '11 状态传播 · 2 类非全知载体与生态波及细分域与题材边界',
      profileKey: 'propagation_categories',
      stepKey: 'propagation_categories',
      focusKey: 'propagation_focus',
      label: '11 状态传播',
    },
  }[step.step_id];
  if (!cfg) return '';
  const categories = execProfile?.[cfg.profileKey] || step[cfg.stepKey] || [];
  if (!categories.length) return '';
  const boundary = execProfile?.step_boundaries?.[step.step_id] || step.step_boundary || {};
  const ep = execProfile?.execution_profile || null;
  return `<div class="card stack" id="${cfg.panelId}">
    <div class="row spread wrap">
      <strong>${cfg.heading}</strong>
      <span class="muted">${execProfile?.has_genre_binding ? `已按「${esc((execProfile.main_types || []).map(t => t.name).join(' / '))}」排序与隔离` : '选择上方类型可按题材自动区隔核心与跨类型项'}</span>
    </div>
    <div class="stack" style="gap:8px">${categories.map(cat => {
      const badgeCls = cat.relevance === 'primary' ? 'green' : cat.relevance === 'optional' ? 'blue' : '';
      return `<div class="method-section">
        <div class="row spread wrap">
          <strong>${esc(cat.name)}</strong>
          <div class="row wrap">
            ${cat.relevance_label ? `<span class="tag ${badgeCls}">${esc(cat.relevance_label)}</span>` : ''}
            ${cat.receivable_count != null ? `<span class="tag ${cat.receivable_count ? 'green' : ''}">可接收方法 ${cat.receivable_count} 条</span>` : ''}
          </div>
        </div>
        <p class="muted">${esc(cat.boundary_note || cat.usage_mode || cat.description || '')}</p>
        ${cat.source_files?.length ? `<small class="faint">原工作流资料来源：${esc(cat.source_files.join('；'))}</small>` : ''}
      </div>`;
    }).join('')}</div>
    ${ep?.[cfg.focusKey] ? `<p class="muted"><strong>本类型本步重点</strong>：${esc(ep[cfg.focusKey])}</p>` : ''}
    ${execProfile?.decomposition_focus ? `<p class="muted"><strong>拆解 08–11 执行链重点</strong>：${esc(execProfile.decomposition_focus)}</p>` : ''}
    ${boundary.out_of_scope?.length ? `<details class="details"><summary>${cfg.label}严格禁止越界事项（${boundary.out_of_scope.length} 条）</summary><ul>${boundary.out_of_scope.map(item => `<li>${esc(item)}</li>`).join('')}</ul></details>` : ''}
  </div>`;
}

function craftCategoriesHtml(step, craftProfile = null) {
  const cfg = {
    anchor_design: {
      panelId: 'anchorBlueprintCategories',
      heading: '12 锚点设计 · 2 类具象节拍与传播落场细分域与边界',
      key: 'anchor_categories',
      focusKey: 'anchor_focus',
      label: '12 锚点设计',
    },
    expression_design: {
      panelId: 'expressionBlueprintCategories',
      heading: '13 表达设计 · 6 类叙述距离、对白感官、语气与文风细分域与边界',
      key: 'expression_categories',
      focusKey: 'expression_focus',
      label: '13 表达设计',
    },
    bind_scope: {
      panelId: 'bindScopeBlueprintCategories',
      heading: '14 绑定汇总 · 范围收口与写审交接契约边界',
      key: 'bind_scope_categories',
      focusKey: 'writer_review_focus',
      label: '14 绑定汇总',
    },
    writer: {
      panelId: 'writerBlueprintCategories',
      heading: '15 正文写作 · 受限 POV、精确动词与代价可视化执行域',
      key: 'writer_categories',
      focusKey: 'writer_review_focus',
      label: '15 正文写作',
    },
    review: {
      panelId: 'reviewBlueprintCategories',
      heading: '16 独立审稿 · 正文引文核验、语言红线与一致性复核域',
      key: 'review_categories',
      focusKey: 'writer_review_focus',
      label: '16 独立审稿',
    },
    acceptance: {
      panelId: 'acceptanceBlueprintCategories',
      heading: '17 状态验收 · 正文偏移增量提取、主客观事实隔离与批次收口域',
      key: 'acceptance_categories',
      focusKey: 'acceptance_focus',
      label: '17 状态验收',
    },
  }[step.step_id];
  if (!cfg) return '';
  const categories = craftProfile?.[cfg.key] || step[cfg.key] || [];
  if (!categories.length) return '';
  const boundary = craftProfile?.step_boundaries?.[step.step_id] || step.step_boundary || {};
  const cp = craftProfile?.craft_profile || null;
  return `<div class="card stack" id="${cfg.panelId}">
    <div class="row spread wrap">
      <strong>${cfg.heading}</strong>
      <span class="muted">${craftProfile?.has_genre_binding ? `已按「${esc((craftProfile.main_types || []).map(t => t.name).join(' / '))}」绑定语气/文风与写审重点` : '选择上方类型可按题材定制语气文风与写审重点'}</span>
    </div>
    <div class="stack" style="gap:8px">${categories.map(cat => {
      const badgeCls = cat.relevance === 'primary' ? 'green' : cat.relevance === 'optional' ? 'blue' : '';
      return `<div class="method-section">
        <div class="row spread wrap">
          <strong>${esc(cat.name)}</strong>
          <div class="row wrap">
            ${cat.relevance_label ? `<span class="tag ${badgeCls}">${esc(cat.relevance_label)}</span>` : ''}
            ${cat.receivable_count != null ? `<span class="tag ${cat.receivable_count ? 'green' : ''}">可接收方法 ${cat.receivable_count} 条</span>` : ''}
          </div>
        </div>
        <p class="muted">${esc(cat.boundary_note || cat.usage_mode || cat.description || '')}</p>
        ${cat.source_files?.length ? `<small class="faint">原工作流资料来源：${esc(cat.source_files.join('；'))}</small>` : ''}
      </div>`;
    }).join('')}</div>
    ${cp?.[cfg.focusKey] ? `<p class="muted"><strong>本类型本步重点</strong>：${esc(cp[cfg.focusKey])}</p>` : ''}
    ${craftProfile?.decomposition_focus ? `<p class="muted"><strong>拆解 12–17 表达与写审重点</strong>：${esc(craftProfile.decomposition_focus)}</p>` : ''}
    ${boundary.out_of_scope?.length ? `<details class="details"><summary>${cfg.label}严格禁止越界事项（${boundary.out_of_scope.length} 条）</summary><ul>${boundary.out_of_scope.map(item => `<li>${esc(item)}</li>`).join('')}</ul></details>` : ''}
  </div>`;
}

function stepCard(step, auditStep = null, worldProfile = null, charProfile = null, plotProfile = null, execProfile = null, craftProfile = null) {
  const cov = step.library_coverage || {};
  const badge = auditStep
    ? (auditStep.receivable_count > 0
      ? `<span class="tag green">本类型可接收 ${auditStep.receivable_count} 条</span>`
      : auditStep.blocked_count > 0
        ? `<span class="tag" style="color:var(--danger)">受阻 ${auditStep.blocked_count} 条</span>`
        : auditStep.extra_assets?.length
          ? '<span class="tag blue">样本/技法已接通</span>'
          : auditStep.draft_count > 0
            ? `<span class="tag amber">待审核草稿 ${auditStep.draft_count} 条</span>`
            : '<span class="tag">待拆解补齐</span>')
    : (cov.status === 'covered'
      ? `<span class="tag green">已批准方法 ${cov.approved_method_count} 条</span>`
      : cov.status === 'draft_only'
        ? `<span class="tag amber">待审核草稿 ${cov.draft_method_count} 条</span>`
        : '<span class="tag">待拆解补齐</span>');
  const scopes = (step.hierarchical_scopes || step.scopes || []).map(s => scopeLabels[s] || s).join(' / ');
  const natures = (step.material_natures || []).map(n => `<span class="tag blue">${esc(n.name)}</span>`).join(' ');
  const guide = step.decomposition_guide || {};
  const outputs = (step.output_fields || []).map(f => f.label).join('、') || '交付下游写审与状态提交';
  const tasks = (step.method_tasks || []).map(t => t.name).join('、') || '由上游设计与写审规则承接';
  const domains = (step.corpus_domains || []).map(d => d.name).join('、') || '不直接拆解';
  const techniques = (step.passage_techniques || []).map(t => t.label).join('、');
  const auditHtml = auditStep ? `<div class="card">
      <strong>下游真实接收体检（按工作流实际前置与层级规则）</strong>
      ${auditStep.extra_assets?.length ? `<p class="muted" style="margin-top:6px">已接通非方法资产：${auditStep.extra_assets.map(esc).join('；')}</p>` : ''}
      ${auditStep.receivable_methods?.length ? `<div style="margin-top:6px"><small class="muted">本步可接收方法：</small><ul>${auditStep.receivable_methods.map(m => `<li><a class="text-link" href="#/kb/items?method=${enc(m.id)}&amp;version=${m.version}">${esc(m.title)} · v${m.version}</a>（${esc(m.scope_name)} · ${esc((m.field_labels || []).join('/') || (m.task_names || []).join('/'))}）</li>`).join('')}</ul></div>` : ''}
      ${auditStep.blocked_methods?.length ? `<div class="notice warning" style="margin-top:6px"><strong>已批准但本步暂不能接收</strong><ul>${auditStep.blocked_methods.map(m => `<li><a class="text-link" href="#/kb/items?method=${enc(m.id)}&amp;version=${m.version}">${esc(m.title)}</a>：${esc((m.reasons || []).join('；'))}</li>`).join('')}</ul></div>` : ''}
      ${!auditStep.receivable_methods?.length && !auditStep.blocked_methods?.length && !auditStep.extra_assets?.length ? '<p class="muted" style="margin-top:6px">该类型在此步骤暂无已就绪拆解产物。</p>' : ''}
    </div>` : '';
  return `<details class="details" data-step-blueprint="${esc(step.step_id)}">
    <summary><div class="row spread wrap" style="display:inline-flex;width:calc(100% - 24px)">
      <span><strong>${esc(step.name)}</strong> <span class="muted">· ${esc(step.phase_group)} · ${esc(scopes)}</span></span>
      <span>${badge} <span class="muted">内置资料 ${step.workflow_material_key_count || 0} 条</span></span>
    </div></summary>
    <div class="stack" style="margin-top:10px">
      <div class="row wrap">${natures}</div>
      ${auditHtml}
      ${worldCategoriesHtml(step, worldProfile)}
      ${characterCategoriesHtml(step, charProfile)}
      ${plotEventCategoriesHtml(step, plotProfile)}
      ${executionCategoriesHtml(step, execProfile)}
      ${craftCategoriesHtml(step, craftProfile)}
      <div><strong>本步资料需求分类</strong><ul>${(step.need_categories || []).map(c => `<li>${esc(c)}</li>`).join('')}</ul></div>
      <div class="card">
        <strong>拆解参考小说时的采集方式（读取 → 检索 → 作用性 → 方式性）</strong>
        <dl style="margin-top:8px">
          <dt><strong>1. 读取目标</strong></dt><dd>${esc(guide.reading_target || '')}</dd>
          <dt><strong>2. 检索线索</strong></dt><dd>${esc(guide.retrieval_cues || '')}</dd>
          <dt><strong>3. 作用性判定（功能/效果）</strong></dt><dd>${esc(guide.functional_judgment || '')}</dd>
          <dt><strong>4. 方式性判定（做法/边界）</strong></dt><dd>${esc(guide.method_judgment || '')}</dd>
        </dl>
      </div>
      <p class="muted"><strong>关联拆解领域</strong>：${esc(domains)}${techniques ? ` ｜ <strong>段落技法</strong>：${esc(techniques)}` : ''}</p>
      <p class="muted"><strong>对应生产任务</strong>：${esc(tasks)} ｜ <strong>步骤输出产物</strong>：${esc(outputs)}</p>
      <div class="row wrap">
        <a class="secondary" href="#/kb/items?stage=${enc(step.step_id)}">查看本步制作方法</a>
        <a class="ghost" href="#/staging">前往预存库拆解补齐</a>
      </div>
    </div>
  </details>`;
}

export async function renderPrerequisites(ctx) {
  const root = $('#kbContent');
  const designStages = Object.entries(stageNames).filter(([id]) => !['writer', 'review', 'acceptance'].includes(id));
  root.innerHTML = `<section id="stepBlueprintPanel" class="stack" style="margin-bottom:28px">${loading()}</section>
  <div class="divider"></div>
  <section class="stack" id="jointMaterialSandbox">
    <div class="section-head">
      <h2>工作流 14 步联合资料干跑沙盘与前置台账</h2>
      <span class="muted">演练本步真实召回的资料条目、主驱动/硬边界/表达锚点分工、跨步防遗忘守卫与网络前置规则</span>
    </div>
    <div class="row wrap">
      <label class="field"><span>规划层级</span><select id="prerequisiteScope">
        <option value="book">全书（book）</option><option value="volume">卷纲（volume）</option><option value="chapter" selected>章场（chapter）</option>
      </select></label>
      <label class="field"><span>制作步骤</span><select id="prerequisiteStage">
        ${designStages.map(([id, label]) => `<option value="${esc(id)}" ${id === 'world_design' ? 'selected' : ''}>${esc(label)}</option>`).join('')}
      </select></label>
      <label class="field"><span>前置规则筛选</span><select id="prerequisiteStatus">
        <option value="all">全部条目</option><option value="unresolved">仅待核原义</option>
      </select></label>
    </div>
    <div class="form-grid">
      <label class="field"><span>演练故事构想（选填，留空使用内置悬疑样本）</span>
        <input id="sandboxBriefText" placeholder="例如：边境驿站孤证追凶，风雪封山三日内查明失踪密使与军饷账册…">
      </label>
      <label class="field"><span>作者硬约束（选填）</span>
        <input id="sandboxConstraints" placeholder="例如：单章单POV；禁止机械降神；每次试错必须付出社会关系代价…">
      </label>
    </div>
    <div class="row wrap">
      <button class="secondary" type="button" id="runMaterialSandbox">干跑模拟本步资料召回与角色分工</button>
    </div>
    <div id="pipelineRuntimeBlueprint"></div>
    <div id="prerequisiteResults" aria-live="polite"></div>
  </section>`;

  const blueprintPanel = $('#stepBlueprintPanel', root);
  const scopeSelect = $('#prerequisiteScope', root);
  const select = $('#prerequisiteStage', root);
  const filter = $('#prerequisiteStatus', root);
  const briefInput = $('#sandboxBriefText', root);
  const constraintsInput = $('#sandboxConstraints', root);
  const runBtn = $('#runMaterialSandbox', root);
  const runtimeBox = $('#pipelineRuntimeBlueprint', root);
  const target = $('#prerequisiteResults', root);
  let sequence = 0;

  async function loadBlueprint() {
    try {
      const [bp, genreData] = await Promise.all([
        api.get('/kb/step-blueprint', ctx.signal),
        api.get('/genres', ctx.signal).catch(() => ({genres: []})),
      ]);
      if (!ctx.alive()) return;
      const steps = bp.steps || [];
      const summary = bp.summary || {};
      const flatGenres = (genreData.genres || []).flatMap(g => [g, ...(g.children || [])]);
      const initialType = ctx.params?.get('type') || '';
      let audit = null;

      const renderAuditSummary = () => {
        const box = $('#handoffAuditSummary', blueprintPanel);
        if (!box) return;
        if (!audit) {
          box.innerHTML = '<p class="muted">选择小说类型后，将按工作流真实前置、世界来源、人物样本、段落技法与 AI 自动 7 大板块逐项体检拆解产物的下游接收状态。</p>';
          return;
        }
        const s = audit.summary || {};
        const auto = audit.auto_readiness || {};
        const orig = audit.originality_audit || {};
        box.innerHTML = `<div class="card stack">
          <div class="row spread wrap">
            <strong>下游接收体检结果 · ${esc((audit.types || []).map(t => t.name).join(' / ') || '全部类型')}</strong>
            <div class="row wrap">
              <span class="tag green">可接收方法 ${s.receivable_methods || 0}</span>
              ${s.blocked_methods ? `<span class="tag" style="color:var(--danger)">受阻 ${s.blocked_methods}</span>` : ''}
              <span class="tag blue">全书世界方法 ${s.book_world_ready ? '就绪' : '缺口'}</span>
              <span class="tag ${s.cast_sample_ready ? 'green' : ''}">人物样本 ${s.cast_sample_ready ? '已就绪' : '待补'}</span>
              <span class="tag ${s.passage_reference_count ? 'green' : ''}">段落技法 ${s.passage_reference_count || 0} 条</span>
            </div>
          </div>
          ${auto.checked ? `<div><strong>AI 自动 7 大板块就绪度（${auto.ready_count}/${auto.total_boards}）</strong>
            <div class="row wrap" style="margin-top:6px">${(auto.boards || []).map(b => `<span class="tag ${b.ready ? 'green' : ''}" title="${esc(b.ready ? `${b.route.scope_name}·${b.route.stage_name}` : (b.blocked_reasons || []).join('；'))}">${esc(b.label)} · ${b.ready ? `${esc(b.route.scope_name)}/${esc(b.route.stage_name)}` : '缺口'}</span>`).join('')}</div>
            ${!auto.ready ? `<p class="muted" style="margin-top:6px">缺口补齐建议：${(auto.boards || []).filter(b => !b.ready).map(b => `${esc(b.label)}（建议拆解 ${(b.suggested_domains || []).map(d => esc(d.name)).join('/')}${b.blocked_reasons?.length ? `；当前受阻：${esc(b.blocked_reasons[0])}` : ''}）`).join('；')}</p>` : ''}
          </div>` : ''}
          ${(orig.warnings || []).map(w => `<div class="notice warning">${esc(w.message)}</div>`).join('')}
        </div>`;
      };

      const renderList = group => {
        const auditByStep = audit ? Object.fromEntries((audit.steps || []).map(st => [st.step_id, st])) : {};
        const rows = steps.filter(s => {
          if (group === 'all') return true;
          if (group === 'gap') {
            const st = auditByStep[s.step_id];
            return st ? st.receivable_count === 0 : s.library_coverage?.status !== 'covered';
          }
          return s.phase_group.includes(group);
        });
        $('#blueprintList', blueprintPanel).innerHTML = rows.length
          ? rows.map(s => stepCard(s, auditByStep[s.step_id] || null, audit?.world_profile || null, audit?.character_profile || null, audit?.plot_profile || null, audit?.execution_profile || null, audit?.craft_profile || null)).join('')
          : '<p class="muted">该筛选下暂无步骤。</p>';
      };

      async function loadAudit(typeId) {
        const box = $('#handoffAuditSummary', blueprintPanel);
        if (!typeId) {
          audit = null;
          renderAuditSummary();
          renderList($('#blueprintFilter', blueprintPanel).value);
          return;
        }
        if (box) box.innerHTML = loading();
        try {
          audit = await api.get(`/kb/handoff-audit?types=${enc(typeId)}&planning_hierarchy=1`, ctx.signal);
          if (!ctx.alive()) return;
          renderAuditSummary();
          renderList($('#blueprintFilter', blueprintPanel).value);
        } catch (error) {
          if (!ctx.alive() || error.name === 'AbortError') return;
          if (box) box.innerHTML = `<p class="error">下游接收体检失败：${esc(error.message)}</p>`;
        }
      }

      blueprintPanel.innerHTML = `<div class="section-head"><h2>全流程步骤资料需求与拆解映射蓝图</h2>
        <span class="muted">共 ${summary.total_steps || steps.length} 步（${summary.design_steps || 14} 个设计步骤 + ${summary.execution_steps || 3} 个写审验收步骤） · 已覆盖拆解方法 ${summary.covered_steps || 0} 步</span></div>
        <div class="card"><strong>拆解方法论（以步骤需求驱动拆解）</strong>
          <div class="row wrap" style="margin-top:8px">${(bp.methodology || []).map(m => `<span class="tag blue">${esc(m.order)}. ${esc(m.name)}</span>`).join('')}</div>
          <p class="muted" style="margin-top:8px">拆解参考小说时先明确该观察服务哪一步，再分别判定「作用性（解决什么问题/效果）」与「方式性（具体操作与边界）」，最后绑定到对应步骤的方法产物字段。</p>
        </div>
        <div class="row wrap">
          <label class="field"><span>按小说类型做下游接收体检</span><select id="handoffAuditType">
            <option value="">不按类型（显示全库统计）</option>
            ${flatGenres.map(g => `<option value="${esc(g.id)}" ${initialType === g.id ? 'selected' : ''}>${g.parent_id ? '　' : ''}${esc(g.name)}</option>`).join('')}
          </select></label>
          <label class="field"><span>按阶段筛选</span><select id="blueprintFilter">
            <option value="all">全部 17 步</option>
            <option value="全书与细化共用">全书与细化共用（01–06）</option>
            <option value="卷/章/场细化专用">卷/章/场细化专用（07–13）</option>
            <option value="写作与验收">写作、审稿与验收（15–17）</option>
            <option value="gap">仅看尚未有可接收拆解方法的步骤</option>
          </select></label>
        </div>
        <div id="handoffAuditSummary"></div>
        <div id="blueprintList" class="stack"></div>`;
      $('#blueprintFilter', blueprintPanel).onchange = e => renderList(e.target.value);
      $('#handoffAuditType', blueprintPanel).onchange = e => loadAudit(e.target.value);
      if (initialType) await loadAudit(initialType);
      else { renderAuditSummary(); renderList('all'); }
    } catch (error) {
      if (!ctx.alive() || error.name === 'AbortError') return;
      blueprintPanel.innerHTML = `<p class="error">步骤蓝图读取失败：${esc(error.message)}</p>`;
    }
  }

  function renderJointPlan(jp) {
    if (!jp) return '<p class="muted">当前步骤召回单条或零条资料，无需多资料冲突协调。</p>';
    const bucket = (title, cls, arr) => `<div class="method-section">
      <div class="row spread wrap"><strong>${title}</strong><span class="tag ${cls}">${(arr || []).length} 条</span></div>
      <div class="row wrap" style="margin-top:6px;gap:6px">${(arr || []).length ? arr.map(k => `<span class="tag">${esc(k)}</span>`).join('') : '<span class="muted">无</span>'}</div>
    </div>`;
    return `<div class="card stack" id="jointRolePlanCard">
      <div class="row spread wrap">
        <strong>多资料联合分工方案（共协调 ${jp.total_sources || 0} 条资料）</strong>
        <span class="tag blue">优先级裁决生效</span>
      </div>
      <p class="muted" style="margin:0;font-size:12px"><strong>裁决铁律：</strong>${esc(jp.priority || '')}</p>
      <div class="stack" style="gap:8px">
        ${bucket('主驱动（Drivers · 直接负责本步核心目标生成）', 'green', jp.drivers)}
        ${bucket('硬边界与禁区（Boundaries · 仅作合法性与前置约束，禁止喧宾夺主）', 'amber', jp.boundaries)}
        ${bucket('具象锚点与表达辅助（Anchors & Expression · 落场与语言边界）', 'blue', jp.anchors_and_expression)}
        ${(jp.needs_instantiation_or_clause_guard || []).length ? bucket('需逐子句核对或本轮实例化的参考条', '', jp.needs_instantiation_or_clause_guard) : ''}
      </div>
      ${jp.creative_autonomy_rule ? `<div class="notice" style="font-size:12px"><strong>创作弹性与反套路守则：</strong>${esc(jp.creative_autonomy_rule)}</div>` : ''}
    </div>`;
  }

  async function read() {
    const current = ++sequence;
    const stage = select.value;
    const scope = scopeSelect.value;
    filter.disabled = true;
    target.innerHTML = loading();
    try {
      const [data, pipeBp] = await Promise.all([
        api.post('/pipeline/simulate', {
          scope,
          stage,
          brief_text: briefInput.value.trim(),
          constraints: constraintsInput.value.trim(),
          simulate_prior_products: true,
        }, ctx.signal),
        api.get(`/pipeline/blueprint?scope=${enc(scope)}`, ctx.signal).catch(() => null),
      ]);
      if (current !== sequence || !ctx.alive()) return;

      if (pipeBp) {
        const curStep = (pipeBp.design_steps || []).find(s => s.stage === stage);
        const rtSteps = pipeBp.runtime_steps || [];
        runtimeBox.innerHTML = `<details class="details">
          <summary><strong>查看当前层级运行契约与 15–17 写审验收提示词蓝图</strong>
            <span class="muted">（当前层级：${esc(scopeLabels[scope] || scope)} · 共 ${(pipeBp.design_steps || []).length} 个设计步 + ${rtSteps.length} 个运行环节）</span></summary>
          <div class="stack" style="margin-top:10px">
            ${pipeBp.priority_hierarchy ? `<p class="muted" style="font-size:12px;margin:0"><strong>全流程裁决优先级：</strong>${esc(pipeBp.priority_hierarchy)}</p>` : ''}
            ${curStep ? `<div class="card"><strong>${esc(stageNames[stage] || stage)} · 检索词与输出契约</strong>
              <p class="muted" style="margin:6px 0;font-size:12px"><strong>功能检索词：</strong>${esc((curStep.function_queries || []).join(' ｜ ') || '按步骤路由池直接供给')}</p>
              <p class="muted" style="margin:4px 0;font-size:12px"><strong>必产字段：</strong>${esc((curStep.output_fields || []).join('、') || '—')}</p>
            </div>` : ''}
            ${rtSteps.length ? `<div class="card"><strong>15–17 运行时环节与职责边界</strong>
              <div class="stack" style="margin-top:8px;gap:6px">${rtSteps.map(rt => `<div class="method-section">
                <div class="row spread wrap"><strong>${esc(rt.zh || rt.stage)}</strong><span class="tag">${rt.material_chars || 0} 字符规则</span></div>
                <p class="muted" style="margin:4px 0 0;font-size:12px;white-space:pre-wrap">${esc(rt.base_prompt || '')}</p>
              </div>`).join('')}</div>
            </div>` : ''}
          </div>
        </details>`;
      }

      const sources = data.sources || data.offered_sources || [];
      const rules = data.network_design_audit || [];
      const guards = data.anti_forgetting_guards || [];
      const ledger = data.continuity_ledger || null;
      const multiChar = data.multi_character_coordination || null;
      const unresolved = rules.filter(rule => rule.status === 'unresolved');

      if (!data.catalog_available && !sources.length && !rules.length) {
        target.innerHTML = empty('当前工作区尚未构建六大资料目录', '但跨步守卫与提示词骨架仍可核对。', '', 'layers');
        return;
      }

      function paint() {
        const ruleRows = filter.value === 'unresolved' ? unresolved : rules;
        const guardHtml = (guards.length || ledger || multiChar) ? `<div class="card stack">
          <strong>跨步防遗忘守卫与连续性台账</strong>
          ${guards.length ? `<ul style="margin:4px 0 0 18px;font-size:12px">${guards.map(g => `<li>${esc(g)}</li>`).join('')}</ul>` : ''}
          ${multiChar ? `<p class="muted" style="margin:4px 0 0;font-size:12px"><strong>多人物协调（${multiChar.characters_count || 0} 人）：</strong>${esc((multiChar.coordination_rules || []).join('；'))}</p>` : ''}
          ${ledger ? `<details class="details"><summary>展开上游交接连续性台账明细</summary><pre class="raw-data">${esc(JSON.stringify(ledger, null, 2))}</pre></details>` : ''}
        </div>` : '';

        const sourcesHtml = `<div class="card stack">
          <div class="row spread wrap">
            <strong>本步干跑实际召回资料（${sources.length} 条）</strong>
            ${data.queries_executed?.length ? `<span class="muted" style="font-size:12px">执行检索 ${data.queries_executed.length} 组</span>` : '<span class="muted" style="font-size:12px">步骤专属池精准供给</span>'}
          </div>
          ${sources.length ? `<div class="stack" style="gap:8px">${sources.slice(0, 30).map(s => `<div class="method-section">
            <div class="row spread wrap">
              <strong>${esc(s.key || s.id)}</strong>
              <div class="row wrap" style="gap:4px">
                <span class="tag blue">${esc(s.profile || 'general')}</span>
                <span class="tag ${s.source_state === 'design_ready' ? 'green' : 'amber'}">${esc(s.source_state || '')}</span>
                ${s.issues_count ? `<span class="tag">原义备注 ${s.issues_count}</span>` : ''}
              </div>
            </div>
            <p class="muted" style="margin:6px 0 0;font-size:12px;white-space:pre-wrap">${esc(s.step_use || s.meaning || s.original_preview || '')}</p>
          </div>`).join('')}</div>` : '<p class="muted">当前规划层级不包含此步骤或本步无需额外原始资料。</p>'}
        </div>`;

        const rulesHtml = rules.length ? `<div class="card stack">
          <div class="row spread wrap">
            <strong>${esc(stageNames[stage] || stage)} · 网络前置依赖核查（共 ${rules.length} 条）</strong>
            <span class="muted">有条件使用 ${rules.length - unresolved.length} 条 · 待核原义 ${unresolved.length} 条</span>
          </div>
          ${ruleRows.length ? ruleRows.map(ruleDetails).join('') : '<p class="muted">此步骤没有待核原义的条目。</p>'}
        </div>` : '';

        const promptHtml = data.rendered_prompt ? `<details class="details">
          <summary><strong>查看本步实际合成系统提示词（${data.rendered_prompt_chars || data.rendered_prompt.length} 字符）</strong></summary>
          <pre class="raw-data">${esc(data.rendered_prompt)}</pre>
        </details>` : '';

        target.innerHTML = `<div class="stack" style="gap:14px">
          ${renderJointPlan(data.joint_material_plan)}
          ${guardHtml}
          ${sourcesHtml}
          ${rulesHtml}
          ${promptHtml}
        </div>`;
      }

      filter.disabled = !rules.length;
      filter.onchange = paint;
      paint();
    } catch (error) {
      if (current !== sequence || !ctx.alive() || error.name === 'AbortError') return;
      target.innerHTML = empty('步骤资料暂时无法读取', error.message, '<button class="secondary" data-retry>重新读取</button>', 'alert');
      $('[data-retry]', target).onclick = read;
    }
  }

  select.onchange = read;
  scopeSelect.onchange = read;
  runBtn.onclick = read;
  await Promise.all([loadBlueprint(), read()]);
}
