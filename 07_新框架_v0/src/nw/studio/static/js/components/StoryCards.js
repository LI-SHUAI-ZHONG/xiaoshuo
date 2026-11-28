import {api, enc} from '../api.js';
import {$, $$, esc, empty, readable, drawer, busy, toast, fail} from '../ui.js';

const kindLabels = {
  world: '世界规则 (world)',
  character: '人物档案 (character)',
  plot: '剧情母题 (plot)',
  promise: '伏笔承诺 (promise)',
  volume: '卷卡 (volume)',
  chapter: '章卡 (chapter)',
  scene: '场景契约 (scene)',
  style: '文风约束 (style)',
  taboo: '禁忌红线 (taboo)',
};

const statusLabels = {
  approved: '已批准生效',
  proposed: '候选待审',
  trial: '试运行',
  disabled: '已停用',
  superseded: '已替代旧版',
  rejected: '已驳回',
};

const kindTemplates = {
  world: {title: '', rule: '', limits: '', visibility: 'public'},
  character: {name: '', role: '', want: '', voice: '', visibility: 'public'},
  plot: {title: '', conflict: '', consequence: '', visibility: 'public'},
  promise: {title: '', setup: '', payoff: '', visibility: 'public'},
  volume: {title: '', goal: '', turn: '', visibility: 'public'},
  chapter: {title: '', goal: '', consequence: '', visibility: 'public'},
  scene: {title: '', goal: '', pov: '', conflict: '', allowed_disclosure: '', characters: [], visibility: 'public'},
  style: {title: '', guidance: '', check: '', visibility: 'public'},
  taboo: {title: '', constraint: '', check: '', visibility: 'public'},
};

function openCardEditorDrawer(novel, existing, onSaved) {
  const isEdit = Boolean(existing);
  const initialKind = existing?.kind || 'world';
  const initialBody = JSON.stringify(existing?.body || kindTemplates[initialKind] || kindTemplates.world, null, 2);
  drawer(isEdit ? `修订设定卡 · ${existing.card_id}` : '新建设定卡（Story Card）', `<form id="storyCardForm" class="stack">
    <div class="form-grid">
      <label class="field"><span>卡片 ID（唯一标识）</span>
        <input name="card_id" value="${esc(existing?.card_id || '')}" ${isEdit ? 'readonly' : 'required'} placeholder="如 world_tide_lock 或 char_lin">
      </label>
      <label class="field"><span>卡片类型（kind）</span>
        <select name="kind" id="storyCardKindSelect" ${isEdit ? 'disabled' : ''}>
          ${Object.entries(kindLabels).map(([k, l]) => `<option value="${esc(k)}" ${initialKind === k ? 'selected' : ''}>${esc(l)}</option>`).join('')}
        </select>
      </label>
    </div>
    <label class="field"><span>卡片内容（JSON，已自动带出该类型必填字段与 visibility）</span>
      <textarea name="body_json" id="storyCardBodyTextarea" rows="9" required spellcheck="false" style="font-family:var(--font-mono,monospace)">${esc(initialBody)}</textarea>
    </label>
    <label class="field"><span>修订/启用说明</span>
      <input name="reason" value="作者在客户端维护设定卡并同步分支可见性" required>
    </label>
    <div class="row wrap" style="gap:16px">
      <label class="row" style="gap:6px"><input type="checkbox" name="auto_approve" checked> 保存后立即批准启用</label>
      <label class="row" style="gap:6px"><input type="checkbox" name="apply_to_branch" checked> 同步应用到当前工作分支（${esc(novel.current_branch || 'main')}）</label>
    </div>
    <div class="row"><button type="submit" class="button">${isEdit ? '保存为新版本' : '创建设定卡'}</button></div>
  </form>`);
  $('#storyCardKindSelect')?.addEventListener('change', e => {
    const tpl = kindTemplates[e.target.value];
    const box = $('#storyCardBodyTextarea');
    if (tpl && box) box.value = JSON.stringify(tpl, null, 2);
  });
  $('#storyCardForm').onsubmit = event => {
    event.preventDefault();
    const fd = new FormData(event.target);
    let parsedBody;
    try {
      parsedBody = JSON.parse(String(fd.get('body_json') || '{}'));
      if (!parsedBody || typeof parsedBody !== 'object' || Array.isArray(parsedBody)) {
        throw new Error('卡片 body 必须是 JSON 对象');
      }
    } catch (err) {
      toast(`JSON 格式有误：${err.message}`, true);
      return;
    }
    const payload = {
      card_id: isEdit ? existing.card_id : String(fd.get('card_id') || '').trim(),
      kind: isEdit ? existing.kind : String(fd.get('kind') || 'world'),
      body: parsedBody,
      reason: String(fd.get('reason') || '').trim(),
      auto_approve: fd.get('auto_approve') === 'on',
      apply_to_branch: fd.get('apply_to_branch') === 'on',
      branch: novel.current_branch || 'main',
    };
    busy(event.target.querySelector('[type="submit"]'), async () => {
      await api.post(`/projects/${enc(novel.project_dir)}/cards`, payload);
      $('#drawer')?.close?.();
      toast(`设定卡 ${payload.card_id} 已保存`);
      await onSaved();
    }).catch(fail);
  };
}

export async function renderStoryCardsTab(host, novel, project, {onReload}, signal) {
  const res = await api.get(`/projects/${enc(novel.project_dir)}/cards`, signal);
  const cards = res.cards || [];
  const readOnly = novel.status === 'done';
  let kindFilter = 'all';
  let statusFilter = 'all';

  function paint() {
    const filtered = cards.filter(c =>
      (kindFilter === 'all' || c.kind === kindFilter) &&
      (statusFilter === 'all' || c.status === statusFilter)
    );
    host.innerHTML = `<section id="storyCardsBrowser" class="stack" style="gap:16px">
      <div class="row spread wrap" style="gap:12px">
        <div class="row wrap" style="gap:10px">
          <label class="field"><span>类型筛选</span><select id="cardKindFilter">
            <option value="all">全部类型（${cards.length}）</option>
            ${Object.entries(kindLabels).map(([k, l]) => `<option value="${esc(k)}" ${kindFilter === k ? 'selected' : ''}>${esc(l)}</option>`).join('')}
          </select></label>
          <label class="field"><span>状态筛选</span><select id="cardStatusFilter">
            <option value="all">全部状态</option>
            ${Object.entries(statusLabels).map(([k, l]) => `<option value="${esc(k)}" ${statusFilter === k ? 'selected' : ''}>${esc(l)}</option>`).join('')}
          </select></label>
        </div>
        ${!readOnly ? '<button type="button" class="secondary" id="newAuthorCardBtn">新建设定卡</button>' : ''}
      </div>
      ${filtered.length ? `<div class="stack" style="gap:12px">${filtered.map((card, idx) => {
        const vis = card.body?.visibility || 'public';
        const holders = Array.isArray(card.body?.holders) ? card.body.holders.join('、') : '';
        const statusCls = card.status === 'approved' ? 'green' : card.status === 'proposed' ? 'amber' : '';
        const title = card.body?.title || card.body?.name || card.card_id;
        return `<div class="card stack" data-card-id="${esc(card.card_id)}">
          <div class="row spread wrap" style="gap:8px">
            <div>
              <strong>${esc(title)}</strong>
              <span class="muted" style="font-size:12px"> · ${esc(card.card_id)} · v${card.version}</span>
            </div>
            <div class="row wrap" style="gap:6px">
              <span class="tag blue">${esc(kindLabels[card.kind] || card.kind)}</span>
              <span class="tag ${statusCls}">${esc(statusLabels[card.status] || card.status)}</span>
              <span class="tag">可见性：${esc(vis)}${holders ? `（${esc(holders)}）` : ''}</span>
            </div>
          </div>
          <details class="details">
            <summary>查看设定字段、关联关系（${(card.links || []).length}）与审批历史（${(card.decisions || []).length}）</summary>
            <div style="margin-top:8px">${readable(card.body)}</div>
            ${(card.links || []).length ? `<p class="muted" style="font-size:12px;margin-top:8px">关联：${card.links.map(l => `${esc(l.relation)} → ${esc(l.target?.card_id || '')}`).join('；')}</p>` : ''}
          </details>
          ${!readOnly ? `<div class="row wrap" style="gap:8px">
            <button type="button" class="ghost" data-edit-card="${idx}">修订新版本</button>
            ${card.status !== 'approved' ? `<button type="button" class="secondary" data-decide-card="${idx}" data-decision="approved">批准启用</button>` : ''}
            ${card.status === 'approved' ? `<button type="button" class="ghost" data-decide-card="${idx}" data-decision="disabled">停用归档</button>` : ''}
          </div>` : ''}
        </div>`;
      }).join('')}</div>` : empty('当前筛选下没有设定卡片', '批准规划步骤产物或点击右上角「新建设定卡」，即可维护带版本和受限知情范围的世界/人物/伏笔卡片。', '', 'layers')}
    </section>`;

    host.querySelector('#cardKindFilter')?.addEventListener('change', e => { kindFilter = e.target.value; paint(); });
    host.querySelector('#cardStatusFilter')?.addEventListener('change', e => { statusFilter = e.target.value; paint(); });
    host.querySelector('#newAuthorCardBtn')?.addEventListener('click', () => openCardEditorDrawer(novel, null, onReload));
    $$('[data-edit-card]', host).forEach(btn => {
      btn.onclick = () => openCardEditorDrawer(novel, filtered[Number(btn.dataset.editCard)], onReload);
    });
    $$('[data-decide-card]', host).forEach(btn => {
      btn.onclick = () => busy(btn, async () => {
        const card = filtered[Number(btn.dataset.decideCard)];
        const decision = btn.dataset.decision;
        await api.post(`/projects/${enc(novel.project_dir)}/cards/decide`, {
          card_id: card.card_id,
          version: card.version,
          decision,
          reason: `作者在设定卡片页执行 ${decision}`,
        });
        toast(`卡片 ${card.card_id} v${card.version} 状态已更新`);
        await onReload();
      }).catch(fail);
    });
  }

  paint();
}
