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
for(const [tab,f] of [['INTERESES','40-empty-intereses'],['PLANEAR','41-empty-planear'],['MI PLAN','42-empty-miplan']]){
 await p.locator('button.main-nav-tab',{hasText:tab}).click(); await p.waitForTimeout(1800);
 await p.screenshot({path:SHOT+f+'.png'});
 console.log('==== '+tab+' (vacío) ====');
 console.log((await p.evaluate(()=>document.body.innerText)).replace(/[\s\S]*?Omitir\n/,'').split('CAMBIAR FESTIVAL')[0].slice(0,900));
}
// PLANEAR con 0 intereses: pulsar Calcular
await p.locator('button.main-nav-tab',{hasText:'PLANEAR'}).click(); await p.waitForTimeout(1500);
const cb=p.locator('button:has-text("Calcular mi Plan")');
console.log('calcular existe?',await cb.count(),'disabled?',await cb.first().isDisabled().catch(()=>'?'));
if(await cb.count()){await cb.first().click({force:true});await p.waitForTimeout(2500);await p.screenshot({path:SHOT+'43-calcular-vacio.png'});
console.log('== TRAS CALCULAR SIN INTERESES ==');
console.log((await p.evaluate(()=>document.body.innerText)).replace(/[\s\S]*?Omitir\n/,'').split('CAMBIAR FESTIVAL')[0].slice(0,900));}
// día pasado
await p.locator('button.main-nav-tab',{hasText:'PROGRAMA'}).click(); await p.waitForTimeout(1200);
await p.locator('button.dtab').nth(4).click(); await p.waitForTimeout(1200);
await p.screenshot({path:SHOT+'44-dia-pasado.png'});
console.log('== SÁB 15 (pasado) ==');
console.log((await p.evaluate(()=>document.body.innerText)).replace(/[\s\S]*?Omitir\n/,'').split('CAMBIAR FESTIVAL')[0].slice(0,900));
await b.close();
})();
