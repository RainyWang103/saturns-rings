/* Real-browser check, run by validation CI. No live services or travel research.
 * node check_delivery_browser.cjs PREVIEW.html OUTPUT_DIR [BASELINE.html]
 * Requires Playwright. Set PLAYWRIGHT_MODULE and CHROMIUM_EXECUTABLE if not
 * installed locally; FONT_CSS can supply a local CJK stylesheet for inspection.
 */
const fs=require('fs'),path=require('path');
const {pathToFileURL}=require('url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');

(async()=>{
 const [input,out,baseline]=process.argv.slice(2);
 if(!input||!out)throw Error('Expected PREVIEW.html OUTPUT_DIR [BASELINE.html]');
 fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE}:{}),args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader']});
 const context=await browser.newContext();
 const page=await context.newPage();
 const report={errors:[],network:[],viewports:[],interaction:{}};
 page.on('pageerror',e=>report.errors.push(e.message));
 await context.route(/^https?:/,route=>{report.network.push(route.request().url());return route.abort()});
 const open=async file=>{
  await page.goto(pathToFileURL(path.resolve(file)).href);
  if(process.env.FONT_CSS)await page.addStyleTag({content:fs.readFileSync(process.env.FONT_CSS,'utf8')});
  await page.evaluate(()=>document.fonts.ready);
 };
 const measure=()=>page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,
  transportHeight:[...document.querySelectorAll('.transport')].map(e=>Math.round(e.getBoundingClientRect().height)),
  visibleTransfers:[...document.querySelectorAll('.transport li')].filter(e=>e.getBoundingClientRect().height>0).length,
  clipped:[...document.querySelectorAll('main *')].filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&(r.right>innerWidth+1||r.left < -1)}).map(e=>({tag:e.tagName,cls:e.className,text:e.textContent.slice(0,60)}))}));
 for(const width of [320,390,768,1440]){
  await page.setViewportSize({width,height:900});
  const entry={width};
  if(baseline){await open(baseline);entry.before=await measure()}
  await open(input);entry.after=await measure();report.viewports.push(entry);
  if(width===390||width===1440){
   await page.screenshot({path:path.join(out,`new-${width}-top.png`)});
   // Avoid the sticky nav appearing mid-element in stitched screenshots.
   await page.addStyleTag({content:'.nav-wrap{position:static!important}'});
   for(const n of [1,2,3])await page.locator('#day'+n).screenshot({path:path.join(out,`new-${width}-day${n}.png`)});
   if(baseline){await open(baseline);await page.addStyleTag({content:'.nav-wrap{position:static!important}'});await page.locator('#day3').screenshot({path:path.join(out,`before-${width}-day3.png`)})}
  }
 }
 await page.setViewportSize({width:390,height:844});await open(input);
 for(let n=1;n<=3;n++){await page.locator(`nav a[href="#day${n}"]`).click();await page.waitForFunction(n=>location.hash==='#day'+n,n)}
 report.interaction.navigation=3;
 const check=page.locator('[data-check="concert"]');await check.check();await page.reload();report.interaction.checkPersists=await check.isChecked();await check.uncheck();
 await page.locator('#day2 .anchor-ref').click();report.interaction.anchorLink=await page.evaluate(()=>location.hash==='#anchor-day2');
 await page.locator('#map-sources summary').click();report.interaction.disclosure=await page.locator('#map-sources').getAttribute('open')!==null;
 await page.locator('#map-sources summary').click();await page.evaluate(()=>location.hash='#fixture-source');report.interaction.deepLink=await page.locator('#map-sources').getAttribute('open')!==null;
 await page.evaluate(()=>location.hash='#%E0%A4%A');
 await open(input);
 report.interaction.closedBeforePrint=await page.locator('#map-sources').getAttribute('open')===null;
 await page.emulateMedia({media:'print'});await page.evaluate(()=>window.dispatchEvent(new Event('beforeprint')));
 report.interaction.sourcesVisibleInPrint=await page.locator('#fixture-source').isVisible();
 await page.pdf({path:path.join(out,'preview-print.pdf'),printBackground:true,preferCSSPageSize:true});
 await page.evaluate(()=>window.dispatchEvent(new Event('afterprint')));report.interaction.printStateRestored=await page.locator('#map-sources').getAttribute('open')===null;
 await page.emulateMedia({media:'screen'});
 const blocked=await context.newPage();await blocked.addInitScript(()=>Object.defineProperty(window,'localStorage',{get(){throw new Error('Storage disabled')}}));
 blocked.on('pageerror',e=>report.errors.push(e.message));await blocked.goto(pathToFileURL(path.resolve(input)).href);await blocked.locator('[data-check="concert"]').check();report.interaction.noStorageWorks=await blocked.locator('[data-check="concert"]').isChecked();
 fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));
 await browser.close();
 const failed=report.errors.length||report.network.length||report.viewports.some(v=>v.after.scrollWidth>v.width||v.after.clipped.length||v.after.visibleTransfers!==9)||Object.values(report.interaction).some(v=>!v);
 console.log(JSON.stringify(report));if(failed)process.exitCode=1;
})().catch(e=>{console.error(e);process.exit(1)});
