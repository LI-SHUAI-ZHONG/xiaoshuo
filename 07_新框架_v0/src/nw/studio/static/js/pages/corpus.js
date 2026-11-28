import {api,enc} from '../api.js';
import {$,$$,esc,empty,loading,drawer,modal,busy,toast,fail} from '../ui.js';
import {openCorpusEditor,openCorpusReview} from './corpus_editor.js';
import {openCorpusRun,openCorpusResume,jobState,phaseName} from './corpus_jobs.js';
import {analysisCatalogHtml,castDistributionHtml,recordsHtml,recordDrawer,sourceDrawer,sectionNames,stateNames} from './corpus_view.js';

export async function renderCorpus(ctx,book){
  const root=`/staging/${enc(book.id)}/corpus`;
  const latestCatalog=await api.get('/corpus/catalog',ctx.signal);if(!ctx.alive())return;
  const requestedTab=ctx.params.get('tab');
  let record,catalog,tab=['overview','anatomy','distribution',...Object.keys(sectionNames)].includes(requestedTab)?requestedTab:'overview';
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
      <div class="row wrap corpus-toolbar">${!record.initialized&&canStart?'<button class="secondary" id="initializeCorpus">人工建立目录</button>':''}<button class="button" id="startTargetedCorpus" ${canStart?'':'disabled'}>精准步骤拆解（推荐）</button>
      <button class="secondary" id="startCorpus" ${canStart?'':'disabled'}>全书多层图谱拆解</button>
      ${canEdit?'<button class="secondary" id="editCorpusExtent">核对文本完整性</button>':''}
      ${canEdit&&currentSchema&&!record.review?'<button class="secondary" id="reviewCorpus">审核当前结构</button>':''}
      <button class="secondary" id="extractCorpusMethods" ${canDerive?'':'disabled'}>补充提炼方法</button><button class="secondary" id="manualCorpusMethod" ${canDerive?'':'disabled'}>手工提炼方法草稿</button></div>
      ${!latest?'<p class="notice">正在查看历史版本。切换最新版本后编辑；提炼使用当前批准版本。</p>':''}
      <div id="corpusJobPanel"></div>
      ${record.initialized?`<details class="details" ${errors.length?'open':''}><summary>结构核对：${errors.length} 项阻断 · ${warnings.length} 项待核</summary>${record.issues.map(i=>`<p class="${i.severity==='error'?'error':'muted'}">${esc(i.message)}</p>`).join('')||'<p class="muted">结构与引用检查没有发现阻断；这不是文学质量评分。</p>'}</details>`:''}
      <div class="tabs corpus-tabs">${[['overview','全书总览'],['anatomy','黄金三章体检与情绪模块'],['distribution','逐章进展、人物与线索分布'],...Object.entries(sectionNames)].map(([id,name])=>`<button data-corpus-tab="${id}" class="${tab===id?'active':''}">${name}</button>`).join('')}</div>
      <div id="corpusSection"></div></div>`;
    $$('[data-corpus-tab]').forEach(b=>b.onclick=()=>{tab=b.dataset.corpusTab;page=0;search='';unitFilter='';domainFilter='';paintSection(canEdit);$$('[data-corpus-tab]').forEach(t=>t.classList.toggle('active',t===b));});
    $('#startTargetedCorpus')?.addEventListener('click',()=>openCorpusRun({book,record,catalog:latestCatalog,reload:loadLatest,kind:'targeted'}));
    $('#startCorpus').onclick=()=>openCorpusRun({book,record,catalog:latestCatalog,reload:loadLatest,kind:'structure'});
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
      const choices=record.body.threads.filter(t=>t.status!=='uncertain');
      modal('选择方法依据',`<form id="manualFromCorpus" class="stack"><p class="notice">只复制实际结构依据和证据，具体方法仍须由作者归纳并补齐八类要求。</p><select name="thread" multiple size="6" required aria-label="手工提炼依据">${choices.map(t=>`<option value="${esc(t.id)}">${esc(catalog.domains[t.domain])} · ${esc(t.title)}</option>`).join('')}</select><small class="muted">可按住 Ctrl/Command 多选（叙述观察建议逐条单选）。</small><button class="button" type="submit">建立待补齐方法草稿</button></form>`);
      $('#manualFromCorpus').onsubmit=e=>{e.preventDefault();busy(e.target.querySelector('button'),async()=>{
        const ids=Array.from($('[name=thread]',e.target).selectedOptions).map(o=>o.value);
        if(!ids.length)throw new Error('请选择至少一条已核实线索');
        const result=await api.post(root+'/methods',{version:record.version,thread_ids:ids});
        $('#modalBackdrop').close();location.hash=`#/kb/items?method=${enc(result.id)}`;
      });};
    };
    paintSection(canEdit);
  }
  function paintSection(canEdit){
    if(tab==='anatomy'){
      paintAnatomy().catch(fail);
      return;
    }
    if(tab==='distribution'){
      const stats=record.statistics;
      const threads=new Map(record.body.threads.map(t=>[t.id,t]));
      const showProgress=record.body.schema_version>=4;
      const observations=ids=>(ids||[]).map(id=>{
        const t=threads.get(id);
        return t?`<button class="ghost" data-chapter-observation="${esc(id)}">${esc(t.title)}${t.status==='uncertain'?'（存疑）':''}</button>`:`<span class="muted">${esc(id)}</span>`;
      }).join('<br>')||'未登记';
      $('#corpusSection').innerHTML=`<p class="notice">${esc(stats.counting_basis)}机器通读 ${stats.survey.characters}/${stats.survey.total} 字符，细拆 ${stats.detail.characters}/${stats.detail.total}；人工确认 ${stats.manual_reviewed_units.length} 个章节范围。</p>
        ${castDistributionHtml(stats.cast_distribution,record,catalog)}
        <div class="table-wrap"><table class="data-table"><thead><tr><th>当前目录范围</th><th>细节事件</th>${showProgress?'<th>剧情进展</th><th>人物出场与交集</th>':''}<th>钩子引入 / 回应</th><th>伏笔埋设 / 提示 / 回收</th><th>情绪前后</th></tr></thead><tbody>${stats.chapter_ranges.map(r=>`<tr><td>${esc(r.title)}</td><td>${r.detail_events.length}</td>${showProgress?`<td>${observations(r.chapter_progress)}</td><td>${observations(r.cast_entry)}</td>`:''}<td>${r.hook_opens.length} / ${r.hook_responses.length}</td><td>${r.foreshadow_plants.length} / ${r.foreshadow_hints.length} / ${r.foreshadow_payoffs.length}</td><td>${r.emotional_transitions.map(e=>`${esc(e.before||'未明确')} → ${esc(e.after||'未明确')}`).join('<br>')||'未登记'}</td></tr>`).join('')}</tbody></table></div><p class="muted">尚未闭合或存疑的线索：${stats.open_thread_ids.map(esc).join('、')||'没有登记；仍需作者核对是否找全。'}</p>`;
      $$('[data-chapter-observation]').forEach(b=>b.onclick=()=>recordDrawer('threads',threads.get(b.dataset.chapterObservation),record,catalog));
      $$('[data-cast-person]').forEach(b=>b.onclick=()=>recordDrawer('characters',record.body.characters.find(c=>c.id===b.dataset.castPerson),record,catalog));
      return;
    }
    if(tab==='overview'){
      $('#corpusSection').innerHTML=`<div class="stack">${analysisCatalogHtml(latestCatalog,record.statistics.thread_counts)}
        <section class="card stack" id="corpusHandoffCard"><h3>下游步骤接收与入库核验（对接小说工作流）</h3><p class="muted">正在对照小说工作流真实规则核验本书拆解产物的下游可接收状态…</p></section>
        ${Object.entries(catalog.overview_fields).map(([id,label])=>`<section class="card"><h3>${label}</h3><p class="corpus-text">${esc(record.body.overview[id]||'尚未形成全书总览')}</p></section>`).join('')}
        ${canEdit?'<button class="secondary" id="editCorpusOverview">编辑全书总览</button>':''}<section class="card"><h3>待核实项</h3>${record.body.uncertainties.map(s=>`<p>${esc(s)}</p>`).join('')||'<p class="muted">未登记待核实项；不代表没有问题。</p>'}${canEdit?'<button class="ghost" id="editCorpusUnknowns">维护待核实项</button>':''}</section>
        <section class="card"><h3>已提炼方法版本</h3>${record.derived_methods.filter(m=>m.structure_version===record.version).map(m=>`<p><a class="text-link" href="#/kb/items?method=${enc(m.method_id)}&amp;version=${m.method_version}">方法版本 ${m.method_version} · 依据结构修订 ${m.structure_version} →</a></p>`).join('')||'<p class="muted">这份结构修订尚无已提炼方法。</p>'}</section></div>`;
      $$('[data-domain-observations]').forEach(b=>b.onclick=()=>{
        tab='threads';page=0;search='';unitFilter='';domainFilter=b.dataset.domainObservations;paintSection(canEdit);
        $$('[data-corpus-tab]').forEach(t=>t.classList.toggle('active',t.dataset.corpusTab===tab));
      });
      $('#editCorpusOverview')?.addEventListener('click',()=>editor('overview',record.body.overview));$('#editCorpusUnknowns')?.addEventListener('click',()=>editor('uncertainties',record.body.uncertainties));
      paintHandoffAudit().catch(()=>{});
      return;
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
  async function paintHandoffAudit(){
    const card=$('#corpusHandoffCard');
    if(!card||stopped||!ctx.alive())return;
    try{
      const audit=await api.get(`/kb/handoff-audit?book_id=${enc(book.id)}&planning_hierarchy=1`,ctx.signal);
      if(!ctx.alive()||!card.isConnected)return;
      const s=audit.summary||{};
      const primaryType=audit.type_ids?.[0]||(book.confirmed_types||[])[0]||'';
      const castBook=audit.cast_samples?.book_status;
      const castLine=castBook
        ?(castBook.included_in_book_range
          ?'已纳入同类型全书人数分布样本（可供世界/人物/剧情/场景设计参照）'
          :`未纳入全书人数区间：${(castBook.coverage_gaps||[]).join('；')||'请核对文本完整性与逐章阵容核实状态'}`)
        :'尚未形成同类型人数分布样本（批准结构并核实逐章阵容后自动进入）';
      const blocked=(audit.methods||[]).filter(m=>m.status==='blocked');
      const readySteps=(audit.steps||[]).filter(st=>st.receivable_count>0);
      card.innerHTML=`<div class="row spread wrap"><h3>下游步骤接收与入库核验（对接小说工作流）</h3>
          <div class="row wrap">
            <span class="tag green">可接收方法 ${s.receivable_methods||0}</span>
            ${s.draft_methods?`<span class="tag amber">待审核草稿 ${s.draft_methods}</span>`:''}
            ${s.blocked_methods?`<span class="tag" style="color:var(--danger)">受阻 ${s.blocked_methods}</span>`:''}
            <span class="tag blue">覆盖步骤 ${readySteps.length} / ${s.total_steps||17}</span>
          </div></div>
        <p class="muted"><strong>已接通制作步骤</strong>：${readySteps.length?readySteps.map(st=>`${esc(st.short_name)}（${st.receivable_count}）`).join(' · '):'尚无可被下游直接接收的已批准方法。请先批准当前结构，再提炼并独立审核方法。'}</p>
        <p class="muted"><strong>人物分布样本</strong>：${esc(castLine)} ｜ <strong>段落技法通道</strong>：${s.passage_reference_count||0} 条已进入场景/表达候选</p>
        ${blocked.length?`<div class="notice warning"><strong>以下已批准方法尚不能被下游步骤接收（需修订前置、层级或类型匹配）</strong><ul>${blocked.map(m=>`<li><a class="text-link" href="#/kb/items?method=${enc(m.id)}&amp;version=${m.version}">${esc(m.title)}</a>：${esc((m.block_reasons||[]).join('；'))}</li>`).join('')}</ul></div>`:''}
        <div class="row wrap">
          <a class="secondary" href="#/kb/items">管理 / 审核本书提炼方法</a>
          <a class="secondary" href="#/kb/prerequisites${primaryType?'?type='+enc(primaryType):''}">查看本类型 17 步下游接收体检</a>
          ${primaryType?`<button type="button" class="button" data-new-novel="manual" data-prefill="${esc(primaryType)}">以此类型新建小说</button>`:''}
        </div>`;
    }catch(error){
      if(card.isConnected)card.innerHTML=`<h3>下游步骤接收与入库核验</h3><p class="error">体检读取失败：${esc(error.message)}</p>`;
    }
  }
  async function paintAnatomy(){
    const box=$('#corpusSection');
    if(!box||stopped||!ctx.alive())return;
    box.innerHTML=loading();
    const art=await api.get(`/staging/${enc(book.id)}/anatomy`,ctx.signal);
    if(stopped||!ctx.alive()||!box.isConnected)return;
    const q=art.quantitative||{};
    const g3s=q.golden_three_summary||{};
    const p=g3s.paragraphs||{};
    const d=g3s.dialogue||{};
    const pu=g3s.punctuation||{};
    const pb=g3s.prose_balance||{};
    const g3=art.golden_three||{};
    const rh=art.rhythm_registry||{};
    const ems=art.emotion_modules||[];
    const harvested=art.harvested_excerpts||[];
    const backfilled=art.backfilled_topic_ids||art.backfilled_topics||[];
    const pct=v=>v!=null?`${Math.round(Number(v)*1000)/10}%`:'—';

    box.innerHTML=`<div class="stack">
      <section class="card stack">
        <div class="row spread wrap">
          <div>
            <h3>黄金三章量化体检 & 可复用情绪模块</h3>
            <p class="muted">体量识别：<strong>${q.book_scale==='short'?'短篇 (<2.5万字)':'长篇网文'}</strong> · 正文 ${q.story_chapters_count||0} 章（跳过杂项 ${q.skipped_paratext_count||0}） · 总可见字数 ${q.total_visible_chars||0}</p>
          </div>
          <div class="row wrap">
            <button class="secondary" id="runAnatomyZero">0-Token 体检 + 自动采摘实文范例</button>
            <button class="button" id="runAnatomyLlm">AI 黄金三章深拆 + EM情绪模块</button>
          </div>
        </div>
        <div class="row wrap">
          <span class="tag blue">黄金三章卡点率 ${esc(q.golden_three_cliffhanger_rate||'0/0')}</span>
          <span class="tag">金手指信号：${q.golden_finger_signal_chapter?`第 ${q.golden_finger_signal_chapter} 章`:'未检测到明显系统亮牌'}</span>
          <span class="tag green">已采摘三检实文范例 ${harvested.length} 段</span>
          ${backfilled.length?`<a class="tag green" href="#/radar?tab=topics">已回填验证 ${backfilled.length} 条雷达选题 →</a>`:''}
        </div>
        ${(q.benchmark_deviations||[]).length?`<div class="notice warning"><strong>商业常模偏离提示</strong><ul>${q.benchmark_deviations.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`:'<p class="muted">黄金三章竖屏节奏与对话比例处于常见商业常模区间。</p>'}
        ${q.short_lead&&q.short_lead.placement!=='none'?`<p class="notice"><strong>短篇导语检测：</strong>检测到首章内嵌导语（${q.short_lead.chars} 字，分隔符 <code>${esc(q.short_lead.separator)}</code>）。</p>`:''}
        <div class="table-wrap"><table class="data-table">
          <thead><tr><th>竖屏段落指标</th><th>对话与视角</th><th>标点张力（每千字）</th><th>15万章实证文风平衡</th></tr></thead>
          <tbody><tr>
            <td>中位段长 <strong>${p.median_chars??'—'} 字</strong>（均值 ${p.mean_chars??'—'}）<br>≤30字短段 ${pct(p.short_30_ratio)} · >80字长段 ${pct(p.over_80_ratio)}<br>单句成段率 ${pct(p.single_sentence_rate)} · 首段 ${p.first_para_chars??'—'} 字</td>
            <td>对话占比 <strong>${pct(d.ratio)}</strong>（≤15字短句 ${pct(d.short_15_ratio)}）<br>首对话位置：${d.first_dialogue_char!=null?`第 ${d.first_dialogue_char} 字`:'无'}<br>引号规范：${esc(d.quote_style||'—')} · ${esc(g3s.pov?.label||'—')}</td>
            <td>感叹/问号 <strong>${pu.exclaim_question_per_1k??'—'}</strong><br>叙述破折号 ${pu.narration_em_dash_per_1k??'—'}<br>省略号 ${pu.ellipsis_per_1k??'—'}</td>
            <td>动作/感官句占比 <strong>${pct(pb.body_action_sentence_ratio)}</strong><br>心理/因果句占比 ${pct(pb.causal_thought_sentence_ratio)}<br>口语衔接词 ${pb.colloquial_connective_per_1k??'—'}/千字 · 叙述句中位 ${pb.narration_sentence_median??'—'} 字</td>
          </tr></tbody>
        </table></div>
      </section>

      <section class="card stack">
        <div class="row spread wrap">
          <h3>黄金三章逐章解剖</h3>
          <span class="tag">${g3.mode==='llm_deep'?'AI 深拆':'0-Token 量化基线'}</span>
        </div>
        ${g3.overall_verdict?`<p>${esc(g3.overall_verdict)}</p>`:''}
        <div class="table-wrap"><table class="data-table">
          <thead><tr><th>章次</th><th>开篇手法 / 核心事件</th><th>爽点或数据摘要</th><th>章尾卡点</th><th>可复用写法</th></tr></thead>
          <tbody>${(g3.chapters||[]).map(c=>`<tr>
            <td><strong>第 ${c.chapter} 章</strong>${c.title?`<br><small class="muted">${esc(c.title)}</small>`:''}</td>
            <td>${esc(c.hook_method||'—')}${c.core_event?`<br><small>${esc(c.core_event)}</small>`:''}</td>
            <td>${esc(c.payoff_type||(c.chars?`${c.chars}字 · 段中位${c.median_para_chars}字 · 对话${pct(c.dialogue_ratio)}`:'—'))}</td>
            <td>${esc(c.cliffhanger||'—')}</td>
            <td>${esc(c.transferable||'—')}</td>
          </tr>`).join('')||'<tr><td colspan="5" class="muted">暂无前三章记录</td></tr>'}</tbody>
        </table></div>
      </section>

      <section class="card stack">
        <div class="row spread wrap">
          <h3>爽点循环台账（RH）与情绪触发点（TR）</h3>
          <span class="tag">${esc(rh.story_framework||'待深拆')}</span>
        </div>
        <p class="muted">${esc(rh.core_engine||'点击「AI 黄金三章深拆 + EM情绪模块」自动抽取完整 RH 爽点循环与 TR 情绪触发台账。')}</p>
        ${(rh.rh_loops||[]).length?`<h4>RH 爽点循环</h4><div class="table-wrap"><table class="data-table">
          <thead><tr><th>编号</th><th>章节</th><th>铺垫压抑</th><th>释放兑现</th><th>反应层级</th><th>新钩子与升级</th></tr></thead>
          <tbody>${rh.rh_loops.map(r=>`<tr><td><strong>${esc(r.id)}</strong></td><td>${esc(r.chapters||'')}</td><td>${esc(r.setup||'')}</td><td>${esc(r.release||'')}</td><td>${esc(r.reaction||'')}</td><td>${esc(r.next_hook||'')} ${r.escalation?`（${esc(r.escalation)}）`:''}</td></tr>`).join('')}</tbody>
        </table></div>`:''}
        ${(rh.tr_triggers||[]).length?`<h4>TR 情绪触发点</h4><div class="table-wrap"><table class="data-table">
          <thead><tr><th>编号</th><th>章</th><th>触发事件</th><th>目标情绪</th><th>爆发与余波</th><th>复用要点</th></tr></thead>
          <tbody>${rh.tr_triggers.map(t=>`<tr><td><strong>${esc(t.id)}</strong></td><td>${esc(String(t.chapter||''))}</td><td>${esc(t.event||'')}</td><td><span class="tag blue">${esc(t.target_emotion||'')}</span></td><td>${esc(t.peak||'')} → ${esc(t.aftermath||'')}</td><td>${esc(t.reuse_tip||'')}</td></tr>`).join('')}</tbody>
        </table></div>`:''}
      </section>

      <section class="card stack">
        <h3>脱剧情可复用情绪模块卡（EM-*）</h3>
        ${ems.length?`<div class="grid two">${ems.map(em=>`<article class="card stack">
          <div class="row spread wrap"><strong>${esc(em.id||'EM')} · ${esc(em.name||'情绪模块')}</strong>${em.related_rhythm?`<span class="tag">${esc(em.related_rhythm)}</span>`:''}</div>
          <p><strong>读者想看什么：</strong>${esc(em.reader_want||'')}</p>
          <p><strong>情绪链：</strong>${esc(em.emotion_chain||'')}</p>
          <p><strong>核心戏剧单元：</strong>${esc(em.dramatic_unit||'')}</p>
          ${(em.replaceable_slots||[]).length?`<p class="muted"><strong>可替换功能位：</strong>${esc(em.replaceable_slots.join(' / '))}</p>`:''}
          ${(em.do_not_copy||[]).length?`<p class="error"><strong>严禁照搬：</strong>${esc(em.do_not_copy.join('；'))}</p>`:''}
          ${em.failure_conditions?`<p class="muted"><strong>失效条件：</strong>${esc(em.failure_conditions)}</p>`:''}
        </article>`).join('')}</div>`:'<p class="muted">尚未生成脱剧情情绪模块卡。点击右上角「AI 黄金三章深拆 + EM情绪模块」即可抽取（只留结构与情绪链，不带原书专名）。</p>'}
      </section>
    </div>`;

    const triggerAnatomy=(useLlm,btn)=>busy(btn,async()=>{
      const res=await api.post(`/staging/${enc(book.id)}/anatomy`,{use_llm:useLlm,harvest_excerpts:true});
      toast(useLlm
        ?`AI 深拆完成：采摘 ${res.harvested_excerpts?.length||0} 段实文范例，提炼 ${res.emotion_modules?.length||0} 张情绪模块`
        :`0-Token 体检完成：自动采摘 ${res.harvested_excerpts?.length||0} 段三检实文范例`);
      await paintAnatomy();
    });
    $('#runAnatomyZero').onclick=e=>triggerAnatomy(false,e.currentTarget);
    $('#runAnatomyLlm').onclick=e=>triggerAnatomy(true,e.currentTarget);
  }
  async function paintJobs(){
    if(stopped||!ctx.alive()||!$('#corpusJobPanel'))return;
    const jobs=record.jobs;
    if(!jobs.length){$('#corpusJobPanel').innerHTML='';return;}
    if(!shownJob||!jobs.some(j=>j.id===shownJob))shownJob=jobs[0].id;
    jobDetail=await api.get(root+'/jobs/'+enc(shownJob),ctx.signal);if(stopped||!ctx.alive())return;
    const job=jobDetail,coverage=job.coverage;
    const chars=ranges=>{const merged=[];for(const r of [...(ranges||[])].sort((a,b)=>a.start-b.start)){if(merged.length&&r.start<=merged.at(-1).end)merged.at(-1).end=Math.max(r.end,merged.at(-1).end);else merged.push({start:r.start,end:r.end});}return merged.reduce((n,r)=>n+r.end-r.start,0);};
    const kindLabel=k=>k==='targeted'?'精准步骤拆解':k==='methods'?'方法提炼':'全书图谱拆解';
    const publishedCount=Array.isArray(job.progress?.published_methods)?job.progress.published_methods.length:0;
    const fpMap=job.progress?.published_craft_fingerprints||{};
    const fpEntries=Object.values(fpMap).filter(Boolean);
    const fpSummary=fpEntries.length?` · <strong>已收录 ${fpEntries.length} 项脱剧情基座指纹</strong>（${fpEntries.map(f=>esc(f.title)).join(' / ')}）`:(job.progress?.published_voice_fingerprint?` · <strong>已收录语感指纹</strong>（${esc(job.progress.published_voice_fingerprint.title)}）`:'');
    $('#corpusJobPanel').innerHTML=`<section class="card corpus-job"><div class="row spread wrap"><h3>${kindLabel(job.kind)} · ${phaseName[job.phase]||job.phase} · ${jobState[job.status]||job.status}${job.control==='pause'?' · 当前调用后暂停':''}</h3><select id="chooseCorpusJob" aria-label="选择拆解任务">${jobs.map(j=>`<option value="${esc(j.id)}" ${j.id===shownJob?'selected':''}>${kindLabel(j.kind)} · ${jobState[j.status]} · ${esc(j.created_at)}</option>`).join('')}</select></div>
      <p class="muted">任务规格 v${esc(job.structure_schema_version)} · 调用 ${job.calls_used} / 上限 ${job.options.max_calls} · 已读 ${chars(coverage.survey_ranges)} 字符${publishedCount?` · <strong>已直接核验入库 ${publishedCount} 条方法</strong>`:''}${fpSummary}</p>
      ${job.error?`<p class="error">${esc(job.error)}</p>`:''}<div class="row wrap">${job.status==='running'?'<button class="secondary" id="pauseCorpusJob">当前调用后暂停</button>':''}${['paused','failed'].includes(job.status)?'<button class="button" id="resumeCorpusJob">续接 / 重试</button>':''}${['pending','running','paused','failed'].includes(job.status)?'<button class="ghost" id="cancelCorpusJob">取消此任务（保留记录）</button>':''}${publishedCount?'<a class="button" href="#/kb/items">查看已入库方法</a>':''}<button class="ghost" id="corpusCallList">查看逐次调用记录</button></div></section>`;
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
