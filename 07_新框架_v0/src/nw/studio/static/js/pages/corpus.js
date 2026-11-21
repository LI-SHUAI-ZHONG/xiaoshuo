import {api,enc} from '../api.js';
import {$,$$,esc,empty,loading,drawer,modal,busy,toast,fail} from '../ui.js';
import {openCorpusEditor,openCorpusReview} from './corpus_editor.js';
import {openCorpusRun,openCorpusResume,jobState,phaseName} from './corpus_jobs.js';
import {analysisCatalogHtml,castDistributionHtml,recordsHtml,recordDrawer,sourceDrawer,sectionNames,stateNames} from './corpus_view.js';

export async function renderCorpus(ctx,book){
  const root=`/staging/${enc(book.id)}/corpus`;
  const latestCatalog=await api.get('/corpus/catalog',ctx.signal);if(!ctx.alive())return;
  const requestedTab=ctx.params.get('tab');
  let record,catalog,tab=['overview','distribution',...Object.keys(sectionNames)].includes(requestedTab)?requestedTab:'overview';
  let page=0,search='',unitFilter='',domainFilter='',timer,stopped=false,shownJob='',jobDetail=null;
  ctx.onCleanup(()=>{stopped=true;clearTimeout(timer);});
  const history=book.items?.length;
  ctx.sidebar('参考作品结构',[['staging','返回预存库','inbox'],[`staging/${enc(book.id)}?view=source`,'作品分类与原文','book'],
    ...(history?[[`staging/${enc(book.id)}?view=legacy`,'历史局部标注','file']]:[]),['kb/decomposition','现行拆解条目','list'],['kb/items','制作方法','layers']],
    '<strong>先看整本关系，再提炼方法</strong>原文观察、分析推断与方法分别审核。文本完整性由作者声明，不按篇幅猜测。');
  function loadLatest(){
    if(ctx.params.has('version')){location.hash=`#/staging/${enc(book.id)}?view=structure`;return;}
    return load();
  }
  function editor(section,row=null){openCorpusEditor({book,catalog:latestCatalog,record,section,row,initialDomain:domainFilter,reload:loadLatest});}
  const active=()=>record.jobs.some(j=>['running','pending'].includes(j.status));
  async function load(){
    if(stopped||!ctx.alive())return;clearTimeout(timer);
    record=await api.get(`${root}${ctx.params.get('version')?'?version='+enc(ctx.params.get('version')):''}`,ctx.signal);
    if(stopped||!ctx.alive())return;
    catalog=record.body.schema_version===latestCatalog.schema_version?latestCatalog:
      await api.get(`/corpus/catalog?version=${enc(record.body.schema_version)}`,ctx.signal);
    if(stopped||!ctx.alive())return;
    paint();await paintJobs();
    if(active())timer=setTimeout(poll,1500);
  }
  async function poll(){
    if(stopped||!ctx.alive())return;
    try{
      const before=record.jobs.map(j=>`${j.id}:${j.status}`).join('|');
      record.jobs=(await api.get(root+'/jobs',ctx.signal)).jobs;
      const after=record.jobs.map(j=>`${j.id}:${j.status}`).join('|');
      if(before!==after&&!active()){await load();return;}
      await paintJobs();if(active())timer=setTimeout(poll,1500);
    }catch(error){fail(error);if(!stopped)timer=setTimeout(poll,3000);}
  }
  function paint(){
    const latest=record.version===record.latest_version,canEdit=record.initialized&&latest&&!active()&&book.status!=='rejected';
    const currentSchema=record.body.schema_version===latestCatalog.schema_version;
    const canStart=book.status!=='rejected'&&!active();
    const canDerive=currentSchema&&record.available&&record.version===record.approved_version&&!active();
    const errors=record.issues.filter(i=>i.severity==='error'),warnings=record.issues.filter(i=>i.severity!=='error');
    ctx.content.innerHTML=`<div class="page"><div class="page-heading"><div><div class="eyebrow">SOURCE · STRUCTURE · METHODS</div><h1>${esc(book.title)}</h1><p class="page-description">全书总览 → 卷章场细拆 → 跨章关系 → 可复用方法</p></div><a class="secondary" href="#/staging">返回预存库</a></div>
      <div class="row wrap corpus-toolbar"><span class="tag blue">${record.initialized?`${stateNames[record.status]||record.status} · 版本 ${record.version}`:'尚未建立结构'}</span><span class="tag">${esc(catalog.source_extents[record.body.source_extent.status])}</span>
      <span class="tag">本份分析规格 v${esc(record.body.schema_version)} · ${Object.keys(catalog.domains).length} 项</span>
      <span class="muted">${record.body.events.length} 个实际事件 · ${record.body.threads.length} 条拆解观察 · ${record.body.links.length} 条关系</span>
      ${record.history.length?`<select id="corpusVersion" aria-label="拆解版本">${record.history.map(v=>`<option value="${v.version}" ${v.version===record.version?'selected':''}>版本 ${v.version} · ${v.decision==='approve'?'已批准':v.decision==='reject'?'已退回':'待审核'}</option>`).join('')}</select>`:''}</div>
      <p class="notice">请按原文位置核对规则、事件因果和适用边界。方法单独审核后，项目可按前置需求和已选类型生成设计卡。</p>
      ${!currentSchema?`<p class="notice">当前规格 v${esc(latestCatalog.schema_version)} 有 ${Object.keys(latestCatalog.domains).length} 项。此份旧分析保留原记录。重新拆解原文，或在最新修订中补齐各项观察并审核后，可继续提炼。</p>`:''}
      <div class="row wrap corpus-toolbar">${!record.initialized&&canStart?'<button class="secondary" id="initializeCorpus">人工建立目录</button>':''}<button class="button" id="startCorpus" ${canStart?'':'disabled'}>多层自动拆解</button>
      ${canEdit?'<button class="secondary" id="editCorpusExtent">核对文本完整性</button>':''}
      ${canEdit&&currentSchema&&!record.review?'<button class="secondary" id="reviewCorpus">审核当前结构</button>':''}
      <button class="secondary" id="extractCorpusMethods" ${canDerive?'':'disabled'}>自动提炼方法</button><button class="secondary" id="manualCorpusMethod" ${canDerive?'':'disabled'}>手工提炼方法草稿</button></div>
      ${!latest?'<p class="notice">正在查看历史版本。切换最新版本后编辑；提炼使用当前批准版本。</p>':''}
      <div id="corpusJobPanel"></div>
      ${record.initialized?`<details class="details" ${errors.length?'open':''}><summary>结构核对：${errors.length} 项阻断 · ${warnings.length} 项待核</summary>${record.issues.map(i=>`<p class="${i.severity==='error'?'error':'muted'}">${esc(i.message)}</p>`).join('')||'<p class="muted">结构与引用检查没有发现阻断；这不是文学质量评分。</p>'}</details>`:''}
      <div class="tabs corpus-tabs">${[['overview','全书总览'],['distribution','逐章进展、人物与线索分布'],...Object.entries(sectionNames)].map(([id,name])=>`<button data-corpus-tab="${id}" class="${tab===id?'active':''}">${name}</button>`).join('')}</div>
      <div id="corpusSection"></div></div>`;
    $$('[data-corpus-tab]').forEach(b=>b.onclick=()=>{tab=b.dataset.corpusTab;page=0;search='';unitFilter='';domainFilter='';paintSection(canEdit);$$('[data-corpus-tab]').forEach(t=>t.classList.toggle('active',t===b));});
    $('#startCorpus').onclick=()=>openCorpusRun({book,record,catalog:latestCatalog,reload:loadLatest});
    $('#extractCorpusMethods').onclick=()=>openCorpusRun({book,record,catalog,reload:loadLatest,kind:'methods'});
    $('#editCorpusExtent')?.addEventListener('click',()=>editor('source_extent',record.body.source_extent));
    $('#reviewCorpus')?.addEventListener('click',()=>openCorpusReview({book,record,reload:loadLatest}));
    if($('#corpusVersion'))$('#corpusVersion').onchange=e=>{location.hash=`#/staging/${enc(book.id)}?view=structure&version=${e.target.value}`;};
    $('#initializeCorpus')?.addEventListener('click',()=>{
      modal('建立原文目录',`<form id="initializeCorpusForm" class="stack"><p class="notice">只按原文标题和范围建立目录，不生成剧情或方法。</p><label class="field"><span>文本完整性</span><select name="extent">${Object.entries(catalog.source_extents).map(([id,name])=>`<option value="${id}" ${id==='unknown'?'selected':''}>${esc(name)}</option>`).join('')}</select></label><label class="field"><span>作者核对依据</span><textarea name="note" required rows="3"></textarea></label><button class="button" type="submit">建立待分析目录</button></form>`);
      $('#initializeCorpusForm').onsubmit=e=>{e.preventDefault();busy(e.target.querySelector('button'),async()=>{
        await api.post(root+'/initialize',{extent:$('[name=extent]',e.target).value,note:$('[name=note]',e.target).value,expected_version:0});$('#modalBackdrop').close();await load();
      });};
    });
    $('#manualCorpusMethod').onclick=()=>{
      modal('选择方法依据',`<form id="manualFromCorpus" class="stack"><p class="notice">只复制实际结构依据和证据，具体方法仍须由作者归纳并补齐八类要求。</p><select name="thread" aria-label="手工提炼依据">${record.body.threads.map(t=>`<option value="${esc(t.id)}">${esc(catalog.domains[t.domain])} · ${esc(t.title)}</option>`).join('')}</select><button class="button" type="submit">建立待补齐方法草稿</button></form>`);
      $('#manualFromCorpus').onsubmit=e=>{e.preventDefault();busy(e.target.querySelector('button'),async()=>{
        const result=await api.post(root+'/methods',{version:record.version,thread_ids:[$('[name=thread]',e.target).value]});
        $('#modalBackdrop').close();location.hash=`#/kb/items?method=${enc(result.id)}`;
      });};
    };
    paintSection(canEdit);
  }
  function paintSection(canEdit){
    if(tab==='distribution'){
      const stats=record.statistics;
      const threads=new Map(record.body.threads.map(t=>[t.id,t]));
      const showProgress=record.body.schema_version>=4;
      const observations=ids=>(ids||[]).map(id=>{
        const t=threads.get(id);
        return `<button class="ghost" data-chapter-observation="${esc(id)}">${esc(t.title)}${t.status==='uncertain'?'（存疑）':''}</button>`;
      }).join('<br>')||'未登记';
      $('#corpusSection').innerHTML=`<p class="notice">${esc(stats.counting_basis)}机器通读 ${stats.survey.characters}/${stats.survey.total} 字符，细拆 ${stats.detail.characters}/${stats.detail.total}；人工确认 ${stats.manual_reviewed_units.length} 个章节范围。</p>
        ${castDistributionHtml(stats.cast_distribution,record,catalog)}
        <div class="table-wrap"><table class="data-table"><thead><tr><th>当前目录范围</th><th>细节事件</th>${showProgress?'<th>剧情进展</th><th>人物出场与交集</th>':''}<th>钩子引入 / 回应</th><th>伏笔埋设 / 提示 / 回收</th><th>情绪前后</th></tr></thead><tbody>${stats.chapter_ranges.map(r=>`<tr><td>${esc(r.title)}</td><td>${r.detail_events.length}</td>${showProgress?`<td>${observations(r.chapter_progress)}</td><td>${observations(r.cast_entry)}</td>`:''}<td>${r.hook_opens.length} / ${r.hook_responses.length}</td><td>${r.foreshadow_plants.length} / ${r.foreshadow_hints.length} / ${r.foreshadow_payoffs.length}</td><td>${r.emotional_transitions.map(e=>`${esc(e.before||'未明确')} → ${esc(e.after||'未明确')}`).join('<br>')||'未登记'}</td></tr>`).join('')}</tbody></table></div><p class="muted">尚未闭合或存疑的线索：${stats.open_thread_ids.map(esc).join('、')||'没有登记；仍需作者核对是否找全。'}</p>`;
      $$('[data-chapter-observation]').forEach(b=>b.onclick=()=>recordDrawer('threads',threads.get(b.dataset.chapterObservation),record,catalog));
      $$('[data-cast-person]').forEach(b=>b.onclick=()=>recordDrawer('characters',record.body.characters.find(c=>c.id===b.dataset.castPerson),record,catalog));
      return;
    }
    if(tab==='overview'){
      $('#corpusSection').innerHTML=`<div class="stack">${analysisCatalogHtml(latestCatalog,record.statistics.thread_counts)}${Object.entries(catalog.overview_fields).map(([id,label])=>`<section class="card"><h3>${label}</h3><p class="corpus-text">${esc(record.body.overview[id]||'尚未形成全书总览')}</p></section>`).join('')}
        ${canEdit?'<button class="secondary" id="editCorpusOverview">编辑全书总览</button>':''}<section class="card"><h3>待核实项</h3>${record.body.uncertainties.map(s=>`<p>${esc(s)}</p>`).join('')||'<p class="muted">未登记待核实项；不代表没有问题。</p>'}${canEdit?'<button class="ghost" id="editCorpusUnknowns">维护待核实项</button>':''}</section>
        <section class="card"><h3>已提炼方法版本</h3>${record.derived_methods.filter(m=>m.structure_version===record.version).map(m=>`<p><a class="text-link" href="#/kb/items?method=${enc(m.method_id)}&amp;version=${m.method_version}">方法版本 ${m.method_version} · 依据结构修订 ${m.structure_version} →</a></p>`).join('')||'<p class="muted">这份结构修订尚无已提炼方法。</p>'}</section></div>`;
      $$('[data-domain-observations]').forEach(b=>b.onclick=()=>{
        tab='threads';page=0;search='';unitFilter='';domainFilter=b.dataset.domainObservations;paintSection(canEdit);
        $$('[data-corpus-tab]').forEach(t=>t.classList.toggle('active',t.dataset.corpusTab===tab));
      });
      $('#editCorpusOverview')?.addEventListener('click',()=>editor('overview',record.body.overview));$('#editCorpusUnknowns')?.addEventListener('click',()=>editor('uncertainties',record.body.uncertainties));return;
    }
    const all=record.body[tab]||[];
    const selected=all.filter(row=>{
      if(search&&!JSON.stringify(row).includes(search))return false;
      if(domainFilter){const domain=row.domain||record.body.threads.find(t=>t.id===row.thread_id)?.domain;if(domain!==domainFilter)return false;}
      if(unitFilter){let id=row.unit_id||row.id;const seen=new Set();while(id&&!seen.has(id)){if(id===unitFilter)return true;seen.add(id);id=record.body.units.find(u=>u.id===id)?.parent_id;}return false;}return true;
    });
    const rows=selected.slice(page*30,page*30+30);
    $('#corpusSection').innerHTML=`<div class="row wrap corpus-toolbar"><input id="corpusSearch" value="${esc(search)}" placeholder="检索内容或标识" aria-label="结构记录检索">
      ${['events','units'].includes(tab)?`<select id="corpusUnitFilter" aria-label="按卷章场筛选"><option value="">全部范围</option>${record.body.units.map(u=>`<option value="${esc(u.id)}" ${unitFilter===u.id?'selected':''}>${catalog.levels[u.level]} · ${esc(u.title)}</option>`).join('')}</select>`:''}
      ${['threads','links','domains'].includes(tab)?`<select id="corpusDomainFilter" aria-label="按制作职责筛选"><option value="">全部职责</option>${Object.entries(catalog.domains).map(([id,name])=>`<option value="${id}" ${domainFilter===id?'selected':''}>${name}</option>`).join('')}</select>`:''}
      <button class="secondary" id="applyCorpusFilter">筛选</button>${canEdit?'<button class="button" id="addCorpusRecord">添加记录</button>':''}<span class="muted">匹配 ${selected.length} / 共 ${all.length}</span></div>
      <div class="stack">${rows.length?recordsHtml(rows,tab,record,catalog,canEdit):empty('暂无匹配记录','可先完成多层拆解，或以真实原文维护结构观察。','','layers')}</div>
      ${selected.length>30?`<div class="row corpus-toolbar"><button class="secondary" id="corpusPrevious" ${page===0?'disabled':''}>上一页</button><span>${page+1} / ${Math.ceil(selected.length/30)}</span><button class="secondary" id="corpusNext" ${(page+1)*30>=selected.length?'disabled':''}>下一页</button></div>`:''}`;
    $('#applyCorpusFilter').onclick=()=>{search=$('#corpusSearch').value;unitFilter=$('#corpusUnitFilter')?.value||'';domainFilter=$('#corpusDomainFilter')?.value||'';page=0;paintSection(canEdit);};
    $('#addCorpusRecord')?.addEventListener('click',()=>editor(tab));
    $$('[data-corpus-detail]').forEach(b=>b.onclick=()=>tab==='units'?sourceDrawer(book,rows[Number(b.dataset.corpusDetail)]):recordDrawer(tab,rows[Number(b.dataset.corpusDetail)],record,catalog));
    $$('[data-corpus-edit]').forEach(b=>b.onclick=()=>editor(tab,rows[Number(b.dataset.corpusEdit)]));
    $('#corpusPrevious')?.addEventListener('click',()=>{page--;paintSection(canEdit);});$('#corpusNext')?.addEventListener('click',()=>{page++;paintSection(canEdit);});
  }
  async function paintJobs(){
    if(stopped||!ctx.alive()||!$('#corpusJobPanel'))return;
    const jobs=record.jobs;
    if(!jobs.length){$('#corpusJobPanel').innerHTML='';return;}
    if(!shownJob||!jobs.some(j=>j.id===shownJob))shownJob=jobs[0].id;
    jobDetail=await api.get(root+'/jobs/'+enc(shownJob),ctx.signal);if(stopped||!ctx.alive())return;
    const job=jobDetail,coverage=job.coverage;
    const chars=ranges=>{const merged=[];for(const r of [...(ranges||[])].sort((a,b)=>a.start-b.start)){if(merged.length&&r.start<=merged.at(-1).end)merged.at(-1).end=Math.max(r.end,merged.at(-1).end);else merged.push({start:r.start,end:r.end});}return merged.reduce((n,r)=>n+r.end-r.start,0);};
    $('#corpusJobPanel').innerHTML=`<section class="card corpus-job"><div class="row spread wrap"><h3>${phaseName[job.phase]||job.phase} · ${jobState[job.status]||job.status}${job.control==='pause'?' · 当前调用后暂停':''}</h3><select id="chooseCorpusJob" aria-label="选择拆解任务">${jobs.map(j=>`<option value="${esc(j.id)}" ${j.id===shownJob?'selected':''}>${j.kind==='methods'?'方法提炼':'结构拆解'} · ${jobState[j.status]} · ${esc(j.created_at)}</option>`).join('')}</select></div>
      <p class="muted">任务冻结规格 v${esc(job.structure_schema_version)} · 调用记录 ${job.calls_used} / 上限 ${job.options.max_calls} · 通读 ${chars(coverage.survey_ranges)} 字符 · 细拆 ${chars(coverage.detail_ranges)} 字符</p>
      ${job.error?`<p class="error">${esc(job.error)}</p>`:''}<div class="row wrap">${job.status==='running'?'<button class="secondary" id="pauseCorpusJob">当前调用后暂停</button>':''}${['paused','failed'].includes(job.status)?'<button class="button" id="resumeCorpusJob">续接 / 明确重试</button>':''}${['pending','running','paused','failed'].includes(job.status)?'<button class="ghost" id="cancelCorpusJob">取消此任务（保留记录）</button>':''}<button class="ghost" id="corpusCallList">查看逐次调用记录</button></div></section>`;
    $('#chooseCorpusJob').onchange=e=>{shownJob=e.target.value;paintJobs().catch(fail);};
    for(const action of ['pause','cancel'])$(`#${action}CorpusJob`)?.addEventListener('click',e=>busy(e.currentTarget,async()=>{await api.post(root+'/jobs/'+enc(job.id),{action});await load();}));
    $('#resumeCorpusJob')?.addEventListener('click',()=>openCorpusResume({book,job,reload:load}));
    $('#corpusCallList').onclick=()=>{
      drawer('拆解调用记录',`<p class="muted">每条保留完整输入、模型输出、状态及校验错误。未知结果不会自动重试。</p>${job.calls.map(c=>`<div class="todo-row"><span class="grow">${c.seq} · ${phaseName[c.phase]} · ${esc(c.status)} ${esc(c.error||'')}</span><button class="ghost" data-corpus-call="${c.seq}">查看输入输出</button></div>`).join('')||'<p>尚未发送调用。</p>'}`);
      $$('[data-corpus-call]').forEach(b=>b.onclick=()=>busy(b,async()=>{
        const call=await api.get(root+'/jobs/'+enc(job.id)+'/calls/'+b.dataset.corpusCall,ctx.signal);
        drawer('完整调用输入与输出',`<pre class="raw-data">${esc(JSON.stringify(call,null,2))}</pre>`);
      }));
    };
  }
  ctx.content.innerHTML=loading();await load();
}
