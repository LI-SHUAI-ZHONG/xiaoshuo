import {api} from '../api.js';
import {$,esc,busy,date,toast} from '../ui.js';

export async function mountRepositorySettings(ctx){
  const host=$('#repositorySettings');
  let stopped=false,rendered='';
  async function refresh(){
    try{
      const value=await api.get('/repository',ctx.signal);
      if(stopped||!ctx.alive())return;
      const signature=JSON.stringify(value);if(signature===rendered)return;rendered=signature;
      const expanded=Boolean(host.querySelector('details')?.open);
      const labels={disabled:'未启用',pending:'等待同步',syncing:'同步中',synced:'已同步',error:'同步未完成'};
      const colour=value.state==='synced'?'green':value.state==='error'?'amber':'blue';
      host.innerHTML=`<section class="settings-section" id="githubSettings">
        <div class="row spread"><h3 style="margin:0">GitHub 仓库与资料</h3><span id="repositorySyncState" class="tag ${colour}">${esc(labels[value.state]||value.state)}</span></div>
        <p class="muted" style="margin:16px 0">${esc(value.message)}</p>
        ${value.error?`<div class="notice error" id="repositorySyncError">${esc(value.error)}</div>`:''}
        ${value.restart_required?'<div class="notice">GitHub 中的客户端程序已更新。请结束客户端启动窗口后重新双击桌面快捷方式，再继续制作。</div>':''}
        <div class="form-grid">
          <div class="field full"><span>实际连接的仓库</span><p style="overflow-wrap:anywhere">${value.github_url?`<a href="${esc(value.github_url)}" target="_blank" rel="noreferrer">${esc(value.github_url)}</a> · ${esc(value.branch)}`:'此启动配置未连接 GitHub'}</p></div>
          <div class="field"><span>自动同步</span><p>${value.enabled?`启动后、保存后及每 ${value.interval_seconds} 秒检查；制作结束后同步`:'此隔离工作区未启用'}</p></div>
          <div class="field"><span>最近同步成功</span><p>${value.last_synced_at?esc(date(value.last_synced_at)):'尚未成功同步'}</p></div>
          <div class="field full"><span>Git 版本</span><p>${value.local_commit?esc(value.local_commit.slice(0,12)):'等待首次同步'}</p></div>
        </div>
        <details class="details" ${expanded?'open':''}><summary>查看客户端实际使用的位置</summary>
          ${[['Git 工作目录',value.repository],['实际 API 配置（随 Git 保存）',value.config_path],['资料原件',value.original_materials],['运行资料',value.runtime_materials],['作品运行工作区',value.runtime_workspace],['作品在 Git 中的快照',value.git_runtime_snapshot]].map(([name,path])=>`<p><strong>${esc(name)}</strong><br><span class="muted" style="overflow-wrap:anywhere">${esc(path||'未配置')}</span></p>`).join('')}
        </details>
        <div class="row" style="margin-top:16px"><button class="secondary" id="syncGithubNow" type="button" ${!value.enabled||value.state==='syncing'?'disabled':''}>立即同步 GitHub</button><small class="muted">配置、书库、参考作品和正式小说数据随仓库保存；实际 API Key 留在本机环境变量。</small></div>
      </section>`;
      $('#syncGithubNow').onclick=e=>busy(e.currentTarget,async()=>{await api.post('/repository/sync');toast('已请求同步 GitHub');await refresh();});
    }catch(error){if(!stopped&&error.name!=='AbortError')host.innerHTML=`<section class="settings-section"><h3>GitHub 仓库与资料</h3><p class="error">${esc(error.message)}</p></section>`;}
  }
  await refresh();
  if(stopped||!ctx.alive())return;
  const timer=setInterval(refresh,2500);
  ctx.onCleanup(()=>{stopped=true;clearInterval(timer);});
}
