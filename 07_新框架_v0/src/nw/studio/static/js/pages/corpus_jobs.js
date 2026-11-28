import {api,enc} from '../api.js';
import {$,$$,esc,modal,busy,toast} from '../ui.js';

export const jobState={pending:'待启动',running:'运行中',paused:'已暂停',failed:'失败',completed:'已完成',cancelled:'已取消'};
export const phaseName={
  extract:'章节精准提取',synthesize:'提炼工作流方法',
  survey:'通读原文',overview:'整合全书',detail:'卷章场细拆',relations:'核对跨章关系',methods:'提炼方法',publish:'核验入库',
};

const DEFAULT_TRACKS=[
  {id:'genre_world_rules',name:'题材特色世界机制与代价边界',steps:'03 世界定稿 / 08 行动博弈'},
  {id:'character_conflict',name:'核心人物弧光、反派阻力与关系张力',steps:'04 人物定稿 / 05 关系张力'},
  {id:'opening_plot_hooks',name:'开篇承诺、主线推进与钩子伏笔',steps:'06 故事大纲 / 07 事件链'},
  {id:'scene_prose_craft',name:'受限视角、动作节拍与段落文风',steps:'09 场景 / 12 锚点 / 13 表达 / 15 写作'},
];

export function openCorpusRun({book,record,catalog,reload,kind='targeted'}){
  const extent=record.body.source_extent;
  const threads=record.body.threads;
  const bindings=catalog.domain_bindings||{};
  const tracks=(catalog.targeted_tracks?.length?catalog.targeted_tracks.map(t=>({
    id:t.id,name:t.name,steps:(t.target_step_names||[]).join(' / '),
  })):DEFAULT_TRACKS);
  const derivedThreadIds=new Set((record.derived_methods||[]).flatMap(m=>m.thread_ids||[]));
  const stepTag=domain=>{
    const names=bindings[domain]?.target_step_names;
    return names?.length?` → ${names.slice(0,3).join('/')}`:'';
  };
  const titleMap={
    targeted:'精准步骤拆解（推荐 · 直出工作流可用方法）',
    structure:'全书多层图谱拆解（深度研究）',
    methods:'从已批准结构提炼方法',
  };
  const defaultExtentStatus=extent.status==='unknown'?'complete':extent.status;
  const defaultExtentNote=extent.note||(defaultExtentStatus==='complete'?'已导入正文章节文本，采用步骤定向精准拆解':'局部摘录文本');

  modal(titleMap[kind]||'参考小说拆解',`<form id="corpusRunForm" class="stack">
    ${kind==='targeted'?`<div class="notice"><strong>新精准拆解工作流</strong>：自动跳过「书籍信息 / 简介 / 作者感言」等非正文段，按 4 大无重叠创作工作流轨道读取核心章节，<strong>一次任务直接产出带精确原文偏移铁证、程序化合同全检的可复用方法</strong>，无需数百次调用或反复手工二次审批！</div>
      <div class="form-grid">
        <label class="field"><span>抽样读取范围</span><select name="sample_mode">
          <option value="key_chapters" selected>核心样本精拆（推荐：黄金前 3 章 + 中后转折章）</option>
          <option value="chapter_range">自定义正文章节区间</option>
          <option value="all_chapters">全部正文章节</option>
        </select></label>
        <label class="field" id="sampleCountField"><span>抽样章数（3–20 章）</span><input name="sample_count" type="number" min="1" max="20" value="6"></label>
      </div>
      <div class="form-grid" id="chapterRangeFields" hidden>
        <label class="field"><span>起始正文第几章</span><input name="chapter_start" type="number" min="1" value="1"></label>
        <label class="field"><span>结束正文第几章</span><input name="chapter_end" type="number" min="1" value="6"></label>
      </div>
      <fieldset class="method-section"><legend>拆解维度（4 大非重叠工作流轨道，精准绑定下游步骤）</legend>
        ${tracks.map(t=>`<label class="check-row"><input name="tracks" type="checkbox" value="${esc(t.id)}" checked> <span><strong>${esc(t.name)}</strong> <small class="muted">→ ${esc(t.steps)}</small></span></label>`).join('')}
      </fieldset>
      <label class="check-row"><input name="auto_approve" type="checkbox" checked> <strong>程序化核验通过后自动入库启用</strong>（自动核验原文偏移 + 下游步骤合同，免手工双重审批；随时可在资料库编辑或撤回）</label>
      <details class="details"><summary>高级参数 · 文本完整性、每章字符上限与调用预算</summary>
        <div class="stack" style="margin-top:8px">
          <label class="field"><span>参考文本完整性</span><select name="extent">${Object.entries(catalog.source_extents).map(([id,label])=>`<option value="${id}" ${defaultExtentStatus===id?'selected':''}>${esc(label)}</option>`).join('')}</select></label>
          <label class="field"><span>完整性说明</span><textarea name="note" rows="2" required>${esc(defaultExtentNote)}</textarea></label>
          <div class="form-grid">
            <label class="field"><span>每章最大读取字符数</span><input name="chunk_chars" type="number" min="1000" max="20000" value="8000"></label>
            <label class="field"><span>调用次数上限</span><input name="max_calls" type="number" min="1" max="30000" value="24"></label>
            <label class="field"><span>单次输入字符预算</span><input name="max_input_chars" type="number" min="8000" max="512000" value="64000"></label>
          </div>
        </div>
      </details>`:kind==='structure'?`<div class="notice">完整图谱拆解会通读并细拆全部已导入字符，适用于全书逐章人物分布统计等深度研究；长篇网文调用次数较多，日常提炼写法请优先使用「精准步骤拆解」。</div>
      <label class="field"><span>参考文本完整性（由作者确认）</span><select name="extent">${Object.entries(catalog.source_extents).map(([id,label])=>`<option value="${id}" ${extent.status===id?'selected':''}>${esc(label)}</option>`).join('')}</select></label>
      <label class="field"><span>完整性判断依据</span><textarea name="note" rows="3" required>${esc(extent.note||'作者确认导入文本范围')}</textarea></label>
      <div class="form-grid">
        <label class="field"><span>每段原文字符数</span><input name="chunk_chars" type="number" min="1000" max="20000" value="6000"></label>
        <label class="field"><span>调用次数上限（含失败尝试）</span><input name="max_calls" type="number" min="1" max="30000" value="128"></label>
        <label class="field"><span>每次完整输入字符预算</span><input name="max_input_chars" type="number" min="8000" max="512000" value="64000"></label>
      </div>`:
      `<div class="notice">每条方法将按目标制作步骤的资料需求分类提炼，保留结构版本、实际事件及原文依据，生成后仍是待独立审核草稿。</div>
      <fieldset class="method-section"><legend>选择 1–20 条已核实线索 / 弧光（显示绑定下游步骤），可分批提炼</legend>
        <div class="row wrap" style="margin-bottom:8px"><button type="button" class="ghost" id="pickFirst20Threads">选中前 20 条可提炼线索</button><button type="button" class="ghost" id="clearPickedThreads">清空选择</button><span class="muted" id="pickedThreadCount">已选 0 / 20</span></div>
        <div style="max-height:260px;overflow:auto">${threads.map(t=>`<label class="check-row"><input name="threads" type="checkbox" value="${esc(t.id)}" ${t.status==='uncertain'?'disabled':''}> <span>${esc(catalog.domains[t.domain]||t.domain)}${esc(stepTag(t.domain))} · ${esc(t.title)}${derivedThreadIds.has(t.id)?'（已提炼）':''}${t.status==='uncertain'?'（存疑，需先核实后提炼）':''}</span></label>`).join('')}</div></fieldset>
      <div class="form-grid">
        <label class="field"><span>调用次数上限</span><input name="max_calls" type="number" min="1" max="30000" value="40"></label>
        <label class="field"><span>每次完整输入字符预算</span><input name="max_input_chars" type="number" min="8000" max="512000" value="64000"></label>
      </div>`}
    <div id="corpusEstimate" class="muted"></div>
    <div class="row wrap"><button type="button" class="secondary" id="estimateCorpus">估算调用次数</button><button class="button" type="submit">开始${kind==='targeted'?'精准步骤拆解':kind==='methods'?'方法提炼':'全书多层拆解'}</button></div></form>`,'',true);

  const form=$('#corpusRunForm');
  const syncSampleMode=()=>{
    if(kind!=='targeted')return;
    const mode=$('[name=sample_mode]',form).value;
    $('#sampleCountField').hidden=mode!=='key_chapters';
    $('#chapterRangeFields').hidden=mode!=='chapter_range';
  };
  if(kind==='targeted'){
    $('[name=sample_mode]',form).onchange=()=>{syncSampleMode();updateEstimate(true).catch(()=>{});};
    syncSampleMode();
  }

  const options=()=>{
    const base={
      extent:kind==='methods'?extent.status:$('[name=extent]',form).value,
      note:kind==='methods'?(extent.note||'已批准结构提炼'):$('[name=note]',form).value,
      chunk_chars:kind==='methods'?6000:Number($('[name=chunk_chars]',form).value),
      max_calls:Number($('[name=max_calls]',form).value),
      max_input_chars:Number($('[name=max_input_chars]',form).value),
      thread_ids:$$('[name=threads]:checked',form).map(x=>x.value),
    };
    if(kind==='targeted'){
      const mode=$('[name=sample_mode]',form).value;
      base.sample_mode=mode;
      base.sample_count=Number($('[name=sample_count]',form).value)||6;
      if(mode==='chapter_range'){
        base.chapter_start=Number($('[name=chapter_start]',form).value)||1;
        base.chapter_end=Number($('[name=chapter_end]',form).value)||base.chapter_start;
      }
      base.tracks=$$('[name=tracks]:checked',form).map(x=>x.value);
      base.auto_approve=$('[name=auto_approve]',form).checked;
    }
    return base;
  };

  if(kind==='methods'){
    const syncCount=()=>{const n=$$('#corpusRunForm [name=threads]:checked').length;const el=$('#pickedThreadCount');if(el)el.textContent=`已选 ${n} / 20`;};
    $$('#corpusRunForm [name=threads]').forEach(cb=>cb.addEventListener('change',syncCount));
    $('#pickFirst20Threads')?.addEventListener('click',()=>{
      const boxes=$$('#corpusRunForm [name=threads]:not(:disabled)');
      boxes.forEach((cb,idx)=>{cb.checked=idx<20;});
      syncCount();
    });
    $('#clearPickedThreads')?.addEventListener('click',()=>{
      $$('#corpusRunForm [name=threads]').forEach(cb=>{cb.checked=false;});
      syncCount();
    });
    syncCount();
  }

  async function updateEstimate(autoAdjust=false){
    const opts=options();
    if(kind==='methods'){
      $('#corpusEstimate').textContent=`已选 ${opts.thread_ids.length} 条线索；每条至少一次，完整上下文超限会暂停。`;
      return;
    }
    const estimate=await api.post(`/staging/${enc(book.id)}/corpus/estimate`,{kind,...opts,note:opts.note||'等待作者确认完整性'});
    if(kind==='targeted'&&estimate.targeted){
      const t=estimate.targeted;
      if(autoAdjust){
        const callsInput=$('[name=max_calls]',form);
        if(callsInput&&Number(callsInput.value)<t.recommended_max_calls){
          callsInput.value=String(t.recommended_max_calls);
        }
      }
      $('#corpusEstimate').textContent=`全书 ${t.story_chapters} 个正文章节（自动跳过 ${t.skipped_paratext_count} 个简介/非正文段）· 本次精拆 ${t.sampled_chapters} 章，预计仅需 ${t.minimum_targeted_calls} 次模型调用（${(t.sampled_titles||[]).slice(0,4).join('、')}${t.sampled_chapters>4?' 等':''}）。`;
      return;
    }
    if(autoAdjust){
      const callsInput=$('[name=max_calls]',form);
      if(callsInput&&Number(callsInput.value)<estimate.minimum_structure_calls){
        callsInput.value=String(Math.min(30000,estimate.minimum_structure_calls+16));
      }
    }
    $('#corpusEstimate').textContent=`已导入 ${estimate.characters} 字符，${estimate.chapter_units} 个章节范围，全书图谱最低 ${estimate.minimum_structure_calls} 次调用；日常提炼写法建议改用「精准步骤拆解」（约 ${estimate.targeted?.minimum_targeted_calls||8} 次调用）。`;
  }
  $('#estimateCorpus').onclick=e=>busy(e.currentTarget,()=>updateEstimate(true));
  if(kind==='targeted'||kind==='structure')updateEstimate(true).catch(()=>{});
  form.onsubmit=e=>{
    e.preventDefault();busy(e.target.querySelector('[type=submit]'),async()=>{
      const opts=options();
      if(kind==='targeted'&&!opts.tracks.length)throw new Error('请至少勾选 1 个精准拆解维度');
      await api.post(`/staging/${enc(book.id)}/corpus/jobs`,{kind,options:opts});
      $('#modalBackdrop').close();toast(kind==='targeted'?'精准步骤拆解已启动（自动跳过非正文并核验原文偏移）':'任务已启动，输入输出与检查点会逐次保存');await reload();
    });
  };
}

export function openCorpusResume({book,job,reload}){
  const nextMaxCalls=job.calls_used>=job.options.max_calls?Math.min(30000,job.calls_used+16):job.options.max_calls;
  const needRetry=job.status==='failed'||(job.calls||[]).some(c=>['invalid','unknown'].includes(c.status));
  modal('续接拆解任务',`<form id="corpusResumeForm" class="stack"><p class="notice">已完成调用结果自动复用；本次已将拆解接口超时下限提升至 300 秒，防止推理模型在中途超时断线。</p>
    ${job.error?`<p class="error">上次中断原因：${esc(job.error)}</p>`:''}
    <label class="field"><span>调用上限</span><input name="max_calls" type="number" min="${job.calls_used}" max="30000" value="${nextMaxCalls}"></label>
    <label class="field"><span>完整输入字符预算</span><input name="max_input_chars" type="number" min="8000" max="512000" value="${job.options.max_input_chars}"></label>
    <label class="check-row"><input name="retry" type="checkbox" ${needRetry?'checked':''}> 重试上次失败 / 超时的调用</label><button class="button" type="submit">续接任务</button></form>`);
  $('#corpusResumeForm').onsubmit=e=>{e.preventDefault();busy(e.target.querySelector('button'),async()=>{
    const form=e.target;
    await api.post(`/staging/${enc(book.id)}/corpus/jobs/${enc(job.id)}`,{action:'resume',retry_failed:$('[name=retry]',form).checked,
      options:{max_calls:Number($('[name=max_calls]',form).value),max_input_chars:Number($('[name=max_input_chars]',form).value)}});
    $('#modalBackdrop').close();toast('任务已续接');await reload();
  });};
}
