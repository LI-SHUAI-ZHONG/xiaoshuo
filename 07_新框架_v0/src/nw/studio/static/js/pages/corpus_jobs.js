import {api,enc} from '../api.js';
import {$,$$,esc,modal,busy,toast} from '../ui.js';

export const jobState={pending:'待启动',running:'运行中',paused:'已暂停',failed:'失败',completed:'已完成',cancelled:'已取消'};
export const phaseName={survey:'通读原文',overview:'整合全书',detail:'卷章场细拆',relations:'核对跨章关系',methods:'提炼方法',publish:'保存待审核版本'};

export function openCorpusRun({book,record,catalog,reload,kind='structure'}){
  const extent=record.body.source_extent;
  const threads=record.body.threads;
  const bindings=catalog.domain_bindings||{};
  const derivedThreadIds=new Set((record.derived_methods||[]).flatMap(m=>m.thread_ids||[]));
  const stepTag=domain=>{
    const names=bindings[domain]?.target_step_names;
    return names?.length?` → ${names.slice(0,3).join('/')}`:'';
  };
  modal(kind==='methods'?'从已批准结构提炼方法':'多层结构拆解',`<form id="corpusRunForm" class="stack">
    <div class="notice">${kind==='methods'?'每条方法将按目标制作步骤的资料需求分类提炼（区分作用性与方式性），保留结构版本、实际事件及原文依据，生成后仍是待独立审核草稿。':'通读（读取）→ 全书总览 → 卷章场细拆 → 跨章关系（按步骤资料需求检索并判定作用性与方式性）。结果保存为待审核的新版本，原批准版本保留。'}</div>
    ${kind==='structure'?`<label class="field"><span>参考文本完整性（由作者确认）</span><select name="extent">${Object.entries(catalog.source_extents).map(([id,label])=>`<option value="${id}" ${extent.status===id?'selected':''}>${esc(label)}</option>`).join('')}</select></label><label class="field"><span>完整性判断依据</span><textarea name="note" rows="3" required>${esc(extent.note)}</textarea></label>`:
      `<fieldset class="method-section"><legend>选择 1–20 条已核实线索 / 弧光（显示绑定下游步骤），可分批提炼</legend>
        <div class="row wrap" style="margin-bottom:8px"><button type="button" class="ghost" id="pickFirst20Threads">选中前 20 条可提炼线索</button><button type="button" class="ghost" id="clearPickedThreads">清空选择</button><span class="muted" id="pickedThreadCount">已选 0 / 20</span></div>
        <div style="max-height:260px;overflow:auto">${threads.map(t=>`<label class="check-row"><input name="threads" type="checkbox" value="${esc(t.id)}" ${t.status==='uncertain'?'disabled':''}> <span>${esc(catalog.domains[t.domain]||t.domain)}${esc(stepTag(t.domain))} · ${esc(t.title)}${derivedThreadIds.has(t.id)?'（已提炼）':''}${t.status==='uncertain'?'（存疑，需先核实后提炼）':''}</span></label>`).join('')}</div></fieldset>`}
    <div class="form-grid">${kind==='structure'?'<label class="field"><span>每段原文字符数</span><input name="chunk_chars" type="number" min="1000" max="20000" value="6000"></label>':''}
    <label class="field"><span>调用次数上限（含失败尝试）</span><input name="max_calls" type="number" min="1" max="30000" value="${kind==='methods'?40:128}"></label>
    <label class="field"><span>每次完整输入字符预算</span><input name="max_input_chars" type="number" min="8000" max="512000" value="64000"></label></div>
    <p class="muted">字符数不等于模型token；请按所用API容量设置。超限暂停，不静默删除原文或必需上下文。未知结果重试可能重复计费。</p>
    <div id="corpusEstimate" class="muted"></div><div class="row wrap"><button type="button" class="secondary" id="estimateCorpus">估算读取范围</button><button class="button" type="submit">开始${kind==='methods'?'方法提炼':'多层拆解'}</button></div></form>`,'',true);
  const options=()=>{
    const form=$('#corpusRunForm');
    return {extent:kind==='structure'?$('[name=extent]',form).value:extent.status,note:kind==='structure'?$('[name=note]',form).value:extent.note,
      chunk_chars:kind==='structure'?Number($('[name=chunk_chars]',form).value):6000,max_calls:Number($('[name=max_calls]',form).value),
      max_input_chars:Number($('[name=max_input_chars]',form).value),thread_ids:$$('[name=threads]:checked',form).map(x=>x.value)};
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
    const estimate=await api.post(`/staging/${enc(book.id)}/corpus/estimate`,{...opts,note:opts.note||'等待作者确认完整性'});
    if(autoAdjust){
      const callsInput=$('#corpusRunForm [name=max_calls]');
      if(callsInput&&Number(callsInput.value)<estimate.minimum_structure_calls){
        callsInput.value=String(Math.min(30000,estimate.minimum_structure_calls+16));
      }
    }
    $('#corpusEstimate').textContent=`已导入 ${estimate.characters} 字符，${estimate.chapter_units} 个章节范围，最低 ${estimate.minimum_structure_calls} 次调用；整合批次与重试可能增加。`;
  }
  $('#estimateCorpus').onclick=e=>busy(e.currentTarget,()=>updateEstimate(true));
  if(kind==='structure')updateEstimate(true).catch(()=>{});
  $('#corpusRunForm').onsubmit=e=>{
    e.preventDefault();busy(e.target.querySelector('[type=submit]'),async()=>{
      await api.post(`/staging/${enc(book.id)}/corpus/jobs`,{kind,options:options()});
      $('#modalBackdrop').close();toast('任务已启动，输入输出与检查点会逐次保存');await reload();
    });
  };
}

export function openCorpusResume({book,job,reload}){
  const nextMaxCalls=job.calls_used>=job.options.max_calls?Math.min(30000,job.calls_used+16):job.options.max_calls;
  modal('续接多层拆解任务',`<form id="corpusResumeForm" class="stack"><p class="notice">已完成结果按原输入复用；原文、结构或模型配置已改变时须重新建任务。</p>
    <label class="field"><span>调用上限</span><input name="max_calls" type="number" min="${job.calls_used}" max="30000" value="${nextMaxCalls}"></label>
    <label class="field"><span>完整输入字符预算</span><input name="max_input_chars" type="number" min="8000" max="512000" value="${job.options.max_input_chars}"></label>
    <label class="check-row"><input name="retry" type="checkbox"> 我明确重试失败 / 结果未知的调用，理解可能重复计费</label><button class="button" type="submit">续接任务</button></form>`);
  $('#corpusResumeForm').onsubmit=e=>{e.preventDefault();busy(e.target.querySelector('button'),async()=>{
    const form=e.target;
    await api.post(`/staging/${enc(book.id)}/corpus/jobs/${enc(job.id)}`,{action:'resume',retry_failed:$('[name=retry]',form).checked,
      options:{max_calls:Number($('[name=max_calls]',form).value),max_input_chars:Number($('[name=max_input_chars]',form).value)}});
    $('#modalBackdrop').close();toast('任务已续接');await reload();
  });};
}
