/* ═══════════════════════════════════════════════════════════════
   Novel Workflow Studio v2 — Frontend Controller
   Zero external dependencies · Pure ES6 · Chinese UI
   ═══════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  /* ══════ STATE ══════ */
  const state = {
    status: null,
    projects: [],
    activeProject: "",
    overview: null,
    blueprint: null,
    selectedStage: "character_design",
    activeScene: null,
    routing: null,
    notifications: [],
    sidebarCollapsed: false,
  };

  const TAB_TITLES = {
    projects: ["01 · 项目与设定总览", "项目总览", "管理工作区项目、Brief 硬约束、Bible 设定、故事状态托管与分支版本。"],
    pipeline: ["02 · 14步创作流水线", "创作流水线", "可视化14步依赖契约、防遗忘账本，离线干跑任意构想的联合资料调度。"],
    scenes: ["03 · 章场工作台", "章场工作台", "管理大纲、POV 写作工作包、草稿录入、StateDelta 核验与批次验收。"],
    cards: ["04 · 卡片库与知情矩阵", "卡片知情", "版本化卡片管理，对照 WORLD 真相、READER 所知与角色 POV 认知。"],
    materials: ["05 · 资料库与F2台账", "资料台账", "检索已裁定方法原文与入步用法，排查 F2 待补缺口。"],
    routing: ["06 · API与模型配置", "模型配置", "切换离线/在线模式，配置 Carbon + Opus 5.5 双模型路由。"],
  };

  const CARD_TEMPLATES = {
    character: { name: "林沉", role: "基层刑警 / 主视角", want: "查清十年前旧港沉船真相", flaw: "过度执着程序外的旧证", boundaries: "不伪造证词", visibility: "public" },
    world: { title: "旧港潮汐与封存档案规则", rule: "每晚23点涨潮淹没栈桥", limits: "单人私调将触发督察记录", cost: "暴露调查方向", visibility: "public" },
    scene: { title: "雨夜重返三号栈桥", goal: "核对停表时间与涨潮水位", pov: "char_lin", characters: ["char_lin"], story_time: "1", conflict: "潮水提前漫上栈桥", allowed_disclosure: "仅限林沉现场目击", visibility: "author_only" },
    plot: { title: "沉船怀表线索链", conflict: "证词时间与潮汐表存在40分钟死角", consequence: "迫使主角重新调查昔日搭档", visibility: "author_only" },
    promise: { title: "停在23:15的铜怀表", setup: "第一章栈桥排水口发现停摆怀表", payoff: "揭晓当年真正拉闸封舱之人", visibility: "author_only" },
    style: { title: "冷峻克制近景叙事", guidance: "多用触觉、潮湿咸腥气味与短促动作句", check: "禁止直接替角色总结情绪形容词", visibility: "public" },
    taboo: { title: "视角与因果红线", constraint: "单场严禁越过当前POV知情边界", check: "逐段核对信息来源是否在POV已知范围", visibility: "public" },
  };

  /* ══════ UTILITIES ══════ */
  function $(id) { return document.getElementById(id); }
  function $$(sel) { return document.querySelectorAll(sel); }

  function esc(val) {
    return String(val == null ? "" : val)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  /* ══════ TOAST ══════ */
  function toast(msg, kind = "ok") {
    const el = $("toastBanner");
    el.textContent = msg;
    el.className = `toast ${kind} visible`;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => { el.classList.remove("visible"); }, 4500);
    addNotification(msg, kind);
  }

  /* ══════ NOTIFICATIONS ══════ */
  function addNotification(msg, kind = "ok") {
    state.notifications.unshift({ msg, kind, time: new Date().toLocaleTimeString() });
    if (state.notifications.length > 100) state.notifications.length = 100;
    renderNotifications();
  }

  function renderNotifications() {
    const list = $("notificationList");
    if (!state.notifications.length) {
      list.innerHTML = `<div class="muted small text-center" style="padding:20px">暂无操作记录</div>`;
      return;
    }
    list.innerHTML = state.notifications.slice(0, 50).map(n => `
      <div class="notification-item">
        <div>${esc(n.msg)}</div>
        <div class="time">${esc(n.time)}</div>
      </div>
    `).join("");
  }

  /* ══════ MODAL ══════ */
  function showModal(title, bodyHtml, buttons = []) {
    $("modalTitle").textContent = title;
    $("modalBody").innerHTML = bodyHtml;
    $("modalFooter").innerHTML = buttons.map((b, i) =>
      `<button class="btn ${b.cls || 'btn-primary'}" data-modal-btn="${i}">${esc(b.text)}</button>`
    ).join("");
    $("modalFooter").querySelectorAll("[data-modal-btn]").forEach((btn, i) => {
      btn.addEventListener("click", () => { closeModal(); if (buttons[i].onClick) buttons[i].onClick(); });
    });
    $("modalBackdrop").classList.add("open");
  }
  function closeModal() { $("modalBackdrop").classList.remove("open"); }

  /* ══════ LOADING ══════ */
  function setLoading(el, loading) {
    if (loading) {
      el.classList.add("relative");
      if (!el.querySelector(".loading-overlay")) {
        const ov = document.createElement("div");
        ov.className = "loading-overlay";
        ov.innerHTML = '<div class="loading-spinner"></div>';
        el.appendChild(ov);
      }
    } else {
      const ov = el.querySelector(".loading-overlay");
      if (ov) ov.remove();
      el.classList.remove("relative");
    }
  }

  /* ══════ API CLIENT ══════ */
  async function api(path, options = {}) {
    const opts = { headers: { "Content-Type": "application/json" }, ...options };
    if (opts.body && typeof opts.body !== "string") opts.body = JSON.stringify(opts.body);
    const resp = await fetch(path, opts);
    const data = await resp.json().catch(() => ({ error: `HTTP ${resp.status}` }));
    if (!resp.ok) throw new Error(data.error || `请求失败 (${resp.status})`);
    return data;
  }

  /* ══════ TAB ROUTING ══════ */
  function switchTab(tab) {
    $$(".nav-item").forEach(b => b.classList.toggle("active", b.dataset.tab === tab));
    $$(".tab-panel").forEach(p => p.classList.toggle("active", p.id === `tab-${tab}`));
    const meta = TAB_TITLES[tab] || [tab, tab, ""];
    $("viewTitle").textContent = meta[0];
    $("breadcrumbPage").textContent = meta[1];

    if (tab === "pipeline" && !state.blueprint) loadBlueprint().catch(e => toast(e.message, "err"));
    if (tab === "materials") {
      searchMaterials().catch(e => toast(e.message, "err"));
      searchLedger().catch(e => toast(e.message, "err"));
    }
    if (tab === "routing") loadRouting().catch(e => toast(e.message, "err"));
    if (tab === "cards" && state.activeProject) {
      renderCards();
      loadStateMatrix().catch(e => toast(e.message, "err"));
    }
  }

  /* ══════ SEARCH ══════ */
  function openSearch() { $("searchOverlay").classList.add("open"); $("searchInput").focus(); $("searchInput").value = ""; }
  function closeSearch() { $("searchOverlay").classList.remove("open"); }

  async function performSearch(query) {
    const box = $("searchResults");
    if (!query.trim()) {
      box.innerHTML = `<div class="search-hint">输入关键词开始搜索</div>`;
      return;
    }
    box.innerHTML = `<div class="search-hint"><div class="loading-spinner"></div></div>`;
    try {
      const results = [];
      // Search materials
      const matRes = await api(`/api/materials/search?q=${encodeURIComponent(query)}&limit=8`);
      (matRes.items || []).forEach(m => results.push({ type: "资料", label: m.key, sub: m.meaning || m.path, tab: "materials" }));
      // Search cards
      if (state.overview && state.overview.cards) {
        state.overview.cards.filter(c =>
          JSON.stringify(c).toLowerCase().includes(query.toLowerCase())
        ).slice(0, 5).forEach(c => results.push({ type: "卡片", label: `${c.card_id}@v${c.version}`, sub: c.kind, tab: "cards" }));
      }
      // Search scenes
      if (state.overview && state.overview.scenes) {
        state.overview.scenes.filter(s =>
          (s.card && s.card.title || "").includes(query) || s.id.includes(query)
        ).slice(0, 5).forEach(s => results.push({ type: "场景", label: (s.card && s.card.title) || s.id, sub: `第${s.index}场`, tab: "scenes" }));
      }

      if (!results.length) {
        box.innerHTML = `<div class="search-hint">无匹配结果</div>`;
        return;
      }
      box.innerHTML = results.map(r => `
        <div class="search-result-item" data-search-tab="${r.tab}">
          <div class="row-gap-xs"><span class="badge">${esc(r.type)}</span> <strong>${esc(r.label)}</strong></div>
          <div class="muted small">${esc(r.sub)}</div>
        </div>
      `).join("");
      box.querySelectorAll(".search-result-item").forEach(el => {
        el.addEventListener("click", () => { closeSearch(); switchTab(el.dataset.searchTab); });
      });
    } catch (e) {
      box.innerHTML = `<div class="search-hint">${esc(e.message)}</div>`;
    }
  }

  /* ══════ THEME ══════ */
  function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute("data-theme");
    const next = current === "light" ? "dark" : "light";
    html.setAttribute("data-theme", next);
    localStorage.setItem("nw-theme", next);
  }

  function loadTheme() {
    const saved = localStorage.getItem("nw-theme");
    if (saved) document.documentElement.setAttribute("data-theme", saved);
  }

  /* ══════ SIDEBAR ══════ */
  function toggleSidebar() {
    state.sidebarCollapsed = !state.sidebarCollapsed;
    $("appShell").classList.toggle("sidebar-collapsed", state.sidebarCollapsed);
    $("btnSidebarToggle").textContent = state.sidebarCollapsed ? "▶" : "◀";
  }

  /* ══════ TAB 1: PROJECTS ══════ */
  async function loadSystemAndProjects() {
    const [status, projResp] = await Promise.all([api("/api/status"), api("/api/projects")]);
    state.status = status;
    state.projects = projResp.projects || [];

    const pill = $("apiModePill");
    if (status.config_valid) {
      pill.className = "status-pill ready";
      pill.textContent = "模型配置已就绪";
    } else {
      pill.className = "status-pill offline";
      pill.textContent = "离线沙盘模式";
    }
    const cat = status.catalog || {};
    const f2 = status.f2_ledger || {};
    $("catalogSummaryMeta").textContent = cat.available
      ? `裁定资料 ${cat.total_sources.toLocaleString()} 条 · F2台账 ${f2.total_issues.toLocaleString()} 条`
      : "工作区尚未构建 catalog.db";

    const sel = $("globalProjectSelect");
    const prev = state.activeProject || sel.value;
    sel.innerHTML = `<option value="">-- 选择项目 (${state.projects.length}) --</option>` +
      state.projects.map(p => `<option value="${esc(p.dir_name)}">${esc(p.name)} (${esc(p.dir_name)})</option>`).join("");
    if (prev && state.projects.some(p => p.dir_name === prev)) {
      state.activeProject = prev;
    } else if (state.projects.length > 0 && !state.activeProject) {
      state.activeProject = state.projects[0].dir_name;
    }
    sel.value = state.activeProject;
    $("projectCountBadge").textContent = `${state.projects.length} 个`;
    renderProjectsList();
    if (state.activeProject) {
      await loadProjectOverview(state.activeProject);
    } else {
      $("projectDetailSection").classList.add("hidden");
      $("activeProjectBadges").innerHTML = `<span class="badge warn">未选项目</span>`;
      updateStats({});
    }
  }

  function updateStats(ov) {
    $("statChapters").textContent = ov.chapters ? ov.chapters.length : "-";
    $("statScenes").textContent = ov.scenes ? ov.scenes.length : "-";
    $("statCards").textContent = ov.cards ? ov.cards.length : "-";
    $("statDrafts").textContent = ov.scenes ? ov.scenes.reduce((a, s) => a + (s.drafts_count || 0), 0) : "-";
    $("statBriefVer").textContent = ov.briefs ? `v${ov.briefs.length}` : "-";
  }

  function renderProjectsList() {
    const box = $("projectsListContainer");
    if (!state.projects.length) {
      box.innerHTML = `<div class="muted small">暂无项目，请新建。</div>`;
      return;
    }
    box.innerHTML = state.projects.map(p => `
      <div class="list-item ${p.dir_name === state.activeProject ? "selected" : ""}" data-proj="${esc(p.dir_name)}">
        <div class="list-item-head">
          <strong>${esc(p.name)} <span class="muted mono">(${esc(p.dir_name)})</span></strong>
          <span class="badge ${p.managed_story ? "ok" : "warn"}">${p.managed_story ? `已托管 r${p.head ? p.head.revision : 0}` : "未托管"}</span>
        </div>
        <div class="muted small">Brief v${p.brief_versions || 0} · ${p.chapters_count || 0} 章 / ${p.scenes_count || 0} 场 · ${p.cards_count || 0} 卡片</div>
      </div>
    `).join("");
    box.querySelectorAll(".list-item").forEach(el => {
      el.addEventListener("click", async () => {
        state.activeProject = el.dataset.proj;
        $("globalProjectSelect").value = state.activeProject;
        renderProjectsList();
        await loadProjectOverview(state.activeProject);
      });
    });
  }

  async function loadProjectOverview(projName) {
    if (!projName) return;
    const ov = await api(`/api/projects/${encodeURIComponent(projName)}`);
    state.overview = ov;
    $("projectDetailSection").classList.remove("hidden");
    $("activeProjectBadges").innerHTML = `
      <span class="badge ${ov.managed_story ? "ok" : "warn"}">${ov.managed_story ? "已托管" : "未托管"}</span>
      <span class="badge">${ov.chapters.length} 章 / ${ov.scenes.length} 场</span>
      <span class="badge">${ov.cards.length} 卡片</span>
    `;
    updateStats(ov);

    const latestBrief = ov.briefs.length ? ov.briefs[ov.briefs.length - 1] : null;
    $("briefVersionBadge").textContent = latestBrief ? `v${latestBrief.version}` : "未创建";
    $("editBriefText").value = latestBrief ? latestBrief.text : "";
    $("editBriefConstraints").value = latestBrief ? latestBrief.constraints : "";

    $("managedStatusBadge").textContent = ov.managed_story ? "已启用 Story State" : "待初始化";
    $("managedStatusBadge").className = `badge ${ov.managed_story ? "ok" : "warn"}`;
    $("btnAdoptStory").disabled = ov.managed_story;

    $("branchesListBox").innerHTML = ov.branches.length
      ? ov.branches.map(b => `<div class="list-item"><div class="list-item-head"><span class="mono">${esc(b.id)}</span><span class="badge ok">head: r${b.head_revision}</span></div></div>`).join("")
      : `<div class="muted small">启用托管后自动生成 <code>main</code> 分支。</div>`;

    $("bibleEntriesBox").innerHTML = ov.bible.length
      ? ov.bible.slice().reverse().map(b => `
          <div class="list-item">
            <div class="list-item-head"><strong>[${esc(b.kind)}] ${esc(b.name)}</strong><span class="badge">v${b.version}</span></div>
            <div class="small muted truncate">${esc(b.body)}</div>
          </div>`).join("")
      : `<div class="muted small">暂无 Bible 条目。</div>`;

    renderOutlineAndScenes();
    renderCards();
  }

  /* ══════ TAB 2: PIPELINE ══════ */
  async function loadBlueprint() {
    const scope = $("pipelineScopeSelect").value;
    const bp = await api(`/api/pipeline/blueprint?scope=${encodeURIComponent(scope)}`);
    state.blueprint = bp;
    if (!bp.design_steps.some(s => s.stage === state.selectedStage)) {
      state.selectedStage = bp.design_steps[0].stage;
    }
    renderPipelineStrip();
    renderRuntimeSteps();
    await runStageSimulation();
  }

  function renderPipelineStrip() {
    const strip = $("pipelineStepsStrip");
    const steps = (state.blueprint && state.blueprint.design_steps) || [];
    strip.innerHTML = steps.map(s => {
      const isOpus = s.owner_hint.includes("Opus");
      return `
        <button class="step-chip ${s.stage === state.selectedStage ? "active" : ""}" data-stage="${esc(s.stage)}">
          <div class="list-item-head">
            <span class="mono small muted">#${s.step_no}</span>
            <span class="badge ${isOpus ? "opus" : "carbon"}">${esc(s.owner_hint)}</span>
          </div>
          <div class="step-chip-title">${esc(s.zh_title)}</div>
          <div class="muted small">前置: ${s.requires.length} 步 · ${(s.stage_material_chars / 1000).toFixed(1)}k字</div>
        </button>`;
    }).join("");
    strip.querySelectorAll(".step-chip").forEach(btn => {
      btn.addEventListener("click", () => {
        state.selectedStage = btn.dataset.stage;
        renderPipelineStrip();
        runStageSimulation();
      });
    });
  }

  function renderRuntimeSteps() {
    const box = $("runtimeStepsList");
    const list = (state.blueprint && state.blueprint.runtime_steps) || [];
    box.innerHTML = list.map(r => `
      <div class="list-item">
        <div class="list-item-head">
          <strong>${esc(r.zh)}</strong>
          <span class="badge ${r.owner_hint.includes("Opus") ? "opus" : "carbon"}">${esc(r.owner_hint)}</span>
        </div>
        <div class="small muted truncate">${esc(r.base_prompt)}</div>
      </div>
    `).join("");
  }

  async function runStageSimulation() {
    const bp = state.blueprint;
    if (!bp) return;
    const stepMeta = bp.design_steps.find(s => s.stage === state.selectedStage) || bp.design_steps[0];
    $("simStageTitle").textContent = `${stepMeta.zh_title} (${stepMeta.stage})`;
    $("simStageMetaBox").innerHTML = `
      <div><strong>前置步骤 (REQUIRES)：</strong>${stepMeta.requires.length ? stepMeta.requires.map(r => `<code>${esc(r)}</code>`).join(" → ") : "无"}</div>
      <div><strong>法定产物字段：</strong>${stepMeta.output_fields.map(f => `<code>${esc(f)}</code>`).join(", ")}</div>
      <div><strong>防遗忘守卫：</strong>${stepMeta.anti_forgetting_guards.map(g => `<div>• ${esc(g)}</div>`).join("")}</div>
    `;
    $("simStatsBadge").textContent = "计算中…";
    try {
      const res = await api("/api/pipeline/simulate", {
        method: "POST",
        body: {
          scope: $("pipelineScopeSelect").value,
          stage: state.selectedStage,
          brief_text: $("simBriefText").value,
          constraints: $("simConstraints").value,
          project_name: state.activeProject || null,
          simulate_prior_products: $("simPriorToggle").checked,
        },
      });
      $("simStatsBadge").textContent = `召回 ${res.sources_count || 0} 份 · Prompt ${res.rendered_prompt_chars || 0} 字`;

      const jp = res.joint_material_plan;
      $("simJointPlanBox").innerHTML = jp ? `
        <strong>多资料联合创作协同方案</strong>
        <div class="small muted">${esc(jp.rule)}</div>
        <div class="badge-row">
          ${(jp.drivers || []).map(x => `<span class="badge ok">驱动: ${esc(x)}</span>`).join("")}
          ${(jp.boundaries || []).map(x => `<span class="badge carbon">边界: ${esc(x)}</span>`).join("")}
          ${(jp.anchors_and_expression || []).map(x => `<span class="badge opus">锚点: ${esc(x)}</span>`).join("")}
          ${(jp.needs_instantiation_or_clause_guard || []).map(x => `<span class="badge warn">需实例化: ${esc(x)}</span>`).join("")}
        </div>
      ` : `<span class="muted small">本步无需多资料冲突仲裁。</span>`;

      const cl = res.continuity_ledger;
      $("simContinuityBox").innerHTML = cl ? `
        <strong>跨步防遗忘账本 (continuity_ledger)</strong>
        <pre class="mono small">${esc(JSON.stringify(cl, null, 2))}</pre>
      ` : `<span class="muted small">本步已直连全部前置，无需补偿。</span>`;

      $("simSourcesList").innerHTML = (res.sources || []).length
        ? res.sources.map(s => `
            <div class="list-item">
              <div class="list-item-head">
                <strong>${esc(s.key)} <span class="mono muted">(${esc(s.id)})</span></strong>
                <div class="row-gap-xs">
                  <span class="badge">${esc(s.profile)}</span>
                  <span class="badge ${s.source_state === "design_ready" ? "ok" : "warn"}">${esc(s.source_state)}</span>
                </div>
              </div>
              <div class="small">${esc(s.meaning)}</div>
              <div class="small muted truncate">${esc(s.step_use ?? s.original_preview ?? '')}</div>
            </div>`).join("")
        : `<div class="muted small">未召回资料。</div>`;

      $("simPromptPreview").textContent = res.rendered_prompt || "";
    } catch (err) {
      $("simStatsBadge").textContent = "异常";
      toast(err.message, "err");
    }
  }

  /* ══════ TAB 3: SCENES ══════ */
  function renderOutlineAndScenes() {
    const ov = state.overview;
    if (!ov) return;
    const chapSel = $("sceneChapSelect");
    chapSel.innerHTML = ov.chapters.length
      ? ov.chapters.map(c => `<option value="${esc(c.id)}">第${c.index}章 · ${esc(c.title)}</option>`).join("")
      : `<option value="">请先新建章节</option>`;
    $("chapIndex").value = ov.chapters.length + 1;

    const tree = $("outlineTreeBox");
    if (!ov.chapters.length) {
      tree.innerHTML = `<div class="muted small">暂无章节。</div>`;
      return;
    }
    tree.innerHTML = ov.chapters.map(ch => {
      const scenes = ov.scenes.filter(s => s.chapter_id === ch.id);
      return `
        <div class="subtle-box stack-form">
          <div class="list-item-head">
            <strong>第${ch.index}章 · ${esc(ch.title)}</strong>
            <span class="badge">${scenes.length} 场</span>
          </div>
          ${scenes.map(sc => `
            <div class="list-item ${state.activeScene && state.activeScene.id === sc.id ? "selected" : ""}" data-scene="${esc(sc.id)}">
              <div class="list-item-head">
                <span>第${sc.index}场 · ${esc((sc.card && sc.card.title) || sc.id.slice(0, 8))}</span>
                <span class="badge ${sc.accepted_draft_id ? "ok" : ""}">${sc.accepted_draft_id ? "已验收" : `草稿 ${sc.drafts_count}`}</span>
              </div>
              <div class="mono muted small truncate">${sc.card && sc.card.story ? `场景卡: ${esc(sc.card.story.scene_ref.card_id)}@v${sc.card.story.scene_ref.version} (t=${sc.card.story.story_order})` : "未绑定场景卡"}</div>
            </div>
          `).join("") || `<div class="muted small">本章暂无场景</div>`}
        </div>`;
    }).join("");
    tree.querySelectorAll("[data-scene]").forEach(el => {
      el.addEventListener("click", () => loadSceneWorkbench(el.dataset.scene));
    });
  }

  async function loadSceneWorkbench(sceneId) {
    if (!state.activeProject || !sceneId) return;
    const wb = await api(`/api/projects/${encodeURIComponent(state.activeProject)}/scenes/${encodeURIComponent(sceneId)}/workbench`);
    state.activeScene = wb.scene;
    $("activeSceneHeading").textContent = `第${wb.scene.chapter_index}章·第${wb.scene.index}场：${(wb.scene.card && wb.scene.card.title) || wb.scene.id}`;
    $("activeSceneMeta").textContent = wb.context_error
      ? `POV 提示：${wb.context_error}`
      : "POV 写作工作包已就绪。";

    renderPovContext(wb.context_preview);

    $("sceneDraftsList").innerHTML = wb.drafts.length
      ? wb.drafts.slice().reverse().map(d => `
          <div class="list-item" data-draft="${esc(d.id)}">
            <div class="list-item-head">
              <strong>草稿 v${d.version} <span class="mono muted">${esc(d.id.slice(0, 10))}</span></strong>
              <span class="badge ${d.status === "complete" ? "ok" : "warn"}">${esc(d.status)} · ${d.text.length}字</span>
            </div>
            <div class="small muted truncate">${esc(d.text.slice(0, 140))}${d.text.length > 140 ? "…" : ""}</div>
          </div>`).join("")
      : `<div class="muted small">暂无草稿。</div>`;

    if (wb.drafts.length) $("deltaDraftId").value = wb.drafts[wb.drafts.length - 1].id;
    $("sceneDraftsList").querySelectorAll("[data-draft]").forEach(el => {
      el.addEventListener("click", () => { $("deltaDraftId").value = el.dataset.draft; });
    });

    $("sceneDeltasList").innerHTML = wb.deltas.length
      ? wb.deltas.map(entry => {
          const d = entry.delta;
          const hard = (entry.check_findings || []).filter(f => f.severity === "hard");
          return `
            <div class="list-item">
              <div class="list-item-head">
                <strong class="mono">${esc(d.id)}</strong>
                <span class="badge ${hard.length ? "err" : "ok"}">${hard.length ? `硬冲突 ${hard.length}` : "通过"}</span>
              </div>
              <div class="small muted">变更: ${d.operations.length} · 草稿: ${esc(d.draft_id.slice(0, 10))}</div>
              ${!hard.length ? `<button class="btn btn-accent btn-accept-delta" data-delta="${esc(d.id)}" data-draft="${esc(d.draft_id)}">原子验收 (accept_batch)</button>` : `<div class="small" style="color:#fda4af">${esc(JSON.stringify(hard))}</div>`}
            </div>`;
        }).join("")
      : `<div class="muted small">暂无状态增量。</div>`;

    $("sceneDeltasList").querySelectorAll(".btn-accept-delta").forEach(btn => {
      btn.addEventListener("click", async () => {
        try {
          const res = await api(`/api/projects/${encodeURIComponent(state.activeProject)}/scenes/${encodeURIComponent(state.activeScene.id)}/accept`, {
            method: "POST", body: { draft_id: btn.dataset.draft, delta_id: btn.dataset.delta },
          });
          toast(`验收成功！revision ${res.head.revision}`);
          await loadProjectOverview(state.activeProject);
          await loadSceneWorkbench(state.activeScene.id);
        } catch (err) { toast(err.message, "err"); }
      });
    });

    await loadChapterLedger(wb.scene.chapter_index);
    populateZenSelects();
  }

  function renderPovContext(ctx) {
    const meter = $("povContextMeter");
    const box = $("povContextItemsBox");
    if (!ctx) { meter.classList.add("hidden"); box.innerHTML = ""; return; }
    meter.classList.remove("hidden");
    const pct = Math.min(100, Math.round(ctx.usage_ratio * 100));
    $("povMeterText").textContent = `上下文: ${ctx.total_chars.toLocaleString()} / ${ctx.char_limit.toLocaleString()} 字 (${pct}%)`;
    $("povScopeText").textContent = `branch=${ctx.scope.branch_id}@r${ctx.scope.revision} · t=${ctx.scope.story_order} · disclosure=[${ctx.disclosure.join(",")}]`;
    $("povMeterFill").style.width = `${pct}%`;

    box.innerHTML = ctx.items.map(it => `
      <div class="list-item">
        <div class="list-item-head">
          <strong class="mono">${esc(it.key)}</strong>
          <span class="badge">${esc(it.reason)} · ${it.chars}字</span>
        </div>
        <pre class="mono small muted" style="white-space:pre-wrap">${esc(it.content.slice(0, 400))}${it.content.length > 400 ? "…" : ""}</pre>
      </div>
    `).join("");
  }

  async function loadChapterLedger(chapterIdx) {
    if (!state.activeProject || !chapterIdx) return;
    try {
      const res = await api(`/api/projects/${encodeURIComponent(state.activeProject)}/chapters/${chapterIdx}/ledger`);
      if (!res.managed_story) {
        $("chapterLedgerBox").textContent = "启用 Story Adoption 后可查看。";
        return;
      }
      const st = res.chapter_state || {};
      const rec = res.summary && res.summary.record ? res.summary.record.author_record.summary : "未记录";
      $("chapterLedgerBox").innerHTML = `
        <div><strong>第${chapterIdx}章：</strong>${st.scope_complete ? "✅ 全部验收完毕" : `⏳ 待验收 ${(st.pending_scene_ids || []).length} 场`}</div>
        <div><strong>章总结：</strong>${esc(rec)}</div>
      `;
    } catch (err) {
      $("chapterLedgerBox").textContent = `提示：${err.message}`;
    }
  }

  /* ══════ TAB 4: CARDS & MATRIX ══════ */
  function fillCardTemplate() {
    const kind = $("cardKindSelect").value;
    const vis = $("cardVisibilitySelect").value;
    const tpl = { ...(CARD_TEMPLATES[kind] || {}), visibility: vis };
    if (vis === "holders") tpl.holders = ["char_lin"];
    $("cardBodyJson").value = JSON.stringify(tpl, null, 2);
    if (!$("cardIdInput").value) $("cardIdInput").value = `${kind}_01`;
  }

  function renderCards() {
    const cards = (state.overview && state.overview.cards) || [];
    $("cardsCountBadge").textContent = `${cards.length} 张`;
    const box = $("cardsListContainer");
    if (!cards.length) {
      box.innerHTML = `<div class="muted small">当前无卡片。</div>`;
      return;
    }
    box.innerHTML = cards.map(c => `
      <div class="list-item">
        <div class="list-item-head">
          <strong><span class="mono">${esc(c.card_id)}</span>@v${c.version} <span class="badge">${esc(c.kind)}</span></strong>
          <div class="row-gap-xs">
            <span class="badge">${esc(c.body.visibility)}</span>
            <span class="badge ${c.status === "approved" ? "ok" : "warn"}">${esc(c.status)}</span>
          </div>
        </div>
        <pre class="mono small muted" style="white-space:pre-wrap;max-height:60px;overflow:hidden">${esc(JSON.stringify(c.body))}</pre>
      </div>
    `).join("");
  }

  async function loadStateMatrix() {
    if (!state.activeProject) return;
    const order = Number($("matrixStoryOrder").value || 999999);
    const res = await api(`/api/projects/${encodeURIComponent(state.activeProject)}/state-matrix?story_order=${order}`);
    const wrap = $("stateMatrixContainer");
    if (!res.managed_story) {
      wrap.innerHTML = `<div class="muted small">未启用状态机托管。</div>`;
      return;
    }
    if (!res.matrix.length) {
      wrap.innerHTML = `<div class="muted small">revision ${res.head.revision} 尚无动态事实。知情主体：${res.holders.map(esc).join(", ")}</div>`;
      return;
    }
    wrap.innerHTML = `
      <table class="data-table">
        <thead><tr>
          <th>实体</th><th>属性</th>
          ${res.holders.map(h => `<th>${esc(h)}</th>`).join("")}
        </tr></thead>
        <tbody>
          ${res.matrix.map(row => `<tr>
            <td class="mono">${esc(row.entity_id)}</td>
            <td class="mono">${esc(row.predicate)}</td>
            ${res.holders.map(h => {
              const cells = row.cells[h] || [];
              return `<td>${cells.map(c => `<span class="badge ${c.claim === "fact" ? "ok" : "warn"}">${esc(c.claim)}</span> <code>${esc(JSON.stringify(c.value))}</code>`).join("<br/>") || `<span class="muted">—</span>`}</td>`;
            }).join("")}
          </tr>`).join("")}
        </tbody>
      </table>`;
  }

  /* ══════ TAB 5: MATERIALS & F2 ══════ */
  async function searchMaterials() {
    const q = $("matQueryInput").value;
    const st = $("matStateSelect").value;
    const stage = $("matStageSelect").value;
    const res = await api(`/api/materials/search?q=${encodeURIComponent(q)}&state=${encodeURIComponent(st)}&stage=${encodeURIComponent(stage)}&limit=40`);
    $("matSearchTotalBadge").textContent = `${(res.total || 0).toLocaleString()} 条`;
    const box = $("materialsResultList");
    if (!res.items || !res.items.length) {
      box.innerHTML = `<div class="muted small">无匹配资料。</div>`;
      return;
    }
    box.innerHTML = res.items.map(m => `
      <div class="list-item" data-mat-id="${esc(m.id)}">
        <div class="list-item-head">
          <strong>${esc(m.key)}</strong>
          <div class="row-gap-xs">
            <span class="badge">${esc(m.profile)}</span>
            <span class="badge ${m.state === "design_ready" ? "ok" : m.state === "reference" ? "warn" : "err"}">${esc(m.state)}</span>
          </div>
        </div>
        <div class="small muted truncate">${esc(m.meaning || m.path)}</div>
        <div class="badge-row">${(m.stages || []).map(s => `<span class="badge carbon">${esc(s)}</span>`).join("")}</div>
      </div>
    `).join("");
    box.querySelectorAll("[data-mat-id]").forEach(el => {
      el.addEventListener("click", () => loadMaterialDetail(el.dataset.matId));
    });
  }

  async function loadMaterialDetail(id) {
    const d = await api(`/api/materials/detail?id=${encodeURIComponent(id)}`);
    const usages = Object.entries(d.step_usages || {});
    $("materialDetailBox").innerHTML = `
      <div class="list-item-head">
        <strong>${esc(d.source.key)} <span class="mono muted">(${esc(d.source.id)})</span></strong>
        <span class="badge ${d.source_state === "design_ready" ? "ok" : "warn"}">${esc(d.source_state)} · ${esc(d.use_mode)}</span>
      </div>
      <div class="small muted">来源: ${esc(d.source.path || "")} · SHA256: <code>${esc((d.source.sha256 || "").slice(0, 16))}…</code> · 语义子句: ${d.semantic_clauses_count}</div>
      <div><strong>核心原义：</strong>${esc(d.meaning)}</div>
      <h4>各步骤【本步用法】</h4>
      ${usages.length ? usages.map(([st, txt]) => `
        <div class="subtle-box">
          <div class="badge carbon">${esc(st)}</div>
          <pre class="mono small" style="white-space:pre-wrap;margin-top:4px">${esc(txt)}</pre>
        </div>
      `).join("") : `<div class="muted small">通过通用字段契约约束。</div>`}
      <h4>原始不可变快照</h4>
      <pre class="code-preview">${esc(d.original_text)}</pre>
    `;
  }

  async function searchLedger() {
    const q = $("ledgerQueryInput").value;
    const disp = $("ledgerDispInput").value;
    const res = await api(`/api/ledger/search?q=${encodeURIComponent(q)}&disposition=${encodeURIComponent(disp)}&limit=40`);
    $("ledgerTotalBadge").textContent = `${(res.total || 0).toLocaleString()} 条`;
    const box = $("ledgerResultList");
    box.innerHTML = (res.items || []).map(r => {
      const loc = r.source_locator || {};
      const title = r.source_key || loc.key || loc.unit_id || r.issue_id || loc.path || r.unit_id || r.location || r.source_file || "台账条目";
      const st = r.disposition || r.status || r.issue_type || "待核查";
      const badgeCls = (st === "resolved" || st === "recovered_via_verified_archive") ? "ok" : st === "open" ? "warn" : "";
      return `
      <div class="list-item">
        <div class="list-item-head">
          <strong>#${r._line || ""} · ${esc(title)}</strong>
          <span class="badge ${badgeCls}">${esc(st)}</span>
        </div>
        <pre class="mono small muted" style="white-space:pre-wrap;max-height:80px;overflow:hidden">${esc(JSON.stringify(r, null, 2))}</pre>
      </div>`;
    }).join("") || `<div class="muted small">无匹配 F2 记录。</div>`;
  }

  /* ══════ TAB 6: ROUTING ══════ */
  async function loadRouting() {
    const r = await api("/api/config/routing");
    state.routing = r;

    $("envStatusBox").innerHTML = Object.entries(r.env_present || {}).map(([k, ok]) =>
      `<span class="badge ${ok ? "ok" : "warn"}">${esc(k)}: ${ok ? "已设置" : "未设置"}</span>`
    ).join("");

    const presetsGrid = $("routingPresetsGrid");
    presetsGrid.innerHTML = Object.values(r.presets || {}).map(p => `
      <div class="preset-card" data-preset="${esc(p.id)}">
        <div class="list-item-head">
          <strong>${esc(p.name)}</strong>
          <span class="badge ${p.live_api ? "opus" : "ok"}">${p.live_api ? "API 实测" : "零API离线"}</span>
        </div>
        <div class="small muted">${esc(p.description)}</div>
      </div>
    `).join("");

    const allStages = [...(r.design_stages || []), ...(r.runtime_stages || [])];
    $("stageModelsTableWrap").innerHTML = `
      <table class="data-table">
        <thead><tr><th>步骤</th><th>职责</th><th>推荐</th><th>专属覆盖模型</th></tr></thead>
        <tbody>
          ${allStages.map(s => `<tr>
            <td class="mono">${esc(s.stage)}</td>
            <td>${esc(s.zh)}</td>
            <td><span class="badge ${s.owner_hint.includes("Opus") ? "opus" : "carbon"}">${esc(s.owner_hint)}</span></td>
            <td><input type="text" class="input-control mono stage-model-input" data-stage="${esc(s.stage)}" placeholder="继承默认" /></td>
          </tr>`).join("")}
        </tbody>
      </table>`;

    if (r.current && r.valid) applyConfigToForm(r.current);
    else applyPreset("carbon_opus_dual");

    presetsGrid.querySelectorAll(".preset-card").forEach(el => {
      el.addEventListener("click", () => {
        presetsGrid.querySelectorAll(".preset-card").forEach(c => c.classList.remove("active"));
        el.classList.add("active");
        applyPreset(el.dataset.preset);
      });
    });
  }

  function applyConfigToForm(cfg) {
    $("cfgProvider").value = cfg.provider || "ollama";
    $("cfgModel").value = cfg.model || "gemini-4-carbon";
    $("cfgBaseUrl").value = cfg.base_url || "http://127.0.0.1:11434";
    $("cfgApiKeyEnv").value = cfg.api_key_env || "";
    $("cfgTimeout").value = cfg.timeout || 180;
    $("cfgTemp").value = (cfg.params && cfg.params.temperature != null) ? cfg.params.temperature : 0.3;
    const sm = cfg.stage_models || {};
    $$(".stage-model-input").forEach(inp => {
      const spec = sm[inp.dataset.stage];
      inp.value = typeof spec === "string" ? spec : (spec && spec.model ? spec.model : "");
    });
    previewRoutingToml();
  }

  function applyPreset(presetId) {
    const p = state.routing && state.routing.presets && state.routing.presets[presetId];
    if (!p) return;
    applyConfigToForm({ ...p.model, params: p.params, stage_models: p.stage_models });
  }

  function collectRoutingPayload() {
    const stage_models = {};
    $$(".stage-model-input").forEach(inp => {
      const val = inp.value.trim();
      if (val) stage_models[inp.dataset.stage] = { model: val };
    });
    const provider = $("cfgProvider").value;
    const params = { temperature: Number($("cfgTemp").value || 0.3) };
    if (provider === "openai_compat") params.max_tokens = 8192;
    return {
      model: {
        provider, base_url: $("cfgBaseUrl").value.trim(),
        model: $("cfgModel").value.trim(), api_key_env: $("cfgApiKeyEnv").value.trim(),
        timeout: Number($("cfgTimeout").value || 180),
      },
      params, source_driven: true, stage_models,
    };
  }

  async function previewRoutingToml() {
    try {
      const res = await api("/api/config/preview", { method: "POST", body: collectRoutingPayload() });
      $("configTomlPreview").textContent = res.toml;
    } catch (err) {
      $("configTomlPreview").textContent = `校验提示：${err.message}`;
    }
  }

  /* ══════ ZEN READER & DIFF ══════ */
  function populateZenSelects() {
    const opts = [];
    $("sceneDraftsList").querySelectorAll("[data-draft]").forEach((el, i) => {
      opts.push({ id: el.dataset.draft, label: `v${i + 1} (${el.dataset.draft.slice(0, 10)})` });
    });
    ["zenDraftA", "zenDraftB"].forEach(id => {
      const sel = $(id);
      const prev = sel.value;
      sel.innerHTML = `<option value="">选择版本</option>` +
        opts.map(o => `<option value="${esc(o.id)}">${esc(o.label)}</option>`).join("");
      sel.value = prev;
    });
  }

  function simpleDiff(textA, textB) {
    const parasA = textA.split(/\n\n+/);
    const parasB = textB.split(/\n\n+/);
    const maxLen = Math.max(parasA.length, parasB.length);
    const result = [];
    for (let i = 0; i < maxLen; i++) {
      const a = (parasA[i] || "").trim();
      const b = (parasB[i] || "").trim();
      result.push(a === b ? { type: "same", a, b } : { type: "changed", a, b });
    }
    return result;
  }

  function highlightDiffWords(oldText, newText) {
    const oldW = oldText.split(""), newW = newText.split("");
    let oldH = "", newH = "";
    let oi = 0, ni = 0;
    while (oi < oldW.length || ni < newW.length) {
      if (oi < oldW.length && ni < newW.length && oldW[oi] === newW[ni]) {
        oldH += esc(oldW[oi]); newH += esc(newW[ni]); oi++; ni++;
      } else if (oi < oldW.length && !newW.includes(oldW[oi], ni)) {
        oldH += `<mark class="del">${esc(oldW[oi])}</mark>`; oi++;
      } else if (ni < newW.length && !oldW.includes(newW[ni], oi)) {
        newH += `<mark class="add">${esc(newW[ni])}</mark>`; ni++;
      } else {
        if (oi < oldW.length) { oldH += `<mark class="del">${esc(oldW[oi])}</mark>`; oi++; }
        if (ni < newW.length) { newH += `<mark class="add">${esc(newW[ni])}</mark>`; ni++; }
      }
    }
    return { oldHtml: oldH, newHtml: newH };
  }

  async function renderZenDiff() {
    const idA = $("zenDraftA").value, idB = $("zenDraftB").value;
    if (!idA || !idB || !state.activeProject || !state.activeScene) return toast("请选择两个草稿版本", "err");
    try {
      const [dA, dB] = await Promise.all([
        api(`/api/projects/${encodeURIComponent(state.activeProject)}/scenes/${encodeURIComponent(state.activeScene.id)}/drafts/${encodeURIComponent(idA)}`),
        api(`/api/projects/${encodeURIComponent(state.activeProject)}/scenes/${encodeURIComponent(state.activeScene.id)}/drafts/${encodeURIComponent(idB)}`)
      ]);
      const diff = simpleDiff(dA.text || "", dB.text || "");
      $("zenDiffContent").innerHTML = diff.map((d, i) => {
        if (d.type === "same") return `<div class="diff-para"><div class="diff-side"><div class="diff-side-label">§${i + 1} 未改</div><div>${esc(d.a)}</div></div><div class="diff-side"><div class="diff-side-label">§${i + 1}</div><div>${esc(d.b)}</div></div></div>`;
        const hl = highlightDiffWords(d.a, d.b);
        return `<div class="diff-para"><div class="diff-side diff-side-a"><div class="diff-side-label">§${i + 1} A</div><div>${hl.oldHtml}</div></div><div class="diff-side diff-side-b"><div class="diff-side-label">§${i + 1} B</div><div>${hl.newHtml}</div></div></div>`;
      }).join("");
      $("zenDiffContainer").classList.remove("hidden");
      $("zenReaderContainer").classList.add("hidden");
      toast(`Diff：${diff.filter(d => d.type === "changed").length} 段有变更`);
    } catch (err) { toast(err.message, "err"); }
  }

  async function renderZenRead() {
    const idB = $("zenDraftB").value || $("zenDraftA").value;
    if (!idB || !state.activeProject || !state.activeScene) return toast("请选择草稿版本", "err");
    try {
      const draft = await api(`/api/projects/${encodeURIComponent(state.activeProject)}/scenes/${encodeURIComponent(state.activeScene.id)}/drafts/${encodeURIComponent(idB)}`);
      const paras = (draft.text || "").split(/\n\n+/).filter(Boolean);
      $("zenReaderContent").innerHTML = paras.map(p => `<p>${esc(p.trim())}</p>`).join("");
      $("zenReaderContainer").classList.remove("hidden");
      $("zenDiffContainer").classList.add("hidden");
      toast("沉浸阅读模式已开启");
    } catch (err) { toast(err.message, "err"); }
  }

  /* ══════ SVG RELATIONSHIP GRAPH ══════ */
  function renderRelationshipGraph() {
    const cards = (state.overview && state.overview.cards) || [];
    if (!cards.length) return toast("请先创建卡片", "err");
    const svg = $("relationSvg");
    svg.innerHTML = "";
    const W = 960, H = 600;
    const nodeMap = {}, nodes = [], edges = [];

    cards.forEach((c, i) => {
      const angle = (2 * Math.PI * i) / cards.length;
      const r = Math.min(W, H) * 0.35;
      const node = {
        id: c.card_id, kind: c.kind,
        label: c.body?.name || c.body?.title || c.card_id,
        x: W / 2 + r * Math.cos(angle), y: H / 2 + r * Math.sin(angle),
        data: c
      };
      nodes.push(node);
      nodeMap[c.card_id] = node;
    });

    cards.forEach(c => {
      const body = c.body || {};
      if (Array.isArray(body.characters)) body.characters.forEach(charId => { if (nodeMap[charId]) edges.push({ from: c.card_id, to: charId, label: "出场" }); });
      if (body.pov && nodeMap[body.pov]) edges.push({ from: c.card_id, to: body.pov, label: "POV" });
      if (Array.isArray(body.holders)) body.holders.forEach(h => { if (nodeMap[h]) edges.push({ from: c.card_id, to: h, label: "知情" }); });
    });

    // Render edges
    edges.forEach(e => {
      const from = nodeMap[e.from], to = nodeMap[e.to];
      if (!from || !to) return;
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", from.x); line.setAttribute("y1", from.y);
      line.setAttribute("x2", to.x); line.setAttribute("y2", to.y);
      line.classList.add("edge-line"); line.dataset.from = e.from; line.dataset.to = e.to;
      svg.appendChild(line);
      const lbl = document.createElementNS("http://www.w3.org/2000/svg", "text");
      lbl.setAttribute("x", (from.x + to.x) / 2); lbl.setAttribute("y", (from.y + to.y) / 2 - 6);
      lbl.classList.add("edge-label"); lbl.textContent = e.label;
      svg.appendChild(lbl);
    });

    // Render nodes
    nodes.forEach(n => {
      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.dataset.nodeId = n.id;
      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", n.x); circle.setAttribute("cy", n.y); circle.setAttribute("r", 22);
      circle.classList.add("node-circle", `node-${n.kind || "default"}`);
      g.appendChild(circle);
      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", n.x); text.setAttribute("y", n.y);
      text.classList.add("node-label");
      text.textContent = n.label.length > 6 ? n.label.slice(0, 5) + "…" : n.label;
      g.appendChild(text);
      const kindLabel = document.createElementNS("http://www.w3.org/2000/svg", "text");
      kindLabel.setAttribute("x", n.x); kindLabel.setAttribute("y", n.y + 34);
      kindLabel.classList.add("edge-label"); kindLabel.textContent = n.kind;
      g.appendChild(kindLabel);

      // Drag
      let dragging = false;
      circle.addEventListener("mousedown", e => {
        dragging = true; circle.style.cursor = "grabbing"; e.preventDefault();
      });
      document.addEventListener("mousemove", e => {
        if (!dragging) return;
        const svgRect = svg.getBoundingClientRect();
        n.x = (e.clientX - svgRect.left) * (W / svgRect.width);
        n.y = (e.clientY - svgRect.top) * (H / svgRect.height);
        circle.setAttribute("cx", n.x); circle.setAttribute("cy", n.y);
        text.setAttribute("x", n.x); text.setAttribute("y", n.y);
        kindLabel.setAttribute("x", n.x); kindLabel.setAttribute("y", n.y + 34);
        svg.querySelectorAll("line.edge-line").forEach(line => {
          if (line.dataset.from === n.id) { line.setAttribute("x1", n.x); line.setAttribute("y1", n.y); }
          if (line.dataset.to === n.id) { line.setAttribute("x2", n.x); line.setAttribute("y2", n.y); }
        });
        svg.querySelectorAll("text.edge-label").forEach((lbl, idx) => {
          if (idx < edges.length) {
            const ef = nodeMap[edges[idx].from], et = nodeMap[edges[idx].to];
            if (ef && et) { lbl.setAttribute("x", (ef.x + et.x) / 2); lbl.setAttribute("y", (ef.y + et.y) / 2 - 6); }
          }
        });
      });
      document.addEventListener("mouseup", () => { dragging = false; circle.style.cursor = "grab"; });
      svg.appendChild(g);
    });
    toast(`关系图：${nodes.length} 节点 · ${edges.length} 连接`);
  }

  /* ══════ JOB STEPPER ══════ */
  const JOB_STEPS = [
    { key: "plan", label: "设计总装冻结", icon: "📐" },
    { key: "write", label: "场景正文创作", icon: "✍️" },
    { key: "review", label: "独立审稿核验", icon: "🔍" },
    { key: "revise", label: "修订与润色", icon: "✏️" },
    { key: "state_extract", label: "事实增量提取", icon: "📊" },
    { key: "fact_review", label: "事实证据复核", icon: "✅" },
    { key: "accept", label: "批次验收归档", icon: "📦" },
  ];

  async function refreshJobDrawer() {
    if (!state.activeProject) {
      $("jobStepperContent").innerHTML = `<div class="muted small">请先选择项目。</div>`;
      return;
    }
    try {
      const res = await api(`/api/projects/${encodeURIComponent(state.activeProject)}/jobs`);
      const jobs = res.jobs || [];
      if (!jobs.length) {
        $("jobStepperContent").innerHTML = `<div class="muted small">暂无运行中的任务。接入 API 并启动 <code>novel resume</code> 后，任务流将在此显示。</div>`;
        return;
      }
      $("jobStepperContent").innerHTML = jobs.map(job => {
        const currentStep = job.current_step || "plan";
        return `
          <div class="subtle-box">
            <div class="list-item-head" style="margin-bottom:6px">
              <strong>Job ${esc(job.id.slice(0, 12))} · ${esc(job.scope || "scene")}</strong>
              <span class="badge ${job.status === "running" ? "ok" : job.status === "error" ? "err" : ""}">${esc(job.status)}</span>
            </div>
            <div class="job-stepper-content">
              ${JOB_STEPS.map(s => {
                const stepStatus = s.key === currentStep ? (job.status === "error" ? "error" : "active")
                  : JOB_STEPS.findIndex(x => x.key === s.key) < JOB_STEPS.findIndex(x => x.key === currentStep) ? "done" : "waiting";
                return `
                  <div class="job-step-row ${stepStatus}">
                    <div class="job-step-icon">${s.icon}</div>
                    <div class="job-step-info"><h4>${esc(s.label)}</h4><div class="small">${s.key}</div></div>
                    <div class="job-step-actions">
                      ${stepStatus === "active" && job.needs_confirm ? `<button class="btn btn-accent">确认</button>` : ""}
                      ${stepStatus === "error" ? `<button class="btn btn-ghost">重试</button>` : ""}
                    </div>
                  </div>`;
              }).join("")}
            </div>
          </div>`;
      }).join("");
    } catch (err) {
      $("jobStepperContent").innerHTML = `<div class="muted small">任务队列暂不可用（${esc(err.message)}）。</div>`;
    }
  }

  /* ══════ KEYBOARD SHORTCUTS ══════ */
  function setupKeyboard() {
    document.addEventListener("keydown", e => {
      // Ctrl+K: search
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        $("searchOverlay").classList.contains("open") ? closeSearch() : openSearch();
      }
      // Escape: close overlays
      if (e.key === "Escape") {
        closeSearch();
        closeModal();
        $("notificationPanel").classList.remove("open");
      }
      // Ctrl+1-6: switch tabs
      if ((e.ctrlKey || e.metaKey) && e.key >= "1" && e.key <= "6") {
        e.preventDefault();
        const tabs = ["projects", "pipeline", "scenes", "cards", "materials", "routing"];
        switchTab(tabs[parseInt(e.key) - 1]);
      }
      // Ctrl+S: save (prevent browser default)
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        toast("当前为离线沙盘模式，所有更改已自动保存至本地工作区。");
      }
    });
  }

  /* ══════ EVENT WIRING ══════ */
  function bindEvents() {
    // Nav
    $$(".nav-item").forEach(btn => {
      btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });

    // Sidebar
    $("btnSidebarToggle").addEventListener("click", toggleSidebar);
    $("btnMobileMenu").addEventListener("click", () => $("sidebar").classList.toggle("mobile-open"));

    // Theme
    $("btnThemeToggle").addEventListener("click", toggleTheme);

    // Search
    $("searchTrigger").addEventListener("click", openSearch);
    $("searchOverlay").addEventListener("click", e => { if (e.target === $("searchOverlay")) closeSearch(); });
    let searchTimer;
    $("searchInput").addEventListener("input", e => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => performSearch(e.target.value), 300);
    });

    // Notifications
    $("btnNotifications").addEventListener("click", () => $("notificationPanel").classList.toggle("open"));
    $("btnCloseNotifications").addEventListener("click", () => $("notificationPanel").classList.remove("open"));

    // Modal
    $("modalClose").addEventListener("click", closeModal);
    $("modalBackdrop").addEventListener("click", e => { if (e.target === $("modalBackdrop")) closeModal(); });

    // Projects
    $("btnRefreshAll").addEventListener("click", () => loadSystemAndProjects().catch(e => toast(e.message, "err")));
    $("globalProjectSelect").addEventListener("change", async e => {
      state.activeProject = e.target.value;
      renderProjectsList();
      if (state.activeProject) await loadProjectOverview(state.activeProject);
    });

    $("formCreateProject").addEventListener("submit", async e => {
      e.preventDefault();
      try {
        const dir = $("newProjDir").value.trim();
        await api("/api/projects", {
          method: "POST",
          body: { dir_name: dir, title: $("newProjTitle").value.trim(), brief_text: $("newProjBrief").value, constraints: $("newProjConstraints").value },
        });
        state.activeProject = dir;
        $("formCreateProject").reset();
        toast(`项目 ${dir} 创建成功！`);
        await loadSystemAndProjects();
      } catch (err) { toast(err.message, "err"); }
    });

    $("formSaveBrief").addEventListener("submit", async e => {
      e.preventDefault();
      if (!state.activeProject) return toast("请先选择项目", "err");
      try {
        const b = await api(`/api/projects/${encodeURIComponent(state.activeProject)}/brief`, {
          method: "POST", body: { text: $("editBriefText").value, constraints: $("editBriefConstraints").value },
        });
        toast(`已保存 Brief v${b.version}`);
        await loadProjectOverview(state.activeProject);
      } catch (err) { toast(err.message, "err"); }
    });

    $("formAdoptStory").addEventListener("submit", async e => {
      e.preventDefault();
      if (!state.activeProject) return toast("请先选择项目", "err");
      try {
        const entities = $("adoptEntities").value.split(",").map(s => s.trim()).filter(Boolean);
        const predicates = $("adoptPredicates").value.split(",").map(s => s.trim()).filter(Boolean);
        await api(`/api/projects/${encodeURIComponent(state.activeProject)}/adopt`, {
          method: "POST", body: { entities, predicates, include_approved_cards: true },
        });
        toast("故事状态机已启用（main@r0）！");
        await loadSystemAndProjects();
      } catch (err) { toast(err.message, "err"); }
    });

    $("formSaveBible").addEventListener("submit", async e => {
      e.preventDefault();
      if (!state.activeProject) return toast("请先选择项目", "err");
      try {
        await api(`/api/projects/${encodeURIComponent(state.activeProject)}/bible`, {
          method: "POST", body: { kind: $("bibleKind").value, name: $("bibleName").value, body: $("bibleBody").value },
        });
        $("bibleName").value = ""; $("bibleBody").value = "";
        toast("Bible 条目已保存");
        await loadProjectOverview(state.activeProject);
      } catch (err) { toast(err.message, "err"); }
    });

    // Pipeline
    $("pipelineScopeSelect").addEventListener("change", () => loadBlueprint());
    $("btnRunStageSim").addEventListener("click", () => runStageSimulation());

    // Scenes
    $("formAddChapter").addEventListener("submit", async e => {
      e.preventDefault();
      if (!state.activeProject) return toast("请先选择项目", "err");
      try {
        await api(`/api/projects/${encodeURIComponent(state.activeProject)}/chapters`, {
          method: "POST", body: { index: Number($("chapIndex").value), title: $("chapTitle").value },
        });
        $("chapTitle").value = "";
        toast("章节已添加");
        await loadProjectOverview(state.activeProject);
      } catch (err) { toast(err.message, "err"); }
    });

    $("formAddScene").addEventListener("submit", async e => {
      e.preventDefault();
      if (!state.activeProject) return toast("请先选择项目", "err");
      try {
        const card = { title: $("sceneTitleInput").value.trim() };
        const refId = $("sceneRefCardId").value.trim();
        if (refId) card.story = { scene_ref: { card_id: refId, version: 1 }, story_order: Number($("sceneStoryOrder").value || 1) };
        await api(`/api/projects/${encodeURIComponent(state.activeProject)}/scenes`, {
          method: "POST", body: { chapter_id: $("sceneChapSelect").value, index: Number($("sceneIndex").value), card },
        });
        $("sceneTitleInput").value = "";
        toast("场景已创建");
        await loadProjectOverview(state.activeProject);
      } catch (err) { toast(err.message, "err"); }
    });

    $("btnInspectPovContext").addEventListener("click", async () => {
      if (!state.activeProject || !state.activeScene) return toast("请先选择场景", "err");
      try {
        const ctx = await api(`/api/projects/${encodeURIComponent(state.activeProject)}/scenes/${encodeURIComponent(state.activeScene.id)}/context?char_limit=${Number($("ctxCharLimit").value || 24000)}`);
        renderPovContext(ctx);
        toast("POV 工作包已刷新");
      } catch (err) { toast(err.message, "err"); }
    });

    $("btnSaveManualDraft").addEventListener("click", async () => {
      if (!state.activeProject || !state.activeScene) return toast("请先选择场景", "err");
      try {
        await api(`/api/projects/${encodeURIComponent(state.activeProject)}/scenes/${encodeURIComponent(state.activeScene.id)}/draft`, {
          method: "POST", body: { text: $("manualDraftText").value },
        });
        toast("草稿已保存");
        await loadSceneWorkbench(state.activeScene.id);
      } catch (err) { toast(err.message, "err"); }
    });

    $("btnSaveDelta").addEventListener("click", async () => {
      if (!state.activeProject || !state.activeScene) return toast("请先选择场景", "err");
      try {
        let ops;
        try { ops = JSON.parse($("deltaOpsJson").value || "[]"); }
        catch (_) { throw new Error("Operations JSON 格式不正确"); }
        const res = await api(`/api/projects/${encodeURIComponent(state.activeProject)}/scenes/${encodeURIComponent(state.activeScene.id)}/delta`, {
          method: "POST", body: { draft_id: $("deltaDraftId").value.trim(), operations: ops },
        });
        toast(`StateDelta 已保存，发现 ${res.findings.length} 项`);
        await loadSceneWorkbench(state.activeScene.id);
      } catch (err) { toast(err.message, "err"); }
    });

    $("btnLoadChapterLedger").addEventListener("click", () => {
      if (state.activeScene) loadChapterLedger(state.activeScene.chapter_index);
    });

    $("btnSaveChapterSummary").addEventListener("click", async () => {
      if (!state.activeProject || !state.activeScene) return toast("请先选择场景", "err");
      try {
        await api(`/api/projects/${encodeURIComponent(state.activeProject)}/chapters/${state.activeScene.chapter_index}/summary`, {
          method: "POST", body: { summary: $("chapterSummaryInput").value },
        });
        toast("章总结已记录！");
        await loadChapterLedger(state.activeScene.chapter_index);
      } catch (err) { toast(err.message, "err"); }
    });

    // Cards
    $("btnFillCardTemplate").addEventListener("click", fillCardTemplate);
    $("cardKindSelect").addEventListener("change", fillCardTemplate);
    $("cardVisibilitySelect").addEventListener("change", fillCardTemplate);

    $("btnSaveCard").addEventListener("click", async () => {
      if (!state.activeProject) return toast("请先选择项目", "err");
      try {
        let body;
        try { body = JSON.parse($("cardBodyJson").value); }
        catch (_) { throw new Error("卡片 JSON 格式不正确"); }
        const saved = await api(`/api/projects/${encodeURIComponent(state.activeProject)}/cards`, {
          method: "POST",
          body: { card_id: $("cardIdInput").value.trim(), kind: $("cardKindSelect").value, body, auto_approve: $("cardAutoApprove").checked, apply_to_branch: $("cardApplyBranch").checked },
        });
        toast(`卡片 ${saved.card_id}@v${saved.version} 已保存`);
        await loadProjectOverview(state.activeProject);
      } catch (err) { toast(err.message, "err"); }
    });

    // Zen Reader & Diff
    $("btnZenDiff").addEventListener("click", renderZenDiff);
    $("btnZenRead").addEventListener("click", renderZenRead);

    // SVG Graph
    $("btnRenderGraph").addEventListener("click", renderRelationshipGraph);

    // Job Stepper
    $("btnRefreshJobs").addEventListener("click", refreshJobDrawer);

    // Materials & F2
    $("btnLoadMatrix").addEventListener("click", () => loadStateMatrix().catch(e => toast(e.message, "err")));
    $("btnSearchMaterials").addEventListener("click", () => searchMaterials().catch(e => toast(e.message, "err")));
    $("btnSearchLedger").addEventListener("click", () => searchLedger().catch(e => toast(e.message, "err")));

    // Config
    $("btnPreviewConfig").addEventListener("click", previewRoutingToml);
    $("btnSaveConfig").addEventListener("click", async () => {
      try {
        await api("/api/config/save", { method: "POST", body: collectRoutingPayload() });
        toast("config.toml 已写入磁盘！");
        await loadSystemAndProjects();
        await loadRouting();
      } catch (err) { toast(err.message, "err"); }
    });
  }

  /* ══════ INIT ══════ */
  loadTheme();
  fillCardTemplate();
  bindEvents();
  setupKeyboard();
  loadSystemAndProjects().catch(err => toast(err.message, "err"));
})();
