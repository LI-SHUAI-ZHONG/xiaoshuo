import {api, enc, query} from '../api.js';
import {esc} from '../ui.js';

export const readCastSamples = (types, signal) => api.get(`/recommendations/cast?${query({types})}`, signal);

function people(range) {
  if (!range) return '样本不足';
  return range.min === range.max ? `${esc(range.min)} 人` : `${esc(range.min)}–${esc(range.max)} 人`;
}

function roleTable(title, ranges, labels, unit = '每部完整作品的人数') {
  const rows = Object.entries(ranges).filter(([,range]) => range != null);
  if (!rows.length) return '';
  return `<details class="details"><summary>${title}</summary>
    <table class="data-table"><thead><tr><th>角色类别</th><th>${unit}</th></tr></thead>
    <tbody>${rows.map(([key,range]) => `<tr><td>${esc(labels[key] || key)}</td><td>${people(range)}</td></tr>`).join('')}</tbody></table></details>`;
}

function chapterBands(data) {
  const labels = {opening:'前段', middle:'中段', ending:'后段'};
  const bands = Object.entries(data.chapter_bands).filter(([,band]) => band.chapter_count);
  if (!bands.length) return '<p class="muted">还没有可按前、中、后段比较的多章完整作品。</p>';
  return `<details class="details"><summary>各章段的出场分布</summary>
    <p class="muted">完整作品按原书章序分成三段，表中为每章观察到的人数。</p>
    <table class="data-table"><thead><tr><th>章段</th><th>样本章数</th><th>出场</th><th>初次出场</th><th>再次出场</th></tr></thead>
    <tbody>${bands.map(([key,band]) => `<tr><td>${labels[key]}</td><td>${esc(band.chapter_count)}</td><td>${people(band.appearing)}</td><td>${people(band.first)}</td><td>${people(band.returning)}</td></tr>`).join('')}</tbody></table>
    ${bands.map(([key,band]) => roleTable(labels[key]+'每章的人物地位', band.positions, data.position_labels, '每章人数')
      + roleTable(labels[key]+'每章的剧情作用', band.functions, data.function_labels, '每章人数')).join('')}</details>`;
}

function coverageNotes(source) {
  if (!source.coverage_gaps?.length) return '';
  return `<ul>${source.coverage_gaps.map(gap => {
    const detail = gap.coverage === 'unassessed' ? '尚未核实本章'
      : `待核人物 ${esc(gap.pending_individual_count)} 人，待核观察 ${esc(gap.pending_observation_count)} 条`;
    const unknown = gap.unidentified_observation_count ? `，其中 ${esc(gap.unidentified_observation_count)} 条尚未确定个体归属` : '';
    return `<li>第 ${esc(gap.chapter_index)} 章 · 已确认出场 ${esc(gap.confirmed_appearing)} 人 · ${detail}${unknown}</li>`;
  }).join('')}</ul>`;
}

export function castSamplesHtml(data, {keepWizard = false} = {}) {
  const title = '<h3>同类型作品的人物阵容</h3>';
  if (!data.sample_count) {
    return `<section class="method-section" aria-label="同类型作品的人物阵容">${title}
      <p>已确认的阵容样本为 0 部。导入并审核对应类型的作品、核实人物在各章的出场后即可比较。</p></section>`;
  }
  const chapter = data.chapter_ranges;
  const extents = {complete:'完整作品', excerpt:'节选', unknown:'完整范围待确认'};
  return `<section class="method-section" aria-label="同类型作品的人物阵容">${title}
    <p>匹配 ${esc(data.sample_count)} 部作品，${esc(data.chapter_count)} 章可比较人数，其中全书逐章核实 ${esc(data.complete_count)} 部。</p>
    ${data.uncertainty?.chapter_count ? `<p>另有 ${esc(data.uncertainty.source_count)} 部作品共 ${esc(data.uncertainty.chapter_count)} 章待核。下方范围只计已核实的样本，来源详情列出待核章节。</p>` : ''}
    <dl class="selection-summary"><dt>单部作品出场人数（去重）</dt><dd>${people(data.book_range)}</dd>
      <dt>每章出场</dt><dd>${people(chapter.appearing)}</dd>
      <dt>每章在样本中初次出场</dt><dd>${people(chapter.first)}</dd>
      <dt>每章再次出场</dt><dd>${people(chapter.returning)}</dd></dl>
    ${roleTable('按人物在全书中的地位比较', data.position_ranges, data.position_labels)}
    ${roleTable('按人物承担的剧情作用比较', data.function_ranges, data.function_labels)}
    ${data.category_sample_counts && (data.category_sample_counts.positions < data.complete_count || data.category_sample_counts.functions < data.complete_count)
      ? `<p>部分作品有未定的人物地位或职责。可比较地位 ${esc(data.category_sample_counts.positions)} 部，可比较职责 ${esc(data.category_sample_counts.functions)} 部。</p>` : ''}
    ${chapterBands(data)}
    <p class="muted">${data.complete_count === 1 ? '仅一部可作全书比较，人数反映该部作品的做法。'
      : data.complete_count ? '这些范围来自已核实的出场记录。本书按剧情需要安排角色。'
      : '全书人数和角色类别范围需有完整且逐章核实的作品。'}</p>
    <details class="details"><summary>查阅来源作品</summary><ul>${data.sources.map(source =>
      `<li><a class="text-link" href="#/staging/${enc(source.book_id)}?tab=distribution&amp;version=${enc(source.version)}" ${keepWizard ? 'target="_blank" rel="noopener"' : ''}>${esc(source.title)} · 修订 ${esc(source.version)}</a>
        · ${esc(extents[source.extent] || source.extent)} · ${esc(source.chapter_count)} 章可比较 · 已确认出场 ${esc(source.unique_count)} 人
        · ${source.included_in_book_range ? '计入全书比较' : '全书上限未确定'}
        ${coverageNotes(source)}</li>`).join('')}</ul></details>
    </section>`;
}
