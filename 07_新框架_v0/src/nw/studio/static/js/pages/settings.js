import {api} from '../api.js';
import {$,$$,esc,icon,drawer,busy,toast} from '../ui.js';
import {persist} from '../store.js';
import {mountNovelCacheSettings} from '../components/NovelCache.js';
import {mountRepositorySettings} from '../components/RepositorySettings.js';

const API_PARAMS=new Set(['temperature','top_p','max_tokens','max_completion_tokens','seed','stop']);

export async function render(ctx){
  const config=await api.get('/config/routing',ctx.signal);
  if(!ctx.alive())return;
  const current=config.current||{};
  const stored=current.model&&typeof current.model==='object'?current.model:current;
  const model=stored.provider==='openai_compat'?stored:{};
  const configured=Boolean(config.valid&&stored.provider==='openai_compat');
  const staged=stored.provider==='openai_compat'?(current.stage_overrides??current.stage_models??{}):{};
  const apiKeyEnv=model.api_key_env||'NW_API_KEY';
  ctx.sidebar('设置',[['settings','通用 API','settings'],['settings?section=appearance','外观与工作空间','sun'],['settings?section=cache','小说存储与缓存','inbox']],
    '<strong>使用通用 OpenAI 兼容接口</strong>填写服务地址、模型名称和密钥环境变量名。设计、写作和审稿默认共用此接口。');
  $('#statusModel').textContent=configured?'API 配置已保存':'API 待配置';
  ctx.content.innerHTML=`<div class="page">
    <div class="page-heading"><div><div class="eyebrow">MAKE IT YOUR WORKSPACE</div><h1>设置</h1><p class="page-description">配置你的通用 API，保存后用于小说设计、写作和审稿。</p></div></div>
    <form id="settingsForm" class="settings-form">
      <section class="settings-section">
        <div class="row spread" style="margin-bottom:20px"><h3 style="margin:0">通用 API</h3><span class="tag ${configured?'blue':'amber'}">${configured?'配置已保存 · 连接未验证':'等待填写 API 配置'}</span></div>
        <div class="notice" style="margin-bottom:20px">支持 OpenAI 兼容的 Chat Completions 接口。${config.repository_managed?'API 地址、模型和密钥变量名保存在仓库的共享配置中，并自动同步 GitHub。':'配置保存在当前工作区指定的配置文件中。'}实际密钥只读取环境变量，保存配置不会发起模型调用。</div>
        <div class="form-grid">
          <label class="field full"><span>API 服务地址</span><input id="modelBaseUrl" type="url" required value="${esc(model.base_url||'')}" placeholder="https://你的服务地址/v1"><small class="muted">填写基础地址，例如服务商提供的 /v1 地址；不包含 /chat/completions。</small></label>
          <label class="field"><span>模型名称</span><input id="modelName" required value="${esc(model.model||'')}" placeholder="填写服务商提供的实际模型名称" autocomplete="off"></label>
          <label class="field"><span>API Key 环境变量名称</span><input id="apiKeyEnv" required pattern="[A-Za-z_][A-Za-z0-9_]*" value="${esc(apiKeyEnv)}" placeholder="例如 NW_API_KEY" autocomplete="off"><small class="muted">这里填写保存密钥的变量名，密钥从环境变量读取。</small></label>
          <label class="field"><span>调用超时（秒）</span><input id="modelTimeout" type="number" min="1" max="3600" required value="${Number(model.timeout||120)}"></label>
          <label class="field"><span>模型上下文窗口（token）</span><input id="contextWindowTokens" type="number" min="1" step="1" value="${esc(model.context_window_tokens??'')}" placeholder="按服务商标注容量填写">
            <small class="muted">选填。制作会按 token 估算输入、预留输出，并按字符数检查工作包。</small></label>
          <div class="field"><span>密钥变量状态</span><span class="tag" id="keyEnvStatus"></span><small class="muted">设置环境变量后，重新启动客户端使服务进程读取新值。</small></div>
        </div>
      </section>
      <details class="settings-section" id="stageModelSettings"><summary>分步骤模型（选填）</summary>
        <p class="muted" style="margin:16px 0">可单独指定模型或窗口。同一服务和模型可以共用通用窗口。改用其他模型时，请填写对应容量，留空时按输入字符预算检查。</p>
        <div class="form-grid">${[...(config.design_stages||[]),...(config.runtime_stages||[])].map(s=>{
          const spec=staged[s.stage];
          const value=typeof spec==='string'?spec:spec?.model||'';
          const title=esc(s.zh||s.label||s.stage), stage=esc(s.stage);
          return `<label class="field"><span>${title} · 模型</span><input data-stage-model="${stage}" value="${esc(value)}" placeholder="跟随默认模型"></label>
            <label class="field"><span>${title} · 窗口（token）</span><input type="number" min="1" step="1" data-stage-window="${stage}" value="${esc(spec?.context_window_tokens??'')}"></label>`;
        }).join('')}</div>
      </details>
      <section class="settings-section" id="appearance"><h3>外观与工作空间</h3><div class="form-grid">
        <label class="field"><span>主题</span><select id="appearanceTheme"><option value="dark" ${ctx.store.theme==='dark'?'selected':''}>深色 · 专注创作</option><option value="light" ${ctx.store.theme==='light'?'selected':''}>浅色 · 清晰阅读</option></select></label>
        <div class="field"><span>工作流资料目录</span><p style="overflow-wrap:anywhere">${esc(current.workspace||ctx.state.status?.workspace||'由启动配置决定')}</p><small class="muted">小说的保存位置见下方「小说存储与缓存」。</small></div>
      </div></section>
      <div class="row spread"><button class="secondary" type="button" id="previewConfig">预览配置</button><button class="button" type="submit">${icon('check')} 保存 API 配置</button></div>
    </form><section class="settings-section" id="novelCacheSettings" style="margin-top:24px" aria-label="小说存储与缓存"><h3>小说存储与缓存</h3><p class="muted">正在读取目录…</p></section><div id="repositorySettings" style="margin-top:24px"></div></div>`;

  function keyStatus(){
    const name=$('#apiKeyEnv').value.trim(),present=config.env_present?.[name];
    $('#keyEnvStatus').textContent=present===true?`${name} · 已设置`:present===false?`${name} · 未设置`:`${name||'未填写变量名'} · 保存后查看`;
    $('#keyEnvStatus').classList.toggle('green',present===true);
  }
  function payload(){
    const stage_models={...staged};
    $$('[data-stage-model]').forEach(el=>{
      const stage=el.dataset.stageModel, old=staged[stage];
      const spec=typeof old==='object'&&old?{...old}:{};
      const window=document.querySelector(`[data-stage-window="${CSS.escape(stage)}"]`).value;
      if(el.value.trim())spec.model=el.value.trim();else delete spec.model;
      if(window)spec.context_window_tokens=Number(window);else delete spec.context_window_tokens;
      if(Object.keys(spec).length)stage_models[stage]=spec;else delete stage_models[stage];
    });
    const window=$('#contextWindowTokens').value;
    return {model:{provider:'openai_compat',base_url:$('#modelBaseUrl').value.trim(),model:$('#modelName').value.trim(),api_key_env:$('#apiKeyEnv').value.trim(),timeout:Number($('#modelTimeout').value),...(window?{context_window_tokens:Number(window)}:{})},
      params:Object.fromEntries(Object.entries(current.params||{}).filter(([key])=>API_PARAMS.has(key))),stage_models,
      source_driven:current.source_driven??current.workflow?.source_driven??true};
  }
  const normalizeUrl = url => (url || '').trim().replace(/\/+$/, '');
  function showWindowSource(){
    const common = $('#modelName').value.trim(), url = normalizeUrl($('#modelBaseUrl').value);
    $$('[data-stage-model]').forEach(el => {
      const stage = el.dataset.stageModel, spec = staged[stage];
      const sameModel = !el.value.trim() || el.value.trim() === common;
      const sameService = (!spec?.provider || spec.provider === 'openai_compat')
        && (!spec?.base_url || normalizeUrl(spec.base_url) === url);
      const field = document.querySelector(`[data-stage-window="${CSS.escape(stage)}"]`);
      field.placeholder = sameService && sameModel && $('#contextWindowTokens').value
        ? '沿用通用窗口' : '未知，按字符预算检查';
    });
  }
  $$('#modelName,#modelBaseUrl,#contextWindowTokens,[data-stage-model]').forEach(el => el.addEventListener('input',showWindowSource));
  showWindowSource();
  $('#apiKeyEnv').oninput=keyStatus;keyStatus();
  $('#appearanceTheme').onchange=e=>{persist({theme:e.target.value});document.documentElement.dataset.theme=e.target.value;};
  $('#previewConfig').onclick=e=>{
    if(!$('#settingsForm').reportValidity())return;
    busy(e.currentTarget,async()=>{const data=await api.post('/config/preview',payload());drawer('高级 · 配置预览',`<pre class="raw-data">${esc(data.toml)}</pre>`);});
  };
  $('#settingsForm').onsubmit=e=>{
    e.preventDefault();
    busy(e.target.querySelector('button[type=submit]'),async()=>{
      await api.post('/config/save',payload());
      ctx.state.status={...ctx.state.status,config_valid:true};
      $('#statusModel').textContent='API 配置已保存';
      toast('API 配置已保存，尚未验证连接');ctx.navigate();
    });
  };
  if(ctx.params.get('section')==='appearance')$('#appearance').scrollIntoView({block:'start'});
  if(ctx.params.get('section')==='cache')$('#novelCacheSettings').scrollIntoView({block:'start'});
  await Promise.all([mountNovelCacheSettings(ctx), mountRepositorySettings(ctx)]);
}
