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

export async function openWizard(prefill) {
  const token = ++session;
  const dialog = modal('新建小说', loading(), '', true);
  const known = new Map(), selectedMethods = new Map();
  const chosen = {};
  let step = prefill ? 1 : 0, revision = 0, selectedMain = '', selectedSub = '';
  let secondary = [], genres = [], combinations = [], options = [], methods = [], currentVersions = {};
  let title = '', idea = '', constraints = '', lengthPlan = {length_mode:'tiered'};
  let limits = {}, defaultBudget = {}, bookWorldAvailable = false, submitting = false;
  let tierRecommendation = null;
  let castSamples = null;

  const alive = () => token === session && dialog.open;
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
    const last = step === 8;
    const summary = step === 0 ? names() : selections(STEPS[step].slot).map(key => known.get(key)?.name || key).join('、') || names();
    const disabled = pending || submitting || (step === 0 && !selectedMain) || (last && staleMethods());
    const unavailable = disabled ? 'disabled' : '';
    $('#modalFooter').innerHTML = `<div class="wizard-selection">${step === 0 ? '已选类型' : '创作偏好'} <strong>${esc(summary)}</strong></div>
      ${step ? '<button class="secondary" id="wizardPrev">上一步</button>' : '<button class="secondary" data-close-modal>取消</button>'}
      ${step > 0 && step < 8 ? '<button class="ghost" id="wizardSkip">跳过此步</button>' : ''}
      ${last ? `<button class="secondary" id="wizardNext" ${unavailable}>人工选择</button>
        <button class="button" id="wizardAuto" ${unavailable}>AI 自动</button>`
        : `<button class="button" id="wizardNext" ${unavailable}>下一步：${STEPS[step + 1].name} ${icon('arrow')}</button>`}`;
    const move = delta => {
      if (submitting) return;
      if (step === 6 && delta > 0) {
        const invalid = $('#modalBody [data-length-field]:invalid,#modalBody [data-budget-field]:invalid');
        if (invalid) {
          const group = invalid.closest('details');
          if (group) group.open = true;
          invalid.reportValidity();
          return;
        }
      }
      capture();
      step += delta;
      repainted();
    };
    $('#wizardPrev')?.addEventListener('click', () => move(-1));
    $('#wizardSkip')?.addEventListener('click', () => move(1));
    $('#wizardNext').onclick = last ? event => submit('manual', event.currentTarget) : () => move(1);
    $('#wizardAuto')?.addEventListener('click', event => submit('auto', event.currentTarget));
  }

  function capture() {
    if (step === 8 && $('#wizardTitle')) {
      title = $('#wizardTitle').value.trim();
      idea = $('#wizardIdea').value.trim();
      constraints = $('#wizardConstraints').value.trim();
    }
    if (step === 6 && $('#modalBody [data-tier-mode]')) {
      lengthPlan = readLengthFields($('#modalBody'));
    }
  }

  async function paint() {
    const current = ++revision;
    const slot = STEPS[step].slot;
    $('#modalTitle').textContent = `新建小说 · ${STEPS[step].name}`;
    $('#modalBody').innerHTML = stepsBar(step) + loading();
    $('#modalBody').scrollTop = 0;
    footer(true);
    try {
      const [library, optionResult, tierData, castData] = await Promise.all([
        api.get(`/kb/method-recommendations?${query({
          slot:slot === 'confirm' ? 'world' : slot, types:types(), selected:[...selectedMethods.keys()]})}`),
        slot !== 'confirm' && slot !== 'genre' ? api.get(`/options?${query({slot})}`) : {},
        slot === 'structure' ? readTierRecommendation(types()) : null,
        slot === 'character' ? readCastSamples(types()) : null,
      ]);
      if (!alive() || current !== revision) return;
      methods = library.recommendations || [];
      currentVersions = library.current_versions || {};
      if (slot === 'confirm') bookWorldAvailable = library.book_world_available;
      options = optionResult.options || [];
      if (tierData) tierRecommendation = tierData;
      castSamples = castData;
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
    if (step === 0) paintGenres();
    else if (step === 8) paintConfirm();
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
        selectedMethods.set(method.id, {id:method.id, version:method.version, slot:STEPS[step].slot, title:method.title});
        currentVersions[method.id] = method.version;
      }
      render();
    });
    $$('[data-remove-wizard-method]').forEach(button => button.onclick = () => {
      capture();
      selectedMethods.delete(button.dataset.removeWizardMethod);
      render();
    });
  }

  const libraryPanel = () => methodRecommendations(methods, selectedMethods, currentVersions);

  function paintGenres() {
    const current = genres.find(genre => genre.id === selectedMain);
    const atLimit = types().length >= limits.genre;
    const secondaryLimit = Math.min(2, limits.genre - 1 - Number(Boolean(selectedSub)));
    $('#modalBody').innerHTML = stepsBar(0) + `
      <div class="row spread"><h2>为故事选择类型</h2><input id="genreSearch" placeholder="搜索类型…" aria-label="搜索类型"></div>
      <p class="muted">主类型选 1 项，主类型下的子类型最多选 1 项。主、子、副类型合计最多选 ${limits.genre} 项。</p>
      ${libraryPanel()}
      <div class="genre-layout">
        <div class="genre-list" id="genreList">${genres.map(genre => `<button data-main="${esc(genre.id)}" class="${genre.id === selectedMain ? 'active' : ''}">${esc(genre.name)} <small class="faint">${genre.children.length}</small></button>`).join('')}</div>
        <div><div class="row spread" style="margin-bottom:16px"><h3>${esc(current?.name || '选择主类型')}</h3>
          ${current ? `<button class="ghost" data-genre-info="${esc(current.id)}">${icon('info')} 类型定义</button>` : ''}</div>
          <div class="option-grid" id="subgenres">${(current?.children || []).map(genre => `
            <div class="option-card ${selectedSub === genre.id ? 'selected' : ''}">
              <button class="rec-pick grow" data-sub="${esc(genre.id)}" aria-pressed="${selectedSub === genre.id}"
                ${selectedSub !== genre.id && (selectedSub || atLimit) ? 'disabled' : ''}><h3>${esc(genre.name)}</h3><p>${esc(genre.definition || '定义待补充')}</p></button>
              <button class="icon-button" data-genre-info="${esc(genre.id)}" aria-label="查看${esc(genre.name)}详情">${icon('info')}</button>
            </div>`).join('') || '<p class="muted">此主类型暂无细分类型，可以直接进入下一步。</p>'}</div>
          </div>
      </div>
      <div class="divider"></div><div class="row wrap"><span class="muted">副类型（当前最多 ${secondaryLimit} 项）</span>
        ${secondary.map(id => `<span class="selection-chip">${esc(flatGenres().find(genre => genre.id === id)?.name || id)}<button data-remove-secondary="${esc(id)}" aria-label="移除副类型">×</button></span>`).join('')}
        <select id="secondaryGenre" aria-label="添加副类型" ${secondary.length >= secondaryLimit ? 'disabled' : ''}><option value="">＋ 添加副类型</option>
          ${flatGenres().filter(genre => !types().includes(genre.id) && (!genre.parent_id || secondary.includes(genre.parent_id)))
            .map(genre => `<option value="${esc(genre.id)}">${esc(genre.name)}</option>`).join('')}
        </select></div>${selectionLimit(types().length, limits.genre)}
        ${selectedSub && !atLimit ? '<p class="muted">子类型已选满。再次点击已选子类型可取消。</p>' : ''}
        <p class="wizard-description" id="compatibility">${compatibilityText()}</p>`;
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

  function paintOptions() {
    const {slot, name} = STEPS[step];
    $('#modalBody').innerHTML = stepsBar(step) + WizardStep({name, description:`基于 ${names()}`,
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
      const key = current.key || current.id;
      drawer(`${slotName(slot)} · ${current.name}`, `<div class="row spread"><p class="muted">${esc(current.description || '')}</p>
        ${parents.length ? '<button class="ghost" id="optionBack">返回上一级</button>' : ''}</div>
        ${selectionLimit(selections(slot).length, limits[slot])}
        <div class="option-grid" style="grid-template-columns:1fr">${children.map(child => OptionCard(child, selections(slot), limits[slot])).join('')}</div>
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
    const summary = STEPS.slice(1, 8).map(({name, slot}) => `<dt>${name}</dt><dd>${esc(selections(slot).map(key => known.get(key)?.name || key).join('、') || '由设计阶段展开')}</dd>`).join('');
    $('#modalBody').innerHTML = stepsBar(8) + `<div class="wizard-confirm"><h2>确认立项卡</h2>
      <div class="card"><dl class="selection-summary"><dt>类型</dt><dd>${esc(names())}</dd>${summary}
        ${lengthSummary(lengthPlan, tierRecommendation?.tiers)}</dl></div>
      ${methodChoices(selectedMethods, currentVersions)}
      ${selectedMethods.size ? '<button type="button" class="secondary" data-refresh-wizard-methods>刷新所选方法的版本</button>' : ''}
      <div class="divider"></div><div class="stack">
        <label class="field"><span>小说书名</span><input id="wizardTitle" maxlength="120" placeholder="给故事起一个暂定书名" value="${esc(title)}"></label>
        <label class="field"><span>一句话故事构想 <span class="error">*</span></span><textarea id="wizardIdea" rows="4" maxlength="12000" required placeholder="谁，在什么处境下，为了什么目标，必须做出怎样的选择？">${esc(idea)}</textarea></label>
        <label class="field"><span>硬约束（选填）</span><textarea id="wizardConstraints" rows="3" maxlength="12000" placeholder="必须保留的设定、不能发生的情节、阅读对象…">${esc(constraints)}</textarea></label>
        ${wizardMethods(bookWorldAvailable)}
        <div class="notice">
          <p><strong>人工选择</strong> 使用你勾选的偏好，需要采用所选拆解方法时由你核对确认。</p>
          <p><strong>AI 自动</strong> 保留你的类型、已选偏好与硬约束，按每一步的前置和需求从已批准的推荐中选材。</p>
          <p>两个入口都会保存立项并启动全书设计。你可以用「上一步」回改立项选项。书纲和章场方案确认后进入正文制作。</p>
        </div>
      </div></div>`;
  }

  async function submit(mode, button) {
    if (submitting || staleMethods()) return;
    capture();
    if (!idea) { $('#wizardIdea').focus(); toast('请先填写一句话故事构想', true); return; }
    const payload = {
      title:title || '未命名小说', idea, constraints, genre_ids:types(),
      design_mode:mode,
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
    const other = mode === 'auto' ? $('#wizardNext') : $('#wizardAuto');
    other.disabled = true;
    try {
      await busy(button, async () => {
        const result = await api.post('/novels', payload);
        const novel = result.novel || result;
        if (!novel.id) throw new Error('项目创建结果没有返回作品标识');
        dialog.close();
        document.dispatchEvent(new CustomEvent('studio:created', {bubbles:true}));
        location.hash = `#/studio/${enc(novel.id)}`;
        toast(result.run?.reason || '立项卡已保存，进入制作台');
      });
    } finally {
      submitting = false;
      if (alive()) other.disabled = false;
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
    selectedMain = genre?.parent_id || genre?.id || genres[0]?.id || '';
    selectedSub = genre?.parent_id ? genre.id : '';
    repainted();
  } catch (error) {
    if (!alive()) return;
    $('#modalBody').innerHTML = `<p class="error">${esc(error.message)}</p>`;
    $('#modalFooter').innerHTML = '<button class="secondary" data-close-modal>关闭</button>';
    fail(error);
  }
}
