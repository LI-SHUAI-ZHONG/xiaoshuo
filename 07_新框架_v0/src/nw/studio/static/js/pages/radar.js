import {api,enc} from '../api.js';
import {$,$$,esc,empty,loading,drawer,busy,toast,fail} from '../ui.js';

const FEASIBILITY_LABEL={high:'高可行',medium:'中（受限/首扫）',low:'低'};
const FEASIBILITY_CLASS={high:'green',medium:'amber',low:''};
const VERIFY_LABEL={verified:'已拆文验证',pending_deconstruction:'待拆文验证',unconfirmed:'待复核'};
const VERIFY_CLASS={verified:'green',pending_deconstruction:'amber',unconfirmed:''};

export async function render(ctx){
  let data=null;
  let tab=['collect','aggregate','topics','playbooks'].includes(ctx.params.get('tab'))?ctx.params.get('tab'):'collect';
  let platformFilter=ctx.params.get('platform')||'';
  let diffResult=null;
  let fetchNote='';
  let recScale='long',recExp='beginner',recGenre='',recList=null;

  ctx.sidebar('扫榜雷达与选题决策',[
    ['radar?tab=collect','扫榜采集与导入','spark'],
    ['radar?tab=aggregate','跨榜聚合与趋势差分','layers'],
    ['radar?tab=topics','选题决策与拆解验证','book'],
    ['radar?tab=playbooks','赚钱平台与榜单规则','shield'],
    ['staging','进入预存库拆书','inbox'],
    ['atlas','对照类型图鉴','atlas'],
  ],'<strong>扫榜 → 拆书 → 创作变现闭环</strong>内置 6 大主流变现平台（番茄/起点/七猫/晋江/知乎盐言/刺猬猫）最新签约、全勤、晋级与榜单规则；采集仅走公开接口，遇风控自动引导粘贴导入。');

  async function load(){
    const q=platformFilter?`?platform=${enc(platformFilter)}`:'';
    data=await api.get(`/radar${q}`,ctx.signal);
    if(!ctx.alive())return;
    paint();
  }

  function paint(){
    const snaps=data.snapshots||[];
    const agg=data.aggregation||{snapshot_count:0,skipped_duplicates:[],platforms:[]};
    const topics=data.topics||[];
    const platforms=data.platforms||[];
    ctx.content.innerHTML=`<div class="page">
      <div class="page-heading">
        <div>
          <div class="eyebrow">MARKET RADAR · CHART AGGREGATION · TOPIC DECISIONS</div>
          <h1>扫榜雷达与选题决策</h1>
          <p class="page-description">多平台实时公开采集 + 万能粘贴导入 → 跨榜去重聚合与期次趋势差分 → 证据约束选题（拆书后自动回填验证）</p>
        </div>
        <div class="row wrap">
          <select id="radarPlatformFilter" aria-label="按平台筛选">
            <option value="">全部平台</option>
            ${platforms.map(p=>`<option value="${esc(p.id)}" ${platformFilter===p.id?'selected':''}>${esc(p.name)}（${esc(p.full_name)}）</option>`).join('')}
          </select>
          <a class="secondary" href="#/staging">去预存库拆书</a>
        </div>
      </div>

      <div class="row wrap corpus-toolbar">
        <span class="tag blue">已存快照 ${snaps.length} 份</span>
        <span class="tag">覆盖平台 ${(agg.platforms||[]).length} 个</span>
        <span class="tag green">已验证选题 ${topics.filter(t=>t.verification_status==='verified').length}</span>
        <span class="tag amber">待拆文验证 ${topics.filter(t=>t.verification_status==='pending_deconstruction').length}</span>
      </div>

      <div class="tabs corpus-tabs">
        ${[['collect','扫榜采集与万能导入'],['aggregate','跨榜聚合与趋势差分'],['topics','选题决策与拆解验证'],['playbooks','赚钱平台与榜单规则库（6大平台）']].map(([id,label])=>
          `<button data-radar-tab="${id}" class="${tab===id?'active':''}">${label}</button>`
        ).join('')}
      </div>
      <div id="radarTabBody"></div>
    </div>`;

    $('#radarPlatformFilter').onchange=e=>{
      platformFilter=e.target.value;
      load().catch(fail);
    };
    $$('[data-radar-tab]').forEach(btn=>btn.onclick=()=>{
      tab=btn.dataset.radarTab;
      $$('[data-radar-tab]').forEach(t=>t.classList.toggle('active',t===btn));
      paintTab();
    });
    paintTab();
  }

  function paintTab(){
    if(tab==='collect') paintCollect();
    else if(tab==='aggregate') paintAggregate();
    else if(tab==='playbooks') paintPlaybooks();
    else paintTopics();
  }

  function paintCollect(){
    const platforms=data.platforms||[];
    const livePlatforms=platforms.filter(p=>(p.live_lists||[]).length>0);
    const snaps=data.snapshots||[];
    const initialPid=livePlatforms[0]?.id||'qidian';
    const initialLists=livePlatforms.find(p=>p.id===initialPid)?.live_lists||[];

    $('#radarTabBody').innerHTML=`<div class="stack">
      <div class="grid two">
        <section class="card stack">
          <div>
            <h3>实时公开采集（公开 SSR / JSON 接口）</h3>
            <p class="muted">直接请求站点公开排行榜并入库快照。如目标站点触发风控或人机验证，系统会如实提示，绝不绕过，请改用右侧万能粘贴导入。</p>
          </div>
          <form id="radarFetchForm" class="stack">
            <div class="grid two">
              <label class="field"><span>目标平台</span>
                <select name="platform" id="fetchPlatformSel">
                  ${livePlatforms.map(p=>`<option value="${esc(p.id)}">${esc(p.name)}（${esc(p.full_name)}）</option>`).join('')}
                </select>
              </label>
              <label class="field"><span>榜单类型</span>
                <select name="rank_type" id="fetchRankSel">
                  ${initialLists.map(l=>`<option value="${esc(l.id)}">${esc(l.label)}</option>`).join('')}
                </select>
              </label>
            </div>
            <label class="field" id="fetchPagesWrap" style="display:none"><span>采集页数（七猫书库 1-5 页）</span>
              <input name="pages" type="number" min="1" max="5" value="2">
            </label>
            <div class="row wrap">
              <button class="button" type="submit">立即采集并入库快照</button>
            </div>
          </form>
          ${fetchNote?`<p class="notice">${esc(fetchNote)}</p>`:''}
        </section>

        <section class="card stack">
          <div>
            <h3>万能榜单粘贴 / 文件导入（零风控）</h3>
            <p class="muted">支持 Markdown（含 oh-story 扫榜格式）、CSV、JSON，或直接从浏览器排行榜页面全选复制粘贴。</p>
          </div>
          <form id="radarImportForm" class="stack">
            <div class="grid two">
              <label class="field"><span>平台</span>
                <select name="platform">
                  <option value="">自动识别</option>
                  ${platforms.map(p=>`<option value="${esc(p.id)}">${esc(p.name)}</option>`).join('')}
                </select>
              </label>
              <label class="field"><span>榜单名称</span>
                <input name="list_name" placeholder="例如：黑马新书榜 / 月票榜 / 盐言热榜">
              </label>
            </div>
            <div class="grid two">
              <label class="field"><span>格式</span>
                <select name="format">
                  <option value="auto">自动识别（推荐）</option>
                  <option value="markdown">Markdown 榜单</option>
                  <option value="csv">CSV 表格</option>
                  <option value="json">JSON 数据</option>
                  <option value="paste">网页复制文本</option>
                </select>
              </label>
              <label class="field"><span>从本地文件载入（可选）</span>
                <input type="file" id="radarFileInput" accept=".md,.txt,.csv,.json">
              </label>
            </div>
            <label class="field"><span>榜单原文内容</span>
              <textarea name="text" id="radarImportText" rows="6" required placeholder="粘贴榜单内容，例如：&#10;1. 《诡秘之主》 | 爱潜水的乌贼 | 玄幻 | 连载 | 446万字 | 12.5万月票&#10;或直接粘贴 Markdown / CSV / JSON"></textarea>
            </label>
            <div class="row wrap">
              <button class="button" type="submit">解析并入库快照</button>
            </div>
          </form>
        </section>
      </div>

      <section class="card stack">
        <div class="row spread wrap">
          <h3>已入库榜单快照（${snaps.length}）</h3>
          ${snaps.length?`<button class="secondary" id="gotoAggFromSnaps">前往跨榜聚合与趋势分析 →</button>`:''}
        </div>
        ${snaps.length?`<div class="table-wrap"><table class="data-table">
          <thead><tr><th>日期</th><th>平台</th><th>榜单名称</th><th>来源方式</th><th>条目数</th><th>质量状态</th><th>操作</th></tr></thead>
          <tbody>${snaps.map(s=>`<tr>
            <td>${esc(s.captured_date)}</td>
            <td><strong>${esc(s.platform_name)}</strong></td>
            <td>${esc(s.list_name)}</td>
            <td><span class="muted">${esc(s.source_mode)}</span></td>
            <td>${s.entry_count}</td>
            <td><span class="tag ${s.quality_status==='[OK]'?'green':'amber'}">${esc(s.quality_status)}</span>${(s.quality_notes||[]).length?` <small class="muted">${esc(s.quality_notes.join('；'))}</small>`:''}</td>
            <td><button class="ghost" data-snap-detail="${esc(s.id)}">查看条目</button></td>
          </tr>`).join('')}</tbody>
        </table></div>`:empty('尚无榜单快照','请通过上方实时公开采集，或粘贴/上传一份排行榜数据开始市场雷达分析。','','spark')}
      </section>
    </div>`;

    const syncRankOptions=()=>{
      const pid=$('#fetchPlatformSel')?.value;
      const p=livePlatforms.find(x=>x.id===pid);
      const lists=p?.live_lists||[];
      $('#fetchRankSel').innerHTML=lists.map(l=>`<option value="${esc(l.id)}">${esc(l.label)}</option>`).join('');
      $('#fetchPagesWrap').style.display=pid==='qimao'?'block':'none';
    };
    $('#fetchPlatformSel')?.addEventListener('change',syncRankOptions);
    syncRankOptions();

    $('#radarFileInput')?.addEventListener('change',async e=>{
      const f=e.target.files?.[0];
      if(!f)return;
      $('#radarImportText').value=await f.text();
      toast(`已读取文件：${f.name}`);
    });

    $('#radarFetchForm').onsubmit=e=>{
      e.preventDefault();
      busy(e.target.querySelector('button[type=submit]'),async()=>{
        const fd=new FormData(e.target);
        const res=await api.post('/radar/fetch',{
          platform:fd.get('platform'),
          rank_type:fd.get('rank_type'),
          pages:Number(fd.get('pages')||2),
        });
        if(res.fetched?.ok && res.saved){
          fetchNote=`采集成功：${res.saved.platform_name}·${res.saved.list_name}（共 ${res.saved.entry_count} 条）已入库。`;
          toast('榜单采集成功');
          await load();
        }else{
          fetchNote=`未能直接采集：${res.fetched?.reason||'站点返回空数据或触发风控'}。系统不绕过验证码，请使用右侧万能粘贴导入。`;
          paintCollect();
        }
      });
    };

    $('#radarImportForm').onsubmit=e=>{
      e.preventDefault();
      busy(e.target.querySelector('button[type=submit]'),async()=>{
        const fd=new FormData(e.target);
        const res=await api.post('/radar/import',{
          platform:fd.get('platform'),
          list_name:fd.get('list_name'),
          format:fd.get('format'),
          text:fd.get('text'),
        });
        toast(`已入库：${res.saved.platform_name} · ${res.saved.list_name}（${res.saved.entry_count} 条）`);
        await load();
      });
    };

    $('#gotoAggFromSnaps')?.addEventListener('click',()=>{
      tab='aggregate';
      $$('[data-radar-tab]').forEach(t=>t.classList.toggle('active',t.dataset.radarTab===tab));
      paintTab();
    });

    $$('[data-snap-detail]').forEach(btn=>btn.onclick=()=>busy(btn,async()=>{
      const snap=await api.get(`/radar/snapshots/${enc(btn.dataset.snapDetail)}`,ctx.signal);
      drawer(`${snap.platform_name} · ${snap.list_name}（${snap.captured_date}）`,
        `<p class="muted">共 ${snap.entry_count} 条 · 来源 ${esc(snap.source_mode)} · ${esc(snap.quality_status)}</p>
        <div class="table-wrap"><table class="data-table">
          <thead><tr><th>#</th><th>书名 / 作者</th><th>平台题材 / 映射类型</th><th>指标</th><th>字数</th><th>标签</th></tr></thead>
          <tbody>${(snap.entries||[]).map(e=>`<tr>
            <td>${e.rank}</td>
            <td><strong>${esc(e.title)}</strong>${e.author?`<br><small class="muted">${esc(e.author)}</small>`:''}${e.desc_text?`<br><small class="faint">${esc(e.desc_text.slice(0,70))}</small>`:''}</td>
            <td>${esc(e.genre_raw)}${(e.mapped_type_ids||[]).length?`<br><small class="muted">${esc(e.mapped_type_ids.join(', '))}</small>`:''}</td>
            <td>${e.metric_name?`${esc(e.metric_name)} ${esc(String(e.metric_value??''))}`:'—'}</td>
            <td>${e.words!=null?`${Math.round(e.words/10000*10)/10}万`:'—'}</td>
            <td>${(e.tags||[]).slice(0,4).map(t=>`<span class="tag">${esc(t)}</span>`).join(' ')||'—'}</td>
          </tr>`).join('')}</tbody>
        </table></div>`);
    }));
  }

  function paintAggregate(){
    const agg=data.aggregation||{snapshot_count:0,skipped_duplicates:[],platforms:[]};
    const snaps=data.snapshots||[];
    const platforms=agg.platforms||[];

    $('#radarTabBody').innerHTML=`<div class="stack">
      ${(agg.skipped_duplicates||[]).length?`<p class="notice">已自动剔除 ${agg.skipped_duplicates.length} 份与历史内容完全一致的镜像重复榜单，防止虚假跨榜重叠。</p>`:''}
      ${platforms.length?platforms.map(p=>`<section class="card stack">
        <div class="row spread wrap">
          <div>
            <h3>${esc(p.platform_name)} · 跨榜去重总计 ${p.book_count} 本</h3>
            <p class="muted">汇总榜单：${esc((p.lists||[]).join(' / '))} ｜ 稀疏门槛 ${p.sparse_threshold} 本${p.primary_metric?` ｜ 主热度指标：${esc(p.primary_metric)}`:''}</p>
          </div>
          <div class="row wrap">
            ${p.heat_distribution?`<span class="tag blue">中位 ${esc(p.heat_distribution.p50_label)} · P75 ${esc(p.heat_distribution.p75_label)}</span>`:''}
            <span class="tag">字数中位 ${esc(p.words_distribution?.median_label||'—')}</span>
            <button class="secondary" data-gen-for-platform="${esc(p.platform)}">基于此平台生成选题</button>
          </div>
        </div>

        <div class="table-wrap"><table class="data-table">
          <thead><tr><th>题材</th><th>本数 / 占比</th><th>新书信号</th><th>热度中位</th><th>字数中位</th><th>知识库映射</th><th>代表书目</th></tr></thead>
          <tbody>${(p.genres||[]).slice(0,15).map(g=>`<tr>
            <td><strong>${esc(g.genre)}</strong> ${g.sparse?'<span class="tag amber">样本稀疏</span>':''}</td>
            <td>${g.count} 本（${Math.round((g.share||0)*100)}%）</td>
            <td>${g.new_count} 本</td>
            <td>${esc(g.heat_median_label)}</td>
            <td>${esc(g.words_median_label)}</td>
            <td>${(g.mapped_type_ids||[]).map(id=>`<a class="text-link" href="#/atlas/${enc(id)}">${esc(id)}</a>`).join(' ')||'—'}</td>
            <td>${(g.representatives||[]).map(r=>`《${esc(r.title)}》${r.heat_label&&r.heat_label!=='—'?`(${esc(r.heat_label)})`:''}`).join(' · ')||'—'}</td>
          </tr>`).join('')}</tbody>
        </table></div>

        <div class="grid two">
          <div>
            <h4>高频标签（Top 15）</h4>
            <div class="row wrap">${(p.hot_tags||[]).slice(0,15).map(t=>`<span class="tag">${esc(t.tag)} · ${t.count}</span>`).join('')||'<span class="muted">暂无标签数据</span>'}</div>
            <h4 style="margin-top:12px">书名高频二字词</h4>
            <div class="row wrap">${(p.title_bigrams||[]).slice(0,12).map(b=>`<span class="tag">${esc(b.gram)} (${b.count})</span>`).join('')||'<span class="muted">样本较少，未出现重复高频词</span>'}</div>
          </div>
          <div>
            <h4>多榜重叠黑马（跨榜印证）</h4>
            ${(p.multi_list_overlaps||[]).length?`<ul>${p.multi_list_overlaps.slice(0,8).map(o=>`<li><strong>《${esc(o.title)}》</strong>（${esc(o.genre)} · ${o.list_count} 榜：${esc(o.lists.join(' / '))}）${o.in_new_list?' <span class="tag green">新书</span>':''}</li>`).join('')}</ul>`:'<p class="muted">当前平台仅单榜或尚无跨榜重叠书目。多采一份新书榜可自动识别黑马。</p>'}
            <h4 style="margin-top:12px">字数分布桶</h4>
            <div class="row wrap">${(p.words_distribution?.buckets||[]).filter(b=>b.count>0).map(b=>`<span class="tag">${esc(b.label)}：${b.count}</span>`).join('')||'<span class="muted">无字数字段</span>'}</div>
          </div>
        </div>
      </section>`).join(''):empty('暂无聚合数据','请先在「扫榜采集与万能导入」中至少入库一份榜单。','','layers')}

      <section class="card stack">
        <h3>期次趋势差分（对比上期 vs 本期）</h3>
        <p class="muted">选择两份同平台不同时间的快照，自动计算题材份额涨跌、热度变化、上升标签与新晋上榜书。</p>
        ${snaps.length>=2?`<form id="radarDiffForm" class="row wrap">
          <label class="field"><span>基线快照（较早）</span>
            <select name="baseline_id">${snaps.map((s,i)=>`<option value="${esc(s.id)}" ${i===snaps.length-1?'selected':''}>${esc(s.captured_date)} · ${esc(s.platform_name)} · ${esc(s.list_name)} (${s.entry_count})</option>`).join('')}</select>
          </label>
          <label class="field"><span>当前快照（较新）</span>
            <select name="current_id">${snaps.map((s,i)=>`<option value="${esc(s.id)}" ${i===0?'selected':''}>${esc(s.captured_date)} · ${esc(s.platform_name)} · ${esc(s.list_name)} (${s.entry_count})</option>`).join('')}</select>
          </label>
          <button class="button" type="submit" style="align-self:flex-end">计算趋势差分</button>
        </form>`:'<p class="muted">至少需要 2 份榜单快照才可进行期次趋势对比。</p>'}
        ${diffResult?renderDiffHtml(diffResult):''}
      </section>
    </div>`;

    $$('[data-gen-for-platform]').forEach(btn=>btn.onclick=()=>busy(btn,async()=>{
      await api.post('/radar/topics',{platform:btn.dataset.genForPlatform,use_llm:false,max_topics:3});
      toast('已生成证据约束选题方向');
      tab='topics';
      await load();
    }));

    $('#radarDiffForm')?.addEventListener('submit',e=>{
      e.preventDefault();
      busy(e.target.querySelector('button[type=submit]'),async()=>{
        const fd=new FormData(e.target);
        diffResult=await api.post('/radar/diff',{
          baseline_snapshot_ids:[fd.get('baseline_id')],
          current_snapshot_ids:[fd.get('current_id')],
        });
        paintAggregate();
      });
    });
  }

  function renderDiffHtml(res){
    if(!res.has_baseline||!(res.diffs||[]).length){
      return '<p class="notice">所选两份快照属于不同平台，请选择同一平台的两期快照对比。</p>';
    }
    return res.diffs.map(d=>`<div class="stack" style="margin-top:8px">
      <h4>${esc(d.platform_name)} · 趋势变化</h4>
      <div class="table-wrap"><table class="data-table">
        <thead><tr><th>题材</th><th>本期 / 基线</th><th>份额变化</th><th>热度变化</th><th>趋势判定</th></tr></thead>
        <tbody>${(d.genre_trends||[]).slice(0,12).map(g=>`<tr>
          <td>${esc(g.genre)}</td>
          <td>${g.current_count} / ${g.baseline_count}</td>
          <td>${g.share_delta>=0?'+':''}${Math.round(g.share_delta*1000)/10}%</td>
          <td>${g.heat_delta_pct!=null?`${g.heat_delta_pct>=0?'+':''}${g.heat_delta_pct}%`:'—'}</td>
          <td><span class="tag ${g.trend==='rising'?'green':g.trend==='cooling'?'amber':''}">${g.trend==='rising'?'升温':g.trend==='cooling'?'退温':'持平'}</span></td>
        </tr>`).join('')}</tbody>
      </table></div>
      <div class="grid two">
        <div><strong>上升标签：</strong>${(d.rising_tags||[]).map(t=>`<span class="tag green">${esc(t.tag)} +${t.delta}</span>`).join(' ')||'<span class="muted">无明显上升</span>'}</div>
        <div><strong>新晋上榜书：</strong>${(d.new_entrants||[]).slice(0,6).map(e=>`《${esc(e.title)}》(#${e.rank})`).join(' · ')||'<span class="muted">无新增</span>'}</div>
      </div>
    </div>`).join('');
  }

  function paintTopics(){
    const topics=data.topics||[];
    const platforms=data.platforms||[];
    $('#radarTabBody').innerHTML=`<div class="stack">
      <section class="card stack">
        <div>
          <h3>生成证据约束选题决策</h3>
          <p class="muted">严格执行可行性上限规则：单榜或样本低于门槛的题材最高仅评「中」，并标记「待拆文验证」；在预存库拆解对应对标书后自动回填为「已拆文验证」。</p>
        </div>
        <form id="radarTopicForm" class="stack">
          <div class="grid two">
            <label class="field"><span>限定平台（可选）</span>
              <select name="platform">
                <option value="">跨平台综合</option>
                ${platforms.map(p=>`<option value="${esc(p.id)}">${esc(p.name)}</option>`).join('')}
              </select>
            </label>
            <label class="field"><span>作者偏好 / 差异化优势（可选）</span>
              <input name="author_focus" placeholder="例如：擅长群像推理、偏冷硬写实、避免无脑系统流">
            </label>
          </div>
          <div class="row wrap">
            <button class="button" type="button" id="btnGenTopicsZero">0-Token 证据选题（快速）</button>
            <button class="secondary" type="button" id="btnGenTopicsLlm">AI 商业卖点深化选题</button>
          </div>
        </form>
      </section>

      ${topics.length?topics.map(t=>`<section class="card stack">
        <div class="row spread wrap">
          <div>
            <h3>${esc(t.title)}</h3>
            <div class="row wrap" style="margin-top:6px">
              <span class="tag ${FEASIBILITY_CLASS[t.feasibility]||''}">可行性：${esc(FEASIBILITY_LABEL[t.feasibility]||t.feasibility)}</span>
              <span class="tag ${VERIFY_CLASS[t.verification_status]||''}">${esc(VERIFY_LABEL[t.verification_status]||t.verification_status)}</span>
              ${t.primary_genre_id?`<a class="tag blue" href="#/atlas/${enc(t.primary_genre_id)}">${esc(t.primary_genre_id)}</a>`:''}
              ${(t.platforms||[]).map(p=>`<span class="tag">${esc(p)}</span>`).join('')}
            </div>
          </div>
          <div class="row wrap">
            <button type="button" class="button" data-new-novel="manual" ${t.primary_genre_id?`data-prefill="${esc(t.primary_genre_id)}"`:''}>以此方向新建小说</button>
            <a class="secondary" href="#/staging">送对标书去拆解</a>
          </div>
        </div>
        <p><strong>目标读者：</strong>${esc(t.target_reader)}</p>
        <p><strong>核心卖点与开篇钩子：</strong>${esc(t.core_hook)}</p>
        <p><strong>榜单证据：</strong>${esc(t.why_it_works)}</p>
        <p><strong>差异化切口：</strong>${esc(t.differentiation)}</p>
        <p class="muted"><strong>可行性依据：</strong>${esc(t.feasibility_reason)} ｜ <strong>主要风险：</strong>${esc(t.risks)}</p>
        <p class="muted"><strong>建议验证动作：</strong>${esc(t.validation_action)}</p>
        ${(t.benchmark_books||[]).length?`<p class="muted"><strong>对标参考书：</strong>${t.benchmark_books.map(b=>`《${esc(b.title)}》${b.author?`(${esc(b.author)})`:''}${b.heat&&b.heat!=='—'?` · ${esc(b.heat)}`:''}`).join(' ｜ ')}</p>`:''}
        ${t.verification_note?`<p class="notice">${esc(t.verification_note)}${t.verified_by_book_id?` <a class="text-link" href="#/staging/${enc(t.verified_by_book_id)}?view=structure&amp;tab=anatomy">查看拆解体检报告 →</a>`:''}</p>`:''}
      </section>`).join(''):empty('尚未生成选题方向','采集或导入榜单后，点击上方按钮即可生成基于真实市场数据的选题卡片。','','book')}
    </div>`;

    const triggerGen=(useLlm,btn)=>busy(btn,async()=>{
      const form=$('#radarTopicForm');
      await api.post('/radar/topics',{
        platform:$('[name=platform]',form).value,
        author_focus:$('[name=author_focus]',form).value,
        use_llm:useLlm,
        max_topics:3,
      });
      toast(useLlm?'AI 深化选题已生成':'0-Token 证据选题已生成');
      await load();
    });
    $('#btnGenTopicsZero').onclick=e=>triggerGen(false,e.currentTarget);
    $('#btnGenTopicsLlm').onclick=e=>triggerGen(true,e.currentTarget);
  }

  function paintPlaybooks(){
    const playbooks=data.playbooks||[];
    const recs=recList||data.beginner_recommendations||[];
    const friendlyTag=f=>f==='high'?'<span class="tag green">新人高友好</span>':f==='medium'?'<span class="tag amber">中（需避坑）</span>':'<span class="tag">内卷高门槛</span>';

    $('#radarTabBody').innerHTML=`<div class="stack">
      <section class="card stack">
        <div class="row spread wrap">
          <div>
            <h3>按我的情况推荐最适合赚钱的发书平台（2025–2026 规则版）</h3>
            <p class="muted">综合签约门槛、2026 最新政策变化（如番茄新人完本签约、刺猬猫全勤改版）、全勤兜底与题材匹配度智能排序。</p>
          </div>
          <span class="tag blue">覆盖 6 大主流变现平台</span>
        </div>
        <form id="playbookRecForm" class="row wrap">
          <label class="field"><span>计划篇幅</span>
            <select name="scale">
              <option value="long" ${recScale==='long'?'selected':''}>长篇连载（20万–200万字）</option>
              <option value="short" ${recScale==='short'?'selected':''}>短篇快变现（0.5万–3万字完本）</option>
            </select>
          </label>
          <label class="field"><span>当前经验</span>
            <select name="experience">
              <option value="beginner" ${recExp==='beginner'?'selected':''}>新手 / 首本变现（稳健低试错优先）</option>
              <option value="experienced" ${recExp==='experienced'?'selected':''}>有完本经验 / Lv.2+（高流量与高订阅上限优先）</option>
            </select>
          </label>
          <label class="field"><span>主攻题材（可选）</span>
            <select name="genre">
              <option value="">不限题材</option>
              <option value="GENRE_DUSHI" ${recGenre==='GENRE_DUSHI'?'selected':''}>都市 / 脑洞</option>
              <option value="GENRE_XUANHUAN" ${recGenre==='GENRE_XUANHUAN'?'selected':''}>玄幻 / 奇幻</option>
              <option value="GENRE_XIANXIA" ${recGenre==='GENRE_XIANXIA'?'selected':''}>仙侠 / 修真</option>
              <option value="GENRE_YANQING" ${recGenre==='GENRE_YANQING'?'selected':''}>言情 / 女频</option>
              <option value="GENRE_XUANYI" ${recGenre==='GENRE_XUANYI'?'selected':''}>悬疑 / 规则怪谈</option>
              <option value="GENRE_LISHI" ${recGenre==='GENRE_LISHI'?'selected':''}>历史 / 架空</option>
              <option value="GENRE_QINGXIAOSHUO" ${recGenre==='GENRE_QINGXIAOSHUO'?'selected':''}>轻小说 / 二次元</option>
              <option value="GENRE_XIANSHI" ${recGenre==='GENRE_XIANSHI'?'selected':''}>现实 / 婚姻家庭</option>
            </select>
          </label>
          <button class="button" type="submit" style="align-self:flex-end">匹配推荐平台</button>
        </form>
        <div class="grid two">
          ${recs.slice(0,4).map((r,idx)=>`<article class="card stack">
            <div class="row spread wrap">
              <strong>#${idx+1} ${esc(r.platform_name)}</strong>
              <span class="tag ${r.fit_score>=80?'green':r.fit_score>=60?'blue':'amber'}">匹配度 ${r.fit_score}</span>
            </div>
            <p class="muted" style="margin:0">${esc(r.monetization_model)}</p>
            <p style="margin:0"><strong>推荐理由：</strong>${esc((r.fit_reasons||[]).join('；')||'符合综合变现需求')}</p>
            <p class="muted" style="margin:0"><strong>关键提醒：</strong>${esc((r.cautions||[]).join('；'))}</p>
            <p class="faint" style="margin:0">日更要求：${esc(r.daily_words)}</p>
          </article>`).join('')}
        </div>
      </section>

      <section class="card stack">
        <h3>6 大热门赚钱平台横向对比总表</h3>
        <div class="table-wrap"><table class="data-table">
          <thead><tr><th>平台</th><th>定位与新人友好</th><th>核心赚钱模式</th><th>签约门槛</th><th>全勤规则</th><th>日更与单章建议</th></tr></thead>
          <tbody>${playbooks.map(pb=>`<tr>
            <td><strong>${esc(pb.name)}</strong><br><small class="muted">${esc(pb.tier)}</small></td>
            <td>${friendlyTag(pb.beginner_friendly)}<br><small class="muted">${esc(pb.audience_focus)}</small></td>
            <td>${esc(pb.monetization.model)}</td>
            <td>${esc(pb.signing.threshold)}</td>
            <td>${esc(pb.monetization.full_attendance)}</td>
            <td>${esc(pb.craft_requirements.daily_words)}<br><small class="muted">${esc(pb.craft_requirements.chapter_words)}</small></td>
          </tr>`).join('')}</tbody>
        </table></div>
      </section>

      ${playbooks.map(pb=>`<section class="card stack">
        <div class="row spread wrap">
          <div>
            <h3>${esc(pb.full_name)}</h3>
            <div class="row wrap" style="margin-top:4px">
              <span class="tag blue">${esc(pb.tier)}</span>
              ${friendlyTag(pb.beginner_friendly)}
              <span class="tag">合约性质：${esc(pb.signing.contract_binding)}</span>
            </div>
          </div>
          <div class="row wrap">
            ${pb.craft_requirements.hot_genres?.[0]?`<button type="button" class="button" data-new-novel="manual" data-prefill="${esc(pb.craft_requirements.hot_genres[0])}">按该平台强势题材开新书</button>`:''}
            <button type="button" class="secondary" data-jump-collect="${esc(pb.id)}">去采/导该平台榜单</button>
          </div>
        </div>
        <p class="notice">${esc(pb.signing.recent_2026_alert)}</p>
        <div class="grid two">
          <div>
            <h4>赚钱与分成机制</h4>
            <p><strong>收益模式：</strong>${esc(pb.monetization.model)}</p>
            <p><strong>分成细则：</strong>${esc(pb.monetization.revenue_split)}</p>
            <p><strong>全勤政策：</strong>${esc(pb.monetization.full_attendance)}</p>
            <p><strong>衍生加分渠道：</strong>${(pb.monetization.bonus_channels||[]).map(c=>`<span class="tag">${esc(c)}</span>`).join(' ')}</p>
          </div>
          <div>
            <h4>签约与写作硬规范</h4>
            <p><strong>签约通道：</strong>${esc(pb.signing.mode)} — ${esc(pb.signing.threshold)}</p>
            <p><strong>黄金三章 / 导语重点：</strong>${esc(pb.craft_requirements.golden_three_focus)}</p>
            <p class="error"><strong>平台硬红线：</strong></p>
            <ul>${(pb.craft_requirements.redlines||[]).map(x=>`<li>${esc(x)}</li>`).join('')}</ul>
          </div>
        </div>
        <details class="details" open>
          <summary>推荐晋级阶梯（${(pb.progression_ladder||[]).length} 个关键节点）</summary>
          <div class="table-wrap" style="margin-top:8px"><table class="data-table">
            <thead><tr><th>阶段</th><th>字数 / 时间窗口</th><th>核心考核指标</th><th>实战策略</th></tr></thead>
            <tbody>${(pb.progression_ladder||[]).map(st=>`<tr>
              <td><strong>${esc(st.stage)}</strong></td>
              <td>${esc(st.words_or_time)}</td>
              <td>${esc(st.core_metrics)}</td>
              <td>${esc(st.action_tip)}</td>
            </tr>`).join('')}</tbody>
          </table></div>
        </details>
        <details class="details">
          <summary>主要榜单规则与冲榜策略（${(pb.rank_lists||[]).length} 个榜单）</summary>
          <div class="table-wrap" style="margin-top:8px"><table class="data-table">
            <thead><tr><th>榜单名称</th><th>榜单定位</th><th>核心驱动指标</th><th>上榜窗口</th><th>冲榜实操建议</th></tr></thead>
            <tbody>${(pb.rank_lists||[]).map(rl=>`<tr>
              <td><strong>${esc(rl.name)}</strong></td>
              <td>${esc(rl.category)}</td>
              <td>${esc(rl.driver_metrics)}</td>
              <td>${esc(rl.window)}</td>
              <td>${esc(rl.strategy)}</td>
            </tr>`).join('')}</tbody>
          </table></div>
        </details>
      </section>`).join('')}
      <p class="faint">注：以上规则基于 2025–2026 各平台公开作家政策整理，具体分成比例与当期激励请以对应平台官方作家后台合同及最新公告为准。</p>
    </div>`;

    $('#playbookRecForm').onsubmit=e=>{
      e.preventDefault();
      busy(e.target.querySelector('button[type=submit]'),async()=>{
        const fd=new FormData(e.target);
        recScale=fd.get('scale');
        recExp=fd.get('experience');
        recGenre=fd.get('genre');
        const q=new URLSearchParams({scale:recScale,experience:recExp,...(recGenre?{types:recGenre}:{})});
        const res=await api.get(`/radar/playbooks?${q.toString()}`,ctx.signal);
        recList=res.recommendations||[];
        paintPlaybooks();
      });
    };

    $$('[data-jump-collect]').forEach(btn=>btn.onclick=()=>{
      tab='collect';
      $$('[data-radar-tab]').forEach(t=>t.classList.toggle('active',t.dataset.radarTab===tab));
      paintTab();
    });
  }

  ctx.content.innerHTML=loading();
  await load();
}
