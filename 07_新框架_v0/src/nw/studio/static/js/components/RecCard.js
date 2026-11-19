import {esc,icon} from '../ui.js';
export function RecCard(item, index, selected = []) {
  if (!item) return `<div class="rec-card empty">${icon('spark')}<span>等待拆解数据补充</span><small>有真实用法，才有推荐</small></div>`;
  return `<div class="rec-card ${selected.includes(item.option_key) ? 'selected' : ''}"><div class="row spread"><span class="rec-rank">TOP 0${index+1}</span>${item.level !== 'exact' ? '<span class="tag">同主类型参考</span>' : ''}</div><button class="rec-pick" data-rec="${esc(item.option_key)}">${esc(item.name || item.option_key)}</button><div class="rec-count">用法 ${Number(item.corpus_count || 0)} · 采用 ${Number(item.adopt_count || 0)}</div><small>来自 ${(item.books || []).length} 本已入库作品</small>${(item.examples || []).length ? `<details><summary>查看示例与来源</summary>${item.examples.map(e=>`<p class="evidence">${esc(e.quote || e.text)}</p>`).join('')}<p>${(item.books || []).map(b=>esc(b.title)).join('、')}</p></details>`:''}</div>`;
}
