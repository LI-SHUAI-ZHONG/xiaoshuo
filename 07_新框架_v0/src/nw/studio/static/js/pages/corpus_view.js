import {$,$$,esc,drawer,number} from '../ui.js';

export const sectionNames={units:'卷章场目录',characters:'人物与归并',events:'事件因果节点',threads:'线索与人物弧光',links:'跨章关系',evidence:'原作证据',domains:'制作职责核对'};
export const stateNames={draft:'待审核',approved:'已批准',rejected:'已退回',source_unavailable:'来源不可用'};

export function analysisCatalogHtml(catalog,counts=null){
  const domains=Object.entries(catalog.domains);
  return `<section aria-label="现行拆解条目"><div class="section-head"><h2>现行拆解条目</h2><span class="muted">规格 v${esc(catalog.schema_version)} · ${domains.length} 项</span></div>
    ${domains.map(([id,name])=>`<details class="details" data-analysis-domain="${esc(id)}"><summary>${esc(name)}</summary>
      <ul>${Object.values(catalog.domain_details[id]).map(label=>`<li>${esc(label)}</li>`).join('')}</ul>
      ${id==='cast_roster'?`<p>全书地位：${Object.values(catalog.cast_roster_options.standing).map(esc).join('、')}。</p>
        <p>本章职责：${Object.values(catalog.cast_roster_options.function_kind).map(esc).join('、')}。</p>`:''}
      ${counts?(Object.hasOwn(counts,id)?`<button class="ghost" data-domain-observations="${esc(id)}">查看本书观察（${esc(counts[id])}）</button>`:'<p class="muted">本份旧分析未包含此项。</p>'):''}</details>`).join('')}</section>`;
}

export function castDistributionHtml(stats,record,catalog){
  if(!stats)return '<section class="card"><h3>人物数量、类型与逐章分布</h3><p>此份分析没有可核验的人物分布统计。</p></section>';
  const status=catalog.domain_statuses[stats.status]||'尚未核对';
  if(stats.unique_count==null)return `<section class="card"><h3>人物数量、类型与逐章分布</h3><p>${esc(status)}。补齐人物与章内事件的原文依据后可查看人数。</p></section>`;
  const labels=catalog.cast_roster_options;
  function breakdown(groups,names){
    return Object.entries(groups).filter(([,n])=>n>0).map(([k,n])=>`${esc(names[k]||k)} ${esc(n)}`).join('、')||'未登记';
  }
  const people=new Map(record.body.characters.map(c=>[c.id,c.name]));
  const names=ids=>ids.map(id=>people.has(id)?`<button class="ghost" data-cast-person="${esc(id)}">${esc(people.get(id))}</button>`:esc(id)).join('、');
  const countAndNames=(n,ids)=>`${esc(n)}${n?` · ${names(ids)}`:''}`;
  const observations=new Map(record.body.threads.map(t=>[t.id,t.title]));
  return `<section aria-label="人物数量与分布"><div class="section-head"><h3>人物数量、类型与逐章分布</h3></div>
    <p>覆盖文本内去重出场 ${esc(stats.unique_count)} 人 · 仅被提及 ${esc(stats.mentioned_only_count)} 人。</p>
    <p>人物地位：${breakdown(stats.positions,labels.standing)}。剧情职责：${breakdown(stats.functions,labels.function_kind)}。</p>
    <p class="muted">首次与再次出场以本次已核对的文本为准。同一人可承担多种职责，各类人数可重叠。</p>
    <div class="table-wrap"><table class="data-table"><thead><tr><th>章节</th><th>出场人物</th><th>本次首次</th><th>再次出场</th><th>仅被提及</th><th>人物地位与本章职责</th><th>观察依据</th></tr></thead><tbody>
    ${stats.chapters.map(c=>`<tr><td>${esc(c.title)}</td>${c.observed?`<td>${countAndNames(c.appearing_count,c.appearing_ids)}</td><td>${countAndNames(c.first_count,c.first_ids)}</td>
      <td>${esc(c.returning_count)}</td><td>${countAndNames(c.mentioned_only_count,c.mentioned_only_ids)}</td><td>${breakdown(c.positions,labels.standing)}<br>${breakdown(c.functions,labels.function_kind)}</td>
      <td>${(c.observation_ids||[]).map(id=>`<button class="ghost" data-chapter-observation="${esc(id)}">${esc(observations.get(id)||id)}</button>`).join(' ')}</td>`:'<td colspan="6">本章尚无可用于计数的观察</td>'}</tr>`).join('')}</tbody></table></div></section>`;
}

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
    const detailValue=key=>{
      const val=row.details[key];
      if(key==='claim_status')return catalog.narration_claims?.[val];
      if(row.domain==='cast_roster'){
        if(['appearance_evidence','standing_evidence'].includes(key))return doc.evidence.find(e=>e.id===val)?.quote;
        if(catalog.cast_roster_options[key])return catalog.cast_roster_options[key][val];
      }
      return val;
    };
    extra=`<div class="stack">${Object.entries(catalog.domain_details[row.domain]).map(([key,label])=>`<section class="design-card"><h3>${esc(label)}</h3><p>${esc(detailValue(key)||'原作未明确 / 待核实')}</p></section>`).join('')}</div>
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
