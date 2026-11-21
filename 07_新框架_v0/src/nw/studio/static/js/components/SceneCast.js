import {esc} from '../ui.js';

const bands = {opening:'前段', middle:'中段', ending:'后段', unknown:'章段待定'};
const appearances = {first:'计划首次出场', returning:'计划再次出场', unknown:'既往出场待核'};
const metrics = {appearing:'出场人数', first:'首次出场', returning:'再次出场'};

function metricLabel(key, labels) {
  const [kind, category] = key.split('.');
  return metrics[key] || labels?.[kind]?.[category] || key;
}

export function SceneCast(cast) {
  if (!cast) return '';
  const plan = cast.plan, accepted = cast.accepted;
  const parts = [];
  if (plan) {
    const range = plan.appearing_range;
    const partial = plan.reference_scope === 'partial';
    let sample = partial ? '本次只规划部分场景' : '尚无可核实的人数范围';
    if (range) {
      const count = range.min === range.max ? range.min : range.min + '–' + range.max;
      sample = (plan.reference_scope === 'band' ? '同类作品该章段' : '同类作品整体') + '每章出场 ' + count + ' 人';
    }
    parts.push(`<h4>第${esc(plan.chapter)}章用人安排</h4>
      <p class="muted">${esc(bands[plan.band] || '章段待定')} · ${esc(sample)} · ${partial ? '本次' : '本章'}安排 ${plan.people.length} 人</p>
      <p>${esc(plan.reason)}</p>
      ${plan.differences?.length ? `<p>与样本范围有差异的项目　${plan.differences.map(k=>esc(metricLabel(k, cast.labels))).join('、')}</p>` : ''}
      ${plan.people.map(person => `<details class="details"><summary>${esc(person.name)} · ${esc(appearances[person.appearance] || '既往出场待核')}</summary>
        <p>${(person.functions || []).map(k=>esc(cast.labels?.functions?.[k] || k)).join('、')}</p><p>${esc(person.reason)}</p></details>`).join('')}`);
  }
  if (accepted) {
    parts.push(`<h4>本场已接受稿的人物</h4>
      ${accepted.complete ? '' : '<p class="muted">这版稿件的出场名单尚未核全。</p>'}
      ${accepted.people.map(person => `<details class="details"><summary>${esc(person.name)} · ${person.presence === 'onstage' ? '实际出场' : '仅被提及'}</summary><p>${esc(person.reason)}</p><blockquote>${esc(person.quote)}</blockquote></details>`).join('')}
      ${accepted.complete && !accepted.people.length ? '<p>本场没有核实到可辨认的个人。</p>' : ''}`);
  }
  return parts.length ? `<section class="inspector-section">${parts.join('')}</section>` : '';
}
