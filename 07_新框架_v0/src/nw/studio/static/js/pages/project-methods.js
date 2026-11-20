import {api,enc} from '../api.js';
import {$,$$,esc,drawer,loading,readable,busy,toast,fail} from '../ui.js';
import {matchLabel, methodEvidence} from '../components/MethodEvidence.js';

const names={type_selection:'类型选择',type_adaptation:'类型适配',world_design:'世界设计',character_design:'人物设计',static_relations:'人物关系',plot_design:'剧情设计',event_design:'事件设计',action_design:'行动设计',scene_design:'场景设计',state_transition:'状态变化',state_propagation:'后果传播',anchor_design:'表现锚点',expression_design:'表达设计',bind_scope:'交接汇总',brief:'立项需求',parent_outline:'上层大纲',accepted_state:'已接受状态',hook:'钩子与问题接力',foreshadow:'伏笔与兑现',pacing:'节奏与情绪',main_plot:'主线与结局',character_arc:'人物弧光'};
const words=value=>typeof value==='string'?[value]:Array.isArray(value)?value.flatMap(words):value&&typeof value==='object'?Object.entries(value).filter(([key])=>!key.startsWith('_')&&!['ref','source_ids','input_refs','output_refs'].includes(key)).flatMap(([,v])=>words(v)):[];
const paragraphs=value=>words(value).filter((v,i,a)=>v&&a.indexOf(v)===i).map(v=>`<p class="corpus-text">${esc(v)}</p>`).join('');
function methodDetails(item){
  const method=item.method;
  return `<div class="stack">${Object.entries(item.inputs).map(([key,input])=>{const requirement=method.body.prerequisites.find(p=>p.key===key);return `<section class="method-section"><h3>${esc(requirement?.artifact||names[input.kind]||input.kind)}</h3><p>${esc(requirement?.requirement||'')}</p><p class="muted">${input.status==='proposed_requires_author'?'本次新设计，需确认后作为方法前置':'已有批准产物或作者立项输入'} · 版本 ${input.ref.version??input.ref.sha256?.slice(0,8)??'已冻结'}</p>${paragraphs(input.value)}</section>`;}).join('')}
    <section class="method-section"><h3>具体操作</h3>${item.operations.map(op=>`<p>${esc(op.instruction)}</p>`).join('')}<h3>本步应产出</h3>${item.outputs.map(o=>`<p>${esc(o.description)}</p>`).join('')}</section>
    <section class="method-section"><h3>原作中的实际设计</h3>${method.instance.threads.map(t=>`<h4>${esc(t.title)}</h4><p>${esc(t.explanation)}</p>${paragraphs(t.details)}`).join('')}<h3>对应事件</h3>${method.instance.events.map(e=>`<p>${esc(e.summary)} · 选择：${esc(e.choice||'原作未明确')} · 后果：${esc(e.result||'原作未明确')}</p>`).join('')}<h3>原文证据</h3>${method.body.evidence.map(e=>`<blockquote class="evidence">${esc(e.quote)}</blockquote><p>${esc(e.explanation)}</p><small>字符 ${e.start}–${e.end}</small>`).join('')}</section>
    <details class="details"><summary>高级 · 冻结版本与完整前置</summary>${readable(item.inputs)}</details></div>`;
}
function usageRows(rows){
  return rows.map(row=>`<article class="card"><h3>${esc(row.title||'下游承接回执')}</h3><p class="muted">${esc(names[row.stage]||row.stage)}${row.method_version?' · 方法版本 '+row.method_version:''} · ${row.validation==='VALID'?'执行结果已校验':'尚未通过执行校验'}</p>
    ${row.application?row.application.operations.map(op=>`<p>${esc(op.explanation)}</p>`).join('')+row.application.outputs.flatMap(o=>o.placements).map(p=>`<div class="method-section"><h4>实际设计产物</h4>${paragraphs(p.value)}</div>`).join(''):row.receipt?`<p>${esc(row.receipt.operation)}</p>${row.receipt.placements.map(p=>`<div class="method-section"><h4>下游实际产物</h4>${paragraphs(p.value)}</div>`).join('')}`:'<p>只有送达记录，尚无有效产物。</p>'}
    <details class="details"><summary>高级 · 版本与具体字段</summary>${readable(row)}</details></article>`).join('');
}

export function wizardMethods(enabled, hasSelections) {
  return `<fieldset class="method-section"><legend>参考作品制作方法</legend>
    <label class="check-row"><input type="checkbox" id="wizardUseMethods" ${enabled ? 'checked' : ''} ${hasSelections ? 'disabled' : ''}> 按已批准的拆解方法制作</label>
    <p class="muted">默认需要人物弧光、全书主线、钩子和节奏方法。制作台会在相关步骤列出候选及其前置，供你确认。</p>
    ${hasSelections ? '<p class="muted">已选方法随立项保存。如需关闭，请先移除所选方法。</p>' : ''}
  </fieldset>`;
}

export function methodGate(gate, {checked = new Set(), reason = ''} = {}) {
  const {target} = gate;
  const missingTasks = (target.missing_tasks || []).map(key => esc(names[key] || key));
  return drawer('选择具体方法并确认前置', `<p class="notice">核对方法的适用条件和项目前置。新生成的设计会另行提交审核。</p>
    <div class="row spread wrap">
      <p>${esc(names[target.stage] || target.stage)} · ${target.required_tasks.map(key => esc(names[key] || key)).join('、') || '按本步需要选用'}</p>
      <button type="button" class="secondary" id="refreshMethodCandidates">刷新方法候选</button>
    </div>
    ${missingTasks.length ? `<p class="error">以下职责缺少前置就绪的方法 · ${missingTasks.join('、')}。可补充资料后刷新。</p>` : ''}
    <div class="stack">${target.candidates.map(item => {
      const {method} = item;
      const snapshot = method.snapshot_sha256;
      return `<section class="card">
        <label class="check-row"><input name="projectMethod" type="checkbox" value="${esc(method.id)}" data-snapshot="${esc(snapshot)}" ${item.missing.length ? 'disabled' : checked.has(snapshot) ? 'checked' : ''}> ${esc(method.body.title)} · v${method.version}</label>
        ${item.type_match || item.preferred ? `<p class="muted">${[matchLabel(item.type_match), item.preferred ? '立项已选' : ''].filter(Boolean).map(esc).join(' · ')}</p>` : ''}
        <p>${method.body.applicability.map(esc).join('。')}</p><p class="muted">不适用情况 · ${method.body.non_applicability.map(esc).join('。')}</p>
        ${item.missing.length ? `<p class="error">缺少前置 · ${item.missing.map(input => esc(input.artifact)).join('、')}</p>` : ''}
        <details class="details"><summary>核对当前项目前置、操作和原作实例</summary>${methodDetails(item)}</details>
      </section>`;
    }).join('') || '<p class="muted">当前没有可以推荐的方法。</p>'}</div>
    <label class="field"><span>适用性判断与前置确认依据</span><textarea id="gateReason" required rows="4">${esc(reason)}</textarea></label>
    <div class="row wrap"><button class="button" data-method-action="approve" ${missingTasks.length ? 'disabled' : ''}>批准所选方法与前置</button>
      <button class="secondary" data-method-action="reject">退回补设计</button></div>`);
}

export function bindMethodGate(gate, novelId, onSaved) {
  const path = `/novels/${enc(novelId)}/gates/${enc(gate.id)}`;
  const refresh = $('#refreshMethodCandidates');
  refresh.onclick = () => busy(refresh, async () => {
    const panel = $('#drawer');
    const actions = $$('[data-method-action]').filter(button => !button.disabled);
    actions.forEach(button => button.disabled = true);
    try {
      const result = await api.post(`${path}/refresh`);
      if (panel.open && refresh.isConnected) {
        if (result.changed) {
          const checked = new Set($$('[name=projectMethod]:checked').map(input => input.dataset.snapshot));
          methodGate(result.gate, {checked, reason:$('#gateReason').value});
          bindMethodGate(result.gate, novelId, onSaved);
        }
        toast(result.changed ? '已更新方法候选，请核对新版本' : '方法候选已是最新版');
      }
      if (result.changed) await onSaved();
    } finally {
      actions.forEach(button => { if (button.isConnected) button.disabled = false; });
    }
  });
  $$('[data-method-action]').forEach(button=>button.onclick=()=>busy(button,async()=>{
    const reason=$('#gateReason').value.trim();if(!reason)throw new Error('请说明适用性判断与前置确认依据');
    const result=await api.post(path,{action:button.dataset.methodAction,
      reason,token:gate.token,method_ids:$$('[name=projectMethod]:checked').map(x=>x.value)});
    $('#drawer').close();toast(result.reason||'方法与前置确认已保存');await onSaved();
  }));
}

export async function showProjectMethods(novelId){
  drawer('具体制作方法与使用回执',loading());
  try{
    const [data,catalog,genres]=await Promise.all([api.get(`/novels/${enc(novelId)}/methods`),api.get('/kb/method-catalog'),api.get('/genres')]);
    const policy=data.policy,tasks=policy.tasks||data.default_tasks;
    $('#drawerBody').innerHTML=`<p class="notice">${esc(data.note)}</p><form id="projectMethodSettings" class="stack">
      <label class="check-row"><input name="enabled" type="checkbox" ${policy.policy?'checked':''}> 后续设计使用已批准的拆解方法</label>
      ${!data.project_type_ids.length?`<label class="field"><span>本项目实际类型（旧项目需先明确）</span><select name="types" multiple size="6">${genres.genres.flatMap(g=>[g,...g.children]).map(g=>`<option value="${esc(g.id)}">${esc(g.name)}</option>`).join('')}</select></label>`:''}
      <fieldset class="method-section"><legend>本项目需要的制作职责</legend>${catalog.tasks.map(t=>`<label class="check-row"><input name="tasks" type="checkbox" value="${t.id}" ${tasks.includes(t.id)?'checked':''}>${esc(t.name)}</label>`).join('')}</fieldset>
      <label class="field"><span>每步最多采用的方法数</span><input name="max_methods" type="number" min="1" max="12" value="${policy.max_methods||6}"></label>
      <label class="field"><span>修改依据</span><textarea name="reason" required rows="3"></textarea></label>
      <p class="muted">保存用于下一次新建设计任务；关闭不撤销已批准父纲，仍须承接其设计。当前任务保留冻结配置；如需改当前任务，先取消后新建设计，已有正文继续按候选分支规则处理。</p>
      <button class="button" type="submit">保存后续制作配置</button></form>
      ${data.method_references?.length ? `<section class="method-section"><h3>立项保存的方法版本</h3>${data.method_references.map(method => `
        <details class="details"><summary>${esc(method.title)} · v${method.version} · ${esc(matchLabel(method.type_match))}</summary>
          ${methodEvidence(method)}
        </details>`).join('')}</section>` : ''}
      <section class="method-section"><h3>资料库已批准且有结构来源的方法：${data.available_methods.length}</h3>${data.available_methods.map(m=>`<p><a href="#/kb/items?method=${enc(m.id)}" data-project-method-source>${esc(m.title)} · v${m.version}</a></p>`).join('')||'<p>尚无完整方法。请先拆解对应类型作品并审核结构及方法。</p>'}</section>
      <section class="method-section" id="actualProjectMethodUses"><h3>本项目实际执行与下游回执</h3>${data.uses.length?usageRows(data.uses):'<p>尚无执行记录；开启配置不等于已经使用。</p>'}</section>
      <section class="method-section"><h3>正文独立审稿证据</h3>${data.review_checks.length?readable(data.review_checks):'<p>尚无正文方法核验证据。</p>'}</section>`;
    $$('[data-project-method-source]').forEach(link=>link.onclick=()=>$('#drawer').close());
    $('#projectMethodSettings').onsubmit=e=>{e.preventDefault();busy(e.target.querySelector('[type=submit]'),async()=>{
      const form=e.target;const next=$('[name=enabled]',form).checked?{tasks:$$('[name=tasks]:checked',form).map(x=>x.value),max_methods:Number($('[name=max_methods]',form).value)}:null;
      if(next&&$('[name=types]',form))next.type_ids=Array.from($('[name=types]',form).selectedOptions).map(o=>o.value);
      await api.post(`/novels/${enc(novelId)}/methods`,{policy:next,reason:$('[name=reason]',form).value});toast('后续制作配置已保存，当前任务保持冻结版本');await showProjectMethods(novelId);
    });};
  }catch(error){fail(error);$('#drawerBody').innerHTML=`<p class="error">${esc(error.message)}</p>`;}
}
