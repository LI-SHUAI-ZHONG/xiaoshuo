import {api, query, enc} from '../api.js';
import {$, $$, esc, icon, modal, drawer, loading, fail, toast, busy, readable} from '../ui.js';
import {STEPS, stepsBar, FlatOptionSection, autoCapabilitiesHtml, selectionLimit, slotName} from '../components/WizardStep.js';
import {METHOD_PREFERENCE_LIMIT, methodChoices} from './wizard-methods.js';
import {lengthFields, lengthSummary, readLengthFields, readTierRecommendation} from '../components/LengthPlan.js';

const fields = {tone:'tone_ids', style:'style_ids', narration:'narration_ids', world:'world_ids',
  character:'character_ids', structure:'structure_ids', hook:'mechanism_ids'};
let session = 0;

function chooseMode(prefill) {
  modal('新建小说', `<div class="stack">
    <p class="muted">本工具由 <strong>15,375 条内置工作流规则</strong> 自动保障基础写作能力（主角/配角防工具化、人物关系网、伏笔回收、受限 POV、独立审稿），立项只需决定本作的<strong>差异化题材边界与写法方向</strong>：</p>
    <div class="option-grid">
      <article class="card"><h3>人工选择（4 步快速配置）</h3><p class="muted">选定题材篇幅 → 平铺直选架构与卖点 → 视角与文风（可选挂载参考拆解方法）→ 填写核心构想直接开写。</p></article>
      <article class="card"><h3>AI 自动（一键直出方向）</h3><p class="muted">只需选定题材（可附篇幅与一句话方向），自动配齐本类型架构文风并挂载已有同类型参考方法，不因缺参考书卡死。</p></article>
    </div>
  </div>`, `
    <button class="secondary" data-wizard-mode="manual">人工选择（4 步）</button>
    <button class="button" data-wizard-mode="auto">AI 自动开写</button>`);
  $$('#modalFooter [data-wizard-mode]').forEach(button => {
    button.onclick = () => openWizard({mode:button.dataset.wizardMode, prefill});
  });
}

export async function openWizard({mode, prefill} = {}) {
  const token = ++session;
  if (!mode) { chooseMode(prefill); return; }
  const auto = mode === 'auto';
  const dialog = modal(auto ? '新建小说 · AI 自动' : '新建小说 · 4 步快速立项', loading(), '', true);
  const known = new Map(), selectedMethods = new Map();
  const chosen = {};
  let step = 0, revision = 0, selectedMain = '', selectedSub = '';
  let secondary = [], genres = [], combinations = [];
  let title = '', idea = '', constraints = '', lengthPlan = {length_mode:'tiered'};
  let directionReview = true, strictCorpusAuto = false, submitting = false;
  let limits = {}, defaultBudget = {}, tierRecommendation = null;
  let setupProfile = null, handoffAudit = null;

  const alive = () => token === session && dialog.open;
  const currentStep = () => STEPS[step] || STEPS[0];
  const types = () => [selectedMain, selectedSub, ...secondary].filter(Boolean);
  const flatGenres = () => genres.flatMap(genre => [genre, ...genre.children]);
  const names = () => types().map(id => flatGenres().find(genre => genre.id === id)?.name || id).join(' › ');
  const selections = slot => chosen[slot] || [];
  const limitFor = slot => limits[slot] || 10;
  const canPick = (slot, key) => selections(slot).includes(key) || selections(slot).length < limitFor(slot);
  const repainted = () => paint().catch(fail);

  function rememberProfile(profile) {
    if (!profile?.sections) return;
    for (const list of Object.values(profile.sections)) {
      for (const item of list || []) known.set(item.key, item);
    }
  }

  function toggle(slot, key) {
    // Enforce mutual exclusion of single vs multi POV immediately in UI
    if (key === 'structure.NARRATIVE_STRUCTURE_SINGLE_POV' && selections('structure').includes('structure.NARRATIVE_STRUCTURE_MULTI_POV')) {
      chosen.structure = selections('structure').filter(x => x !== 'structure.NARRATIVE_STRUCTURE_MULTI_POV');
    } else if (key === 'structure.NARRATIVE_STRUCTURE_MULTI_POV' && selections('structure').includes('structure.NARRATIVE_STRUCTURE_SINGLE_POV')) {
      chosen.structure = selections('structure').filter(x => x !== 'structure.NARRATIVE_STRUCTURE_SINGLE_POV');
    }
    if (!canPick(slot, key)) { toast(`${slotName(slot)}最多选 ${limitFor(slot)} 项，请先取消一项。`, true); return; }
    const items = selections(slot);
    chosen[slot] = items.includes(key) ? items.filter(item => item !== key) : [...items, key];
  }

  function allPickedSummary() {
    const picked = Object.keys(fields).flatMap(slot => selections(slot).map(k => known.get(k)?.name || k));
    return picked.length ? picked.slice(0, 6).join('、') + (picked.length > 6 ? ` 等 ${picked.length} 项` : '') : names();
  }

  function footer(pending = false) {
    const stepMeta = currentStep();
    const isFirst = step === 0;
    const isLast = stepMeta.id === 'confirm';
    const disabled = pending || submitting || !selectedMain;
    const unavailable = disabled ? 'disabled' : '';
    $('#modalFooter').innerHTML = `<div class="wizard-selection">${isFirst ? '已选类型' : '已定创作配置'} <strong>${esc(isFirst ? names() : allPickedSummary())}</strong></div>
      ${step && !auto ? '<button class="secondary" id="wizardPrev">上一步</button>' : '<button class="secondary" data-close-modal>取消</button>'}
      ${!auto && !isFirst && !isLast ? '<button class="ghost" id="wizardSkip">跳过此步</button>' : ''}
      ${auto || isLast ? `<button class="button" id="wizardNext" ${unavailable}>${auto ? '生成方向与故事大纲' : '确认并生成故事大纲'} ${icon('arrow')}</button>`
        : `<button class="button" id="wizardNext" ${unavailable}>下一步：${STEPS[step + 1].name} ${icon('arrow')}</button>`}`;
    const move = delta => {
      if (submitting) return;
      if (stepMeta.id === 'genre' && delta > 0) {
        const invalid = $('#modalBody [data-length-field]:invalid,#modalBody [data-budget-field]:invalid');
        if (invalid) {
          const group = invalid.closest('details');
          if (group) group.open = true;
          invalid.reportValidity();
          return;
        }
      }
      capture();
      step = Math.max(0, Math.min(STEPS.length - 1, step + delta));
      repainted();
    };
    $('#wizardPrev')?.addEventListener('click', () => move(-1));
    $('#wizardSkip')?.addEventListener('click', () => move(1));
    $('#wizardNext').onclick = auto ? event => submitAuto(event.currentTarget)
      : isLast ? event => submitManual(event.currentTarget) : () => move(1);
  }

  function capture() {
    if ($('#wizardTitle')) title = $('#wizardTitle').value.trim();
    if ($('#wizardIdea')) idea = $('#wizardIdea').value.trim();
    if ($('#wizardConstraints')) constraints = $('#wizardConstraints').value.trim();
    if ($('#wizardDirectionReview')) directionReview = $('#wizardDirectionReview').checked;
    if ($('#wizardStrictCorpusAuto')) strictCorpusAuto = $('#wizardStrictCorpusAuto').checked;
    if ($('#modalBody [data-tier-mode]')) lengthPlan = readLengthFields($('#modalBody'));
  }

  async function paint() {
    const current = ++revision;
    const stepMeta = currentStep();
    $('#modalTitle').textContent = auto ? '新建小说 · AI 自动开写' : `新建小说 · ${step + 1}/${STEPS.length} ${stepMeta.name}`;
    $('#modalBody').innerHTML = (auto ? '' : stepsBar(step)) + loading();
    $('#modalBody').scrollTop = 0;
    footer(true);
    try {
      const selectedTypes = types();
      const [profileData, tierData, auditData] = await Promise.all([
        selectedTypes.length ? api.get(`/wizard/setup-profile?${query({types:selectedTypes})}`) : null,
        selectedTypes.length && (auto || stepMeta.id === 'genre') ? readTierRecommendation(selectedTypes).catch(() => null) : null,
        selectedTypes.length && (auto || stepMeta.id === 'confirm') ? api.get(`/kb/handoff-audit?${query({types:selectedTypes, planning_hierarchy:1})}`).catch(() => null) : null,
      ]);
      if (!alive() || current !== revision) return;
      setupProfile = profileData;
      rememberProfile(setupProfile);
      if (tierData) tierRecommendation = tierData;
      handoffAudit = auditData;
      render();
    } catch (error) {
      if (!alive() || current !== revision) return;
      $('#modalBody').innerHTML = `${auto ? '' : stepsBar(step)}<p class="error">${esc(error.message)}</p><button class="secondary" id="wizardRetry">重试</button>`;
      $('#wizardRetry').onclick = repainted;
      throw error;
    }
  }

  function render() {
    if (auto) paintAuto();
    else {
      const stepId = currentStep().id;
      if (stepId === 'genre') paintGenreAndLength();
      else if (stepId === 'architecture') paintArchitecture();
      else if (stepId === 'craft') paintCraftAndMethods();
      else paintConfirm();
    }
    footer();
    bindCommonEvents();
  }

  function bindCommonEvents() {
    $$('#modalBody [data-option]').forEach(button => button.onclick = () => {
      capture();
      const key = button.dataset.option;
      const slot = button.dataset.slot || known.get(key)?.slot || '';
      if (!slot) return;
      toggle(slot, key);
      render();
    });
    $$('[data-wizard-method]').forEach(button => button.onclick = () => {
      const pool = setupProfile?.available_corpus_methods || [];
      const method = pool.find(row => row.id === button.dataset.wizardMethod);
      if (!method) return;
      capture();
      if (selectedMethods.has(method.id)) selectedMethods.delete(method.id);
      else {
        if (selectedMethods.size >= METHOD_PREFERENCE_LIMIT) {
          toast(`最多挂载 ${METHOD_PREFERENCE_LIMIT} 条参考拆解方法`, true);
          return;
        }
        selectedMethods.set(method.id, {id:method.id, version:method.version, slot:method.slot, title:method.title, uses:method.uses || []});
      }
      render();
    });
    $$('[data-remove-wizard-method]').forEach(button => button.onclick = () => {
      capture();
      selectedMethods.delete(button.dataset.removeWizardMethod);
      render();
    });
    $$('[data-wizard-nav-link]').forEach(link => link.onclick = () => dialog.close());
  }

  function genrePickerHtml() {
    const current = genres.find(genre => genre.id === selectedMain);
    const atLimit = types().length >= limits.genre;
    const secondaryLimit = Math.min(2, limits.genre - 1 - Number(Boolean(selectedSub)));
    return `<div id="wizardTypeSelection">
      <div class="row spread"><h2>选择小说题材</h2><input id="genreSearch" placeholder="搜索类型…" aria-label="搜索类型"></div>
      <p class="muted">主类型 1 项 + 子类型最多 1 项 + 副类型最多 2 项（共最多 ${limits.genre} 项）；选定后自动锁定本类型的规则范围、典型资源与跨题材防污染边界。</p>
      <div class="genre-layout">
        <div class="genre-list" id="genreList">${genres.map(genre => `<button type="button" data-main="${esc(genre.id)}" class="${genre.id === selectedMain ? 'active' : ''}" aria-pressed="${genre.id === selectedMain}">${esc(genre.name)} <small class="faint">${genre.children.length}</small></button>`).join('')}</div>
        <div><div class="row spread" style="margin-bottom:16px"><h3>${esc(current?.name || '选择主类型')}</h3>
          ${current ? `<button type="button" class="ghost" data-genre-info="${esc(current.id)}">${icon('info')} 类型定义</button>` : ''}</div>
          <div class="option-grid" id="subgenres">${(current?.children || []).map(genre => `
            <div class="option-card ${selectedSub === genre.id ? 'selected' : ''}">
              <button type="button" class="rec-pick grow" data-sub="${esc(genre.id)}" aria-pressed="${selectedSub === genre.id}"
                ${selectedSub !== genre.id && (selectedSub || atLimit) ? 'disabled' : ''}><h3>${esc(genre.name)}</h3><p>${esc(genre.definition || '定义待补充')}</p></button>
              <button type="button" class="icon-button" data-genre-info="${esc(genre.id)}" aria-label="查看${esc(genre.name)}详情">${icon('info')}</button>
            </div>`).join('') || (current ? '<p class="muted">此主类型暂无细分类型。</p>' : '')}</div>
        </div>
      </div>
      <div class="divider"></div>
      <div class="row wrap"><span class="muted">副类型（当前最多 ${secondaryLimit} 项）</span>
        ${secondary.map(id => `<span class="selection-chip">${esc(flatGenres().find(genre => genre.id === id)?.name || id)}<button type="button" data-remove-secondary="${esc(id)}" aria-label="移除副类型">×</button></span>`).join('')}
        <select id="secondaryGenre" aria-label="添加副类型" ${!selectedMain || secondary.length >= secondaryLimit ? 'disabled' : ''}><option value="">＋ 添加副类型</option>
          ${flatGenres().filter(genre => !types().includes(genre.id) && (!genre.parent_id || secondary.includes(genre.parent_id)))
            .map(genre => `<option value="${esc(genre.id)}">${esc(genre.name)}</option>`).join('')}
        </select></div>${selectionLimit(types().length, limits.genre)}
      <p class="wizard-description" id="compatibility">${compatibilityText()}</p>
    </div>`;
  }

  function bindGenrePicker() {
    $('#genreSearch')?.addEventListener('input', event => {
      const term = event.target.value.trim();
      $$('[data-main]').forEach(button => {
        const genre = genres.find(row => row.id === button.dataset.main);
        button.hidden = term && ![genre, ...genre.children].some(row => row.name.includes(term));
      });
      $$('#subgenres .option-card').forEach(card => card.hidden = term && !card.textContent.includes(term));
    });
    $$('[data-main]').forEach(button => button.onclick = () => {
      if (button.dataset.main === selectedMain) return;
      capture();
      selectedMain = button.dataset.main; selectedSub = '';
      secondary = secondary.filter(id => id !== selectedMain && flatGenres().find(row => row.id === id)?.parent_id !== selectedMain);
      repainted();
    });
    $$('[data-sub]').forEach(button => button.onclick = () => {
      capture();
      const atLimit = types().length >= limits.genre;
      if (button.dataset.sub === selectedSub) selectedSub = '';
      else if (!selectedSub && !atLimit) selectedSub = button.dataset.sub;
      repainted();
    });
    $('#secondaryGenre')?.addEventListener('change', event => {
      capture();
      const secondaryLimit = Math.min(2, limits.genre - 1 - Number(Boolean(selectedSub)));
      if (event.target.value && secondary.length < secondaryLimit) { secondary.push(event.target.value); repainted(); }
    });
    $$('[data-remove-secondary]').forEach(button => button.onclick = () => {
      capture();
      const remove = button.dataset.removeSecondary;
      secondary = secondary.filter(id => id !== remove && flatGenres().find(row => row.id === id)?.parent_id !== remove);
      repainted();
    });
    $$('[data-genre-info]').forEach(button => button.onclick = () => showGenre(button.dataset.genreInfo));
  }

  function paintAuto() {
    const corpusCount = setupProfile?.available_corpus_methods?.length || 0;
    const defaults = setupProfile?.ai_auto_defaults || {};
    const defaultLabels = ['structure_ids', 'mechanism_ids', 'tone_ids', 'style_ids']
      .flatMap(f => (defaults[f] || []).map(id => [...known.values()].find(v => v.id === id)?.name || id));
    const ar = handoffAudit?.auto_readiness;
    const statusCard = selectedMain ? `<section class="card stack" id="wizardAutoReadiness" style="margin-bottom:14px">
      <div class="row spread wrap">
        <strong>AI 自动运行引擎状态（内置工作流主驱 + 拆解方法自动增强）</strong>
        <span class="tag green">立即可启动 · 内置 15,375 条规则已就绪</span>
      </div>
      <p class="muted">AI 将按所选类型自动配齐差异化架构与文风${defaultLabels.length ? `（建议默认：<strong>${esc(defaultLabels.join(' / '))}</strong>）` : ''}，并自动挂载当前资料库中可用的同类型拆解方法（当前 <strong>${corpusCount} 条</strong>可用；无拆解书时依然可基于内置工作流高质量开写）。</p>
      ${corpusCount === 0 ? '<p class="muted">提示：若希望融入某本参考小说的具体写法，随时可前往 <a class="text-link" href="#/staging" data-wizard-nav-link>预存库 → 精准步骤拆解</a>（约 7–10 次调用自动核验入库）。</p>' : ''}
      ${ar?.checked && ar.ready ? `<p class="muted">同类型 7 大板块参考方法已齐备（${ar.ready_count}/${ar.total_boards}），将自动启用完整参考方法路线。</p>` : ''}
    </section>` : '';

    $('#modalBody').innerHTML = `
      <p id="wizardAutoError" class="error" role="alert" tabindex="-1" hidden></p>
      ${statusCard}
      ${genrePickerHtml()}
      ${selectedMain ? `<div class="divider"></div>
        <section class="stack" style="margin-top:12px">
          <h3>可选 · 给 AI 指定篇幅或一句话灵感（全部留空则由 AI 自主构思）</h3>
          ${lengthFields(lengthPlan, tierRecommendation, defaultBudget)}
          <label class="field"><span>暂定书名（选填）</span><input id="wizardTitle" maxlength="120" placeholder="留空自动命名" value="${esc(title)}"></label>
          <label class="field"><span>一句话故事灵感 / 想看的卖点（选填）</span><textarea id="wizardIdea" rows="3" maxlength="12000" placeholder="例如：想写一个靠残缺古骨在宗门底层破局的冷静主角，节奏明快，重智斗与代价…（留空则由 AI 原创构思）">${esc(idea)}</textarea></label>
          <label class="field"><span>硬约束（选填）</span><textarea id="wizardConstraints" rows="2" maxlength="12000" placeholder="如：单女主、不圣母、无后宫、严禁系统面板…">${esc(constraints)}</textarea></label>
        </section>
        ${autoCapabilitiesHtml(setupProfile?.auto_enforced_capabilities, setupProfile?.genre_scope)}
        <details class="details" style="margin-top:12px">
          <summary>高级 · 严格参考书模式（仅当要求 7 大板块全部来自参考书拆解时勾选）</summary>
          <label class="check-row" style="margin-top:8px"><input type="checkbox" id="wizardStrictCorpusAuto" ${strictCorpusAuto ? 'checked' : ''}> 强制要求同类型全部 7 大板块均具备已批准拆解方法才允许启动（缺项则阻断提示补拆）</label>
        </details>` : ''}`;
    bindGenrePicker();
  }

  function paintGenreAndLength() {
    $('#modalBody').innerHTML = stepsBar(step) + genrePickerHtml() + `
      <div class="divider"></div>
      <section aria-label="篇幅计划" style="margin-top:12px">
        <h3>目标篇幅档位</h3>
        ${lengthFields(lengthPlan, tierRecommendation, defaultBudget)}
      </section>
      ${autoCapabilitiesHtml(setupProfile?.auto_enforced_capabilities, setupProfile?.genre_scope)}`;
    bindGenrePicker();
  }

  function paintArchitecture() {
    const sections = setupProfile?.sections || {};
    const scope = setupProfile?.genre_scope || {};
    const plotFocus = scope.plot_focus || {};
    $('#modalBody').innerHTML = stepsBar(step) + `
      <div class="row spread wrap"><h2>故事架构、卖点与特色机制</h2><span class="tag blue">直接驱动 03 世界 / 06 大纲 / 07 事件</span></div>
      <p class="wizard-description">基于 <strong>${esc(names())}</strong> —— 只需点选决定本作特色的结构与核心推进机制；主角/配角体系、人物关系网、基础世界观、黄金三章与伏笔回收已由引擎自动保障，无需手动勾选。</p>
      ${plotFocus.arc_pattern ? `<div class="notice"><strong>本类型架构提示</strong>：${esc(plotFocus.arc_pattern)}${plotFocus.hook_foreshadow_pattern ? ` ｜ <strong>钩子重点</strong>：${esc(plotFocus.hook_foreshadow_pattern)}` : ''}</div>` : ''}
      ${FlatOptionSection({id:'structures', title:'1. 叙事结构框架（直接点选，单/多视角互斥）', hint:`最多选 ${limitFor('structure')} 项；不选则由大纲步骤按本类型默认推进。`, items:sections.structures || [], selectedForSlot:selections, limitForSlot:limitFor})}
      ${FlatOptionSection({id:'mechanisms', title:'2. 核心推进机制与卖点（直接点选）', hint:`最多选 ${limitFor('hook')} 项；本类型核心卖点已置顶。`, items:sections.mechanisms || [], selectedForSlot:selections, limitForSlot:limitFor})}
      ${FlatOptionSection({id:'special_mechanisms', title:'3. 特殊世界 / 金手指 / 危机机制（系统、血脉、无限流、副本等）', hint:'仅当故事明确带有特殊顶层机制或金手指时勾选；常规世界观与人物能力由引擎按类型自动生成。', items:sections.special_mechanisms || [], selectedForSlot:selections, limitForSlot:limitFor, collapsedAll:true})}`;
  }

  function paintCraftAndMethods() {
    const sections = setupProfile?.sections || {};
    const craftFocus = setupProfile?.genre_scope?.craft_focus || {};
    const methods = setupProfile?.available_corpus_methods || [];
    const methodsHtml = `<section class="method-section" style="margin-top:18px" aria-label="可选参考书拆解方法">
      <div class="row spread wrap"><h3>4. 可选 · 挂载同类型参考书拆解方法</h3><span class="tag">${methods.length ? `${methods.length} 条可用` : '暂无（不影响开写）'}</span></div>
      ${methods.length ? `<p class="muted">勾选后将把对应参考写法精准绑定到下游制作步骤（完全可选，最多 ${METHOD_PREFERENCE_LIMIT} 条）。</p>
        <div class="rec-grid">${methods.map(m => {
          const active = selectedMethods.has(m.id);
          const targets = (m.uses || []).map(u => `${u.scope_name}·${u.stage_name}`).filter((v, i, a) => a.indexOf(v) === i).join('、');
          return `<article class="rec-card ${active ? 'selected' : ''}">
            <h4>${esc(m.title)} · v${m.version}</h4>
            <p class="muted">${targets ? `绑定步骤：${esc(targets)}` : ''}</p>
            <p>${(m.applicability || []).map(esc).join('。')}</p>
            <button type="button" class="secondary" data-wizard-method="${esc(m.id)}" aria-pressed="${active}">${active ? '取消挂载' : '挂载此写法'}</button>
          </article>`;
        }).join('')}</div>`
        : '<p class="muted">当前类型尚无已入库的参考书拆解方法。内置 15,375 条工作流规则已足以直接高质量创作；如需学习某本参考书写法，可随时在 <a class="text-link" href="#/staging" data-wizard-nav-link>预存库 → 精准步骤拆解</a> 一键拆解入库。</p>'}
    </section>`;

    $('#modalBody').innerHTML = stepsBar(step) + `
      <div class="row spread wrap"><h2>叙事视角、语气文风与参考写法</h2><span class="tag blue">直接驱动 09 场景 / 13 表达 / 15 写作</span></div>
      <p class="wizard-description">基于 <strong>${esc(names())}</strong> —— 选定本作的叙述人称、语气基调与语言质感；身体动作锚点、潜台词对白、受限 POV 防越界与审稿红线均自动生效。</p>
      ${craftFocus.expression_focus ? `<div class="notice"><strong>本类型表达重点</strong>：${esc(craftFocus.expression_focus)}</div>` : ''}
      ${FlatOptionSection({id:'tones', title:'1. 语气基调（10 类直选）', hint:`最多选 ${limitFor('tone')} 项，本类型核心语气已置顶。`, items:sections.tones || [], selectedForSlot:selections, limitForSlot:limitFor})}
      ${FlatOptionSection({id:'styles', title:'2. 文风与语言质感（20 类直选）', hint:`最多选 ${limitFor('style')} 项；若同时选竞争文风，表达步骤会自动分配到不同场景节拍。`, items:sections.styles || [], selectedForSlot:selections, limitForSlot:limitFor})}
      ${FlatOptionSection({id:'viewpoint', title:'3. 叙事人称、距离与时序偏好', hint:'仅在需要明确指定人称形态（第一/第三人称有限）、不可靠叙述或插叙/倒叙时勾选。', items:sections.viewpoint_choices || [], selectedForSlot:selections, limitForSlot:limitFor, collapsedAll:true})}
      ${methodsHtml}`;
  }

  function paintConfirm() {
    const pickedRows = [
      ['叙事结构', selections('structure')],
      ['核心推进机制', selections('hook')],
      ['特殊世界/人物机制', [...selections('world'), ...selections('character')]],
      ['视角与时序', selections('narration')],
      ['语气基调', selections('tone')],
      ['文风质感', selections('style')],
    ].map(([label, keys]) => `<dt>${label}</dt><dd>${esc(keys.map(k => known.get(k)?.name || k).join('、') || '按本类型工作流自动展开')}</dd>`).join('');

    const currentVersions = Object.fromEntries((setupProfile?.available_corpus_methods || []).map(m => [m.id, m.version]));
    $('#modalBody').innerHTML = stepsBar(step) + `<div class="wizard-confirm">
      <h2>填写故事构想并确认开写</h2>
      <div class="card"><dl class="selection-summary">
        <dt>题材边界</dt><dd>${esc(names())}</dd>
        ${lengthSummary(lengthPlan, tierRecommendation?.tiers)}
        ${pickedRows}
        <dt>基础写作能力</dt><dd>已自动启用（主角/配角防工具化、关系网、黄金三章/伏笔回收、受限 POV、独立审稿）</dd>
      </dl></div>
      ${methodChoices(selectedMethods, currentVersions)}
      <div class="divider"></div>
      <div class="stack">
        <label class="field"><span>小说书名</span><input id="wizardTitle" maxlength="120" placeholder="给故事起一个暂定书名" value="${esc(title)}"></label>
        <label class="field"><span>一句话故事构想 <span class="error">*</span></span><textarea id="wizardIdea" rows="4" maxlength="12000" required placeholder="谁，在什么处境下，为了什么目标，必须做出怎样的选择？">${esc(idea)}</textarea></label>
        <label class="field"><span>硬约束（选填）</span><textarea id="wizardConstraints" rows="3" maxlength="12000" placeholder="必须保留的设定、不能发生的情节、阅读对象…">${esc(constraints)}</textarea></label>
        <label class="check-row"><input type="checkbox" id="wizardDirectionReview" ${directionReview ? 'checked' : ''}> 先生成 2–3 份全书方向与故事大纲供对比选择（若已在构想中写明完整方向，取消勾选则直接展开设定与全书大纲）</label>
        <div class="notice">
          <p><strong>实际创作工作流（默认启用 · 内置规则主驱）</strong>：立项选定的题材边界与写法偏好由程序自动冻结并继承至卷纲与每一章，不再重复空转「类型判定 / 类型适配」；也不会因缺少参考书拆解而卡死，直接推进<strong>全书方向与故事大纲 → 世界与人物定稿 → 卷纲逐章切分 → 章细纲与场景包 → 正文写审接受</strong>。</p>
        </div>
      </div>
    </div>`;
  }

  function compatibilityText() {
    if (!secondary.length) return '可选副类型。';
    const selected = types();
    const matching = combinations.filter(row => Array.isArray(row.types) && row.types.length > 1
      && row.types.every(id => selected.includes(id)) && secondary.some(id => row.types.includes(id)));
    const review = '多类型组合会在全书设计中做融合边界校核。';
    return matching.length ? review + matching.map(row => esc((String(row.status).toLowerCase().includes('blocked') ? '不兼容警告 · ' : '')
      + (row.description || row.name || '已有组合资料'))).join('。') : review;
  }

  async function showGenre(id) {
    drawer('类型图鉴', loading());
    try {
      const genre = flatGenres().find(row => row.id === id);
      const data = await api.get(`/kb/types/${enc(id)}`);
      $('#drawerBody').innerHTML = `<h2>${esc(genre?.name || id)}</h2><div class="divider"></div>${readable(data.type || data)}<a class="secondary" href="#/atlas/${enc(id)}" id="openAtlas">打开完整图鉴</a>`;
      $('#openAtlas').onclick = () => { $('#drawer').close(); dialog.close(); };
    } catch {
      $('#drawerBody').innerHTML = '<p class="muted">类型定义待补充，可以在知识库维护。</p>';
    }
  }

  async function createNovel(payload) {
    const result = await api.post('/novels', {
      direction_review:true, planning_hierarchy:true, creative_workflow:true,
      method_policy_mode:'builtin_enhanced', ...payload,
    });
    const novel = result.novel || result;
    if (!novel.id) throw new Error('项目创建结果没有返回作品标识');
    const active = alive();
    if (active) dialog.close();
    document.dispatchEvent(new CustomEvent('studio:created', {bubbles:true}));
    if (active) location.hash = `#/studio/${enc(novel.id)}`;
    toast(result.run?.reason || '立项卡已保存');
  }

  async function submitAuto(button) {
    if (submitting || !selectedMain) return;
    capture();
    const errorMessage = $('#wizardAutoError');
    const typeSelection = $('#wizardTypeSelection');
    if (errorMessage) errorMessage.hidden = true;
    submitting = true;
    if (typeSelection) typeSelection.inert = true;
    try {
      await busy(button, async () => {
        try {
          const payload = {
            design_mode:'auto',
            genre_ids:types(),
            auto_length:true,
            ...Object.fromEntries(Object.entries(lengthPlan).filter(([,value]) => value != null)),
            ...(title ? {title} : {}),
            ...(idea ? {idea} : {}),
            ...(constraints ? {constraints} : {}),
          };
          if (strictCorpusAuto) {
            Object.assign(payload, {auto_recommendations:true, method_policy_mode:'strict_corpus'});
          } else {
            Object.assign(payload, {auto_recommendations:false, method_policy_mode:'builtin_enhanced'});
          }
          await createNovel(payload);
        } catch (error) {
          if (!alive()) return;
          if (errorMessage) {
            errorMessage.hidden = false;
            errorMessage.textContent = error.message.replace(/^AUTO_RECOMMENDATIONS_MISSING[：:]\s*/, '');
            errorMessage.focus();
          } else {
            fail(error);
          }
        }
      });
    } finally {
      submitting = false;
      if (typeSelection) typeSelection.inert = false;
    }
  }

  async function submitManual(button) {
    if (submitting) return;
    capture();
    if (!idea) { $('#wizardIdea')?.focus(); toast('请先填写一句话故事构想', true); return; }
    const payload = {
      title:title || '未命名小说', idea, constraints, genre_ids:types(),
      design_mode:'manual',
      method_policy_mode:'builtin_enhanced',
      direction_review: $('#wizardDirectionReview')?.checked ?? true,
      method_preferences:[...selectedMethods.values()].map(({id, version, slot}) => ({id, version, slot})),
      choices:types().map(id => ({slot:'genre', option_key:'genre.' + id})),
      auto_length:true,
      ...Object.fromEntries(Object.entries(lengthPlan).filter(([,value]) => value != null)),
    };
    for (const [slot, field] of Object.entries(fields)) {
      payload[field] = selections(slot);
      payload.choices.push(...selections(slot).map(option_key => ({slot, option_key})));
    }
    submitting = true;
    try {
      await busy(button, () => createNovel(payload));
    } finally {
      submitting = false;
    }
  }

  try {
    const data = await api.get('/genres');
    if (!alive()) return;
    genres = data.genres || [];
    combinations = data.combinations || [];
    limits = data.selection_limits;
    defaultBudget = data.default_budget;
    const genre = flatGenres().find(row => row.id === prefill);
    selectedMain = genre?.parent_id || genre?.id || (auto ? '' : genres[0]?.id) || '';
    selectedSub = genre?.parent_id ? genre.id : '';
    repainted();
  } catch (error) {
    if (!alive()) return;
    $('#modalBody').innerHTML = `<p class="error">${esc(error.message)}</p>`;
    $('#modalFooter').innerHTML = '<button class="secondary" data-close-modal>关闭</button>';
    fail(error);
  }
}
