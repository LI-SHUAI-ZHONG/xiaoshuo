import {api, query, enc} from '../api.js';
import {$, $$, esc, icon, modal, drawer, loading, fail, toast, busy, readable} from '../ui.js';
import {STEPS, stepsBar, WizardStep, OptionCard, slotName} from '../components/WizardStep.js';
import {RecCard} from '../components/RecCard.js';
import {wizardMethods} from './project-methods.js';
import {methodChoices, methodRecommendations} from './wizard-methods.js';

const fields = {tone:'tone_ids', style:'style_ids', narration:'narration_ids', world:'world_ids',
  character:'character_ids', structure:'structure_ids', hook:'mechanism_ids'};
let session = 0;

export async function openWizard(prefill) {
  const token = ++session;
  const dialog = modal('新建小说', loading(), '', true);
  const known = new Map(), recMeta = new Map(), selectedMethods = new Map();
  const chosen = {};
  let step = prefill ? 1 : 0, revision = 0, selectedMain = '', selectedSub = '';
  let secondary = [], genres = [], combinations = [], rec = [], options = [], methods = [], currentVersions = {};
  let title = '', idea = '', constraints = '', targetWords = '', chapterCount = '', volumeCount = '', useMethods = true;

  const alive = () => token === session && dialog.open;
  const types = () => [selectedMain, selectedSub, ...secondary].filter(Boolean);
  const flatGenres = () => genres.flatMap(genre => [genre, ...genre.children]);
  const names = () => types().map(id => flatGenres().find(genre => genre.id === id)?.name || id).join(' › ');
  const selections = slot => chosen[slot] || [];
  const staleMethods = () => [...selectedMethods.values()].some(method => currentVersions[method.id] !== method.version);
  const repainted = () => paint().catch(fail);

  function rememberOptions(items) {
    for (const option of items) {
      known.set(option.key || option.id, option);
      rememberOptions(option.children || []);
    }
  }

  function toggle(slot, key, recommendation) {
    const items = selections(slot);
    chosen[slot] = items.includes(key) ? items.filter(item => item !== key) : [...items, key];
    if (!chosen[slot].includes(key)) recMeta.delete(key);
    else if (recommendation) rememberRecommendation(key, recommendation);
  }

  function rememberRecommendation(key, recommendation) {
    recMeta.set(key, {recommended:true, rec_rank:rec.indexOf(recommendation) + 1, rec_level:recommendation.level});
  }

  function footer(pending = false) {
    const last = step === 8;
    const summary = step === 0 ? names() : selections(STEPS[step].slot).map(key => known.get(key)?.name || key).join('、') || names();
    const disabled = pending || (step === 0 && !selectedMain) || (last && staleMethods());
    $('#modalFooter').innerHTML = `<div class="wizard-selection">${step === 0 ? '已选类型' : '创作偏好'} <strong>${esc(summary)}</strong></div>
      ${step ? '<button class="secondary" id="wizardPrev">上一步</button>' : '<button class="secondary" data-close-modal>取消</button>'}
      ${step > 0 && step < 8 ? '<button class="ghost" id="wizardSkip">跳过此步</button>' : ''}
      <button class="button" id="wizardNext" ${disabled ? 'disabled' : ''}>${last ? '开始制作' : `下一步：${STEPS[step + 1].name}`} ${icon(last ? 'play' : 'arrow')}</button>`;
    const move = delta => { capture(); step += delta; repainted(); };
    $('#wizardPrev')?.addEventListener('click', () => move(-1));
    $('#wizardSkip')?.addEventListener('click', () => move(1));
    $('#wizardNext').onclick = last ? () => { capture(); submit(); } : () => move(1);
  }

  function capture() {
    if (step === 8 && $('#wizardTitle')) {
      title = $('#wizardTitle').value.trim();
      idea = $('#wizardIdea').value.trim();
      constraints = $('#wizardConstraints').value.trim();
      useMethods = $('#wizardUseMethods').checked;
    }
    if (step === 6 && $('#targetWords')) {
      targetWords = $('#targetWords').value;
      chapterCount = $('#chapterCount').value;
      volumeCount = $('#volumeCount').value;
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
      const [library, legacy, optionResult] = await Promise.all([
        slot !== 'confirm' || selectedMethods.size ? api.get(`/kb/method-recommendations?${query({
          slot:slot === 'confirm' ? 'genre' : slot, types:types(), selected:[...selectedMethods.keys()]})}`) : {},
        slot !== 'confirm' ? api.get(`/recommend?${query({slot, types:types()})}`) : {},
        slot !== 'confirm' && slot !== 'genre' ? api.get(`/options?${query({slot})}`) : {},
      ]);
      if (!alive() || current !== revision) return;
      methods = library.recommendations || [];
      currentVersions = library.current_versions || {};
      rec = legacy.recommendations || [];
      options = optionResult.options || [];
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
        if (!prior && selectedMethods.size >= 24) { toast('最多保存 24 条方法偏好', true); return; }
        selectedMethods.set(method.id, {id:method.id, version:method.version, slot:STEPS[step].slot, title:method.title});
        currentVersions[method.id] = method.version;
        useMethods = true;
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
    const legacy = rec.filter(Boolean);
    $('#modalBody').innerHTML = stepsBar(0) + `
      <div class="row spread"><h2>为故事选择类型</h2><input id="genreSearch" placeholder="搜索类型…" aria-label="搜索类型"></div>
      ${libraryPanel()}
      ${legacy.length ? `<details class="details"><summary>类型选项用法参考</summary><div class="rec-grid">${legacy.map((row, index) => RecCard(row, index, types().map(id => 'genre.' + id))).join('')}</div></details>` : ''}
      <div class="genre-layout">
        <div class="genre-list" id="genreList">${genres.map(genre => `<button data-main="${esc(genre.id)}" class="${genre.id === selectedMain ? 'active' : ''}">${esc(genre.name)} <small class="faint">${genre.children.length}</small></button>`).join('')}</div>
        <div><div class="row spread" style="margin-bottom:16px"><h3>${esc(current?.name || '选择主类型')}</h3>
          ${current ? `<button class="ghost" data-genre-info="${esc(current.id)}">${icon('info')} 类型定义</button>` : ''}</div>
          <div class="option-grid" id="subgenres">${(current?.children || []).map(genre => `
            <div class="option-card ${selectedSub === genre.id ? 'selected' : ''}">
              <button class="rec-pick grow" data-sub="${esc(genre.id)}"><h3>${esc(genre.name)}</h3><p>${esc(genre.definition || '定义待补充')}</p></button>
              <button class="icon-button" data-genre-info="${esc(genre.id)}" aria-label="查看${esc(genre.name)}详情">${icon('info')}</button>
            </div>`).join('') || '<p class="muted">此主类型暂无细分类型，可以直接进入下一步。</p>'}</div>
        </div>
      </div>
      <div class="divider"></div><div class="row wrap"><span class="muted">副类型（最多 2 个）</span>
        ${secondary.map(id => `<span class="selection-chip">${esc(flatGenres().find(genre => genre.id === id)?.name || id)}<button data-remove-secondary="${esc(id)}" aria-label="移除副类型">×</button></span>`).join('')}
        <select id="secondaryGenre" aria-label="添加副类型" ${secondary.length >= 2 ? 'disabled' : ''}><option value="">＋ 添加副类型</option>
          ${flatGenres().filter(genre => !types().includes(genre.id)).map(genre => `<option value="${esc(genre.id)}">${esc(genre.name)}</option>`).join('')}
        </select></div><p class="wizard-description" id="compatibility">${compatibilityText()}</p>`;
    $('#genreSearch').oninput = event => {
      const term = event.target.value.trim();
      $$('[data-main]').forEach(button => {
        const genre = genres.find(row => row.id === button.dataset.main);
        button.hidden = term && ![genre, ...genre.children].some(row => row.name.includes(term));
      });
      $$('#subgenres .option-card').forEach(card => card.hidden = term && !card.textContent.includes(term));
    };
    $$('[data-main]').forEach(button => button.onclick = () => {
      selectedMain = button.dataset.main; selectedSub = '';
      secondary = secondary.filter(id => id !== selectedMain);
      repainted();
    });
    $$('[data-sub]').forEach(button => button.onclick = () => {
      selectedSub = button.dataset.sub;
      secondary = secondary.filter(id => id !== selectedSub);
      repainted();
    });
    $('#secondaryGenre').onchange = event => {
      if (event.target.value && secondary.length < 2) { secondary.push(event.target.value); repainted(); }
    };
    $$('[data-remove-secondary]').forEach(button => button.onclick = () => {
      secondary = secondary.filter(id => id !== button.dataset.removeSecondary);
      repainted();
    });
    $$('[data-genre-info]').forEach(button => button.onclick = () => showGenre(button.dataset.genreInfo));
    bindLegacy('genre');
  }

  function compatibilityText() {
    if (!secondary.length) return '可选副类型。';
    const selected = types();
    const matching = combinations.filter(row => Array.isArray(row.types) && row.types.length > 1
      && row.types.every(id => selected.includes(id)) && secondary.some(id => row.types.includes(id)));
    return matching.length ? matching.map(row => esc((String(row.status).toLowerCase().includes('blocked') ? '不兼容警告 · ' : '')
      + (row.description || row.name || '已有组合资料，可查看图鉴'))).join('。') : '这组类型由设计阶段核对。';
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

  function bindLegacy(slot) {
    $$('#modalBody [data-rec]').forEach(button => button.onclick = () => {
      const key = button.dataset.rec;
      const row = rec.find(item => item?.option_key === key);
      if (slot !== 'genre') { capture(); toggle(slot, key, row); render(); return; }
      const genre = flatGenres().find(item => item.id === key.replace(/^genre\./, ''));
      if (!genre) return;
      selectedMain = genre.parent_id || genre.id;
      selectedSub = genre.parent_id ? genre.id : '';
      secondary = secondary.filter(id => id !== selectedMain && id !== selectedSub);
      rememberRecommendation(key, row);
      repainted();
    });
  }

  function paintOptions() {
    const {slot, name} = STEPS[step];
    $('#modalBody').innerHTML = stepsBar(step) + WizardStep({name, description:`基于 ${names()}`,
      methods:libraryPanel(), recommendations:rec, options, selected:selections(slot)}) + (slot === 'structure' ? `
      <div class="section-head"><h3>篇幅计划</h3></div><div class="form-grid">
        <label class="field"><span>目标总字数</span><input id="targetWords" type="number" min="1" value="${esc(targetWords)}"></label>
        <label class="field"><span>计划章节数</span><input id="chapterCount" type="number" min="1" value="${esc(chapterCount)}"></label>
        <label class="field"><span>计划卷数</span><input id="volumeCount" type="number" min="1" value="${esc(volumeCount)}"></label>
      </div>` : '');
    bindLegacy(slot);
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
      const related = rec.filter(row => row && children.some(child => (child.key || child.id) === row.option_key));
      const key = current.key || current.id;
      drawer(`${slotName(slot)} · ${current.name}`, `<div class="row spread"><p class="muted">${esc(current.description || '')}</p>
        ${parents.length ? '<button class="ghost" id="optionBack">返回上一级</button>' : ''}</div>
        ${related.length ? `<div class="rec-grid" style="grid-template-columns:1fr">${related.map((row, index) => RecCard(row, index, selections(slot))).join('')}</div>` : ''}
        <div class="option-grid" style="grid-template-columns:1fr">${children.map(child => OptionCard(child, selections(slot))).join('')}</div>
        <div class="divider"></div><button class="secondary" id="pickParent" ${current.selectable === false ? 'hidden disabled' : ''}>${selections(slot).includes(key) ? '取消选择' : '选择'}「${esc(current.name)}」</button>`);
      const pick = (id, row) => { toggle(slot, id, row); render(); show(); };
      $('#optionBack')?.addEventListener('click', () => { current = parents.pop(); show(); });
      $('#pickParent').onclick = () => pick(key);
      $$('#drawerBody [data-option]').forEach(button => button.onclick = () => {
        const child = known.get(button.dataset.option);
        if (child.children?.length) { parents.push(current); current = child; show(); }
        else pick(button.dataset.option);
      });
      $$('#drawerBody [data-rec]').forEach(button => button.onclick = () => pick(button.dataset.rec, rec.find(row => row?.option_key === button.dataset.rec)));
    }
    show();
  }

  function paintConfirm() {
    const summary = STEPS.slice(1, 8).map(({name, slot}) => `<dt>${name}</dt><dd>${esc(selections(slot).map(key => known.get(key)?.name || key).join('、') || '由设计阶段展开')}</dd>`).join('');
    $('#modalBody').innerHTML = stepsBar(8) + `<div class="wizard-confirm"><h2>确认立项卡</h2>
      <div class="card"><dl class="selection-summary"><dt>类型</dt><dd>${esc(names())}</dd>${summary}
        ${chapterCount ? `<dt>计划篇幅</dt><dd>${esc(chapterCount)} 章${targetWords ? ` · ${esc(targetWords)} 字` : ''}</dd>` : ''}</dl></div>
      ${methodChoices(selectedMethods, currentVersions)}
      ${selectedMethods.size ? '<button type="button" class="secondary" data-refresh-wizard-methods>刷新所选方法的版本</button>' : ''}
      <div class="divider"></div><div class="stack">
        <label class="field"><span>小说书名</span><input id="wizardTitle" maxlength="120" placeholder="给故事起一个暂定书名" value="${esc(title)}"></label>
        <label class="field"><span>一句话故事构想 <span class="error">*</span></span><textarea id="wizardIdea" rows="4" maxlength="12000" required placeholder="谁，在什么处境下，为了什么目标，必须做出怎样的选择？">${esc(idea)}</textarea></label>
        <label class="field"><span>硬约束（选填）</span><textarea id="wizardConstraints" rows="3" maxlength="12000" placeholder="必须保留的设定、不能发生的情节、阅读对象…">${esc(constraints)}</textarea></label>
        ${wizardMethods(useMethods, selectedMethods.size > 0)}
        <div class="notice">立项后会启动全书设计。模型未配置时，项目会保存并等待配置。</div>
      </div></div>`;
  }

  function submit() {
    if (!idea) { $('#wizardIdea').focus(); toast('请先填写一句话故事构想', true); return; }
    const payload = {
      title:title || '未命名小说', idea, constraints, genre_ids:types(),
      production_methods:useMethods ? {} : undefined,
      method_preferences:[...selectedMethods.values()].map(({id, version, slot}) => ({id, version, slot})),
      choices:types().map(id => ({slot:'genre', option_key:'genre.' + id, ...recMeta.get('genre.' + id)})),
      target_words:targetWords ? Number(targetWords) : undefined,
      chapter_count:chapterCount ? Number(chapterCount) : undefined,
      volume_count:volumeCount ? Number(volumeCount) : undefined,
    };
    for (const [slot, field] of Object.entries(fields)) {
      payload[field] = selections(slot);
      payload.choices.push(...selections(slot).map(option_key => ({slot, option_key, ...recMeta.get(option_key)})));
    }
    busy($('#wizardNext'), async () => {
      const result = await api.post('/novels', payload);
      const novel = result.novel || result;
      if (!novel.id) throw new Error('项目创建结果没有返回作品标识');
      dialog.close();
      document.dispatchEvent(new CustomEvent('studio:created', {bubbles:true}));
      location.hash = `#/studio/${enc(novel.id)}`;
      toast(result.run?.reason || '立项卡已保存，进入制作台');
    });
  }

  try {
    const data = await api.get('/genres');
    if (!alive()) return;
    genres = data.genres || [];
    combinations = data.combinations || [];
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
