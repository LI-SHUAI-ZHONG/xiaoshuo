import {api, enc} from '../api.js';
import {busy, drawer, esc, number, toast} from '../ui.js';

const fields = [
  {key:'target_words', id:'targetWords', label:'目标总字数', unit:'字'},
  {key:'chapter_count', id:'chapterCount', label:'计划章节数', unit:'章'},
  {key:'volume_count', id:'volumeCount', label:'计划卷数', unit:'卷'},
  {key:'chapter_target_words', id:'chapterTargetWords', label:'每章参考字数', unit:'字'},
  {key:'scene_target_words', id:'sceneTargetWords', label:'每场参考字数', unit:'字'},
  {key:'word_tolerance_pct', id:'wordTolerancePct', label:'全书允许少写', unit:'%'},
];

const limits = [
  {key:'context_char_limit', label:'每次完整输入上限（字符）', min:1000, max:1000000, fallback:64000},
  {key:'output_limit', label:'每次最大输出（token）', min:128, max:100000, fallback:4096},
];

export function lengthFields(plan = {}) {
  return `<div class="form-grid">${fields.map(({key,id,label,unit}) => {
    const percent = key === 'word_tolerance_pct';
    return `<label class="field"><span>${label}${percent ? '（%）' : ''}</span>
      <input type="number" step="1" id="${id}" name="${key}" data-length-field
        min="${percent ? '0' : '1'}" max="${percent ? '99' : '10000000'}" value="${esc(plan[key] ?? '')}"
        placeholder="${percent ? '默认 0' : unit === '字' && key !== 'target_words' ? '由 AI 按剧情分配' : '选填'}"></label>`;
  }).join('')}</div>
    <details class="details"><summary>高级 · 模型调用预算</summary>
      <div class="form-grid">${limits.map(({key,label,min,max,fallback}) =>
        `<label class="field"><span>${label}</span><input name="${key}" type="number" step="1"
          min="${min}" max="${max}" data-budget-field value="${esc(plan.budget?.[key] ?? '')}"
          placeholder="默认 ${number(fallback)}"></label>`).join('')}</div>
      <p class="muted">字符上限用于组装输入，输出按 token 预留。模型的实际窗口在 API 设置中填写。</p>
    </details>`;
}

export function readLengthFields(root) {
  const read = input => [input.name, input.value === '' ? null : Number(input.value)];
  const plan = Object.fromEntries([...root.querySelectorAll('[data-length-field]')].map(read));
  const budget = Object.fromEntries([...root.querySelectorAll('[data-budget-field]')].map(read)
    .filter(([,value]) => value != null));
  return {...plan, budget:Object.keys(budget).length ? budget : null};
}

export function lengthSummary(plan = {}) {
  const words = fields.filter(({key}) => plan[key] != null && plan[key] !== '' &&
    (key !== 'word_tolerance_pct' || plan[key] > 0)).map(({key,label,unit}) =>
    `<dt>${label}</dt><dd>${number(plan[key])}${unit === '%' ? '%' : ' ' + unit}</dd>`).join('');
  const budget = limits.filter(({key}) => plan.budget?.[key] != null).map(({label,key}) =>
    `<dt>${label}</dt><dd>${number(plan.budget[key])}</dd>`).join('');
  return words + budget;
}

function chaptersTable(chapters = []) {
  const range = budget => budget ? `${number(budget.min_words)}–${number(budget.max_words)} 字` : '尚未分配';
  const cell = item => `<td>${item.budget ? number(item.budget.target_words) : '—'}</td>
    <td>${range(item.budget)}</td><td>${number(item.accepted_words)}</td><td>${esc(item.budget?.reason || '—')}</td>`;
  return chapters.length ? `<section><h3>章与场的篇幅</h3>${chapters.map(chapter => `
    <details class="details"><summary>第 ${number(chapter.index)} 章 · ${esc(chapter.title)}
      · ${range(chapter.budget)} · 已接受 ${number(chapter.accepted_words)} 字</summary>
      <div class="table-wrap"><table class="data-table"><thead><tr>
        <th>范围</th><th>目标字数</th><th>批准区间</th><th>已接受字数</th><th>分配依据</th></tr></thead>
        <tbody><tr><th scope="row">本章</th>${cell(chapter)}</tr>${(chapter.scenes || []).map(scene =>
          `<tr><th scope="row">第 ${number(scene.index)} 场</th>${cell(scene)}</tr>`).join('')}</tbody></table></div>
    </details>`).join('')}</section>` : '';
}

export function showLengthPlan(host, plan, novel, onSaved) {
  const target = plan.effective_target_words ?? plan.target_words, delta = plan.delta_words;
  const targetLabel = plan.target_words == null && target != null ? '全书目标 · 已批准书纲' : '全书目标';
  const metrics = [['主稿已接受', plan.accepted_words], [targetLabel, target]];
  if (target != null) metrics.push(['距目标剩余', plan.remaining_words]);
  const gap = target != null && delta != null ? (delta > 0 ? `已超出目标 ${number(delta)} 字`
    : delta < 0 ? `低于目标 ${number(-delta)} 字` : '已达到目标字数') : '';
  const summary = lengthSummary(plan);
  host.innerHTML = `<section aria-label="作品篇幅计划">
    <div class="row spread wrap"><h2>篇幅计划</h2>${novel.status !== 'done'
      ? '<button type="button" class="secondary" id="editLengthPlan">调整篇幅</button>' : ''}</div>
    <div class="stat-grid">${metrics.map(([name,value]) => `<div class="card"><div class="stat-label">${name}</div>
      <div class="stat-value">${value == null ? '—' : number(value)}</div></div>`).join('')}</div>
    <p class="muted">${gap ? esc(gap) + '。' : ''}主稿按已接受正文的非空白字符计数，含标点。</p>
    ${plan.effective_chapter_count && !plan.chapter_count ? `<p>已批准书纲计划 ${number(plan.effective_chapter_count)} 章。</p>` : ''}
    ${plan.book_plan?.reason ? `<p>书纲分配依据 · ${esc(plan.book_plan.reason)}</p>` : ''}
    ${summary ? `<dl class="selection-summary">${summary}</dl>` : ''}
    ${target == null ? '<p>全书目标待设定或由 AI 在书纲中提出。</p>' : ''}
    ${plan.minimum_words != null ? `<p class="muted">完稿最低字数 ${number(plan.minimum_words)} 字。超出目标会显示差额。</p>` : ''}
    ${chaptersTable(plan.chapters)}</section>`;
  const edit = host.querySelector('#editLengthPlan');
  if (edit) edit.onclick = () => {
    const panel = drawer('调整后续制作篇幅', `<form class="stack" id="lengthPlanForm">
      ${lengthFields(plan)}
      <p class="muted">单章、单场留空，由 AI 依剧情分配。保存后用于新任务。遇到上下文超限时，提高可用预算后可在制作台点“按已保存预算继续”。其他已冻结的任务需取消后重建才能使用新预算。章纲或场景可通过重新设计调整。</p>
      <button class="button" type="submit">保存篇幅计划</button></form>`);
    const form = panel.querySelector('form');
    form.onsubmit = event => {
      event.preventDefault();
      const next = readLengthFields(form);
      const changes = Object.fromEntries(fields.filter(({key}) => next[key] !== (plan[key] ?? null))
        .map(({key}) => [key,next[key]]));
      const budgetChanges = limits.filter(({key}) => (next.budget?.[key] ?? null) !== (plan.budget?.[key] ?? null));
      if (budgetChanges.length) changes.budget = next.budget && Object.fromEntries(
        budgetChanges.map(({key}) => [key, next.budget[key] ?? null]));
      if (!Object.keys(changes).length) { panel.close(); return; }
      busy(form.querySelector('[type=submit]'), async () => {
        const result = await api.post(`/novels/${enc(novel.id)}/length`, changes);
        if (form.isConnected && panel.open) panel.close();
        onSaved(result.length_plan);
        toast('后续制作篇幅已保存');
      });
    };
  };
}
