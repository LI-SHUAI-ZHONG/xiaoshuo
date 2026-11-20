import {esc,icon} from '../ui.js';
import {RecCard} from './RecCard.js';
export const STEPS = [{slot:'genre',name:'类型'},{slot:'tone',name:'风格'},{slot:'style',name:'文笔'},{slot:'narration',name:'写法'},{slot:'world',name:'世界观'},{slot:'character',name:'人物'},{slot:'structure',name:'结构篇幅'},{slot:'hook',name:'卖点'},{slot:'confirm',name:'确认'}];
export const slotName = slot => STEPS.find(x=>x.slot===slot)?.name || slot;
export function stepsBar(current) { return `<div class="wizard-steps">${STEPS.map((s,i)=>`<span class="wizard-step ${i===current?'current':i<current?'done':''}" ${i===current?'aria-current="step"':''}><b>${i<current?'✓':i+1}</b>${s.name}</span>`).join('')}</div>`; }
export function OptionCard(option, selected = []) { const key = option.key || option.id; return `<button class="option-card ${selected.includes(key)?'selected':''}" data-option="${esc(key)}"><div class="grow"><h3>${esc(option.name)}</h3><p>${esc(option.description || '查看并选择此创作偏好')}</p></div>${icon(option.children?.length ? 'chevron' : selected.includes(key) ? 'check' : 'plus')}</button>`; }
export function WizardStep({name, description, methods = '', recommendations = [], options = [], selected = []}) {
  const recs = recommendations.filter(Boolean);
  return `<h2>${esc(name)}</h2><p class="wizard-description">${esc(description)}</p>
    ${methods}
    ${recs.length ? `<details class="details"><summary>选项用法参考</summary><div class="rec-grid">${recs.map((row, index) => RecCard(row, index, selected)).join('')}</div></details>` : ''}
    <div class="section-head"><h3>创作偏好选项</h3></div>
    <div class="option-grid">${options.map(option => OptionCard(option, selected)).join('')}</div>
    ${!options.length ? '<p class="muted">这个板块暂无偏好选项，可在立项卡中补充。</p>' : ''}`;
}
