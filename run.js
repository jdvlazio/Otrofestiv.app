const { chromium } = require('playwright');
const SHOT='../shots/';
(async()=>{
const b=await chromium.launch();
const ctx=await b.newContext({viewport:{width:390,height:844},userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',locale:'es-CO',deviceScaleFactor:2,isMobile:true,hasTouch:true});
const p=await ctx.newPage();
await p.goto('https://otrofestiv.app',{waitUntil:'domcontentloaded'});
await p.waitForSelector('html[data-app-ready="1"]');
await p.waitForTimeout(3000);
const card=p.locator('#splash-rail .splash-card[data-fest="finca2026"]').first();
await card.scrollIntoViewIfNeeded(); await p.waitForTimeout(500); await card.click(); await p.waitForTimeout(600);
await p.locator('button:has-text("Entrar")').first().click(); await p.waitForTimeout(2800);

const heart=async(day,title)=>{
 await p.locator('button.dtab').nth(day).click(); await p.waitForTimeout(1100);
 const loc=p.locator('.plist-item').filter({has:p.locator('.plist-title-txt',{hasText:title})}).locator('.plist-heart').first();
 await loc.click(); await p.waitForTimeout(1000);
 const wl=await p.evaluate(()=>JSON.parse(localStorage.getItem('finca2026_wl')||'[]'));
 console.log('heart "'+title+'" -> wl('+wl.length+'):',wl.join(' / '));
};
await heart(5,'La vida fracturada');
await heart(6,'Mora');
await heart(6,'¿Cuán profundo es tu amor?');
await heart(7,'Yintah');
await heart(7,'Tierra que habla');
await heart(8,'El costo del crecimiento');

await p.locator('button.main-nav-tab',{hasText:'INTERESES'}).click(); await p.waitForTimeout(1600);
await p.screenshot({path:SHOT+'20-intereses.png',fullPage:true});
console.log('== INTERESES ==');
console.log((await p.evaluate(()=>document.body.innerText)).replace(/[\s\S]*?Omitir\n/,'').split('CAMBIAR FESTIVAL')[0].slice(0,1800));

await p.locator('button.main-nav-tab',{hasText:'PLANEAR'}).click(); await p.waitForTimeout(1800);
await p.screenshot({path:SHOT+'21-planear.png',fullPage:true});
console.log('== PLANEAR ==');
console.log((await p.evaluate(()=>document.body.innerText)).replace(/[\s\S]*?Omitir\n/,'').split('CAMBIAR FESTIVAL')[0].slice(0,2500));

await ctx.storageState({path:'../state2.json'});
await b.close();
})();
