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
    await expect(page.locator('[data-tier-mode]')).toBeVisible();
  };
  const pick=(view,target)=>view.locator(`input[name=bookTier][value="${target}"]`).check();
  const summary=page.locator('.selection-summary');
  await goToLength();
  const radios=page.locator('[data-tier-mode] input[name=bookTier]');
  assert.deepEqual(await radios.evaluateAll(items=>items.map(item=>item.value)),
    ['300000','500000','1000000','1500000','2000000','']);
  await expect(radios.last()).toBeChecked();
  await expect(page.locator('#modalBody [data-tier-evidence]')).toContainText('暂无可用于推荐');
  await expect(page.locator('.length-recommended')).toHaveCount(0);
  await expect(page.locator('.length-chapter-rule')).toContainText('2,000–2,500');
  await expect(page.locator('#chapterCount,#chapterTargetWords,#sceneTargetWords,#wordTolerancePct')).toHaveCount(0);
  await pick(page,500000);
  await toConfirm();
  await expect(summary).toContainText('50 万字');
  await expect(summary).toContainText('40 万至不足 75 万字');
  await expect(summary).toContainText('完整段落处换章');
  // Feed the real HTTP endpoint through imported text and approved corpus versions in the temporary workspace.
  const project=path.resolve(__dirname,'../../..');
  const python=process.env.STUDIO_VERIFY_PYTHON || path.join(project,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
  function runFixture(script,...args) {
    const result=spawnSync(python,['-c',script,process.argv[3],...args],{
      cwd:project,env:{...process.env,PYTHONPATH:path.join(project,'src')},encoding:'utf8',
    });
    assert.equal(result.status,0,result.stderr || String(result.error || ''));
  }
  const addVotes=`
from pathlib import Path
import sys
sys.path.insert(0,'tests')
from test_studio_length_recommendations import reference
from nw.studio.library import LibraryService
library=LibraryService(Path(sys.argv[1])/'workspace')
genre=library.genres()['genres'][0]['id']
rows={'plurality':[('甲',300000),('乙',450000),('丙',500000)], 'tie':[('丁',350000)], 'majority':[('戊',550000)]}[sys.argv[2]]
for mark, size in rows:
    reference(library,mark * size,'隔离浏览器样本'+mark,[genre])
`;
  runFixture(addVotes,'plurality');
  await back();
  await expect(radios.nth(1)).toBeChecked();
  await expect(page.locator('.length-recommended')).toHaveText('推荐');
  await expect(page.locator('.length-tier').filter({has:page.locator('.length-recommended')})).toContainText('50 万字');
  await expect(page.locator('#modalBody [data-tier-evidence]')).toContainText('2 部落在 50 万字档');
  await pick(page,'');
  await toConfirm();
  await expect(summary).toContainText('由 AI 在书纲中提出');
  runFixture(addVotes,'tie');
  await back();
  await expect(radios.last()).toBeChecked();
  await expect(page.locator('#modalBody [data-tier-evidence]')).toContainText('并列最多');
  await expect(page.locator('.length-recommended')).toHaveCount(0);
  await toConfirm();
  const recRoute='**/api/recommendations/length?*';
  await page.route(recRoute,route=>route.fulfill({status:503,contentType:'application/json',body:'{}'}));
  await back();
  await expect(page.locator('#modalBody [data-tier-evidence]')).toContainText('暂时无法读取');
  await pick(page,1500000);
  await toConfirm();
  await expect(summary).toContainText('150 万字');
  await page.unroute(recRoute);
  await back();
  await pick(page,300000);
  await page.locator('#volumeCount').fill('3');
  await page.getByText('高级 · 模型调用预算',{exact:true}).click();
  await page.locator('[name=context_char_limit]').fill('999');
  await page.locator('#wizardNext').click();
  await expect(page.locator('#modalBody h2')).toHaveText('结构篇幅');
  await page.locator('[name=context_char_limit]').fill('80000');
  await page.locator('[name=output_limit]').fill('5000');
  await toConfirm();
  await expect(summary).toContainText('3 卷');
  await expect(summary).toContainText('80,000');
  await page.locator('#wizardTitle').fill('[UI] 篇幅隔离验收');
  await page.locator('#wizardIdea').fill('一位抄书人发现反复遗失的案卷。');
  const createPromise=page.waitForResponse(r=>r.url().endsWith('/api/novels')&&r.request().method()==='POST');
  await page.locator('#wizardNext').click();
  const created=await createPromise;
  assert.equal(created.status(),201,await created.text());
  const payload=created.request().postDataJSON();
  assert.equal(payload.auto_length,true);
  assert.deepEqual([payload.length_mode,payload.target_words,payload.volume_count],['tiered',300000,3]);
  for (const key of ['chapter_count','chapter_target_words','scene_target_words','word_tolerance_pct'])
    assert(!(key in payload),key);
  assert.deepEqual(payload.budget,{context_char_limit:80000,output_limit:5000});
  const id=(await created.json()).novel.id;
  const editor=page.locator('#studioEditor');
  await page.locator('#tab-length').click();
  await expect(editor).toContainText('20 万至不足 40 万字');
  await expect(editor).toContainText('2,000–2,500');
  console.log('five tiers, full-text sample states, manual choice during outage, flexible chapter range and persisted creation OK');
  await page.locator('#editLengthPlan').click();
  await pick(page.locator('#drawer'),1000000);
  await page.locator('#drawer details summary').click();
  await page.locator('#drawer [name=output_limit]').fill('');
  const savePromise=page.waitForResponse(r=>r.url().endsWith('/length')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'保存篇幅计划'}).click();
  const saved=await savePromise; assert.equal(saved.status(),200,await saved.text());
  assert.deepEqual(saved.request().postDataJSON(), {target_words:1000000,budget:{output_limit:null}});
  await expect(page.locator('#drawer')).not.toBeVisible();
  await page.reload();
  await page.locator('#tab-length').click();
  await expect(editor).toContainText('75 万至不足 125 万字');
  await expect(editor).toContainText('80,000');
  await expect(editor).toContainText('4,096');
  const other=await browser.newPage();
  await other.goto(pageUrl+'/#/studio/'+id);
  await page.locator('#tab-design').click();
  await other.locator('#tab-length').click();
  await other.locator('#editLengthPlan').click();
  await pick(other.locator('#drawer'),2000000);
  await other.getByRole('button',{name:'保存篇幅计划'}).click();
  await expect(other.locator('#studioEditor')).toContainText('175–225 万字');
  const reentered=page.waitForResponse(r=>r.url().endsWith('/api/novels/'+id)&&r.request().method()==='GET');
  await page.locator('#tab-length').click();
  await reentered;
  await expect(editor).toContainText('175–225 万字');
  await other.locator('#editLengthPlan').click();
  await pick(other.locator('#drawer'),'');
  await other.getByRole('button',{name:'保存篇幅计划'}).click();
  await expect(editor).toContainText('全书目标待设定', {timeout:10000});
  await other.close();

  // Insert an older saved wizard through the service, preserving independent legacy controls until conversion.
  const legacy=await page.request.post(pageUrl+'/api/novels',{data:{...Object.fromEntries(Object.entries(payload)
    .filter(([key])=>key!=='length_mode')),title:'[UI] 旧版篇幅',target_words:160000,chapter_count:40,
    chapter_target_words:4000,word_tolerance_pct:10}});
  assert.equal(legacy.status(),201,await legacy.text());
  const oldId=(await legacy.json()).novel.id;
  await page.goto(pageUrl+'/#/studio/'+oldId);
  await page.locator('#tab-length').click();
  await expect(editor).toContainText('144,000');
  await page.locator('#editLengthPlan').click();
  await expect(page.locator('#drawer #targetWords')).toHaveValue('160000');
  await page.locator('[data-switch-tiers]').click();
  await expect(page.locator('#drawer #chapterCount')).toHaveCount(0);
  await pick(page.locator('#drawer'),500000);
  await page.getByRole('button',{name:'保存篇幅计划'}).click();
  await expect(editor).toContainText('40 万至不足 75 万字');
  const migrated=(await (await page.request.get(pageUrl+'/api/novels/'+oldId)).json()).novel.wizard;
  assert.equal(migrated.length_mode,'tiered');
  for(const key of ['chapter_count','chapter_target_words','word_tolerance_pct'])assert(!(key in migrated),key);
  console.log('legacy settings retained until explicit migration, new ranges and saved budgets survive reload');

  // Leave every length preference blank. The real create request lets the AI use the frozen genre votes.
  runFixture(addVotes,'majority');
  await page.goto(pageUrl+'/#/home');
  await goToLength();
  await expect(page.locator('#modalBody [data-tier-evidence]')).toContainText('3 部落在 50 万字档');
  await expect(page.locator('#modalBody [name=bookTier][value=""]')).toBeChecked();
  await toConfirm();
  await page.locator('#wizardIdea').fill('隔离验收 · 一份遗失的案卷。');
  const autoCreate=page.waitForResponse(r=>r.url().endsWith('/api/novels')&&r.request().method()==='POST');
  await page.locator('#wizardNext').click();
  const autoResult=await autoCreate;
  assert.equal(autoResult.status(),201,await autoResult.text());
  assert(!('target_words' in autoResult.request().postDataJSON()));
  const autoBook=(await autoResult.json()).novel.wizard;
  assert.equal(autoBook.length_mode,'tiered');
  assert.equal(autoBook.length_recommendation.recommended_tier,500000);
  assert.equal(autoBook.length_recommendation.sample_count,5);
  console.log('automatic book choice freezes real genre votes without turning the recommendation into an author target');
  // Approve an AI book tier in this isolated project with no scenes; the open tab must refresh.
  await page.goto(pageUrl+'/#/studio/'+id);
  await page.locator('#tab-length').click();
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
    governance = {'plot_design': {'length_policy': {'length_mode':'tiered'}, 'length_auto': True}}
    model = plan('book',500000)
    for item in model.output['candidate_cards']:
        item['body']['length_plan'].update(chapter_count=220,reason='依线索追查和人物行动估算篇幅')
    apply(store, propose_plan(store, 1, 'book', model, config, Budget(1,60000,4000), governance_inputs=governance))
`;
  runFixture(approveBook,id);
  await expect(editor).toContainText('已批准书纲 · 50 万字档',{timeout:10000});
  await expect(editor).toContainText('依线索追查和人物行动估算篇幅');
  console.log('re-entered tab, external length edit and real background book approval refresh the live manuscript plan');
  // Supply a blocked progress snapshot to check the repair action without invoking a model.
  const progressPath='**/api/novels/'+id+'/progress';
  const eventsPath='**/api/novels/'+id+'/events';
  const liveProgress=await page.request.get(pageUrl+'/api/novels/'+id+'/progress');
  assert.equal(liveProgress.status(),200,await liveProgress.text());
  const snapshot={...await liveProgress.json(),status:'BLOCKED',reason:'CONTEXT_TOO_LARGE'};
  await page.route(eventsPath,r=>r.abort());
  await page.route(progressPath,r=>r.fulfill({json:snapshot}));
  try {
    await page.reload();
    await expect(page.locator('#runNovel')).toHaveText('按已保存预算继续');
    const retry=page.waitForResponse(r=>r.url().endsWith('/retry')&&r.request().method()==='POST');
    await page.locator('#runNovel').click();
    const retried=await retry;
    assert.equal(retried.status(),200,await retried.text());
    assert.deepEqual(retried.request().postDataJSON(),{use_saved_context_budget:true});
  } finally {
    // Disarm both poll routes and await outstanding handlers before switching pages.
    await page.unrouteAll({behavior:'wait'});
  }
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
