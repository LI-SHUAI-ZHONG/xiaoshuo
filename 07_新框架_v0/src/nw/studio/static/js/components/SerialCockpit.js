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
