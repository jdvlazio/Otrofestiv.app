const { chromium } = require('playwright');
const SHOT='../shots/';
(async()=>{
const b=await chromium.launch();
const ctx=await b.newContext({storageState:'../state2.json',viewport:{width:390,height:844},userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',locale:'es-CO',deviceScaleFactor:2,isMobile:true,hasTouch:true});
const p=await ctx.newPage();
const dl=[];p.on('download',d=>dl.push(d.suggestedFilename()));
p.on('dialog',d=>{console.log('DIALOG',d.message());d.dismiss();});
await p.goto('https://otrofestiv.app',{waitUntil:'domcontentloaded'});
await p.waitForSelector('html[data-app-ready="1"]'); await p.waitForTimeout(3200);
if(await p.locator('#splash-rail').isVisible().catch(()=>0)){
 const c=p.locator('#splash-rail .splash-card[data-fest="finca2026"]').first();
 await c.scrollIntoViewIfNeeded();await p.waitForTimeout(400);await c.click();await p.waitForTimeout(500);
 await p.locator('button:has-text("Entrar")').first().click();await p.waitForTimeout(2500);
}
await p.locator('button.main-nav-tab',{hasText:'MI PLAN'}).click(); await p.waitForTimeout(2500);
await p.evaluate(()=>window.scrollTo(0,0)); await p.waitForTimeout(500);
// right arrow = 2nd mplan-nav-btn
await p.locator('button.mplan-nav-btn').nth(1).click(); await p.waitForTimeout(1300);
await p.screenshot({path:SHOT+'33-next-day.png'});
console.log('== TRAS FLECHA > ==');
console.log((await p.evaluate(()=>document.body.innerText)).replace(/[\s\S]*?Omitir\n/,'').split('CAMBIAR FESTIVAL')[0].slice(0,700));
await p.locator('button.mplan-nav-btn').nth(1).click(); await p.waitForTimeout(1300);
await p.screenshot({path:SHOT+'34-next-day2.png'});
console.log('== 2a FLECHA ==');
console.log((await p.evaluate(()=>document.body.innerText)).replace(/[\s\S]*?Omitir\n/,'').split('CAMBIAR FESTIVAL')[0].slice(0,700));
// Compartir
await p.locator('button[data-action="sharePlan"]').click(); await p.waitForTimeout(2500);
await p.screenshot({path:SHOT+'35-share.png'});
console.log('downloads',dl);
// Calendario
await p.locator('button[data-action="exportICS"]').click({force:true}).catch(e=>console.log('ics err',e.message.slice(0,80)));
await p.waitForTimeout(2500);
await p.screenshot({path:SHOT+'36-ics.png'});
console.log('downloads2',dl);
await b.close();
})();
