import {api} from '../api.js';
import {$, esc, empty, loading} from '../ui.js';

const stageNames = {
  world_design: '世界设计', character_design: '人物设计', static_relations: '静态关系',
  plot_design: '剧情设计', event_design: '事件设计', action_design: '行动设计',
  scene_design: '场景设计', state_transition: '状态变化', state_propagation: '状态传播',
  anchor_design: '锚点设计', expression_design: '表达设计'
};

function ruleDetails(rule) {
  const fields = [
    ['原条条件', rule.condition],
    ['需要的前置', rule.needs],
    ['本步操作', rule.operation],
    ['核对前置的步骤', stageNames[rule.basis_stage] || rule.basis_stage],
    ['交接步骤', rule.status === 'unresolved' ? '待原义核清后再决定' : rule.consumers.map(key => stageNames[key] || key).join('、')],
    ['验收方法', rule.check]
  ];
  if (rule.blocked_reason) fields.push(['原义待核原因', rule.blocked_reason]);
  return `<details class="details" data-rule-key="${esc(rule.key)}">
    <summary><strong>${esc(rule.key)}</strong> · ${esc(rule.source)} → ${esc(rule.target)}
      <span class="muted">（${esc(rule.relation)}）</span>
      ${rule.status === 'unresolved' ? '<span class="tag">待核原义</span>' : ''}</summary>
    <dl>${fields.map(([name, value]) => `<dt><strong>${name}</strong></dt><dd>${esc(value)}</dd>`).join('')}</dl>
  </details>`;
}

export async function renderPrerequisites(ctx) {
  const root = $('#kbContent');
  root.innerHTML = `<div class="row wrap">
    <label class="field"><span>制作步骤</span><select id="prerequisiteStage">
      <option value="world_design">世界设计</option><option value="character_design">人物设计</option>
    </select></label>
    <label class="field"><span>原义状态</span><select id="prerequisiteStatus">
      <option value="all">全部条目</option><option value="unresolved">待核原义</option>
    </select></label>
  </div><div id="prerequisiteResults" aria-live="polite"></div>`;
  const select = $('#prerequisiteStage', root);
  const filter = $('#prerequisiteStatus', root);
  const target = $('#prerequisiteResults', root);
  let sequence = 0;

  async function read() {
    const current = ++sequence;
    const stage = select.value;
    filter.disabled = true;
    target.innerHTML = loading();
    try {
      const data = await api.post('/pipeline/simulate', {scope: 'book', stage, simulate_prior_products: true}, ctx.signal);
      if (current !== sequence || !ctx.alive()) return;
      const rules = data.network_design_audit || [];
      if (!data.catalog_available || !rules.length) {
        target.innerHTML = empty('当前样本没有可显示的前置记录', '请检查工作空间中的资料版本和步骤配置。', '', 'layers');
        return;
      }
      const unresolved = rules.filter(rule => rule.status === 'unresolved');
      function paint() {
        const rows = filter.value === 'unresolved' ? unresolved : rules;
        target.innerHTML = `<div class="section-head"><h3>${stageNames[stage]} · 共 ${rules.length} 条</h3>
          <span class="muted">有条件使用 ${rules.length - unresolved.length} 条 · 待核原义 ${unresolved.length} 条</span></div>`
          + (rows.length ? rows.map(ruleDetails).join('') : '<p class="muted">此步骤没有待核原义的条目。</p>');
      }
      filter.disabled = false;
      filter.onchange = paint;
      paint();
    } catch (error) {
      if (current !== sequence || !ctx.alive() || error.name === 'AbortError') return;
      target.innerHTML = empty('步骤资料暂时无法读取', error.message, '<button class="secondary" data-retry>重新读取</button>', 'alert');
      $('[data-retry]', target).onclick = read;
    }
  }

  select.onchange = read;
  await read();
}
