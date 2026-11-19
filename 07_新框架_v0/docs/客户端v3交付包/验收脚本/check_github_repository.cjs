const {chromium,expect}=require(process.env.PLAYWRIGHT_MODULE||'@playwright/test');
const fs=require('node:fs'),path=require('node:path');
const base=process.env.STUDIO_BROWSER_URL||'http://127.0.0.1:8767';
const output=path.resolve(process.env.STUDIO_CHECK_OUTPUT||'build/client-v3-browser-evidence/github');
fs.mkdirSync(output,{recursive:true});
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE||undefined});
  const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[],external=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('request',request=>{if(/^https?:/.test(request.url())&&!request.url().startsWith(base+'/'))external.push(request.url());});
  await page.goto(base+'/#/settings');
  await expect(page.locator('#githubSettings')).toBeVisible();
  await expect(page.locator('#githubSettings')).toContainText('https://github.com/LI-SHUAI-ZHONG/xiaoshuo');
  await expect(page.locator('#githubSettings')).toContainText('studio.config.toml');
  await expect(page.locator('#githubSettings')).toContainText('workspace');
  await expect(page.locator('#githubSettings')).toContainText('studio_data');
  await expect(page.locator('#statusGit')).toBeVisible();
  const status=await (await page.request.get(base+'/api/repository')).json();
  expect(status.enabled).toBe(true);expect(status.branch).toBe('master');
  expect(status.config_path.endsWith('studio.config.toml')).toBe(true);
  if(process.env.STUDIO_EXPECT_SYNCED==='1'){
    expect(status.state).toBe('synced');
    await expect(page.locator('#repositorySyncState')).toHaveText('已同步');
  }
  await page.locator('#githubSettings details summary').click();
  await page.locator('#githubSettings').screenshot({path:path.join(output,'GitHub仓库与资料位置.png')});
  expect(errors).toEqual([]);expect(external).toEqual([]);
  const result={passed:true,state:status.state,repository:status.repository,github_url:status.github_url,
    branch:status.branch,config_path:status.config_path,original_materials:status.original_materials,
    runtime_materials:status.runtime_materials,runtime_workspace:status.runtime_workspace,
    git_runtime_snapshot:status.git_runtime_snapshot,local_commit:status.local_commit,
    remote_commit:status.remote_commit,last_synced_at:status.last_synced_at,model_calls:0,errors};
  fs.writeFileSync(path.join(output,'GitHub客户端浏览器核验.json'),JSON.stringify(result,null,2));
  console.log(JSON.stringify(result));await browser.close();
})().catch(error=>{console.error(error);process.exit(1);});
