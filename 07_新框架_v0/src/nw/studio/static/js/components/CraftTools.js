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

export async function openStyleReferenceDrawer(novelId, {onSaved} = {}) {
  drawer('写前语感参照（15 步起草定调锚点）', loading());
  try {
    const data = await api.get(`/novels/${enc(novelId)}/style-reference`);
    const acceptedInfo = data.can_use_auto_book_prose
      ? `本书已有已接受章节（第 ${data.accepted_chapters.join('、')} 章），可随时切为「沿用本书已采用正文语感」。`
      : '本书尚未接受第 1 章正文，开篇黄金三章建议先用「作者参照样段」定准腔调。';

    $('#drawerBody').innerHTML = `<form id="styleReferenceForm" class="stack">
      <div class="notice"><strong>为什么写前参照比堆规则更管用：</strong>动笔前紧贴一段高水准样段定调，能立刻对齐句式呼吸、长短句节奏与对白脾气。系统严守「只学腔调、严禁照搬人名/设定/情节或原句」，且作为预算感知项在窗口紧张时自动让位。</div>
      <label class="field">
        <span>参照模式</span>
        <select name="mode" id="styleRefMode">
          <option value="off" ${data.mode === 'off' ? 'selected' : ''}>${esc(MODE_LABEL.off)}</option>
          <option value="author_sample" ${data.mode === 'author_sample' ? 'selected' : ''}>${esc(MODE_LABEL.author_sample)}</option>
          <option value="auto_book_prose" ${data.mode === 'auto_book_prose' ? 'selected' : ''}>${esc(MODE_LABEL.auto_book_prose)}</option>
        </select>
        <small class="muted">${esc(acceptedInfo)}</small>
      </label>
      <div id="styleSampleFields" class="stack" style="gap:12px">
        <div class="form-grid">
          <label class="field"><span>样段标题（可选）</span><input name="title" value="${esc(data.title || '')}" placeholder="如：作者自写试笔第一章 / 语感参照"></label>
          <label class="field"><span>来源备注（可选）</span><input name="source_note" value="${esc(data.source_note || '')}" placeholder="如：作者自写 / 选定同类腔调参照"></label>
        </div>
        <label class="field">
          <span>参照样段正文（最多 ${number(data.max_excerpt_chars || 4000)} 字，实际写前挂载前 ${number(data.prompt_excerpt_chars || 2200)} 字）</span>
          <textarea name="excerpt" rows="8" placeholder="粘贴 1–3 段或一章最代表你想要的叙述口吻、句式呼吸与对白脾气的正文…">${esc(data.excerpt || '')}</textarea>
        </label>
      </div>
      <label class="field">
        <span>本书语感与写法要点（可选，无论哪种开启模式都会作为写前提示）</span>
        <textarea name="style_notes" rows="3" placeholder="例如：句子按意思一路说完不切碎；人物心里想法直白鲜活；对白带各人脾气；不强行堆四字成语。">${esc(data.style_notes || '')}</textarea>
      </label>
      <div class="row wrap" style="gap:8px">
        <button type="submit" class="button">保存写前语感参照</button>
        <button type="button" class="ghost" id="disableStyleRefBtn">关闭参照</button>
      </div>
    </form>`;

    const syncVisibility = () => {
      const m = $('#styleRefMode').value;
      $('#styleSampleFields').style.display = m === 'author_sample' ? '' : 'none';
    };
    $('#styleRefMode').onchange = syncVisibility;
    syncVisibility();

    const submitPayload = async (btn, payload) => {
      await busy(btn, async () => {
        await api.post(`/novels/${enc(novelId)}/style-reference`, payload);
        $('#drawer')?.close?.();
        toast(payload.mode === 'off' ? '已关闭写前语感参照' : '写前语感参照已保存，将在下次起草/工作包重算时生效');
        if (onSaved) await onSaved();
      });
    };

    $('#disableStyleRefBtn').onclick = e => submitPayload(e.currentTarget, {
      enabled: false, mode: 'off', title: '', source_note: '', excerpt: '', style_notes: '',
    }).catch(fail);

    $('#styleReferenceForm').onsubmit = e => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const mode = String(fd.get('mode') || 'off');
      submitPayload(e.target.querySelector('[type=submit]'), {
        enabled: mode !== 'off',
        mode,
        title: String(fd.get('title') || ''),
        source_note: String(fd.get('source_note') || ''),
        excerpt: String(fd.get('excerpt') || ''),
        style_notes: String(fd.get('style_notes') || ''),
      }).catch(fail);
    };
  } catch (error) {
    $('#drawerBody').innerHTML = `<p class="error">${esc(error.message)}</p>`;
    fail(error);
  }
}

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
