import {api,enc,query} from '../api.js';
import {$,$$,esc,drawer,loading,fail,toast,busy,number,date} from '../ui.js';

const WANT_LABEL = {yes:'想看下一章', weak:'追读意愿偏弱', no:'不想继续看', unknown:'见总评'};
const WANT_TONE = {yes:'green', weak:'amber', no:'', unknown:'blue'};
const MODE_LABEL = {
  off: '关闭（仅用内置规则与前场衔接）',
  author_sample: '作者参照样段（开篇黄金三章推荐）',
  auto_book_prose: '沿用本书已采用正文语感（前三章后推荐）',
};

export function renderColdReadReport(report) {
  if (!report) return '<p class="muted">尚无冷读报告。</p>';
  const p = report.parsed || {};
  const keep = p.keep_reading || {};
  const hook = p.hook_moment || {};
  const want = keep.want_next || 'unknown';
  const skips = Array.isArray(p.skip_zones) ? p.skip_zones : [];
  const under = Array.isArray(p.underwritten_spots) ? p.underwritten_spots : [];
  const reps = Array.isArray(p.repetitive_beats) ? p.repetitive_beats : [];
  const conf = Array.isArray(p.confusion_or_mismatch) ? p.confusion_or_mismatch : [];
  const scopeTag = {scene:'单场盲读', chapter:'整章盲读', range:'多章连读'}[report.scope] || report.scope || '盲读';

  const renderQuote = q => q ? `<blockquote style="margin:4px 0;padding:4px 8px;border-left:2px solid var(--border);font-size:12px">${esc(q)}</blockquote>` : '';

  return `<article class="card stack" style="gap:12px">
    <div class="row spread wrap" style="gap:8px">
      <div>
        <strong>${esc(report.label || '陌生读者冷读')}</strong>
        <span class="muted" style="font-size:12px;margin-left:8px">${esc(date(report.created_at))} · ${esc(report.model || '')} · ${number(report.target_chars || 0)} 字</span>
      </div>
      <div class="row wrap" style="gap:6px">
        <span class="tag blue">${esc(scopeTag)}</span>
        <span class="tag ${WANT_TONE[want] || ''}" ${want === 'no' ? 'style="color:var(--danger)"' : ''}>${esc(WANT_LABEL[want] || want)}</span>
      </div>
    </div>
    ${p.verdict_summary ? `<div class="notice" style="margin:0"><strong>陌生读者总评：</strong><span style="white-space:pre-wrap">${esc(p.verdict_summary)}</span></div>` : ''}
    <div class="method-section">
      <strong>1. 读到哪一句开始想往下看</strong>
      <p style="margin:4px 0 0;font-size:12px">${hook.found ? '<span class="tag green">已勾住</span> ' : '<span class="tag amber">暂未勾住</span> '}${esc(hook.reason || '无说明')}</p>
      ${renderQuote(hook.quote)}
    </div>
    <div class="method-section">
      <strong>2. 哪些段落读着想跳过（${skips.length} 处）</strong>
      ${skips.length ? skips.map(s => `<div style="margin-top:6px;font-size:12px"><span class="tag amber">${esc(s.location || (s.chapter ? `第${s.chapter}章` : '段落'))}</span> ${esc(s.reason || '')}${renderQuote(s.quote)}</div>`).join('') : '<p class="muted" style="margin:4px 0 0;font-size:12px">读者未发现明显想跳过的段落。</p>'}
    </div>
    <div class="method-section">
      <strong>3. 最该细写却写太短的地方（${under.length} 处）</strong>
      ${under.length ? under.map(u => `<div style="margin-top:6px;font-size:12px"><span class="tag blue">${esc(u.location || (u.chapter ? `第${u.chapter}章` : '位置'))}</span> ${esc(u.reason || '')}${renderQuote(u.quote)}</div>`).join('') : '<p class="muted" style="margin:4px 0 0;font-size:12px">读者未指出明显略写过快的重点戏。</p>'}
    </div>
    ${report.scope === 'range' || reps.length ? `<div class="method-section">
      <strong>重复疲倦的桥段/套路（${reps.length} 处）</strong>
      ${reps.length ? reps.map(r => `<div style="margin-top:6px;font-size:12px">${Array.isArray(r.chapters) && r.chapters.length ? `<span class="tag amber">第 ${esc(r.chapters.join('、'))} 章</span> ` : ''}${esc(r.pattern || '')}</div>`).join('') : '<p class="muted" style="margin:4px 0 0;font-size:12px">未发现明显重复疲倦套路。</p>'}
    </div>` : ''}
    <div class="method-section">
      <strong>4. 读完想不想看下一章</strong>
      <p style="margin:4px 0 0;font-size:12px">${keep.lingering_question ? `<strong>最惦记的事：</strong>${esc(keep.lingering_question)}<br>` : ''}${esc(keep.reason || '无补充说明')}</p>
    </div>
    <div class="method-section">
      <strong>5. 看不懂或前后对不上的位置（${conf.length} 处）</strong>
      ${conf.length ? conf.map(c => `<div style="margin-top:6px;font-size:12px"><span class="tag" style="color:var(--danger)">${esc(c.location || (Array.isArray(c.chapters) ? `第${c.chapters.join('/')}章` : '疑点'))}</span> ${esc(c.misread_risk || c.reason || '')}${renderQuote(c.quote)}</div>`).join('') : '<p class="muted" style="margin:4px 0 0;font-size:12px">读者未发现明显理解障碍或前后错位。</p>'}
    </div>
    <details class="details">
      <summary>查看隔离输入核验与读者原始回复</summary>
      <p class="muted" style="font-size:11px;margin:6px 0">输入字段严格隔离为：${esc((report.isolated_input_keys || []).join(', ') || 'target_prose')}（不含大纲、设定卡、人物卡、Brief 或历史审稿）</p>
      <pre class="raw-data" style="white-space:pre-wrap">${esc(report.raw_text || '')}</pre>
    </details>
  </article>`;
}

export function renderColdReadInspectorSection(coldRead, hasScene) {
  if (!hasScene && !coldRead) return '';
  const latest = coldRead?.latest_for_draft || null;
  const p = latest?.parsed || {};
  const keep = p.keep_reading || {};
  const want = keep.want_next || 'unknown';
  const skips = (p.skip_zones || []).length;
  const under = (p.underwritten_spots || []).length;
  const conf = (p.confusion_or_mismatch || []).length;
  return `<section class="inspector-section" id="inspectorColdRead">
    <div class="row spread" style="margin-bottom:8px">
      <h4 style="margin:0">陌生读者冷读（零大纲盲读）</h4>
      ${latest ? `<span class="tag ${WANT_TONE[want] || ''}">${esc(WANT_LABEL[want] || want)}</span>`
        : coldRead?.recommended ? '<span class="tag amber">黄金三章建议</span>' : ''}
    </div>
    ${latest ? `<p style="font-size:12px;margin:0 0 8px;white-space:pre-wrap">${esc(p.verdict_summary || keep.reason || '已完成本次陌生读者盲读。')}</p>
      <div class="row wrap" style="gap:6px;margin-bottom:8px">
        <span class="tag ${skips ? 'amber' : 'green'}">想跳过 ${skips}</span>
        <span class="tag ${under ? 'blue' : 'green'}">写太短 ${under}</span>
        <span class="tag ${conf ? 'amber' : 'green'}">疑点/错位 ${conf}</span>
      </div>`
      : `<p class="muted" style="font-size:12px;margin:0 0 8px">${esc(coldRead?.recommendation_reason || '不给大纲与设定，请干净读者挑出想跳读、写太短或看不懂的地方。')}</p>`}
    ${hasScene ? '<button class="secondary" type="button" id="inspectorOpenColdRead" style="width:100%">打开陌生读者冷读与历史报告</button>' : ''}
  </section>`;
}

const DOMAIN_TABS = [
  {id:'plot_pacing', label:'剧情节奏与钩子', stages:'06 书卷章纲 / 07 事件 / 09 场景 / 15 本场2行节拍 / 16 审稿', contrastTitle:'脱剧情大纲/节奏正反微对照（校准 06 推演坐标）', badLabel:'❌ 注水/套路大纲', goodLabel:'✅ 强因果节奏大纲'},
  {id:'world', label:'世界规则底座', stages:'03 世界定稿 / 08 行动门槛 / 16 规则审稿（不塞入 15 写手）', contrastTitle:'脱剧情世界卡正反微对照（校准 03 造卡边界）', badLabel:'❌ 空壳设定/说明书', goodLabel:'✅ 可运行硬边界卡'},
  {id:'cast', label:'人物群像力学', stages:'04 人物定稿 / 05 关系张力 / 16 角色审稿（不塞入 15 写手）', contrastTitle:'脱剧情人物关系正反微对照（校准 04/05 造卡深度）', badLabel:'❌ 工具人/扁平卡', goodLabel:'✅ 带盲点与利害活人卡'},
  {id:'voice', label:'语感规范与参照', stages:'13 表达设计 / 15 正文写作 / 16 语感审稿', contrastTitle:'脱剧情 50 字正反微对照（校准 15 写手采样坐标 · 0 抄袭风险）', badLabel:'❌ 僵硬 AI 腔', goodLabel:'✅ 目标语感'},
];

const DOMAIN_DIM_LABELS = {
  world: {
    premise_law: '底层铁律',
    scarcity_cost: '稀缺与代价',
    institution_gate: '制度制约',
    background_clock: '后台时钟',
    exposition_policy: '渗入纪律',
    genre_firewall: '题材防污染墙',
  },
  cast: {
    protagonist_drive: '主角驱动与盲点',
    antagonist_logic: '反派不降智逻辑',
    supporting_roster: '配角复用纪律',
    relation_asymmetry: '关系不对称',
    independent_side_ties: '配角独立互动',
    arc_conversion: '弧光代价转化',
  },
  plot_pacing: {
    drive_loop: '核心驱动循环',
    golden_three: '黄金三章密度',
    pacing_cadence: '篇幅联动节奏',
    hook_contract: '章末钩子纪律',
    foreshadow_payoff: '伏笔与反转兑现',
    aftermath_carry: '高潮余波承接',
  },
  voice: {
    register: '语体寄存器',
    cadence: '句式呼吸',
    psychic_distance: '内心贴近度',
    dialogue_texture: '对白质地',
    imagery_budget: '描写克制度',
    pacing_payoff: '节奏与落点',
  },
};

export function renderCraftSpecPreview(domain, base, {scaleProfile = null, fps = [], compact = false} = {}) {
  if (!base) return '';
  const tabMeta = DOMAIN_TABS.find(t => t.id === domain) || DOMAIN_TABS[3];
  const dimLabels = DOMAIN_DIM_LABELS[domain] || DOMAIN_DIM_LABELS.voice;
  const dims = base.dimensions || {};
  const contrasts = (base.micro_contrasts || []).slice(0, compact ? 1 : 2);
  const redlines = base.anti_drift_redlines || base.drift_redlines || [];
  const scaleBanner = (domain === 'plot_pacing' && scaleProfile)
    ? `<div class="notice" style="margin:0;font-size:12px"><strong>篇幅联动节奏标尺（${esc(scaleProfile.tier_label || '')}）：</strong>${esc(scaleProfile.recommended_volumes || '')} · 小高潮每 ${esc((scaleProfile.small_climax_every_chapters || [5, 8]).join('–'))} 章 · 配比 ${esc(scaleProfile.chapter_weight_ratio || '')}${scaleProfile.stage_escalation_rule ? `<br><span class="muted">${esc(scaleProfile.stage_escalation_rule)}</span>` : ''}</div>`
    : '';
  return `<div class="card stack" style="gap:10px;background:var(--bg-soft, var(--bg-panel))">
    <div class="row spread wrap">
      <strong>${esc(base.name)}</strong>
      <span class="tag green">${esc(base.relevance_label || '可执行规范')}</span>
    </div>
    <p class="muted" style="margin:0;font-size:12px">${esc(base.tagline || '')}</p>
    ${scaleBanner}
    <div class="stack" style="gap:4px;font-size:12px">
      ${Object.entries(dimLabels).map(([k, lbl]) => dims[k] ? `<p style="margin:0"><strong>${esc(lbl)}：</strong>${esc(dims[k])}</p>` : '').join('')}
    </div>
    ${redlines.length ? `<div style="font-size:12px"><strong>专属防崩坏/防漂移红线（同步用于 16 步审稿）：</strong><ul style="margin:4px 0 0 18px">${redlines.map(r => `<li>${esc(r)}</li>`).join('')}</ul></div>` : ''}
    ${contrasts.length ? `<details class="details" ${compact ? '' : 'open'}>
      <summary><strong>${esc(tabMeta.contrastTitle)}</strong></summary>
      <div class="stack" style="gap:8px;margin-top:8px">
        ${contrasts.map(c => `<div class="method-section" style="font-size:12px">
          <strong>${esc(c.label)}</strong>
          <p style="margin:4px 0;color:var(--danger)">${esc(tabMeta.badLabel)}：${esc(c.bad_ai)}</p>
          <p style="margin:4px 0">${esc(tabMeta.goodLabel)}：${esc(c.target_craft || c.target_voice || '')}</p>
          <p class="muted" style="margin:2px 0 0">要点：${esc(c.why)}</p>
        </div>`).join('')}
      </div>
    </details>` : ''}
    ${fps.length ? `<p class="muted" style="margin:0;font-size:12px">已叠加同题材拆解指纹：${fps.map(f => esc(f.title)).join('、')}</p>` : ''}
  </div>`;
}

export function renderVoiceSpecPreview(base, knobs, fps = []) {
  return renderCraftSpecPreview('voice', base, {fps});
}

export async function openCraftSpecsDrawer(novelId, {initialDomain = 'plot_pacing', onSaved} = {}) {
  drawer('本书四维创作基座卡（世界 · 人物 · 剧情节奏 · 语感）', loading());
  let activeDomain = DOMAIN_TABS.some(t => t.id === initialDomain) ? initialDomain : 'plot_pacing';
  let data = null;

  const paintTab = () => {
    const tabMeta = DOMAIN_TABS.find(t => t.id === activeDomain) || DOMAIN_TABS[0];
    const spec = (data.specs || {})[activeDomain] || {};
    const domSetup = (data.setup || {})[activeDomain] || {};
    const bases = domSetup.bases || [];
    const knobsMeta = domSetup.knobs || {};
    const fps = domSetup.available_fingerprints || [];
    const styleData = data.style_reference || {};
    const activeBaseId = spec.base_id || spec.base_voice_id || bases[0]?.id || '';
    const activeKnobs = spec.knobs || {};
    const activeFpIds = new Set(spec.fingerprint_ids || []);
    const singleKnobKeys = Object.keys(knobsMeta).filter(k => !knobsMeta[k]?.multi);
    const multiKnobKey = Object.keys(knobsMeta).find(k => knobsMeta[k]?.multi) || '';

    const acceptedInfo = styleData.can_use_auto_book_prose
      ? `本书已有已接受章节（第 ${(styleData.accepted_chapters || []).join('、')} 章），可随时切为「沿用本书已采用正文语感」。`
      : '本书尚未接受第 1 章正文，默认以「本书语感规范卡」精准控腔即可，无需强求外部样章。';

    $('#drawerBody').innerHTML = `<div class="stack" style="gap:16px">
      <div class="row wrap" style="gap:6px" id="craftSpecTabBar">
        ${DOMAIN_TABS.map(t => {
          const sp = (data.specs || {})[t.id];
          const on = t.id === activeDomain;
          return `<button type="button" class="${on ? 'button' : 'secondary'}" data-spec-tab="${esc(t.id)}">${esc(t.label)}${sp?.enabled ? ' · 启' : ''}</button>`;
        }).join('')}
      </div>
      <div class="notice" style="margin:0;font-size:12px">
        <strong>生效步骤：</strong>${esc(tabMeta.stages)}。<br>
        <strong>优先级铁律：</strong>作者硬约束与已批准上游卡片 &gt; 本基座规范 &gt; 通用默认规则。随时调整只影响后续新建或重设计卷章，不篡改已定稿正文。
      </div>
      <form id="craftSpecForm" class="stack" style="gap:12px">
        <label class="check-row"><input type="checkbox" name="enabled" id="craftSpecEnabled" ${spec.enabled !== false ? 'checked' : ''}> <strong>启用「${esc(tabMeta.label)}」（推荐）</strong></label>
        <label class="field">
          <span>1. 内置可执行基座（已按本书题材推荐排序）</span>
          <select name="base_id" id="craftBaseSelect">
            ${bases.map(b => `<option value="${esc(b.id)}" ${b.id === activeBaseId ? 'selected' : ''}>${esc(b.name)} · ${esc(b.relevance_label || '')}</option>`).join('')}
          </select>
        </label>
        <div id="craftBasePreviewBox"></div>
        <div class="form-grid">
          ${singleKnobKeys.map(k => {
            const meta = knobsMeta[k];
            const cur = activeKnobs[k] || '';
            return `<label class="field"><span>${esc(meta.label)}</span><select name="knob_${esc(k)}" id="craftKnob_${esc(k)}">
              ${(meta.options || []).map(o => `<option value="${esc(o.id)}" ${o.id === cur ? 'selected' : ''}>${esc(o.label)}</option>`).join('')}
            </select></label>`;
          }).join('')}
        </div>
        ${multiKnobKey && knobsMeta[multiKnobKey] ? `<fieldset class="method-section"><legend>${esc(knobsMeta[multiKnobKey].label)}</legend>
          <div class="row wrap" style="gap:10px">
            ${(knobsMeta[multiKnobKey].options || []).map(o => `<label class="check-row" style="margin:0"><input type="checkbox" name="craftMultiKnob" value="${esc(o.id)}" ${(activeKnobs[multiKnobKey] || []).includes(o.id) ? 'checked' : ''}> <span>${esc(o.label)}</span></label>`).join('')}
          </div>
        </fieldset>` : ''}
        <fieldset class="method-section">
          <legend>2. 可选 · 叠加同题材拆解收录的脱剧情指纹（${fps.length} 条兼容，已自动隔离跨题材污染）</legend>
          ${fps.length ? fps.map(fp => `<label class="check-row"><input type="checkbox" name="fingerprint_ids" value="${esc(fp.id)}" ${activeFpIds.has(fp.id) ? 'checked' : ''}> <span><strong>${esc(fp.title)}</strong> <small class="muted">(${esc(fp.base_name || fp.base_voice_name || '')} · ${(fp.body?.techniques || []).length} 条手法)</small></span></label>`).join('')
            : '<p class="muted" style="margin:4px 0 0;font-size:12px">当前题材该维尚无已拆解收录的参考书指纹；内置基座已可直接高质量驱动制作。在预存库运行「精准步骤拆解」后 4 条轨道均会自动沉淀同题材指纹。</p>'}
        </fieldset>
        <label class="field">
          <span>3. 本书补充细则（选填）</span>
          <textarea name="custom_notes" rows="2" placeholder="针对本书这一维的专属要求或补充边界…">${esc(spec.custom_notes || '')}</textarea>
        </label>
        <div class="row wrap" style="gap:8px">
          <button type="submit" class="button">保存并编译「${esc(tabMeta.label)}」</button>
        </div>
      </form>
      ${activeDomain === 'voice' ? `<details class="details" ${styleData.enabled ? 'open' : ''}>
        <summary><strong>可选 · 附加写前语感样段参照（${styleData.enabled ? '已启用' : '未启用'}）</strong></summary>
        <form id="styleReferenceForm" class="stack" style="margin-top:12px">
          <label class="field">
            <span>样段参照模式</span>
            <select name="mode" id="styleRefMode">
              <option value="off" ${styleData.mode === 'off' ? 'selected' : ''}>${esc(MODE_LABEL.off)}</option>
              <option value="author_sample" ${styleData.mode === 'author_sample' ? 'selected' : ''}>${esc(MODE_LABEL.author_sample)}</option>
              <option value="auto_book_prose" ${styleData.mode === 'auto_book_prose' ? 'selected' : ''}>${esc(MODE_LABEL.auto_book_prose)}</option>
            </select>
            <small class="muted">${esc(acceptedInfo)}</small>
          </label>
          <div id="styleSampleFields" class="stack" style="gap:10px">
            <div class="form-grid">
              <label class="field"><span>样段标题（可选）</span><input name="title" value="${esc(styleData.title || '')}" placeholder="如：作者自写试笔第一章"></label>
              <label class="field"><span>来源备注（可选）</span><input name="source_note" value="${esc(styleData.source_note || '')}" placeholder="如：作者自写"></label>
            </div>
            <label class="field">
              <span>参照样段正文（最多 ${number(styleData.max_excerpt_chars || 4000)} 字，严禁照搬剧情人名）</span>
              <textarea name="excerpt" rows="6" placeholder="可选粘贴 1–2 段代表目标语感的自写正文…">${esc(styleData.excerpt || '')}</textarea>
            </label>
          </div>
          <label class="field">
            <span>样段补充说明（可选）</span>
            <textarea name="style_notes" rows="2">${esc(styleData.style_notes || '')}</textarea>
          </label>
          <div class="row wrap" style="gap:8px">
            <button type="submit" class="secondary">保存附加样段参照</button>
            <button type="button" class="ghost" id="disableStyleRefBtn">关闭样段参照</button>
          </div>
        </form>
      </details>` : ''}
    </div>`;

    $$('#craftSpecTabBar [data-spec-tab]').forEach(btn => {
      btn.onclick = () => { activeDomain = btn.dataset.specTab; paintTab(); };
    });

    const paintPreview = () => {
      const bid = $('#craftBaseSelect').value;
      const base = bases.find(b => b.id === bid) || bases[0];
      const pickedFps = fps.filter(fp => $$('#craftSpecForm [name=fingerprint_ids]:checked').some(el => el.value === fp.id));
      $('#craftBasePreviewBox').innerHTML = renderCraftSpecPreview(activeDomain, base, {
        scaleProfile: activeDomain === 'plot_pacing' ? (spec.scale_profile || domSetup.scale_profile) : null,
        fps: pickedFps,
      });
    };
    $('#craftBaseSelect').onchange = () => {
      const base = bases.find(b => b.id === $('#craftBaseSelect').value);
      if (base?.default_knobs) {
        for (const k of singleKnobKeys) {
          const el = $(`#craftKnob_${k}`);
          if (el && base.default_knobs[k]) el.value = base.default_knobs[k];
        }
        if (multiKnobKey) {
          const defs = new Set(base.default_knobs[multiKnobKey] || []);
          $$('#craftSpecForm [name=craftMultiKnob]').forEach(cb => { cb.checked = defs.has(cb.value); });
        }
      }
      paintPreview();
    };
    $$('#craftSpecForm [name=fingerprint_ids]').forEach(cb => { cb.onchange = paintPreview; });
    paintPreview();

    $('#craftSpecForm').onsubmit = e => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const knobsPayload = {};
      for (const k of singleKnobKeys) {
        knobsPayload[k] = $(`#craftKnob_${k}`)?.value || '';
      }
      if (multiKnobKey) {
        knobsPayload[multiKnobKey] = $$('#craftSpecForm [name=craftMultiKnob]:checked').map(el => el.value);
      }
      const payload = {
        enabled: $('#craftSpecEnabled').checked,
        base_id: $('#craftBaseSelect').value,
        knobs: knobsPayload,
        fingerprint_ids: $$('#craftSpecForm [name=fingerprint_ids]:checked').map(el => el.value),
        custom_notes: String(fd.get('custom_notes') || ''),
      };
      busy(e.target.querySelector('[type=submit]'), async () => {
        data = await api.post(`/novels/${enc(novelId)}/craft-specs/${enc(activeDomain)}`, payload);
        toast(`「${tabMeta.label}」已编译保存，后续对应步骤与 16 步审稿将自动生效`);
        paintTab();
        if (onSaved) await onSaved();
      }).catch(fail);
    };

    if (activeDomain === 'voice' && $('#styleRefMode')) {
      const syncVisibility = () => {
        const m = $('#styleRefMode').value;
        $('#styleSampleFields').style.display = m === 'author_sample' ? '' : 'none';
      };
      $('#styleRefMode').onchange = syncVisibility;
      syncVisibility();

      const submitSample = async (btn, payload) => {
        await busy(btn, async () => {
          await api.post(`/novels/${enc(novelId)}/style-reference`, payload);
          data = await api.get(`/novels/${enc(novelId)}/craft-specs`);
          toast(payload.mode === 'off' ? '已关闭附加样段参照' : '附加样段参照已保存');
          paintTab();
          if (onSaved) await onSaved();
        });
      };
      $('#disableStyleRefBtn').onclick = e => submitSample(e.currentTarget, {
        enabled: false, mode: 'off', title: '', source_note: '', excerpt: '', style_notes: '',
      }).catch(fail);
      $('#styleReferenceForm').onsubmit = e => {
        e.preventDefault();
        const fd = new FormData(e.target);
        const mode = String(fd.get('mode') || 'off');
        submitSample(e.target.querySelector('[type=submit]'), {
          enabled: mode !== 'off',
          mode,
          title: String(fd.get('title') || ''),
          source_note: String(fd.get('source_note') || ''),
          excerpt: String(fd.get('excerpt') || ''),
          style_notes: String(fd.get('style_notes') || ''),
        }).catch(fail);
      };
    }
  };

  try {
    data = await api.get(`/novels/${enc(novelId)}/craft-specs`);
    paintTab();
  } catch (error) {
    $('#drawerBody').innerHTML = `<p class="error">${esc(error.message)}</p>`;
    fail(error);
  }
}

export function openVoiceSpecDrawer(novelId, opts = {}) {
  return openCraftSpecsDrawer(novelId, {initialDomain: 'voice', ...opts});
}

export const openStyleReferenceDrawer = openVoiceSpecDrawer;

export async function openColdReadDrawer(novelId, {sceneId = '', chapterIndex = null, branch = 'main', onCompleted} = {}) {
  drawer('陌生读者冷读（零大纲 · 零设定盲态诊断）', loading());
  const paint = async () => {
    const data = await api.get(`/novels/${enc(novelId)}/cold-reads?${query({scene: sceneId})}`);
    const chapters = data.chapters || [];
    const reports = data.reports || [];
    const defaultChapter = chapterIndex || chapters[0]?.index || 1;
    const lastChapter = chapters.at(-1)?.index || defaultChapter;

    $('#drawerBody').innerHTML = `<div class="stack" style="gap:16px">
      <div class="notice"><strong>严格零剧透盲读隔离：</strong>只把正文（及可选已读前文）交给干净读者模型，<strong>绝不发送</strong>大纲、世界设定、人物卡、Brief 或历史审稿意见。仅诊断不自动改稿、不打分，改不改由你拍板。</div>
      ${data.summary?.recommended ? `<div class="notice warning" style="margin:0"><strong>黄金三章提醒：</strong>${esc(data.summary.recommendation_reason)}</div>` : ''}
      <form id="coldReadForm" class="card stack" style="gap:12px">
        <div class="form-grid">
          <label class="field">
            <span>冷读范围</span>
            <select name="scope" id="coldReadScope">
              ${sceneId ? '<option value="scene" selected>当前单场冷读</option>' : ''}
              <option value="chapter" ${!sceneId ? 'selected' : ''}>整章冷读（合并本章各场）</option>
              <option value="range">多章连读（查弃书点、重复桥段与跨章错位）</option>
            </select>
          </label>
          <label class="field" id="coldReadSingleChBox" style="display:none">
            <span>目标章号</span>
            <select name="chapter_index">
              ${chapters.map(c => `<option value="${c.index}" ${c.index === defaultChapter ? 'selected' : ''}>第${c.index}章 ${esc(c.title || '')}</option>`).join('') || `<option value="${defaultChapter}">第${defaultChapter}章</option>`}
            </select>
          </label>
        </div>
        <div class="form-grid" id="coldReadRangeBox" style="display:none">
          <label class="field">
            <span>起始章</span>
            <select name="chapter_start">
              ${chapters.map(c => `<option value="${c.index}" ${c.index === (chapters[0]?.index || 1) ? 'selected' : ''}>第${c.index}章 ${esc(c.title || '')}</option>`).join('') || '<option value="1">第1章</option>'}
            </select>
          </label>
          <label class="field">
            <span>结束章</span>
            <select name="chapter_end">
              ${chapters.map(c => `<option value="${c.index}" ${c.index === lastChapter ? 'selected' : ''}>第${c.index}章 ${esc(c.title || '')}</option>`).join('') || `<option value="${lastChapter}">第${lastChapter}章</option>`}
            </select>
          </label>
        </div>
        <label class="row" style="gap:8px;font-size:13px">
          <input type="checkbox" name="include_prior_chapters" checked>
          <span>附带读者理应已读过的前文正文（最多 12,000 字，仅正文不含设定）</span>
        </label>
        <label class="field">
          <span>补充关注焦点（可选）</span>
          <input name="custom_focus" placeholder="如：重点看节奏有没有拖沓、爽感给得足不足、对白有没有脾气…">
        </label>
        <div class="row">
          <button type="submit" class="button" id="submitColdReadBtn">立即启动陌生读者冷读</button>
        </div>
      </form>
      <div class="stack" id="coldReadReportsList" style="gap:12px">
        <div class="row spread"><strong>冷读报告记录（${reports.length} 份）</strong></div>
        ${reports.length ? reports.map(renderColdReadReport).join('') : '<p class="muted">当前还没有陌生读者冷读报告。写完一章或一段故事后，点击上方按钮即可发起一次盲态读感诊断。</p>'}
      </div>
    </div>`;

    const syncScope = () => {
      const sc = $('#coldReadScope').value;
      $('#coldReadSingleChBox').style.display = sc === 'chapter' ? '' : 'none';
      $('#coldReadRangeBox').style.display = sc === 'range' ? '' : 'none';
    };
    $('#coldReadScope').onchange = syncScope;
    syncScope();

    $('#coldReadForm').onsubmit = e => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const scope = String(fd.get('scope') || 'scene');
      const payload = {
        scope,
        branch,
        scene_id: sceneId,
        include_prior_chapters: fd.get('include_prior_chapters') === 'on',
        custom_focus: String(fd.get('custom_focus') || '').trim(),
      };
      if (scope === 'chapter') payload.chapter_index = Number(fd.get('chapter_index') || defaultChapter);
      if (scope === 'range') {
        payload.chapter_start = Number(fd.get('chapter_start') || 1);
        payload.chapter_end = Number(fd.get('chapter_end') || lastChapter);
      }
      busy($('#submitColdReadBtn'), async () => {
        const res = await api.post(`/novels/${enc(novelId)}/cold-reads`, payload);
        toast(`陌生读者冷读已完成：${res.report?.label || ''}`);
        await paint();
        if (onCompleted) await onCompleted();
      }).catch(fail);
    };
  };
  try {
    await paint();
  } catch (error) {
    $('#drawerBody').innerHTML = `<p class="error">${esc(error.message)}</p>`;
    fail(error);
  }
}
