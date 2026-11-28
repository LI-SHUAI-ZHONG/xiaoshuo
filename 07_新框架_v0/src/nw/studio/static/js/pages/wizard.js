import {api, query, enc} from '../api.js';
import {$, $$, esc, icon, modal, drawer, loading, fail, toast, busy, readable} from '../ui.js';
import {STEPS, stepsBar, WizardStep, OptionCard, selectionLimit, slotName} from '../components/WizardStep.js';
import {wizardMethods} from './project-methods.js';
import {METHOD_PREFERENCE_LIMIT, methodChoices, methodRecommendations} from './wizard-methods.js';
import {lengthFields, lengthSummary, readLengthFields, readTierRecommendation} from '../components/LengthPlan.js';
import {readCastSamples, castSamplesHtml} from '../components/CastSamples.js';

const fields = {tone:'tone_ids', style:'style_ids', narration:'narration_ids', world:'world_ids',
  character:'character_ids', structure:'structure_ids', hook:'mechanism_ids'};
let session = 0;

function chooseMode(prefill) {
  modal('新建小说', '<p>选择创作方式</p>', `
    <button class="secondary" data-wizard-mode="manual">人工选择</button>
    <button class="button" data-wizard-mode="auto">AI 自动</button>`);
  $$('#modalFooter [data-wizard-mode]').forEach(button => {
    button.onclick = () => openWizard({mode:button.dataset.wizardMode, prefill});
  });
}

export async function openWizard({mode, prefill} = {}) {
  const token = ++session;
  if (!mode) { chooseMode(prefill); return; }
  const auto = mode === 'auto';
  const dialog = modal(auto ? '新建小说 · AI 自动' : '新建小说', loading(), '', true);
  const known = new Map(), selectedMethods = new Map();
  const chosen = {};
  let step = prefill && !auto ? 1 : 0, revision = 0, selectedMain = '', selectedSub = '';
  let secondary = [], genres = [], combinations = [], options = [], methods = [], currentVersions = {}, totalMethods = null;
  let title = '', idea = '', constraints = '', lengthPlan = {length_mode:'tiered'};
  let directionReview = true, applyTasks = false, selectedTasks = new Set(['world_rules']);
  let limits = {}, defaultBudget = {}, bookWorldAvailable = false, submitting = false;
  let tierRecommendation = null;
  let castSamples = null;
  let handoffAudit = null;
  let worldBlueprint = null;
  let characterBlueprint = null;
  let plotBlueprint = null;
  let craftBlueprint = null;

  const alive = () => token === session && dialog.open;
  const currentStep = () => STEPS[step] || STEPS[0];
  const currentSlot = () => currentStep().slot;
  const types = () => [selectedMain, selectedSub, ...secondary].filter(Boolean);
  const flatGenres = () => genres.flatMap(genre => [genre, ...genre.children]);
  const names = () => types().map(id => flatGenres().find(genre => genre.id === id)?.name || id).join(' › ');
  const selections = slot => chosen[slot] || [];
  const canPick = (slot, key) => selections(slot).includes(key) || selections(slot).length < limits[slot];
  const staleMethods = () => [...selectedMethods.values()].some(method => currentVersions[method.id] !== method.version);
  const repainted = () => paint().catch(fail);

  function rememberOptions(items) {
    for (const option of items) {
      known.set(option.key || option.id, option);
      rememberOptions(option.children || []);
    }
  }

  function toggle(slot, key) {
    if (!canPick(slot, key)) { toast(`${slotName(slot)}最多选 ${limits[slot]} 项，请先取消一项。`, true); return; }
    const items = selections(slot);
    chosen[slot] = items.includes(key) ? items.filter(item => item !== key) : [...items, key];
  }

  function footer(pending = false) {
    const slot = currentSlot();
    const isGenre = slot === 'genre';
    const isStructure = slot === 'structure';
    const last = slot === 'confirm';
    const summary = isGenre ? names() : selections(slot).map(key => known.get(key)?.name || key).join('、') || names();
    const disabled = pending || submitting || (isGenre && !selectedMain) || (last && staleMethods());
    const unavailable = disabled ? 'disabled' : '';
    $('#modalFooter').innerHTML = `<div class="wizard-selection">${isGenre ? '已选类型' : '创作偏好'} <strong>${esc(summary)}</strong></div>
      ${step ? '<button class="secondary" id="wizardPrev">上一步</button>' : '<button class="secondary" data-close-modal>取消</button>'}
      ${!isGenre && !last ? '<button class="ghost" id="wizardSkip">跳过此步</button>' : ''}
      ${auto || last ? `<button class="button" id="wizardNext" ${unavailable}>生成方向短案 ${icon('arrow')}</button>`
        : `<button class="button" id="wizardNext" ${unavailable}>下一步：${STEPS[step + 1].name} ${icon('arrow')}</button>`}`;
    const move = delta => {
      if (submitting) return;
      if (isStructure && delta > 0) {
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
      : last ? event => submitManual(event.currentTarget) : () => move(1);
  }

  function capture() {
    const slot = currentSlot();
    if (slot === 'confirm' && $('#wizardTitle')) {
      title = $('#wizardTitle').value.trim();
      idea = $('#wizardIdea').value.trim();
      constraints = $('#wizardConstraints').value.trim();
      if ($('#wizardDirectionReview')) directionReview = $('#wizardDirectionReview').checked;
      if ($('#wizardApplyTasks')) applyTasks = $('#wizardApplyTasks').checked;
      const taskInputs = $$('[name=wizardTask]');
      if (taskInputs.length) selectedTasks = new Set(taskInputs.filter(el => el.checked).map(el => el.value));
    }
    if (slot === 'structure' && $('#modalBody [data-tier-mode]')) {
      lengthPlan = readLengthFields($('#modalBody'));
    }
  }

  async function paint() {
    if (auto) {
      const current = ++revision;
      handoffAudit = null;
      render();
      if (selectedMain) {
        try {
          const audit = await api.get(`/kb/handoff-audit?${query({types:types(), planning_hierarchy:1})}`);
          if (!alive() || current !== revision) return;
          handoffAudit = audit;
          render();
        } catch {/* Keep submission error handling available if audit lookup fails. */}
      }
      return;
    }
    const current = ++revision;
    const stepMeta = currentStep();
    const slot = stepMeta.slot;
    $('#modalTitle').textContent = `新建小说 · ${stepMeta.stage ? `${stepMeta.stage} ` : ''}${stepMeta.name}`;
    $('#modalBody').innerHTML = stepsBar(step) + loading();
    $('#modalBody').scrollTop = 0;
    footer(true);
    try {
      const [library, optionResult, tierData, castData, auditData, worldBpData, charBpData, plotBpData, craftBpData] = await Promise.all([
        api.get(`/kb/method-recommendations?${query({
          slot:slot === 'confirm' ? 'world' : slot, types:types(), selected:[...selectedMethods.keys()], planning_hierarchy:1, limit:12})}`),
        slot !== 'confirm' && slot !== 'genre' ? api.get(`/options?${query({slot, types:types()})}`) : {},
        slot === 'structure' ? readTierRecommendation(types()) : null,
        slot === 'character' ? readCastSamples(types()) : null,
        slot === 'confirm' && types().length ? api.get(`/kb/handoff-audit?${query({types:types(), planning_hierarchy:1})}`).catch(() => null) : null,
        slot === 'world' && types().length ? api.get(`/kb/world-blueprint?${query({types:types()})}`).catch(() => null) : null,
        slot === 'character' && types().length ? api.get(`/kb/character-blueprint?${query({types:types()})}`).catch(() => null) : null,
        (slot === 'structure' || slot === 'hook') && types().length ? api.get(`/kb/plot-blueprint?${query({types:types()})}`).catch(() => null) : null,
        (slot === 'narration' || slot === 'tone' || slot === 'style') && types().length ? api.get(`/kb/craft-blueprint?${query({types:types()})}`).catch(() => null) : null,
      ]);
      if (!alive() || current !== revision) return;
      methods = library.recommendations || [];
      totalMethods = library.total_available ?? null;
      currentVersions = library.current_versions || {};
      if (slot === 'confirm') bookWorldAvailable = library.book_world_available;
      options = optionResult.options || [];
      if (tierData) tierRecommendation = tierData;
      castSamples = castData;
      if (slot === 'confirm') handoffAudit = auditData;
      worldBlueprint = worldBpData || (optionResult.world_profile ? {...optionResult.world_profile, coverage_summary: null} : null);
      characterBlueprint = charBpData || (optionResult.character_profile ? {...optionResult.character_profile, coverage_summary: null} : null);
      plotBlueprint = plotBpData || (optionResult.plot_profile ? {...optionResult.plot_profile, coverage_summary: null} : null);
      craftBlueprint = craftBpData || (optionResult.craft_profile ? {...optionResult.craft_profile, coverage_summary: null} : null);
      rememberOptions(options);
      render();
    } catch (error) {
      if (!alive() || current !== revision) return;
      $('#modalBody').innerHTML = `${stepsBar(step)}<p class="error">${esc(error.message)}</p><button class="secondary" id="wizardRetry">重试</button>`;
      $('#wizardRetry').onclick = repainted;
      throw error;
    }
  }

  function render() {
    const slot = currentSlot();
    if (slot === 'genre') paintGenres();
    else if (slot === 'confirm') paintConfirm();
    else paintOptions();
    footer();
    $('[data-refresh-wizard-methods]')?.addEventListener('click', () => { capture(); repainted(); });
    $$('[data-wizard-method]').forEach(button => button.onclick = () => {
      const method = methods.find(row => row.id === button.dataset.wizardMethod);
      if (!method) return;
      capture();
      const prior = selectedMethods.get(method.id);
      if (prior?.version === method.version) selectedMethods.delete(method.id);
      else {
        if (!prior && selectedMethods.size >= METHOD_PREFERENCE_LIMIT) {
          toast(`最多保存 ${METHOD_PREFERENCE_LIMIT} 条方法偏好`, true);
          return;
        }
        selectedMethods.set(method.id, {id:method.id, version:method.version, slot:STEPS[step].slot, title:method.title, uses:method.uses || []});
        currentVersions[method.id] = method.version;
      }
      render();
    });
    $$('[data-remove-wizard-method]').forEach(button => button.onclick = () => {
      capture();
      selectedMethods.delete(button.dataset.removeWizardMethod);
      render();
    });
    $$('[data-wizard-nav-link]').forEach(link => link.onclick = () => dialog.close());
    $('#syncWizardTasksFromMethods')?.addEventListener('click', () => {
      capture();
      const auditedById = new Map((handoffAudit?.methods || []).map(m => [m.id, m]));
      const next = new Set(['world_rules']);
      for (const m of selectedMethods.values()) {
        for (const task of (auditedById.get(m.id)?.tasks || [])) next.add(task);
      }
      selectedTasks = next;
      applyTasks = true;
      render();
      toast(`已按所选拆解方法同步 ${next.size} 项步骤制作职责`);
    });
  }

  const libraryPanel = () => methodRecommendations(methods, selectedMethods, currentVersions, totalMethods);

  function autoReadinessHtml() {
    if (!auto || !selectedMain || !handoffAudit?.auto_readiness?.checked) return '';
    const ar = handoffAudit.auto_readiness;
    const orig = handoffAudit.originality_audit || {};
    const primary = types()[0] || '';
    return `<section class="card stack" id="wizardAutoReadiness" style="margin-bottom:14px">
      <div class="row spread wrap"><strong>AI 自动下游接收就绪体检（${ar.ready_count}/${ar.total_boards} 大板块已就绪）</strong>
        <span class="tag ${ar.ready ? 'green' : ''}">${ar.ready ? '可立即启动 AI 自动' : `尚缺 ${ar.missing_boards.length} 块`}</span></div>
      <div class="row wrap">${(ar.boards || []).map(b => `<span class="tag ${b.ready ? 'green' : ''}" title="${esc(b.ready ? `${b.route.scope_name}·${b.route.stage_name}` : (b.blocked_reasons || []).join('；'))}">${esc(b.label)} · ${b.ready ? `${esc(b.route.scope_name)}/${esc(b.route.stage_name)}` : '待补'}</span>`).join('')}</div>
      ${!ar.ready ? `<p class="muted">缺少项补齐指引：${(ar.boards || []).filter(b => !b.ready).map(b => `${esc(b.label)}（请拆解 ${(b.suggested_domains || []).map(d => esc(d.name)).join('/')}${b.blocked_reasons?.length ? `；当前受阻：${esc(b.blocked_reasons[0])}` : ''}）`).join('；')}</p>` : ''}
      ${(orig.warnings || []).map(w => `<p class="muted">${esc(w.message)}</p>`).join('')}
      <div class="row wrap"><a class="secondary" href="#/kb/prerequisites?type=${enc(primary)}" data-wizard-nav-link>查看 17 步接收详情</a><a class="ghost" href="#/staging" data-wizard-nav-link>前往预存库拆解补齐</a></div>
    </section>`;
  }

  function paintGenres() {
    const current = genres.find(genre => genre.id === selectedMain);
    const atLimit = types().length >= limits.genre;
    const secondaryLimit = Math.min(2, limits.genre - 1 - Number(Boolean(selectedSub)));
    const intro = auto ? `<p class="wizard-description">AI 从已批准的同类型小说拆解推荐中，按工作流顺序为你选择世界观、人物、结构篇幅、卖点、写法、风格和文笔。齐备后会生成几份全书方向短案，请你选定一个。缺少推荐时，页面会列出缺项。</p>
      <p id="wizardAutoError" class="error" role="alert" tabindex="-1" hidden></p>${autoReadinessHtml()}` : stepsBar(step);
    $('#modalBody').innerHTML = intro + `
      <div id="wizardTypeSelection">
      <div class="row spread"><h2>为故事选择类型</h2><input id="genreSearch" placeholder="搜索类型…" aria-label="搜索类型"></div>
      <p class="muted">主类型选 1 项，主类型下的子类型最多选 1 项。主、子、副类型合计最多选 ${limits.genre} 项。</p>
      ${auto ? '' : libraryPanel()}
      <div class="genre-layout">
        <div class="genre-list" id="genreList">${genres.map(genre => `<button data-main="${esc(genre.id)}" class="${genre.id === selectedMain ? 'active' : ''}" aria-pressed="${genre.id === selectedMain}">${esc(genre.name)} <small class="faint">${genre.children.length}</small></button>`).join('')}</div>
        <div><div class="row spread" style="margin-bottom:16px"><h3>${esc(current?.name || '选择主类型')}</h3>
          ${current ? `<button class="ghost" data-genre-info="${esc(current.id)}">${icon('info')} 类型定义</button>` : ''}</div>
          <div class="option-grid" id="subgenres">${(current?.children || []).map(genre => `
            <div class="option-card ${selectedSub === genre.id ? 'selected' : ''}">
              <button class="rec-pick grow" data-sub="${esc(genre.id)}" aria-pressed="${selectedSub === genre.id}"
                ${selectedSub !== genre.id && (selectedSub || atLimit) ? 'disabled' : ''}><h3>${esc(genre.name)}</h3><p>${esc(genre.definition || '定义待补充')}</p></button>
              <button class="icon-button" data-genre-info="${esc(genre.id)}" aria-label="查看${esc(genre.name)}详情">${icon('info')}</button>
            </div>`).join('') || (current ? '<p class="muted">此主类型暂无细分类型。</p>' : '')}</div>
          </div>
      </div>
      <div class="divider"></div><div class="row wrap"><span class="muted">副类型（当前最多 ${secondaryLimit} 项）</span>
        ${secondary.map(id => `<span class="selection-chip">${esc(flatGenres().find(genre => genre.id === id)?.name || id)}<button data-remove-secondary="${esc(id)}" aria-label="移除副类型">×</button></span>`).join('')}
        <select id="secondaryGenre" aria-label="添加副类型" ${!selectedMain || secondary.length >= secondaryLimit ? 'disabled' : ''}><option value="">＋ 添加副类型</option>
          ${flatGenres().filter(genre => !types().includes(genre.id) && (!genre.parent_id || secondary.includes(genre.parent_id)))
            .map(genre => `<option value="${esc(genre.id)}">${esc(genre.name)}</option>`).join('')}
        </select></div>${selectionLimit(types().length, limits.genre)}
        ${selectedSub && !atLimit ? '<p class="muted">子类型已选满。再次点击已选子类型可取消。</p>' : ''}
        <p class="wizard-description" id="compatibility">${compatibilityText()}</p></div>`;
    $('#genreSearch').oninput = event => {
      const term = event.target.value.trim();
      $$('[data-main]').forEach(button => {
        const genre = genres.find(row => row.id === button.dataset.main);
        button.hidden = term && ![genre, ...genre.children].some(row => row.name.includes(term));
      });
      $$('#subgenres .option-card').forEach(card => card.hidden = term && !card.textContent.includes(term));
    };
    $$('[data-main]').forEach(button => button.onclick = () => {
      if (button.dataset.main === selectedMain) return;
      selectedMain = button.dataset.main; selectedSub = '';
      secondary = secondary.filter(id => id !== selectedMain && flatGenres().find(row => row.id === id)?.parent_id !== selectedMain);
      repainted();
    });
    $$('[data-sub]').forEach(button => button.onclick = () => {
      if (button.dataset.sub === selectedSub) selectedSub = '';
      else if (!selectedSub && !atLimit) selectedSub = button.dataset.sub;
      repainted();
    });
    $('#secondaryGenre').onchange = event => {
      if (event.target.value && secondary.length < secondaryLimit) { secondary.push(event.target.value); repainted(); }
    };
    $$('[data-remove-secondary]').forEach(button => button.onclick = () => {
      const remove = button.dataset.removeSecondary;
      secondary = secondary.filter(id => id !== remove && flatGenres().find(row => row.id === id)?.parent_id !== remove);
      repainted();
    });
    $$('[data-genre-info]').forEach(button => button.onclick = () => showGenre(button.dataset.genreInfo));
  }

  function compatibilityText() {
    if (!secondary.length) return '可选副类型。';
    const selected = types();
    const matching = combinations.filter(row => Array.isArray(row.types) && row.types.length > 1
      && row.types.every(id => selected.includes(id)) && secondary.some(id => row.types.includes(id)));
    const review = '多类型组合须在全书设计中审核。';
    return matching.length ? review + matching.map(row => esc((String(row.status).toLowerCase().includes('blocked') ? '不兼容警告 · ' : '')
      + (row.description || row.name || '已有组合资料，可查看图鉴'))).join('。') : review;
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

  function worldGuideHtml() {
    if (currentSlot() !== 'world' || !worldBlueprint) return '';
    const rp = worldBlueprint.resource_profile || {};
    const cov = worldBlueprint.coverage_summary || null;
    const primaryCats = (worldBlueprint.categories || []).filter(c => c.relevance === 'primary');
    const oosCats = (worldBlueprint.categories || []).filter(c => c.relevance === 'out_of_scope');
    const primaryType = types()[0] || '';
    return `<section class="card stack" id="wizardWorldGuide" style="margin-bottom:16px">
      <div class="row spread wrap">
        <strong>03 世界设定 · 按所选类型定制的资料边界与上下游衔接</strong>
        ${cov ? `<span class="tag ${cov.book_world_ready ? 'green' : ''}">同类型全书世界方法 ${cov.book_world_ready ? '已就绪' : '待补拆'} · 核心子域覆盖 ${cov.covered_primary_categories}/${cov.primary_category_count}</span>` : ''}
      </div>
      <p class="muted"><strong>上下游直通</strong>：承接 01–02 类型承诺与适配 + 拆解库「世界规则」方法 → 本步只建外部规则卡（rule / limits / visibility）、硬限制与待核边界 → 交接给 04 人物 / 05 关系 / 06 剧情 / 08 行动 / 09 场景。</p>
      <div><small class="muted">本类型优先世界资料分类（已自动排至最前）：</small>
        <div class="row wrap" style="margin-top:6px">${primaryCats.map(c => `<span class="tag ${c.receivable_count ? 'green' : 'blue'}" title="${esc(c.usage_mode || '')}">${esc(c.short_name || c.name)}${cov ? ` · ${c.receivable_count || 0} 条方法` : ''}</span>`).join('')}</div>
      </div>
      ${rp.preferred_resources?.length ? `<p class="muted"><strong>本类型典型资源口径</strong>：核心资源（${esc(rp.preferred_resources.join('、'))}）｜交换媒介（${esc((rp.exchange_media || []).join('、'))}）｜长期制约（${esc((rp.long_term_constraints || []).join('、'))}）</p>` : ''}
      <p class="muted"><strong>步骤边界守则</strong>：本步不提前写单个角色弧光（04）、私人恩怨（05）或分章剧情结局（06）。${oosCats.length ? `已将「${esc(oosCats.map(c => c.short_name || c.name).join('、'))}」折叠至下方跨类型扩展区，防止跨题材污染。` : ''}</p>
      ${cov && !cov.book_world_ready ? `<div class="row wrap"><a class="secondary" href="#/kb/prerequisites?type=${enc(primaryType)}" data-wizard-nav-link>查看世界资料蓝图</a><a class="ghost" href="#/staging" data-wizard-nav-link>前往预存库拆解同类型世界规则</a></div>` : ''}
    </section>`;
  }

  function characterGuideHtml() {
    if (currentSlot() !== 'character' || !characterBlueprint) return '';
    const cp = characterBlueprint.cast_profile || {};
    const cov = characterBlueprint.coverage_summary || null;
    const primaryChar = (characterBlueprint.character_categories || []).filter(c => c.relevance === 'primary');
    const primaryRel = (characterBlueprint.relation_categories || []).filter(c => c.relevance === 'primary');
    const oosCats = (characterBlueprint.categories || []).filter(c => c.relevance === 'out_of_scope');
    const primaryType = types()[0] || '';
    return `<section class="card stack" id="wizardCharacterGuide" style="margin-bottom:16px">
      <div class="row spread wrap">
        <strong>04 人物设计与 05 静态关系 · 按所选类型定制的资料边界与上下游衔接</strong>
        ${cov ? `<span class="tag ${cov.receivable_character_methods || cov.receivable_relation_methods ? 'green' : ''}">04人物方法 ${cov.receivable_character_methods || 0} 条 · 05关系方法 ${cov.receivable_relation_methods || 0} 条 · 核心覆盖 ${cov.covered_primary_categories}/${cov.primary_category_count}</span>` : ''}
      </div>
      <p class="muted"><strong>上下游直通</strong>：承接 03 世界制度/限制与剧情用人需求（cast_demands）→ 04 人物卡（复用优先、独立目标、外化声线、能力边界与暗身份隔离）→ 05 静态关系（仅用已建实体、含 ≥2 条不经过主角的独立配角互动）→ 交付 06 剧情 / 08 行动 / 09 场景。</p>
      <div class="stack" style="gap:6px">
        <div><small class="muted">04 人物设计优先子域（已按类型前置，自动路由至 04）：</small>
          <div class="row wrap" style="margin-top:4px">${primaryChar.map(c => `<span class="tag ${c.receivable_count ? 'green' : 'blue'}" title="${esc(c.usage_mode || '')}">04 · ${esc(c.short_name || c.name)}${cov ? ` (${c.receivable_count || 0})` : ''}</span>`).join('')}</div>
        </div>
        <div><small class="muted">05 静态关系优先子域（已按类型前置，自动路由至 05）：</small>
          <div class="row wrap" style="margin-top:4px">${primaryRel.map(c => `<span class="tag ${c.receivable_count ? 'green' : 'blue'}" title="${esc(c.usage_mode || '')}">05 · ${esc(c.short_name || c.name)}${cov ? ` (${c.receivable_count || 0})` : ''}</span>`).join('')}</div>
        </div>
      </div>
      ${cp.archetype_focus ? `<p class="muted"><strong>本类型建卡重点</strong>：${esc(cp.archetype_focus)}</p>` : ''}
      ${cp.relation_focus ? `<p class="muted"><strong>本类型关系张力核心</strong>：${esc(cp.relation_focus)}</p>` : ''}
      ${cp.antagonist_pattern ? `<p class="muted"><strong>反派/对立面模式</strong>：${esc(cp.antagonist_pattern)}</p>` : ''}
      <p class="muted"><strong>步骤边界守则</strong>：不按样本人数硬造工具人；暗身份严禁泄露到公开字段；05 关系只用 04 已建实体且不提前写死未发生背叛/结局。${oosCats.length ? `已将「${esc(oosCats.map(c => c.short_name || c.name).join('、'))}」折叠至下方跨类型扩展区。` : ''}</p>
      ${cov && !cov.receivable_character_methods && !cov.receivable_relation_methods ? `<div class="row wrap"><a class="secondary" href="#/kb/prerequisites?type=${enc(primaryType)}" data-wizard-nav-link>查看 04–05 资料蓝图</a><a class="ghost" href="#/staging" data-wizard-nav-link>前往预存库拆解人物与阵容</a></div>` : ''}
    </section>`;
  }

  function plotHookGuideHtml() {
    const slot = currentSlot();
    if ((slot !== 'structure' && slot !== 'hook') || !plotBlueprint) return '';
    const pp = plotBlueprint.plot_profile || {};
    const cov = plotBlueprint.coverage_summary || null;
    const primaryType = types()[0] || '';
    if (slot === 'structure') {
      const cats = plotBlueprint.structure_categories || [];
      const primary = cats.filter(c => c.relevance === 'primary');
      const oos = cats.filter(c => c.relevance === 'out_of_scope');
      return `<section class="card stack" id="wizardStructureGuide" style="margin-bottom:16px">
        <div class="row spread wrap">
          <strong>06 剧情结构与篇幅 · 按所选类型定制的资料边界与上下游衔接</strong>
          ${cov ? `<span class="tag ${cov.receivable_plot_methods ? 'green' : ''}">06 剧情方法 ${cov.receivable_plot_methods || 0} 条 · 篇幅样本 ${cov.length_recommendation_ready ? '已就绪' : '待补'}</span>` : ''}
        </div>
        <p class="muted"><strong>上下游直通</strong>：承接 01–05 类型承诺、世界限制、人物目标与静态关系 → 本步确立主支线骨架、章节节奏轮换、篇幅档位与 event_nodes → 交付 07 事件链 / 08 行动 / 09 场景。</p>
        <div><small class="muted">本类型优先结构与节奏子域（单视角与多视角互斥，已按类型排序）：</small>
          <div class="row wrap" style="margin-top:4px">${primary.map(c => `<span class="tag ${c.receivable_count ? 'green' : 'blue'}" title="${esc(c.usage_mode || '')}">${esc(c.short_name || c.name)}${cov ? ` (${c.receivable_count || 0})` : ''}</span>`).join('')}</div>
        </div>
        ${pp.arc_pattern ? `<p class="muted"><strong>主线结构特点</strong>：${esc(pp.arc_pattern)}</p>` : ''}
        ${pp.pacing_profile ? `<p class="muted"><strong>节奏与篇幅控制</strong>：${esc(pp.pacing_profile)}</p>` : ''}
        <p class="muted"><strong>步骤边界守则</strong>：06 剧情不提前写场景 POV 卡（09）或动作试错细节（08）；reader_plan 只写读者信息顺序与情绪变化。${oos.length ? `已将「${esc(oos.map(c => c.short_name || c.name).join('、'))}」折叠至跨类型扩展区。` : ''}</p>
        ${cov && !cov.receivable_plot_methods ? `<div class="row wrap"><a class="secondary" href="#/kb/prerequisites?type=${enc(primaryType)}" data-wizard-nav-link>查看 06–07 蓝图</a><a class="ghost" href="#/staging" data-wizard-nav-link>前往预存库拆解主线与章场推进</a></div>` : ''}
      </section>`;
    }
    const cats = plotBlueprint.hook_categories || [];
    const primaryPlot = cats.filter(c => c.target_stage === 'plot_design' && c.relevance === 'primary');
    const primaryEvent = cats.filter(c => c.target_stage === 'event_design' && c.relevance === 'primary');
    const oos = cats.filter(c => c.relevance === 'out_of_scope');
    return `<section class="card stack" id="wizardHookGuide" style="margin-bottom:16px">
      <div class="row spread wrap">
        <strong>06–07 卖点、伏笔与事件链 · 按所选类型定制的资料边界与上下游衔接</strong>
        ${cov ? `<span class="tag ${cov.receivable_plot_methods || cov.receivable_event_methods ? 'green' : ''}">06 剧情/伏笔 ${cov.receivable_plot_methods || 0} 条 · 07 事件链 ${cov.receivable_event_methods || 0} 条</span>` : ''}
      </div>
      <p class="muted"><strong>上下游直通</strong>：06 负责黄金三章钩子、伏笔窗口（promise_plan）与信息差（reader_plan）→ 07 仅在卷/章细化运行，严格沿用 06 event_nodes 完成门（104.1）生成条件后继候选（candidates）→ 交付 08 行动 / 09 场景。</p>
      <div class="stack" style="gap:6px">
        <div><small class="muted">06 卖点/伏笔优先子域（自动路由至 06）：</small>
          <div class="row wrap" style="margin-top:4px">${primaryPlot.map(c => `<span class="tag ${c.receivable_count ? 'green' : 'blue'}">06 · ${esc(c.short_name || c.name)}${cov ? ` (${c.receivable_count || 0})` : ''}</span>`).join('')}</div>
        </div>
        <div><small class="muted">07 事件链优先子域（自动路由至 07）：</small>
          <div class="row wrap" style="margin-top:4px">${primaryEvent.map(c => `<span class="tag ${c.receivable_count ? 'green' : 'blue'}">07 · ${esc(c.short_name || c.name)}${cov ? ` (${c.receivable_count || 0})` : ''}</span>`).join('')}</div>
        </div>
      </div>
      ${pp.hook_foreshadow_pattern ? `<p class="muted"><strong>钩子与伏笔模式</strong>：${esc(pp.hook_foreshadow_pattern)}</p>` : ''}
      ${pp.event_trigger_pattern ? `<p class="muted"><strong>07 事件触发模式</strong>：${esc(pp.event_trigger_pattern)}</p>` : ''}
      <p class="muted"><strong>步骤边界守则</strong>：反转须有前文可回溯线索，远期伏笔回收章未定时留 null；07 候选事件严禁颠倒因果顺序或假称既成事实。${oos.length ? `已将「${esc(oos.map(c => c.short_name || c.name).join('、'))}」折叠至跨类型扩展区。` : ''}</p>
    </section>`;
  }

  function craftGuideHtml() {
    const slot = currentSlot();
    if (!['narration', 'tone', 'style'].includes(slot) || !craftBlueprint) return '';
    const cp = craftBlueprint.craft_profile || {};
    const cov = craftBlueprint.coverage_summary || null;
    const primaryType = types()[0] || '';
    if (slot === 'narration') {
      const cats = craftBlueprint.narration_categories || [];
      return `<section class="card stack" id="wizardNarrationGuide" style="margin-bottom:16px">
        <div class="row spread wrap">
          <strong>09/12/13 写法、锚点与叙述表达 · 按所选类型定制的资料边界与上下游衔接</strong>
          ${cov ? `<span class="tag ${cov.receivable_anchor_methods || cov.receivable_expression_methods || cov.passage_reference_count ? 'green' : ''}">12锚点 ${cov.receivable_anchor_methods || 0} · 13表达 ${cov.receivable_expression_methods || 0} · 段落技法 ${cov.passage_reference_count || 0} 条</span>` : ''}
        </div>
        <p class="muted"><strong>上下游直通</strong>：叙述视角与知识边界路由至 09 场景与 13 表达；具象镜头/脉搏/氛围锚点精准路由至 12 锚点设计；对白潜台词与五感距离路由至 13 表达设计 → 14 收口交付 15 正文写作与 16 独立审稿。</p>
        <div class="row wrap">${cats.map(c => `<span class="tag ${c.receivable_count ? 'green' : 'blue'}" title="${esc(c.usage_mode || '')}">${esc(c.target_stage_label || '')} · ${esc(c.short_name || c.name)}${cov ? ` (${c.receivable_count || 0})` : ''}</span>`).join('')}</div>
        ${cp.anchor_focus ? `<p class="muted"><strong>12 锚点重点</strong>：${esc(cp.anchor_focus)}</p>` : ''}
        ${cp.expression_focus ? `<p class="muted"><strong>13 表达重点</strong>：${esc(cp.expression_focus)}</p>` : ''}
        <p class="muted"><strong>步骤边界守则</strong>：锚点必须绑定当前 POV 观察者与真实动作步骤；表达严守 09 allowed_disclosure，不提前泄密或篡改 10 状态变化。</p>
        ${cov && !cov.receivable_expression_methods && !cov.passage_reference_count ? `<div class="row wrap"><a class="secondary" href="#/kb/prerequisites?type=${enc(primaryType)}" data-wizard-nav-link>查看 12–17 收口蓝图</a><a class="ghost" href="#/staging" data-wizard-nav-link>前往预存库拆解叙述与段落技法</a></div>` : ''}
      </section>`;
    }
    if (slot === 'tone') {
      return `<section class="card stack" id="wizardToneGuide" style="margin-bottom:16px">
        <div class="row spread wrap">
          <strong>13 语气基调（风格）· 按所选类型排序核心并隔离跨题材项</strong>
          ${cov ? `<span class="tag ${cov.receivable_expression_methods ? 'green' : ''}">13 表达方法 ${cov.receivable_expression_methods || 0} 条</span>` : ''}
        </div>
        <p class="muted"><strong>上下游直通</strong>：点击下方「语气与情绪」抽屉后，本类型核心语气排至最前，非本类型常规语气自动折叠至跨类型扩展区；所选语气仅送达 13 表达设计并写入 14 写审核验口径。</p>
        ${cp.expression_focus ? `<p class="muted"><strong>本类型表达与语气重点</strong>：${esc(cp.expression_focus)}</p>` : ''}
        <p class="muted"><strong>偏好协调机制</strong>：若同时勾选互相竞争的语气，13 表达设计须通过 <code>preference_resolutions</code> 明确各自落入不同场景节拍或延后条件，防止全文语体分裂。</p>
      </section>`;
    }
    return `<section class="card stack" id="wizardStyleGuide" style="margin-bottom:16px">
      <div class="row spread wrap">
        <strong>13 文风与语言质感（文笔）· 按所选类型排序核心并隔离跨题材项</strong>
        ${cov ? `<span class="tag ${cov.receivable_expression_methods || cov.receivable_writer_methods ? 'green' : ''}">13 表达 ${cov.receivable_expression_methods || 0} · 写审交接 ${cov.receivable_writer_methods || 0} 条</span>` : ''}
      </div>
      <p class="muted"><strong>上下游直通</strong>：点击下方「文风与语言质感」抽屉后，20 类标准风格已按当前主副类型分层（核心置顶，跨题材风格自动折叠隔离）；所选文风驱动 13 表达指导并交由 15 写手落笔、16 独立审稿核验。</p>
      ${cp.expression_focus ? `<p class="muted"><strong>本类型文风重点</strong>：${esc(cp.expression_focus)}</p>` : ''}
      ${cp.writer_review_focus ? `<p class="muted"><strong>15–16 写审核验红线</strong>：${esc(cp.writer_review_focus)}</p>` : ''}
      <p class="muted"><strong>偏好协调机制</strong>：竞争风格（如轻松 vs 写实）会在 13 表达设计强制通过 <code>preference_resolutions</code> 指向互不重叠的场景指导，确保不同场面各得其所。</p>
    </section>`;
  }

  function paintOptions() {
    const {slot, stage, name} = currentStep();
    $('#modalBody').innerHTML = stepsBar(step) + WizardStep({name, stage, description:`基于 ${names()}`,
      stepGuide: worldGuideHtml() + characterGuideHtml() + plotHookGuideHtml() + craftGuideHtml(),
      lengthPlan:slot === 'structure' ? `<section aria-label="篇幅计划"><h3>篇幅计划</h3>
        ${lengthFields(lengthPlan, tierRecommendation, defaultBudget)}</section>` : '',
      methods:(castSamples ? castSamplesHtml(castSamples, {keepWizard:true}) : '') + libraryPanel(),
      options, selected:selections(slot), limit:limits[slot]});
    $$('#modalBody [data-option]').forEach(button => button.onclick = () => {
      capture();
      const option = known.get(button.dataset.option);
      if (option?.children?.length) openOption(option, slot);
      else { toggle(slot, button.dataset.option); render(); }
    });
  }

  function openOption(option, slot) {
    let current = option;
    const parents = [];
    function show() {
      const children = current.children || [];
      const activeChildren = children.filter(child => child.relevance !== 'out_of_scope');
      const guardedChildren = children.filter(child => child.relevance === 'out_of_scope');
      const key = current.key || current.id;
      drawer(`${slotName(slot)} · ${current.name}`, `<div class="row spread"><p class="muted">${esc(current.description || '')}</p>
        ${parents.length ? '<button class="ghost" id="optionBack">返回上一级</button>' : ''}</div>
        ${selectionLimit(selections(slot).length, limits[slot])}
        <div class="option-grid" style="grid-template-columns:1fr">${activeChildren.map(child => OptionCard(child, selections(slot), limits[slot])).join('')}</div>
        ${guardedChildren.length ? `<details class="details" id="drawerOutOfScopeOptions" style="margin-top:12px">
          <summary>跨类型扩展条目（非当前类型常规项，按需展开 · ${guardedChildren.length} 项）</summary>
          <div class="option-grid" style="grid-template-columns:1fr;margin-top:8px">${guardedChildren.map(child => OptionCard(child, selections(slot), limits[slot])).join('')}</div>
        </details>` : ''}
        <div class="divider"></div><button class="secondary" id="pickParent"
          ${current.selectable === false ? 'hidden disabled' : canPick(slot, key) ? '' : 'disabled'}>${selections(slot).includes(key) ? '取消选择' : '选择'}「${esc(current.name)}」</button>`);
      const pick = id => { toggle(slot, id); render(); show(); };
      $('#optionBack')?.addEventListener('click', () => { current = parents.pop(); show(); });
      $('#pickParent').onclick = () => pick(key);
      $$('#drawerBody [data-option]').forEach(button => button.onclick = () => {
        const child = known.get(button.dataset.option);
        if (child.children?.length) { parents.push(current); current = child; show(); }
        else pick(button.dataset.option);
      });
    }
    show();
  }

  function paintConfirm() {
    const summary = STEPS.filter(s => s.slot !== 'genre' && s.slot !== 'confirm').map(({name, slot}) => `<dt>${name}</dt><dd>${esc(selections(slot).map(key => known.get(key)?.name || key).join('、') || '由设计阶段展开')}</dd>`).join('');
    const audit = handoffAudit;
    const auditSummary = audit ? `<section class="card stack" id="wizardHandoffPreview">
      <div class="row spread wrap"><strong>拆解产物下游接收预览（对接工作流 17 步）</strong>
        <div class="row wrap">
          <span class="tag green">同类型可接收方法 ${audit.summary?.receivable_methods || 0} 条</span>
          <span class="tag ${audit.summary?.book_world_ready ? 'green' : ''}">03 全书世界方法 ${audit.summary?.book_world_ready ? '已就绪' : '待补拆'}</span>
          <span class="tag ${audit.summary?.cast_sample_ready ? 'green' : ''}">人物分布样本 ${audit.summary?.cast_sample_ready ? '已自动接入' : '待拆解'}</span>
          <span class="tag ${audit.summary?.passage_reference_count ? 'green' : ''}">段落技法 ${audit.summary?.passage_reference_count || 0} 条</span>
        </div></div>
      ${(audit.originality_audit?.warnings || []).map(w => `<p class="muted">${esc(w.message)}</p>`).join('')}
      <p class="muted">全书方向短案与类型适配会自动接收你已选拆解方法的抽象摘要（不含原作情节），03 世界设计及后续各步会按所选类型资料边界与实际前置调用对应方法。</p>
    </section>` : '';
    $('#modalBody').innerHTML = stepsBar(step) + `<div class="wizard-confirm"><h2>确认立项卡</h2>
      <div class="card"><dl class="selection-summary"><dt>类型</dt><dd>${esc(names())}</dd>${summary}
        ${lengthSummary(lengthPlan, tierRecommendation?.tiers)}</dl></div>
      ${auditSummary}
      ${methodChoices(selectedMethods, currentVersions)}
      ${selectedMethods.size ? '<div class="row wrap"><button type="button" class="secondary" data-refresh-wizard-methods>刷新所选方法的版本</button><button type="button" class="secondary" id="syncWizardTasksFromMethods">按已选拆解方法自动勾选对应步骤职责</button></div>' : ''}
      <div class="divider"></div><div class="stack">
        <label class="field"><span>小说书名</span><input id="wizardTitle" maxlength="120" placeholder="给故事起一个暂定书名" value="${esc(title)}"></label>
        <label class="field"><span>一句话故事构想 <span class="error">*</span></span><textarea id="wizardIdea" rows="4" maxlength="12000" required placeholder="谁，在什么处境下，为了什么目标，必须做出怎样的选择？">${esc(idea)}</textarea></label>
        <label class="field"><span>硬约束（选填）</span><textarea id="wizardConstraints" rows="3" maxlength="12000" placeholder="必须保留的设定、不能发生的情节、阅读对象…">${esc(constraints)}</textarea></label>
        ${wizardMethods(bookWorldAvailable)}
        <details class="details" ${applyTasks ? 'open' : ''}><summary>可选 · 按创作环节启用 22 项制作方法职责（不改则按所选偏好与世界方法自动执行）</summary>
          <div class="method-choices" style="margin-top:8px">
            ${[
              ['world_rules','世界定稿·世界规则与限制'],['character_arc','人物定稿·人物目标与弧光'],['relationships','人物定稿·人物关系与势力'],
              ['main_plot','全书大纲·主线与结局兑现'],['subplot','全书/卷纲·支线与主线交汇'],['volume_outline','卷纲切章·分卷目标与转折'],
              ['chapter_outline','章细纲·连续章纲与承接'],['hook','大纲/章纲·钩子与问题接力'],['foreshadow','大纲/章纲·伏笔埋设与回收'],
              ['information','大纲/场景·信息披露与悬念'],['event_chain','场景节拍·事件触发与因果'],['action_chain','场景节拍·行动阻碍与代价'],
              ['scene_composition','场景节拍·场景职责与选择'],['state_change','场景节拍·状态变化与代价'],['state_propagation','场景节拍·后果与影响传播'],
              ['anchors','写前表达·可见线索与节拍'],['pacing','节奏与情绪序列'],['narration','写前表达·叙述时序与视角'],
              ['expression','写前表达·叙事对话与文风'],['method_binding','工作包·方法交接与核验'],
              ['type_choice','前置契约·类型边界（按需）'],['type_adaptation','前置契约·多类型融合（按需）'],
            ].map(([id,label])=>`<label class="method-choice"><input type="checkbox" name="wizardTask" value="${id}" ${selectedTasks.has(id)?'checked':''}> ${label}</label>`).join('')}
          </div>
          <label class="check-row"><input type="checkbox" id="wizardApplyTasks" ${applyTasks ? 'checked' : ''}> 启用以上勾选职责作为本轮制作要求</label>
        </details>
        <label class="check-row"><input type="checkbox" id="wizardDirectionReview" ${directionReview ? 'checked' : ''}> 先生成 2–3 份全书方向与故事大纲供对比选择（若已在构想中写明方向，取消勾选则直接展开设定与全书大纲）</label>
        <div class="notice">
          <p><strong>实际创作工作流（默认启用）</strong>：立项选定的类型与偏好由程序自动冻结并继承至卷纲与每一章，不再重复空转「类型判定 / 类型适配」；直接围绕<strong>全书大纲（含开篇黄金三章与人物弧）→ 世界与人物定稿 → 卷纲逐章任务切分 → 章细纲与场景包 → 正文写审接受</strong>推进。</p>
        </div>
      </div></div>`;
  }

  async function createNovel(payload) {
    const result = await api.post('/novels', {direction_review:true, planning_hierarchy:true, creative_workflow:true, ...payload});
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
    const errorMessage = $('#wizardAutoError');
    const typeSelection = $('#wizardTypeSelection');
    errorMessage.hidden = true;
    submitting = true;
    typeSelection.inert = true;
    try {
      await busy(button, async () => {
        try {
          await createNovel({
            design_mode:'auto', auto_recommendations:true, genre_ids:types(),
            auto_length:true, length_mode:'tiered',
          });
        } catch (error) {
          if (!alive()) return;
          errorMessage.hidden = false;
          errorMessage.textContent = error.message.replace(/^AUTO_RECOMMENDATIONS_MISSING[：:]\s*/, '');
          errorMessage.focus();
        }
      });
    } finally {
      submitting = false;
      typeSelection.inert = false;
    }
  }

  async function submitManual(button) {
    if (submitting || staleMethods()) return;
    capture();
    if (!idea) { $('#wizardIdea').focus(); toast('请先填写一句话故事构想', true); return; }
    const payload = {
      title:title || '未命名小说', idea, constraints, genre_ids:types(),
      design_mode:'manual',
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
    if ($('#wizardApplyTasks')?.checked) {
      const checkedTasks = $$('[name=wizardTask]:checked').map(el => el.value);
      if (checkedTasks.length) payload.production_methods = {tasks: checkedTasks};
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
