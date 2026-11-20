function portableOutput(name=''){const p=require('node:path'),f=require('node:fs');const root=p.resolve(process.env.STUDIO_CHECK_OUTPUT||'build/client-v3-browser-evidence');f.mkdirSync(root,{recursive:true});return p.join(root,name);}
const {chromium, expect}=require(process.env.PLAYWRIGHT_MODULE||'@playwright/test');
const fs=require('node:fs'); const out=portableOutput();
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE||undefined)});
 const page=await browser.newPage({viewport:{width:1440,height:1000}}); const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 const base=process.env.STUDIO_WIZARD_URL||'http://127.0.0.1:18765';
 await page.goto(base+'/#/home');
 await page.getByRole('button',{name:'新建小说',exact:true}).click();
 await expect(page.locator('#modalBody h2')).toContainText('为故事选择');
 const active=await page.locator('button.active[data-main]').getAttribute('data-main');
 const genreRec=await (await page.request.get(base+'/api/recommend?slot=genre&types='+encodeURIComponent(active))).json();
 await expect(page.locator('#modalBody [data-rec]')).toHaveCount(genreRec.recommendations.filter(Boolean).length);
 await page.screenshot({path:out+'/wizard-genres.png'});
 await page.locator('[data-sub]').first().click();
 await expect(page.locator('#wizardNext')).toBeEnabled();
 await page.locator('#wizardNext').click();
 await expect(page.locator('#modalBody h2')).toHaveText('风格');
 if(process.env.WIZARD_EXPECT_DATA){await page.getByText('选项用法参考',{exact:true}).click();await expect(page.locator('#modalBody [data-rec="tone.TONE_SERIOUS"]')).toBeVisible();}
 await page.locator('#modalBody [data-option]').first().click();
 await expect(page.locator('#drawer')).toBeVisible();
 await page.locator('#drawerBody [data-option]').first().click();
 await page.locator('#drawer [data-close-drawer]').click();
 await page.locator('#wizardNext').click();
 for(const title of ['文笔','写法','世界观','人物']) {
   await expect(page.locator('#modalBody h2')).toHaveText(title);
   await page.locator('#wizardSkip').click();
 }
 await expect(page.locator('#modalBody h2')).toHaveText('结构篇幅');
 await page.locator('[name=bookTier][value="300000"]').check();
 await expect(page.locator('.length-chapter-rule')).toContainText('2,000–2,500');
 await page.locator('#volumeCount').fill('1');
 await page.locator('#wizardNext').click();
 await expect(page.locator('#modalBody h2')).toHaveText('卖点');
 await page.locator('#wizardSkip').click();
 await expect(page.locator('#modalBody h2')).toHaveText('确认立项卡');
 await expect(page.locator('.selection-summary')).toContainText('30 万字');
 await page.locator('#wizardTitle').fill('[UI TEST] 回声档案');
 await page.locator('#wizardIdea').fill('[UI TEST] 一名抄书员发现昨日的档案被改写，必须在封库前找回原始记录。');
 await page.screenshot({path:out+'/wizard-confirm.png'});
 const responsePromise=page.waitForResponse(r=>r.url().endsWith('/api/novels')&&r.request().method()==='POST');
 await page.locator('#wizardNext').click();
 const response=await responsePromise;const data=await response.json();
 if(response.status()!==201)throw new Error(JSON.stringify(data));
 await expect(page).toHaveURL(new RegExp('#/studio/'+data.novel.id));
 await expect(page.locator('#studioNotice')).toContainText('CONFIG_REQUIRED');
 await expect(page.locator('#studioSide')).toContainText('全书设计');
 await page.screenshot({path:out+'/studio-unconfigured.png'});
 const detail=await (await page.request.get(base+'/api/novels/'+data.novel.id)).json();
 expect(detail.novel.wizard.tone_ids).toHaveLength(1);
 expect(detail.novel.wizard.length_mode).toBe('tiered');
 expect(detail.novel.wizard.target_words).toBe(300000);
 expect(detail.novel.wizard.volume_count).toBe(1);
 if(process.env.WIZARD_EXPECT_DATA)expect(detail.novel.wizard.author_references.length).toBeGreaterThan(0);
 if(errors.length)throw new Error(errors.join('\n'));
 fs.writeFileSync(out+'/browser-wizard.json',JSON.stringify({passed:true,id:data.novel.id,project_dir:data.novel.project_dir,errors},null,2));
 console.log(JSON.stringify({passed:true,id:data.novel.id,errors}));await browser.close();
})().catch(e=>{console.error(e);process.exit(1);});
