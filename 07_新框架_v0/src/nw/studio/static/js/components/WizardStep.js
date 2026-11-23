import {esc,icon} from '../ui.js';
export const STEPS = [{slot:'genre',name:'类型'},{slot:'tone',name:'风格'},{slot:'style',name:'文笔'},{slot:'narration',name:'写法'},{slot:'world',name:'世界观'},{slot:'character',name:'人物'},{slot:'structure',name:'结构篇幅'},{slot:'hook',name:'卖点'},{slot:'confirm',name:'确认'}];
export const slotName = slot => STEPS.find(x=>x.slot===slot)?.name || slot;
export function stepsBar(current) { return `<div class="wizard-steps">${STEPS.map((s,i)=>`<span class="wizard-step ${i===current?'current':i<current?'done':''}" ${i===current?'aria-current="step"':''}><b>${i<current?'✓':i+1}</b>${s.name}</span>`).join('')}</div>`; }
export function selectionLimit(count, max) {
  return `<p class="${count >= max ? 'warning' : 'muted'}" role="status">
    已选 ${count} 项，最多选 ${max} 项。${count >= max ? ' 已达上限，请先取消一项。' : ''}
  </p>`;
}
export function OptionCard(option, selected, limit) {
  const key = option.key || option.id, active = selected.includes(key), hasChildren = Boolean(option.children?.length);
  const disabled = !hasChildren && (option.selectable === false || !active && selected.length >= limit);
  return `<button class="option-card ${active ? 'selected' : ''}" data-option="${esc(key)}" ${disabled ? 'disabled' : ''}
    ${hasChildren ? 'aria-haspopup="dialog"' : `aria-pressed="${active}"`}>
    <div class="grow"><h3>${esc(option.name)}</h3><p>${esc(option.description || '查看并选择此创作偏好')}</p></div>
    ${icon(hasChildren ? 'chevron' : active ? 'check' : 'plus')}</button>`;
}
export function WizardStep({name, description, lengthPlan = '', methods = '', options = [], selected = [], limit}) {
  return `<h2>${esc(name)}</h2><p class="wizard-description">${esc(description)}</p>
    ${lengthPlan}${methods}
    <div class="section-head"><h3>创作偏好选项</h3></div>${selectionLimit(selected.length, limit)}
    <div class="option-grid">${options.map(option => OptionCard(option, selected, limit)).join('')}</div>
    ${!options.length ? '<p class="muted">这个板块暂无偏好选项，可在立项卡中补充。</p>' : ''}`;
}
