// Run with Node and Playwright from a checkout with the local Python environment installed.
const path = require('node:path');
const {spawnSync} = require('node:child_process');
if (!process.argv[2]) {
  const project = path.resolve(__dirname, '../../..');
  const python = process.env.STUDIO_VERIFY_PYTHON || path.join(project, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  const isolate = `
from pathlib import Path
import subprocess, sys
from tempfile import TemporaryDirectory
from threading import Thread
from nw.studio.api import StudioService
from nw.studio.server import create_studio_server
with TemporaryDirectory(prefix='studio-length-ui-') as tmp:
    root = Path(tmp)
    service = StudioService(root / 'workspace', config_path=root / 'studio.toml', projects_root=root / 'books')
    server = create_studio_server(service, port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f'http://127.0.0.1:{server.server_port}'
        code = subprocess.call([sys.argv[1], sys.argv[2], url, str(root)])
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    raise SystemExit(code)
`;
  const result = spawnSync(python, ['-c', isolate, process.execPath, __filename], {
    cwd:project, env:{...process.env,PYTHONPATH:path.join(project, 'src')}, stdio:'inherit',
  });
  if (result.error) throw result.error;
  process.exit(result.status ?? 1);
}
const assert = require('node:assert/strict');
const {chromium, expect} = require(process.env.PLAYWRIGHT_MODULE || '@playwright/test');
(async()=>{
const pageUrl=process.argv[2];
const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined});
try {
  const page=await browser.newPage({viewport:{width:1370,height:950}});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pageUrl+'/#/home');
  const config=await (await page.request.get(pageUrl+'/api/repository')).json();
  assert(!config.enabled);
  assert.equal(path.resolve(config.runtime_workspace), path.resolve(process.argv[3], 'workspace'));
  assert.equal(path.resolve(config.novel_storage_path), path.resolve(process.argv[3], 'books'));
  const goToLength=async()=>{
    await page.getByRole('button',{name:'新建小说',exact:true}).click();
    for(const name of ['为故事选择类型','风格','文笔','写法','世界观','人物']){
      await expect(page.locator('#modalBody h2')).toHaveText(name);
      await page.locator('#wizardNext').click();
    }
    await expect(page.locator('#modalBody h2')).toHaveText('结构篇幅');
  };
  const toConfirm=async()=>{
    await page.locator('#wizardNext').click();
    await expect(page.locator('#modalBody h2')).toHaveText('卖点');
    await page.locator('#wizardNext').click();
    await expect(page.locator('#wizardTitle')).toBeVisible();
  };
  const back=async()=>{
    await page.locator('#wizardPrev').click();
    await expect(page.locator('#modalBody h2')).toHaveText('卖点');
    await page.locator('#wizardPrev').click();
    await expect(page.locator('#targetWords')).toBeVisible();
  };
  await goToLength();
  await page.locator('#targetWords').fill('160000');
  await toConfirm();
  await expect(page.locator('.selection-summary')).toContainText('160,000 字');
  await back();
  await expect(page.locator('#targetWords')).toHaveValue('160000');
  await page.locator('#targetWords').fill('');
  await page.locator('#volumeCount').fill('3');
  await toConfirm();
  await expect(page.locator('.selection-summary')).toContainText('3 卷');
  await back();
  await page.locator('#targetWords').fill('160000');
  await page.locator('#chapterTargetWords').fill('4000');
  await page.locator('#sceneTargetWords').fill('800');
  await page.locator('#wordTolerancePct').fill('101');
  await page.locator('#wizardNext').click();
  await expect(page.locator('#modalBody h2')).toHaveText('结构篇幅');
  await page.locator('#wordTolerancePct').fill('10');
  await page.getByText('高级 · 模型调用预算',{exact:true}).click();
  await page.locator('[name=context_char_limit]').fill('80000');
  await page.locator('[name=output_limit]').fill('5000');
  await toConfirm();
  await expect(page.locator('.selection-summary')).toContainText('80,000');
  await page.locator('#wizardTitle').fill('[UI] 篇幅隔离验收');
  await page.locator('#wizardIdea').fill('一位抄书人发现反复遗失的案卷。');
  const createPromise=page.waitForResponse(r=>r.url().endsWith('/api/novels')&&r.request().method()==='POST');
  await page.locator('#wizardNext').click();
  const created=await createPromise;
  assert.equal(created.status(),201,await created.text());
  const payload=created.request().postDataJSON();
  assert.equal(payload.auto_length,true);
  assert.deepEqual([payload.target_words,payload.chapter_target_words,payload.scene_target_words,payload.volume_count,payload.word_tolerance_pct],[160000,4000,800,3,10]);
  assert.deepEqual(payload.budget,{context_char_limit:80000,output_limit:5000});
  const id=(await created.json()).novel.id;
  await page.locator('#tab-length').click();
  await expect(page.locator('#studioEditor')).toContainText('160,000');
  await expect(page.locator('#studioEditor')).toContainText('144,000');
  console.log('wizard single-field confirmations, optional chapter/scene budgets, range validation and creation OK');
  await page.locator('#editLengthPlan').click();
  await page.locator('#drawer #targetWords').fill('200000');
  await page.locator('#drawer #sceneTargetWords').fill('');
  await page.locator('#drawer #wordTolerancePct').fill('5');
  await page.locator('#drawer details summary').click();
  await page.locator('#drawer [name=output_limit]').fill('');
  const savePromise=page.waitForResponse(r=>r.url().endsWith('/length')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'保存篇幅计划'}).click();
  const saved=await savePromise; assert.equal(saved.status(),200,await saved.text());
  assert.deepEqual(saved.request().postDataJSON(), {target_words:200000,scene_target_words:null,word_tolerance_pct:5,budget:{output_limit:null}});
  await expect(page.locator('#drawer')).not.toBeVisible();
  await expect(page.locator('#studioEditor')).toContainText('200,000');
  await page.reload();
  await page.locator('#tab-length').click();
  await expect(page.locator('#studioEditor')).toContainText('200,000');
  await expect(page.locator('#studioEditor')).toContainText('190,000');
  await expect(page.locator('#studioEditor')).toContainText('80,000');
  await expect(page.locator('#studioEditor')).toContainText('4,096');
  console.log('real length save, field removal, retained overrides, threshold and reload OK');
  const other=await browser.newPage();
  await other.goto(pageUrl+'/#/studio/'+id);
  await page.locator('#tab-design').click();
  await other.locator('#tab-length').click();
  await other.locator('#editLengthPlan').click();
  await other.locator('#drawer #targetWords').fill('215000');
  await other.getByRole('button',{name:'保存篇幅计划'}).click();
  await expect(other.locator('#studioEditor')).toContainText('215,000');
  const reentered=page.waitForResponse(r=>r.url().endsWith('/api/novels/'+id)&&r.request().method()==='GET');
  await page.locator('#tab-length').click();
  await reentered;
  await expect(page.locator('#studioEditor')).toContainText('215,000');
  await other.locator('#editLengthPlan').click();
  await other.locator('#drawer #targetWords').fill('');
  await other.getByRole('button',{name:'保存篇幅计划'}).click();
  await expect(page.locator('#studioEditor')).toContainText('全书目标待设定', {timeout:10000});
  await other.close();
  // Approve a real stored book card while this tab remains open and there are still no scenes.
  const project=path.resolve(__dirname,'../../..');
  const python=process.env.STUDIO_VERIFY_PYTHON || path.join(project,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
  const approveBook=`
import sys
from pathlib import Path
sys.path.insert(0, 'tests')
from test_length_plan import plan
from test_planning import apply
from nw.config import Config
from nw.planning import propose_plan
from nw.studio.api import StudioService
from nw.studio.library import LibraryService
from nw.studio.production import ProductionService
from nw.task_models import Budget
root = Path(sys.argv[1])
studio = StudioService(root/'workspace', config_path=root/'studio.toml', projects_root=root/'books')
app = ProductionService(studio, LibraryService(studio.workspace), test_mode=True)
novel = app.db.get(sys.argv[2])
with app.open_store(novel) as store:
    assert not store.list('scene') and not novel['wizard'].get('target_words')
    config = Config('fake', 'http://localhost', 'test', '', 5, {}, store.directory, source_driven=False)
    governance = {'plot_design': {'length_policy': {}, 'length_auto': True}}
    apply(store, propose_plan(store, 1, 'book', plan('book', 212345), config, Budget(1, 60000, 4000), governance_inputs=governance))
`;
  const approved=spawnSync(python,['-c',approveBook,process.argv[3],id],{
    cwd:project,env:{...process.env,PYTHONPATH:path.join(project,'src')},encoding:'utf8',
  });
  assert.equal(approved.status,0,approved.stderr || String(approved.error || ''));
  await expect(page.locator('#studioEditor')).toContainText('212,345',{timeout:10000});
  await expect(page.locator('#studioEditor')).toContainText('一章内揭晓证据');
  console.log('re-entered tab, external length edit and background book approval refresh the live manuscript plan');
  // Supply a blocked progress snapshot to check the repair action without invoking a model.
  const progressPath='**/api/novels/'+id+'/progress';
  const eventsPath='**/api/novels/'+id+'/events';
  await page.route(eventsPath,r=>r.abort());
  await page.route(progressPath,async r=>{
    const response=await r.fetch(), snapshot=await response.json();
    await r.fulfill({response,json:{...snapshot,status:'BLOCKED',reason:'CONTEXT_TOO_LARGE'}});
  });
  await page.reload();
  await expect(page.locator('#runNovel')).toHaveText('按已保存预算继续');
  const retry=page.waitForRequest(r=>r.url().endsWith('/retry')&&r.method()==='POST');
  await page.locator('#runNovel').click();
  assert.deepEqual((await retry).postDataJSON(),{use_saved_context_budget:true});
  await page.unroute(eventsPath);
  await page.unroute(progressPath);
  await page.goto(pageUrl+'/#/settings');
  await page.locator('#modelBaseUrl').fill('https://ui-audit.example.test/v1');
  await page.locator('#modelName').fill('test-model');
  await page.locator('#apiKeyEnv').fill('UI_TEST_NO_SUCH_KEY');
  await page.locator('#contextWindowTokens').fill('96000');
  await page.locator('#stageModelSettings summary').click();
  await page.locator('[data-stage-window=review]').fill('64000');
  await page.locator('[data-stage-model=write]').fill('test-writer');
  const configSave=page.waitForResponse(r=>r.url().endsWith('/config/save')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'保存 API 配置'}).click();
  const savedConfig=await configSave; assert.equal(savedConfig.status(),200,await savedConfig.text());
  const post=savedConfig.request().postDataJSON();
  assert.equal(post.model.context_window_tokens,96000);
  assert.deepEqual(post.stage_models.review,{context_window_tokens:64000});
  assert.deepEqual(post.stage_models.write,{model:'test-writer'});
  await page.reload();
  await expect(page.locator('#contextWindowTokens')).toHaveValue('96000');
  await page.locator('#stageModelSettings summary').click();
  await expect(page.locator('[data-stage-model=review]')).toHaveValue('');
  await expect(page.locator('[data-stage-window=review]')).toHaveValue('64000');
  await expect(page.locator('[data-stage-window=write]')).toHaveValue('');
  await expect(page.locator('[data-stage-window=write]')).toHaveAttribute('placeholder','未知，按字符预算检查');
  await expect(page.locator('[data-stage-window=revise]')).toHaveAttribute('placeholder','沿用通用窗口');
  assert.deepEqual(errors,[]);
  console.log('same-model window inheritance, independent stages and unknown model windows verified without browser errors');
} finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1})
