const { chromium } = require('playwright');
const SHOT='../shots/';
(async()=>{
const b=await chromium.launch();
const ctx=await b.newContext({viewport:{width:390,height:844},userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',locale:'es-CO',deviceScaleFactor:2,isMobile:true,hasTouch:true});
const p=await ctx.newPage();
await p.goto('https://otrofestiv.app',{waitUntil:'domcontentloaded'});
await p.waitForSelector('html[data-app-ready="1"]'); await p.waitForTimeout(3200);
const c=p.locator('#splash-rail .splash-card[data-fest="finca2026"]').first();
await c.scrollIntoViewIfNeeded();await p.waitForTimeout(400);await c.click();await p.waitForTimeout(500);
await p.locator('button:has-text("Entrar")').first().click();await p.waitForTimeout(2800);
await p.locator('button.dtab').nth(4).click(); await p.waitForTimeout(1200);
// open ficha of a past film
await p.locator('.plist-title-txt',{hasText:'Karuara'}).first().click(); await p.waitForTimeout(1500);
await p.screenshot({path:SHOT+'45-ficha-pasada.png'});
console.log((await p.evaluate(()=>document.body.innerText)).replace(/[\s\S]*?Omitir\n/,'').split('CAMBIAR FESTIVAL')[0].slice(0,700));
await p.locator('button.pel-sheet-close').first().click({force:true}).catch(()=>{});
await p.waitForTimeout(800);
// heart it from list
await p.locator('.plist-item').filter({has:p.locator('.plist-title-txt',{hasText:'Karuara'})}).locator('.plist-heart').first().click();
await p.waitForTimeout(1200);
console.log('wl:',await p.evaluate(()=>localStorage.getItem('finca2026_wl')));
await p.locator('button.main-nav-tab',{hasText:'INTERESES'}).click(); await p.waitForTimeout(1500);
await p.screenshot({path:SHOT+'46-intereses-pasada.png'});
console.log('INTERESES:',(await p.evaluate(()=>document.body.innerText)).replace(/[\s\S]*?Omitir\n/,'').split('CAMBIAR FESTIVAL')[0].slice(0,600));
await p.locator('button.main-nav-tab',{hasText:'PLANEAR'}).click(); await p.waitForTimeout(1500);
await p.locator('button:has-text("Calcular mi Plan")').click(); await p.waitForTimeout(2500);
await p.screenshot({path:SHOT+'47-plan-pasada.png'});
console.log('PLAN:',(await p.evaluate(()=>document.body.innerText)).replace(/[\s\S]*?Omitir\n/,'').split('CAMBIAR FESTIVAL')[0].slice(0,900));
await b.close();
})();
