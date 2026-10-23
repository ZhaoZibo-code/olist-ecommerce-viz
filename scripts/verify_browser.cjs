const {createRequire}=require('node:module');const fs=require('node:fs');const path=require('node:path');
const runtimeRoot=path.join(require('node:os').homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const req=createRequire(path.join(runtimeRoot,'entry.cjs'));const {chromium}=req('playwright');
const ROOT=path.resolve(__dirname,'..');const base=process.env.OLIST_TEST_URL||'http://127.0.0.1:8791';
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});let errors=[];page.on('pageerror',e=>errors.push(String(e)));
 const out=path.join(ROOT,'deliverables/screenshots');fs.mkdirSync(out,{recursive:true});let results=[];
 await page.goto(base,{waitUntil:'networkidle'});await page.evaluate(()=>document.fonts.ready);await page.waitForFunction(()=>document.querySelectorAll('canvas').length>=10);
 await page.addStyleTag({content:'html{scroll-behavior:auto!important;scroll-snap-type:none!important}*{animation-duration:0s!important;transition:none!important}'});
 const chapterIds=await page.locator('.chapter').evaluateAll(es=>es.map(e=>e.id));
 for(const [i,id] of chapterIds.entries()){
  await page.locator('#nav [data-goto=\"'+id+'\"]').click();await page.waitForTimeout(350);
  await page.screenshot({path:path.join(out,'course-web-'+i+'.png')});results.push({kind:'roadshow',chapter:i,title:await page.locator('#'+id).getAttribute('data-title')});
 }
 await page.locator('#nav [data-goto=\"p1\"]').click();await page.selectOption('#year','2017');await page.waitForTimeout(400);const roadYear=await page.locator('#year').inputValue();if(roadYear!=='2017')throw Error('Roadshow year failed');await page.selectOption('#year','all');
 await page.goto(base+'/reports/analysis/analysis_report.html',{waitUntil:'networkidle'});await page.waitForFunction(()=>document.querySelector('#loading').classList.contains('hide'),{timeout:60000});
 for(let y of ['2017','2018','all']){await page.selectOption('#year',y);await page.waitForFunction(()=>document.querySelector('#loading').classList.contains('hide'));if(await page.locator('#year').inputValue()!==y)throw Error('Atlas year failed');}
 await page.click('#present');
 for(let i=0;i<6;i++){
  await page.waitForTimeout(250);await page.screenshot({path:path.join(out,'course-atlas-'+i+'.png')});results.push({kind:'atlas',chapter:i,label:await page.locator('#slide-label').innerText()});
  if(i===2){await page.click('#treemap-btn');await page.waitForTimeout(200);await page.click('#sunburst-btn');}
  if(i<5)await page.click('#next-slide');
 }
 await browser.close();const record={result:errors.length?'failed':'passed',pages:results.length,pageErrors:errors,yearSelection:['all','2017','2018'],hierarchyToggle:true,pagesChecked:results};fs.writeFileSync(path.join(ROOT,'reports/browser_verification.json'),JSON.stringify(record,null,2));console.log(JSON.stringify(record));if(errors.length)process.exit(1);
})().catch(e=>{console.error(e);process.exit(1)});
