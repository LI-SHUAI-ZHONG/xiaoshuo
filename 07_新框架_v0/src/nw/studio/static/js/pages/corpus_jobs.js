import {api,enc} from '../api.js';
import {$,$$,esc,modal,busy,toast} from '../ui.js';

export const jobState={pending:'待启动',running:'运行中',paused:'已暂停',failed:'失败',completed:'已完成',cancelled:'已取消'};
export const phaseName={survey:'通读原文',overview:'整合全书',detail:'卷章场细拆',relations:'核对跨章关系',methods:'提炼方法',publish:'保存待审核版本'};

export function openCorpusRun({book,record,catalog,reload,kind='structure'}){
  const extent=record.body.source_extent;
  const threads=record.body.threads;
  modal(kind==='methods'?'从已批准结构提炼方法':'多层结构拆解',`<form id="corpusRunForm" class="stack">
    <div class="notice">${kind==='methods'?'每条方法必须保留结构版本、实际事件及原文依据，生成后仍是待独立审核草稿。':'通读 → 全书总览 → 卷章场细拆 → 跨章关系。结果保存为待审核的新版本，原批准版本保留。'}</div>
    ${kind==='structure'?`<label class="field"><span>参考文本完整性（由作者确认）</span><select name="extent">${Object.entries(catalog.source_extents).map(([id,label])=>`<option value="${id}" ${extent.status===id?'selected':''}>${esc(label)}</option>`).join('')}</select></label><label class="field"><span>完整性判断依据</span><textarea name="note" rows="3" required>${esc(extent.note)}</textarea></label>`:
      `<fieldset class="method-section"><legend>选择1–20条线索 / 弧光，可分批提炼</legend>${threads.map(t=>`<label class="check-row"><input name="threads" type="checkbox" value="${esc(t.id)}"> ${esc(catalog.domains[t.domain])} · ${esc(t.title)}</label>`).join('')}</fieldset>`}
    <div class="form-grid"><label class="field"><span>每段原文字符数</span><input name="chunk_chars" type="number" min="1000" max="20000" value="6000"></label>
    <label class="field"><span>调用次数上限（含失败尝试）</span><input name="max_calls" type="number" min="1" max="3000" value="128"></label>
    <label class="field"><span>每次完整输入字符预算</span><input name="max_input_chars" type="number" min="8000" max="512000" value="64000"></label></div>
    <p class="muted">字符数不等于模型token；请按所用API容量设置。超限暂停，不静默删除原文或必需上下文。未知结果重试可能重复计费。</p>
    <div id="corpusEstimate" class="muted"></div><div class="row wrap"><button type="button" class="secondary" id="estimateCorpus">估算读取范围</button><button class="button" type="submit">开始${kind==='methods'?'方法提炼':'多层拆解'}</button></div></form>`,'',true);
  const options=()=>{
    const form=$('#corpusRunForm');
    return {extent:kind==='structure'?$('[name=extent]',form).value:extent.status,note:kind==='structure'?$('[name=note]',form).value:extent.note,
      chunk_chars:Number($('[name=chunk_chars]',form).value),max_calls:Number($('[name=max_calls]',form).value),
      max_input_chars:Number($('[name=max_input_chars]',form).value),thread_ids:$$('[name=threads]:checked',form).map(x=>x.value)};
  };
  $('#estimateCorpus').onclick=e=>busy(e.currentTarget,async()=>{
    const estimate=await api.post(`/staging/${enc(book.id)}/corpus/estimate`,options());
    $('#corpusEstimate').textContent=kind==='methods'?`已选 ${options().thread_ids.length} 条线索；每条至少一次，完整上下文超限会暂停。`:
      `已导入 ${estimate.characters} 字符，${estimate.chapter_units} 个章节范围，最低 ${estimate.minimum_structure_calls} 次调用；整合批次与重试可能增加。`;
  });
  $('#corpusRunForm').onsubmit=e=>{
    e.preventDefault();busy(e.target.querySelector('[type=submit]'),async()=>{
      await api.post(`/staging/${enc(book.id)}/corpus/jobs`,{kind,options:options()});
      $('#modalBackdrop').close();toast('任务已启动，输入输出与检查点会逐次保存');await reload();
    });
  };
}

export function openCorpusResume({book,job,reload}){
  modal('续接多层拆解任务',`<form id="corpusResumeForm" class="stack"><p class="notice">已完成结果按原输入复用；原文、结构或模型配置已改变时须重新建任务。</p>
    <label class="field"><span>调用上限</span><input name="max_calls" type="number" min="${job.calls_used}" max="3000" value="${job.options.max_calls}"></label>
    <label class="field"><span>完整输入字符预算</span><input name="max_input_chars" type="number" min="8000" max="512000" value="${job.options.max_input_chars}"></label>
    <label class="check-row"><input name="retry" type="checkbox"> 我明确重试失败 / 结果未知的调用，理解可能重复计费</label><button class="button" type="submit">续接任务</button></form>`);
  $('#corpusResumeForm').onsubmit=e=>{e.preventDefault();busy(e.target.querySelector('button'),async()=>{
    const form=e.target;
    await api.post(`/staging/${enc(book.id)}/corpus/jobs/${enc(job.id)}`,{action:'resume',retry_failed:$('[name=retry]',form).checked,
      options:{max_calls:Number($('[name=max_calls]',form).value),max_input_chars:Number($('[name=max_input_chars]',form).value)}});
    $('#modalBackdrop').close();toast('任务已续接');await reload();
  });};
}
