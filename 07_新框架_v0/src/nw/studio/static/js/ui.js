export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
export const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
export const short = (value, max = 110) => { const s = String(value ?? ''); return s.length > max ? `${s.slice(0,max)}…` : s; };
export const number = value => Number(value || 0).toLocaleString('zh-CN');
export const date = value => value ? new Date(value).toLocaleString('zh-CN', {month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}) : '尚无记录';
export const loading = () => '<div class="loading"><span class="loading-spinner"></span>正在读取工作空间</div>';
const paths = {
 home:'<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z"/>',
 pen:'<path d="m16 3 5 5-12 12-6 1 1-6Z"/><path d="m13 6 5 5M3 21l5-5"/>',
 library:'<path d="M4 3h4v18H4zM11 3h4v18h-4zM18 4l3-1 4 17-3 1z" transform="translate(-1 0)"/>',
 atlas:'<path d="m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2Z"/><path d="M9 3v16M15 5v16"/>',
 brain:'<path d="M12 4c-2-3-6-1-6 2-4 0-4 6-1 7-3 4 1 8 4 6 1 3 3 2 3 0V4Zm0 0c2-3 6-1 6 2 4 0 4 6 1 7 3 4-1 8-4 6-1 3-3 2-3 0"/><path d="m6 6 2 2M5 13l3-1m10-6-2 2m3 5-3-1"/>',
 inbox:'<path d="M4 3h16l2 13v5H2v-5Z"/><path d="M2 16h6l2 3h4l2-3h6M12 6v7m-3-3 3 3 3-3"/>',
 settings:'<path d="m9 3-1 3-3 1-2 4 2 2v4l3 2 3-1 3 3 4-2v-3l3-2-1-4-3-1-1-4Z"/><circle cx="12" cy="12" r="3"/>',
 search:'<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
 bell:'<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
 sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2"/>',
 panel:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/>',
 plus:'<path d="M12 5v14M5 12h14"/>',
 arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
 chevron:'<path d="m9 5 7 7-7 7"/>',
 book:'<path d="M4 3h15a1 1 0 0 1 1 1v17H5a3 3 0 0 1-3-3V5a2 2 0 0 1 2-2ZM2 17h18M6 3v14"/>',
 play:'<path d="m7 4 14 8-14 8Z"/>',
 pause:'<path d="M7 4v16M17 4v16"/>',
 clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
 check:'<path d="m5 12 4 4L20 5"/>',
 more:'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
 alert:'<path d="m12 3 10 18H2Z"/><path d="M12 9v5m0 3v1"/>',
 spark:'<path d="m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3Z"/>',
 refresh:'<path d="M20 8a9 9 0 0 0-15-3L2 8m0-6v6h6m-4 8a9 9 0 0 0 15 3l3-3m0 6v-6h-6"/>',
 file:'<path d="M5 2h9l5 5v15H5ZM14 2v6h5M8 12h8M8 16h8"/>',
 download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
 eye:'<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
 grid:'<path d="M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z"/>',
 list:'<path d="M8 5h13M8 12h13M8 19h13M3 5h1M3 12h1M3 19h1"/>',
 close:'<path d="m6 6 12 12M6 18 18 6"/>',
 info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v1"/>',
 terminal:'<path d="m4 6 6 6-6 6m10 0h7"/>',
 shield:'<path d="m12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6Z"/><path d="m8 12 3 3 5-6"/>',
 layers:'<path d="m2 8 10-6 10 6-10 6Zm0 5 10 6 10-6M2 18l10 6 10-6" transform="translate(0 -1)"/>'
};
export function icon(name, cls = '') { return `<svg class="${esc(cls)}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.file}</svg>`; }
export function empty(title, text, action = '', glyph = 'book') { return `<div class="empty-state"><div class="empty-art">${icon(glyph)}</div><h3>${esc(title)}</h3><p>${esc(text)}</p>${action}</div>`; }
export function button(label, action, primary = false, glyph = '') { return `<button class="${primary ? 'button' : 'secondary'}" data-action="${esc(action)}">${glyph ? icon(glyph) : ''}${esc(label)}</button>`; }
export function toast(message, error = false) { const div = document.createElement('div'); div.className = `toast-message${error ? ' error' : ''}`; div.textContent = message; $('#toastBanner').append(div); setTimeout(() => div.remove(), error ? 10000 : 5000); }
export function fail(error) {
  if (error?.name === 'AbortError') return;
  const ae = error?.data?.author_error;
  if (ae && ae.title) {
    const msg = `${ae.title}：${ae.summary || ''}${ae.action_hint ? `（建议：${ae.action_hint}）` : ''}`;
    toast(msg, true);
    return;
  }
  toast(error?.message || String(error), true);
}
export function modal(title, body, footer = '', full = false) { const el = $('#modalBackdrop'); $('#modalTitle').textContent = title; $('#modalBody').innerHTML = body; $('#modalFooter').innerHTML = footer; el.classList.toggle('fullscreen', full); if (!el.open) el.showModal(); return el; }
export function drawer(title, body) { $('#drawerTitle').textContent = title; $('#drawerBody').innerHTML = body; if (!$('#drawer').open) $('#drawer').showModal(); return $('#drawer'); }
export async function confirmAction(title, message, label = '确认') { return new Promise(resolve => { const d = modal(title, `<p>${esc(message)}</p>`, `<button class="secondary" data-close-modal>取消</button><button class="danger" id="confirmAction">${esc(label)}</button>`); const close = () => resolve(false); d.addEventListener('close', close, {once:true}); $('#confirmAction').onclick = () => { d.removeEventListener('close', close); d.close(); resolve(true); }; }); }
export function busy(button, action) { const before = button.innerHTML; button.disabled = true; button.innerHTML = '处理中…'; return Promise.resolve().then(action).catch(fail).finally(() => { if (button.isConnected) {button.disabled = false; button.innerHTML = before;} }); }
export function safeColor(value) { return /^#[0-9a-f]{6}$/i.test(value || '') ? value : '#526b9c'; }
export function readable(value, depth = 0) { if (value == null) return '<span class="muted">尚无记录</span>'; if (typeof value !== 'object') return `<p>${esc(({pass:'通过',revise:'需修订',reject:'未通过',approved:'已批准',pending:'待处理',done:'已完成',completed:'已完成',running:'进行中',failed:'失败',waiting:'待确认',public:'公开',private:'私有',known:'已知',unknown:'未知'}[String(value).toLowerCase()]||value))}</p>`; if (depth > 8) return '<p class="muted">更多嵌套内容可在高级原始记录中查看。</p>'; if (Array.isArray(value)) return value.map(v => typeof v==='object'?`<div class="design-card">${readable(v, depth+1)}</div>`:`<p>${esc(v)}</p>`).join('') || '<p class="muted">暂无条目</p>'; const rows=Object.entries(value).filter(([k]) => !k.startsWith('_')&&k!=='id'&&!k.endsWith('_id')&&!k.endsWith('_ids')&&!['hash','sha256','prompt','raw','request','input_snapshot','manifest','token','source_ref','source_key','priority_hierarchy','governance','option_key'].some(x => k.includes(x))); return rows.map(([k,v]) => depth>2&&typeof v==='object'?`<details class="details"><summary>${esc(labels[k]||k)}</summary><div>${readable(v,depth+1)}</div></details>`:`<div class="design-card"><h3>${esc(labels[k] || k)}</h3>${readable(v,depth+1)}</div>`).join('')||'<p class="muted">技术留痕可在高级原始记录中查看。</p>'; }
const labels = {reader_promise:'读者承诺',resistance:'阻力',unknowns:'未知信息',visibility:'可见范围',recommendation:'审稿结论',core_changes:'核心设定变化',material_checks:'资料落实',mechanism:'情节机制',stakes:'风险与代价',choice:'选择',cost:'代价',motivation:'动机',role:'角色职责',traits:'人物特征',relationships:'人物关系',world:'世界观',tone:'风格基调',style:'文笔',narration:'叙述方式',hook:'卖点钩子',structure:'叙事结构',constraints:'硬约束',idea:'故事构想',target_words:'目标字数',chapter_count:'计划章节',volume_count:'计划卷数',title:'标题',name:'名称',summary:'摘要',description:'描述',reason:'原因',status:'状态',issues:'问题',findings:'发现',conclusion:'结论',content:'内容',text:'正文',character:'人物',characters:'人物',setting:'设定',goal:'目标',conflict:'冲突',outcome:'结果',pov:'视角',scene:'场景',scenes:'场景',chapter:'章节',chapters:'章节',notes:'说明',review:'审稿',evidence:'证据',decision:'决定',warnings:'告警',materials:'资料落实',stage:'步骤',scope:'范围',type_selection:'类型选择',world_design:'世界观设计'};
