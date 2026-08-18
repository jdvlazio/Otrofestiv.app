const { chromium } = require('playwright');
const SHOT='../shots/';
async function open(){
const b=await chromium.launch();
let sp={};
try{ sp={storageState:'../state.json'} }catch(e){}
const ctx=await b.newContext(Object.assign({viewport:{width:390,height:844},userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',locale:'es-CO',deviceScaleFactor:2,isMobile:true,hasTouch:true},sp));
const p=await ctx.newPage();
await p.goto('https://otrofestiv.app',{waitUntil:'domcontentloaded'});
await p.waitForSelector('html[data-app-ready="1"]');
await p.waitForTimeout(2800);
const splashVisible = await p.locator('#splash-rail').isVisible().catch(()=>false);
if(splashVisible){
  const card=p.locator('#splash-rail .splash-card[data-fest="finca2026"]').first();
  await card.scrollIntoViewIfNeeded(); await p.waitForTimeout(500); await card.click();
  await p.waitForTimeout(600);
  await p.locator('button:has-text("Entrar")').first().click();
  await p.waitForTimeout(2500);
}
return {b,ctx,p,SHOT};
}
module.exports={open,SHOT};
