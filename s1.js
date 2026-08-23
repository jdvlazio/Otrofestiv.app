const { chromium } = require('playwright');
const SHOT='/private/tmp/claude-501/-Users-Juanda-Documents-Otrofestiv-dev/ac36ccd0-a238-46af-a759-d15ea587035c/scratchpad/shots/';
(async()=>{
const b=await chromium.launch();
const ctx=await b.newContext({viewport:{width:390,height:844},userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',locale:'es-CO',deviceScaleFactor:2,isMobile:true,hasTouch:true});
const p=await ctx.newPage();
p.on('console',m=>{if(m.type()==='error')console.log('CONSOLE ERR:',m.text().slice(0,200));});
await p.goto('https://otrofestiv.app',{waitUntil:'domcontentloaded'});
await p.waitForSelector('html[data-app-ready="1"]',{timeout:30000});
await p.waitForTimeout(3000);
await p.screenshot({path:SHOT+'01-splash.png'});
console.log('TITLE',await p.title());
console.log(await p.evaluate(()=>document.body.innerText.slice(0,1500)));
await ctx.storageState({path:'/private/tmp/claude-501/-Users-Juanda-Documents-Otrofestiv-dev/ac36ccd0-a238-46af-a759-d15ea587035c/scratchpad/state.json'});
await b.close();
})();
