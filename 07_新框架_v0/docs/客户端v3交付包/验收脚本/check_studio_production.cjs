function portableOutput(name=''){const p=require('node:path'),f=require('node:fs');const root=p.resolve(process.env.STUDIO_CHECK_OUTPUT||'build/client-v3-browser-evidence');f.mkdirSync(root,{recursive:true});return p.join(root,name);}
const {chromium,expect}=require(process.env.PLAYWRIGHT_MODULE||'@playwright/test');
const fs=require('node:fs');
const out=portableOutput(),base=process.env.STUDIO_FIXTURE_URL||'http://127.0.0.1:18766';
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE||undefined)});
 const page=await browser.newPage({viewport:{width:1520,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const novel=(await(await page.request.get(base+'/api/novels')).json()).novels[0],id=novel.id;
 await page.goto(base+'/#/studio/'+id);
 const snapshot=async()=>{const response=await page.request.get(base+'/api/novels/'+id+'/progress');const data=await response.json();if(!response.ok())throw Error(JSON.stringify({base,id,status:response.status(),data}));return data;};
 async function waiting(){await expect.poll(async()=>(await snapshot()).status,{timeout:90000,intervals:[500,1000]}).toBe('WAITING');await expect(page.locator('[data-gate]').first()).toBeVisible({timeout:10000});}
 async function approve(action,shot){await waiting();await page.locator('[data-gate]').first().click();await page.locator('#gateReason').fill('[FAKE] 浏览器隔离验收：检查方案和证据后确认。');if(shot)await page.screenshot({path:out+'/'+shot});const response=page.waitForResponse(r=>r.url().includes('/gates/')&&r.request().method()==='POST');await page.locator(`[data-gate-action=${action}]`).click();const result=await response;if(!result.ok())throw Error(JSON.stringify({status:result.status(),data:await result.json()}));await expect.poll(async()=>(await snapshot()).status,{timeout:90000,intervals:[500,1000]}).toBe('DONE');await expect(page.locator('#drawer')).not.toBeVisible();await expect(page.locator('[data-gate]')).toHaveCount(0);await expect(page.locator('#statusTask')).toHaveText('当前任务已完成');}
 if(!process.env.STUDIO_SKIP_DESIGN){await approve('approve','production-book-gate.png');
 await page.locator('#runNovel').click();await approve('approve','production-chapter-gate.png');
 await page.locator('#runNovel').click();}await waiting();
 await page.locator('#studioSide [data-node]').last().click();await expect(page.locator('#manuscriptRead')).toContainText('[FAKE]');
 await expect(page.locator('#inspectorContent')).toContainText('通过');await page.screenshot({path:out+'/production-review.png'});
 await approve('accept');
 await page.locator('#btnZenRead').click();await expect(page.locator('#zenReaderContainer')).toContainText('[FAKE]');await page.screenshot({path:out+'/production-reader.png'});
 await page.locator('[data-editor-tab=text]').click();await page.locator('#startEditing').click();
 const old=await page.locator('#manuscriptText').inputValue();await page.locator('#manuscriptText').fill(old+'\n[FAKE] 手动修改形成第二版本，仅用于版本对比验收。');
 await page.locator('#saveDraft').click();await expect(page.locator('#studioEditor')).toContainText('2 个版本');
 await page.locator('#btnZenDiff').click();await expect(page.locator('#zenDiffContainer')).toContainText('手动修改');await expect(page.locator('#zenDiffContainer ins')).not.toHaveCount(0);await page.screenshot({path:out+'/production-diff.png'});
 await page.locator('#showQuality').click();await expect(page.locator('#inspectorContent')).toContainText('尚无匹配的审稿结果');
 await page.goto(base+'/#/book/'+id);await expect(page.getByRole('heading',{level:1})).toContainText('[FAKE]');await page.screenshot({path:out+'/production-book.png'});
 if(errors.length)throw Error(errors.join('\n'));const result={passed:true,id,errors};fs.writeFileSync(out+'/browser-production.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
