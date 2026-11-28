import {api, enc, query} from '../api.js';
import {$, $$, esc, drawer, modal, toast, fail, busy, loading, number} from '../ui.js';

const STATUS_BADGE = {
  healthy: ['green', '状态健康'],
  watch: ['amber', '建议关注'],
  alert: ['danger', '存在节奏债'],
  ok: ['green', '通过'],
  warning: ['amber', '提醒'],
  error: ['danger', '需处理'],
  attention: ['amber', '需留意'],
  blocked: ['danger', '存在阻断'],
};

function badge(status, fallback = '') {
  const [cls, text] = STATUS_BADGE[status] || ['', fallback || status || '—'];
  const style = cls === 'danger' ? 'style="color:var(--danger);border-color:var(--danger)"' : '';
  return `<span class="tag ${cls === 'danger' ? '' : cls}" ${style}>${esc(text)}</span>`;
}

export function openSoftOverrideModal(novelId, item, {sceneId = '', draftId = '', chapterIndex = null, rationaleTags = {}, onSaved = null} = {}) {
  const tags = Object.entries(rationaleTags || {});
  const optionsHtml = (tags.length ? tags : [
    ['TRANSITIONAL_SETUP', {label: '铺垫与过渡需要'}],
    ['CHARACTER_CREDIBILITY', {label: '人物可信度优先'}],
    ['LOGIC_INTEGRITY', {label: '逻辑与悬疑公平性优先'}],
    ['ARC_TIMING', {label: '长线大回收蓄力窗口'}],
    ['EDITORIAL_INTENT', {label: '作者主观品味与艺术意图'}],
  ]).map(([k, v]) => `<option value="${esc(k)}">${esc(v.label || k)}</option>`).join('');

  const dlg = modal(
    '登记软约束显式豁免',
    `<form id="softOverrideForm" class="stack" style="gap:12px">
      <div class="notice"><strong>${esc(item.title || item.constraint_code || '软建议项')}</strong><p class="muted" style="margin:4px 0 0;font-size:12px">仅软建议支持显式豁免；事实、时间线与 POV 视角泄密硬红线永远禁止豁免。同类豁免累计 3 次将自动提议固化进本书工艺基座。</p></div>
      <label class="field"><span>豁免理由分类</span><select name="reason_tag" required>${optionsHtml}</select></label>
      <label class="field"><span>具体原因说明（必填）</span><textarea name="reason_text" rows="3" required placeholder="例如：本章刻意放缓收束前文大战余波，下章转入新冲突"></textarea></label>
    </form>`,
    `<button type="button" class="secondary" data-close-modal>取消</button><button type="button" class="button" id="submitSoftOverride">确认登记豁免</button>`,
  );
  $('#submitSoftOverride').onclick = e => busy(e.currentTarget, async () => {
    const form = $('#softOverrideForm');
    const reason_tag = form.querySelector('[name=reason_tag]').value;
    const reason_text = form.querySelector('[name=reason_text]').value.trim();
    if (!reason_text) {
      toast('请填写具体的豁免原因说明', true);
      return;
    }
    await api.post(`/novels/${enc(novelId)}/overrides`, {
      constraint_kind: item.lens === 'script_gate' ? 'voice_soft' : 'soft_gate',
      constraint_code: item.constraint_code || 'SOFT_GATE',
      reason_tag,
      reason_text,
      scene_id: sceneId || null,
      draft_id: draftId || null,
      chapter_index: chapterIndex,
      details: {lens: item.lens || '', title: item.title || ''},
    });
    dlg.close();
    toast('已登记显式豁免，该软提醒不再阻断当前场景');
    if (onSaved) await onSaved();
  });
}

export async function openSerialHealthDrawer(novelId, {onChanged = null} = {}) {
  drawer('连载盘面 · 节奏债与卷级长程记忆', loading());
  try {
    const data = await api.get(`/novels/${enc(novelId)}/serial-health`);
    const b = data.board || {};
    const sh = b.strand_health || {};
    const hh = b.hook_health || {};
    const pd = b.promise_debt || {};
    const crt = b.cold_read_trend || {};
    const prof = b.strand_profile || {};
    const vols = data.volume_summaries || [];
    const opp = data.foreshadowing_opportunities || {};

    $('#drawerBody').innerHTML = `<div class="stack" style="gap:16px">
      <div class="card stack" style="gap:8px">
        <div class="row spread wrap">
          <strong>当前连载健康盘面（分支 ${esc(data.branch_id || 'main')}）</strong>
          <div class="row" style="gap:6px">${badge(b.status)}<span class="tag">节奏债分 ${number(b.rhythm_debt_score || 0)}</span><span class="tag blue">已追踪 ${number(b.chapters_tracked || 0)} 章</span></div>
        </div>
        <p class="muted" style="margin:0;font-size:12px">适配剧情基座：${esc(prof.base_id || '默认')}（篇幅档位：${esc(prof.tier_id || 'medium')}）· ${esc(prof.strand_notes || '')}</p>
        ${(b.next_chapter_corrections || []).length
          ? `<div class="notice warning" style="margin:0"><strong>自动注入下一章策划的纠偏提醒：</strong><ul style="margin:6px 0 0 18px;font-size:12px">${b.next_chapter_corrections.map(c => `<li>${esc(c)}</li>`).join('')}</ul></div>`
          : '<div class="notice" style="margin:0;font-size:12px">当前三线配比、章尾钩子与承诺兑现均健康，可直接推进下一章。</div>'}
      </div>

      <div class="card stack" style="gap:8px">
        <strong>三线编织（Strand Weave）与钩子多样性</strong>
        <div class="row wrap" style="gap:6px">
          <span class="tag">主线 Quest：${number(sh.counts?.quest || 0)} 章（连跑 ${number(sh.quest_streak || 0)}/${number(prof.max_quest_streak || 5)}）</span>
          <span class="tag">情感 Fire：${number(sh.counts?.fire || 0)} 章（距上次 ${number(sh.chapters_since_fire || 0)} 章）</span>
          <span class="tag">格局 Constellation：${number(sh.counts?.constellation || 0)} 章（距上次 ${number(sh.chapters_since_constellation || 0)} 章）</span>
          <span class="tag ${hh.weak_streak >= 3 ? 'amber' : ''}">连续弱钩：${number(hh.weak_streak || 0)} 章</span>
          ${crt.count ? `<span class="tag blue">盲态冷读追读率：${crt.want_next_yes_ratio != null ? Math.round(crt.want_next_yes_ratio * 100) + '%' : '待统计'}（${crt.count} 次）</span>` : ''}
        </div>
      </div>

      <div class="card stack" style="gap:8px">
        <div class="row spread"><strong>承诺节奏债（逾期 ${(pd.overdue || []).length} · 停滞 ${(pd.stalled || []).length}）</strong><span class="muted" style="font-size:12px">到期 ${(pd.due || []).length} 项</span></div>
        ${(pd.overdue || []).concat(pd.stalled || []).slice(0, 6).map(item => `<div class="review-item"><div class="row spread"><strong>${esc(item.title || item.promise)}</strong><span class="tag amber">${item.stalled_chapters ? `停滞 ${item.stalled_chapters} 章` : '已超期'}</span></div><p class="muted" style="margin:4px 0 0;font-size:12px">${esc(item.reason || '')}</p></div>`).join('') || '<p class="muted" style="margin:0;font-size:12px">暂无逾期或停滞承诺债。</p>'}
      </div>

      ${opp.ready ? `<div class="card stack" style="gap:6px"><strong>卷末远期伏笔机会锚点（${(opp.future_anchors || []).length} 个远期节点）</strong><p class="muted" style="margin:0;font-size:12px">下次发起「新卷设计」时，系统会自动把以下远期节点喂给策划，提议 3–5 条本卷可顺手埋设的长线伏笔：</p><ul style="margin:0 0 0 18px;font-size:12px">${opp.future_anchors.map(a => `<li><strong>${esc(a.title)}</strong>：${esc(a.anchor)}</li>`).join('')}</ul></div>` : ''}

      <div class="card stack" style="gap:10px">
        <div class="row spread"><strong>卷级压缩摘要（L2 情节记忆 · 已存 ${vols.length} 卷）</strong></div>
        ${vols.map(v => `<div class="review-item"><div class="row spread"><strong>第${v.volume_index}卷《${esc(v.title)}》</strong><span class="muted" style="font-size:11px">第 ${v.chapter_start}–${v.chapter_end} 章</span></div><p style="margin:6px 0 0;font-size:12px;white-space:pre-wrap">${esc(v.summary_text)}</p></div>`).join('') || '<p class="muted" style="margin:0;font-size:12px">完结一卷后保存 500 字内卷级摘要，写到第 100–500 章也能精准召回前卷脉络。</p>'}
        <form id="volumeSummaryForm" class="stack" style="gap:8px;border-top:1px solid var(--border);padding-top:10px">
          <strong style="font-size:12px">新增 / 更新卷级摘要</strong>
          <div class="form-grid">
            <label class="field"><span>卷号</span><input type="number" name="volume_index" min="1" value="${vols.length + 1}" required></label>
            <label class="field"><span>卷名</span><input name="title" value="第${vols.length + 1}卷" required></label>
            <label class="field"><span>起始章</span><input type="number" name="chapter_start" min="1" value="1" required></label>
            <label class="field"><span>结束章</span><input type="number" name="chapter_end" min="1" value="${Math.max(1, b.latest_chapter || 1)}" required></label>
          </div>
          <label class="field"><span>卷摘要（建议 500 字以内：主线推进、关系定格、跨卷未回收伏笔）</span><textarea name="summary_text" rows="3" required placeholder="点下方「按章摘要自动起草」或手动填写本卷核心脉络"></textarea></label>
          <div class="row wrap" style="gap:8px">
            <button type="button" class="secondary" id="draftVolSummaryBtn">按章摘要自动起草</button>
            <button type="submit" class="button">保存卷级摘要</button>
          </div>
        </form>
      </div>
    </div>`;

    $('#draftVolSummaryBtn')?.addEventListener('click', e => busy(e.currentTarget, async () => {
      const f = $('#volumeSummaryForm');
      const res = await api.post(`/novels/${enc(novelId)}/volume-summaries`, {
        mode: 'draft',
        volume_index: Number(f.querySelector('[name=volume_index]').value || 1),
        title: f.querySelector('[name=title]').value.trim(),
        chapter_start: Number(f.querySelector('[name=chapter_start]').value || 1),
        chapter_end: Number(f.querySelector('[name=chapter_end]').value || 1),
      });
      f.querySelector('[name=summary_text]').value = res.suggested_summary || '';
      toast(`已汇总 ${res.chapter_summaries_used || 0} 章摘要生成草稿，可修改后保存`);
    }));
    $('#volumeSummaryForm')?.addEventListener('submit', e => {
      e.preventDefault();
      const f = e.currentTarget;
      busy(f.querySelector('[type=submit]'), async () => {
        await api.post(`/novels/${enc(novelId)}/volume-summaries`, {
          volume_index: Number(f.querySelector('[name=volume_index]').value || 1),
          title: f.querySelector('[name=title]').value.trim(),
          chapter_start: Number(f.querySelector('[name=chapter_start]').value || 1),
          chapter_end: Number(f.querySelector('[name=chapter_end]').value || 1),
          summary_text: f.querySelector('[name=summary_text]').value.trim(),
        });
        toast('卷级摘要已保存并接入 L2 情节记忆');
        if (onChanged) await onChanged();
        await openSerialHealthDrawer(novelId, {onChanged});
      });
    });
  } catch (err) {
    fail(err);
  }
}

export async function openCraftEvolutionDrawer(novelId, {sceneId = '', onChanged = null} = {}) {
  drawer('四维基座 · 第 5 层活体自演化与文体漂移体检', loading());
  try {
    const data = await api.get(`/novels/${enc(novelId)}/craft-evolution?${query({scene: sceneId})}`);
    const drift = data.style_drift || {};
    const proposals = data.promotion_proposals || [];
    const pending = data.pending_author_edit_contrasts || [];
    const learned = data.learned_contrasts || [];
    const redlinesByDom = data.learned_redlines_by_domain || {};
    const domNames = {world: '世界基座', cast: '人物基座', plot_pacing: '剧情节奏基座', voice: '语感基座'};

    $('#drawerBody').innerHTML = `<div class="stack" style="gap:16px">
      <div class="card stack" style="gap:8px">
        <div class="row spread wrap">
          <strong>周期性文体指纹漂移监测</strong>
          ${badge(drift.status === 'drift_detected' ? 'warning' : 'ok', drift.status === 'drift_detected' ? '检测到漂移' : '指纹稳定')}
        </div>
        <p style="margin:0;font-size:12px">${esc(drift.summary || '')}</p>
        ${(drift.drifts || []).length ? `<div class="notice warning" style="margin:0;font-size:12px">${drift.drifts.map(d => `<div>• ${esc(d.message)}</div>`).join('')}</div>` : ''}
        <form id="pinBaselineForm" class="row wrap" style="gap:8px;align-items:flex-end;margin-top:4px">
          <label class="field" style="width:90px"><span>基线起始章</span><input type="number" name="start_chapter" min="1" value="${drift.baseline?.range_start || 1}"></label>
          <label class="field" style="width:90px"><span>基线结束章</span><input type="number" name="end_chapter" min="1" value="${drift.baseline?.range_end || 10}"></label>
          <button type="submit" class="secondary">锁定/更新本书文体基线</button>
        </form>
      </div>

      <div class="card stack" style="gap:8px">
        <strong>待确认：作者亲改 Diff 语感微对照（${pending.length}）</strong>
        ${pending.length ? pending.map((c, idx) => `<div class="review-item stack" style="gap:6px">
          <div class="row spread"><strong>${esc(c.label)}</strong><span class="tag blue">改写度 ${Math.round((c.change_ratio || 0) * 100)}%</span></div>
          <p class="muted" style="margin:0;font-size:12px">❌ AI 原稿：${esc(c.bad_ai)}</p>
          <p style="margin:0;font-size:12px">✅ 作者亲改：${esc(c.target_voice)}</p>
          <p class="muted" style="margin:0;font-size:11px">💡 ${esc(c.why || '')}</p>
          <div><button type="button" class="button" data-accept-evo-contrast="${idx}">确认收录进本书语感基座</button></div>
        </div>`).join('') : '<p class="muted" style="margin:0;font-size:12px">当你在正文页手动润色 AI 草稿（改幅 25%–72%）后，系统会自动提炼正反对照供你一键收录。</p>'}
      </div>

      <div class="card stack" style="gap:8px">
        <strong>高频校准 → 升格为本书红线提案（${proposals.length}）</strong>
        ${proposals.length ? proposals.map((p, idx) => `<div class="review-item stack" style="gap:6px">
          <div class="row spread"><strong>${esc(domNames[p.target_domain] || p.target_domain)} · 累计 ${p.count} 次</strong><span class="tag amber">${esc(p.reason_label || p.reason_tag)}</span></div>
          <p style="margin:0;font-size:12px">${esc(p.proposed_redline)}</p>
          <div><button type="button" class="button" data-promote-evo-rule="${idx}">一键升格固化为本书红线</button></div>
        </div>`).join('') : '<p class="muted" style="margin:0;font-size:12px">同一类软豁免或审稿打回累计满 3 次时，会自动出现在此处提议固化为规则。</p>'}
      </div>

      <div class="card stack" style="gap:8px">
        <strong>已收录的作者亲改活体微对照（${learned.length}，优先替换通用样板）</strong>
        ${learned.map(c => `<div class="review-item stack" style="gap:4px">
          <div class="row spread"><strong>${esc(c.label)}</strong><button type="button" class="ghost" data-remove-evo-contrast="${esc(c.id)}">移除</button></div>
          <p class="muted" style="margin:0;font-size:12px">❌ ${esc(c.bad_ai)}</p>
          <p style="margin:0;font-size:12px">✅ ${esc(c.target_voice)}</p>
        </div>`).join('') || '<p class="muted" style="margin:0;font-size:12px">尚未收录作者亲改微对照。</p>'}
      </div>

      <div class="card stack" style="gap:6px">
        <strong>已升格的活体工艺红线</strong>
        ${Object.entries(redlinesByDom).map(([dom, list]) => (list || []).length ? `<div><strong style="font-size:12px">${esc(domNames[dom] || dom)}：</strong><ul style="margin:4px 0 0 18px;font-size:12px">${list.map(r => `<li>${esc(r.rule)}</li>`).join('')}</ul></div>` : '').join('') || '<p class="muted" style="margin:0;font-size:12px">尚未从否决/豁免中升格红线。</p>'}
      </div>
    </div>`;

    $('#pinBaselineForm')?.addEventListener('submit', e => {
      e.preventDefault();
      const f = e.currentTarget;
      busy(f.querySelector('[type=submit]'), async () => {
        await api.post(`/novels/${enc(novelId)}/craft-evolution/pin-baseline`, {
          start_chapter: Number(f.querySelector('[name=start_chapter]').value || 1),
          end_chapter: Number(f.querySelector('[name=end_chapter]').value || 10),
        });
        toast('已锁定本书文体基线');
        await openCraftEvolutionDrawer(novelId, {sceneId, onChanged});
      });
    });
    $$('[data-accept-evo-contrast]').forEach(btn => {
      btn.onclick = e => busy(e.currentTarget, async () => {
        const cand = pending[Number(btn.dataset.acceptEvoContrast)];
        await api.post(`/novels/${enc(novelId)}/craft-evolution/accept-contrast`, cand);
        toast('已收录进本书语感基座，后续同类场景将优先参照你的亲改示范');
        if (onChanged) await onChanged();
        await openCraftEvolutionDrawer(novelId, {sceneId, onChanged});
      });
    });
    $$('[data-promote-evo-rule]').forEach(btn => {
      btn.onclick = e => busy(e.currentTarget, async () => {
        const prop = proposals[Number(btn.dataset.promoteEvoRule)];
        await api.post(`/novels/${enc(novelId)}/craft-evolution/promote`, prop);
        toast('已升格固化为本书防漂移红线');
        if (onChanged) await onChanged();
        await openCraftEvolutionDrawer(novelId, {sceneId, onChanged});
      });
    });
    $$('[data-remove-evo-contrast]').forEach(btn => {
      btn.onclick = e => busy(e.currentTarget, async () => {
        await api.post(`/novels/${enc(novelId)}/craft-evolution/remove-contrast`, {contrast_id: btn.dataset.removeEvoContrast});
        toast('已移除该条活体微对照');
        if (onChanged) await onChanged();
        await openCraftEvolutionDrawer(novelId, {sceneId, onChanged});
      });
    });
  } catch (err) {
    fail(err);
  }
}

export async function openProjectDoctorDrawer(novelId, {repairCache = false} = {}) {
  drawer('一键项目健康体检（Project Doctor）', loading());
  try {
    const data = await api.get(`/novels/${enc(novelId)}/doctor?${query({repair_cache: repairCache ? '1' : ''})}`);
    $('#drawerBody').innerHTML = `<div class="stack" style="gap:14px">
      <div class="card stack" style="gap:8px">
        <div class="row spread wrap">
          <strong>健康总分：${number(data.score || 0)} / 100</strong>
          <div class="row" style="gap:6px">${badge(data.overall_status)}<button type="button" class="secondary" id="doctorRebuildCache">清理并重建派生缓存</button></div>
        </div>
        <p style="margin:0;font-size:12px">${esc(data.summary || '')}</p>
        ${data.cache_cleared ? `<p class="muted" style="margin:0;font-size:11px">本次已清理 ${data.cache_cleared} 条旧状态重放缓存，下次读取将从 SQLite 真源自动重建。</p>` : ''}
      </div>
      <div class="stack" style="gap:8px">
        ${(data.checks || []).map(c => `<div class="review-item">
          <div class="row spread"><strong>${esc(c.category)} · ${esc(c.title)}</strong>${badge(c.status)}</div>
          <p class="muted" style="margin:4px 0 0;font-size:12px">${esc(c.detail || '')}</p>
          ${c.repair_hint ? `<p style="margin:4px 0 0;font-size:12px"><strong>建议动作：</strong>${esc(c.repair_hint)}</p>` : ''}
        </div>`).join('')}
      </div>
    </div>`;
    $('#doctorRebuildCache')?.addEventListener('click', e => busy(e.currentTarget, async () => {
      await openProjectDoctorDrawer(novelId, {repairCache: true});
      toast('已完成缓存清理与重新体检');
    }));
  } catch (err) {
    fail(err);
  }
}

export async function openSceneBriefingDrawer(novelId, sceneId) {
  drawer('0-Token 自然语境写前任务书预览', loading());
  try {
    const data = await api.get(`/novels/${enc(novelId)}/briefing?${query({scene: sceneId})}`);
    $('#drawerBody').innerHTML = `<div class="stack" style="gap:12px">
      <div class="notice" style="margin:0;font-size:12px">真实写作模型收到的就是下方这份零 JSON 噪音的 5 段式中文任务书（${number(data.briefing_chars || 0)} 字符，0 额外 LLM 调用）；后台审计清单仍完整冻结原始设定卡片与 SHA256。</div>
      <pre class="raw-data" style="white-space:pre-wrap;line-height:1.7;font-family:var(--font-sans)">${esc(data.briefing_text || '')}</pre>
    </div>`;
  } catch (err) {
    fail(err);
  }
}

export async function openForecastSandboxDrawer(novelId, {onChanged = null} = {}) {
  drawer('剧情多分支沙盘推演（非正史零污染）', loading());
  try {
    const data = await api.get(`/novels/${enc(novelId)}/forecasts`);
    const list = data.forecasts || [];
    const activeConstraint = data.active_constraint || null;
    const statusLabel = s => ({active: '有效', stale: '已过期（正史推进）', adopted: '已采纳为规划约束', forked: '已孵化为候选分支'}[s] || s);

    $('#drawerBody').innerHTML = `<div class="stack" style="gap:16px">
      <div class="notice" style="margin:0;font-size:12px">
        在关键卷/章转折点动笔前，一次性推演 2–5 条互不干扰的未来走势（含人物抉择、伏笔/关系连锁变化与风险预警）。推演绝不改写正史；正史推进后旧推演自动标为「已过期」。
      </div>
      ${activeConstraint ? `<div class="card stack" style="gap:6px;border-color:var(--accent)">
        <div class="row spread"><strong>当前生效的沙盘规划约束：${esc(activeConstraint.label || activeConstraint.branch_id)}</strong><span class="tag green">已接入下轮策划</span></div>
        <p style="margin:0;font-size:12px">${esc(activeConstraint.premise || '')}</p>
      </div>` : ''}
      <form id="createForecastForm" class="card stack" style="gap:10px">
        <strong>发起新一轮剧情沙盘推演</strong>
        <label class="field"><span>关键剧情分歧点（必填）</span><textarea name="divergence" rows="2" required placeholder="例如：第28章拍卖会结束，长老当众逼宫交出古玉，主角如何应对？"></textarea></label>
        <div class="form-grid">
          <label class="field"><span>分支数（2–5）</span><input type="number" name="branch_count" min="2" max="5" value="3"></label>
          <label class="field"><span>前瞻步长（章）</span><input type="number" name="horizon" min="1" max="10" value="5"></label>
        </div>
        <div class="row wrap" style="gap:8px">
          <button type="submit" class="button" data-fc-mode="model">模型深度推演</button>
          <button type="button" class="secondary" id="offlineForecastBtn">0-Token 离线战略沙盘预览</button>
        </div>
      </form>
      <div class="stack" style="gap:12px">
        ${list.length ? list.map(fc => `<div class="card stack" style="gap:10px">
          <div class="row spread wrap">
            <strong>分歧点：${esc(fc.divergence)}</strong>
            <div class="row" style="gap:6px">
              <span class="tag ${fc.stale ? 'amber' : (fc.status === 'adopted' || fc.status === 'forked' ? 'green' : 'blue')}">${esc(statusLabel(fc.status))}</span>
              <span class="tag">基准第 ${number(fc.base_chapter || 0)} 章 · 前瞻 ${number(fc.horizon || 5)} 章</span>
            </div>
          </div>
          <div class="stack" style="gap:8px">
            ${(fc.branches || []).map(br => `<div class="review-item stack" style="gap:6px">
              <div class="row spread wrap">
                <strong>${esc(br.label || br.branch_id)}</strong>
                ${fc.selected_branch_id === br.branch_id ? '<span class="tag green">已选分支</span>' : ''}
              </div>
              <p style="margin:0;font-size:12px">${esc(br.premise || '')}</p>
              ${(br.beats || []).length ? `<ul style="margin:0 0 0 18px;font-size:12px">${br.beats.slice(0, 5).map(bt => `<li>第${bt.chapter}章（${esc(bt.dominant_strand || 'quest')}）：${esc(bt.summary || '')}</li>`).join('')}</ul>` : ''}
              ${(br.risks || []).length ? `<p class="muted" style="margin:0;font-size:11px">⚠ 风险预警：${esc(br.risks.join('；'))}</p>` : ''}
              <div class="row wrap" style="gap:8px">
                <button type="button" class="secondary" data-fc-adopt="${esc(fc.id)}" data-fc-branch="${esc(br.branch_id)}">采纳为下章策划约束</button>
                <button type="button" class="ghost" data-fc-fork="${esc(fc.id)}" data-fc-branch="${esc(br.branch_id)}">一键孵化为真实候选分支</button>
              </div>
            </div>`).join('')}
          </div>
        </div>`).join('') : '<p class="muted" style="margin:0;font-size:12px">尚未发起剧情沙盘推演。</p>'}
      </div>
    </div>`;

    const submitForecast = (offline, btn) => busy(btn, async () => {
      const f = $('#createForecastForm');
      const divergence = f.querySelector('[name=divergence]').value.trim();
      if (!divergence) { toast('请填写剧情分歧点', true); return; }
      await api.post(`/novels/${enc(novelId)}/forecasts`, {
        divergence,
        branch_count: Number(f.querySelector('[name=branch_count]').value || 3),
        horizon: Number(f.querySelector('[name=horizon]').value || 5),
        offline_preview: offline,
      });
      toast(offline ? '已生成 0-Token 离线沙盘对比方案' : '已完成多分支剧情沙盘推演');
      await openForecastSandboxDrawer(novelId, {onChanged});
    });
    $('#createForecastForm')?.addEventListener('submit', e => {
      e.preventDefault();
      submitForecast(false, e.currentTarget.querySelector('[type=submit]'));
    });
    $('#offlineForecastBtn')?.addEventListener('click', e => submitForecast(true, e.currentTarget));
    $$('[data-fc-adopt]').forEach(btn => {
      btn.onclick = e => busy(e.currentTarget, async () => {
        await api.post(`/novels/${enc(novelId)}/forecasts/${enc(btn.dataset.fcAdopt)}/select`, {
          branch_choice_id: btn.dataset.fcBranch,
          mode: 'adopt_constraint',
        });
        toast('已采纳为下几章规划约束（正史零污染）');
        if (onChanged) await onChanged();
        await openForecastSandboxDrawer(novelId, {onChanged});
      });
    });
    $$('[data-fc-fork]').forEach(btn => {
      btn.onclick = e => busy(e.currentTarget, async () => {
        const res = await api.post(`/novels/${enc(novelId)}/forecasts/${enc(btn.dataset.fcFork)}/select`, {
          branch_choice_id: btn.dataset.fcBranch,
          mode: 'fork_branch',
        });
        toast(`已孵化真实候选分支：${res.forecast?.forked_branch_id || '已创建'}`);
        if (onChanged) await onChanged();
        await openForecastSandboxDrawer(novelId, {onChanged});
      });
    });
  } catch (err) {
    fail(err);
  }
}

export async function openSemanticDeslopDrawer(novelId, sceneId, {onChanged = null} = {}) {
  drawer('事实冻结型 · 语义去 AI 味精修（Deslop）', loading());
  try {
    const data = await api.get(`/novels/${enc(novelId)}/deslop?${query({scene: sceneId})}`);
    const analysis = data.analysis || {};
    const flagged = analysis.flagged_paragraphs || [];
    $('#drawerBody').innerHTML = `<div class="stack" style="gap:14px">
      <div class="notice" style="margin:0;font-size:12px">
        只针对命中的局部段落执行宿主锁界 Spot-Fix 语义润色：<strong>未选中段落字节级零篡改，人物姓名、剧情因果与 POV 披露边界严格冻结</strong>，并自动注入本书活体语感基座与作者亲改微对照。
      </div>
      <div class="card stack" style="gap:8px">
        <div class="row spread wrap">
          <strong>0-Token 功能性 AI 味扫描结果</strong>
          <span class="tag ${flagged.length ? 'amber' : 'green'}">${flagged.length ? `命中 ${flagged.length} 段 / ${analysis.total_slop_hits || 0} 处` : '未检出明显 AI 味'}</span>
        </div>
        ${flagged.length ? flagged.map(p => `<div class="review-item stack" style="gap:4px">
          <div class="row spread"><strong>段落 P${p.paragraph}（风险分 ${p.score}）</strong><span class="tag amber">${p.hit_count} 处</span></div>
          <p class="muted" style="margin:0;font-size:11px">${esc((p.hits || []).map(h => h.label).join('；'))}</p>
          <p style="margin:0;font-size:12px">${esc(p.preview || '')}</p>
        </div>`).join('') : '<p class="muted" style="margin:0;font-size:12px">当前草稿整体语感干净；如需手动指定段落润色，可在下方输入 0 基段落号。</p>'}
      </div>
      <form id="deslopForm" class="card stack" style="gap:10px">
        <label class="field"><span>目标段落号（留空则自动选中上方最高风险段落，逗号分隔如 2,5）</span><input name="paragraphs" value="${esc((analysis.recommended_target_paragraphs || []).join(','))}"></label>
        <label class="field"><span>补充润色意图（可选）</span><input name="extra_instruction" placeholder="例如：把情绪解释删掉，改用冷硬动作与停顿留白"></label>
        <div class="row wrap" style="gap:8px">
          <button type="submit" class="button">预览事实冻结去 AI 味润色</button>
        </div>
      </form>
      <div id="deslopPreviewArea"></div>
    </div>`;

    $('#deslopForm')?.addEventListener('submit', e => {
      e.preventDefault();
      const f = e.currentTarget;
      busy(f.querySelector('[type=submit]'), async () => {
        const rawP = f.querySelector('[name=paragraphs]').value.trim();
        const targets = rawP ? rawP.split(/[，,\s]+/).map(s => Number(s)).filter(n => Number.isInteger(n) && n >= 0) : null;
        const extra = f.querySelector('[name=extra_instruction]').value.trim();
        const res = await api.post(`/novels/${enc(novelId)}/deslop`, {
          scene_id: sceneId,
          target_paragraphs: targets,
          extra_instruction: extra,
          apply: false,
        });
        const pres = res.fact_preservation || {};
        $('#deslopPreviewArea').innerHTML = `<div class="card stack" style="gap:8px">
          <div class="row spread wrap">
            <strong>润色结果预览</strong>
            <div class="row" style="gap:6px">
              ${res.protected_intact ? '<span class="tag green">保护段落 100% 零篡改</span>' : ''}
              <span class="tag ${pres.passed !== false ? 'green' : 'amber'}">${pres.passed !== false ? '事实/实体零漂移通过' : '存在实体或篇幅提醒'}</span>
              <span class="tag blue">AI味命中：${number(res.before_slop_hits || 0)} → ${number(res.after_slop_hits || 0)}</span>
            </div>
          </div>
          ${(pres.issues || []).length ? `<div class="notice warning" style="margin:0;font-size:12px">${esc(pres.issues.join('；'))}</div>` : ''}
          ${(res.applied_ranges || []).map(r => `<div class="review-item stack" style="gap:4px">
            <strong>${esc(r.range_id)}（P${r.start_paragraph}..P${r.end_paragraph}）</strong>
            <p class="muted" style="margin:0;font-size:12px">❌ 原段：${esc(r.before_preview || '')}</p>
            <p style="margin:0;font-size:12px">✅ 润色：${esc(r.after_preview || '')}</p>
          </div>`).join('')}
          ${res.changed ? '<div><button type="button" class="button" id="applyDeslopBtn">确认应用为新草稿版本</button></div>' : `<p class="muted" style="margin:0;font-size:12px">${esc(res.message || '无改动')}</p>`}
        </div>`;
        $('#applyDeslopBtn')?.addEventListener('click', ev => busy(ev.currentTarget, async () => {
          await api.post(`/novels/${enc(novelId)}/deslop`, {
            scene_id: sceneId,
            polished_text: res.polished_text,
            apply: true,
          });
          toast('已将事实冻结去 AI 味版本保存为新草稿');
          if (onChanged) await onChanged();
        }));
      });
    });
  } catch (err) {
    fail(err);
  }
}

export async function openManuscriptImportDrawer(novelId, {onChanged = null} = {}) {
  drawer('导入已有半成品书稿 → 重构正史基线', loading());
  try {
    const data = await api.get(`/novels/${enc(novelId)}/manuscript-imports`);
    const imports = data.imports || [];
    $('#drawerBody').innerHTML = `<div class="stack" style="gap:14px">
      <div class="notice" style="margin:0;font-size:12px">
        已有写到第 10–60 章的 TXT/Markdown 半成品？直接粘贴导入：系统按「证据驱动重构铁律」自动切章、抽取角色现态与未回收伏笔；<strong>如遇前文自相矛盾，保留双边证据交你拍板，绝不静默二选一</strong>；确认后一键写入 SQLite 基线即可无缝续写下一章。
      </div>
      <form id="manuscriptImportForm" class="card stack" style="gap:10px">
        <label class="field"><span>书稿标题（可选）</span><input name="title" placeholder="例如：已写前12章底稿"></label>
        <label class="field"><span>粘贴已有章节正文（支持「第X章」「Chapter N」自动切分）</span><textarea name="text" rows="6" required placeholder="第一章 风雪入城&#10;正文...&#10;&#10;第二章 暗潮涌动&#10;正文..."></textarea></label>
        <div><button type="submit" class="button">分析书稿结构与前文冲突</button></div>
      </form>
      <div class="stack" style="gap:10px">
        ${imports.map(imp => `<div class="card stack" style="gap:8px">
          <div class="row spread wrap">
            <strong>${esc(imp.title)}</strong>
            <div class="row" style="gap:6px">
              <span class="tag ${imp.status === 'applied' ? 'green' : 'blue'}">${imp.status === 'applied' ? '已写入正史基线' : '待确认写入'}</span>
              <span class="tag">${number(imp.chapter_count)} 章 · ${number(imp.total_chars || 0)} 字</span>
            </div>
          </div>
          <p class="muted" style="margin:0;font-size:12px">识别角色：${esc((imp.characters || []).slice(0, 8).map(c => c.name).join('、') || '暂无')} · 潜在伏笔：${(imp.hooks || []).length} 条</p>
          ${(imp.conflicts || []).length ? `<div class="notice warning" style="margin:0;font-size:12px"><strong>检测到 ${imp.conflicts.length} 处前文自相矛盾（请裁决后再入库）：</strong>${imp.conflicts.map(c => `<div style="margin-top:4px">• ${esc(c.summary)}</div>`).join('')}</div>` : ''}
          ${imp.status !== 'applied' ? `<div><button type="button" class="secondary" data-apply-import="${esc(imp.id)}">确认写入 SQLite 正史基线</button></div>` : ''}
        </div>`).join('') || '<p class="muted" style="margin:0;font-size:12px">暂无书稿导入记录。</p>'}
      </div>
    </div>`;

    $('#manuscriptImportForm')?.addEventListener('submit', e => {
      e.preventDefault();
      const f = e.currentTarget;
      busy(f.querySelector('[type=submit]'), async () => {
        await api.post(`/novels/${enc(novelId)}/manuscript-imports`, {
          title: f.querySelector('[name=title]').value.trim(),
          text: f.querySelector('[name=text]').value,
        });
        toast('书稿分析完成，请核对角色、伏笔与矛盾清单');
        await openManuscriptImportDrawer(novelId, {onChanged});
      });
    });
    $$('[data-apply-import]').forEach(btn => {
      btn.onclick = e => busy(e.currentTarget, async () => {
        const res = await api.post(`/novels/${enc(novelId)}/manuscript-imports/${enc(btn.dataset.applyImport)}/apply`, {});
        toast(`已导入 ${res.chapters_imported} 章至正史基线，可直接续写第 ${res.next_chapter_index} 章`);
        if (onChanged) await onChanged();
        await openManuscriptImportDrawer(novelId, {onChanged});
      });
    });
  } catch (err) {
    fail(err);
  }
}

export async function openAuthorMemoryDrawer(novelId, {onChanged = null} = {}) {
  drawer('作者跨书记忆（AP / BP）与本书样式白名单', loading());
  try {
    const data = await api.get(`/novels/${enc(novelId)}/author-memory`);
    const merged = data.merged || {};
    const bookItems = data.book_items || [];
    const globalItems = data.global_items || [];
    const whitelist = data.style_whitelist || [];
    const used = Number(merged.bytes_used || 0);
    const budget = Number(merged.byte_budget || 2048);
    const pct = Math.min(100, Math.round((used / Math.max(1, budget)) * 100));

    $('#drawerBody').innerHTML = `<div class="stack" style="gap:14px">
      <div class="card stack" style="gap:8px">
        <div class="row spread wrap">
          <strong>写前偏好注入预算（按渲染行 UTF-8 字节实测）</strong>
          <span class="tag ${pct >= 90 ? 'amber' : 'green'}">${number(used)} / ${number(budget)} B（${pct}%）</span>
        </div>
        <div class="progress-track"><span style="width:${pct}%"></span></div>
        <p class="muted" style="margin:0;font-size:12px">已注入 ${(merged.items || []).length} 条（本书 BP ${bookItems.length} 条 · 跨书全局 AP ${globalItems.length} 条）；按重要度 → 本书覆写 → 最近更新排序。</p>
        ${merged.omission_notice ? `<div class="notice warning" style="margin:0;font-size:12px">${esc(merged.omission_notice)}</div>` : ''}
      </div>

      <form id="authorMemoryForm" class="card stack" style="gap:10px">
        <strong>新增作者显式偏好</strong>
        <div class="row wrap" style="gap:8px">
          <label class="field" style="flex:1"><span>作用域级别</span><select name="level"><option value="book">本书专属（BP · 随书携带可覆写全局）</option><option value="global">跨书全局（AP · 写入 library.db 复用）</option></select></label>
          <label class="field" style="flex:1"><span>分类</span><select name="kind"><option value="prose">行文语感</option><option value="dialogue">对白口吻</option><option value="pacing">节奏推进</option><option value="character">人物塑造</option><option value="world">世界规则</option><option value="taboo">雷点禁忌</option><option value="workflow">工作流偏好</option></select></label>
          <label class="field" style="width:110px"><span>重要度 (1-5)</span><input type="number" name="importance" min="1" max="5" value="4"></label>
        </div>
        <label class="field"><span>偏好断言（简明可执行，不超过 240 字）</span><textarea name="assertion" rows="2" required placeholder="例如：对峙场面优先用人物利害算账和短交锋推进，不要让角色反复摩挲指腹或茶杯。"></textarea></label>
        <label class="field"><span>可选：覆写哪条全局偏好 ID（仅本书 BP 生效，如 AP001）</span><input name="overrides_global_id" placeholder="留空表示不覆写"></label>
        <div><button type="submit" class="button">记住这条偏好</button></div>
      </form>

      <div class="card stack" style="gap:8px">
        <strong>本书专属偏好（BP · ${bookItems.length} 条）</strong>
        ${bookItems.map(it => `<div class="review-item row spread wrap" style="gap:8px">
          <div class="grow">
            <span class="tag blue">${esc(it.id)}</span>
            <span class="tag">重要度 ${it.importance}</span>
            ${it.overrides_global_id ? `<span class="tag amber">覆写 ${esc(it.overrides_global_id)}</span>` : ''}
            <span style="font-size:13px;margin-left:4px">${esc(it.assertion)}</span>
          </div>
          <div class="row" style="gap:6px">
            <button type="button" class="ghost" data-mem-promote="${esc(it.id)}">升格全局</button>
            <button type="button" class="ghost" data-mem-forget="${esc(it.id)}">遗忘</button>
          </div>
        </div>`).join('') || '<p class="muted" style="margin:0;font-size:12px">暂无本书专属偏好。</p>'}
      </div>

      <div class="card stack" style="gap:8px">
        <strong>跨书全局偏好（AP · ${globalItems.length} 条）</strong>
        ${globalItems.map(it => `<div class="review-item row spread wrap" style="gap:8px">
          <div class="grow">
            <span class="tag green">${esc(it.id)}</span>
            <span class="tag">${esc(it.scope)} · 重要度 ${it.importance}</span>
            <span style="font-size:13px;margin-left:4px">${esc(it.assertion)}</span>
          </div>
          <button type="button" class="ghost" data-mem-forget="${esc(it.id)}">遗忘</button>
        </div>`).join('') || '<p class="muted" style="margin:0;font-size:12px">暂无跨书全局偏好。</p>'}
      </div>

      <form id="styleWhitelistForm" class="card stack" style="gap:8px">
        <strong>本书样式白名单（严格仅限本书，绝不跨书污染）</strong>
        <p class="muted" style="margin:0;font-size:12px">每行一条固定口头禅、书内专有标语或刻意保留的格式字面量；0-Token 机检、去 AI 味和标点归一化都会精确豁免这些片段。</p>
        <textarea name="items" rows="3" placeholder="例如：&#10;这一刻，命运的齿轮开始转动&#10;【系统提示】">${esc(whitelist.join('\n'))}</textarea>
        <div><button type="submit" class="secondary">保存本书样式白名单</button></div>
      </form>
    </div>`;

    $('#authorMemoryForm')?.addEventListener('submit', e => {
      e.preventDefault();
      const f = e.currentTarget;
      busy(f.querySelector('[type=submit]'), async () => {
        await api.post(`/novels/${enc(novelId)}/author-memory`, {
          action: 'remember',
          level: f.querySelector('[name=level]').value,
          kind: f.querySelector('[name=kind]').value,
          importance: Number(f.querySelector('[name=importance]').value || 4),
          assertion: f.querySelector('[name=assertion]').value.trim(),
          overrides_global_id: f.querySelector('[name=overrides_global_id]').value.trim(),
        });
        toast('已记住作者创作偏好');
        if (onChanged) await onChanged();
        await openAuthorMemoryDrawer(novelId, {onChanged});
      });
    });
    $$('[data-mem-promote]').forEach(btn => {
      btn.onclick = e => busy(e.currentTarget, async () => {
        const res = await api.post(`/novels/${enc(novelId)}/author-memory`, {
          action: 'promote', id: btn.dataset.memPromote, scope: 'global',
        });
        toast(`已升格为跨书全局偏好 ${res.global_item?.id || ''}`);
        await openAuthorMemoryDrawer(novelId, {onChanged});
      });
    });
    $$('[data-mem-forget]').forEach(btn => {
      btn.onclick = e => busy(e.currentTarget, async () => {
        await api.post(`/novels/${enc(novelId)}/author-memory`, {action: 'forget', id: btn.dataset.memForget});
        toast(`已遗忘偏好 ${btn.dataset.memForget}`);
        await openAuthorMemoryDrawer(novelId, {onChanged});
      });
    });
    $('#styleWhitelistForm')?.addEventListener('submit', e => {
      e.preventDefault();
      const f = e.currentTarget;
      busy(f.querySelector('[type=submit]'), async () => {
        const res = await api.post(`/novels/${enc(novelId)}/style-whitelist`, {
          items: f.querySelector('[name=items]').value,
        });
        toast(`已保存 ${res.style_whitelist.length} 条本书样式白名单`);
        if (onChanged) await onChanged();
      });
    });
  } catch (err) {
    fail(err);
  }
}

export async function openPublishPreflightDrawer(novelId, {onChanged = null} = {}) {
  drawer('发书上架合规体检与全书一键清扫', loading());
  try {
    const initial = await api.get(`/novels/${enc(novelId)}/publish-preflight?platform=fanqie`);
    const renderBody = (rep, formVals = {}) => {
      const meta = rep.metadata_check || {};
      const sweep = rep.chapter_sweep || {};
      const platforms = rep.platforms || [];
      $('#drawerBody').innerHTML = `<div class="stack" style="gap:14px">
        <div class="card stack" style="gap:10px">
          <div class="row spread wrap">
            <strong>目标发书平台合规校验</strong>
            <span class="tag ${rep.overall_passed ? 'green' : 'amber'}">${rep.overall_passed ? '✅ 可直接发书上架' : '⚠️ 存在待修项'}</span>
          </div>
          <p class="muted" style="margin:0;font-size:12px">${esc(meta.signing_notes || '')}</p>
          <form id="publishPreflightForm" class="stack" style="gap:8px">
            <div class="row wrap" style="gap:8px">
              <label class="field" style="flex:1"><span>发布平台</span><select name="platform">${platforms.map(p => `<option value="${esc(p.id)}" ${p.id === meta.platform ? 'selected' : ''}>${esc(p.name)}</option>`).join('')}</select></label>
              <label class="field" style="flex:1"><span>引号归一化格式</span><select name="quote_mode"><option value="keep" ${sweep.quote_mode === 'keep' ? 'selected' : ''}>保持原样（仅修破损标点）</option><option value="curly" ${sweep.quote_mode === 'curly' ? 'selected' : ''}>统一为双引号“”</option><option value="yan" ${sweep.quote_mode === 'yan' ? 'selected' : ''}>统一为直角引号「」</option></select></label>
            </div>
            <label class="field"><span>书名（当前折算 ${meta.weighted_title_length ?? 0} / 上限 ${meta.max_title_length ?? 15} 字）</span><input name="title" value="${esc(formVals.title ?? '')}" placeholder="输入待上架书名（留空使用当前立项书名）"></label>
            <label class="field"><span>简介（当前 ${meta.synopsis_length ?? 0} 字，区间 ${(meta.synopsis_range || [40, 500]).join('–')} 字）</span><textarea name="synopsis" rows="3" placeholder="输入发书简介（留空使用立项梗概）">${esc(formVals.synopsis ?? '')}</textarea></label>
            <label class="field"><span>发书标签（逗号分隔，最多 ${meta.max_tags ?? 5} 个）</span><input name="tags" value="${esc(formVals.tags ?? '')}" placeholder="例如：悬疑推理, 现实向, 强反转"></label>
            <div><button type="submit" class="button">执行上架体检 + 整书标点退化扫描</button></div>
          </form>
        </div>

        <div class="card stack" style="gap:8px">
          <strong>元信息检查结果（书名 / 简介 / 标签）</strong>
          ${(meta.blocking_issues || []).map(it => `<div class="notice warning" style="margin:0;font-size:12px">⛔ ${esc(it.message)}</div>`).join('')}
          ${(meta.warnings || []).map(it => `<div class="notice" style="margin:0;font-size:12px">⚠️ ${esc(it.message)}</div>`).join('')}
          ${!(meta.blocking_issues || []).length && !(meta.warnings || []).length ? '<p class="muted" style="margin:0;font-size:12px">✅ 书名、简介与标签全部通过平台规范。</p>' : ''}
          ${meta.playbook_summary && meta.playbook_summary.monetization_model ? `<details class="details" style="margin-top:4px">
            <summary>查看「${esc(meta.platform_name || '')}」变现分成、签约与晋级规则</summary>
            <div class="stack" style="gap:6px;margin-top:8px;font-size:12px">
              ${meta.playbook_summary.recent_2026_alert ? `<p class="notice" style="margin:0">${esc(meta.playbook_summary.recent_2026_alert)}</p>` : ''}
              <p style="margin:0"><strong>变现模式：</strong>${esc(meta.playbook_summary.monetization_model)}</p>
              <p style="margin:0"><strong>签约门槛：</strong>${esc(meta.playbook_summary.signing_threshold || '')}</p>
              <p style="margin:0"><strong>全勤要求：</strong>${esc(meta.playbook_summary.full_attendance || '')}（${esc(meta.playbook_summary.daily_words || '')}）</p>
              <a class="text-link" href="#/radar?tab=playbooks">打开 6 大平台完整榜单与变现规则库 →</a>
            </div>
          </details>` : ''}
        </div>

        <div class="card stack" style="gap:8px">
          <div class="row spread wrap">
            <strong>全书已接受章节清扫（${number(sweep.chapter_count || 0)} 章 · ${number(sweep.total_chars || 0)} 字）</strong>
            <div class="row" style="gap:6px">
              <span class="tag ${sweep.blocked_chapters ? 'amber' : 'green'}">阻断 ${number(sweep.blocked_chapters || 0)} 章</span>
              <span class="tag blue">自动修标点 ${number(sweep.auto_cleaned_chapters || 0)} 章</span>
            </div>
          </div>
          ${(sweep.chapters || []).map(ch => `<div class="review-item stack" style="gap:4px">
            <div class="row spread wrap">
              <strong>第${ch.chapter_index}章 ${esc(ch.title)}</strong>
              <span class="tag ${ch.status === 'blocked' ? 'amber' : (ch.status === 'clean' ? 'green' : 'blue')}">${esc(ch.status)} · ${number(ch.chars)} 字</span>
            </div>
            ${ch.length_note ? `<p class="muted" style="margin:0;font-size:12px">${esc(ch.length_note)}</p>` : ''}
            ${(ch.blocking_issues || []).map(x => `<p style="margin:0;font-size:12px">⛔ ${esc(x.message)}</p>`).join('')}
            ${(ch.attention_issues || []).map(x => `<p class="muted" style="margin:0;font-size:12px">⚠️ ${esc(x.message)}</p>`).join('')}
          </div>`).join('') || '<p class="muted" style="margin:0;font-size:12px">当前尚无已接受章节正文。</p>'}
          ${sweep.clean_export_text ? `<details class="details"><summary>预览 / 复制一键标点归一化后的发书净稿</summary><textarea readonly rows="8" style="width:100%;margin-top:8px">${esc(sweep.clean_export_text)}</textarea></details>` : ''}
        </div>
      </div>`;

      $('#publishPreflightForm')?.addEventListener('submit', e => {
        e.preventDefault();
        const f = e.currentTarget;
        const vals = {
          platform: f.querySelector('[name=platform]').value,
          quote_mode: f.querySelector('[name=quote_mode]').value,
          title: f.querySelector('[name=title]').value.trim() || undefined,
          synopsis: f.querySelector('[name=synopsis]').value.trim() || undefined,
          tags: f.querySelector('[name=tags]').value.trim() || undefined,
        };
        busy(f.querySelector('[type=submit]'), async () => {
          const next = await api.post(`/novels/${enc(novelId)}/publish-preflight`, vals);
          toast(next.overall_passed ? '上架合规体检全部通过' : '体检完成，请按标红项修正');
          renderBody(next, {
            title: f.querySelector('[name=title]').value,
            synopsis: f.querySelector('[name=synopsis]').value,
            tags: f.querySelector('[name=tags]').value,
          });
        });
      });
    };
    renderBody(initial);
  } catch (err) {
    fail(err);
  }
}

export async function openAbBlindJudgeDrawer(novelId, sceneId, {onChanged = null} = {}) {
  drawer('同场双稿双向换位双盲裁判（抗位置偏见）', loading());
  try {
    const wb = await api.get(`/novels/${enc(novelId)}/quality?scene=${enc(sceneId || '')}`);
    const detail = await api.get(`/novels/${enc(novelId)}`);
    const sc = (detail.project?.scenes || []).find(s => s.id === sceneId);
    const drafts = sc?.drafts || [];
    $('#drawerBody').innerHTML = `<div class="stack" style="gap:14px">
      <div class="notice" style="margin:0;font-size:12px">
        单次让模型对比 A/B 两稿极易出现「总是偏爱排在前面的稿一」的位置偏见。本裁判自动执行 <strong>(A, B)</strong> 与 <strong>(B, A)</strong> 两轮完全匿名换位评审：<strong>只有两轮结论完全一致才判胜出，否则自动裁定平局交作者拍板</strong>。
      </div>
      <form id="abJudgeForm" class="card stack" style="gap:10px">
        ${drafts.length >= 2 ? `<div class="row wrap" style="gap:8px">
          <label class="field" style="flex:1"><span>稿件 A</span><select name="draft_a_id">${drafts.map((d, i) => `<option value="${esc(d.id)}" ${i === drafts.length - 2 ? 'selected' : ''}>草稿 v${d.version}</option>`).join('')}</select></label>
          <label class="field" style="flex:1"><span>稿件 B</span><select name="draft_b_id">${drafts.map((d, i) => `<option value="${esc(d.id)}" ${i === drafts.length - 1 ? 'selected' : ''}>草稿 v${d.version}</option>`).join('')}</select></label>
        </div>` : `<div class="stack" style="gap:8px">
          <label class="field"><span>粘贴稿件 A 正文</span><textarea name="draft_a_text" rows="4" required placeholder="粘贴第一版草稿"></textarea></label>
          <label class="field"><span>粘贴稿件 B 正文</span><textarea name="draft_b_text" rows="4" required placeholder="粘贴第二版草稿"></textarea></label>
        </div>`}
        <label class="field"><span>附加评审侧重点（可选）</span><input name="criteria" placeholder="例如：重点比较两人对峙的张力与去 AI 套话自然度"></label>
        <div><button type="submit" class="button">发起双向换位盲评（2 轮校验）</button></div>
      </form>
      <div id="abJudgeResult"></div>
    </div>`;

    $('#abJudgeForm')?.addEventListener('submit', e => {
      e.preventDefault();
      const f = e.currentTarget;
      busy(f.querySelector('[type=submit]'), async () => {
        const res = await api.post(`/novels/${enc(novelId)}/ab-judge`, {
          scene_id: sceneId,
          draft_a_id: f.querySelector('[name=draft_a_id]')?.value || '',
          draft_b_id: f.querySelector('[name=draft_b_id]')?.value || '',
          draft_a_text: f.querySelector('[name=draft_a_text]')?.value || '',
          draft_b_text: f.querySelector('[name=draft_b_text]')?.value || '',
          criteria: f.querySelector('[name=criteria]').value.trim(),
        });
        $('#abJudgeResult').innerHTML = `<div class="card stack" style="gap:8px">
          <div class="row spread wrap">
            <strong>裁决结果：${esc(res.winner_label)}</strong>
            <div class="row" style="gap:6px">
              <span class="tag ${res.consensus ? 'green' : 'amber'}">${res.consensus ? '两轮一致' : '未一致 / 平局'}</span>
              ${res.position_bias_detected ? '<span class="tag amber">已拦截位置偏见</span>' : ''}
            </div>
          </div>
          <p style="margin:0;font-size:13px">${esc(res.summary)}</p>
          ${(res.rounds || []).map((rd, idx) => `<div class="review-item stack" style="gap:4px">
            <strong>第 ${idx + 1} 轮（匿名顺位：${esc((rd.order || []).join(' vs '))} → 映射胜者：${esc(rd.mapped_winner)}）</strong>
            <p class="muted" style="margin:0;font-size:12px">${esc(rd.rationale || '')}</p>
          </div>`).join('')}
        </div>`;
        toast(`盲评完成：${res.winner_label}`);
        if (onChanged) await onChanged();
      });
    });
  } catch (err) {
    fail(err);
  }
}


export async function openBookAuditDrawer(novelId, {onChanged = null} = {}) {
  drawer('全书 12 维 0-Token 机械审读报告', loading());
  try {
    const rep = await api.get(`/novels/${enc(novelId)}/book-audit`);
    const st = rep.stats || {};
    const checks = rep.checks || [];
    const findings = rep.findings || [];
    const members = rep.presence?.members || [];
    const chs = rep.presence?.chapters || [];
    const cps = rep.catchphrases || [];
    const repeats = rep.repeats || [];
    const anchor = rep.calibration_anchor;

    const lvlBadge = lvl => lvl === 'pass'
      ? '<span class="tag green">通过</span>'
      : lvl === 'fix'
        ? '<span class="tag" style="color:var(--danger);border-color:var(--danger)">需修</span>'
        : lvl === 'advise'
          ? '<span class="tag amber">建议核查</span>'
          : lvl === 'skip'
            ? '<span class="tag">跳过</span>'
            : '<span class="tag blue">留意</span>';

    $('#drawerBody').innerHTML = `<div class="stack" style="gap:14px">
      <div class="card stack" style="gap:8px">
        <div class="row spread wrap">
          <strong>全书机械体检总览（${number(st.chapters || 0)} 章 · ${number(st.total_words || 0)} 字）</strong>
          <div class="row wrap" style="gap:6px">
            <span class="tag">中位 ${number(st.median_words || 0)} 字/章</span>
            <span class="tag blue">对白占比 ${st.dialogue_pct || 0}%</span>
            <span class="tag ${st.findings?.fix ? 'amber' : 'green'}">需修 ${st.findings?.fix || 0} · 建议 ${st.findings?.advise || 0}</span>
          </div>
        </div>
        <div class="row wrap" style="gap:6px">
          ${checks.map(c => `<span class="tag">${esc(c.name)} ${lvlBadge(c.level)}${c.count ? ` (${c.count})` : ''}</span>`).join('')}
        </div>
      </div>

      <div class="card stack" style="gap:8px">
        <div class="row spread wrap">
          <strong>本书第 1 章文风自校准锚段（语态尾置注入）</strong>
          <button type="button" class="secondary" id="btnAutoCalibrateAnchor">重新从第 1 章自动提炼锚段</button>
        </div>
        ${anchor
          ? `<p class="muted" style="margin:0;font-size:12px">来源：第 ${anchor.chapter_index} 章（${anchor.chars} 字）· 后续写作将把此段与前文尾段置放于 Prompt 最末尾以稳住语态。</p><blockquote style="margin:0;padding:8px 12px;border-left:3px solid var(--accent);font-size:12px;white-space:pre-wrap">${esc(anchor.excerpt.slice(0, 360))}${anchor.excerpt.length > 360 ? '…' : ''}</blockquote>`
          : '<p class="muted" style="margin:0;font-size:12px">尚未提取本书第 1 章校准锚段；接受第 1 章正文后将自动提取，也可点右上角按钮手动提取。</p>'}
      </div>

      <div class="card stack" style="gap:8px">
        <strong>发现明细（${findings.length} 项）</strong>
        ${findings.length ? findings.slice(0, 20).map(f => `<div class="review-item">
          <div class="row spread wrap"><strong>${esc(f.title)}</strong>${lvlBadge(f.severity)}</div>
          <p class="muted" style="margin:4px 0 0;font-size:12px">${esc(f.detail)}</p>
        </div>`).join('') : '<p class="muted" style="margin:0;font-size:12px">✅ 12 项机械指标全部干净，未发现跨章断档、引号失衡或重度短语复读。</p>'}
      </div>

      ${members.length ? `<div class="card stack" style="gap:8px">
        <strong>角色全书在场矩阵（${members.length} 人）</strong>
        <div class="table-wrap"><table class="data-table">
          <thead><tr><th>角色</th><th>定位</th><th>总提及</th><th>出场章数</th><th>逐章频次（第${chs[0] || 1}–${chs.at(-1) || 1}章）</th></tr></thead>
          <tbody>${members.map(m => `<tr><td><strong>${esc(m.name)}</strong></td><td>${esc(m.role)}</td><td>${m.total}</td><td>${m.appearances}/${chs.length}</td><td><small class="muted">${(m.counts || []).join(' · ')}</small></td></tr>`).join('')}</tbody>
        </table></div>
      </div>` : ''}

      ${cps.length ? `<div class="card stack" style="gap:8px">
        <strong>口头禅声部落实核对（支持跨插入语拼接）</strong>
        <div class="row wrap" style="gap:6px">${cps.map(r => `<span class="tag ${r.total === 0 ? 'amber' : 'green'}">${esc(r.name)}「${esc(r.phrase)}」：${r.total} 次</span>`).join('')}</div>
      </div>` : ''}

      ${repeats.length ? `<div class="card stack" style="gap:8px">
        <strong>全书高频重复短语（O(N) 扫描 Top 12）</strong>
        <div class="row wrap" style="gap:6px">${repeats.map(r => `<span class="tag ${r.count >= 8 ? 'amber' : ''}">「${esc(r.phrase)}」×${r.count}</span>`).join('')}</div>
      </div>` : ''}
    </div>`;

    $('#btnAutoCalibrateAnchor')?.addEventListener('click', e => busy(e.currentTarget, async () => {
      await api.post(`/novels/${enc(novelId)}/calibration-anchor`, {});
      toast('已从第 1 章重新提取文风自校准锚段');
      await openBookAuditDrawer(novelId, {onChanged});
    }));
  } catch (err) {
    fail(err);
  }
}

export async function openFactLedgerDrawer(novelId, {onChanged = null} = {}) {
  drawer('设定名词与硬数字事实词典（先登记后动笔）', loading());
  try {
    const data = await api.get(`/novels/${enc(novelId)}/fact-ledger`);
    const entries = data.entries || [];
    const cats = data.categories || {term: '设定名词', number: '硬数字事实', timeline: '时间线锚点', foreshadow: '伏笔/母题'};

    $('#drawerBody').innerHTML = `<div class="stack" style="gap:14px">
      <div class="notice" style="margin:0;font-size:12px">
        <strong>先登记后引用 · 防穿帮与防提前剧透：</strong>写入此处的新名词会在首现章强制要求附带上下文线索；硬数字与时间线会注入写前简报防现场编数；到达「计划揭示章」前绝不向写手泄露「完整真相」。
      </div>

      <form id="factLedgerForm" class="card stack" style="gap:8px">
        <strong>新增 / 更新词典条目</strong>
        <div class="row wrap" style="gap:8px">
          <label class="field" style="flex:1"><span>类别</span><select name="category">${Object.entries(cats).map(([k, v]) => `<option value="${esc(k)}">${esc(v)}</option>`).join('')}</select></label>
          <label class="field" style="flex:2"><span>名词 / 事实项名称</span><input name="name" required placeholder="例如：蓝晶 / 主角年龄 / 北凉灭国年限"></label>
          <label class="field" style="flex:1"><span>首现章</span><input name="first_chapter" type="number" min="0" value="1"></label>
          <label class="field" style="flex:1"><span>计划揭示章</span><input name="planned_reveal_chapter" type="number" min="1" placeholder="选填"></label>
        </div>
        <label class="field"><span>读者当前已知（写手可见边界）</span><input name="reader_known" required placeholder="例如：贵重黑市晶体 / 二十岁 / 十一年前"></label>
        <label class="field"><span>完整真相（未到揭示章前对写手保密，选填）</span><input name="full_truth" placeholder="例如：实际是储存记忆的容器"></label>
        <div><button type="submit" class="button">登记入词典</button></div>
      </form>

      <div class="card stack" style="gap:8px">
        <strong>已登记条目（${entries.length}）</strong>
        ${entries.length ? `<div class="table-wrap"><table class="data-table">
          <thead><tr><th>类别</th><th>条目名</th><th>首现</th><th>读者已知</th><th>完整真相 / 揭示章</th><th>操作</th></tr></thead>
          <tbody>${entries.map(e => `<tr>
            <td><span class="tag">${esc(e.category_label)}</span></td>
            <td><strong>${esc(e.name)}</strong></td>
            <td>第${e.first_chapter}章</td>
            <td>${esc(e.reader_known)}</td>
            <td>${e.full_truth ? esc(e.full_truth) : '—'}${e.planned_reveal_chapter ? ` <span class="tag blue">第${e.planned_reveal_chapter}章兑现</span>` : ''}</td>
            <td><button type="button" class="ghost" data-del-fact="${esc(e.id)}">删除</button></td>
          </tr>`).join('')}</tbody>
        </table></div>` : '<p class="muted" style="margin:0;font-size:12px">尚无词典条目。建议先登记关键年龄、时间线、金额与核心世界名词。</p>'}
      </div>
    </div>`;

    $('#factLedgerForm').onsubmit = e => {
      e.preventDefault();
      const fd = new FormData(e.target);
      busy(e.target.querySelector('[type=submit]'), async () => {
        await api.post(`/novels/${enc(novelId)}/fact-ledger`, {
          category: fd.get('category'),
          name: fd.get('name'),
          first_chapter: Number(fd.get('first_chapter') || 1),
          planned_reveal_chapter: fd.get('planned_reveal_chapter') ? Number(fd.get('planned_reveal_chapter')) : null,
          reader_known: fd.get('reader_known'),
          full_truth: fd.get('full_truth'),
        });
        toast('已登记入设定与事实词典');
        if (onChanged) await onChanged();
        await openFactLedgerDrawer(novelId, {onChanged});
      });
    };

    $$('[data-del-fact]').forEach(btn => btn.onclick = () => busy(btn, async () => {
      await api.post(`/novels/${enc(novelId)}/fact-ledger/${enc(btn.dataset.delFact)}/delete`, {});
      toast('已删除词典条目');
      await openFactLedgerDrawer(novelId, {onChanged});
    }));
  } catch (err) {
    fail(err);
  }
}
