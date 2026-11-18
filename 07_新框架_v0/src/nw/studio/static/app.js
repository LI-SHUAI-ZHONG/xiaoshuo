/* Novel Workflow Studio Frontend Controller (Zero external dependencies, clean ES6) */
(function () {
  const state = {
    status: null,
    projects: [],
    activeProject: "",
    overview: null,
    blueprint: null,
    selectedStage: "character_design",
    activeScene: null,
    routing: null,
  };

  const TAB_TITLES = {
    projects: ["01 · 项目与设定总览", "管理本地工作区项目、Brief 硬约束、Bible 设定、故事状态托管（Story Adoption）与分支版本。"],
    pipeline: ["02 · 14步创作与联合资料沙盘", "可视化检视 7/14 步依赖契约、防遗忘账本（continuity_ledger），并离线干跑任意构想的联合资料调度。"],
    scenes: ["03 · 章场工作台与POV上下文", "管理章场大纲、实时生成受限 POV 写作工作包、录入样章草稿、核验 StateDelta 并执行批次验收与章总结。"],
    cards: ["04 · 卡片库与多视角知情矩阵", "维护不可变版本化卡片（人物/世界/场景/伏笔/禁忌），对照 WORLD 真相、READER 所知与各角色 POV 认知。"],
    materials: ["05 · 六大资料库与F2问题台账", "检索 22,941 条已裁定方法原文与入步用法，排查 F2 统一问题台账中的待补原始资料缺口。"],
    routing: ["06 · API接入与双模型分工配置", "暂不接 API 时保持离线沙盘；实测阶段可一键切换 Carbon + Opus 5.5 分步骤路由并安全生成 config.toml。"],
  };

  const CARD_TEMPLATES = {
    character: { name: "林沉", role: "基层刑警 / 主视角", want: "查清十年前旧港沉船真相", flaw: "过度执着程序外的旧证", boundaries: "不伪造证词", visibility: "public" },
    world: { title: "旧港潮汐与封存档案规则", rule: "每晚23点涨潮淹没栈桥；十年前案卷需双人签字调阅", limits: "单人私调将触发督察记录", cost: "暴露调查方向", visibility: "public" },
    scene: { title: "雨夜重返三号栈桥", goal: "核对目击者声称的停表时间与涨潮水位", pov: "char_lin", characters: ["char_lin"], story_time: "1", conflict: "潮水提前漫上栈桥且证物箱锁死", allowed_disclosure: "仅限林沉现场目击与随身旧怀表", visibility: "author_only" },
    plot: { title: "沉船怀表线索链", conflict: "证词时间与潮汐表存在40分钟死角", consequence: "迫使主角重新调查昔日搭档", visibility: "author_only" },
    promise: { title: "停在23:15的铜怀表", setup: "第一章栈桥排水口发现背面刻字的停摆怀表", payoff: "揭晓当年真正拉闸封舱之人", visibility: "author_only" },
    style: { title: "冷峻克制近景叙事", guidance: "多用触觉、潮湿咸腥气味与短促动作句承载心理压力", check: "禁止直接替角色总结情绪形容词", visibility: "public" },
    taboo: { title: "视角与因果红线", constraint: "单场严禁越过当前POV知情边界读取他人内心；严禁无代价巧合破局", check: "逐段核对信息来源是否在POV已知或现场可见范围", visibility: "public" },
  };

  function $(id) {
    return document.getElementById(id);
  }

  function esc(val) {
    return String(val == null ? "" : val)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function toast(msg, kind = "ok") {
    const el = $("toastBanner");
    el.textContent = msg;
    el.className = `toast ${kind}`;
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => el.classList.add("hidden"), 5000);
  }

  async function api(path, options = {}) {
    const opts = { headers: { "Content-Type": "application/json" }, ...options };
    if (opts.body && typeof opts.body !== "string") {
      opts.body = JSON.stringify(opts.body);
    }
    const resp = await fetch(path, opts);
    const data = await resp.json().catch(() => ({ error: `HTTP ${resp.status}` }));
    if (!resp.ok) {
      throw new Error(data.error || `请求失败 (${resp.status})`);
    }
    return data;
  }

  function switchTab(tab) {
    document.querySelectorAll(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === `tab-${tab}`));
    const meta = TAB_TITLES[tab] || [tab, ""];
    $("viewTitle").textContent = meta[0];
    $("viewSubtitle").textContent = meta[1];
    if (tab === "pipeline" && !state.blueprint) loadBlueprint();
    if (tab === "materials") {
      searchMaterials();
      searchLedger();
    }
    if (tab === "routing") loadRouting();
    if (tab === "cards" && state.activeProject) {
      renderCards();
      loadStateMatrix();
    }
  }

  async function loadSystemAndProjects() {
    const [status, projResp] = await Promise.all([api("/api/status"), api("/api/projects")]);
    state.status = status;
    state.projects = projResp.projects || [];

    const pill = $("apiModePill");
    if (status.config_valid) {
      pill.className = "status-pill ready";
      pill.textContent = "模型配置已就绪（可随时运行）";
    } else {
      pill.className = "status-pill offline";
      pill.textContent = "暂不接 API · 离线沙盘模式";
    }
    const cat = status.catalog || {};
    const f2 = status.f2_ledger || {};
    $("catalogSummaryMeta").textContent = cat.available
      ? `已索引裁定资料 ${cat.total_sources.toLocaleString()} 条 · F2台账 ${f2.total_issues.toLocaleString()} 条`
      : "当前工作区尚未构建 catalog.db";

    const sel = $("globalProjectSelect");
    const prev = state.activeProject || sel.value;
    sel.innerHTML = `<option value="">-- 请选择或新建项目 (${state.projects.length}) --</option>` +
      state.projects.map((p) => `<option value="${esc(p.dir_name)}">${esc(p.name)} (${esc(p.dir_name)})</option>`).join("");
    if (prev && state.projects.some((p) => p.dir_name === prev)) {
      state.activeProject = prev;
    } else if (state.projects.length > 0 && !state.activeProject) {
      state.activeProject = state.projects[0].dir_name;
    }
    sel.value = state.activeProject;
    renderProjectsList();
    if (state.activeProject) {
      await loadProjectOverview(state.activeProject);
    } else {
      $("projectDetailSection").classList.add("hidden");
      $("activeProjectBadges").innerHTML = `<span class="badge warn">未选项目</span>`;
    }
  }

  function renderProjectsList() {
    const box = $("projectsListContainer");
    if (!state.projects.length) {
      box.innerHTML = `<div class="muted small">当前 workspace 下暂无项目，请在左侧新建第一个小说项目。</div>`;
      return;
    }
    box.innerHTML = state.projects.map((p) => `
      <div class="list-item ${p.dir_name === state.activeProject ? "selected" : ""}" data-proj="${esc(p.dir_name)}">
        <div class="list-item-head">
          <strong>${esc(p.name)} <span class="muted mono">(${esc(p.dir_name)})</span></strong>
          <span class="badge ${p.managed_story ? "ok" : "warn"}">${p.managed_story ? `已托管 r${p.head ? p.head.revision : 0}` : "传统未托管"}</span>
        </div>
        <div class="muted small">Brief v${p.brief_versions || 0} · ${p.chapters_count || 0} 章 / ${p.scenes_count || 0} 场 · 卡片 ${p.cards_count || 0} 张</div>
      </div>
    `).join("");
    box.querySelectorAll(".list-item").forEach((el) => {
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
      <span class="badge ${ov.managed_story ? "ok" : "warn"}">${ov.managed_story ? "状态机已托管" : "未托管"}</span>
      <span class="badge">${ov.chapters.length} 章 / ${ov.scenes.length} 场</span>
      <span class="badge">${ov.cards.length} 卡片</span>
    `;
    const latestBrief = ov.briefs.length ? ov.briefs[ov.briefs.length - 1] : null;
    $("briefVersionBadge").textContent = latestBrief ? `v${latestBrief.version}` : "未创建";
    $("editBriefText").value = latestBrief ? latestBrief.text : "";
    $("editBriefConstraints").value = latestBrief ? latestBrief.constraints : "";

    $("managedStatusBadge").textContent = ov.managed_story ? "已启用 Story State" : "待初始化";
    $("managedStatusBadge").className = `badge ${ov.managed_story ? "ok" : "warn"}`;
    $("btnAdoptStory").disabled = ov.managed_story;

    $("branchesListBox").innerHTML = ov.branches.length
      ? ov.branches.map((b) => `<div class="list-item"><div class="list-item-head"><span class="mono">${esc(b.id)}</span><span class="badge ok">head revision: ${b.head_revision}</span></div></div>`).join("")
      : `<div class="muted small">启用托管后将自动生成 <code>main</code> 主干版本链。</div>`;

    $("bibleEntriesBox").innerHTML = ov.bible.length
      ? ov.bible.slice().reverse().map((b) => `
          <div class="list-item">
            <div class="list-item-head"><strong>[${esc(b.kind)}] ${esc(b.name)}</strong><span class="badge">v${b.version}</span></div>
            <div class="small muted">${esc(b.body)}</div>
          </div>`).join("")
      : `<div class="muted small">暂无 Bible 备忘条目。</div>`;

    renderOutlineAndScenes();
    renderCards();
  }

  /* ---------- TAB 2: 14-STEP PIPELINE & JOINT MATERIAL DRY-RUN ---------- */

  async function loadBlueprint() {
    const scope = $("pipelineScopeSelect").value;
    const bp = await api(`/api/pipeline/blueprint?scope=${encodeURIComponent(scope)}`);
    state.blueprint = bp;
    if (!bp.design_steps.some((s) => s.stage === state.selectedStage)) {
      state.selectedStage = bp.design_steps[0].stage;
    }
    renderPipelineStrip();
    renderRuntimeSteps();
    await runStageSimulation();
  }

  function renderPipelineStrip() {
    const strip = $("pipelineStepsStrip");
    const steps = (state.blueprint && state.blueprint.design_steps) || [];
    strip.innerHTML = steps.map((s) => {
      const isOpus = s.owner_hint.includes("Opus");
      return `
        <button class="step-chip ${s.stage === state.selectedStage ? "active" : ""}" data-stage="${esc(s.stage)}">
          <div class="list-item-head">
            <span class="mono small muted">#${s.step_no}</span>
            <span class="badge ${isOpus ? "opus" : "carbon"}">${esc(s.owner_hint)}</span>
          </div>
          <div class="step-chip-title">${esc(s.zh_title)}</div>
          <div class="muted small">直连前置: ${s.requires.length} 步 · 资料说明 ${(s.stage_material_chars / 1000).toFixed(1)}k字</div>
        </button>
      `;
    }).join("");
    strip.querySelectorAll(".step-chip").forEach((btn) => {
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
    box.innerHTML = list.map((r) => `
      <div class="list-item">
        <div class="list-item-head">
          <strong>${esc(r.zh)}</strong>
          <span class="badge ${r.owner_hint.includes("Opus") ? "opus" : "carbon"}">${esc(r.owner_hint)}</span>
        </div>
        <div class="small muted">${esc(r.base_prompt)}</div>
      </div>
    `).join("");
  }

  async function runStageSimulation() {
    const bp = state.blueprint;
    if (!bp) return;
    const stepMeta = bp.design_steps.find((s) => s.stage === state.selectedStage) || bp.design_steps[0];
    $("simStageTitle").textContent = `${stepMeta.zh_title} (${stepMeta.stage})`;
    $("simStageMetaBox").innerHTML = `
      <div><strong>直连前置步骤 (REQUIRES)：</strong>${stepMeta.requires.length ? stepMeta.requires.map((r) => `<code>${esc(r)}</code>`).join(" → ") : "无（起始/独立收口步）"}</div>
      <div><strong>本步法定产物字段：</strong>${stepMeta.output_fields.map((f) => `<code>${esc(f)}</code>`).join(", ")}</div>
      <div><strong>防遗忘与防崩塌守卫：</strong>${stepMeta.anti_forgetting_guards.map((g) => `<div>• ${esc(g)}</div>`).join("")}</div>
    `;
    $("simStatsBadge").textContent = "检索计算中…";
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
      $("simStatsBadge").textContent = `召回 ${res.sources_count || 0} 份资料 · Prompt ${res.rendered_prompt_chars || 0} 字符`;

      const jp = res.joint_material_plan;
      $("simJointPlanBox").innerHTML = jp ? `
        <strong>多资料联合创作协同方案（joint_material_plan）</strong>
        <div class="small muted">${esc(jp.rule)}</div>
        <div class="badge-row">
          ${(jp.drivers || []).map((x) => `<span class="badge ok">驱动推进: ${esc(x)}</span>`).join("")}
          ${(jp.boundaries || []).map((x) => `<span class="badge carbon">边界约束: ${esc(x)}</span>`).join("")}
          ${(jp.anchors_and_expression || []).map((x) => `<span class="badge opus">锚点表达: ${esc(x)}</span>`).join("")}
          ${(jp.needs_instantiation_or_clause_guard || []).map((x) => `<span class="badge warn">需结合本书实例化: ${esc(x)}</span>`).join("")}
        </div>
      ` : `<span class="muted small">本步召回少于2份资料或当前环境无资料库，无需启动多资料冲突仲裁器。</span>`;

      const cl = res.continuity_ledger;
      $("simContinuityBox").innerHTML = cl ? `
        <strong>跨步防遗忘账本（continuity_ledger · 自动补偿非直连前置约束）</strong>
        <pre class="mono small">${esc(JSON.stringify(cl, null, 2))}</pre>
      ` : `<span class="muted small">本步已直连全部所需前置步骤，无需额外补偿跨步账本。</span>`;

      $("simSourcesList").innerHTML = (res.sources || []).length
        ? res.sources.map((s) => `
            <div class="list-item">
              <div class="list-item-head">
                <strong>${esc(s.key)} <span class="mono muted">(${esc(s.id)})</span></strong>
                <div class="row-gap-xs">
                  <span class="badge">${esc(s.profile)}</span>
                  <span class="badge ${s.source_state === "design_ready" ? "ok" : "warn"}">${esc(s.source_state)}</span>
                </div>
              </div>
              <div class="small">${esc(s.meaning)}</div>
              <div class="small muted">${esc(s.original_preview)}</div>
            </div>
          `).join("")
        : `<div class="muted small">未召回资料（或当前处于空白测试工作区）。</div>`;

      $("simPromptPreview").textContent = res.rendered_prompt || "";
    } catch (err) {
      $("simStatsBadge").textContent = "干跑异常";
      toast(err.message, "err");
    }
  }

  /* ---------- TAB 3: SCENES, POV WORK PACKAGE & DELTA ---------- */

  function renderOutlineAndScenes() {
    const ov = state.overview;
    if (!ov) return;
    const chapSel = $("sceneChapSelect");
    chapSel.innerHTML = ov.chapters.length
      ? ov.chapters.map((c) => `<option value="${esc(c.id)}">第${c.index}章 · ${esc(c.title)}</option>`).join("")
      : `<option value="">请先新建章节</option>`;
    $("chapIndex").value = ov.chapters.length + 1;

    const tree = $("outlineTreeBox");
    if (!ov.chapters.length) {
      tree.innerHTML = `<div class="muted small">暂无章节，请在上方创建第一章。</div>`;
      return;
    }
    tree.innerHTML = ov.chapters.map((ch) => {
      const scenes = ov.scenes.filter((s) => s.chapter_id === ch.id);
      return `
        <div class="subtle-box stack-form">
          <div class="list-item-head">
            <strong>第 ${ch.index} 章 · ${esc(ch.title)}</strong>
            <span class="badge">${scenes.length} 场</span>
          </div>
          ${scenes.map((sc) => `
            <div class="list-item ${state.activeScene && state.activeScene.id === sc.id ? "selected" : ""}" data-scene="${esc(sc.id)}">
              <div class="list-item-head">
                <span>第 ${sc.index} 场 · ${esc((sc.card && sc.card.title) || sc.id.slice(0, 8))}</span>
                <span class="badge ${sc.accepted_draft_id ? "ok" : ""}">${sc.accepted_draft_id ? "已验收" : `草稿 ${sc.drafts_count}`}</span>
              </div>
              <div class="mono muted small">${sc.card && sc.card.story ? `绑定场景卡: ${esc(sc.card.story.scene_ref.card_id)}@v${sc.card.story.scene_ref.version} (t=${sc.card.story.story_order})` : "未绑定版本化场景卡"}</div>
            </div>
          `).join("") || `<div class="muted small">本章暂无场景</div>`}
        </div>
      `;
    }).join("");

    tree.querySelectorAll("[data-scene]").forEach((el) => {
      el.addEventListener("click", () => loadSceneWorkbench(el.dataset.scene));
    });
  }

  async function loadSceneWorkbench(sceneId) {
    if (!state.activeProject || !sceneId) return;
    const wb = await api(`/api/projects/${encodeURIComponent(state.activeProject)}/scenes/${encodeURIComponent(sceneId)}/workbench`);
    state.activeScene = wb.scene;
    $("activeSceneHeading").textContent = `第${wb.scene.chapter_index}章·第${wb.scene.index}场：${(wb.scene.card && wb.scene.card.title) || wb.scene.id}`;
    $("activeSceneMeta").textContent = wb.context_error
      ? `POV 工作包提示：${wb.context_error}（请先启用状态机托管并绑定已批准的 scene 卡与 POV 人物卡）`
      : "POV 写作工作包已就绪，严格隔离非本视角知情信息。";

    renderPovContext(wb.context_preview);

    $("sceneDraftsList").innerHTML = wb.drafts.length
      ? wb.drafts.slice().reverse().map((d) => `
          <div class="list-item" data-draft="${esc(d.id)}">
            <div class="list-item-head">
              <strong>草稿 v${d.version} <span class="mono muted">${esc(d.id.slice(0, 10))}</span></strong>
              <span class="badge ${d.status === "complete" ? "ok" : "warn"}">${esc(d.status)} · ${d.text.length}字</span>
            </div>
            <div class="small muted">${esc(d.text.slice(0, 140))}${d.text.length > 140 ? "…" : ""}</div>
          </div>
        `).join("")
      : `<div class="muted small">暂无草稿，可在上方直接录入样章进行离线验收测试。</div>`;

    if (wb.drafts.length) {
      $("deltaDraftId").value = wb.drafts[wb.drafts.length - 1].id;
    }
    $("sceneDraftsList").querySelectorAll("[data-draft]").forEach((el) => {
      el.addEventListener("click", () => {
        $("deltaDraftId").value = el.dataset.draft;
      });
    });

    $("sceneDeltasList").innerHTML = wb.deltas.length
      ? wb.deltas.map((entry) => {
          const d = entry.delta;
          const hard = (entry.check_findings || []).filter((f) => f.severity === "hard");
          return `
            <div class="list-item">
              <div class="list-item-head">
                <strong class="mono">${esc(d.id)}</strong>
                <span class="badge ${hard.length ? "err" : "ok"}">${hard.length ? `硬冲突 ${hard.length}` : "check_delta 通过"}</span>
              </div>
              <div class="small muted">变更项: ${d.operations.length} · 关联草稿: ${esc(d.draft_id.slice(0, 10))}</div>
              ${!hard.length ? `<button class="btn btn-accent btn-accept-delta" data-delta="${esc(d.id)}" data-draft="${esc(d.draft_id)}">原子验收并推进分支版本 (accept_batch)</button>` : `<div class="small" style="color:#fda4af">${esc(JSON.stringify(hard))}</div>`}
            </div>
          `;
        }).join("")
      : `<div class="muted small">暂无状态增量记录。</div>`;

    $("sceneDeltasList").querySelectorAll(".btn-accept-delta").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          const res = await api(`/api/projects/${encodeURIComponent(state.activeProject)}/scenes/${encodeURIComponent(state.activeScene.id)}/accept`, {
            method: "POST",
            body: { draft_id: btn.dataset.draft, delta_id: btn.dataset.delta },
          });
          toast(`验收成功！分支已推进至 revision ${res.head.revision}，正文已导出至 正文/ 目录`);
          await loadProjectOverview(state.activeProject);
          await loadSceneWorkbench(state.activeScene.id);
        } catch (err) {
          toast(err.message, "err");
        }
      });
    });

    await loadChapterLedger(wb.scene.chapter_index);
  }

  function renderPovContext(ctx) {
    const meter = $("povContextMeter");
    const box = $("povContextItemsBox");
    if (!ctx) {
      meter.classList.add("hidden");
      box.innerHTML = "";
      return;
    }
    meter.classList.remove("hidden");
    const pct = Math.min(100, Math.round(ctx.usage_ratio * 100));
    $("povMeterText").textContent = `上下文占用：${ctx.total_chars.toLocaleString()} / ${ctx.char_limit.toLocaleString()} 字符 (${pct}%)`;
    $("povScopeText").textContent = `branch=${ctx.scope.branch_id}@r${ctx.scope.revision} · story_order=${ctx.scope.story_order} · disclosure=[${ctx.disclosure.join(",")}]`;
    $("povMeterFill").style.width = `${pct}%`;

    box.innerHTML = ctx.items.map((it) => `
      <div class="list-item">
        <div class="list-item-head">
          <strong class="mono">${esc(it.key)}</strong>
          <span class="badge">${esc(it.reason)} · ${it.chars}字</span>
        </div>
        <pre class="mono small muted" style="white-space:pre-wrap">${esc(it.content.slice(0, 420))}${it.content.length > 420 ? "…" : ""}</pre>
      </div>
    `).join("");
  }

  async function loadChapterLedger(chapterIdx) {
    if (!state.activeProject || !chapterIdx) return;
    try {
      const res = await api(`/api/projects/${encodeURIComponent(state.activeProject)}/chapters/${chapterIdx}/ledger`);
      if (!res.managed_story) {
        $("chapterLedgerBox").textContent = "启用 Story Adoption 后可在此检视整章状态承接与章总结。";
        return;
      }
      const st = res.chapter_state || {};
      const rec = res.summary && res.summary.record ? res.summary.record.author_record.summary : "尚未记录章总结";
      $("chapterLedgerBox").innerHTML = `
        <div><strong>第 ${chapterIdx} 章完整度：</strong>${st.scope_complete ? "✅ 本章已批准场景全部验收完毕" : `⏳ 待验收场景数：${(st.pending_scene_ids || []).length}`}</div>
        <div><strong>当前章总结：</strong>${esc(rec)}</div>
      `;
    } catch (err) {
      $("chapterLedgerBox").textContent = `读取章节台账提示：${err.message}`;
    }
  }

  /* ---------- TAB 4: CARDS & STATE MATRIX ---------- */

  function fillCardTemplate() {
    const kind = $("cardKindSelect").value;
    const vis = $("cardVisibilitySelect").value;
    const tpl = { ...(CARD_TEMPLATES[kind] || {}), visibility: vis };
    if (vis === "holders") tpl.holders = ["char_lin"];
    $("cardBodyJson").value = JSON.stringify(tpl, null, 2);
    if (!$("cardIdInput").value) {
      $("cardIdInput").value = `${kind}_01`;
    }
  }

  function renderCards() {
    const cards = (state.overview && state.overview.cards) || [];
    $("cardsCountBadge").textContent = `${cards.length} 张`;
    const box = $("cardsListContainer");
    if (!cards.length) {
      box.innerHTML = `<div class="muted small">当前项目尚无卡片，可在左侧用模板快速创建人物卡、世界卡与场景卡。</div>`;
      return;
    }
    box.innerHTML = cards.map((c) => `
      <div class="list-item">
        <div class="list-item-head">
          <strong><span class="mono">${esc(c.card_id)}</span>@v${c.version} <span class="badge">${esc(c.kind)}</span></strong>
          <div class="row-gap-xs">
            <span class="badge">${esc(c.body.visibility)}</span>
            <span class="badge ${c.status === "approved" ? "ok" : "warn"}">${esc(c.status)}</span>
          </div>
        </div>
        <pre class="mono small muted" style="white-space:pre-wrap">${esc(JSON.stringify(c.body))}</pre>
      </div>
    `).join("");
  }

  async function loadStateMatrix() {
    if (!state.activeProject) return;
    const order = Number($("matrixStoryOrder").value || 999999);
    const res = await api(`/api/projects/${encodeURIComponent(state.activeProject)}/state-matrix?story_order=${order}`);
    const wrap = $("stateMatrixContainer");
    if (!res.managed_story) {
      wrap.innerHTML = `<div class="muted small">该项目尚未启用 Story Adoption 状态机托管。</div>`;
      return;
    }
    if (!res.matrix.length) {
      wrap.innerHTML = `<div class="muted small">当前分支 revision ${res.head.revision} 尚无已记录的动态事实（可通过场景 StateDelta 验收写入）。知情主体：${res.holders.map(esc).join(", ")}</div>`;
      return;
    }
    wrap.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th>实体 (entity_id)</th>
            <th>属性 (predicate)</th>
            ${res.holders.map((h) => `<th>${esc(h)}</th>`).join("")}
          </tr>
        </thead>
        <tbody>
          ${res.matrix.map((row) => `
            <tr>
              <td class="mono">${esc(row.entity_id)}</td>
              <td class="mono">${esc(row.predicate)}</td>
              ${res.holders.map((h) => {
                const cells = row.cells[h] || [];
                return `<td>${cells.map((c) => `<span class="badge ${c.claim === "fact" ? "ok" : "warn"}">${esc(c.claim)}</span> <code>${esc(JSON.stringify(c.value))}</code>`).join("<br/>") || `<span class="muted">—</span>`}</td>`;
              }).join("")}
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
  }

  /* ---------- TAB 5: MATERIALS & F2 LEDGER ---------- */

  async function searchMaterials() {
    const q = $("matQueryInput").value;
    const st = $("matStateSelect").value;
    const stage = $("matStageSelect").value;
    const res = await api(`/api/materials/search?q=${encodeURIComponent(q)}&state=${encodeURIComponent(st)}&stage=${encodeURIComponent(stage)}&limit=40`);
    $("matSearchTotalBadge").textContent = `${(res.total || 0).toLocaleString()} 条匹配`;
    const box = $("materialsResultList");
    if (!res.items || !res.items.length) {
      box.innerHTML = `<div class="muted small">无匹配资料条目。</div>`;
      return;
    }
    box.innerHTML = res.items.map((m) => `
      <div class="list-item" data-mat-id="${esc(m.id)}">
        <div class="list-item-head">
          <strong>${esc(m.key)}</strong>
          <div class="row-gap-xs">
            <span class="badge">${esc(m.profile)}</span>
            <span class="badge ${m.state === "design_ready" ? "ok" : m.state === "reference" ? "warn" : "err"}">${esc(m.state)}</span>
          </div>
        </div>
        <div class="small muted">${esc(m.meaning || m.path)}</div>
        <div class="badge-row">${(m.stages || []).map((s) => `<span class="badge carbon">${esc(s)}</span>`).join("")}</div>
      </div>
    `).join("");
    box.querySelectorAll("[data-mat-id]").forEach((el) => {
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
      <div class="small muted">来源路径：${esc(d.source.path || "")} · SHA256: <code>${esc((d.source.sha256 || "").slice(0, 16))}…</code> · 语义子句数：${d.semantic_clauses_count}</div>
      <div><strong>核心原义：</strong>${esc(d.meaning)}</div>
      <h4>进入各创作步骤的精确【本步用法】</h4>
      ${usages.length ? usages.map(([st, txt]) => `
        <div class="subtle-box">
          <div class="badge carbon">${esc(st)}</div>
          <pre class="mono small" style="white-space:pre-wrap;margin-top:6px">${esc(txt)}</pre>
        </div>
      `).join("") : `<div class="muted small">通过通用字段契约与语义子句直接约束。</div>`}
      <h4>原始资料不可变快照文本</h4>
      <pre class="code-preview">${esc(d.original_text)}</pre>
    `;
  }

  async function searchLedger() {
    const q = $("ledgerQueryInput").value;
    const disp = $("ledgerDispInput").value;
    const res = await api(`/api/ledger/search?q=${encodeURIComponent(q)}&disposition=${encodeURIComponent(disp)}&limit=40`);
    $("ledgerTotalBadge").textContent = `${(res.total || 0).toLocaleString()} 条记录`;
    const box = $("ledgerResultList");
    box.innerHTML = (res.items || []).map((r) => `
      <div class="list-item">
        <div class="list-item-head">
          <strong>#${r._line || ""} · ${esc(r.source_key || r.unit_id || r.location || r.source_file || "台账条目")}</strong>
          <span class="badge warn">${esc(r.disposition || r.issue_type || "待核查")}</span>
        </div>
        <pre class="mono small muted" style="white-space:pre-wrap">${esc(JSON.stringify(r, null, 2))}</pre>
      </div>
    `).join("") || `<div class="muted small">没有匹配的 F2 台账记录。</div>`;
  }

  /* ---------- TAB 6: ROUTING & API READINESS ---------- */

  async function loadRouting() {
    const r = await api("/api/config/routing");
    state.routing = r;

    $("envStatusBox").innerHTML = Object.entries(r.env_present || {}).map(([k, ok]) =>
      `<span class="badge ${ok ? "ok" : "warn"}">${esc(k)}: ${ok ? "已设置" : "未设置"}</span>`
    ).join("");

    const presetsGrid = $("routingPresetsGrid");
    presetsGrid.innerHTML = Object.values(r.presets || {}).map((p) => `
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
        <thead><tr><th>步骤标识</th><th>步骤职责</th><th>能力推荐</th><th>专属覆盖模型名（可留空继承默认）</th></tr></thead>
        <tbody>
          ${allStages.map((s) => `
            <tr>
              <td class="mono">${esc(s.stage)}</td>
              <td>${esc(s.zh)}</td>
              <td><span class="badge ${s.owner_hint.includes("Opus") ? "opus" : "carbon"}">${esc(s.owner_hint)}</span></td>
              <td><input type="text" class="input-control mono stage-model-input" data-stage="${esc(s.stage)}" placeholder="默认继承基座模型" /></td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;

    if (r.current && r.valid) {
      applyConfigToForm(r.current);
    } else {
      applyPreset("carbon_opus_dual");
    }

    presetsGrid.querySelectorAll(".preset-card").forEach((el) => {
      el.addEventListener("click", () => {
        presetsGrid.querySelectorAll(".preset-card").forEach((c) => c.classList.remove("active"));
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
    document.querySelectorAll(".stage-model-input").forEach((inp) => {
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
    document.querySelectorAll(".stage-model-input").forEach((inp) => {
      const val = inp.value.trim();
      if (val) stage_models[inp.dataset.stage] = { model: val };
    });
    const provider = $("cfgProvider").value;
    const params = { temperature: Number($("cfgTemp").value || 0.3) };
    if (provider === "openai_compat") params.max_tokens = 8192;
    return {
      model: {
        provider,
        base_url: $("cfgBaseUrl").value.trim(),
        model: $("cfgModel").value.trim(),
        api_key_env: $("cfgApiKeyEnv").value.trim(),
        timeout: Number($("cfgTimeout").value || 180),
      },
      params,
      source_driven: true,
      stage_models,
    };
  }

  async function previewRoutingToml() {
    try {
      const res = await api("/api/config/preview", { method: "POST", body: collectRoutingPayload() });
      $("configTomlPreview").textContent = res.toml;
    } catch (err) {
      $("configTomlPreview").textContent = `配置校验提示：${err.message}`;
    }
  }

  /* ---------- EVENT WIRING ---------- */

  function bindEvents() {
    document.querySelectorAll(".nav-item").forEach((btn) => {
      btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });

    $("btnRefreshAll").addEventListener("click", () => loadSystemAndProjects().catch((e) => toast(e.message, "err")));
    $("globalProjectSelect").addEventListener("change", async (e) => {
      state.activeProject = e.target.value;
      renderProjectsList();
      if (state.activeProject) await loadProjectOverview(state.activeProject);
    });

    $("formCreateProject").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const dir = $("newProjDir").value.trim();
        await api("/api/projects", {
          method: "POST",
          body: {
            dir_name: dir,
            title: $("newProjTitle").value.trim(),
            brief_text: $("newProjBrief").value,
            constraints: $("newProjConstraints").value,
          },
        });
        state.activeProject = dir;
        $("formCreateProject").reset();
        toast(`项目 ${dir} 创建成功！`);
        await loadSystemAndProjects();
      } catch (err) {
        toast(err.message, "err");
      }
    });

    $("formSaveBrief").addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!state.activeProject) return toast("请先选择项目", "err");
      try {
        const b = await api(`/api/projects/${encodeURIComponent(state.activeProject)}/brief`, {
          method: "POST",
          body: { text: $("editBriefText").value, constraints: $("editBriefConstraints").value },
        });
        toast(`已保存 Brief v${b.version}`);
        await loadProjectOverview(state.activeProject);
      } catch (err) {
        toast(err.message, "err");
      }
    });

    $("formAdoptStory").addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!state.activeProject) return toast("请先选择项目", "err");
      try {
        const entities = $("adoptEntities").value.split(",").map((s) => s.trim()).filter(Boolean);
        const predicates = $("adoptPredicates").value.split(",").map((s) => s.trim()).filter(Boolean);
        await api(`/api/projects/${encodeURIComponent(state.activeProject)}/adopt`, {
          method: "POST",
          body: { entities, predicates, include_approved_cards: true },
        });
        toast("已成功启用故事状态机托管（main@r0）！");
        await loadSystemAndProjects();
      } catch (err) {
        toast(err.message, "err");
      }
    });

    $("formSaveBible").addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!state.activeProject) return toast("请先选择项目", "err");
      try {
        await api(`/api/projects/${encodeURIComponent(state.activeProject)}/bible`, {
          method: "POST",
          body: { kind: $("bibleKind").value, name: $("bibleName").value, body: $("bibleBody").value },
        });
        $("bibleName").value = "";
        $("bibleBody").value = "";
        toast("Bible 条目已保存");
        await loadProjectOverview(state.activeProject);
      } catch (err) {
        toast(err.message, "err");
      }
    });

    $("pipelineScopeSelect").addEventListener("change", () => loadBlueprint());
    $("btnRunStageSim").addEventListener("click", () => runStageSimulation());

    $("formAddChapter").addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!state.activeProject) return toast("请先选择项目", "err");
      try {
        await api(`/api/projects/${encodeURIComponent(state.activeProject)}/chapters`, {
          method: "POST",
          body: { index: Number($("chapIndex").value), title: $("chapTitle").value },
        });
        $("chapTitle").value = "";
        toast("章节已添加");
        await loadProjectOverview(state.activeProject);
      } catch (err) {
        toast(err.message, "err");
      }
    });

    $("formAddScene").addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!state.activeProject) return toast("请先选择项目", "err");
      try {
        const card = { title: $("sceneTitleInput").value.trim() };
        const refId = $("sceneRefCardId").value.trim();
        if (refId) {
          card.story = { scene_ref: { card_id: refId, version: 1 }, story_order: Number($("sceneStoryOrder").value || 1) };
        }
        await api(`/api/projects/${encodeURIComponent(state.activeProject)}/scenes`, {
          method: "POST",
          body: { chapter_id: $("sceneChapSelect").value, index: Number($("sceneIndex").value), card },
        });
        $("sceneTitleInput").value = "";
        toast("场景已创建");
        await loadProjectOverview(state.activeProject);
      } catch (err) {
        toast(err.message, "err");
      }
    });

    $("btnInspectPovContext").addEventListener("click", async () => {
      if (!state.activeProject || !state.activeScene) return toast("请先在左侧点击一个场景", "err");
      try {
        const ctx = await api(`/api/projects/${encodeURIComponent(state.activeProject)}/scenes/${encodeURIComponent(state.activeScene.id)}/context?char_limit=${Number($("ctxCharLimit").value || 24000)}`);
        renderPovContext(ctx);
        toast("POV 工作包已刷新");
      } catch (err) {
        toast(err.message, "err");
      }
    });

    $("btnSaveManualDraft").addEventListener("click", async () => {
      if (!state.activeProject || !state.activeScene) return toast("请先选择场景", "err");
      try {
        await api(`/api/projects/${encodeURIComponent(state.activeProject)}/scenes/${encodeURIComponent(state.activeScene.id)}/draft`, {
          method: "POST",
          body: { text: $("manualDraftText").value },
        });
        toast("样章草稿已保存");
        await loadSceneWorkbench(state.activeScene.id);
      } catch (err) {
        toast(err.message, "err");
      }
    });

    $("btnSaveDelta").addEventListener("click", async () => {
      if (!state.activeProject || !state.activeScene) return toast("请先选择场景", "err");
      try {
        const ops = JSON.parse($("deltaOpsJson").value || "[]");
        const res = await api(`/api/projects/${encodeURIComponent(state.activeProject)}/scenes/${encodeURIComponent(state.activeScene.id)}/delta`, {
          method: "POST",
          body: { draft_id: $("deltaDraftId").value.trim(), operations: ops },
        });
        toast(`StateDelta 已保存，发现问题数：${res.findings.length}`);
        await loadSceneWorkbench(state.activeScene.id);
      } catch (err) {
        toast(err.message, "err");
      }
    });

    $("btnLoadChapterLedger").addEventListener("click", () => {
      if (state.activeScene) loadChapterLedger(state.activeScene.chapter_index);
    });

    $("btnSaveChapterSummary").addEventListener("click", async () => {
      if (!state.activeProject || !state.activeScene) return toast("请先选择一个场景以定位章节", "err");
      try {
        await api(`/api/projects/${encodeURIComponent(state.activeProject)}/chapters/${state.activeScene.chapter_index}/summary`, {
          method: "POST",
          body: { summary: $("chapterSummaryInput").value },
        });
        toast("章总结已记录并锚定至当前分支版本！");
        await loadChapterLedger(state.activeScene.chapter_index);
      } catch (err) {
        toast(err.message, "err");
      }
    });

    $("btnFillCardTemplate").addEventListener("click", fillCardTemplate);
    $("cardKindSelect").addEventListener("change", fillCardTemplate);
    $("cardVisibilitySelect").addEventListener("change", fillCardTemplate);

    $("btnSaveCard").addEventListener("click", async () => {
      if (!state.activeProject) return toast("请先选择项目", "err");
      try {
        const body = JSON.parse($("cardBodyJson").value);
        const saved = await api(`/api/projects/${encodeURIComponent(state.activeProject)}/cards`, {
          method: "POST",
          body: {
            card_id: $("cardIdInput").value.trim(),
            kind: $("cardKindSelect").value,
            body,
            auto_approve: $("cardAutoApprove").checked,
            apply_to_branch: $("cardApplyBranch").checked,
          },
        });
        toast(`卡片 ${saved.card_id}@v${saved.version} 已保存 (${saved.status})`);
        await loadProjectOverview(state.activeProject);
      } catch (err) {
        toast(err.message, "err");
      }
    });

    $("btnLoadMatrix").addEventListener("click", () => loadStateMatrix().catch((e) => toast(e.message, "err")));
    $("btnSearchMaterials").addEventListener("click", () => searchMaterials().catch((e) => toast(e.message, "err")));
    $("btnSearchLedger").addEventListener("click", () => searchLedger().catch((e) => toast(e.message, "err")));
    $("btnPreviewConfig").addEventListener("click", previewRoutingToml);
    $("btnSaveConfig").addEventListener("click", async () => {
      try {
        await api("/api/config/save", { method: "POST", body: collectRoutingPayload() });
        toast("config.toml 已通过严格安全校验并写入磁盘！");
        await loadSystemAndProjects();
        await loadRouting();
      } catch (err) {
        toast(err.message, "err");
      }
    });
  }

  fillCardTemplate();
  bindEvents();
  loadSystemAndProjects().catch((err) => toast(err.message, "err"));
})();
