/* Run only against serve_project_methods_fixture.py. */
const fs=require('node:fs'),path=require('node:path');
const {chromium,expect}=require(process.env.PLAYWRIGHT_MODULE||'@playwright/test');
const meta=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
if(!meta.isolated||meta.github_sync!==false)throw Error('An isolated FAKE fixture is required');
const out=path.resolve(process.env.STUDIO_CHECK_OUTPUT||'build/project-method-browser-evidence');fs.mkdirSync(out,{recursive:true});
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE||undefined});
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const network=[];page.on('requestfailed',r=>network.push({url:r.url(),failure:r.failure()}));
  try{
    await page.goto(`${meta.base}/#/studio/${encodeURIComponent(meta.novel_id)}`);
    await expect(page.locator('#runNovel')).toContainText('处理待确认事项',{timeout:20000});
    await page.locator('#runNovel').click();
    await expect(page.locator('#drawerBody')).toContainText('核对方法的适用条件');
    await page.locator('input[name=projectMethod]').check();
    await page.locator('#drawerBody details summary').first().click();
    await expect(page.locator('#drawerBody')).toContainText('本项目');
    await page.screenshot({path:path.join(out,'方法与前置确认_桌面.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    const gateSize=await page.locator('#drawerBody').evaluate(el=>({width:el.clientWidth,scroll:el.scrollWidth}));
    expect(gateSize.scroll).toBeLessThanOrEqual(gateSize.width);
    await page.screenshot({path:path.join(out,'方法与前置确认_390px.png'),fullPage:true});
    await page.locator('#gateReason').fill('[FAKE] 对照具体调查需求，原作多处证据和本项目前置均已核对。');
    await page.locator('[data-method-action=approve]').click();
    await page.setViewportSize({width:1440,height:1000});
    await expect.poll(async()=>{const r=await page.request.get(`${meta.base}/api/novels/${encodeURIComponent(meta.novel_id)}/progress`);return (await r.json()).gates.some(g=>g.target.candidates);},{timeout:20000}).toBe(true);
    await page.locator('#refreshProgress').click();
    await expect(page.locator('#runNovel')).toContainText('处理待确认事项',{timeout:20000});
    await page.locator('#runNovel').click();
    await expect(page.locator('#gateCandidate')).toBeVisible({timeout:10000});
    await page.locator('#gateReason').fill('[FAKE] 核对具体人物及剧情卡片，保留调查中的回应与代价。');
    await page.locator('[data-gate-action=approve]').click();
    await expect.poll(async()=>{const r=await page.request.get(`${meta.base}/api/novels/${encodeURIComponent(meta.novel_id)}/progress`);return (await r.json()).status;},{timeout:20000}).toBe('DONE');
    await page.locator('#refreshProgress').click();await page.locator('#studioToolbar details.menu summary').click();
    await page.locator('#openProjectMethods').click();
    await expect(page.locator('#projectMethodSettings')).toBeVisible();
    await expect(page.locator('#drawerBody')).toContainText('本项目实际执行与下游回执');
    await expect(page.locator('#drawerBody')).toContainText('尚无正文方法核验证据');
    const data=await(await page.request.get(`${meta.base}/api/novels/${encodeURIComponent(meta.novel_id)}/methods`)).json();
    expect(data.uses.some(r=>r.application&&r.validation==='VALID')).toBe(true);expect(data.review_checks).toHaveLength(0);
    await page.locator('#actualProjectMethodUses').scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(out,'实际方法执行回执_桌面.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    const form=await page.locator('#projectMethodSettings').evaluate(el=>({width:el.clientWidth,scroll:el.scrollWidth}));
    expect(form.scroll).toBeLessThanOrEqual(form.width);
    await page.locator('#projectMethodSettings [name=reason]').fill('[FAKE] 保留当前方法，用于后续任务。');
    await page.locator('#projectMethodSettings button[type=submit]').click();
    await expect(page.locator('#projectMethodSettings')).toBeVisible();
    await page.screenshot({path:path.join(out,'制作方法配置_390px.png'),fullPage:true});
    expect(errors).toEqual([]);
    const result={passed:true,isolated:true,model:meta.model,gateSize,form,errors,actual_applications:data.uses.filter(r=>r.application).length,prose_review_checks:data.review_checks.length};
    fs.writeFileSync(path.join(out,'浏览器核验.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
  }catch(error){await page.screenshot({path:path.join(out,'failure.png'),fullPage:true});fs.writeFileSync(path.join(out,'failure-network.json'),JSON.stringify(network,null,2));throw error;}
  finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
