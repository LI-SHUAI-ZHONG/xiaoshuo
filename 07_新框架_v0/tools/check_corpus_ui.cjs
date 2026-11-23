/* [FAKE] Headless browser acceptance against serve_corpus_fixture.py only. */
const fs=require('node:fs'),path=require('node:path');
const {chromium,expect}=require(process.env.PLAYWRIGHT_MODULE||'@playwright/test');
const meta=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
if(!meta.isolated||meta.github_sync!==false)throw Error('An isolated FAKE fixture is required');
const out=path.resolve(process.env.STUDIO_CHECK_OUTPUT||'build/corpus-browser-evidence');fs.mkdirSync(out,{recursive:true});

async function checkAutomaticEntry(page) {
  await page.goto(`${meta.base}/#/home`);
  const modal=page.locator('#modalBackdrop');
  const start=modal.getByRole('button',{name:'开始创作',exact:true});
  await page.getByRole('button',{name:'AI 自动',exact:true}).click();
  await expect(start).toBeDisabled();
  await modal.locator('[data-main=GENRE_XUANYI]').click();
  await modal.locator('[data-sub=SUB_XUANYI_02]').click();
  await expect(modal).toContainText('已批准的同类型');
  await expect(modal.locator('#wizardIdea')).toHaveCount(0);
  await expect(modal.locator('#wizardTitle')).toHaveCount(0);
  const request=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/api/novels');
  await start.click();
  const response=await request;
  expect(response.request().postDataJSON()).toEqual({
    design_mode:'auto',auto_recommendations:true,genre_ids:['GENRE_XUANYI','SUB_XUANYI_02'],
    auto_length:true,length_mode:'tiered',
  });
  expect(response.status(),await response.text()).toBe(400);
  expect((await response.json()).error).toContain('AUTO_RECOMMENDATIONS_MISSING');
  await expect(modal.locator('#modalBody [role=alert]')).toContainText(/风格.*文笔/);
  await expect(modal.locator('[data-sub=SUB_XUANYI_02]')).toHaveAttribute('aria-pressed','true');
  await expect(start).toBeEnabled();
  await expect(page).toHaveURL(/#\/home$/);
  await page.screenshot({path:path.join(out,'AI自动_同类型推荐缺失.png'),fullPage:true});
  await modal.locator('#modalFooter [data-close-modal]').click();

  await page.goto(`${meta.base}/#/library?tab=writing`);
  await page.getByRole('button',{name:'新建小说',exact:true}).click();
  await expect(modal.getByRole('button',{name:'人工选择',exact:true})).toBeVisible();
  await modal.getByRole('button',{name:'AI 自动',exact:true}).click();
  await expect(start).toBeDisabled();
  await modal.locator('#modalFooter [data-close-modal]').click();
  await page.goto(`${meta.base}/#/atlas/SUB_XUANYI_02`);
  await page.getByRole('button',{name:'用这个类型写一本',exact:true}).click();
  await modal.getByRole('button',{name:'AI 自动',exact:true}).click();
  await expect(modal.locator('[data-sub=SUB_XUANYI_02]')).toHaveAttribute('aria-pressed','true');
  await expect(start).toBeEnabled();
  await modal.locator('#modalFooter [data-close-modal]').click();
  return response.status();
}

(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE||undefined});
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  try{
    if(process.argv.includes('--auto-entry-only')){
      const status=await checkAutomaticEntry(page);
      expect(errors).toEqual([]);
      console.log(JSON.stringify({passed:true,isolated:true,auto_recommendations_missing_status:status,errors}));
      return;
    }
    await page.goto(`${meta.base}/#/staging`);
    await page.locator('#importBooks').click();
    await page.locator('#stagingFiles').setInputFiles({name:'[FAKE] 世界拆解浏览器测试.md',mimeType:'text/markdown',
      buffer:Buffer.from(meta.reference_text,'utf8')});
    await page.locator('#confirmImport').click();
    await page.getByRole('link',{name:/世界拆解浏览器测试/}).click();
    await page.locator('#reviewTypes').selectOption('GENRE_XUANYI');
    await page.locator('#reviewBookForm button[type=submit]').click();
    await expect(page.locator('#initializeCorpus')).toBeVisible();
    const bookUrl=page.url();
    await page.locator('#initializeCorpus').click();
    await page.locator('#initializeCorpusForm [name=extent]').selectOption('complete');
    await page.locator('#initializeCorpusForm [name=note]').fill('[FAKE] 浏览器测试全文声明，不是实际完整作品。');
    await page.locator('#initializeCorpusForm button[type=submit]').click();
    await expect(page.locator('#initializeCorpus')).toHaveCount(0);
    await expect(page.locator('#corpusVersion')).toHaveValue('1');
    await page.locator('#startCorpus').click();
    await page.locator('#corpusRunForm [name=note]').fill('[FAKE] 隔离自动拆解验收');
    await page.locator('#estimateCorpus').click();await expect(page.locator('#corpusEstimate')).toContainText('最低 13 次调用');
    await page.locator('#corpusRunForm button[type=submit]').click();
    await expect(page.locator('#corpusVersion')).toHaveValue('2',{timeout:20000});
    await expect(page.locator('#corpusJobPanel')).toContainText('已完成');
    await page.screenshot({path:path.join(out,'结构总览_桌面.png'),fullPage:true});
    await page.locator('[data-corpus-tab=threads]').click();
    await expect(page.locator('#corpusSection .corpus-record')).toHaveCount(8);
    await page.locator('#corpusDomainFilter').selectOption('hook');await page.locator('#applyCorpusFilter').click();
    await expect(page.locator('#corpusSection .corpus-record')).toHaveCount(1);
    await page.locator('[data-corpus-detail]').click();await expect(page.locator('#drawerBody')).toContainText('对应实际事件序列');
    await expect(page.locator('#drawerBody blockquote')).not.toHaveCount(0);
    await page.screenshot({path:path.join(out,'钩子与跨章证据.png')});
    await page.locator('#drawer [data-close-drawer]').click();
    await page.locator('#corpusDomainFilter').selectOption('world_rules');await page.locator('#applyCorpusFilter').click();
    await page.locator('[data-corpus-detail]').click();
    await expect(page.locator('#drawerBody')).toContainText('影碑破裂时也须扣签');
    await expect(page.locator('#drawerBody blockquote').last()).toContainText('留下复验笔录');
    await page.locator('#drawer [data-close-drawer]').click();
    await page.locator('[data-corpus-tab=distribution]').click();
    await expect(page.locator('#corpusSection')).toContainText('不是类型配额');
    await page.screenshot({path:path.join(out,'钩子伏笔分布.png')});
    await page.locator('[data-corpus-tab=evidence]').click();
    await page.locator('[data-corpus-edit]').first().click();
    await page.locator('#corpusRecordForm [name=explanation]').fill('[FAKE] 浏览器核对证据，不修改原文。');
    await page.locator('#locateCorpusQuote').click();
    await page.locator('#corpusRecordForm button[type=submit]').click();
    await expect(page.locator('#corpusVersion')).toHaveValue('3');
    await page.locator('#reviewCorpus').click();
    await page.locator('#corpusReviewForm [name=note]').fill('[FAKE] 人工确认测试结构、证据与来源范围。');
    await page.locator('#corpusReviewForm button[type=submit]').click();
    await expect(page.locator('#extractCorpusMethods')).toBeEnabled();
    await page.locator('#extractCorpusMethods').click();
    await page.locator('#corpusRunForm [name=threads][value=T_world_rules]').check();
    await page.locator('#corpusRunForm button[type=submit]').click();
    await expect(page.locator('#corpusJobPanel')).toContainText('已完成',{timeout:20000});
    await page.locator('[data-corpus-tab=overview]').click();
    await expect(page.getByText('方法版本 1 · 依据结构版本 3 →')).toBeVisible({timeout:10000});
    await page.getByText('方法版本 1 · 依据结构版本 3 →').click();
    await expect(page.locator('#drawerBody')).toContainText('依据已批准结构版本 3');
    await expect(page.locator('#drawerBody')).toContainText('具体操作');
    await expect(page.locator('#drawerBody')).toContainText('世界卡');
    await expect(page.locator('#drawerBody')).toContainText('场景设计');
    await page.locator('#methodReview [name=note]').fill('[FAKE] 已核对规则、受影响事件及原文。');
    await page.locator('#methodReview button[type=submit]').click();
    await expect(page.locator('#drawerBody .tag').first()).toContainText('已批准');
    await page.locator('#drawer [data-close-drawer]').click();
    const autoStatus=await checkAutomaticEntry(page);
    await page.goto(`${meta.base}/#/staging/${meta.retry_book_id}`);
    await expect(page.locator('#corpusJobPanel')).toContainText('已暂停');
    await page.locator('#resumeCorpusJob').click();
    await page.locator('#corpusResumeForm [name=retry]').check();
    await page.locator('#corpusResumeForm button[type=submit]').click();
    await expect(page.locator('#corpusVersion')).toHaveValue('1',{timeout:20000});
    await expect(page.locator('#corpusJobPanel')).toContainText('已完成');
    await page.locator('#corpusCallList').click();
    await expect(page.locator('#drawerBody')).toContainText('unknown');
    await page.locator('[data-corpus-call]').first().click();
    await expect(page.locator('#drawerBody')).toContainText('messages');
    await page.locator('#drawer [data-close-drawer]').click();
    await page.setViewportSize({width:390,height:844});
    await page.goto(bookUrl);
    await page.locator('[data-corpus-tab=distribution]').click();
    const dimensions=await page.evaluate(()=>({viewport:innerWidth,body:document.body.scrollWidth}));
    expect(dimensions.body).toBeLessThanOrEqual(dimensions.viewport);
    await page.screenshot({path:path.join(out,'结构分布_390px.png'),fullPage:true});
    await page.locator('[data-corpus-tab=threads]').click();
    await page.locator('[data-corpus-edit]').first().click();
    await expect(page.locator('#corpusDomainDetails')).toBeVisible();
    await page.screenshot({path:path.join(out,'结构编辑_390px.png')});
    const form=await page.locator('#corpusRecordForm').evaluate(el=>({width:el.clientWidth,scroll:el.scrollWidth}));
    expect(form.scroll).toBeLessThanOrEqual(form.width);
    expect(errors).toEqual([]);
    const result={passed:true,isolated:true,provider:meta.provider,desktop:{width:1440,height:1000},mobile:dimensions,form,errors,
      auto_recommendations_missing_status:autoStatus};
    fs.writeFileSync(path.join(out,'浏览器核验.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
  }catch(error){await page.screenshot({path:path.join(out,'failure.png'),fullPage:true});throw error;}
  finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
