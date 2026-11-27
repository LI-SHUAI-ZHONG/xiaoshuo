import {api,enc,query} from '../api.js';
import {$,$$,esc,empty,loading,drawer,modal,busy,toast,fail} from '../ui.js';

const statuses={draft:'待补齐 / 待审核',approved:'已批准',rejected:'已退回',source_unavailable:'来源不可用'};
const listLines=value=>String(value||'').split('\n').map(s=>s.trim()).filter(Boolean);
const field=(label,html)=>`<label class="field"><span>${esc(label)}</span>${html}</label>`;
const area=(name,value='',rows=3)=>`<textarea name="${name}" rows="${rows}">${esc(value)}</textarea>`;
const options=(rows,selected='')=>Object.entries(rows).map(([id,label])=>`<option value="${esc(id)}" ${id===selected?'selected':''}>${esc(label)}</option>`).join('');
const bullets=rows=>rows.length?`<ul>${rows.map(row=>`<li>${esc(row)}</li>`).join('')}</ul>`:'<p class="muted">待补充</p>';

function productionStatus(row){
  if(row.current_for_production)return '已批准，可供新制作按需选用';
  if(row.status==='approved'&&row.runtime_integration==='requires_approved_structure')return '仅方法库已批准（未绑定多层结构，暂不参与选材）';
  if(row.status==='approved'&&row.runtime_integration==='requires_current_structure')return '结构已过期（须绑定当前 v5 结构）';
  if(row.status==='approved')return '历史已批准，本版本不参与新制作选材';
  if(row.status==='draft'&&row.origin_item_id)return '历史标注草稿 · 待补齐、绑定结构并审核';
  return statuses[row.status];
}

export async function renderMethods(ctx){
  const [catalog,genres]=await Promise.all([api.get('/kb/method-catalog',ctx.signal),api.get('/genres',ctx.signal)]);
  if(!ctx.alive())return;
  const flat=genres.genres.flatMap(g=>[g,...g.children]);
  const taskNames=Object.fromEntries(catalog.tasks.map(t=>[t.id,t.name]));
  const stageFilterChoices=Object.fromEntries([...catalog.stages.map(s=>[s.id,s.name]),['writer','正文写作'],['review','独立审稿'],['acceptance','范围验收']]);
  $('#kbContent').innerHTML=`<div class="notice">方法按制作步骤、生产任务和制作层级组织，类型用于筛选。从已批准的多层结构提炼方法并独立审核；项目启用后按实际需求确认方法与前置，生成具体设计卡、交接下游并核对正文。方法批准不等于已经用于某本小说。</div>
    <form id="methodFilters" class="row wrap method-filters">
    ${field('制作步骤',`<select name="stage"><option value="">全部制作步骤</option>${options(stageFilterChoices,ctx.params.get('stage')||'')}</select>`)}
    ${field('生产任务',`<select name="task"><option value="">全部生产任务</option>${options(taskNames,ctx.params.get('task')||'')}</select>`)}
    ${field('层级',`<select name="scope"><option value="">全书 / 卷 / 章 / 场景</option>${options(catalog.scopes,ctx.params.get('scope')||'')}</select>`)}
    ${field('类型',`<select name="types"><option value="">全部类型</option>${flat.map(g=>`<option value="${esc(g.id)}" ${ctx.params.get('type')===g.id?'selected':''}>${g.parent_id?'　':''}${esc(g.name)}</option>`).join('')}</select>`)}
    ${field('审核状态',`<select name="status"><option value="">全部状态</option>${options(statuses)}</select>`)}
    ${field('查找方法','<input name="q" placeholder="方法名称或需求关键词">')}
    <button class="secondary" type="submit">筛选</button><button class="button" type="button" id="newMethod">新建方法</button></form>
    <div id="methodResults"></div>`;
  let offset=0,serial=0;
  async function load(){
    if(!ctx.alive())return;
    const seq=++serial, filters=Object.fromEntries(new FormData($('#methodFilters')));
    $('#methodResults').innerHTML=loading();
    const data=await api.get(`/kb/methods?${query({...filters,limit:20,offset})}`,ctx.signal);
    if(!ctx.alive()||seq!==serial)return;
    $('#methodResults').innerHTML=`<div class="row spread wrap"><p class="muted">匹配 ${data.total} 条制作方法</p><a class="text-link" href="#/kb/decomposition">查看现行拆解条目 →</a></div>
      ${data.legacy_pending_count?`<p class="muted">历史标注草稿 · ${data.legacy_pending_count} 条待补齐并绑定结构（请在本页列表打开编辑；<a class="text-link" href="#/kb/legacy">查看只读原文</a>）</p>`:''}`+
      (data.methods.length?`<div class="stack">${data.methods.map(row=>`<article class="card"><div class="row spread wrap"><h3>${esc(row.body.title||'未命名方法')}</h3><span class="tag">${esc(productionStatus(row))}</span></div>
      <p class="muted">${row.body.tasks.map(id=>esc(taskNames[id])).join(' · ')||'待确定生产任务'} ｜ ${row.body.scopes.map(id=>esc(catalog.scopes[id])).join(' / ')||'待确定层级'}</p>
      <p>${esc(row.body.applicability[0]||'适用条件待补充')}</p><div class="row spread wrap"><small class="muted">版本 ${row.version}${row.approved_version?` · 已批准版本 ${row.approved_version}`:''} · ${row.body.evidence.length} 处原作证据 · ${row.issues.length+row.source_issues.length} 项待核对</small><button class="secondary" data-method="${esc(row.id)}" data-version="${row.version}">查看 / 编辑</button></div></article>`).join('')}</div>`:
      empty('还没有匹配的制作方法','从预存库导入参考作品并批准多层结构后，即可按生产步骤提炼方法。','<a class="secondary" href="#/staging">导入参考作品</a>','layers'))+
      (data.total>20?`<div class="row method-filters"><button class="secondary" id="methodPrev" ${!offset?'disabled':''}>上一页</button><span>${offset+1}–${Math.min(offset+20,data.total)} / ${data.total}</span><button class="secondary" id="methodNext" ${offset+20>=data.total?'disabled':''}>下一页</button></div>`:'');
    $$('[data-method]').forEach(button=>button.onclick=()=>showMethod(button.dataset.method,Number(button.dataset.version)).catch(fail));
    if($('#methodPrev'))$('#methodPrev').onclick=()=>{offset-=20;load().catch(fail);};
    if($('#methodNext'))$('#methodNext').onclick=()=>{offset+=20;load().catch(fail);};
  }
  async function showMethod(id,version){
    if(version!=null&&(!/^[1-9]\d*$/.test(String(version))||!Number.isSafeInteger(Number(version))))throw new Error('方法版本须为正整数');
    const row=await api.get(`/kb/methods/${enc(id)}${version==null?'':'?version='+enc(version)}`,ctx.signal);
    if(!ctx.alive())return;
    const body=row.body, issues=[...row.issues,...row.source_issues];
    drawer(body.title||'方法详情',`<div class="row spread wrap"><span class="tag">${esc(productionStatus(row))} · 版本 ${row.version}</span><button class="secondary" id="editMethod">编辑最新版本</button></div>
      <p class="muted">${body.tasks.map(t=>esc(taskNames[t])).join(' · ')||'待分类'} ｜ ${body.scopes.map(s=>esc(catalog.scopes[s])).join(' / ')||'层级待定'}</p>
      ${row.approved_version&&row.version!==row.approved_version?`<p class="notice">已批准版本 ${row.approved_version} 保留；当前版本单独审核。</p>`:''}
      ${issues.length?`<div class="notice"><strong>待补齐或核对</strong>${bullets(issues.map(i=>i.message))}</div>`:''}
      ${row.origin_item_id?'<p class="muted">来自旧拆解条目；原始短文与审核记录保留。</p>':''}
      ${row.structure_origin?`<p class="notice">依据原作分析规格 v${esc(row.structure_schema_version)}、结构修订 ${row.structure_origin.structure_version}。<a class="text-link" href="#/staging/${enc(row.structure_origin.book_id)}?view=structure&version=${row.structure_origin.structure_version}" data-method-source>查看结构与多处原文证据 →</a></p>`:`<p class="notice warning">此方法尚未绑定已批准的多层参考结构，仅可在资料库查看，不能进入立项推荐或制作选材。请点击「编辑最新版本」关联参考作品已批准结构。</p>`}
      <section class="method-section"><h3>适用条件</h3>${bullets(body.applicability)}</section>
      <section class="method-section"><h3>所需前置</h3>${bullets(body.prerequisites.map(p=>`${catalog.input_kinds[p.input_kind]} / ${p.artifact}：${p.requirement}`))}</section>
      <section class="method-section"><h3>具体操作</h3>${bullets(body.operations.map(o=>o.instruction))}</section>
      <section class="method-section"><h3>预期产物</h3>${bullets(body.outputs.map(o=>{
        const stage=catalog.stages.find(s=>s.id===o.stage);
        return `${stage?.name||o.stage} · ${catalog.output_labels[o.field]||o.field} · ${catalog.artifact_kinds[o.artifact_kind]}：${o.description}`;
      }))}</section>
      <section class="method-section"><h3>下游用途</h3>${bullets(body.downstream.map(d=>`${catalog.consumers[d.consumer]}：${d.usage}`))}</section>
      <section class="method-section"><h3>验收方法</h3>${bullets(body.acceptance.map(a=>`${a.check}；所需证据：${a.evidence_required}`))}</section>
      <section class="method-section"><h3>原作证据</h3>${body.evidence.map(e=>`<blockquote class="evidence">${esc(e.quote)}</blockquote><p>${esc(e.explanation)}</p><a class="text-link" href="#/staging/${enc(e.book_id)}" data-method-source>${esc(row.evidence_locations.find(p=>p.book_id===e.book_id)?.book_title||'查看来源作品')} · 字符 ${e.start}–${e.end} →</a>`).join('')||'<p class="muted">待补充</p>'}</section>
      <section class="method-section"><h3>不适用情况</h3>${bullets(body.non_applicability)}</section>
      <section class="method-section"><h3>版本记录</h3><div class="row wrap">${row.history.map(v=>`<button class="ghost" data-method-history="${v.version}">版本 ${v.version} · ${v.decision==='approve'?'已批准':v.decision==='reject'?'已退回':'待审核'}</button>`).join('')}</div></section>
      ${!row.review&&row.version===row.latest_version?`<form id="methodReview" class="stack">${field('审核依据 / 退回原因',area('note'))}<div class="row"><button type="submit" class="button" ${issues.length?'disabled':''}>批准此版本</button><button type="button" class="secondary" id="rejectMethod">退回此版本</button></div></form>`:`<p class="muted">${esc(row.review?.note||'历史版本只读；请审核最新版本。')}</p>`}`);
    $('#editMethod').onclick=()=>busy($('#editMethod'),async()=>{const latest=await api.get(`/kb/methods/${enc(id)}`);$('#drawer').close();await editMethod(latest);});
    $$('[data-method-source]').forEach(a=>a.onclick=()=>$('#drawer').close());
    $$('[data-method-history]').forEach(b=>b.onclick=()=>showMethod(id,Number(b.dataset.methodHistory)).catch(fail));
    async function review(decision,button){await busy(button,async()=>{await api.post(`/kb/methods/${enc(id)}/review`,{version:row.version,decision,note:$('#methodReview [name=note]').value});toast(decision==='approve'?'此方法版本已批准':'此版本已退回，修订将保存为新版本');await load();await showMethod(id,row.version);});}
    if($('#methodReview'))$('#methodReview').onsubmit=e=>{e.preventDefault();review('approve',e.target.querySelector('[type=submit]'));};
    if($('#rejectMethod'))$('#rejectMethod').onclick=()=>review('reject',$('#rejectMethod'));
  }
  function outputChoicesForStage(stage) {
    const definition=catalog.stages.find(s=>s.id===stage);
    return Object.fromEntries(definition.output_fields.map(field=>{
      const label=catalog.output_labels[field]||field;
      const when=definition.conditional_output_fields?.[field];
      return [field,when?`${label}（${when}）`:label];
    }));
  }
  async function editMethod(row=null){
    const [{books},approvedData,corpusCatalog]=await Promise.all([
      api.get('/staging',ctx.signal),
      api.get('/kb/approved-structures',ctx.signal).catch(()=>({structures:[]})),
      api.get('/corpus/catalog',ctx.signal).catch(()=>({domains:{},domain_bindings:{}})),
    ]);
    if(!ctx.alive())return;
    const structures=approvedData.structures||[];
    const domainNames=corpusCatalog.domains||{};
    const domainBindings=corpusCatalog.domain_bindings||{};
    const initialOrigin=row?.structure_origin||null;
    const body=structuredClone(row?.body||{title:'',tasks:[],scopes:[],type_tags:[],applicability:[],non_applicability:[],prerequisites:[],outputs:[],operations:[],downstream:[],acceptance:[],evidence:[]});
    const sections={prerequisites:'所需前置',outputs:'预期产物',operations:'具体操作',downstream:'下游用途',acceptance:'验收方法',evidence:'原作证据'};
    const checks=(name,rows,selected)=>Object.entries(rows).map(([id,label])=>`<label class="method-choice"><input type="checkbox" name="${name}" value="${esc(id)}" ${selected.includes(id)?'checked':''}> ${esc(label)}</label>`).join('');
    const select=(name,rows,value)=>`<select name="${name}">${options(rows,value)}</select>`;
    const multi=(name,rows,selected)=>`<select name="${name}" multiple size="3">${Object.entries(rows).map(([id,label])=>`<option value="${esc(id)}" ${selected.includes(id)?'selected':''}>${esc(label)}</option>`).join('')}</select>`;
    modal(row?'编辑方法 · 保存为新版本':'新建可复用方法',`<form id="methodForm" class="stack">
      <p class="muted">可以先保存不完整草稿；批准前必须补齐八类要求、真实证据和前置/产物之间的引用。需关联已批准 v5 多层结构后方可进入制作选材。</p>
      ${field('方法名称',`<input name="title" maxlength="120" value="${esc(body.title)}">`)}
      <fieldset class="method-section"><legend>关联参考作品结构依据（进入制作选材必需）</legend>
        ${field('已批准结构作品',`<select name="origin_book_id"><option value="">暂不绑定（仅资料库草稿）</option>${structures.map(s=>`<option value="${esc(s.book_id)}" ${initialOrigin?.book_id===s.book_id?'selected':''}>${esc(s.title)} · v${s.structure_version}</option>`).join('')}</select>`)}
        <div id="originThreadWrap"></div>
      </fieldset>
      <fieldset class="method-section"><legend>帮助完成哪些生产任务</legend><div class="method-choices">${checks('tasks',taskNames,body.tasks)}</div></fieldset>
      <fieldset class="method-section"><legend>制作层级</legend><div class="method-choices">${checks('scopes',catalog.scopes,body.scopes)}</div></fieldset>
      ${field('类型范围（含父类型最多 64 项；留空表示跨类型，仍须说明条件）',multi('type_tags',Object.fromEntries(flat.map(g=>[g.id,(g.parent_id?'　':'')+g.name])),body.type_tags))}
      ${field('适用条件（每行一条）',area('applicability',body.applicability.join('\n')))}
      ${Object.entries(sections).map(([key,label])=>`<fieldset class="method-section"><legend>${label}</legend><div data-method-section="${key}" class="stack"></div><button class="ghost" type="button" data-add-method-row="${key}">＋ 添加${label}</button></fieldset>`).join('')}
      ${field('不适用情况（每行一条）',area('non_applicability',body.non_applicability.join('\n')))}
      <div class="row spread wrap"><span class="muted">${row?`基于当前版本 ${row.latest_version}，原版本保留`:'新方法保存为草稿'}</span><button class="button" type="submit">保存${row?'新版本':'草稿'}</button></div></form>`,'',true);
    let next=Date.now();
    const stageNames=Object.fromEntries(catalog.stages.map(s=>[s.id,s.name]));
    function inputChoices(){return Object.fromEntries($$('[data-method-section=prerequisites] [data-method-row]').map((r,i)=>[r.dataset.key,$('[name=artifact]',r).value||`前置 ${i+1}`]));}
    function outputChoices(){return Object.fromEntries($$('[data-method-section=outputs] [data-method-row]').map((r,i)=>[r.dataset.key,$('[name=description]',r).value.slice(0,45)||`产物 ${i+1}`]));}
    function refs(){
      for(const section of ['operations','downstream','acceptance'])$$(`[data-method-section=${section}] [data-method-row]`).forEach(r=>{
        for(const name of ['input_keys','output_keys','output_key']){
          const el=$(`[name=${name}]`,r);if(!el)continue;
          const selected=Array.from(el.selectedOptions).map(o=>o.value);
          const choices=name==='input_keys'?inputChoices():outputChoices();
          el.innerHTML=Object.entries(choices).map(([id,label])=>`<option value="${esc(id)}" ${selected.includes(id)?'selected':''}>${esc(label)}</option>`).join('');
        }
      });
    }
    function add(section,value={}){
      const r=document.createElement('div');r.className='card method-edit-row';r.dataset.methodRow=section;r.dataset.key=value.key||`row_${++next}`;
      let html='';
      if(section==='prerequisites')html=field('前置来自',select('input_kind',catalog.input_kinds,value.input_kind||'brief'))+field('需要的具体资料 / 设计',`<input name="artifact" value="${esc(value.artifact||'')}">`)+field('必须满足什么要求',area('requirement',value.requirement));
      if(section==='outputs'){
        const stage=value.stage||'plot_design',fields=outputChoicesForStage(stage);
        const outputField=value.field||Object.keys(fields)[0],kinds=Object.fromEntries(catalog.output_artifact_kinds[stage][outputField].map(k=>[k,catalog.artifact_kinds[k]]));
        html=field('产出步骤',select('stage',stageNames,stage))+field('对应现有产物字段',select('field',fields,outputField))+field('产物种类',select('artifact_kind',kinds,value.artifact_kind||'stage_product'))+field('应设计出的具体内容',area('description',value.description));
      }
      if(section==='operations')html=field('具体操作',area('instruction',value.instruction))+field('使用哪些前置（可多选）',multi('input_keys',inputChoices(),value.input_keys||[]))+field('产生哪些产物（可多选）',multi('output_keys',outputChoices(),value.output_keys||[]));
      if(section==='downstream')html=field('使用哪个产物',select('output_key',outputChoices(),value.output_key))+field('交给哪个下游',select('consumer',catalog.consumers,value.consumer||'writer'))+field('下游要执行什么',area('usage',value.usage));
      if(section==='acceptance')html=field('验收哪个产物',select('output_key',outputChoices(),value.output_key))+field('如何验收',area('check',value.check))+field('需要什么实际证据',area('evidence_required',value.evidence_required));
      if(section==='evidence')html=field('来源作品',select('book_id',Object.fromEntries(books.map(b=>[b.id,b.title])),value.book_id))+field('原作短摘录（保持原文，最多 1500 字）',area('quote',value.quote))+field('字符起点（可留空自动定位；重复摘录须填写）',`<input name="start" type="number" min="0" value="${value.start??''}">`)+field('这处证据说明什么',area('explanation',value.explanation));
      r.innerHTML=html+'<button class="ghost" type="button" data-remove-method-row>移除此行</button>';
      $(`[data-method-section=${section}]`).append(r);
      $('[data-remove-method-row]',r).onclick=()=>{r.remove();refs();};
      if(section==='outputs'){
        const refreshKinds=()=>{const current=$('[name=artifact_kind]',r).value,kinds=catalog.output_artifact_kinds[$('[name=stage]',r).value][$('[name=field]',r).value];$('[name=artifact_kind]',r).innerHTML=options(Object.fromEntries(kinds.map(k=>[k,catalog.artifact_kinds[k]])),current);};
        $('[name=stage]',r).onchange=e=>{$('[name=field]',r).innerHTML=options(outputChoicesForStage(e.target.value));refreshKinds();};
        $('[name=field]',r).onchange=refreshKinds;
      }
      if(section==='prerequisites'||section==='outputs')r.addEventListener('change',refs);
      if(section==='evidence')$('[name=quote]',r).value=value.quote||'';
      refs();
    }
    for(const section of Object.keys(sections))body[section].forEach(value=>add(section,value));
    $$('[data-add-method-row]').forEach(b=>b.onclick=()=>add(b.dataset.addMethodRow));
    const originBookSelect=$('#methodForm [name=origin_book_id]');
    function renderOriginThreads(){
      const bookId=originBookSelect.value,wrap=$('#originThreadWrap');
      const spec=structures.find(s=>s.book_id===bookId);
      if(!spec){wrap.innerHTML=structures.length?'':'<small class="muted">尚无已批准的 v5 参考结构；请先在预存库完成拆解并批准结构。</small>';return;}
      const chosen=initialOrigin?.book_id===bookId?(initialOrigin.basis?.thread_ids||[]):[];
      wrap.innerHTML=field('依据的结构线索 / 弧光（可多选，括号内为对应制作步骤）',`<select name="origin_thread_ids" multiple size="5">${spec.threads.map(t=>{
        const dName=domainNames[t.domain]||t.domain;
        const steps=(domainBindings[t.domain]?.target_step_names||[]).slice(0,3).join('/');
        return `<option value="${esc(t.id)}" ${chosen.includes(t.id)?'selected':''}>${esc(dName)}${steps?`（${esc(steps)}）`:''} · ${esc(t.title)}</option>`;
      }).join('')}</select>`)
        +`<div id="originStepHint" class="muted" style="margin-top:6px"></div>`
        +field('依据说明（写明作用性与方式性提炼依据）',`<input name="origin_explanation" value="${esc(initialOrigin?.basis?.explanation||'依据该参考作品已批准结构归纳可复用方法')}">`);
      const sel=$('[name=origin_thread_ids]',wrap),hint=$('#originStepHint',wrap);
      const showHint=()=>{
        const picked=Array.from(sel.selectedOptions).map(o=>spec.threads.find(t=>t.id===o.value)).filter(Boolean);
        const bindings=[...new Set(picked.map(t=>t.domain))].map(d=>domainBindings[d]).filter(Boolean);
        hint.innerHTML=bindings.length?bindings.map(b=>`<div><strong>${esc(b.name)}</strong> → 推荐任务：${esc((b.recommended_task_names||[]).join('、'))} ｜ 目标步骤：${esc((b.target_step_names||[]).join('、'))}<br>作用性：${esc(b.functional_judgment)}<br>方式性：${esc(b.method_judgment)}</div>`).join(''):'选择线索后将提示该观察推荐绑定的生产任务、目标步骤与作用性/方式性要点。';
      };
      sel.onchange=showHint;showHint();
    }
    renderOriginThreads();originBookSelect.onchange=renderOriginThreads;
    $('#methodForm').onsubmit=e=>{
      e.preventDefault();busy(e.target.querySelector('[type=submit]'),async()=>{
        const form=e.target;
        const result={title:$('[name=title]',form).value,tasks:$$('[name=tasks]:checked',form).map(x=>x.value),scopes:$$('[name=scopes]:checked',form).map(x=>x.value),type_tags:Array.from($('[name=type_tags]',form).selectedOptions).map(o=>o.value),applicability:listLines($('[name=applicability]',form).value),non_applicability:listLines($('[name=non_applicability]',form).value)};
        for(const section of Object.keys(sections)){
          result[section]=[];
          for(const r of $$(`[data-method-section=${section}] [data-method-row]`)){
            let value=Object.fromEntries(rowFields(r));
            if(['downstream','acceptance'].includes(section)&&!value.output_key){
              throw new Error('请先在「预期产物」中添加至少一条产物，再关联下游用途或验收方法');
            }
            if(['prerequisites','outputs','operations'].includes(section))value.key=r.dataset.key;
            if(section==='operations')for(const name of ['input_keys','output_keys'])value[name]=Array.from($(`[name=${name}]`,r).selectedOptions).map(o=>o.value);
            if(section==='evidence'){
              if(value.start==='')delete value.start;else value.start=Number(value.start);
              value=await api.post('/kb/method-evidence',value);
            }
            result[section].push(value);
          }
        }
        const payload={body:result,expected_version:row?.latest_version||0};
        const originBook=originBookSelect.value;
        if(originBook){
          const threadIds=Array.from($('[name=origin_thread_ids]',form)?.selectedOptions||[]).map(o=>o.value);
          if(!threadIds.length)throw new Error('关联结构依据时请至少选择一条参考结构线索');
          const spec=structures.find(s=>s.book_id===originBook);
          payload.structure_origin={book_id:originBook,structure_version:spec.structure_version,thread_ids:threadIds,explanation:$('[name=origin_explanation]',form)?.value||''};
        }else if(initialOrigin){
          payload.structure_origin=null;
        }
        const saved=await api.post(row?`/kb/methods/${enc(row.id)}`:'/kb/methods',payload);
        $('#modalBackdrop').close();toast('方法草稿已保存，批准前会核对完整性与原作证据');await load();await showMethod(saved.id,saved.version);
      });
    };
  }
  $('#methodFilters').onsubmit=e=>{e.preventDefault();offset=0;load().catch(fail);};
  $$('#methodFilters select').forEach(select=>select.onchange=()=>{offset=0;load().catch(fail);});
  $('#newMethod').onclick=()=>editMethod().catch(fail);
  await load();
  if(ctx.params.get('method')&&ctx.alive()){
    try{await showMethod(ctx.params.get('method'),ctx.params.get('version'));}catch(error){fail(error);}
  }
}

function* rowFields(root){for(const el of $$('input[name],select[name],textarea[name]',root))yield [el.name,el.value];}
