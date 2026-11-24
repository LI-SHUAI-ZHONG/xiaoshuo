import {api,enc,query} from '../api.js';
import {$,$$,esc,icon,empty,loading,drawer,fail,toast,busy,number,confirmAction} from '../ui.js';
import {persist} from '../store.js';
import {ProgressTree,flattenTree} from '../components/ProgressTree.js';
import {simpleDiff} from '../components/Diff.js';
import {watchProgress} from '../sse.js';
import {showGate,showBranches} from './studio-decisions.js';
import {showProjectMethods} from './project-methods.js';
import {trashButton} from '../components/NovelCache.js';
import {Inspector} from '../components/Inspector.js';
import {showLengthPlan} from '../components/LengthPlan.js';
import {renderBookDirections} from '../components/BookDirections.js';
import {approvedParent,planArtifacts,scopeName} from '../components/PlanArtifacts.js';
function workbenchProject(project) {
  return {...project, scenes:project.scenes.filter(scene=>scene.in_branch_workbench!==false)};
}
export async function render(ctx){
  let id=ctx.id||ctx.store.activeNovel;if(!id){const data=await api.get('/novels',ctx.signal);ctx.state.novels=data.novels||[];ctx.sidebar('制作台',[], '<strong>选择一本小说开始</strong>从首页创建新小说，或从成品仓库打开制作中的作品。');ctx.content.innerHTML=`<div class="page"><div class="page-heading"><h1>制作台</h1></div>${empty('打开你的创作空间','每本小说拥有独立的进度、草稿和制作档案。','<button class="button" data-new-novel>新建小说</button>','pen')}${(data.novels||[]).map(n=>`<div class="row"><a class="todo-row grow" href="#/studio/${enc(n.id)}">${icon('book')}<span class="grow">${esc(n.title)}</span>${icon('chevron')}</a>${trashButton(n,'ghost')}</div>`).join('')}</div>`;return;}
  persist({activeNovel:id});const [detail,initial]=await Promise.all([api.get(`/novels/${enc(id)}`,ctx.signal),api.get(`/novels/${enc(id)}/progress`,ctx.signal)]);if(!ctx.alive())return;
  const novel=detail.novel;let project=workbenchProject(detail.project),lengthPlan=detail.length_plan||novel.wizard||{};let progress=initial,tab='design',selected='',sceneId='',workbench=null,editing=false,editingBranch='main',paintToken=0,lastSceneVersion='';const base=`/projects/${enc(novel.project_dir)}`;let outputStamp='';
  let projectStamp = revisionStamp(initial), requestedStamp = projectStamp, refreshRequested = false, pendingSync = null;
  function revisionStamp(snapshot) {
    const latestLengthEdit = snapshot.logs?.filter(row => row.kind === 'length').at(-1);
    const scenes = flattenTree(snapshot.tree).filter(node => node.scene_id)
      .map(node => [node.scene_id, node.draft_id, node.accepted_draft_id, node.status]);
    return JSON.stringify([snapshot.branch_id || novel.current_branch || project.branch_id || 'main',
      snapshot.main_revision, latestLengthEdit?.ts, scenes]);
  }
  async function readRequestedProject() {
    while (ctx.alive() && (refreshRequested || requestedStamp !== projectStamp)) {
      const stamp = requestedStamp;
      refreshRequested = false;
      const fresh = await api.get(`/novels/${enc(id)}`, ctx.signal);
      if (!ctx.alive()) return;
      project = workbenchProject(fresh.project);
      if (!editing && sceneId && !project.scenes.some(scene => scene.id === sceneId)) {
        sceneId = '';
        selected = '';
      }
      Object.assign(novel, fresh.novel);
      lengthPlan = fresh.length_plan || novel.wizard || {};
      projectStamp = stamp;
      if (!editing || tab === 'length') {
        workbench = null;
        if (!sceneId && !['design', 'length'].includes(tab) && project.scenes.length) {
          sceneId = project.scenes[0].id;
          selected = sceneId;
        }
        await paintEditor();
      }
      renderToolbar();
      await quality();
    }
  }
  async function syncProject(snapshot, force = false) {
    requestedStamp = revisionStamp(snapshot);
    refreshRequested ||= force;
    if (!pendingSync && (refreshRequested || requestedStamp !== projectStamp)) {
      pendingSync = readRequestedProject().finally(() => { pendingSync = null; });
    }
    await pendingSync;
  }
  ctx.content.innerHTML=`<div class="editor-tabs" id="studioTabs"></div><div id="studioNotice"></div><div class="editor-toolbar" id="studioToolbar"></div><div class="editor-content" id="studioEditor"></div>`;
  $('#sidebarContent').innerHTML='<div id="studioSide"></div>';ctx.refreshHeader();
  function currentNode(){return flattenTree(progress.tree).find(n=>n.id===selected);}
  function planningParent(node) {
    if (!node) return null;
    return node.approved_parent || flattenTree(progress.tree)
      .find(group => group.children?.some(child => child.id === node.id))?.approved_parent;
  }
  function directionGate(node) {
    return progress.gates?.find(gate => gate.target?.kind === 'book_direction_selection' && gate.job_id
      && (node.job_id === gate.job_id || node.id.startsWith(`${gate.job_id}:`)));
  }
  function update(snapshot){if(!ctx.alive())return;$('#statusConnection').innerHTML='<span class="status-dot"></span>后端已连接';progress=snapshot;const listed=ctx.state.novels.find(n=>n.id===id);if(listed)Object.assign(listed,{runtime_status:snapshot.status,current_step:snapshot.current_step,pending_gates:snapshot.gates?.length||0,words:snapshot.words,progress:snapshot.progress});syncProject(snapshot).catch(fail);const node=currentNode();const nextOutput=JSON.stringify([node?.output,planningParent(node),node?.kind==='book_direction'?[node.status,directionGate(node)?.id]:null]);if(tab==='design'&&outputStamp!==nextOutput){outputStamp=nextOutput;paintEditor().catch(fail);}const oldOpen=new Map($$('details[data-tree]').map(d=>[d.dataset.tree,d.open]));$('#studioSide').innerHTML=`<div class="sidebar-heading"><span>制作进度</span><div class="row"><button class="icon-button" id="refreshProgress" title="刷新进度">${icon('refresh')}</button></div></div><div class="current-task"><div class="row">${icon(progress.status==='RUNNING'?'play':'clock')}<strong>${esc(progress.current_step||'等待开始制作')}</strong></div><p>${esc(statusName(progress.status))} · ${number(progress.words)} 字 · ${Number(progress.progress||0)}%</p><div class="progress-track"><span style="width:${Math.max(0,Math.min(100,Number(progress.progress||0)))}%"></span></div></div>${ProgressTree(progress.tree,selected)}${progress.gates?.length?`<div class="sidebar-heading warning">待你确认（${progress.gates.length}）</div><div class="side-nav">${progress.gates.map(g=>`<button class="side-link" style="border:0;background:var(--bg-panel);text-align:left" data-gate="${esc(g.id)}">${icon('alert')}<span>${esc(g.summary)}</span></button>`).join('')}</div>`:''}<div class="side-note"><strong>${esc(novel.title)}</strong><a href="#/book/${enc(id)}?tab=brief">查看立项卡 ${icon('arrow')}</a></div>`;
    $$('details[data-tree]').forEach(d=>{if(oldOpen.has(d.dataset.tree))d.open=oldOpen.get(d.dataset.tree);});$$('[data-node]').forEach(b=>b.onclick=()=>openNode(b.dataset.node).catch(fail));$$('[data-gate]').forEach(b=>b.onclick=()=>openGate(b.dataset.gate));$('#refreshProgress').onclick=()=>refresh().catch(fail);
    $('#studioNotice').innerHTML=progress.reason?`<div class="notice ${progress.status==='CONFIG_REQUIRED'?'warning':''}" style="margin:16px 24px 0">${esc(progress.reason)} ${providerOutcomeUnknown()?'<p>客户端未取得可核实的模型结果。重试会向接口重新发起一次请求。</p>':''} ${progress.status==='CONFIG_REQUIRED'?'<a class="text-link" href="#/settings">前往配置模型 →</a>':''}</div>`:'';
    ctx.state.logs=progress.logs||[];ctx.state.outputs=flattenTree(progress.tree).filter(n=>n.output).map(n=>({summary:`${n.label} · 已生成设计产物`}));ctx.renderPanel();$('#statusWords').textContent=`${number(progress.words)} 字`;$('#statusTask').textContent=statusName(progress.status);const budget=progress.job?.outputs?.budget||progress.job?.budget||progress.job?.request?.budget;$('#statusBudget').textContent=budget?`调用 ${budget.used_calls??budget.used??0}/${budget.max_calls||budget.limit||'—'}`:'调用 —';$('#runPill').hidden=progress.status!=='RUNNING';$('#runPill').dataset.novel=id;$('#runPill').textContent=`● ${novel.title} · ${progress.current_step||'制作中'}`;renderToolbar();}
  async function refresh(){update(await api.get(`/novels/${enc(id)}/progress`,ctx.signal));await syncProject(progress,true);}
  function renderTabs(){const labels=[['design','设计','layers'],['length','篇幅','list'],['text','正文','pen'],['diff','对比','file'],['read','阅读','book']];$('#studioTabs').innerHTML=labels.map(([key,label,glyph])=>`<button data-editor-tab="${key}" id="${key==='diff'?'btnZenDiff':key==='read'?'btnZenRead':'tab-'+key}" class="${tab===key?'active':''}">${icon(glyph)} ${label}</button>`).join('')+`<button id="showQuality" title="质量检查">${icon('shield')}</button>`;$$('[data-editor-tab]').forEach(b=>b.onclick=()=>changeTab(b.dataset.editorTab).catch(fail));$('#showQuality').onclick=()=>{persist({inspector:true});$('#inspector').hidden=false;quality().catch(fail);};}
  function contextBudgetBlocked() {
    return progress.status === 'BLOCKED' && /CONTEXT_TOO_LARGE|MODEL_CONTEXT_WINDOW/.test(progress.reason || '');
  }
  function providerOutcomeUnknown() {
    return progress.status === 'BLOCKED' && (progress.reason || '').includes('PROVIDER_OUTCOME_UNKNOWN');
  }
  function resumeCurrentTask(retry = false) {
    const budgetBlocked = contextBudgetBlocked();
    const action = retry || budgetBlocked || providerOutcomeUnknown() ? 'retry' : 'run';
    return api.post(`/novels/${enc(id)}/${action}`, budgetBlocked ? {use_saved_context_budget:true} : {});
  }
  function runLabel(budgetBlocked) {
    if (progress.gates?.length) {
      const target = progress.gates[0].target;
      if (target?.kind === 'book_direction_selection') return '选择全书方向';
      if (target?.kind === 'chapter_outline_approval') return '确认章纲';
      if (target?.scope === 'chapter' && target.approved_chapter) return '确认场景设计';
      return '处理待确认事项';
    }
    if (budgetBlocked) return '按已保存预算继续';
    if (providerOutcomeUnknown()) return '重试接口调用';
    if (progress.status === 'REJECTED' && flattenTree(progress.tree).some(node => node.kind === 'book_direction'
        && node.status === 'rejected' && node.job_id === progress.job?.id)) return '重新生成方向短案';
    if (progress.status === 'DONE' && scopeName(progress.next_design?.scope)) {
      return progress.next_design.label || `开始${scopeName(progress.next_design.scope)}设计`;
    }
    return '继续制作';
  }
  function renderToolbar(){const hasScene=Boolean(sceneId),budgetBlocked=contextBudgetBlocked();$('#studioToolbar').innerHTML=`<button class="button" id="runNovel" ${progress.status==='RUNNING'||progress.status==='PAUSING'?'disabled':''}>${icon('play')} ${esc(runLabel(budgetBlocked))}</button><button class="secondary" id="pauseNovel" ${progress.status!=='RUNNING'?'disabled':''}>${icon('pause')} 暂停</button><span class="grow muted">${esc(currentNode()?.label||novel.title)}</span>${hasScene?`<select id="sceneSelect" aria-label="选择场景">${project.scenes.map(s=>`<option value="${esc(s.id)}" ${s.id===sceneId?'selected':''}>第${s.chapter_index}章 · 场${s.index} ${esc(s.card?.title||'')}</option>`).join('')}</select>`:''}<details class="menu"><summary class="icon-button" aria-label="更多操作">${icon('more')}</summary><div>${hasScene?'<button id="editScene">手动修改正文</button><button id="acceptScene">接受本场</button><button id="rewriteScene">重写本场</button><button id="reviseScene">退回修订</button>':''}${progress.can_plan_volume?'<button id="planNewVolume">开始新卷设计</button>':''}<button id="openBranches">制作候选与主线</button><button id="openProjectMethods">具体制作方法与回执</button><button id="retryNovel">${budgetBlocked?'按已保存预算继续':'重试当前任务'}</button><button id="rawOutput">查看原始数据</button><a href="#/book/${enc(id)}">制作档案</a><button id="cancelNovel" class="error">取消任务</button>${trashButton(novel)}</div></details>`;$('#runNovel').onclick=e=>busy(e.currentTarget,async()=>{if(progress.gates?.length){openGate(progress.gates[0].id);return;}const r=await resumeCurrentTask();toast(r.reason||'制作任务已启动');await refresh();});$('#pauseNovel').onclick=e=>busy(e.currentTarget,async()=>{const r=await api.post(`/novels/${enc(id)}/pause`);toast(r.reason||'已请求暂停');await refresh();});$('#openBranches').onclick=()=>showBranches(id,refresh).catch(fail);$('#planNewVolume')?.addEventListener('click',e=>busy(e.currentTarget,async()=>{const r=await api.post(`/novels/${enc(id)}/run`,{mode:'design',scope:'volume'});toast(r.reason||'新卷设计已启动');await refresh();}));$('#openProjectMethods').onclick=()=>showProjectMethods(id).catch(fail);$('#retryNovel').onclick=e=>busy(e.currentTarget,async()=>{const r=await resumeCurrentTask(true);toast(r.reason||'已请求重试');await refresh();});$('#cancelNovel').onclick=async()=>{try{if(await confirmAction('取消当前任务','已保存的草稿与制作记录会保留，当前任务将停止。','取消任务')){await api.post(`/novels/${enc(id)}/cancel`);await refresh();}}catch(error){fail(error);}};$('#rawOutput').onclick=()=>drawer('高级 · 原始数据',`<pre class="raw-data">${esc(JSON.stringify(currentNode()?.output||progress,null,2))}</pre>`);$('#sceneSelect')?.addEventListener('change',e=>openNode(e.target.value).catch(fail));$('#editScene')?.addEventListener('click',()=>{tab='text';editing=true;renderTabs();paintEditor().catch(fail);});$('#acceptScene')?.addEventListener('click',acceptScene);$('#rewriteScene')?.addEventListener('click',()=>runScene('write'));$('#reviseScene')?.addEventListener('click',()=>runScene('revise'));}
  async function runScene(mode){if(!await confirmAction(mode==='write'?'重写本场':'退回修订','将启动模型任务并新增草稿版本，已有草稿和接受记录会保留。','确认启动'))return;try{const r=await api.post(`/novels/${enc(id)}/run`,{mode,scene_ids:[sceneId],scope:'chapter'});toast(r.reason||'任务已启动');await refresh();}catch(error){fail(error);}}
  function currentDraft(wb){return wb.drafts.find(d=>d.id===wb.latest_draft_id);}
  async function openNode(nodeId){if(editing&&$('#manuscriptText')&&workbench&&$('#manuscriptText').value!==(currentDraft(workbench)?.text||'')){if(!await confirmAction('离开未保存草稿','离开后将丢弃尚未保存的手动修改。','离开'))return;}editing=false;selected=nodeId;const node=currentNode();if(node?.scene_id){sceneId=node.scene_id;workbench=null;tab='text';}else{tab='design';}renderTabs();renderToolbar();update(progress);await paintEditor();quality().catch(fail);}
  async function changeTab(next){if(!['length','design'].includes(next)&&!sceneId&&project.scenes?.length){sceneId=project.scenes[0].id;selected=sceneId;}tab=next;renderTabs();if(next==='length'){await syncProject(progress,true);return;}await paintEditor();}
  async function loadScene(){if(!sceneId)return null;if(!workbench)workbench=await api.get(`${base}/scenes/${enc(sceneId)}/workbench?${query({branch:novel.current_branch||project.branch_id||'main'})}`,ctx.signal);return workbench;}
  async function paintEditor(){const token=++paintToken;const editor=$('#studioEditor');if(tab==='length'){showLengthPlan(editor,lengthPlan,novel,updated=>{if(!ctx.alive())return;lengthPlan=updated;if(tab==='length')paintEditor().catch(fail);});return;}if(tab==='design'){const node=currentNode();
    if(node?.kind==='book_direction'){
      const gate=directionGate(node);
      renderBookDirections(editor,node,gate?()=>openGate(gate.id):null);
      return;
    }
    editor.innerHTML=node?.output||planningParent(node)?`<h2>${esc(node.label)}</h2>${scopeName(node.scope)?`<p class="muted">${scopeName(node.scope)}设计</p>`:''}<div class="divider"></div>${approvedParent(planningParent(node))}${node.output?planArtifacts(node.output):'<p class="muted">等待本步设计产物。</p>'}`:empty('故事正在等待成形',progress.status==='CONFIG_REQUIRED'?'先配置本地或在线模型，然后点击“继续制作”。':'点击左侧设计步骤查看产物；每一步都按照工作流依赖顺序执行。',progress.status==='CONFIG_REQUIRED'?'<a class="secondary" href="#/settings">配置模型</a>':'','layers');return;}if(!sceneId){editor.innerHTML=empty('还没有场景','完成全书与章节设计后，场景正文会出现在这里。','','pen');return;}editor.innerHTML=loading();const wb=await loadScene();if(!ctx.alive()||token!==paintToken)return;const drafts=wb.drafts||[],latest=currentDraft(wb);if(tab==='text'){editor.innerHTML=`<div class="row spread" style="margin-bottom:18px"><span class="muted">${esc(wb.scene?.card?.title||'场景正文')} · ${drafts.length} 个版本</span>${editing?'<button class="secondary" id="saveDraft">保存为新版本</button>':`<button class="ghost" id="startEditing">${icon('pen')} 手动修改</button>`}</div>${editing?`<textarea class="manuscript-editor" id="manuscriptText" aria-label="正文编辑器" spellcheck="false">${esc(latest?.text||'')}</textarea>`:latest?`<div class="prose" id="manuscriptRead">${esc(latest.text)}</div>`:empty('本场还没有草稿','继续制作可生成正文，也可以手动创作。','','pen')}`;$('#startEditing')?.addEventListener('click',()=>{editingBranch=novel.current_branch||project.branch_id||'main';editing=true;paintEditor().catch(fail);});$('#saveDraft')?.addEventListener('click',e=>busy(e.currentTarget,async()=>{await api.post(`${base}/scenes/${enc(sceneId)}/draft`,{text:$('#manuscriptText').value,branch:editingBranch});editing=false;workbench=null;toast('已保存新草稿版本');await paintEditor();await refresh();}));}else if(tab==='diff'){const currentIndex=Math.max(0,drafts.findIndex(d=>d.id===wb.latest_draft_id));editor.innerHTML=`<div class="row wrap" style="margin-bottom:24px"><label>旧版本 <select id="diffBefore" aria-label="旧版本">${drafts.map((d,i)=>`<option value="${i}" ${i===Math.max(0,currentIndex-1)?'selected':''}>版本 ${i+1}</option>`).join('')}</select></label><label>新版本 <select id="diffAfter" aria-label="新版本">${drafts.map((d,i)=>`<option value="${i}" ${i===currentIndex?'selected':''}>版本 ${i+1}</option>`).join('')}</select></label><span class="tag green">新增</span><span class="tag" style="color:var(--danger)">删除</span></div><div id="zenDiffContainer" class="prose"></div>`;const draw=()=>{$('#zenDiffContainer').innerHTML=drafts.length?simpleDiff(drafts[Number($('#diffBefore').value)]?.text||'',drafts[Number($('#diffAfter').value)]?.text||''):empty('暂无版本可对比','产生两个草稿版本后，可在这里查看词级差异。','','file');};$('#diffBefore').onchange=draw;$('#diffAfter').onchange=draw;draw();}else{const chapterScenes=project.scenes.filter(s=>s.chapter_id===wb.scene.chapter_id);const texts=await Promise.all(chapterScenes.map(async s=>{const draft=s.accepted_draft_id||s.latest_draft_id;return draft?{scene:s,data:await api.get(`${base}/scenes/${enc(s.id)}/drafts/${enc(draft)}`,ctx.signal)}:null;}));if(!ctx.alive()||token!==paintToken)return;editor.innerHTML=`<div class="eyebrow">CHAPTER READER</div><h2 style="text-align:center;margin-bottom:32px">第${wb.scene.chapter_index}章 ${esc(wb.scene.chapter_title)}</h2><div id="zenReaderContainer" class="prose">${texts.filter(Boolean).map(t=>`<div><p class="muted" style="font:11px var(--font-sans);margin:24px 0">场 ${t.scene.index}${t.scene.accepted_draft_id?' · 已接受':' · 未接受草稿'}</p>${esc(t.data.text)}</div>`).join('')||'本章尚无正文。'}</div>`;}}
  async function acceptScene(){try{const wb=await loadScene();const latest=currentDraft(wb);const delta=(wb.deltas||[]).find(x=>x.delta?.draft_id===latest?.id);if(!latest||!delta){toast('本场需先完成状态提取与事实复核；请通过“继续制作”完成后再接受。',true);return;}if(!await confirmAction('接受本场','确认接受当前草稿与对应状态增量？后续写作将使用本场已接受事实。','接受'))return;await api.post(`${base}/scenes/${enc(sceneId)}/accept`,{draft_id:latest.id,delta_id:delta.delta.id,branch:novel.current_branch||project.branch_id||'main'});toast('本场已接受');await refresh();}catch(error){fail(error);}}
  async function quality(){const selectedScene=sceneId;const q=await api.get(`/novels/${enc(id)}/quality?${query({scene:selectedScene})}`,ctx.signal);if(!ctx.alive()||selectedScene!==sceneId)return;$('#inspector').hidden=!ctx.store.inspector;$('#inspectorContent').innerHTML=Inspector(q,Boolean(sceneId));$$('[data-locate-issue]').forEach(b=>b.onclick=()=>changeTab('text').catch(fail));$('#statusGuards').textContent=`守卫 ${(q.guards||[]).length}`;ctx.state.problems=(q.guards||[]).filter(g=>g.severity==='error'||g.severity==='warning').map(g=>({summary:`${g.kind} · ${typeof g.detail==='string'?g.detail:'检查内容请打开质量面板'}`}));ctx.renderPanel();}
  function openGate(gid){const gate=progress.gates.find(g=>g.id===gid);if(gate)showGate(gate,{novelId:id,project,onSaved:refresh});}
  const nodes=flattenTree(initial.tree).filter(node=>!node.children?.length);selected=nodes.find(n=>n.status==='running')?.id
    || nodes.find(n=>n.kind==='book_direction'&&n.status==='waiting')?.id
    || nodes.find(n=>n.output)?.id||nodes.find(n=>!n.children?.length)?.id||'';update(initial);renderTabs();await paintEditor();quality().catch(fail);const stop=watchProgress(id,update,error=>{if(ctx.alive())$('#statusConnection').innerHTML='<span class="status-dot offline"></span>重连中';});ctx.onCleanup(()=>stop());
}
function statusName(status){return {CONFIG_REQUIRED:'需要配置模型',RUNNING:'制作中',WAITING:'等待作者确认',REJECTED:'已退回',READY:'准备就绪',DONE:'当前任务已完成',FAILED:'任务失败',PAUSED:'已暂停',PAUSING:'等待当前调用结束后暂停',CANCELLED:'已取消',BLOCKED:'制作遇到阻碍',PLANNED:'等待开始'}[status]||status||'就绪';}
function actionName(action){return {choose:'选择方案',select:'选择方案',approve:'批准',confirm:'确认',accept:'接受本场',reject:'退回',revise:'请求修订',retry:'重试',cancel:'取消',allow:'允许变更',continue:'继续'}[action]||action;}
