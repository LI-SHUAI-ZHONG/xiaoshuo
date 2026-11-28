import {api,enc} from '../api.js';
import {$,$$,esc,icon,drawer,loading,readable,fail,busy,toast} from '../ui.js';
import {methodGate,bindMethodGate} from './project-methods.js';
import {approvedBookDirection,showBookDirectionGate} from '../components/BookDirections.js';
import {approvedChapter,approvedParent,chapterOutline,planArtifacts,scopeName} from '../components/PlanArtifacts.js';

function candidateCard(candidate, index, scope) {
  const body = candidate.root?.body || {};
  const label = scopeName(scope) || `方案 ${index + 1}`;
  const members = candidate.members || [];
  const cards = members.length ? `<details class="details" ${scope && scope !== 'book' ? 'open' : ''}>
    <summary>查看相关设计卡</summary><div>${planArtifacts({members})}</div></details>` : '';
  return `<div class="design-card"><div class="row"><span class="tag blue">${label}</span>
    <h3>${esc(body.title||body.name||'候选方案')}</h3></div>${readable(body)}${cards}</div>`;
}

function formatDeltaVal(value) {
  if (value == null) return '无';
  if (typeof value === 'string') return value;
  try { return JSON.stringify(value); } catch { return String(value); }
}

function batchAcceptanceSummary(target, project) {
  const scenes = Array.isArray(target.scenes) ? target.scenes : [];
  if (!scenes.length || !scenes.some(s => s && typeof s === 'object' && ('draft' in s || 'operations' in s))) return '';
  const head = target.head || {};
  const byId = new Map((project?.scenes || []).map(s => [s.id, s]));
  const scoped = target.material_scope_review;
  const scopedHtml = scoped
    ? `<div class="notice" style="margin-bottom:14px"><strong>跨场材料复核（16 scope_review）：</strong>${esc(scoped.summary || scoped.recommendation || scoped.status || '已完成本批跨场核验')}</div>`
    : '';
  const cards = scenes.map((item, idx) => {
    const meta = byId.get(item.scene_id);
    const title = meta
      ? `第${meta.chapter_index}章 · 场${meta.index} ${meta.card?.title || ''}`.trim()
      : `场景 ${idx + 1} (${item.scene_id || ''})`;
    const draftText = item.draft?.text || '';
    const checks = Array.isArray(item.material_checks) ? item.material_checks : [];
    const passedChecks = checks.filter(c => c.status === 'pass').length;
    const ops = Array.isArray(item.operations) ? item.operations : [];
    const findings = Array.isArray(item.findings) ? item.findings : [];
    const worldOps = ops.filter(op => op.holder === 'WORLD');
    const charOps = ops.filter(op => op.holder !== 'WORLD');
    return `<div class="design-card" style="margin-bottom:14px">
      <div class="row spread wrap" style="margin-bottom:8px">
        <div class="row wrap" style="gap:6px">
          <span class="tag blue">场景 ${idx + 1}</span>
          <h3 style="margin:0">${esc(title)}</h3>
        </div>
        <div class="row wrap" style="gap:6px">
          ${item.draft?.version ? `<span class="tag">版本 v${item.draft.version}</span>` : ''}
          <span class="tag">${draftText.length} 字</span>
          ${checks.length ? `<span class="tag ${passedChecks === checks.length ? 'green' : 'amber'}">16 材料核验 ${passedChecks}/${checks.length}</span>` : ''}
          <span class="tag ${findings.some(f => f.severity === 'hard') ? 'amber' : 'green'}">17 状态增量 ${ops.length} 项</span>
        </div>
      </div>
      <details class="details" style="margin-bottom:8px">
        <summary>预览本场待接受正文（${draftText.length} 字）</summary>
        <div class="prose" style="max-height:240px;overflow:auto;white-space:pre-wrap;margin-top:8px">${esc(draftText || '（正文为空）')}</div>
      </details>
      <div style="margin-top:8px">
        <p class="muted" style="font-size:12px;margin:0 0 6px">17 状态增量：客观世界 ${worldOps.length} 项 · 人物认知 ${charOps.length} 项</p>
        ${ops.length
          ? ops.map(op => `<div class="review-item" style="margin-bottom:6px"><span class="tag ${op.holder === 'WORLD' ? 'blue' : ''}">${esc(op.holder === 'WORLD' ? 'WORLD' : op.holder || '人物')}</span> <strong>${esc([op.entity_id, op.predicate].filter(Boolean).join('.'))}</strong>：${esc(formatDeltaVal(op.expected_old))} → ${esc(formatDeltaVal(op.new_value))}</div>`).join('')
          : '<p class="muted" style="font-size:12px">本场无新增状态变更。</p>'}
      </div>
      ${findings.length ? `<div style="margin-top:8px"><p style="font-size:12px;margin:0 0 6px"><strong>17 事实复核提示（${findings.length}）</strong></p>${findings.map(f => `<div class="review-item"><span class="${f.severity === 'hard' ? 'error' : f.severity === 'soft' ? 'warning' : 'muted'}">${esc(f.severity || 'info')}${f.code ? ` · ${esc(f.code)}` : ''}</span> ${esc(f.explanation || f.message || '')}</div>`).join('')}</div>` : ''}
    </div>`;
  }).join('');
  return `<div id="batchAcceptanceGate"><div class="notice" style="margin-bottom:14px"><strong>16–17 批次稿件与状态增量验收单（共 ${scenes.length} 场）</strong> · 分支 ${esc(head.branch_id || 'main')} · 当前版本 ${head.revision ?? 0}</div>${scopedHtml}${cards}</div>`;
}

export function showGate(gate,{novelId,project,onSaved}){
  if(gate.target?.kind==='book_direction_selection'){showBookDirectionGate(gate,{novelId,onSaved});return;}
  if(gate.target?.kind==='production_method_selection'){methodGate(gate);bindMethodGate(gate,novelId,onSaved);return;}
  const target = gate.target || {};
  const candidates = target.candidates || [], sceneIds = target.scenes || target.scene_ids || [];
  const isChapterOutline = target.kind === 'chapter_outline_approval';
  const isScenePlan = target.scope === 'chapter' && Boolean(target.approved_chapter);
  const isBatchConfirm = String(gate.step || '').includes('batch');
  const parent = target.approved_parent || target.outline_lineage?.at(-1);
  const outline = isChapterOutline ? chapterOutline(target.chapter, target.event_nodes, target.direction) : '';
  const batchSummary = isBatchConfirm ? batchAcceptanceSummary(target, project) : '';
  const summaries = outline || batchSummary || (candidates.length
    ? candidates.map((candidate,index)=>candidateCard(candidate,index,isScenePlan?'scene':target.scope)).join('')
    : readable(Object.fromEntries(Object.entries(target).filter(([key])=>!['token','actions','job_id','step'].includes(key)))));
  const actions = {approve:isChapterOutline?'批准章纲并设计场景':isScenePlan?'批准场景设计':'批准所选方案',
    reject:isChapterOutline?'退回章纲':isBatchConfirm?'退回所选场景或整批':'退回',
    accept:isBatchConfirm?'接受本批正文与状态增量':'接受本场', keep:'保留当前草稿', confirm:'确认', continue:'继续'};
  drawer(gate.summary,`<div class="notice">核对当前方案并填写决定理由。确认结果会保存在制作档案中。</div><div class="divider"></div>${approvedBookDirection(target.approved_direction)}${approvedParent(parent)}${approvedChapter(target.approved_chapter)}${summaries}${candidates.length?`<label class="field"><span>要批准的方案</span><select id="gateCandidate">${candidates.map((c,i)=>`<option value="${esc(c.root.card_id)}">方案 ${i+1} · ${esc(c.root.body?.title||c.root.body?.name||c.root.kind||'候选')}</option>`).join('')}</select></label>`:''}${String(gate.step).includes('batch')?`<label class="field" style="margin-top:16px"><span>退回时选择场景</span><select id="gateScene"><option value="">请选择需要退回的场景</option>${project.scenes.filter(s=>!sceneIds.length||sceneIds.some(i=>(typeof i==='string'?i:i.scene_id||i.id)===s.id)).map(s=>`<option value="${esc(s.id)}">第${s.chapter_index}章 · 场${s.index} ${esc(s.card?.title||'')}</option>`).join('')}</select></label>`:''}<label class="field" style="margin-top:16px"><span>决定理由（必填）</span><textarea id="gateReason" rows="3" required placeholder="记录你选择、接受或退回的原因"></textarea></label><div class="row wrap" style="margin-top:20px">${(gate.actions||[]).map(a=>`<button class="${a==='reject'?'ghost':'secondary'}" data-gate-action="${esc(a)}">${esc(actions[a]||a)}</button>`).join('')}</div><details class="details"><summary>高级 · 节点原始记录</summary><pre class="raw-data">${esc(JSON.stringify(gate,null,2))}</pre></details>`);
  $$('[data-gate-action]').forEach(b=>b.onclick=()=>busy(b,async()=>{const reason=$('#gateReason').value.trim();if(!reason)throw new Error('请填写本次决定的理由');const action=b.dataset.gateAction;const body={action,token:gate.token,reason};if($('#gateCandidate'))body.root=$('#gateCandidate').value;if(action==='reject'&&$('#gateScene')?.value)body.scene_id=$('#gateScene').value;const r=await api.post(`/novels/${enc(novelId)}/gates/${enc(gate.id)}`,body);$('#drawer').close();toast(r.reason||'作者决定已留档');await onSaved();}));
}
export async function showBranches(novelId,onSaved){drawer('制作候选与主线',loading());try{const status=await api.get(`/novels/${enc(novelId)}/branches`);const current=status.current_branch;const revalNames=(status.revalidation_details||[]).length?status.revalidation_details.map(r=>r.label):(status.needs_revalidation||[]);const changedNames=(status.changed_scene_details||[]).length?status.changed_scene_details.map(r=>r.label):(status.changed_scenes||[]);$('#drawerBody').innerHTML=`<div class="notice">主线保存当前正式故事。后续章节与修订在候选中制作，通过检查后由作者确认并入主线。</div><div class="section-head"><h3>当前：${current==='main'?'主线':esc(current)}</h3></div><div class="metric"><span>主线版本</span><span>${status.main_head?.revision??'—'}</span></div>${status.candidate_head?`<div class="metric"><span>候选版本</span><span>${status.candidate_head.revision}</span></div>`:''}${current!=='main'&&(changedNames.length||status.settings_changed)?`<div class="card" style="margin:14px 0"><div class="row wrap" style="gap:6px;margin-bottom:6px">${status.settings_changed?'<span class="tag blue">已更新设定/大纲</span>':''}<span class="tag green">候选已接受变更 ${changedNames.length} 场</span></div>${changedNames.length?`<p class="muted" style="margin:0;font-size:12px">${changedNames.map(esc).join('、')}</p>`:''}</div>`:''}${status.blockers?.length?`<div class="notice warning" style="margin:18px 0">${status.blockers.map(esc).join('<br>')}</div>`:''}${status.needs_revalidation?.length?`<div class="card"><h3>需要重新审稿的场景</h3><p class="muted">${revalNames.map(esc).join('、')}</p><button class="secondary" id="revalidateCandidate" style="margin-top:16px">启动候选修订与复核</button></div>`:''}<div class="section-head"><h3>已有分支</h3></div>${(status.branches||[]).map(b=>`<div class="todo-row"><div class="grow"><strong>${esc(b.id==='main'?'主线':b.id)}</strong><p class="muted">版本 ${b.head.revision}${b.is_current?' · 当前工作分支':''}${b.id!=='main'&&b.can_promote?' · 可并入主线':''}</p></div>${!b.is_current?`<button class="secondary" data-select-branch="${esc(b.id)}">切换</button>`:''}</div>`).join('')}<div class="divider"></div><label class="field"><span>建立新候选（名称选填）</span><input id="candidateName" placeholder="例如 第二章候选" maxlength="64"></label><button class="secondary" id="forkCandidate" style="margin-top:14px" ${!status.managed_story?'disabled':''}>${icon('plus')} 从主线建立制作候选</button>${current!=='main'?`<div class="divider"></div><label class="field"><span>并入主线的作者确认理由</span><textarea id="promoteReason" rows="3" placeholder="说明本次候选审查结果与接受原因"></textarea></label><button class="secondary" id="promoteCandidate" style="margin-top:14px" ${!status.can_promote?'disabled':''}>${icon('check')} 确认并入主线</button>`:''}`;
  $('#forkCandidate').onclick=e=>busy(e.currentTarget,async()=>{await api.post(`/novels/${enc(novelId)}/branches/fork`,{name:$('#candidateName').value.trim()||undefined,reason:'作者从客户端建立制作候选',expected_main:status.main_head?.revision});toast('已建立并选中制作候选');await onSaved();await showBranches(novelId,onSaved);});
  $$('[data-select-branch]').forEach(b=>b.onclick=()=>busy(b,async()=>{await api.post(`/novels/${enc(novelId)}/branches/select`,{branch_id:b.dataset.selectBranch});toast('已切换工作分支');await onSaved();await showBranches(novelId,onSaved);}));
  $('#revalidateCandidate')?.addEventListener('click',e=>busy(e.currentTarget,async()=>{const result=await api.post(`/novels/${enc(novelId)}/run`,{mode:'revise',scene_ids:status.needs_revalidation,scope:'chapter'});toast(result.reason||'修订复核已启动');$('#drawer').close();await onSaved();}));
  $('#promoteCandidate')?.addEventListener('click',e=>busy(e.currentTarget,async()=>{const reason=$('#promoteReason').value.trim();if(!reason)throw new Error('请填写并入主线的作者确认理由');const r=await api.post(`/novels/${enc(novelId)}/branches/promote`,{reason,branch_id:current,expected_main:status.main_head.revision,expected_candidate:status.candidate_head.revision});if(r.status==='BLOCKED'){toast((r.blockers||[]).join('；')||'候选尚未通过检查',true);await showBranches(novelId,onSaved);return;}toast('候选已通过检查并入主线');await onSaved();await showBranches(novelId,onSaved);}));
  }catch(error){$('#drawerBody').innerHTML=`<p class="error">${esc(error.message)}</p>`;fail(error);}}
