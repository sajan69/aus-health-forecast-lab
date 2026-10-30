const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const root=path.resolve(__dirname,'..');
const artifacts=path.join(root,'forecast-artifacts');
(async()=>{
 const browser=await chromium.launch({headless:true, ...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE}:{}),args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1280,height:900}});
 const problems=[],requests=[],checks=[];
 page.on('pageerror',e=>problems.push(e.message));
 page.on('dialog',async d=>{problems.push('dialog');await d.dismiss()});
 page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url())});
 try{
 await page.goto(pathToFileURL(path.join(artifacts,'report.html')).href);
 assert.match(await page.locator('h1').innerText(),/Carer Payment/);
 assert.match(await page.locator('body').innerText(),/Ridge change/);
 assert.equal(await page.locator('svg').count(),1);
 assert.equal(await page.locator('table').count(),3);
 assert.match(await page.locator('.notice').innerText(),/Research use only/);
 checks.push('computed tables, chart and intended-use warning');
 await page.locator('summary').click();
 assert.match(await page.locator('pre').innerText(),/6a72d3c5/);
 checks.push('expandable source, protocol and environment');
 await page.screenshot({path:path.join(artifacts,'desktop.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 assert(await page.locator('.scroll').first().evaluate(e=>e.scrollWidth>e.clientWidth));
 await page.screenshot({path:path.join(artifacts,'mobile.png'),fullPage:true});
 checks.push('390px body fit with table scrolling');
 await page.goto(pathToFileURL(path.join(artifacts,'probe.html')).href);
 assert.equal(await page.locator('script,img').count(),0);
 assert.match(await page.locator('body').innerText(),/<img/);
 assert.equal(problems.length,0);assert.equal(requests.length,0);
 checks.push('inert HTML payload and no network, dialogs or page errors');
 fs.writeFileSync(path.join(artifacts,'browser-checks.json'),JSON.stringify({checks,passed:checks.length,browser:browser.version()},null,2));
 for(const c of checks)console.log('Passed: '+c);
 }catch(e){await page.screenshot({path:path.join(artifacts,'failure.png'),fullPage:true});throw e}
 finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
