import {api,enc} from '../api.js';
import {$,$$,esc,icon,empty,number,busy,toast,fail} from '../ui.js';

const promiseStageLabels = {
  unverified: '未核实（仅计划）',
  planted: '已埋设',
  sleeping: '休眠中',
  awake: '已唤醒',
  paid_off: '已回收',
};

const claimLabels = {
  fact: '事实',
  belief: '信念',
  suspicion: '怀疑',
  utterance: '说法',
  plan: '计划',
};

function fmtVal(val) {
  if (val == null) return '—';
  if (typeof val === 'string') return val;
  try { return JSON.stringify(val); } catch { return String(val); }
}

function renderBranchBar(novel, guidance) {
  const isCand = Boolean(guidance?.is_candidate);
  const badge = isCand
    ? `<span class="tag amber">当前候选分支：${esc(guidance.branch_id)}</span>`
    : '<span class="tag green">当前正式主线（main）</span>';
  let hint = '所有章总结与阶段复盘都会随当前分支留档，并自动注入下一章设计。';
  if (guidance?.needs_candidate_branch) {
    hint = '当前主线已规划场景均已接受。如需续写下一章/下一卷，请先前往制作台建立候选分支，完成复核后再并入主线。';
  } else if (isCand && guidance?.needs_revalidation?.length) {
    hint = `候选分支存在 ${guidance.needs_revalidation.length} 场需重新审稿复核的受影响旧稿，复核完成后方可合并回主线。`;
  } else if (isCand && guidance?.can_promote) {
    hint = `候选分支已通过全部检查（变更 ${guidance.changed_scenes_count || 0} 场），可在制作台「制作候选与主线」中审查并入主线。`;
  }
  return `<section class="card" id="continuationBranchBar" style="margin-bottom:20px">
    <div class="row spread wrap" style="gap:8px;margin-bottom:8px">
      <div class="row wrap" style="gap:8px">${badge}${guidance?.latest_completed_chapter ? `<span class="tag blue">最近已完结章：第 ${number(guidance.latest_completed_chapter)} 章</span>` : ''}</div>
      <a class="secondary" href="#/studio/${enc(novel.id)}">${icon('pen')} 返回制作台</a>
    </div>
    <p class="muted" style="margin:0;font-size:13px">${esc(hint)}</p>
  </section>`;
}

function renderChapterReviews(ch, readOnly) {
  const reviews = ch.reviews || [];
  if (!reviews.length) return '';
  return `<div style="margin-top:12px">
    <p style="font-size:12px;margin:0 0 8px"><strong>本章到期 / 可填阶段复盘（${reviews.length}）</strong></p>
    ${reviews.map(rv => {
      const done = rv.status === 'recorded';
      const ready = rv.status === 'ready' || done;
      const badgeCls = done ? 'green' : ready ? 'amber' : '';
      const badgeText = done ? '已留档' : rv.status === 'ready' ? '待复盘' : rv.status === 'state_evidence_pending' ? '缺少状态证据' : '窗口内章稿未齐';
      return `<details class="details" style="margin-bottom:8px" ${ready && !done ? 'open' : ''}>
        <summary><span class="tag ${badgeCls}">${badgeText}</span> ${esc(rv.title)} · <span class="muted">${esc(rv.source)}</span></summary>
        <div style="margin-top:8px">
          <p class="muted" style="font-size:12px;margin:0 0 8px">${esc(rv.instructions)}</p>
          ${ready && !readOnly ? `<form class="stack" data-review-form data-chapter="${ch.index}" data-kind="${esc(rv.kind)}" data-sha="${esc(rv.input_sha256 || '')}">
            <textarea name="finding" rows="3" required placeholder="记录对照正文证据的核查发现与后续调整要点">${esc(rv.finding || '')}</textarea>
            <div class="row"><button type="submit" class="secondary">${done ? '更新复盘结论' : '保存复盘结论'}</button></div>
          </form>` : rv.finding ? `<p style="font-size:13px;white-space:pre-wrap">${esc(rv.finding)}</p>` : `<p class="muted" style="font-size:12px">${rv.missing_chapters?.length ? `待完成章节：第 ${rv.missing_chapters.join('、')} 章` : '完成窗口内所有场景审稿接受后可填写。'}</p>`}
        </div>
      </details>`;
    }).join('')}
  </div>`;
}

function renderChaptersSection(data, readOnly) {
  const chapters = data.chapters || [];
  if (!chapters.length) {
    return `<section id="chapterContinuationList" style="margin-bottom:24px">
      <h3>章总结与周期阶段复盘</h3>
      ${empty('尚无已规划章节', '批准章节设计与正文接受后，可在此记录百字章总结与每 1/3/10 章周期复盘，并自动注入下一章设计。', '', 'book')}
    </section>`;
  }
  return `<section id="chapterContinuationList" style="margin-bottom:24px">
    <div class="row spread wrap" style="margin-bottom:12px">
      <h3 style="margin:0">章总结与周期阶段复盘</h3>
      <span class="muted" style="font-size:12px">已留档记录会自动进入下一章 plot_design 续章上下文</span>
    </div>
    ${chapters.map(ch => {
      const done = ch.summary_status === 'recorded';
      const ready = ch.summary_status === 'ready' || done;
      const statusTag = done
        ? '<span class="tag green">章总结已留档</span>'
        : ch.scope_complete
          ? '<span class="tag amber">章总结待填写</span>'
          : `<span class="tag">仍有 ${ch.pending_scene_ids.length} 场未接受</span>`;
      return `<div class="card" style="margin-bottom:14px">
        <div class="row spread wrap" style="gap:8px;margin-bottom:8px">
          <h4 style="margin:0">第 ${number(ch.index)} 章 · ${esc(ch.title)}</h4>
          <div class="row wrap" style="gap:6px">
            ${statusTag}
            <span class="tag blue">已接受 ${number(ch.accepted_scenes_count)} 场</span>
            <span class="tag">客观变更 ${number(ch.world_changes_count)} · 人物变化 ${number(ch.character_changes_count)}</span>
          </div>
        </div>
        ${ready && !readOnly ? `<form class="stack" data-summary-form data-chapter="${ch.index}" data-sha="${esc(ch.summary_input_sha256 || '')}">
          <label class="field">
            <span>本章百字总结（≤100 字，记录实际落地进展与章末遗留悬念）</span>
            <textarea name="summary" rows="2" maxlength="100" required placeholder="例如：沈砚夜查封条发现破口与铜钥匙，值夜人闪烁其词，引出次日调档冲突。">${esc(ch.summary_text || '')}</textarea>
          </label>
          ${ch.has_preview ? `<label class="field">
            <span>对照章纲偏差说明（选填）</span>
            <input name="comparison" value="${esc(ch.summary_comparison || '')}" placeholder="记录实际正文与原定章纲的差异或调整理由">
          </label>` : ''}
          <div class="row"><button type="submit" class="secondary">${done ? '更新章总结' : '保存章总结'}</button></div>
        </form>` : ch.summary_text
          ? `<p style="margin:6px 0;font-size:13px"><strong>章总结：</strong>${esc(ch.summary_text)}</p>${ch.summary_comparison ? `<p class="muted" style="margin:4px 0;font-size:12px">章纲对照：${esc(ch.summary_comparison)}</p>` : ''}`
          : '<p class="muted" style="font-size:12px;margin:4px 0">本章所有已批准场景完成审稿接受后，即可填写章总结。</p>'}
        ${renderChapterReviews(ch, readOnly)}
      </div>`;
    }).join('')}
    ${data.chapter_index_markdown ? `<details class="details"><summary>查看全书章节摘要索引（Markdown）</summary><pre class="raw-data">${esc(data.chapter_index_markdown)}</pre></details>` : ''}
  </section>`;
}

function renderPromisesSection(promises) {
  const items = promises?.items || [];
  const counts = promises?.lifecycle_counts || {};
  const overdue = promises?.overdue || [];
  const due = promises?.due || [];
  return `<section id="promiseContinuityPanel" style="margin-bottom:24px">
    <div class="row spread wrap" style="margin-bottom:10px">
      <h3 style="margin:0">伏笔与读者承诺连续性</h3>
      <div class="row wrap" style="gap:6px">
        <span class="tag">未核实 ${number(counts.unverified || 0)}</span>
        <span class="tag blue">已埋设 ${number(counts.planted || 0)}</span>
        <span class="tag amber">已暗示 ${number(counts.hinted || 0)}</span>
        <span class="tag green">已回收 ${number(counts.paid_off || 0)}</span>
      </div>
    </div>
    ${overdue.length ? `<div class="notice warning" style="margin-bottom:12px"><strong>超期未回收告警（${overdue.length}）：</strong>${overdue.map(o => `${esc(o.title)}（${esc(o.reason)}）`).join('；')}</div>` : ''}
    ${due.length ? `<div class="notice" style="margin-bottom:12px"><strong>当前到期兑现提醒（${due.length}）：</strong>${due.map(d => esc(d.title)).join('、')}</div>` : ''}
    ${items.length ? `<div class="table-wrap"><table class="data-table">
      <thead><tr><th>伏笔 / 承诺</th><th>当前状态</th><th>实际埋设章</th><th>计划回收窗口</th></tr></thead>
      <tbody>${items.map(p => {
        const sch = p.schedule || {};
        const windowText = sch.payoff_chapter ? `第 ${sch.payoff_chapter} 章`
          : sch.payoff_window ? `埋设后 ${sch.payoff_window.min_offset}–${sch.payoff_window.max_offset} 章` : '未指定';
        const cls = p.accepted_stage === 'paid_off' ? 'green' : p.accepted_stage ? 'blue' : '';
        return `<tr>
          <td><strong>${esc(p.title)}</strong><div class="muted" style="font-size:11px">${esc(p.card_id)} v${p.version}</div></td>
          <td><span class="tag ${cls}">${esc(promiseStageLabels[p.accepted_stage || 'unverified'] || p.accepted_stage)}</span></td>
          <td>${p.planted_chapter ? `第 ${p.planted_chapter} 章` : '—'}</td>
          <td>${esc(windowText)}</td>
        </tr>`;
      }).join('')}</tbody></table></div>`
      : `<p class="muted" style="font-size:13px">${esc(promises?.rule || '当前分支尚无已批准的伏笔承诺卡。')}</p>`}
  </section>`;
}

function renderKnowledgeMatrixSection(matrixData) {
  const holders = matrixData?.holders || [];
  const rows = matrixData?.matrix || [];
  return `<section id="knowledgeMatrixPanel" style="margin-bottom:24px">
    <div class="row spread wrap" style="margin-bottom:10px">
      <h3 style="margin:0">多主体知情矩阵（WORLD / READER / 人物认知差）</h3>
      <span class="muted" style="font-size:12px">${holders.length} 个主体 · ${rows.length} 条状态命题</span>
    </div>
    ${rows.length ? `<div class="table-wrap"><table class="data-table">
      <thead><tr><th>实体 · 属性</th>${holders.map(h => `<th>${esc(h === 'WORLD' ? '客观世界(WORLD)' : h === 'READER' ? '读者已知(READER)' : h)}</th>`).join('')}</tr></thead>
      <tbody>${rows.map(row => `<tr>
        <td><strong>${esc(row.entity_id)}</strong>.${esc(row.predicate)}</td>
        ${holders.map(h => {
          const vals = row.cells?.[h] || [];
          if (!vals.length) return '<td class="muted">—</td>';
          return `<td>${vals.map(v => `<div><span class="tag ${v.claim === 'fact' ? 'blue' : 'amber'}" style="font-size:10px">${esc(claimLabels[v.claim] || v.claim)}</span> ${esc(fmtVal(v.value))}</div>`).join('')}</td>`;
        }).join('')}
      </tr>`).join('')}</tbody></table></div>`
      : '<p class="muted" style="font-size:13px">接受包含状态增量的场景正文后，此处将横向对比世界真相、读者所知与各角色的认知差异，防止视角泄密与真相混写。</p>'}
  </section>`;
}

export function renderFinishReadinessBlock(finishData, {buttonId = 'confirmFinishBook'} = {}) {
  const checks = finishData?.checks || [];
  const advisories = finishData?.advisories || [];
  const summary = finishData?.summary || {};
  const isDone = finishData?.novel_status === 'done';
  return `<div id="finishReadinessPanel">
    <div class="row spread wrap" style="margin-bottom:12px">
      <div class="row wrap" style="gap:8px">
        <span class="tag ${finishData?.ready || isDone ? 'green' : 'amber'}">${isDone ? '作品已完稿' : finishData?.ready ? '全部 9 项强门禁通过，可完稿' : `已通过 ${summary.passed_count || 0}/${summary.total_checks || checks.length} 项强门禁`}</span>
        <span class="muted" style="font-size:12px">已接受 ${number(summary.accepted_words || 0)} 字 · ${number(summary.accepted_scenes || 0)}/${number(summary.total_active_scenes || 0)} 场</span>
      </div>
    </div>
    <div class="stack" style="gap:8px">
      ${checks.map(c => `<div class="review-item" style="display:flex;gap:10px;align-items:flex-start">
        <span class="tag ${c.passed ? 'green' : ''}" style="${c.passed ? '' : 'color:var(--danger)'}">${c.passed ? '通过' : '阻断'}</span>
        <div class="grow">
          <strong style="font-size:13px">${esc(c.title)}</strong>
          <p class="muted" style="margin:3px 0 0;font-size:12px">${esc(c.detail)}</p>
        </div>
      </div>`).join('')}
    </div>
    ${advisories.length ? `<div class="notice" style="margin-top:14px">
      <strong>完稿前复盘建议（不阻断完稿）：</strong>
      <ul style="margin:6px 0 0 18px;padding:0;font-size:12px">${advisories.map(a => `<li><strong>${esc(a.title)}：</strong>${esc(a.detail)}</li>`).join('')}</ul>
    </div>` : ''}
    ${!isDone ? `<div class="row" style="margin-top:16px">
      <button class="button" id="${esc(buttonId)}" ${finishData?.ready ? '' : 'disabled'}>${icon('check')} 确认标记为完稿并导出全书</button>
    </div>` : ''}
  </div>`;
}

export function renderFinishDrawerHtml(finishData) {
  return `<div id="finishReadinessDrawer">
    <p class="muted" style="margin-top:0">完稿操作会核验全部 9 项强门禁，并在通过后将正式主线正文导出至项目成品目录。</p>
    ${renderFinishReadinessBlock(finishData, {buttonId: 'confirmFinishBook'})}
  </div>`;
}

export function renderContinuationHub(host, novel, data, finishData, {onReload, onFinish}) {
  if (!data?.managed_story) {
    const actionBtn = novel.status !== 'done'
      ? '<button class="button" type="button" id="adoptStoryBtn">立即接管故事状态机（Story Adopt）</button>'
      : '';
    host.innerHTML = `<div id="bookContinuationHub">${empty('尚未接入故事状态机', '完成 story adopt 接管故事状态后，可在此管理章总结、周期复盘、伏笔追踪、多主体知情矩阵与完稿体检。', actionBtn, 'layers')}</div>`;
    host.querySelector('#adoptStoryBtn')?.addEventListener('click', e => busy(e.currentTarget, async () => {
      await api.post(`/projects/${enc(novel.project_dir)}/adopt`, {include_approved_cards: true});
      toast('已接管故事状态机（main 分支初始化完成）');
      await onReload();
    }).catch(fail));
    return;
  }
  const readOnly = novel.status === 'done';
  host.innerHTML = `<div id="bookContinuationHub">
    ${renderBranchBar(novel, data.branch_guidance)}
    ${renderChaptersSection(data, readOnly)}
    ${renderPromisesSection(data.promises)}
    ${renderKnowledgeMatrixSection(data.knowledge_matrix)}
    <section class="card" style="margin-bottom:24px">
      <h3 style="margin-top:0">完稿前全量体检</h3>
      ${renderFinishReadinessBlock(finishData, {buttonId: 'triggerFinishFromHub'})}
    </section>
  </div>`;

  $$('[data-summary-form]', host).forEach(form => {
    form.onsubmit = event => {
      event.preventDefault();
      const ch = Number(form.dataset.chapter);
      const summary = form.querySelector('[name="summary"]').value.trim();
      const comparisonEl = form.querySelector('[name="comparison"]');
      const body = {summary, input_sha256: form.dataset.sha || undefined};
      if (comparisonEl && comparisonEl.value.trim()) body.comparison = comparisonEl.value.trim();
      busy(form.querySelector('[type="submit"]'), async () => {
        await api.post(`/novels/${enc(novel.id)}/chapters/${ch}/summary`, body);
        toast(`第 ${ch} 章章总结已保存，将自动注入下一章设计`);
        await onReload();
      }).catch(fail);
    };
  });

  $$('[data-review-form]', host).forEach(form => {
    form.onsubmit = event => {
      event.preventDefault();
      const ch = Number(form.dataset.chapter);
      const kind = form.dataset.kind;
      const finding = form.querySelector('[name="finding"]').value.trim();
      busy(form.querySelector('[type="submit"]'), async () => {
        await api.post(`/novels/${enc(novel.id)}/chapters/${ch}/reviews/${enc(kind)}`, {
          finding,
          input_sha256: form.dataset.sha || undefined,
        });
        toast(`第 ${ch} 章阶段复盘已留档`);
        await onReload();
      }).catch(fail);
    };
  });

  host.querySelector('#triggerFinishFromHub')?.addEventListener('click', () => onFinish());
}
