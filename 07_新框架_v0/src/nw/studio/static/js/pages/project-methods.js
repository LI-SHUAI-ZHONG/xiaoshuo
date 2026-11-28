import {api,enc} from '../api.js';
import {$,$$,esc,drawer,loading,readable,busy,toast,fail} from '../ui.js';
import {matchLabel, methodEvidence} from '../components/MethodEvidence.js';

const names={type_selection:'立项类型契约（自动冻结）',type_adaptation:'多类型融合适配',world_design:'世界规则定稿',character_design:'核心人物定稿',static_relations:'人物关系张力',plot_design:'故事大纲与卷章切分',event_design:'本章事件链',action_design:'行动博弈与代价',scene_design:'场景卡与POV',state_transition:'场内状态变化',state_propagation:'状态连锁传播',anchor_design:'具象动作锚点',expression_design:'叙述与表达指导',bind_scope:'可写场景工作包',brief:'立项需求',parent_outline:'上层大纲',accepted_state:'已接受状态',type_choice:'前置契约·类型边界',world_rules:'世界规则与限制',character_arc:'人物目标与弧光',relationships:'人物关系与势力',main_plot:'全书主线与结局兑现',subplot:'支线与主线交汇',volume_outline:'卷纲目标与逐章切分',chapter_outline:'连续章纲与承接',event_chain:'事件触发与因果',action_chain:'行动、阻碍与代价',scene_composition:'场景职责与选择',state_change:'人物与关系状态变化',anchors:'可见线索与表现锚点',information:'信息披露与悬念',hook:'钩子与问题接力',foreshadow:'伏笔埋设与回收',pacing:'节奏与情绪序列',expression:'叙事、对话与文风',narration:'叙述时序、视角与呈现',method_binding:'方法交接与核验'};
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
    ${row.design_needs?.length?`<div class="method-section"><h4>AI 采用这条方法时所依据的本书需求</h4>${row.design_needs.map(need=>`<p>${esc(names[need.kind]||need.kind)} · ${esc(need.value)}</p>`).join('')}</div>`:row.selection_origin==='ai'?'<p class="muted">AI 按本步需求采用</p>':''}
    ${row.application?row.application.operations.map(op=>`<p>${esc(op.explanation)}</p>`).join('')+row.application.outputs.flatMap(o=>o.placements).map(p=>`<div class="method-section"><h4>实际设计产物</h4>${paragraphs(p.value)}</div>`).join(''):row.receipt?`<p>${esc(row.receipt.operation)}</p>${row.receipt.placements.map(p=>`<div class="method-section"><h4>下游实际产物</h4>${paragraphs(p.value)}</div>`).join('')}`:'<p>只有送达记录，尚无有效产物。</p>'}
    <details class="details"><summary>高级 · 版本与具体字段</summary>${readable(row)}</details></article>`).join('');
}

export function wizardMethods(bookWorldAvailable) {
  return `<fieldset class="method-section"><legend>参考作品制作方法</legend>
    <p>世界设计由 AI 根据本书类型和前一步的适配需求，选用对应参考小说中有原文依据的制作方法，生成本书的规则与限制。无需预写世界卡。</p>
    ${bookWorldAvailable ? '' : '<p class="warning" role="status">当前类型缺少已批准的全书世界规则方法。可以先保存立项。全书设计走到世界设计时，需要从类型资料库补齐相应方法。</p>'}
  </fieldset>`;
}

export function methodGate(gate, {checked = new Set(), reason = ''} = {}) {
  const {target} = gate;
  const missingTasks = (target.missing_tasks || []).map(key => esc(names[key] || key));
  const maxMethods = target.max_methods || 6;
  const initialSelectedCount = (target.candidates || []).filter(item => !item.missing.length && checked.has(item.method.snapshot_sha256)).length;
  return drawer('选择具体方法并确认前置', `<p class="notice">核对方法的适用条件、预期落点字段与项目前置。新生成的设计会另行提交审核。</p>
    <div class="row spread wrap">
      <p><strong>${esc(names[target.stage] || target.stage)}</strong> · ${target.required_tasks.map(key => esc(names[key] || key)).join('、') || '按本步需要选用'} <span class="tag blue" id="methodGateCount">已选 ${initialSelectedCount} / 上限 ${maxMethods}</span></p>
      <button type="button" class="secondary" id="refreshMethodCandidates">刷新方法候选</button>
    </div>
    ${missingTasks.length ? `<div class="notice warning"><strong>以下职责缺少前置就绪的方法：${missingTasks.join('、')}</strong><div class="row wrap" style="margin-top:8px"><a class="secondary" href="#/kb/items?stage=${enc(target.stage)}" data-project-method-source>前往类型资料库补本步方法</a><a class="ghost" href="#/staging" data-project-method-source>前往预存库拆解</a></div></div>` : ''}
    <div class="stack">${target.candidates.map(item => {
      const {method} = item;
      const snapshot = method.snapshot_sha256;
      const targetOutputs = (item.outputs || []).map(o => `${names[o.stage] || o.stage}·${o.field}${o.artifact_kind !== 'stage_product' ? `(${o.artifact_kind})` : ''}`).join('、');
      const consumers = [...new Set((method.body.downstream || []).map(d => names[d.consumer] || d.consumer))].join('、');
      return `<section class="card">
        <label class="check-row"><input name="projectMethod" type="checkbox" value="${esc(method.id)}" data-snapshot="${esc(snapshot)}" ${item.missing.length ? 'disabled' : checked.has(snapshot) ? 'checked' : ''}> ${esc(method.body.title)} · v${method.version}</label>
        ${item.type_match || item.preferred ? `<p class="muted">${[matchLabel(item.type_match), item.preferred ? '立项已选' : ''].filter(Boolean).map(esc).join(' · ')}</p>` : ''}
        ${targetOutputs ? `<p class="muted">落点产物：${esc(targetOutputs)}${consumers ? ` ｜ 下游交接：${esc(consumers)}` : ''}</p>` : ''}
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
  const maxMethods = gate.target?.max_methods || 6;
  const syncGateCount = () => {
    const picked = $$('[name=projectMethod]:checked').length;
    const badge = $('#methodGateCount');
    if (badge) badge.textContent = `已选 ${picked} / 上限 ${maxMethods}`;
  };
  $$('[name=projectMethod]').forEach(cb => cb.addEventListener('change', () => {
    if (cb.checked && $$('[name=projectMethod]:checked').length > maxMethods) {
      cb.checked = false;
      toast(`本步最多采用 ${maxMethods} 条方法`, true);
    }
    syncGateCount();
  }));
  $$('[data-project-method-source]').forEach(link => link.onclick = () => $('#drawer').close());
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
      <label class="check-row"><input name="aiWorld" type="checkbox" ${policy.world_selection==='ai'?'checked':''}> 世界规则由 AI 按前置需求从参考小说方法中选用并设计</label>
      <label class="field"><span>后续方法选择</span><select name="recommendationMode">
        <option value="manual" ${policy.recommendation_mode==='auto'?'':'selected'}>人工选择</option>
        <option value="auto" ${policy.recommendation_mode==='auto'?'selected':''}>AI 自动（自动覆盖七大板块、启用 AI 世界规则，每步上限不超过 3 条）</option>
      </select></label>
      ${!data.project_type_ids.length?`<label class="field"><span>本项目实际类型（旧项目需先明确，最多选 8 项）</span><select name="types" multiple size="6">${genres.genres.flatMap(g=>[g,...g.children]).map(g=>`<option value="${esc(g.id)}">${esc(g.name)}</option>`).join('')}</select></label>`:''}
      <fieldset class="method-section"><legend>本项目需要的制作职责</legend>${catalog.tasks.map(t=>`<label class="check-row"><input name="tasks" type="checkbox" value="${t.id}" ${tasks.includes(t.id)?'checked':''}>${esc(t.name)}</label>`).join('')}</fieldset>
      <label class="field"><span>每步最多采用的方法数</span><input name="max_methods" type="number" min="1" max="12" value="${policy.max_methods||6}"></label>
      <label class="field"><span>修改依据</span><textarea name="reason" required rows="3"></textarea></label>
      <p class="muted">保存用于下一次新建设计任务；关闭不撤销已批准父纲，仍须承接其设计。当前任务保留冻结配置；如需改当前任务，先取消后新建设计，已有正文继续按候选分支规则处理。</p>
      <button class="button" type="submit">保存后续制作配置</button></form>
      ${data.handoff_audit ? `<section class="method-section card stack" id="projectHandoffAudit">
        <div class="row spread wrap"><h3>本项目下一步拆解产物接收体检</h3>
          <div class="row wrap">
            <span class="tag green">当前配置可接收 ${data.handoff_audit.summary?.receivable_methods || 0} 条</span>
            ${data.handoff_audit.summary?.inactive_methods ? `<span class="tag amber">未启用职责 ${data.handoff_audit.summary.inactive_methods} 条</span>` : ''}
            ${data.handoff_audit.summary?.blocked_methods ? `<span class="tag" style="color:var(--danger)">受阻 ${data.handoff_audit.summary.blocked_methods} 条</span>` : ''}
          </div></div>
        <p class="muted">全书世界方法：${data.handoff_audit.summary?.book_world_ready ? '已就绪' : '待补'} ｜ 人物分布样本：${data.handoff_audit.summary?.cast_sample_ready ? '已就绪' : '待补'} ｜ 段落技法：${data.handoff_audit.summary?.passage_reference_count || 0} 条</p>
        ${(data.handoff_audit.originality_audit?.warnings || []).map(w => `<div class="notice warning">${esc(w.message)}</div>`).join('')}
        <p class="muted">已接通步骤：${(data.handoff_audit.steps || []).filter(s => s.receivable_count > 0).map(s => `${esc(s.short_name)}（${s.receivable_count}）`).join(' · ') || '暂无'}</p>
      </section>` : ''}
      ${data.method_references?.length ? `<section class="method-section"><h3>立项保存的方法版本</h3>${data.method_references.map(method => `
        <details class="details"><summary>${esc(method.title)} · v${method.version} · ${esc(matchLabel(method.type_match))}</summary>
          ${methodEvidence(method)}
        </details>`).join('')}</section>` : ''}
      <section class="method-section"><h3>符合本项目类型的已批准制作方法：${data.available_methods.length}</h3>${data.available_methods.map(m=>{
        const stageText=(m.stages||[]).map(st=>names[st]||st).join('、');
        const stTag=m.handoff_status==='receivable'?'<span class="tag green">当前配置可接收</span>':m.handoff_status==='inactive_by_policy'?'<span class="tag amber">未勾选对应职责</span>':'<span class="tag" style="color:var(--danger)">前置/条件受阻</span>';
        return `<div style="margin-bottom:8px"><p><a href="#/kb/items?method=${enc(m.id)}&version=${m.version}" data-project-method-source>${esc(m.title)} · v${m.version}</a> ${stTag}</p>${stageText?`<small class="muted">目标步骤：${esc(stageText)}</small>`:''}${m.block_reasons?.length?`<br><small class="muted">${esc(m.block_reasons[0])}</small>`:''}</div>`;
      }).join('')||'<p>暂无适用方法。可在<a href="#/staging" data-project-method-source>预存库</a>导入对应类型作品，批准结构拆解并提炼制作方法。</p>'}</section>
      <section class="method-section" id="actualProjectMethodUses"><h3>本项目实际执行与下游回执</h3>${data.uses.length?usageRows(data.uses):'<p>尚无执行记录；开启配置不等于已经使用。</p>'}</section>
      <section class="method-section"><h3>正文独立审稿证据</h3>${data.review_checks.length?readable(data.review_checks):'<p>尚无正文方法核验证据。</p>'}</section>`;
    $$('[data-project-method-source]').forEach(link=>link.onclick=()=>$('#drawer').close());
    $('#projectMethodSettings [name=recommendationMode]')?.addEventListener('change',e=>{
      if(e.target.value==='auto'){
        const form=$('#projectMethodSettings');
        if($('[name=enabled]',form))$('[name=enabled]',form).checked=true;
        if($('[name=aiWorld]',form))$('[name=aiWorld]',form).checked=true;
      }
    });
    $('#projectMethodSettings').onsubmit=e=>{e.preventDefault();busy(e.target.querySelector('[type=submit]'),async()=>{
      const form=e.target, aiWorld=$('[name=aiWorld]',form).checked;
      const tasks=$('[name=enabled]',form).checked?$$('[name=tasks]:checked',form).map(x=>x.value):[];
      if(aiWorld && !tasks.includes('world_rules')) tasks.push('world_rules');
      const next=tasks.length?{tasks,max_methods:Number($('[name=max_methods]',form).value),
        recommendation_mode:$('[name=recommendationMode]',form).value,...(aiWorld?{world_selection:'ai'}:{})}:null;
      if(next&&$('[name=types]',form)){
        const types=Array.from($('[name=types]',form).selectedOptions).map(o=>o.value);
        if(types.length>8)throw new Error('项目类型最多选择 8 项');
        next.type_ids=types;
      }
      await api.post(`/novels/${enc(novelId)}/methods`,{policy:next,reason:$('[name=reason]',form).value});toast('后续制作配置已保存，当前任务保持冻结版本');await showProjectMethods(novelId);
    });};
  }catch(error){fail(error);$('#drawerBody').innerHTML=`<p class="error">${esc(error.message)}</p>`;}
}
