import {esc,icon} from '../ui.js';
const states={pending:'○',not_started:'○',running:'◐',in_progress:'◐',done:'✓',completed:'✓',succeeded:'✓',waiting:'⚠',waiting_gate:'⚠',needs_confirmation:'⚠',blocked:'⚠',failed:'×',error:'×',paused:'Ⅱ',cancelled:'Ⅱ',revise:'↻',rejected:'↶'};
export function statusIcon(status) { const cls = ['running','in_progress'].includes(status) ? 'running spin' : ['done','completed','succeeded'].includes(status) ? 'success' : ['failed','error'].includes(status) ? 'error' : ['waiting','waiting_gate','needs_confirmation','blocked'].includes(status) ? 'warning' : 'muted'; return `<span class="state-icon ${cls}">${states[status] || '○'}</span>`; }
export function ProgressTree(nodes = [], selected = '') { return `<div class="tree">${nodes.map(n=>node(n,selected)).join('')}</div>`; }
function renderChildren(children, selected) {
  let html = '', lastGroup = '';
  for (const child of children) {
    if (child.group_label && child.group_label !== lastGroup) {
      lastGroup = child.group_label;
      html += `<div class="faint" style="font-size:11px;padding:8px 8px 2px;font-weight:600">${esc(lastGroup)}</div>`;
    }
    html += node(child, selected);
  }
  return html;
}
function autoContractsHtml(items, selected) {
  if (!Array.isArray(items) || !items.length) return '';
  const allDone = items.every(c => c.status === 'done');
  return `<details class="details" style="margin:4px 0 6px;font-size:12px" data-auto-contracts>
    <summary style="padding:4px 8px;cursor:pointer" class="muted">${statusIcon(allDone ? 'done' : 'pending')} 已自动继承/冻结前置契约（${items.length} 项 · 免重复判定）</summary>
    <div class="tree-children" style="margin-top:4px">${items.map(c => node(c, selected)).join('')}</div>
  </details>`;
}
function node(n, selected) { const segments=n.segments?`<small class="scene-segments">${[['write','写'],['review','审'],['accept','收']].map(([key,label])=>`<span class="${n.segments[key]?'success':'faint'}">${label}${n.segments[key]?'✓':'○'}</span>`).join(' ')}</small>`:''; const body=`${statusIcon(n.status)}<span class="grow">${esc(n.label || n.name || n.id)}${segments}</span>`; return (n.children?.length || n.auto_contracts?.length) ? `<details open data-tree="${esc(n.id)}"><summary>${icon('chevron')}${body}</summary><div class="tree-children">${autoContractsHtml(n.auto_contracts, selected)}${renderChildren(n.children || [], selected)}</div></details>` : `<button class="tree-button ${n.id===selected?'selected':''}" data-node="${esc(n.id)}">${body}</button>`; }
export function flattenTree(nodes = []) { return nodes.flatMap(n=>[n,...flattenTree(n.auto_contracts || []),...flattenTree(n.children || [])]); }
