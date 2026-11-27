import {esc,icon} from '../ui.js';

export const STEPS = [
  {slot:'genre', stage:'01–02', name:'类型'},
  {slot:'world', stage:'03', name:'世界观'},
  {slot:'character', stage:'04–05', name:'人物'},
  {slot:'structure', stage:'06', name:'结构篇幅'},
  {slot:'hook', stage:'06–07', name:'卖点'},
  {slot:'narration', stage:'09/12/13', name:'写法'},
  {slot:'tone', stage:'13', name:'风格'},
  {slot:'style', stage:'13', name:'文笔'},
  {slot:'confirm', stage:'立项', name:'确认'},
];

export const slotName = slot => STEPS.find(x => x.slot === slot)?.name || slot;

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
  return `<button class="option-card ${active || pickedInside ? 'selected' : ''}" data-option="${esc(key)}" ${disabled ? 'disabled' : ''}
    ${hasChildren ? 'aria-haspopup="dialog"' : `aria-pressed="${active}"`}>
    <div class="grow">
      <h3>${esc(option.name)}${option.target_stage_label ? `<span class="tag" style="font-size:11px;margin-left:6px">${esc(option.target_stage_label)}</span>` : ''}${relevanceBadge(option)}${pickedInside ? `<span class="tag green" style="font-size:11px;margin-left:6px">已选 ${pickedInside}</span>` : ''}</h3>
      <p>${esc(option.description || '查看并选择此创作偏好')}${childCount ? `（共 ${childCount} 项）` : ''}</p>
    </div>
    ${icon(hasChildren ? 'chevron' : active ? 'check' : 'plus')}</button>`;
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
      <p class="muted" style="margin:8px 0 12px">以下资料分类在当前主副类型中非常规配置；仅在你的故事明确引入跨题材要素时展开选用，避免跨类型规则污染。</p>
      <div class="option-grid">${guardedOptions.map(option => OptionCard(option, selected, limit)).join('')}</div>
    </details>` : ''}
    ${!options.length ? '<p class="muted">这个板块暂无偏好选项，可在立项卡中补充。</p>' : ''}`;
}
