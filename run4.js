const { chromium } = require('playwright');
const SHOT='../shots/';
(async()=>{
const b=await chromium.launch();
const ctx=await b.newContext({storageState:'../state2.json',viewport:{width:390,height:844},userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',locale:'es-CO',deviceScaleFactor:2,isMobile:true,hasTouch:true});
const p=await ctx.newPage();
await p.goto('https://otrofestiv.app',{waitUntil:'domcontentloaded'});
await p.waitForSelector('html[data-app-ready="1"]'); await p.waitForTimeout(3000);
if(await p.locator('#splash-rail').isVisible().catch(()=>0)){
 const c=p.locator('#splash-rail .splash-card[data-fest="finca2026"]').first();
 await c.scrollIntoViewIfNeeded();await p.waitForTimeout(400);await c.click();await p.waitForTimeout(500);
 await p.locator('button:has-text("Entrar")').first().click();await p.waitForTimeout(2500);
}
await p.locator('button.main-nav-tab',{hasText:'PLANEAR'}).click(); await p.waitForTimeout(1500);
await p.locator('button:has-text("Calcular mi Plan")').click(); await p.waitForTimeout(2500);
await p.locator('button:has-text("Usar este Plan")').click(); await p.waitForTimeout(2500);
await p.screenshot({path:SHOT+'24-usar.png'});
console.log((await p.evaluate(()=>document.body.innerText)).replace(/[\s\S]*?Omitir\n/,'').split('CAMBIAR FESTIVAL')[0].slice(0,2000));
await p.locator('button.plan-confirm-cta').click(); await p.waitForTimeout(2500);
await p.screenshot({path:SHOT+'25-miplan.png'});
for(let i=1;i<=3;i++){await p.mouse.wheel(0,700);await p.waitForTimeout(700);await p.screenshot({path:SHOT+'25-miplan-'+i+'.png'});}
console.log('=== MI PLAN ===');
console.log((await p.evaluate(()=>document.body.innerText)).replace(/[\s\S]*?Omitir\n/,'').split('CAMBIAR FESTIVAL')[0].slice(0,2500));
await ctx.storageState({path:'../state2.json'});
await b.close();
})();
