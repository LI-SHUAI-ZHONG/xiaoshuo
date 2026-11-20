import {$,$$,esc,drawer,number} from '../ui.js';

export const sectionNames={units:'卷章场目录',characters:'人物与归并',events:'事件因果节点',threads:'线索与人物弧光',links:'跨章关系',evidence:'原作证据',domains:'制作职责核对'};
export const stateNames={draft:'待审核',approved:'已批准',rejected:'已退回',source_unavailable:'来源不可用'};

export function sourceDrawer(book,unit){
  const text=Array.from(book.text).slice(unit.start,unit.end).join('');
  drawer(unit.title||'原作范围',`<p class="muted">字符 ${unit.start}–${unit.end} · ${number(unit.end-unit.start)} 字符。位置按Unicode字符计算。</p><textarea readonly rows="22" class="corpus-source" aria-label="所选范围原作">${esc(text)}</textarea>`);
}

export function recordDrawer(section,row,record,catalog){
  const doc=record.body;
  const eventName=id=>doc.events.find(e=>e.id===id)?.summary||id;
  const evidence=doc.evidence.filter(e=>(row.evidence_ids||[]).includes(e.id));
  let extra='';
  if(section==='threads'){
    extra=`<div class="stack">${Object.entries(catalog.domain_details[row.domain]).map(([key,label])=>`<section class="design-card"><h3>${esc(label)}</h3><p>${esc(row.details[key]||'原作未明确 / 待核实')}</p></section>`).join('')}</div>
      <div class="section-head"><h3>对应实际事件序列</h3></div>${row.node_ids.map(id=>{const e=doc.events.find(x=>x.id===id);return e?`<section class="card"><h3>${esc(e.summary)}</h3><p class="muted">${esc(e.id)} · ${catalog.granularity[e.granularity]}</p>${['goal','conflict','choice','cost','result','information_before','information_after','emotion_before','emotion_after'].map(key=>`<p><strong>${esc(catalog.row_fields.events[key])}：</strong>${esc(e[key]||'原作未明确 / 待核')}</p>`).join('')}</section>`:`<p class="error">引用缺失：${esc(id)}</p>`;}).join('')}`;
  }
  const fields=catalog.row_fields[section];
  drawer(row.title||row.name||row.summary||sectionNames[section],`<div class="stack">${Object.entries(fields).filter(([key])=>key!=='details'&&key!=='evidence_ids').map(([key,label])=>{
    let value=row[key];if(section==='links'&&['source','target'].includes(key))value=eventName(value);
    if(Array.isArray(value))value=value.join('、');
    return `<div class="design-card"><h3>${esc(label)}</h3><p>${esc(value??'未知')}</p></div>`;
  }).join('')}${extra}<div class="section-head"><h3>原作证据</h3></div>${evidence.map(e=>`<blockquote class="evidence">${esc(e.quote)}</blockquote><p>${esc(e.explanation)}</p><small class="muted">${esc(e.id)} · 字符 ${e.start}–${e.end}</small>`).join('')||'<p class="muted">没有已定位证据</p>'}</div>`);
}

export function recordsHtml(rows,section,record,catalog,canEdit){
  const doc=record.body;
  const label=row=>row.title||row.name||row.summary||row.quote||catalog.domains[row.domain]||row.id;
  return rows.map((row,index)=>`<article class="card corpus-record"><div class="row spread wrap"><h3>${esc(label(row))}</h3>
    <span class="tag">${section==='units'?catalog.levels[row.level]:section==='events'?catalog.granularity[row.granularity]:section==='threads'?catalog.domains[row.domain]:section==='links'?catalog.link_kinds[row.kind]:sectionNames[section]}</span></div>
    ${section==='links'?`<p>${esc(doc.events.find(e=>e.id===row.source)?.summary||row.source)} → ${esc(doc.events.find(e=>e.id===row.target)?.summary||row.target)}</p>`:''}
    <p class="muted">${esc(row.explanation||row.summary||row.role||row.initial_state||'')}${row.status?' · '+esc(catalog.thread_statuses[row.status]||catalog.domain_statuses[row.status]||row.status):''}</p>
    <div class="row spread wrap"><small class="muted">${esc(row.id||row.domain)}${row.start!=null?` · 字符 ${row.start}–${row.end}`:''}${row.evidence_ids?` · ${row.evidence_ids.length} 处证据`:''}</small>
    <div class="row"><button class="ghost" data-corpus-detail="${index}">${section==='units'?'阅读原作':'查看分析与证据'}</button>${canEdit?`<button class="secondary" data-corpus-edit="${index}">编辑</button>`:''}</div></div></article>`).join('');
}
