// Behavioral and projection-layout regression checks for the offline defense.
const {createRequire}=require('node:module');
const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');
const req=createRequire(path.join(require('node:os').homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/entry.cjs'));
const {chromium}=req('playwright');const ROOT=path.resolve(__dirname,'..');
const base=process.env.OLIST_TEST_URL||'http://127.0.0.1:8780/';
const expected=['p0','project-video','foundation','p1','p2','p3','p5','p6','customer-cohort','p8','completion'];
const output=path.join(ROOT,'deliverables/screenshots/defense');fs.mkdirSync(output,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 const ctx=await browser.newContext({viewport:{width:1366,height:768},reducedMotion:'reduce'});
 const page=await ctx.newPage();const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto(base,{waitUntil:'load'});await page.waitForFunction(()=>document.body.classList.contains('ready'));await page.evaluate(()=>document.fonts.ready);
 const chapters=await page.locator('.chapter:not([data-route="supplement"])').evaluateAll(es=>es.map(e=>e.id));assert.deepEqual(chapters,expected);
 assert.equal(await page.locator('.chapter[data-route="supplement"]').count(),2);
 assert.equal(await page.locator('[data-seconds]').evaluateAll(es=>es.reduce((a,e)=>a+Number(e.dataset.seconds),0)),535);
 assert.match(await page.title(),/Olist 巴西电商数据分析与可视化/);
 const layout=[];
 for(const [width,height] of [[1366,768],[1440,900],[1920,1080]]){
  await page.setViewportSize({width,height});
  for(const id of [...expected,'p4','p7']){
   await page.locator(`#nav [data-goto="${id}"]`).click();await page.waitForTimeout(120);
   const record=await page.locator('#'+id).evaluate(el=>{
    const r=el.getBoundingClientRect();const footer=el.querySelector('.chapter-foot');
    const overflow=[...el.querySelectorAll('h1,h2,.lead,.grain-table,.team-line,.cohort-stat,.output-list,.team-list')].filter(e=>e.getClientRects().length&&e.scrollWidth>e.clientWidth+3).map(e=>e.className||e.tagName);
    return {chapter:el.id,height:Math.round(r.height),viewport:innerHeight,footerBottom:footer?Math.round(footer.getBoundingClientRect().bottom):null,horizontalOverflow:document.documentElement.scrollWidth>innerWidth+2,textOverflow:overflow,charts:[...el.querySelectorAll('.chart')].map(e=>({id:e.id,width:e.clientWidth,height:e.clientHeight,canvas:!!e.querySelector('canvas')}))};
   });
   assert.doesNotMatch(await page.locator('body').innerText(),/演讲提示|翻页 · F|正文约|[0-9]+秒|问答时展示|页面构建|内嵌|离线展示|scripts\//);record.width=width;layout.push(record);
   await page.screenshot({path:path.join(output,`${width}-${id}.png`)});
  }
 }
 await page.setViewportSize({width:1440,height:900});
 // Footer navigation follows only the eleven main chapters.
 await page.locator('#restart').click();for(const id of expected){assert.equal(await page.locator('.chapter:not([hidden])').getAttribute('id'),id);if(id!==expected.at(-1))await page.click('#next');}
 assert.equal(await page.locator('#next').isDisabled(),true);
 // Catalog and evidence remain accessible with stable chapter identities.
 await page.click('#catalogBtn');assert.doesNotMatch(await page.locator('#catalog').innerText(),/秒|分钟|选讲|翻页跳过/);await page.screenshot({path:path.join(output,'catalog-clean.png')});await page.locator('#extraCatalog [data-goto="p4"]').click();assert.match(await page.locator('#pageCount').innerText(),/补充/);await page.locator('#p4 .supplement-return').click();assert.equal(await page.locator('.chapter:not([hidden])').getAttribute('id'),'p8');
 await page.click('#methodBtn');for(const key of ['sources','quality','money','sensitivity','limits','reproduce']){await page.locator(`[data-evidence-tab="${key}"]`).click();assert.doesNotMatch(await page.locator('#evidenceBody').innerText(),/scripts\/|snapshot\.json|内嵌|离线展示|页面构建|没有把页面/);}await page.screenshot({path:path.join(output,'methods-clean.png')});await page.locator('[data-evidence-tab="money"]').click();assert.match(await page.locator('#evidenceBody').innerText(),/13,591,643.70/);await page.locator('[data-evidence-tab="sensitivity"]').click();assert.match(await page.locator('#evidenceBody').innerText(),/53.13/);await page.keyboard.press('Escape');assert.equal(await page.locator('#methods').isVisible(),false);
 // Year filtering and fixed-scope cohort chapters do not cross-contaminate.
 await page.locator('#nav [data-goto="p2"]').click();await page.selectOption('#year','2017');assert.match(await page.locator('#stateDetail').innerText(),/订单/);await page.click('#geoBarBtn');assert.equal(await page.locator('#geoBarBtn').getAttribute('aria-pressed'),'true');
 await page.locator('#nav [data-goto="customer-cohort"]').click();assert.equal(await page.locator('#year').isDisabled(),true);assert.equal(await page.locator('#repeatPct').innerText(),'0.48%');assert.match(await page.locator('#repeatFraction').innerText(),/389 \/ 81,263/);assert.match(await page.locator('#cohortWindow').innerText(),/2018-06.*2018-07/);
 await page.locator('#nav [data-goto="p3"]').click();await page.click('#sunBtn');assert.equal(await page.locator('#sunBtn').getAttribute('aria-pressed'),'true');await page.click('#treeReset');
 await page.locator('#nav [data-goto="p8"]').click();await page.locator('#target').focus();await page.keyboard.press('ArrowRight');assert.equal(await page.locator('.chapter:not([hidden])').getAttribute('id'),'p8');assert.equal(await page.locator('#target').inputValue(),'25');
 await page.keyboard.press('n');assert.equal(await page.locator('#speaker, #notesBtn').count(),0);await page.click('#restart');assert.equal(await page.locator('#year').inputValue(),'all');assert.equal(await page.locator('#target').inputValue(),'20');
 // Embedded media is playable, owns its keyboard input, and stops on navigation.
 await page.locator('#nav [data-goto="project-video"]').click();await page.waitForFunction(()=>document.querySelector('video').readyState>=1);assert.equal(await page.locator('video').evaluate(v=>v.duration),120);
 await page.click('#playVideo');await page.waitForFunction(()=>document.querySelector('video').currentTime>.5);await page.locator('video').focus();await page.keyboard.press('ArrowRight');assert.equal(await page.locator('.chapter:not([hidden])').getAttribute('id'),'project-video');
 await page.click('#continueVideo');assert.equal(await page.locator('video').evaluate(v=>v.paused),true);const pausedTime=await page.locator('video').evaluate(v=>v.currentTime);await page.locator('#nav [data-goto="project-video"]').click();assert.ok(Math.abs(await page.locator('video').evaluate(v=>v.currentTime)-pausedTime)<.2);
 await page.click('#replayVideo');await page.waitForFunction(()=>!document.querySelector('video').paused);assert.ok(await page.locator('video').evaluate(v=>v.currentTime)<3);await page.click('#continueVideo');
 // Direct file:// opening succeeds with all networking disabled.
 const offline=await browser.newContext({viewport:{width:1440,height:900},offline:true,reducedMotion:'reduce'});const filePage=await offline.newPage();filePage.on('pageerror',e=>errors.push('offline: '+e));const external=[];filePage.on('request',r=>{if(/^https?:/.test(r.url()))external.push(r.url())});
 await filePage.goto('file://'+path.join(ROOT,'deliverables/olist_visual_report.html'),{waitUntil:'load'});await filePage.waitForFunction(()=>document.body.classList.contains('ready'));await filePage.evaluate(()=>document.fonts.ready);
 await filePage.locator('#nav [data-goto="project-video"]').click();await filePage.click('#playVideo');await filePage.waitForFunction(()=>document.querySelector('video').currentTime>.5);assert.equal(external.length,0);await filePage.click('#continueVideo');
 assert.equal(await filePage.locator('video').evaluate(v=>v.paused),true);await offline.close();
 const findings=layout.filter(r=>r.height>r.viewport+2||r.horizontalOverflow||r.textOverflow.length||r.footerBottom>r.viewport-49||r.charts.some(c=>c.width<50||!c.canvas));
 const report={status:findings.length||errors.length?'failed':'passed',mainChapters:expected,supplementalChapters:['p4','p7'],plannedSeconds:535,layout,findings,pageErrors:errors,offlineExternalRequests:external,behaviorChecks:['main route','catalog','evidence','year scope','cohort','chart mode','slider keyboard','restart','video keyboard','video pause/resume/replay','offline HTML playback']};
 fs.writeFileSync(path.join(ROOT,'reports/defense_verification.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({status:report.status,findings,pageErrors:errors,layoutChecks:layout.length}));await browser.close();if(report.status!=='passed')process.exitCode=1;
})().catch(e=>{console.error(e);process.exit(1)});
