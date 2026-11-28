import {api,enc,query} from '../api.js';
import {$,$$,esc,icon,empty,number,date,drawer,readable,loading,fail,busy,toast,confirmAction} from '../ui.js';
import {cover,decorateBooks} from '../components/BookCard.js';
import {trashButton} from '../components/NovelCache.js';
import {Timeline} from '../components/Timeline.js';
import {creationPlan} from '../components/CreationPlan.js';
import {renderContinuationHub,renderFinishDrawerHtml} from '../components/BookContinuation.js';
import {renderStoryCardsTab} from '../components/StoryCards.js';
import {openStyleReferenceDrawer} from '../components/CraftTools.js';
import {bookStats} from './book-stats.js';

function bookToc(project, novelId) {
  const volumes = project.volumes || [];
  if (!volumes.length && !project.chapters.length) {
    return empty('目录将在设计后生成','批准各级设计后，可以在这里查看卷、章与场景。','','book');
  }
  const scenesByChapter = new Map();
  for (const scene of project.scenes) {
    if (!scenesByChapter.has(scene.chapter_id)) scenesByChapter.set(scene.chapter_id, []);
    scenesByChapter.get(scene.chapter_id).push(scene);
  }
  const renderChapter = (chapter, heading) => {
    const scenes = (scenesByChapter.get(chapter.id) || []).map(scene =>
      `<a href="#/studio/${enc(novelId)}" data-read-scene="${esc(scene.id)}">
        <span>场 ${esc(scene.index)} · ${esc(scene.title || scene.card?.title || '未命名场景')}</span>
        <span class="tag ${scene.accepted_draft_id ? 'green' : ''}">
          ${scene.accepted_draft_id ? '已接受' : scene.latest_draft_id ? '草稿' : '未开始'}</span></a>`).join('');
    return `<section style="margin-bottom:24px"><${heading}>第${esc(chapter.index)}章 ${esc(chapter.title)}</${heading}>
      <div class="book-toc">${scenes || '<p class="muted">尚无场景</p>'}</div></section>`;
  };
  const assigned = new Set(volumes.flatMap(volume => volume.chapter_ids || []));
  const grouped = volumes.map(volume => {
    const ids = new Set(volume.chapter_ids || []);
    const chapters = project.chapters.filter(chapter => ids.has(chapter.id));
    return `<section class="card" style="margin-bottom:24px"><h3>${esc(volume.title)}</h3>
      ${chapters.map(chapter => renderChapter(chapter, 'h4')).join('') || '<p class="muted">尚无章节归入此卷</p>'}</section>`;
  }).join('');
  return grouped + project.chapters.filter(chapter => !assigned.has(chapter.id)).map(chapter => renderChapter(chapter, 'h3')).join('');
}
export async function render(ctx){if(!ctx.id){location.hash='#/library';return;}const [detail,genreData,progress]=await Promise.all([api.get(`/novels/${enc(ctx.id)}`,ctx.signal),api.get('/genres',ctx.signal),api.get(`/novels/${enc(ctx.id)}/progress`,ctx.signal)]);if(!ctx.alive())return;const rawProject=detail.project,project={...rawProject,scenes:(rawProject.scenes||[]).filter(s=>s.in_branch_workbench!==false).sort((a,b)=>(Number(a.chapter_index||0)-Number(b.chapter_index||0))||(Number(a.index||0)-Number(b.index||0)))},novel=decorateBooks([{...detail.novel,words:progress.words}],genreData.genres)[0];let tab=ctx.params.get('tab')||'toc',events=[];ctx.sidebar('作品详情',[[`studio/${enc(ctx.id)}`,'继续制作','pen'],['library?tab=done','返回成品仓库','library']],`<strong>${esc(novel.title)}</strong>所有设计、草稿版本与作者决定都属于这本书。`);ctx.content.innerHTML=`<div class="page"><div class="book-detail-head">${cover(novel)}<div class="grow"><div class="eyebrow">A STORY OF YOUR OWN</div><h1>${esc(novel.title)}</h1><p class="page-description">${number(novel.words)} 字 · ${project.chapters.length} 章 · ${project.scenes.length} 场</p><p class="page-description">立项于 ${esc(date(novel.created_at))}</p><div class="row wrap" style="margin-top:20px"><a class="button" href="#/studio/${enc(ctx.id)}">${icon('pen')} ${novel.status==='done'?'打开制作台':'继续制作'}</a><button class="secondary" id="readBook">${icon('book')} 阅读</button><button class="secondary" id="exportBook">${icon('download')} 导出</button><details class="menu"><summary class="icon-button" aria-label="作品更多操作">${icon('more')}</summary><div><button id="finishBook">完稿体检与完稿</button>${trashButton(novel)}</div></details></div></div></div><div class="tabs" id="bookTabs"></div><div id="bookContent"></div></div>`;
  function nav(){ $('#bookTabs').innerHTML=[['toc','目录'],['cards','设定卡片'],['continuation','连载与复盘'],['timeline','制作档案'],['brief','立项信息'],['stats','统计']].map(([key,label])=>`<button class="${tab===key?'active':''}" data-book-tab="${key}">${label}</button>`).join('');$$('[data-book-tab]').forEach(b=>b.onclick=()=>{tab=b.dataset.bookTab;paint().catch(fail);});}
  async function reloadProjectMeta(){
    const fresh=await api.get(`/novels/${enc(ctx.id)}`,ctx.signal);
    if(!ctx.alive())return;
    Object.assign(project,{...fresh.project,scenes:(fresh.project.scenes||[]).filter(s=>s.in_branch_workbench!==false).sort((a,b)=>(Number(a.chapter_index||0)-Number(b.chapter_index||0))||(Number(a.index||0)-Number(b.index||0)))});
  }
  function openBriefDrawer(){
    const latestBrief=project.briefs?.at(-1)||{};
    const initialText=latestBrief.text||novel.wizard?.idea||novel.wizard?.story_idea||'';
    const initialCons=latestBrief.constraints||'';
    drawer('修订全书 Brief 与硬约束（生成新版本）',`<form id="briefVersionForm" class="stack">
      <div class="notice">每次保存都会新增一个不可变 Brief 版本（当前 v${latestBrief.version||1}），供后续设计与写作任务绑定。</div>
      <label class="field"><span>故事核心构想（Brief 正文）</span><textarea name="text" rows="5" required>${esc(initialText)}</textarea></label>
      <label class="field"><span>作者硬约束（每条红线将作为最高裁决优先级）</span><textarea name="constraints" rows="4" placeholder="例如：单章单POV；严禁未铺垫巧合解围…">${esc(initialCons)}</textarea></label>
      <div class="row"><button type="submit" class="button">保存新版本 Brief</button></div>
    </form>`);
    $('#briefVersionForm').onsubmit=e=>{
      e.preventDefault();
      const fd=new FormData(e.target);
      busy(e.target.querySelector('[type=submit]'),async()=>{
        const saved=await api.post(`/projects/${enc(novel.project_dir)}/brief`,{text:String(fd.get('text')||''),constraints:String(fd.get('constraints')||'')});
        $('#drawer')?.close?.();
        toast(`Brief v${saved.version} 已保存`);
        await reloadProjectMeta();
        await paint();
      }).catch(fail);
    };
  }
  function openBibleDrawer(){
    drawer('新增设定备忘（Bible）',`<form id="bibleEntryForm" class="stack">
      <div class="form-grid">
        <label class="field"><span>备忘分类</span><select name="kind"><option value="world">世界规则 (world)</option><option value="character">人物备忘 (character)</option><option value="timeline">年表线索 (timeline)</option><option value="style">语言禁忌 (style)</option><option value="note">创作随记 (note)</option></select></label>
        <label class="field"><span>条目名称</span><input name="name" required placeholder="如：旧港潮汐封锁时刻表"></label>
      </div>
      <label class="field"><span>设定内容</span><textarea name="body" rows="5" required placeholder="记录供创作随时查阅的硬设定细节…"></textarea></label>
      <div class="row"><button type="submit" class="button">保存设定备忘</button></div>
    </form>`);
    $('#bibleEntryForm').onsubmit=e=>{
      e.preventDefault();
      const fd=new FormData(e.target);
      busy(e.target.querySelector('[type=submit]'),async()=>{
        await api.post(`/projects/${enc(novel.project_dir)}/bible`,{kind:String(fd.get('kind')||'note'),name:String(fd.get('name')||''),body:String(fd.get('body')||'')});
        $('#drawer')?.close?.();
        toast('设定备忘已添加');
        await reloadProjectMeta();
        await paint();
      }).catch(fail);
    };
  }
  async function executeFinish(){if(await confirmAction('确认完稿','确认标记为完稿并导出正式全书成品？完稿后将锁定修改。','标记完稿')){try{await api.post(`/novels/${enc(ctx.id)}/finish`);$('#drawer')?.close?.();toast('作品已完稿并导出成品');ctx.navigate();}catch(error){fail(error);}}}
  async function openFinishCheck(){drawer('完稿前全量体检',loading());try{const check=await api.get(`/novels/${enc(ctx.id)}/finish-check`);$('#drawerBody').innerHTML=renderFinishDrawerHtml(check);$('#confirmFinishBook')?.addEventListener('click',()=>executeFinish());}catch(error){$('#drawerBody').innerHTML=`<p class="error">${esc(error.message)}</p>`;fail(error);}}
  async function paint(){nav();const body=$('#bookContent');if(tab==='toc'){body.innerHTML=bookToc(project, ctx.id);$$('[data-read-scene]').forEach(a=>a.onclick=e=>{e.preventDefault();readScene(a.dataset.readScene);});}else if(tab==='cards'){body.innerHTML=loading();await renderStoryCardsTab(body,novel,project,{onReload:async()=>{await reloadProjectMeta();await paint();}},ctx.signal);}else if(tab==='continuation'){body.innerHTML=loading();const [cont,check]=await Promise.all([api.get(`/novels/${enc(ctx.id)}/continuation`,ctx.signal),api.get(`/novels/${enc(ctx.id)}/finish-check`,ctx.signal)]);if(!ctx.alive()||tab!=='continuation')return;renderContinuationHub(body,novel,cont,check,{onReload:()=>paint(),onFinish:()=>executeFinish()});}else if(tab==='brief'){const latestBrief=project.briefs?.at(-1),bibles=project.bible||[];body.innerHTML=`<div class="card stack" style="margin-bottom:20px"><div class="row spread wrap"><h3>故事构想与作者硬约束${latestBrief?` · Brief v${latestBrief.version}`:''}</h3>${novel.status!=='done'?'<div class="row wrap" style="gap:8px"><button type="button" class="secondary" id="editBriefBtn">修订 Brief 与硬约束</button><button type="button" class="ghost" id="editStyleRefBtn">本书语感规范与参照</button><button type="button" class="ghost" id="addBibleBtn">新增设定备忘（Bible）</button></div>':''}</div><p class="prose" style="font-size:14px;margin-top:8px">${esc(latestBrief?.text||novel.wizard?.idea||novel.wizard?.story_idea||'暂无立项构想')}</p>${latestBrief?.constraints?`<div class="notice" style="margin-top:8px"><strong>作者硬约束：</strong><span style="white-space:pre-wrap">${esc(latestBrief.constraints)}</span></div>`:''}</div>${bibles.length?`<section id="bookBibleList" class="card stack" style="margin-bottom:20px"><h3>设定备忘录（Bible · ${bibles.length} 条）</h3><div class="stack" style="gap:10px">${bibles.map(b=>`<div class="method-section"><div class="row spread wrap"><strong>${esc(b.name)}</strong><span class="tag blue">${esc(b.kind)}</span></div><p class="muted" style="margin:6px 0 0;white-space:pre-wrap">${esc(b.body)}</p></div>`).join('')}</div></section>`:''}${novel.wizard?.creation_plan?.version === 1 ? creationPlan(novel.wizard.creation_plan, novel.wizard) : '<div class="section-head"><h3>当时的创作选择</h3></div>'+readable(novel.wizard)}<details class="details"><summary>高级 · 立项原始记录</summary><pre class="raw-data">${esc(JSON.stringify(novel.wizard,null,2))}</pre></details>`;$('#editBriefBtn')?.addEventListener('click',openBriefDrawer);$('#editStyleRefBtn')?.addEventListener('click',()=>openStyleReferenceDrawer(ctx.id));$('#addBibleBtn')?.addEventListener('click',openBibleDrawer);}else if(tab==='timeline'){body.innerHTML=loading();events=(await api.get(`/novels/${enc(ctx.id)}/timeline`,ctx.signal)).events||[];if(!ctx.alive())return;body.innerHTML=`<div class="row" style="margin-bottom:24px"><label class="muted">筛选 <select id="timelineFilter" aria-label="制作档案筛选"><option value="">全部记录</option>${[...new Set(events.map(e=>e.kind))].map(k=>`<option value="${esc(k)}">${esc(k)}</option>`).join('')}</select></label><span class="muted">${events.length} 条真实记录</span></div><div id="bookTimeline"></div>`;function timeline(){const rows=events.filter(e=>!$('#timelineFilter').value||e.kind===$('#timelineFilter').value);$('#bookTimeline').innerHTML=rows.length?Timeline(rows):empty('暂无这类记录','制作过程中产生的操作与结果会自动留档。','','clock');$$('[data-event]').forEach(b=>b.onclick=()=>drawer('制作档案 · 当时记录',readable(rows[Number(b.dataset.event)].ref)+`<details class="details"><summary>高级 · 原始留痕</summary><pre class="raw-data">${esc(JSON.stringify(rows[Number(b.dataset.event)],null,2))}</pre></details>`));}$('#timelineFilter').onchange=timeline;timeline();}else{body.innerHTML=loading();const html=await bookStats(novel,project,ctx.signal);if(ctx.alive()&&tab==='stats')body.innerHTML=html;}}
  async function readScene(sid){const scene=project.scenes.find(s=>s.id===sid);const did=scene?.accepted_draft_id||scene?.latest_draft_id;if(!did){toast('这个场景还没有正文');return;}drawer(`场 ${scene.index} · ${scene.title||scene.card?.title||'正文'}`,loading());try{const draft=await api.get(`/projects/${enc(novel.project_dir)}/scenes/${enc(sid)}/drafts/${enc(did)}`);$('#drawerBody').innerHTML=`${!scene.accepted_draft_id?'<p class="tag amber">未接受草稿</p>':''}<div class="prose" style="margin-top:18px">${esc(draft.text)}</div>`;}catch(error){$('#drawerBody').innerHTML=`<p class="error">${esc(error.message)}</p>`;fail(error);}}
  $('#readBook').onclick=async()=>{const scenes=project.scenes.filter(s=>s.in_branch_manuscript!==false&&(s.accepted_draft_id||s.latest_draft_id));if(!scenes.length){toast('还没有可阅读的正文');return;}drawer(novel.title,loading());try{const parts=await Promise.all(scenes.map(async s=>({scene:s,draft:await api.get(`/projects/${enc(novel.project_dir)}/scenes/${enc(s.id)}/drafts/${enc(s.accepted_draft_id||s.latest_draft_id)}`)})));$('#drawerBody').innerHTML=parts.map(p=>`<h3 style="margin:24px 0">第${p.scene.chapter_index}章 · 场${p.scene.index} ${p.scene.accepted_draft_id?'':'（未接受草稿）'}</h3><div class="prose">${esc(p.draft.text)}</div>`).join('');}catch(error){$('#drawerBody').innerHTML=`<p class="error">${esc(error.message)}</p>`;fail(error);}};
  $('#exportBook').onclick=()=>{const branchName=novel.current_branch||'main',acceptedCount=project.scenes.filter(s=>s.in_branch_manuscript!==false&&s.accepted_draft_id).length;drawer('导出书稿',`<div class="row wrap" style="gap:6px;margin-bottom:10px"><span class="tag ${branchName==='main'?'green':'amber'}">${branchName==='main'?'导出分支：正式主线（main）':`导出分支：候选 ${esc(branchName)}`}</span><span class="tag blue">已接受 ${acceptedCount} 场</span></div><p class="muted">导出当前工作分支已接受的正文，并同步保存副本至项目「成品」目录。按卷导出仅在已批准方案记录了章节归属时提供。</p><div class="stack" style="margin-top:24px"><label class="field"><span>格式</span><select id="exportFormat"><option value="txt">纯文本 TXT</option><option value="md">Markdown</option></select></label><label class="field"><span>范围</span><select id="exportScope"><option value="book">整本小说</option>${(project.volumes||[]).filter(v=>v.chapter_ids?.length).map(v=>`<option value="volume:${esc(v.id)}">按卷 · ${esc(v.title)}</option>`).join('')}${project.chapters.map(c=>`<option value="chapter:${esc(c.id)}">第${c.index}章 ${esc(c.title)}</option>`).join('')}</select></label><button class="secondary" id="downloadExport">${icon('download')} 下载书稿</button></div>`);$('#downloadExport').onclick=e=>busy(e.currentTarget,async()=>{const response=await fetch(`/api/novels/${enc(ctx.id)}/export?${query({fmt:$('#exportFormat').value,scope:$('#exportScope').value})}`);if(!response.ok){const data=await response.json();throw new Error(data.error||'导出失败');}const blob=await response.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`${novel.title.replace(/[\\/:*?"<>|]/g,'_')}.${$('#exportFormat').value}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('书稿已导出');});};
  $('#finishBook').onclick=()=>openFinishCheck();await paint();}
