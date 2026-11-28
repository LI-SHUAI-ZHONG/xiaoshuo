import {api,enc,query} from '../api.js';
import {$,$$,esc,icon,empty,loading,readable,drawer,fail,busy,toast} from '../ui.js';
import {slotName,STEPS} from '../components/WizardStep.js';
import {RecCard} from '../components/RecCard.js';
import {renderMethods} from './methods.js';
import {renderPrerequisites} from './prerequisites.js';
import {analysisCatalogHtml} from './corpus_view.js';
export async function render(ctx){const page=ctx.subpage||'types';ctx.sidebar('知识库',[['kb/types','类型知识库','brain'],['kb/decomposition','拆解条目与方法论','book'],['kb/prerequisites','步骤资料需求蓝图','list'],['kb/items','类型资料库','layers'],['kb/search','高级检索','search']],'<strong>让经验成为可用的方法</strong>先看每个制作步骤需要什么资料，再按「读取→检索→作用性→方式性」拆解参考作品，把不同性质的资料绑定到准确步骤。');const titles={types:'类型知识库',items:'类型资料库',prerequisites:'步骤资料需求蓝图与前置',decomposition:'拆解条目与步骤绑定',legacy:'历史局部短文',upgrades:'历史升级记录',search:'高级检索'};ctx.content.innerHTML=`<div class="page"><div class="page-heading"><div><div class="eyebrow">KNOWLEDGE & CRAFT</div><h1>${titles[page]||titles.types}</h1><p class="page-description">${{types:'维护可核对的类型定义与识别特征。',items:'按制作步骤、生产任务、层级和设计产物组织可复用方法。',prerequisites:'查看 14 个设计步骤与写作/审稿的资料需求分类、拆解采集绑定、库内方法覆盖率与工作流前置干跑台账。',legacy:'保留历史短文、证据及统计；完整方法需要另行补齐与审核。',decomposition:'按各制作步骤所需资料组织拆解条目：先读取与检索，再分别判定作用性与方式性，并绑定到对应步骤。',upgrades:'查阅局部短文的升级记录与当时的审核依据。',search:'需要查证时，在这里检索六大资料与 F2 台账。'}[page]}</p></div></div><div id="kbContent"></div></div>`;if(page==='decomposition'){
    const catalog=await api.get('/corpus/catalog',ctx.signal);
    if(!ctx.alive())return;
    const natures=(catalog.material_natures||[]).length?`<section class="card" style="margin-bottom:20px"><h3>资料性质分类（不同用途绑定不同制作步骤）</h3><div class="stack" style="margin-top:10px">${catalog.material_natures.map(n=>`<div><strong>${esc(n.name)}</strong>：<span class="muted">${esc(n.description)}</span></div>`).join('')}</div></section>`:'';
    $('#kbContent').innerHTML=natures+analysisCatalogHtml(catalog)+`<div class="row wrap" style="margin-top:16px"><a class="button" href="#/kb/prerequisites">查看 17 步资料需求蓝图</a><a class="secondary" href="#/staging">打开作品拆解</a><a class="secondary" href="#/kb/items">按步骤查看制作方法</a></div><details class="details" style="margin-top:16px"><summary>历史资料</summary><a class="text-link" href="#/kb/legacy">局部短文与原文</a> · <a class="text-link" href="#/kb/upgrades">升级审核记录</a></details>`;
  }else if(page==='items')await renderMethods(ctx);else if(page==='prerequisites')await renderPrerequisites(ctx);else if(page==='legacy')await items(ctx);else if(page==='upgrades')await upgrades(ctx);else if(page==='search')search(ctx);else await types(ctx);}
async function types(ctx){const data=await api.get('/genres',ctx.signal);if(!ctx.alive())return;const flat=data.genres.flatMap(g=>[g,...g.children]);$('#kbContent').innerHTML=`<div class="row" style="margin-bottom:24px"><select id="kbType" aria-label="选择类型" class="grow">${flat.map(g=>`<option value="${esc(g.id)}" ${ctx.params.get('type')===g.id?'selected':''}>${g.parent_id?'　':''}${esc(g.name)}</option>`).join('')}</select><a class="secondary" id="typeAtlas">查看图鉴</a></div><div id="typeForm"></div>`;let sequence=0;async function load(){const seq=++sequence;const id=$('#kbType').value;$('#typeAtlas').href=`#/atlas/${enc(id)}`;$('#typeForm').innerHTML=loading();const row=await api.get(`/kb/types/${enc(id)}`,ctx.signal);if(!ctx.alive()||seq!==sequence)return;$('#typeForm').innerHTML=`<form id="saveTypeForm" class="stack"><div class="notice">每次保存都会增加知识版本。包含、排除与特征每行填写一条；识别建议不会替代作者审核。</div><label class="field"><span>定义</span><textarea name="definition" rows="4" placeholder="待补充">${esc(row.definition)}</textarea></label><div class="form-grid">${[['includes','包含项'],['excludes','排除项'],['features','区别特征（用于自动建议）'],['examples','典型元素'],['counterexamples','反例']].map(([key,label])=>`<label class="field"><span>${label}</span><textarea name="${key}" rows="4" placeholder="每行一条">${esc((row[key]||[]).join('\n'))}</textarea></label>`).join('')}</div><div class="row spread"><span class="muted">当前版本 ${row.version}</span><button class="button" type="submit">${icon('check')} 保存类型知识</button></div></form>`;$('#saveTypeForm').onsubmit=e=>{e.preventDefault();const body={version:row.version};new FormData(e.target).forEach((v,k)=>body[k]=k==='definition'?v:String(v).split('\n').map(x=>x.trim()).filter(Boolean));busy(e.target.querySelector('button[type=submit]'),async()=>{await api.post(`/kb/types/${enc(id)}`,body);toast('类型知识已保存');await load();});};}$('#kbType').onchange=()=>load().catch(fail);await load();}
async function items(ctx){const genreData=await api.get('/genres',ctx.signal);if(!ctx.alive())return;$('#kbContent').innerHTML=`<div class="row wrap" style="margin-bottom:24px"><select id="itemSlot" aria-label="资料板块">${STEPS.slice(0,8).map(s=>`<option value="${s.slot}">${s.name}</option>`).join('')}</select><select id="itemType" aria-label="资料类型"><option value="">全部类型</option>${genreData.genres.map(g=>`<option value="${esc(g.id)}">${esc(g.name)}</option>`).join('')}</select><span class="muted">同一本书、同一用法最多计一次</span></div><div id="itemResults"></div>`;let serial=0;async function load(){const seq=++serial;const slot=$('#itemSlot').value,types=$('#itemType').value?[$('#itemType').value]:[];$('#itemResults').innerHTML=loading();const [data,recs]=await Promise.all([api.get(`/kb/items?${query({slot,types})}`,ctx.signal),api.get(`/recommend?${query({slot,types})}`,ctx.signal)]);if(!ctx.alive()||seq!==serial)return;$('#itemResults').innerHTML=`<div class="rec-grid">${recs.recommendations.map((r,i)=>RecCard(r,i)).join('')}</div>${data.stats.length?`<div class="table-wrap"><table class="data-table"><thead><tr><th>板块 / 选项</th><th>拆解用法</th><th>审稿后采用</th><th>来源作品</th><th></th></tr></thead><tbody>${data.stats.map((s,i)=>`<tr><td>${esc(slotName(s.slot||slot))} · ${esc(s.name)}</td><td>${s.corpus_count}</td><td>${s.adopt_count}</td><td>${(s.books||[]).length} 本</td><td><button class="ghost" data-item-row="${i}">展开条目</button></td></tr>`).join('')}</tbody></table></div>`:empty('没有符合条件的历史短文','当前拆解内容可在拆解条目页查看。','<a class="secondary" href="#/staging">前往预存库</a>','layers')}`;async function detail(key){let rows=data.items.filter(i=>i.option_key===key);if(!rows.length){const rec=recs.recommendations.find(r=>r&&r.option_key===key);const allSlot=await api.get(`/kb/items?${query({slot})}`,ctx.signal);const bookIds=new Set((rec?.books||[]).map(b=>b.id));rows=allSlot.items.filter(i=>i.option_key===key&&(!bookIds.size||bookIds.has(i.book_id)));}drawer('用法与原文证据',rows.length?rows.map(i=>`<section class="card" style="margin-bottom:16px"><h3>${esc(i.name||i.option_key)}</h3><p style="margin:12px 0">${esc(i.usage_text)}</p><blockquote class="evidence">${esc(i.evidence?.quote||'')}</blockquote><p class="muted">${esc(i.book_title||i.book_id)} · 位置 ${i.evidence?.start??'—'}–${i.evidence?.end??'—'}</p><a class="text-link" href="#/staging/${enc(i.book_id)}?view=legacy" data-source-book>查看来源作品 →</a></section>`).join(''):empty('暂无更多条目证据','请前往预存库查看来源作品。','','layers'));$$('[data-source-book]').forEach(a=>a.onclick=()=>$('#drawer').close());}$$('[data-item-row]').forEach(b=>b.onclick=()=>detail(data.stats[Number(b.dataset.itemRow)].option_key).catch(fail));$$('#itemResults [data-rec]').forEach(b=>b.onclick=()=>detail(b.dataset.rec).catch(fail));}$('#itemSlot').onchange=()=>load().catch(fail);$('#itemType').onchange=()=>load().catch(fail);await load();}
async function upgrades(ctx){const data=await api.get('/kb/upgrades',ctx.signal);if(!ctx.alive())return;const rows=data.upgrades||[];$('#kbContent').innerHTML=`<div class="notice" style="margin-bottom:24px">这里保存局部短文的历史升级审核。新建制作任务使用已批准的结构拆解方法。</div><div class="tabs" id="upgradeTabs"><button class="active" data-upgrade-status="pending">待批准</button><button data-upgrade-status="approved">已批准</button><button data-upgrade-status="rejected">已驳回</button></div><div id="upgradeList"></div>`;function paint(status){const selected=rows.filter(u=>u.status===status);$('#upgradeList').innerHTML=selected.length?selected.map(u=>`<section class="card" style="margin-bottom:16px"><div class="row spread"><h3>${esc(u.name||u.usage_text||u.id)}</h3><span class="tag">${{enhance:'增强',fill:'补缺',new:'新增'}[u.kind]||esc(u.kind)}</span></div><p class="muted" style="margin:14px 0">${esc(u.reason||u.description||'与现有资料比对后提出，等待作者核对。')}</p><div class="row wrap"><button class="secondary" data-upgrade-detail="${esc(u.id)}">查看依据</button></div></section>`).join(''):empty('暂无'+({pending:'待批准',approved:'已批准',rejected:'已驳回'}[status])+'候选','本页记录局部短文历史升级的审核情况。','','spark');$$('[data-upgrade-detail]').forEach(b=>b.onclick=()=>drawer('升级候选依据',readable(rows.find(u=>u.id===b.dataset.upgradeDetail))));}$$('[data-upgrade-status]').forEach(b=>b.onclick=()=>{$$('[data-upgrade-status]').forEach(x=>x.classList.toggle('active',x===b));paint(b.dataset.upgradeStatus);});paint('pending');}
function search(ctx){
  const stageOpts=[
    ['','全部创作环节'],['world_design','世界规则与限制定稿'],['character_design','核心人物与弧光起点'],
    ['static_relations','人物关系与势力张力'],['plot_design','故事大纲、开篇承诺与卷章切分'],['event_design','本章事件链与因果触发'],
    ['action_design','人物行动博弈与试错代价'],['scene_design','场景卡与 POV 边界排布'],['state_transition','场内状态变化与代价'],
    ['state_propagation','状态连锁传播预案'],['anchor_design','具象动作锚点与感官节拍'],['expression_design','叙述距离、对白与文风指导'],
    ['bind_scope','冻结可写场景工作包'],['writer','场景正文起草 (15)'],['review','事实与读者独立审稿 (16)'],
    ['type_selection','前置契约 · 立项类型冻结'],['type_adaptation','前置契约 · 多类型融合'],
  ];
  let offset=0,limit=40,ledgerFacets={dispositions:{},corpora:{}};
  $('#kbContent').innerHTML=`<form id="kbSearchForm" class="stack" style="gap:12px">
    <div class="row wrap">
      <input class="grow" id="advancedQuery" placeholder="输入原文关键词、条目编号或资料名称（可留空按步骤/状态筛选）…" aria-label="原文检索关键词">
      <select id="advancedScope" aria-label="检索范围"><option value="materials">六大资料（22,941 条）</option><option value="ledger">F2 问题台账</option></select>
      <button class="button" type="submit">${icon('search')} 检索</button>
    </div>
    <div id="kbSearchFilters" class="row wrap"></div>
  </form>
  <div id="kbSearchPagination" style="margin-top:16px"></div>
  <div id="advancedResults" style="margin-top:14px">${empty('按需查证六大资料与 F2 台账','可按制作步骤、资料就绪状态（design_ready / reference / blocked）、资料域或台账处置状态精准筛选。','','search')}</div>`;

  function renderFilterControls(){
    const isMat=$('#advancedScope').value==='materials';
    const prevStage=$('#materialStageFilter')?.value||'';
    const prevState=$('#materialStateFilter')?.value||'';
    const prevProf=$('#materialProfileFilter')?.value||'';
    const prevDisp=$('#ledgerDispositionFilter')?.value||'';
    const prevCorp=$('#ledgerCorpusFilter')?.value||'';
    if(isMat){
      $('#kbSearchFilters').innerHTML=`
        <label class="field"><span>路由步骤</span><select id="materialStageFilter">${stageOpts.map(([v,l])=>`<option value="${esc(v)}" ${v===prevStage?'selected':''}>${esc(l)}</option>`).join('')}</select></label>
        <label class="field"><span>资料状态</span><select id="materialStateFilter">
          <option value="" ${!prevState?'selected':''}>全部状态</option>
          <option value="design_ready" ${prevState==='design_ready'?'selected':''}>design_ready（可直接设计）</option>
          <option value="reference" ${prevState==='reference'?'selected':''}>reference（参考需实例化）</option>
          <option value="blocked" ${prevState==='blocked'?'selected':''}>blocked（原义待核隔离）</option>
        </select></label>
        <label class="field"><span>资料域（Profile）</span><input id="materialProfileFilter" value="${esc(prevProf)}" placeholder="如 character / world / anchor"></label>`;
    }else{
      const disps=Object.entries(ledgerFacets.dispositions||{});
      const corps=Object.entries(ledgerFacets.corpora||{});
      $('#kbSearchFilters').innerHTML=`
        <label class="field"><span>处置状态（Disposition）</span><select id="ledgerDispositionFilter">
          <option value="">全部状态</option>
          ${disps.map(([k,c])=>`<option value="${esc(k)}" ${k===prevDisp?'selected':''}>${esc(k)}（${c}）</option>`).join('')}
          ${!disps.length?`<option value="open" ${prevDisp==='open'?'selected':''}>open</option><option value="resolved" ${prevDisp==='resolved'?'selected':''}>resolved</option>`:''}
        </select></label>
        <label class="field"><span>来源分卷（Corpus）</span><select id="ledgerCorpusFilter">
          <option value="">全部分卷</option>
          ${corps.map(([k,c])=>`<option value="${esc(k)}" ${k===prevCorp?'selected':''}>${esc(k)}（${c}）</option>`).join('')}
        </select></label>`;
    }
  }

  async function executeSearch(){
    const source=$('#advancedScope').value;
    const params=source==='materials'
      ?{q:$('#advancedQuery').value,stage:$('#materialStageFilter')?.value||'',state:$('#materialStateFilter')?.value||'',profile:($('#materialProfileFilter')?.value||'').trim(),limit,offset}
      :{q:$('#advancedQuery').value,disposition:$('#ledgerDispositionFilter')?.value||'',corpus:$('#ledgerCorpusFilter')?.value||'',limit,offset};
    const data=await api.get(`/${source}/search?${query(params)}`,ctx.signal);
    if(!ctx.alive())return;
    if(source==='ledger'&&data.facets){ledgerFacets=data.facets;renderFilterControls();}
    const rows=data.items||data.results||data.rows||data.sources||data.issues||[];
    const total=Number(data.total||rows.length||0);
    const startIdx=total?offset+1:0,endIdx=Math.min(total,offset+rows.length);
    $('#kbSearchPagination').innerHTML=total?`<div class="row spread wrap"><span class="muted">显示第 ${startIdx}–${endIdx} 条 / 共 ${total} 条</span><div class="row" style="gap:8px"><button type="button" class="secondary" id="kbPrevPage" ${offset<=0?'disabled':''}>上一页</button><button type="button" class="secondary" id="kbNextPage" ${offset+limit>=total?'disabled':''}>下一页</button></div></div>`:'';
    $('#kbPrevPage')?.addEventListener('click',()=>{offset=Math.max(0,offset-limit);executeSearch().catch(fail);});
    $('#kbNextPage')?.addEventListener('click',()=>{offset+=limit;executeSearch().catch(fail);});
    $('#advancedResults').innerHTML=rows.length?rows.map((r,i)=>`<div class="card" style="margin-bottom:12px">
      <div class="row spread wrap">
        <h3>${esc(r.key||r.name||r.title||r.source_id||r.issue_id||r.id||'检索记录')}</h3>
        <div class="row wrap" style="gap:6px">
          ${r.profile?`<span class="tag blue">${esc(r.profile)}</span>`:''}
          ${r.state?`<span class="tag ${r.state==='design_ready'?'green':r.state==='reference'?'amber':''}">${esc(r.state)}</span>`:''}
          ${r.disposition?`<span class="tag">${esc(r.disposition)}</span>`:''}
        </div>
      </div>
      <p class="muted" style="margin:10px 0;white-space:pre-wrap">${esc(r.meaning||r.snippet||r.text||r.summary||r.problem||r.description||r.source_key||'')}</p>
      ${r.stages?.length?`<small class="muted">路由步骤：${r.stages.map(esc).join('、')}</small><br>`:''}
      ${r.path?`<small class="faint">来源路径：${esc(r.path)}</small><br>`:''}
      <button class="ghost" style="margin-top:6px" data-search-row="${i}">查看详情与本步用法</button>
    </div>`).join(''):empty('没有匹配记录','尝试调整筛选条件、缩短关键词或切换检索范围。','','search');

    $$('[data-search-row]').forEach(b=>b.onclick=()=>{
      const row=rows[Number(b.dataset.searchRow)];
      if(source==='materials'&&row.id){
        drawer('六大资料原文查证与各步用法',loading());
        api.get(`/materials/detail?${query({id:row.id})}`,ctx.signal).then(detail=>{
          const usages=Object.entries(detail.step_usages||{});
          $('#drawerBody').innerHTML=`<div class="stack" style="gap:12px">
            <div class="row wrap" style="gap:6px">
              <span class="tag blue">${esc(detail.source?.profile||'')}</span>
              <span class="tag ${detail.source_state==='design_ready'?'green':'amber'}">${esc(detail.source_state||'')}</span>
              <span class="tag">使用方式：${esc(detail.use_mode||'')}</span>
              <span class="tag">语义子句：${detail.semantic_clauses_count||0}</span>
            </div>
            ${(detail.routed_stages||[]).length?`<p class="muted" style="margin:0;font-size:12px"><strong>绑定步骤：</strong>${detail.routed_stages.map(esc).join(' → ')}</p>`:''}
            ${usages.length?`<div class="card stack"><strong>各制作步骤【本步用法】说明</strong>${usages.map(([st,txt])=>`<div><span class="tag blue">${esc(st)}</span><p class="muted" style="margin:6px 0 0;white-space:pre-wrap;font-size:12px">${esc(txt)}</p></div>`).join('')}</div>`:''}
            ${detail.meaning?`<div class="card"><strong>核定释义</strong><p style="margin:6px 0 0;white-space:pre-wrap;font-size:13px">${esc(detail.meaning)}</p></div>`:''}
            ${detail.original_text?`<div class="card"><strong>原始条文全文</strong><pre class="raw-data" style="white-space:pre-wrap">${esc(detail.original_text)}</pre></div>`:''}
            <details class="details"><summary>原始定位、问题台账与完整字段</summary><pre class="raw-data">${esc(JSON.stringify(detail,null,2))}</pre></details>
          </div>`;
        }).catch(err=>{$('#drawerBody').innerHTML=`<p class="error">${esc(err.message)}</p>`;});
      }else{
        drawer('台账记录查证',readable(row)+`<details class="details"><summary>原始定位与字段</summary><pre class="raw-data">${esc(JSON.stringify(row,null,2))}</pre></details>`);
      }
    });
  }

  renderFilterControls();
  $('#advancedScope').onchange=()=>{offset=0;renderFilterControls();executeSearch().catch(fail);};
  $('#kbSearchForm').onsubmit=e=>{e.preventDefault();offset=0;busy(e.target.querySelector('button[type=submit]'),()=>executeSearch());};
}
