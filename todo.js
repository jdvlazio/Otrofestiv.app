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
await p.locator('button.dtab').first().click(); await p.waitForTimeout(1800);
await p.screenshot({path:SHOT+'51-todo.png'});
const t=(await p.evaluate(()=>document.body.innerText)).replace(/[\s\S]*?Omitir\n/,'').split('CAMBIAR FESTIVAL')[0];
console.log('== TODO ==\n'+t.slice(0,1200));
console.log('items:',await p.evaluate(()=>document.querySelectorAll('.plist-item').length));
// Mañana tab
await p.locator('button.pmode-tab').nth(1).click(); await p.waitForTimeout(1500);
await p.screenshot({path:SHOT+'52-manana.png'});
console.log('== MAÑANA ==\n'+(await p.evaluate(()=>document.body.innerText)).replace(/[\s\S]*?Omitir\n/,'').split('CAMBIAR FESTIVAL')[0].slice(0,600));
await b.close();
})();
