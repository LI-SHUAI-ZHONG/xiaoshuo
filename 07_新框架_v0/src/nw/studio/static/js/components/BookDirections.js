import {api, enc} from '../api.js';
import {$, busy, drawer, esc, toast} from '../ui.js';

const fields = [
  ['opening_hook', '开篇与黄金三章钩子'],
  ['protagonist', '主角处境'],
  ['goal', '主角目标'],
  ['conflict', '核心矛盾'],
  ['story_arcs', '全书阶段因果路线'],
  ['protagonist_arc', '主角核心弧光'],
  ['world_premise', '世界前提'],
  ['design_needs', '所需世界规则与人物条件'],
  ['long_term_drive', '长篇推进'],
  ['type_fit', '类型依据'],
  ['author_fit', '立项要求落实'],
];

function cards(candidates, selectedId = null, choosing = false) {
  return `<div class="direction-grid">${candidates.map((candidate, index) => {
    const selected = candidate.id === selectedId;
    const title = esc(candidate.title);
    const inputId = `direction-choice-${index}`;
    const heading = choosing
      ? `<label class="row direction-choice" for="${inputId}"><input type="radio" name="root"
          id="${inputId}" value="${esc(candidate.id)}" required><strong>${title}</strong></label>`
      : `<div class="row spread direction-title"><h3>${title}</h3>${selected ? '<span class="tag green">已选定</span>' : ''}</div>`;
    return `<article class="direction-card${selected ? ' selected' : ''}">${heading}
      <p class="direction-premise">${esc(candidate.premise)}</p>
      <dl>${fields.filter(([field]) => candidate[field]).map(([field, label]) =>
        `<div><dt>${label}</dt><dd>${esc(candidate[field])}</dd></div>`).join('')}</dl></article>`;
  }).join('')}</div>`;
}

export function approvedBookDirection(direction) {
  if (!direction?.candidate) return '';
  return `<details class="details" open><summary>本套全书方案沿用的短案</summary>
    ${cards([direction.candidate], direction.candidate_id)}</details>`;
}

export function renderBookDirections(editor, node, openDecision) {
  const {candidates = [], selected_id = null} = node.output || {};
  const guidance = {
    pending: '制作开始后会生成几份方向短案，供你比较和选择。',
    running: '正在根据类型、选材和立项要求生成方向短案。',
    waiting: '请选定一个方向，世界、人物和剧情设计会围绕它展开。',
    done: '世界、人物和剧情设计沿用你选定的方向。',
    rejected: '作者已退回这批方向。制作台可以重新生成方向。',
    blocked: '方向短案生成遇到阻碍，请查看制作台当前提示。',
    failed: '方向短案生成失败，请查看制作台当前提示。',
  };
  editor.innerHTML = `<h2>${esc(node.label)}</h2>
    <p class="direction-intro">${esc(guidance[node.status] || '可查看本轮方向短案和作者决定。')}</p>
    ${openDecision ? '<div class="row direction-intro"><button type="button" class="button" id="chooseBookDirection">选择全书方向</button></div>' : ''}
    ${cards(candidates, selected_id)}`;
  if (openDecision) $('#chooseBookDirection', editor).onclick = openDecision;
}

export function showBookDirectionGate(gate, {novelId, onSaved}) {
  const dialog = drawer('选择全书方向', `<form id="bookDirectionDecision" class="direction-decision">
    <fieldset><legend class="direction-intro">比较短案，选定接下来要深化的一个方向。</legend>
      ${cards(gate.target.candidates, null, true)}
    </fieldset>
    <label class="field direction-intro"><span>决定理由（必填）</span>
      <textarea name="reason" rows="3" required placeholder="记录选择或退回的原因"></textarea></label>
    <div class="row wrap direction-intro">
      ${gate.actions.includes('approve') ? '<button type="submit" class="button" name="action" value="approve">确认方向并继续设计</button>' : ''}
      ${gate.actions.includes('reject') ? '<button type="submit" class="ghost" name="action" value="reject" formnovalidate>退回全部方向</button>' : ''}
    </div></form>`);
  const form = $('#bookDirectionDecision', dialog);
  form.onsubmit = event => {
    event.preventDefault();
    const button = event.submitter;
    if (!button || form.inert) return;
    const action = button.value;
    const reason = form.elements.reason.value.trim();
    const body = {action, token:gate.token, reason};
    if (action === 'approve') {
      const selected = $('input[name="root"]:checked', form);
      if (!selected) return;
      body.root = selected.value;
    }
    if (!reason) {
      toast('请填写本次决定的理由', true);
      form.elements.reason.focus();
      return;
    }
    form.inert = true;
    busy(button, async () => {
      try {
        const result = await api.post(`/novels/${enc(novelId)}/gates/${enc(gate.id)}`, body);
        if (form.isConnected) dialog.close();
        toast(result.reason || (action === 'approve' ? '已选定全书方向' : '已退回这批方向'));
        await onSaved();
      } finally {
        form.inert = false;
      }
    });
  };
}
