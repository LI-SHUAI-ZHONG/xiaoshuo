import {api, enc, query} from '../api.js';
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
  {key:'context_char_limit', label:'每次完整输入上限（字符）', min:1000, max:1000000, fallback:150000},
  {key:'output_limit', label:'每次最大输出（token）', min:128, max:100000, fallback:4096},
];

const fallbackTiers = [300000, 500000, 1000000, 1500000, 2000000].map(target_words => ({target_words}));
const tierName = value => `${number(value / 10000)} 万字`;
const chapterRange = '2,000–2,500 字';
const chapterEnding = '在此范围内写完当前段落，顺着场景或叙事节拍换章。';

export async function readTierRecommendation(types) {
  try {
    return await api.get(`/recommendations/length?${query({types})}`);
  } catch {
    return {status:'unavailable'};
  }
}

function interval(min, max) {
  if (!Number.isInteger(min) || !Number.isInteger(max)) return '';
  if (min % 10000 === 0 && (max + 1) % 10000 === 0) {
    return `${min / 10000} 万至不足 ${(max + 1) / 10000} 万字`;
  }
  if (min % 10000 === 0 && max % 10000 === 0) return `${min / 10000}–${max / 10000} 万字`;
  return `${number(min)}–${number(max)} 字`;
}

function recommendationText(data) {
  const outside = data?.outside_count ? `另有 ${number(data.outside_count)} 部在五档区间之外。` : '';
  switch (data?.status) {
    case 'recommended': {
      const votes = data.counts[data.recommended_tier];
      return `同类型完整拆解作品共 ${number(data.sample_count)} 部，${number(votes)} 部落在 ${tierName(data.recommended_tier)}档，在五档中最多。${outside}`;
    }
    case 'tied': return `同类型完整拆解作品共 ${number(data.sample_count)} 部，${data.leading_tiers.map(tierName).join('、')}档并列最多，各 ${number(data.counts[data.leading_tiers[0]])} 部。${outside}`;
    case 'no_samples': return '当前类型暂无可用于推荐篇幅的完整拆解作品。';
    case 'outside_tiers': return `同类型的 ${number(data.sample_count)} 部完整拆解作品均在五档区间之外。`;
    case 'no_types': return '选择作品类型后可查看拆解资料的篇幅推荐。';
    case 'unavailable': return '篇幅推荐暂时无法读取，仍可选择全书档位。';
    default: return '正在读取同类型作品的篇幅分布…';
  }
}

function tierOptions(plan, data) {
  const isMicro = plan.length_mode === 'micro_short';
  const options = (data?.tiers || fallbackTiers).map(tier => {
    const target = tier.target_words, recommended = target === data?.recommended_tier;
    const range = interval(tier.min_words, tier.max_words);
    return `<label class="length-tier"><input type="radio" name="bookTier" value="${target}"
      ${!isMicro && plan.target_words === target ? 'checked' : ''}><span><strong>${tierName(target)}</strong>
      ${recommended ? '<small class="length-recommended">推荐</small>' : ''}
      ${range ? `<small class="length-range">${esc(range)}</small>` : ''}</span></label>`;
  }).join('');
  return `<fieldset class="length-tiers" data-tier-mode><legend>小说总字数档位（含万字短篇快变现模式）</legend>
    <div class="length-tier-grid">
      <label class="length-tier"><input type="radio" name="bookTier" value="micro_short" ${isMicro ? 'checked' : ''}>
        <span><strong>1.5 万字短篇</strong><small class="length-recommended">快变现</small><small class="length-range">0.5–3万字 · 知乎盐言/番茄短故事</small></span></label>
      ${options}
      <label class="length-tier"><input type="radio" name="bookTier" value="" ${!isMicro && !plan.target_words ? 'checked' : ''}>
        <span><strong>由 AI 提出</strong><small class="length-range">在书纲中选择档位</small></span></label>
    </div><p class="muted" data-tier-evidence aria-live="polite">${isMicro ? '短篇快变现模式：4–10 节一次完结，前 300–500 字强导语钩子 + 约 3000 字免转付卡点，零多卷冗余。' : esc(recommendationText(data))}</p></fieldset>`;
}

function numberFields(plan, visibleFields) {
  return `<div class="form-grid">${visibleFields.map(({key,id,label,unit}) => {
    const percent = key === 'word_tolerance_pct';
    return `<label class="field"><span>${label}${percent ? '（%）' : ''}</span>
      <input type="number" step="1" id="${id}" name="${key}" data-length-field
        min="${percent ? '0' : '1'}" max="${percent ? '99' : '10000000'}" value="${esc(plan[key] ?? '')}"
        placeholder="${percent ? '默认 0' : unit === '字' && key !== 'target_words' ? '由 AI 按剧情分配' : '选填'}"></label>`;
  }).join('')}</div>`;
}

export function lengthFields(plan, recommendation, defaults = {}) {
  const tiered = plan.length_mode === 'tiered' || plan.length_mode === 'micro_short';
  const controls = tiered ? `${tierOptions(plan, recommendation)}
    <p class="length-chapter-rule"><strong>${plan.length_mode === 'micro_short' ? '单节 1,500–3,500 字（短篇快变现）' : `单章 ${chapterRange}`}</strong> · ${chapterEnding}</p>
    ${plan.length_mode === 'micro_short' ? '' : numberFields(plan, fields.filter(f => f.key === 'volume_count'))}` : numberFields(plan, fields);
  return `${controls}<details class="details"><summary>高级 · 模型调用预算</summary>
    <div class="form-grid">${limits.map(({key,label,min,max,fallback}) =>
      `<label class="field"><span>${label}</span><input name="${key}" type="number" step="1"
        min="${min}" max="${max}" data-budget-field value="${esc(plan.budget?.[key] ?? '')}"
        placeholder="默认 ${number(defaults[key] ?? fallback)}"></label>`).join('')}</div>
    <p class="muted">字符上限用于组装输入，输出按 token 预留。模型的实际窗口在 API 设置中填写。</p>
  </details>`;
}

export function readLengthFields(root) {
  const read = input => [input.name, input.value === '' ? null : Number(input.value)];
  const plan = Object.fromEntries([...root.querySelectorAll('[data-length-field]')].map(read));
  const tier = root.querySelector('[data-tier-mode] input:checked');
  if (tier) {
    if (tier.value === 'micro_short') Object.assign(plan, {length_mode:'micro_short', target_words:15000, chapter_count:6});
    else Object.assign(plan, {length_mode:'tiered', target_words:tier.value ? Number(tier.value) : null});
  }
  const budget = Object.fromEntries([...root.querySelectorAll('[data-budget-field]')].map(read)
    .filter(([,value]) => value != null));
  return {...plan, budget:Object.keys(budget).length ? budget : null};
}

export function lengthSummary(plan = {}, tiers = []) {
  if (plan.length_mode === 'micro_short') {
    return `<dt>篇幅模式</dt><dd><strong>短篇快变现（${number(plan.target_words || 15000)} 字 · 知乎盐言 / 番茄短故事）</strong></dd>
      <dt>短篇节拍</dt><dd>前 300–500 字强导语钩子 + 约 3,000 字免转付卡点 + 4–10 节反转闭环</dd>`;
  }
  const tiered = plan.length_mode === 'tiered';
  const visible = tiered ? fields.filter(f => f.key === 'volume_count') : fields;
  const words = visible.filter(({key}) => plan[key] != null && plan[key] !== '' &&
    (key !== 'word_tolerance_pct' || plan[key] > 0)).map(({key,label,unit}) =>
    `<dt>${label}</dt><dd>${number(plan[key])}${unit === '%' ? '%' : ' ' + unit}</dd>`).join('');
  const budget = limits.filter(({key}) => plan.budget?.[key] != null).map(({label,key}) =>
    `<dt>${label}</dt><dd>${number(plan.budget[key])}</dd>`).join('');
  if (!tiered) return words + budget;
  const tier = tiers.find(row => row.target_words === plan.target_words);
  const band = tier ? interval(tier.min_words, tier.max_words) : '';
  const choice = plan.target_words ? tierName(plan.target_words) : plan.effective_target_words
    ? `已批准书纲 · ${tierName(plan.effective_target_words)}档` : '由 AI 在书纲中提出';
  return `<dt>小说总字数档位</dt><dd>${choice}${band ? ' · ' + band : ''}</dd>
    <dt>单章篇幅</dt><dd>${chapterRange}，在完整段落处换章</dd>${words}${budget}`;
}

function chaptersTable(chapters = [], tiered = false) {
  const range = budget => budget ? `${number(budget.min_words)}–${number(budget.max_words)} 字` : '尚未分配';
  const cell = item => `<td>${item.budget ? number(item.budget.target_words) : '—'}</td>
    <td>${range(item.budget)}</td><td>${number(item.accepted_words)}</td><td>${esc(item.budget?.reason || '—')}</td>`;
  return chapters.length ? `<section><h3>章与场的篇幅</h3>${chapters.map(chapter => `
    <details class="details"><summary>第 ${number(chapter.index)} 章 · ${esc(chapter.title)}
      · ${range(chapter.budget)} · 已接受 ${number(chapter.accepted_words)} 字</summary>
      <div class="table-wrap"><table class="data-table"><thead><tr>
        <th>范围</th><th>${tiered ? '设计估算' : '目标字数'}</th><th>批准区间</th><th>已接受字数</th><th>分配依据</th></tr></thead>
        <tbody><tr><th scope="row">本章</th>${cell(chapter)}</tr>${(chapter.scenes || []).map(scene =>
          `<tr><th scope="row">第 ${number(scene.index)} 场</th>${cell(scene)}</tr>`).join('')}</tbody></table></div>
    </details>`).join('')}</section>` : '';
}

function editLengthPlan(plan, novel, onSaved) {
  const legacy = plan.length_mode !== 'tiered';
  const panel = drawer('调整后续制作篇幅', `<form class="stack" id="lengthPlanForm">
    <div data-length-controls>${lengthFields(plan)}</div>
    ${legacy ? '<button type="button" class="secondary" data-switch-tiers>改用全书档位与单章 2,000–2,500 字</button>' : ''}
    <p class="muted">设置用于后续制作。已批准的章场可重新设计。遇到上下文超限时，提高预算后可在制作台点“按已保存预算继续”。</p>
    <button class="button" type="submit">保存篇幅计划</button></form>`);
  const form = panel.querySelector('form'), controls = form.querySelector('[data-length-controls]');
  async function loadEvidence() {
    const data = await readTierRecommendation(novel.wizard?.genre_ids || []);
    const fieldset = controls.querySelector('[data-tier-mode]');
    if (fieldset && form.isConnected && panel.open) {
      // A response may arrive after the user has selected a different tier.
      const focused = fieldset.contains(document.activeElement);
      fieldset.outerHTML = tierOptions(readLengthFields(form), data);
      if (focused) controls.querySelector('[data-tier-mode] input:checked')?.focus();
    }
  }
  if (legacy) {
    form.querySelector('[data-switch-tiers]').onclick = event => {
      const values = readLengthFields(form);
      controls.innerHTML = lengthFields({...values, length_mode:'tiered', target_words:null}) +
        '<p class="muted">切换后，完稿时全书和已有章节都要满足新区间。已有正文可保留，超出范围的章节需调整。</p>';
      event.currentTarget.remove();
      loadEvidence();
    };
  } else loadEvidence();
  form.onsubmit = event => {
    event.preventDefault();
    const next = readLengthFields(form);
    const savedKeys = ['length_mode', ...fields.map(f => f.key)];
    const changes = Object.fromEntries(savedKeys.filter(key => key in next && next[key] !== (plan[key] ?? null))
      .map(key => [key,next[key]]));
    if (next.length_mode === 'tiered' && legacy) changes.target_words = next.target_words;
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
}

export function showLengthPlan(host, plan, novel, onSaved) {
  const tiered = plan.length_mode === 'tiered', target = plan.effective_target_words ?? plan.target_words;
  const delta = plan.delta_words;
  const targetLabel = tiered ? '全书完稿区间'
    : plan.target_words == null && target != null ? '全书目标 · 已批准书纲' : '全书目标';
  const metrics = [['主稿已接受', number(plan.accepted_words)],
    [targetLabel, tiered ? interval(plan.minimum_words, plan.maximum_words) : target == null ? '' : number(target)]];
  if (tiered && delta > 0) metrics.push(['超出区间', number(delta)]);
  else if (target != null) metrics.push([tiered ? '距区间下限' : '距目标剩余', number(plan.remaining_words)]);
  const gap = tiered ? (target != null && delta === 0 ? '已在全书完稿区间内' : '')
    : target != null && delta != null ? (delta > 0 ? `已超出目标 ${number(delta)} 字`
      : delta < 0 ? `低于目标 ${number(-delta)} 字` : '已达到目标字数') : '';
  host.innerHTML = `<section aria-label="作品篇幅计划">
    <div class="row spread wrap"><h2>篇幅计划</h2>${novel.status !== 'done'
      ? '<button type="button" class="secondary" id="editLengthPlan">调整篇幅</button>' : ''}</div>
    <div class="stat-grid">${metrics.map(([name,value]) => `<div class="card"><div class="stat-label">${name}</div>
      <div class="stat-value">${esc(value || '—')}</div></div>`).join('')}</div>
    <p class="muted">${gap ? esc(gap) + '。' : ''}主稿按已接受正文的非空白字符计数，含标点。</p>
    ${plan.effective_chapter_count && !plan.chapter_count ? `<p>已批准书纲${tiered ? '预计' : '计划'} ${number(plan.effective_chapter_count)} 章。</p>` : ''}
    ${plan.book_plan?.reason ? `<p>书纲分配依据 · ${esc(plan.book_plan.reason)}</p>` : ''}
    <dl class="selection-summary">${lengthSummary(plan)}</dl>
    ${target == null ? '<p>全书目标待设定或由 AI 在书纲中提出。</p>' : ''}
    ${!tiered && plan.minimum_words != null ? `<p class="muted">完稿最低字数 ${number(plan.minimum_words)} 字。超出目标会显示差额。</p>` : ''}
    ${chaptersTable(plan.chapters, tiered)}</section>`;
  const edit = host.querySelector('#editLengthPlan');
  if (edit) edit.onclick = () => editLengthPlan(plan, novel, onSaved);
}
