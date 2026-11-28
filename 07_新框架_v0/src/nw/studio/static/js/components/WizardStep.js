import {esc,icon} from '../ui.js';

// Streamlined 4-step Manual Creation Wizard aligned to creative-workflow-v1.
// Mandatory universal craft foundations (protagonist/supporting cast, character relations,
// world baseline, 3-act/golden-3/foreshadowing, event gates, POV/anchors/review redlines)
// are enforced automatically by the built-in 15,375 rules and never clutter manual selection.
export const STEPS = [
  {id:'genre', slot:'genre', stage:'题材篇幅', name:'题材与篇幅'},
  {id:'architecture', slot:'structure', stage:'架构卖点', name:'架构与卖点'},
  {id:'craft', slot:'style', stage:'场景视角', name:'视角与文风'},
  {id:'confirm', slot:'confirm', stage:'确认开写', name:'构想与开写'},
];

const SLOT_NAMES = {
  genre:'类型', world:'特殊世界机制', character:'特色人物机制', structure:'叙事结构',
  hook:'核心推进机制', narration:'叙事视角与时序', tone:'语气基调', style:'文风质感', confirm:'构想与开写',
};

export const slotName = slot => SLOT_NAMES[slot] || STEPS.find(x => x.slot === slot)?.name || slot;

export function stepsBar(current) {
  return `<div class="wizard-steps">${STEPS.map((s, i) => `<span class="wizard-step ${i === current ? 'current' : i < current ? 'done' : ''}" ${i === current ? 'aria-current="step"' : ''} title="对应工作流 ${esc(s.stage || '')}"><b>${i < current ? '✓' : i + 1}</b>${esc(s.name)}${s.stage ? `<small class="faint" style="margin-left:3px">${esc(s.stage)}</small>` : ''}</span>`).join('')}</div>`;
}

export function selectionLimit(count, max) {
  return `<p class="${count >= max ? 'warning' : 'muted'}" role="status">
    已选 ${count} 项，最多选 ${max} 项。${count >= max ? ' 已达上限，请先取消一项。' : ''}
  </p>`;
}

function relevanceBadge(option) {
  if (!option.relevance_label) return '';
  const cls = option.relevance === 'primary' ? 'green' : option.relevance === 'optional' ? 'blue' : '';
  return `<span class="tag ${cls}" style="font-size:11px;margin-left:6px">${esc(option.relevance_label)}</span>`;
}

export function OptionCard(option, selected, limit) {
  const key = option.key || option.id;
  const active = selected.includes(key);
  const hasChildren = Boolean(option.children?.length);
  const childCount = hasChildren ? option.children.length : 0;
  const pickedInside = hasChildren ? option.children.filter(c => selected.includes(c.key || c.id)).length : 0;
  const disabled = !hasChildren && (option.selectable === false || (!active && selected.length >= limit));
  return `<button type="button" class="option-card ${active || pickedInside ? 'selected' : ''}" data-option="${esc(key)}" data-slot="${esc(option.slot || '')}" ${disabled ? 'disabled' : ''}
    ${hasChildren ? 'aria-haspopup="dialog"' : `aria-pressed="${active}"`}>
    <div class="grow">
      <h3>${esc(option.name)}${option.target_stage_label ? `<span class="tag" style="font-size:11px;margin-left:6px">${esc(option.target_stage_label)}</span>` : ''}${option.category_label ? `<span class="tag" style="font-size:11px;margin-left:6px">${esc(option.category_label)}</span>` : ''}${relevanceBadge(option)}${pickedInside ? `<span class="tag green" style="font-size:11px;margin-left:6px">已选 ${pickedInside}</span>` : ''}</h3>
      <p>${esc(option.description || '选择此创作偏好')}${childCount ? `（共 ${childCount} 项）` : ''}</p>
    </div>
    ${icon(hasChildren ? 'chevron' : active ? 'check' : 'plus')}</button>`;
}

export function autoCapabilitiesHtml(capabilities = [], genreScope = null) {
  if (!capabilities?.length) return '';
  const excluded = genreScope?.world_excluded_domains || [];
  const resources = genreScope?.world_resources?.preferred_resources || [];
  return `<details class="details" id="wizardAutoCapabilities" style="margin-top:14px">
    <summary><strong>引擎自动保障的基础写作能力（已按所选题材自动生效，无需手动勾选 · ${capabilities.length} 大核心域）</strong></summary>
    <div class="stack" style="margin-top:10px;gap:8px">
      <p class="muted">主角/配角防工具化、人物关系网、基础世界观规则、黄金三章/伏笔回收、受限 POV 与审稿红线均属于小说写作必选底座，由内置 15,375 条工作流规则自动执行，不再占用你的手动勾选时间。</p>
      ${resources.length ? `<p class="muted"><strong>本类型自动激活资源口径</strong>：${esc(resources.join('、'))}${excluded.length ? ` ｜ <strong>自动隔离跨题材污染</strong>：${esc(excluded.join('、'))}` : ''}</p>` : ''}
      <div class="option-grid">${capabilities.map(cap => `<article class="card" style="padding:10px 12px">
        <div class="row spread wrap"><strong>${esc(cap.title)}</strong><span class="tag green">${esc(cap.stage_label || '自动生效')}</span></div>
        <p class="muted" style="margin-top:6px">${esc(cap.summary)}</p>
      </article>`).join('')}</div>
    </div>
  </details>`;
}

export function FlatOptionSection({id = '', title, hint = '', items = [], selectedForSlot, limitForSlot, collapsedAll = false}) {
  if (!items.length) return '';
  const activeItems = items.filter(item => item.relevance !== 'out_of_scope');
  const guardedItems = items.filter(item => item.relevance === 'out_of_scope');
  const pickedCount = items.filter(item => selectedForSlot(item.slot).includes(item.key)).length;
  const renderGrid = list => `<div class="option-grid">${list.map(item => OptionCard(item, selectedForSlot(item.slot), limitForSlot(item.slot))).join('')}</div>`;
  const inner = `
    ${hint ? `<p class="muted" style="margin:4px 0 10px">${esc(hint)}</p>` : ''}
    ${activeItems.length ? renderGrid(activeItems) : '<p class="muted">当前主副类型下此组无常规推荐项；如需跨题材引入请展开下方扩展区。</p>'}
    ${guardedItems.length ? `<details class="details" id="outOfScopeOptions${id ? '_' + esc(id) : ''}" style="margin-top:12px">
      <summary>跨题材扩展项（非当前类型常规配置，按需展开 · ${guardedItems.length} 项）</summary>
      <div style="margin-top:8px">${renderGrid(guardedItems)}</div>
    </details>` : ''}`;
  if (collapsedAll) {
    return `<details class="details" ${id ? `id="${esc(id)}"` : ''} ${pickedCount ? 'open' : ''} style="margin-top:14px">
      <summary><strong>${esc(title)}</strong>${pickedCount ? ` <span class="tag green">已选 ${pickedCount} 项</span>` : ' <span class="muted">（可选 · 无特殊机制可直接跳过）</span>'}</summary>
      <div style="margin-top:10px">${inner}</div>
    </details>`;
  }
  return `<section class="stack" ${id ? `id="${esc(id)}"` : ''} style="margin-top:16px">
    <div class="row spread wrap"><h3>${esc(title)}</h3>${pickedCount ? `<span class="tag green">已选 ${pickedCount} 项</span>` : '<span class="muted">可选，不选则由工作流按本类型自动展开</span>'}</div>
    ${inner}
  </section>`;
}

export function WizardStep({name, stage = '', description, stepGuide = '', lengthPlan = '', methods = '', options = [], selected = [], limit}) {
  const activeOptions = options.filter(option => option.relevance !== 'out_of_scope');
  const guardedOptions = options.filter(option => option.relevance === 'out_of_scope');
  return `<div class="row spread wrap"><h2>${esc(name)}</h2>${stage ? `<span class="tag blue">对应工作流 ${esc(stage)}</span>` : ''}</div>
    <p class="wizard-description">${esc(description)}</p>
    ${stepGuide}${lengthPlan}${methods}
    <div class="section-head"><h3>创作偏好选项</h3></div>${selectionLimit(selected.length, limit)}
    <div class="option-grid">${activeOptions.map(option => OptionCard(option, selected, limit)).join('')}</div>
    ${guardedOptions.length ? `<details class="details" id="outOfScopeOptions" style="margin-top:16px">
      <summary>跨类型扩展选项（非当前所选类型常规项，按需展开 · ${guardedOptions.length} 组）</summary>
      <div class="option-grid">${guardedOptions.map(option => OptionCard(option, selected, limit)).join('')}</div>
    </details>` : ''}`;
}
