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
function creativeWorkflowRoadmapHtml() {
  const tiers = [
    ['一、全书方向与故事大纲', '可选 2–3 份大纲对比或直接展开；交付开篇黄金三章、全书因果剧情段、逐人弧光变化链，以及世界规则与核心人物/关系定稿。'],
    ['二、当前卷纲与逐章切分', '自动继承全书类型契约（0 调用免重判）；按需补位本卷新增设定与角色，重点交付「逐章任务切分表」，明确每章写什么、留什么给下章。'],
    ['三、当前章细纲与可写场景包', '自动承接卷纲本章任务 + 上章已接受结果/遗留钩子/到期伏笔；确认章纲后直接完成事件链、行动博弈、POV 场景卡、状态变化、锚点与表达包。'],
    ['四、正文起草 · 审稿修订 · 接受续写', '按受限 POV 场景包起草正文 → 事实与读者独立双审及限次修订 → 提取正文事实增量并接受入库 → 携带真实后果推进下一章与周期复盘。'],
  ];
  return `<section class="card stack" id="creativeWorkflowRoadmap" style="margin-top:20px">
    <div class="row spread wrap">
      <div><h3 style="margin:0">实际小说创作工作流（新版默认启用）</h3>
      <p class="muted" style="margin:4px 0 0;font-size:12px">立项所选的类型、偏好、篇幅与拆解方法由程序自动冻结并逐级继承，不再在全书、卷纲、每章重复空转「类型判定 / 类型适配」。</p></div>
      <span class="tag green">立项契约自动继承</span>
    </div>
    <div class="stack" style="gap:10px">${tiers.map(([t, d]) => `<div class="method-section"><strong>${esc(t)}</strong><p class="muted" style="margin:4px 0 0;font-size:12px">${esc(d)}</p></div>`).join('')}</div>
  </section>`;
}
export async function render(ctx){
  let id=ctx.id||ctx.store.activeNovel;if(!id){const data=await api.get('/novels',ctx.signal);ctx.state.novels=data.novels||[];ctx.sidebar('制作台',[], '<strong>选择一本小说开始</strong>从首页创建新小说，或从成品仓库打开制作中的作品。新建小说默认启用「实际创作工作流」，按大纲→卷切章→章细纲与场景包→正文写审推进。');ctx.content.innerHTML=`<div class="page"><div class="page-heading"><h1>制作台</h1></div>${empty('打开你的创作空间','每本小说按「全书大纲 → 卷纲逐章切分 → 章细纲与场景包 → 正文写审接受」推进，类型与立项偏好由程序自动冻结继承。','<button class="button" data-new-novel>新建小说</button>','pen')}${(data.novels||[]).map(n=>`<div class="row"><a class="todo-row grow" href="#/studio/${enc(n.id)}">${icon('book')}<span class="grow">${esc(n.title)}</span>${icon('chevron')}</a>${trashButton(n,'ghost')}</div>`).join('')}${creativeWorkflowRoadmapHtml()}</div>`;return;}
  persist({activeNovel:id});const [detail,initial]=await Promise.all([api.get(`/novels/${enc(id)}`,ctx.signal),api.get(`/novels/${enc(id)}/progress`,ctx.signal)]);if(!ctx.alive())return;
  const novel=detail.novel;let project=workbenchProject(detail.project),lengthPlan=detail.length_plan||novel.wizard||{};let progress=initial,tab='design',selected='',sceneId='',workbench=null,latestQuality=null,editing=false,editingBranch=novel.current_branch||project.branch_id||'main',paintToken=0,lastSceneVersion='';const base=`/projects/${enc(novel.project_dir)}`;let outputStamp='';
  let projectStamp = revisionStamp(initial), requestedStamp = projectStamp, refreshRequested = false, pendingSync = null;
  function revisionStamp(snapshot) {
    const latestLengthEdit = snapshot.logs?.filter(row => row.kind === 'length').at(-1);
    const scenes = flattenTree(snapshot.tree).filter(node => node.scene_id)
      .map(node => [node.scene_id, node.draft_id, node.accepted_draft_id, node.status]);
    return JSON.stringify([snapshot.branch_id || novel.current_branch || project.branch_id || 'main',
      snapshot.main_revision, snapshot.words, snapshot.job?.id, snapshot.job?.status, latestLengthEdit?.ts, scenes]);
  }
  async function readRequestedProject() {
    while (ctx.alive() && (refreshRequested || requestedStamp !== projectStamp)) {
      const stamp = requestedStamp;
      refreshRequested = false;
      const fresh = await api.get(`/novels/${enc(id)}`, ctx.signal);
      if (!ctx.alive()) return;
      const prevBranch = novel.current_branch || project.branch_id || 'main';
      project = workbenchProject(fresh.project);
      if (!editing && sceneId && !project.scenes.some(scene => scene.id === sceneId)) {
        sceneId = '';
        selected = '';
      }
      Object.assign(novel, fresh.novel);
      const nextBranch = novel.current_branch || project.branch_id || 'main';
      if (prevBranch !== nextBranch) {
        editing = false;
        editingBranch = nextBranch;
        workbench = null;
        latestQuality = null;
      }
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
  ctx.content.innerHTML=`<div class="editor-tabs" id="studioTabs"></div><div id="studioNotice"></div><div id="studioContinuationNotice"></div><div class="editor-toolbar" id="studioToolbar"></div><div class="editor-content" id="studioEditor"></div>`;
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
    const methodBlocked = progress.status === 'BLOCKED' && /METHOD_DESIGN_REQUIRED|AUTO_RECOMMENDATIONS_MISSING/.test(progress.reason || '');
    const blockedStage = progress.blocked_design?.stage || '';
    $('#studioNotice').innerHTML=progress.reason?`<div class="notice ${progress.status==='CONFIG_REQUIRED'||methodBlocked?'warning':''}" style="margin:16px 24px 0">${esc(progress.reason)} ${providerOutcomeUnknown()?'<p>客户端未取得可核实的模型结果。重试会向接口重新发起一次请求。</p>':''} ${progress.status==='CONFIG_REQUIRED'?'<a class="text-link" href="#/settings">前往配置模型 →</a>':''} ${methodBlocked?`<div class="row wrap" style="margin-top:8px"><button type="button" class="secondary" id="noticeProjectMethods">查看本项目方法与体检</button><a class="text-link" href="#/kb/items${blockedStage?'?stage='+enc(blockedStage):''}">前往类型资料库补齐本步方法 →</a><a class="text-link" href="#/staging">前往预存库拆解 →</a></div>`:''}</div>`:'';
    $('#noticeProjectMethods')?.addEventListener('click',()=>showProjectMethods(id).catch(fail));
    const cont = progress.continuation || null;
    const contParts = [];
    if (cont?.needs_candidate_branch) {
      contParts.push(`<div class="notice" style="margin:12px 24px 0"><div class="row spread wrap" style="gap:8px"><span><strong>主线当前章节已接受完毕：</strong>按工作流规范，续写下一章或新卷需先建立候选分支，完成复核后再并入主线。</span><div class="row wrap" style="gap:8px"><button type="button" class="secondary" id="quickOpenBranches">建立候选分支以续写</button><a class="text-link" href="#/book/${enc(id)}?tab=continuation">连载复盘与完稿体检 →</a></div></div></div>`);
    } else if (cont?.is_candidate && cont?.needs_revalidation?.length) {
      const names = (cont.revalidation_details || []).map(r => r.label).join('、') || cont.needs_revalidation.join('、');
      contParts.push(`<div class="notice warning" style="margin:12px 24px 0"><div class="row spread wrap" style="gap:8px"><span><strong>候选分支需复核受影响旧稿（${cont.needs_revalidation.length} 场）：</strong>${esc(names)}</span><div class="row wrap" style="gap:8px"><button type="button" class="secondary" id="quickRevalidate">立即启动旧稿复核</button><button type="button" class="ghost" id="quickOpenBranches">查看分支详情</button></div></div></div>`);
    } else if (cont?.is_candidate && cont?.can_promote) {
      contParts.push(`<div class="notice" style="margin:12px 24px 0"><div class="row spread wrap" style="gap:8px"><span><strong>候选分支已通过全部检查：</strong>本分支共有 ${cont.changed_scenes_count || 0} 场已接受变更，可审查并合并回主线。</span><button type="button" class="secondary" id="quickOpenBranches">审查并合并回主线</button></div></div>`);
    }
    if (cont && ((cont.summary_pending_chapters || []).length || cont.due_review_count || cont.overdue_promises_count)) {
      const hints = [];
      if ((cont.summary_pending_chapters || []).length) hints.push(`第 ${cont.summary_pending_chapters.join('、')} 章章总结待填写`);
      if (cont.due_review_count) hints.push(`${cont.due_review_count} 项周期阶段复盘到期`);
      if (cont.overdue_promises_count) hints.push(`${cont.overdue_promises_count} 项伏笔超期未回收`);
      contParts.push(`<div class="notice" style="margin:10px 24px 0;font-size:12px"><div class="row spread wrap" style="gap:8px"><span><strong>续章防遗忘提醒：</strong>${esc(hints.join(' · '))}</span><a class="text-link" href="#/book/${enc(id)}?tab=continuation">前往「连载与复盘」处理 →</a></div></div>`);
    }
    $('#studioContinuationNotice').innerHTML = contParts.join('');
    $('#quickOpenBranches')?.addEventListener('click', () => showBranches(id, refresh).catch(fail));
    $('#quickRevalidate')?.addEventListener('click', e => busy(e.currentTarget, async () => {
      const r = await api.post(`/novels/${enc(id)}/run`, {mode: 'revise', scene_ids: cont.needs_revalidation, scope: 'chapter'});
      toast(r.reason || '受影响旧稿复核已启动');
      await refresh();
    }));
    ctx.state.logs=progress.logs||[];ctx.state.outputs=flattenTree(progress.tree).filter(n=>n.output).map(n=>({summary:`${n.label} · 已生成设计产物`}));ctx.renderPanel();$('#statusWords').textContent=`${number(progress.words)} 字`;$('#statusTask').textContent=statusName(progress.status);const budget=progress.job?.outputs?.budget||progress.job?.budget||progress.job?.request?.budget;$('#statusBudget').textContent=budget?`调用 ${budget.used_calls??budget.used??0}/${budget.max_calls||budget.limit||'—'}`:'调用 —';$('#runPill').hidden=progress.status!=='RUNNING';$('#runPill').dataset.novel=id;$('#runPill').textContent=`● ${novel.title} · ${progress.current_step||'制作中'}`;renderToolbar();}
  async function refresh(){update(await api.get(`/novels/${enc(id)}/progress`,ctx.signal));await syncProject(progress,true);}
  function renderTabs(){const labels=[['design','设计','layers'],['length','篇幅','list'],['text','正文','pen'],['context','工作包','shield'],['diff','对比','file'],['read','阅读','book']];$('#studioTabs').innerHTML=labels.map(([key,label,glyph])=>`<button data-editor-tab="${key}" id="${key==='diff'?'btnZenDiff':key==='read'?'btnZenRead':'tab-'+key}" class="${tab===key?'active':''}">${icon(glyph)} ${label}</button>`).join('')+`<button id="showQuality" title="质量检查">${icon('shield')}</button>`;$$('[data-editor-tab]').forEach(b=>b.onclick=()=>changeTab(b.dataset.editorTab).catch(fail));$('#showQuality').onclick=()=>{persist({inspector:true});$('#inspector').hidden=false;quality().catch(fail);};}
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
      if (target?.kind === 'production_method_selection') return '确认制作方法';
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
    if (progress.continuation?.needs_candidate_branch) return '建立候选以续写';
    return '继续制作';
  }
  function renderToolbar(){const hasScene=Boolean(sceneId),budgetBlocked=contextBudgetBlocked(),currentBranch=progress.branch_id||novel.current_branch||project.branch_id||'main';$('#studioToolbar').innerHTML=`<button class="button" id="runNovel" ${progress.status==='RUNNING'||progress.status==='PAUSING'?'disabled':''}>${icon('play')} ${esc(runLabel(budgetBlocked))}</button><button class="secondary" id="pauseNovel" ${progress.status!=='RUNNING'?'disabled':''}>${icon('pause')} 暂停</button><button class="ghost" id="branchBadge" title="切换或提升工作分支">${esc(currentBranch==='main'?'主线':`候选 · ${currentBranch}`)}</button><span class="grow muted">${esc(currentNode()?.label||novel.title)}</span>${hasScene?`<select id="sceneSelect" aria-label="选择场景">${project.scenes.map(s=>`<option value="${esc(s.id)}" ${s.id===sceneId?'selected':''}>第${s.chapter_index}章 · 场${s.index} ${esc(s.title||s.card?.title||'')}</option>`).join('')}</select>`:''}<details class="menu"><summary class="icon-button" aria-label="更多操作">${icon('more')}</summary><div>${hasScene?'<button id="editScene">手动修改正文</button><button id="acceptScene">接受本场</button><button id="rewriteScene">重写本场</button><button id="reviseScene">退回修订</button>':''}${progress.can_plan_volume?'<button id="planNewVolume">开始新卷设计</button>':''}<button id="openBranches">制作候选与主线</button><a href="#/book/${enc(id)}?tab=continuation">连载复盘与完稿体检</a><button id="openProjectMethods">具体制作方法与回执</button><button id="retryNovel">${budgetBlocked?'按已保存预算继续':'重试当前任务'}</button><button id="rawOutput">查看原始数据</button><a href="#/book/${enc(id)}">制作档案</a><button id="cancelNovel" class="error">取消任务</button>${trashButton(novel)}</div></details>`;$('#runNovel').onclick=e=>busy(e.currentTarget,async()=>{if(progress.gates?.length){openGate(progress.gates[0].id);return;}if(!budgetBlocked&&!providerOutcomeUnknown()&&progress.continuation?.needs_candidate_branch){showBranches(id,refresh).catch(fail);return;}const r=await resumeCurrentTask();toast(r.reason||'制作任务已启动');await refresh();});$('#pauseNovel').onclick=e=>busy(e.currentTarget,async()=>{const r=await api.post(`/novels/${enc(id)}/pause`);toast(r.reason||'已请求暂停');await refresh();});$('#branchBadge').onclick=()=>showBranches(id,refresh).catch(fail);$('#openBranches').onclick=()=>showBranches(id,refresh).catch(fail);$('#planNewVolume')?.addEventListener('click',e=>busy(e.currentTarget,async()=>{const r=await api.post(`/novels/${enc(id)}/run`,{mode:'design',scope:'volume'});toast(r.reason||'新卷设计已启动');await refresh();}));$('#openProjectMethods').onclick=()=>showProjectMethods(id).catch(fail);$('#retryNovel').onclick=e=>busy(e.currentTarget,async()=>{const r=await resumeCurrentTask(true);toast(r.reason||'已请求重试');await refresh();});$('#cancelNovel').onclick=async()=>{try{if(await confirmAction('取消当前任务','已保存的草稿与制作记录会保留，当前任务将停止。','取消任务')){await api.post(`/novels/${enc(id)}/cancel`);await refresh();}}catch(error){fail(error);}};$('#rawOutput').onclick=()=>drawer('高级 · 原始数据',`<pre class="raw-data">${esc(JSON.stringify(currentNode()?.output||progress,null,2))}</pre>`);$('#sceneSelect')?.addEventListener('change',e=>openNode(e.target.value).catch(fail));$('#editScene')?.addEventListener('click',()=>{editingBranch=novel.current_branch||project.branch_id||'main';tab='text';editing=true;renderTabs();paintEditor().catch(fail);});$('#acceptScene')?.addEventListener('click',acceptScene);$('#rewriteScene')?.addEventListener('click',()=>runScene('write'));$('#reviseScene')?.addEventListener('click',()=>runScene('revise'));}
  async function runScene(mode){if(!await confirmAction(mode==='write'?'重写本场':'退回修订','将启动模型任务并新增草稿版本，已有草稿和接受记录会保留。','确认启动'))return;try{const r=await api.post(`/novels/${enc(id)}/run`,{mode,scene_ids:[sceneId],scope:'chapter'});toast(r.reason||'任务已启动');await refresh();}catch(error){fail(error);}}
  async function runManualReview(){if(!sceneId)return;try{const r=await api.post(`/novels/${enc(id)}/run`,{mode:'revise',scene_ids:[sceneId],scope:'chapter'});toast(r.reason||'已启动 16 独立审稿与 17 状态提取');await refresh();}catch(error){fail(error);}}
  function fmtContractRow(item){
    if(!item)return '';
    if(typeof item==='string')return item;
    return [item.beat,item.anchor,item.focus,item.guidance,item.instruction,item.rule,item.summary,item.description].filter(Boolean).join(' · ')||JSON.stringify(item);
  }
  function executionRibbonHtml(wb,q){
    if(!wb)return '';
    const ds=q?.scene_id===sceneId?q.draft_status:null;
    const wc=q?.scene_id===sceneId?q.writing_contract:null;
    const card=wb.scene?.card||{};
    const drafts=wb.drafts||[];
    const hasDraft=drafts.length>0;
    const writeTone=hasDraft?(ds?.is_manual?'amber':'green'):'';
    const reviewTone=ds?.review_recommendation==='pass'?'green':(ds?.review_recommendation?'amber':'');
    const extractTone=ds?.hard_findings_count?'amber':(ds?.has_delta?'green':'');
    const acceptTone=ds?.is_accepted?'green':'';
    const pov=wc?.pov||card.pov||'';
    const disclosure=wc?.allowed_disclosure||card.allowed_disclosure||'';
    const goal=wc?.goal||card.goal||'';
    const conflict=wc?.conflict||card.conflict||'';
    const beats=Array.isArray(wc?.anchor_beats)?wc.anchor_beats:[];
    const exprs=Array.isArray(wc?.expression_guidance)?wc.expression_guidance:[];
    const methods=Array.isArray(wc?.method_guidance)?wc.method_guidance:[];
    return `<div class="card" id="sceneExecutionRibbon" style="margin-bottom:16px;padding:12px 14px">
      <div class="row spread wrap" style="gap:8px;margin-bottom:8px">
        <div class="row wrap" style="gap:6px">
          <span class="tag ${writeTone}">15 正文写作${ds?.is_manual?'（手动）':''}</span>
          <span class="tag ${reviewTone}">16 独立审稿</span>
          <span class="tag ${extractTone}">17 状态提取与复核</span>
          <span class="tag ${acceptTone}">17 接受入库</span>
        </div>
        <div class="row wrap" style="gap:8px">
          ${ds?.stage_label?`<span class="muted" style="font-size:12px">${esc(ds.stage_label)}</span>`:''}
          ${hasDraft&&!ds?.is_accepted?'<button class="ghost" type="button" id="openManualDelta">离线录入状态增量</button>':''}
          ${ds?.needs_review?'<button class="secondary" id="reviewManualDraft">送交 16 独立审稿与验收</button>':''}
        </div>
      </div>
      <details class="details" id="sceneWritingBrief">
        <summary>15 本场写作承接与边界${pov?` · POV：${esc(pov)}`:''}${wc?` · 节拍 ${number(wc.anchor_beats_count||0)} / 表达 ${number(wc.expression_guidance_count||0)} / 方法 ${number(wc.method_guidance_count||0)}`:''}</summary>
        <div style="margin-top:8px;font-size:12px">
          ${goal?`<p style="margin:0 0 4px"><strong>本场目标：</strong>${esc(goal)}</p>`:''}
          ${conflict?`<p style="margin:0 0 4px"><strong>核心冲突：</strong>${esc(conflict)}</p>`:''}
          ${disclosure?`<p style="margin:0 0 4px"><strong>允许披露边界：</strong>${esc(disclosure)}</p>`:''}
          ${beats.length?`<p style="margin:4px 0"><strong>12 具象节拍：</strong>${beats.map(b=>esc(fmtContractRow(b))).join('；')}</p>`:''}
          ${exprs.length?`<p style="margin:4px 0"><strong>13 表达指导：</strong>${exprs.map(g=>esc(fmtContractRow(g))).join('；')}</p>`:''}
          ${methods.length?`<p style="margin:4px 0"><strong>14 绑定方法：</strong>${methods.map(m=>esc(fmtContractRow(m))).join('；')}</p>`:''}
          ${wc?.writer_review_focus?`<p class="muted" style="margin:4px 0 0;white-space:pre-wrap"><strong>题材 15–16 写审红线：</strong>${esc(wc.writer_review_focus)}</p>`:''}
        </div>
      </details>
    </div>`;
  }
  function openManualDeltaDrawer(wb){
    const latest=currentDraft(wb);
    if(!latest){toast('请先生成或保存本场草稿，再录入状态增量',true);return;}
    const curBranch=novel.current_branch||project.branch_id||'main';
    const storyOrder=Number(wb.scene?.card?.story?.story_order||wb.context_preview?.scope?.story_order||1);
    drawer('离线录入本场状态增量（17 StateDelta）',`<form id="manualDeltaForm" class="stack">
      <div class="notice">每条状态增量必须绑定当前草稿中的原文引文（自动定位 Unicode 起止偏移）。若本场属于纯过渡且未产生新客观事实或认知变更，可直接提交空列表完成 17 步增量登记。</div>
      <div id="deltaOpsList" class="stack" style="gap:10px"></div>
      <div class="row wrap" style="gap:8px">
        <button type="button" class="secondary" id="addDeltaOpBtn">+ 添加状态变更项</button>
        <button type="submit" class="button">保存状态增量并执行事实复核</button>
      </div>
    </form>`);
    const listEl=$('#deltaOpsList');
    const addRow=()=>{
      const row=document.createElement('div');
      row.className='card stack';
      row.dataset.deltaOpRow='1';
      row.innerHTML=`<div class="row spread"><strong>状态变更项</strong><button type="button" class="ghost" data-remove-op>移除</button></div>
        <div class="form-grid">
          <label class="field"><span>主体（holder）</span><input name="holder" value="WORLD" required placeholder="WORLD / READER / 人物ID"></label>
          <label class="field"><span>动作（op）</span><select name="op"><option value="set">set（设定/更新）</option><option value="unset">unset（清除）</option></select></label>
          <label class="field"><span>实体 ID（entity_id）</span><input name="entity_id" required placeholder="如 seal 或 char_lin"></label>
          <label class="field"><span>属性名（predicate）</span><input name="predicate" required placeholder="如 status / location"></label>
          <label class="field"><span>命题性质（claim）</span><select name="claim"><option value="fact">fact（事实）</option><option value="belief">belief（信念）</option><option value="suspicion">suspicion（怀疑）</option><option value="plan">plan（计划）</option></select></label>
          <label class="field"><span>原值（expected_old，无则留空）</span><input name="expected_old" placeholder="首次出现留空"></label>
        </div>
        <label class="field"><span>新值（new_value，unset 时留空）</span><input name="new_value" placeholder="如 broken 或 旧港栈桥"></label>
        <label class="field"><span>草稿原文精确引文（用于自动计算段落与偏移）</span><input name="quote" required placeholder="粘贴本场草稿中包含该事实的原句片段"></label>`;
      row.querySelector('[data-remove-op]').onclick=()=>row.remove();
      listEl.appendChild(row);
    };
    $('#addDeltaOpBtn').onclick=addRow;
    $('#manualDeltaForm').onsubmit=e=>{
      e.preventDefault();
      const rows=$$('[data-delta-op-row]',listEl);
      const operations=[];
      for(const r of rows){
        const holder=r.querySelector('[name=holder]').value.trim()||'WORLD';
        const op=r.querySelector('[name=op]').value;
        const entity_id=r.querySelector('[name=entity_id]').value.trim();
        const predicate=r.querySelector('[name=predicate]').value.trim();
        const claim=holder==='WORLD'?'fact':r.querySelector('[name=claim]').value;
        const oldRaw=r.querySelector('[name=expected_old]').value.trim();
        const newRaw=r.querySelector('[name=new_value]').value.trim();
        const quote=r.querySelector('[name=quote]').value;
        const start=latest.text.indexOf(quote);
        if(!quote.trim()||start<0){
          toast(`未能在当前草稿中找到精确引文：「${quote}」`,true);
          return;
        }
        const end=start+quote.length;
        const paraIdx=latest.text.slice(0,end).split(/\r?\n[ \t]*\r?\n+/).length-1;
        operations.push({
          op,
          entity_id,
          predicate,
          holder,
          claim,
          story_order:storyOrder,
          disclosure_order:[Number(wb.scene.chapter_index||1),Number(wb.scene.index||1),Math.max(0,paraIdx)],
          expected_old:oldRaw?oldRaw:null,
          new_value:op==='unset'?null:newRaw,
          evidence:[{start,end}],
        });
      }
      busy(e.target.querySelector('[type=submit]'),async()=>{
        const saved=await api.post(`${base}/scenes/${enc(sceneId)}/delta`,{draft_id:latest.id,branch:curBranch,story_order:storyOrder,operations});
        $('#drawer')?.close?.();
        const hard=(saved.findings||[]).filter(f=>f.severity==='hard').length;
        toast(hard?`状态增量已保存，发现 ${hard} 项硬冲突请核查`:`已保存 ${operations.length} 项状态增量并通过事实复核`);
        workbench=null;
        await paintEditor();
        await refresh();
      }).catch(fail);
    };
  }
  function bindExecutionRibbon(wb){
    $('#reviewManualDraft')?.addEventListener('click',e=>busy(e.currentTarget,()=>runManualReview()));
    $('#openManualDelta')?.addEventListener('click',()=>openManualDeltaDrawer(wb));
  }
  function currentDraft(wb){return wb.drafts.find(d=>d.id===wb.latest_draft_id);}
  async function confirmDiscardDraft(){if(editing&&$('#manuscriptText')&&workbench&&$('#manuscriptText').value!==(currentDraft(workbench)?.text||'')){return await confirmAction('离开未保存草稿','离开后将丢弃尚未保存的手动修改。','离开');}return true;}
  async function openNode(nodeId){if(!await confirmDiscardDraft())return;editing=false;selected=nodeId;const node=currentNode();if(node?.scene_id){if(sceneId!==node.scene_id)latestQuality=null;sceneId=node.scene_id;workbench=null;tab='text';}else{tab='design';}renderTabs();renderToolbar();update(progress);await paintEditor();quality().catch(fail);}
  async function changeTab(next){if(next!=='text'&&!await confirmDiscardDraft())return;if(next!=='text')editing=false;if(!['length','design'].includes(next)&&!sceneId&&project.scenes?.length){sceneId=project.scenes[0].id;selected=sceneId;latestQuality=null;}tab=next;renderTabs();renderToolbar();if(next==='length'){await syncProject(progress,true);return;}await paintEditor();}
  async function loadScene(){if(!sceneId)return null;if(!workbench)workbench=await api.get(`${base}/scenes/${enc(sceneId)}/workbench?${query({branch:novel.current_branch||project.branch_id||'main'})}`,ctx.signal);return workbench;}
  async function paintEditor(){const token=++paintToken;const editor=$('#studioEditor');if(tab==='length'){showLengthPlan(editor,lengthPlan,novel,updated=>{if(!ctx.alive())return;lengthPlan=updated;if(tab==='length')paintEditor().catch(fail);});return;}if(tab==='design'){const node=currentNode();
    if(node?.kind==='book_direction'){
      const gate=directionGate(node);
      renderBookDirections(editor,node,gate?()=>openGate(gate.id):null);
      return;
    }
    const autoTag = node?.execution_mode?.startsWith('programmatic_') ? '<span class="tag green" style="margin-left:8px">程序自动继承/冻结 · 0 模型调用</span>' : '';
    editor.innerHTML=node?.output||planningParent(node)?`<div class="row wrap"><h2>${esc(node.label)}</h2>${autoTag}</div>${scopeName(node.scope)?`<p class="muted">${scopeName(node.scope)}制作</p>`:''}<div class="divider"></div>${approvedParent(planningParent(node))}${node.output?planArtifacts(node.output,{stage:node.stage,scope:node.scope}):'<p class="muted">等待本步设计产物。</p>'}`:`${empty('故事正在等待成形',progress.status==='CONFIG_REQUIRED'?'先配置本地或在线模型，然后点击“继续制作”。':'点击左侧实际创作步骤查看产物；立项类型契约由程序自动继承，直接按大纲→卷切章→章细纲与场景包→正文写审推进。',progress.status==='CONFIG_REQUIRED'?'<a class="secondary" href="#/settings">配置模型</a>':'','layers')}${progress.creative_workflow?creativeWorkflowRoadmapHtml():''}`;return;}if(!sceneId){editor.innerHTML=empty('还没有场景','完成全书与章节设计后，场景正文会出现在这里。','','pen');return;}editor.innerHTML=loading();const wb=await loadScene();if(!ctx.alive()||token!==paintToken)return;const drafts=wb.drafts||[],latest=currentDraft(wb),sceneTitle=project.scenes.find(s=>s.id===sceneId)?.title||wb.scene?.card?.title||'场景正文';if(tab==='text'){editor.innerHTML=`<div id="sceneExecutionRibbonBox">${executionRibbonHtml(wb,latestQuality)}</div><div class="row spread" style="margin-bottom:18px"><span class="muted">${esc(sceneTitle)} · ${drafts.length} 个版本</span>${editing?'<button class="secondary" id="saveDraft">保存为新版本</button>':`<button class="ghost" id="startEditing">${icon('pen')} 手动修改</button>`}</div>${editing?`<textarea class="manuscript-editor" id="manuscriptText" aria-label="正文编辑器" spellcheck="false">${esc(latest?.text||'')}</textarea>`:latest?`<div class="prose" id="manuscriptRead">${esc(latest.text)}</div>`:empty('本场还没有草稿','继续制作可生成正文，也可以手动创作。','','pen')}`;bindExecutionRibbon(wb);$('#startEditing')?.addEventListener('click',()=>{editingBranch=novel.current_branch||project.branch_id||'main';editing=true;paintEditor().catch(fail);});$('#saveDraft')?.addEventListener('click',e=>busy(e.currentTarget,async()=>{await api.post(`${base}/scenes/${enc(sceneId)}/draft`,{text:$('#manuscriptText').value,branch:editingBranch});editing=false;workbench=null;toast('已保存手动草稿版本；点击「送交 16 独立审稿与验收」或「继续制作」可进行审稿、状态提取与验收');await paintEditor();await refresh();}));}else if(tab==='context'){
      const curBranch=novel.current_branch||project.branch_id||'main';
      const paintContext=ctxData=>{
        const pct=ctxData?Math.min(100,Math.round((ctxData.usage_ratio||0)*100)):0;
        editor.innerHTML=`<section id="sceneContextInspector" class="stack" style="gap:16px">
          <div class="row spread wrap" style="gap:12px">
            <div><h3 style="margin:0">15 实时受限 POV 写作工作包与预算检视</h3><p class="muted" style="margin:4px 0 0;font-size:12px">精确展示当前分支、故事时间点与 POV 下真正允许进入写作模型的设定卡、已知事实与跨步守卫</p></div>
            <div class="row wrap" style="gap:8px">
              <label class="row" style="gap:6px;font-size:12px"><span>字符上限</span><input id="ctxCharLimitInput" value="${ctxData?.char_limit||24000}" style="width:96px"></label>
              <button type="button" class="secondary" id="reloadSceneContext">重算工作包</button>
              ${latest?'<button type="button" class="ghost" id="openManualDeltaFromCtx">离线录入状态增量</button>':''}
            </div>
          </div>
          ${ctxData?`<div class="card stack" style="gap:10px">
            <div class="row spread wrap">
              <strong>上下文预算占用：${number(ctxData.total_chars)} / ${number(ctxData.char_limit)} 字符（${pct}%）</strong>
              <span class="muted" style="font-size:12px">系统提示词 ${number(ctxData.prompt_chars)} 字符 · 工作包 JSON ${number(ctxData.package_chars)} 字符</span>
            </div>
            <div class="progress-track"><span style="width:${pct}%"></span></div>
            <div class="row wrap" style="gap:6px">
              <span class="tag blue">分支：${esc(ctxData.scope?.branch_id||curBranch)} (rev ${number(ctxData.scope?.state_revision||0)})</span>
              <span class="tag">故事时间序：${number(ctxData.scope?.story_order||1)}</span>
              <span class="tag">披露坐标：[${(ctxData.disclosure||[]).join(', ')}]</span>
              <span class="tag green">可见设定卡：${(ctxData.card_refs||[]).length} 张</span>
              <span class="tag">写作技法条：${(ctxData.writing_source_keys||[]).length} 条</span>
            </div>
          </div>
          <div class="card stack" style="gap:8px">
            <strong>冻结工作包条目明细（${(ctxData.items||[]).length} 项）</strong>
            ${(ctxData.items||[]).map(it=>`<details class="details"><summary><strong>${esc(it.key)}</strong> · <span class="muted">${esc(it.reason)}</span> · <span class="tag">${number(it.chars)} 字符</span></summary><pre class="raw-data" style="white-space:pre-wrap;margin-top:8px">${esc(it.content)}</pre></details>`).join('')||'<p class="muted">暂无工作包条目。</p>'}
          </div>
          <details class="details">
            <summary><strong>查看 15 步完整系统提示词与跨步连续性守卫（${number(ctxData.prompt_chars)} 字符）</strong></summary>
            <pre class="raw-data" style="white-space:pre-wrap">${esc(ctxData.prompt||'')}</pre>
          </details>`:`<div class="notice warning">${esc(wb.context_error||'当前项目尚未接管故事状态机或场景尚未绑定已批准的 scene 设定卡，暂无法组装受限 POV 工作包。')} <a class="text-link" href="#/book/${enc(id)}?tab=continuation">前往接管状态机 →</a></div>`}
        </section>`;
        $('#reloadSceneContext')?.addEventListener('click',e=>busy(e.currentTarget,async()=>{
          const lim=Math.max(2000,parseInt($('#ctxCharLimitInput').value||'24000',10)||24000);
          const freshCtx=await api.get(`${base}/scenes/${enc(sceneId)}/context?${query({branch:curBranch,char_limit:lim})}`,ctx.signal);
          wb.context_preview=freshCtx;
          wb.context_error=null;
          paintContext(freshCtx);
        }).catch(fail));
        $('#openManualDeltaFromCtx')?.addEventListener('click',()=>openManualDeltaDrawer(wb));
      };
      paintContext(wb.context_preview);
    }else if(tab==='diff'){const currentIndex=Math.max(0,drafts.findIndex(d=>d.id===wb.latest_draft_id));editor.innerHTML=`<div class="row wrap" style="margin-bottom:24px"><label>旧版本 <select id="diffBefore" aria-label="旧版本">${drafts.map((d,i)=>`<option value="${i}" ${i===Math.max(0,currentIndex-1)?'selected':''}>版本 ${i+1}</option>`).join('')}</select></label><label>新版本 <select id="diffAfter" aria-label="新版本">${drafts.map((d,i)=>`<option value="${i}" ${i===currentIndex?'selected':''}>版本 ${i+1}</option>`).join('')}</select></label><span class="tag green">新增</span><span class="tag" style="color:var(--danger)">删除</span></div><div id="zenDiffContainer" class="prose"></div>`;const draw=()=>{$('#zenDiffContainer').innerHTML=drafts.length?simpleDiff(drafts[Number($('#diffBefore').value)]?.text||'',drafts[Number($('#diffAfter').value)]?.text||''):empty('暂无版本可对比','产生两个草稿版本后，可在这里查看词级差异。','','file');};$('#diffBefore').onchange=draw;$('#diffAfter').onchange=draw;draw();}else{const chapterScenes=project.scenes.filter(s=>s.chapter_id===wb.scene.chapter_id).sort((a,b)=>Number(a.index||0)-Number(b.index||0));const texts=await Promise.all(chapterScenes.map(async s=>{const draft=s.accepted_draft_id||s.latest_draft_id;return draft?{scene:s,data:await api.get(`${base}/scenes/${enc(s.id)}/drafts/${enc(draft)}`,ctx.signal)}:null;}));if(!ctx.alive()||token!==paintToken)return;editor.innerHTML=`<div class="eyebrow">CHAPTER READER</div><h2 style="text-align:center;margin-bottom:32px">第${wb.scene.chapter_index}章 ${esc(wb.scene.chapter_title)}</h2><div id="zenReaderContainer" class="prose">${texts.filter(Boolean).map(t=>`<div><p class="muted" style="font:11px var(--font-sans);margin:24px 0">场 ${t.scene.index}${t.scene.accepted_draft_id?' · 已接受':' · 未接受草稿'}</p>${esc(t.data.text)}</div>`).join('')||'本章尚无正文。'}</div>`;}}
  async function acceptScene(){try{const wb=await loadScene();const latest=currentDraft(wb);const delta=(wb.deltas||[]).find(x=>x.delta?.draft_id===latest?.id);if(!latest||!delta){toast('本场需先完成状态提取与事实复核；请通过“继续制作”完成后再接受。',true);return;}if(!await confirmAction('接受本场','确认接受当前草稿与对应状态增量？后续写作将使用本场已接受事实。','接受'))return;await api.post(`/novels/${enc(id)}/scenes/${enc(sceneId)}/accept`,{draft_id:latest.id,delta_id:delta.delta.id,branch:novel.current_branch||project.branch_id||'main'});toast('本场已接受');await refresh();}catch(error){fail(error);}}
  async function quality(){const selectedScene=sceneId;const q=await api.get(`/novels/${enc(id)}/quality?${query({scene:selectedScene})}`,ctx.signal);if(!ctx.alive()||selectedScene!==sceneId)return;latestQuality=q;$('#inspector').hidden=!ctx.store.inspector;$('#inspectorContent').innerHTML=Inspector(q,Boolean(sceneId));$$('[data-locate-issue]').forEach(b=>b.onclick=()=>changeTab('text').catch(fail));$('#inspectorReviewDraft')?.addEventListener('click',e=>busy(e.currentTarget,()=>runManualReview()));if(tab==='text'&&workbench&&$('#sceneExecutionRibbonBox')){$('#sceneExecutionRibbonBox').innerHTML=executionRibbonHtml(workbench,latestQuality);bindExecutionRibbon(workbench);}$('#statusGuards').textContent=`守卫 ${(q.guards||[]).length}`;ctx.state.problems=(q.guards||[]).filter(g=>g.severity==='error'||g.severity==='warning').map(g=>({summary:`${g.kind} · ${typeof g.detail==='string'?g.detail:'检查内容请打开质量面板'}`}));ctx.renderPanel();}
  function openGate(gid){const gate=progress.gates.find(g=>g.id===gid);if(gate)showGate(gate,{novelId:id,project,onSaved:refresh});}
  const nodes=flattenTree(initial.tree).filter(node=>!node.children?.length);selected=nodes.find(n=>n.status==='running')?.id
    || nodes.find(n=>n.kind==='book_direction'&&n.status==='waiting')?.id
    || nodes.find(n=>n.output)?.id||nodes.find(n=>!n.children?.length)?.id||'';if(currentNode()?.scene_id){sceneId=currentNode().scene_id;tab='text';}update(initial);renderTabs();await paintEditor();quality().catch(fail);const stop=watchProgress(id,update,error=>{if(ctx.alive())$('#statusConnection').innerHTML='<span class="status-dot offline"></span>重连中';});ctx.onCleanup(()=>stop());
}
function statusName(status){return {CONFIG_REQUIRED:'需要配置模型',RUNNING:'制作中',WAITING:'等待作者确认',REJECTED:'已退回',READY:'准备就绪',DONE:'当前任务已完成',FAILED:'任务失败',PAUSED:'已暂停',PAUSING:'等待当前调用结束后暂停',CANCELLED:'已取消',BLOCKED:'制作遇到阻碍',PLANNED:'等待开始'}[status]||status||'就绪';}
function actionName(action){return {choose:'选择方案',select:'选择方案',approve:'批准',confirm:'确认',accept:'接受本场',reject:'退回',revise:'请求修订',retry:'重试',cancel:'取消',allow:'允许变更',continue:'继续'}[action]||action;}
