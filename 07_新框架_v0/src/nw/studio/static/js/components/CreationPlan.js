import {enc} from '../api.js';
import {esc} from '../ui.js';
import {lengthSummary} from './LengthPlan.js';
import {slotName} from './WizardStep.js';

const stageNames = {
  type_selection:'立项类型契约（自动冻结）', type_adaptation:'多类型融合适配（单类型自动）', world_design:'世界规则定稿',
  character_design:'核心人物定稿', static_relations:'人物关系张力', plot_design:'故事大纲与卷章切分',
  event_design:'本章事件链', action_design:'行动博弈与代价', scene_design:'场景卡与POV',
  state_transition:'场内状态变化', state_propagation:'状态连锁传播', anchor_design:'具象动作锚点',
  expression_design:'叙述与表达指导', bind_scope:'可写场景工作包',
};
const scopeNames = {book:'全书', volume:'卷纲', chapter:'章场', scene:'场景'};
const stages = keys => keys.map(key => stageNames[key] || key).join('、');
const location = ({scope, stage, scope_name, stage_name}) =>
  [scope_name || scopeNames[scope], stage_name || stageNames[stage] || stage].filter(Boolean).join(' · ');

function methodLink(method) {
  const label = esc(method.title || method.id);
  return `<a class="text-link" href="#/kb/items?method=${esc(enc(method.id))}&amp;version=${esc(enc(method.version))}">${label} · v${esc(method.version)}</a>`;
}

function typeDetails(row) {
  const label = `${esc(row.name || row.id)} <span class="muted"> ·
    ${row.version ? `知识库 v${esc(row.version)}` : '步骤原有定义'}</span>`;
  return row.definition ? `<details class="details"><summary>${label}</summary>
    <p class="prose">${esc(row.definition)}</p></details>` : `<p>${label}</p>`;
}

function preferenceDetails(row) {
  const source = row.source_ref || {};
  const locator = [source.file, source.section || (source.original_line ? `原行 ${source.original_line}` : '')]
    .filter(Boolean).join(' · ');
  return `<details class="details"><summary>${esc(slotName(row.slot))} · ${esc(row.name || row.id)}</summary>
    <p class="muted">负责步骤　${esc(stages(row.stages))}</p>
    ${row.meaning ? `<p class="prose">${esc(row.meaning)}</p>` : ''}
    ${row.step_use ? `<p class="prose">${esc(row.step_use)}</p>` : ''}
    ${locator ? `<p class="muted">来源　${esc(locator)}</p>` : ''}</details>`;
}

export function creationPlan(plan, wizard) {
  const {types, preferences, references, recommendations, preference_interactions: interactions} = plan;
  const length = lengthSummary(wizard);
  const preferenceNames = new Map(preferences.map(row => [row.key, row.name || row.id]));
  return `<div class="section-head"><h3>立项方案</h3>
    <span class="tag">${plan.mode === 'auto' ? 'AI 自动' : '人工选择'}</span></div>
    <section class="card stack">
      <h4>所选类型与知识版本</h4>
      ${types.map(typeDetails).join('')}
      ${length ? `<dl class="selection-summary">${length}</dl>` : ''}
      ${plan.mode === 'manual' && !preferences.length ? '<p class="muted">未勾选创作偏好，具体方案由各制作步骤设计。</p>' : ''}
    </section>
    ${plan.constraints ? `<section class="method-section stack"><h4>作者硬约束</h4>
      <p class="prose">${esc(plan.constraints)}</p></section>` : ''}
    ${preferences.length ? `<section class="method-section"><h4>创作偏好</h4>
      <p class="muted">由负责步骤按本书需要判断采用方式。</p>
      ${preferences.map(preferenceDetails).join('')}
      ${interactions.map(row => `<div class="details"><h5>${row.keys.map(key => esc(preferenceNames.get(key) || key)).join('、')}</h5>
        <p class="muted">${esc(stages(row.stages))}</p><p>${esc(row.guidance)}</p></div>`).join('')}
    </section>` : ''}
    ${references.length ? `<section class="method-section stack"><h4>作者勾选的参考方法</h4>
      ${references.map(row => `<div><p>${esc(slotName(row.slot))} · ${methodLink(row)}</p>
        <p class="muted">${esc(row.uses.map(use => use.conditions?.length
          ? location(use) + '（' + use.conditions.join('、') + '）' : location(use)).join('、'))}</p></div>`).join('')}
    </section>` : ''}
    ${recommendations.length ? `<section class="method-section stack"><h4>AI 自动推荐候选</h4>
      <p class="muted">这里记录立项时核定的候选版本。采用结果以相应步骤的设计和使用回执为准。</p>
      ${recommendations.map(row => `<div><p><strong>${esc(slotName(row.slot))}</strong> · ${esc(location(row))}</p>
        <p>${row.candidates.map(methodLink).join('、')}</p></div>`).join('')}
    </section>` : ''}`;
}
