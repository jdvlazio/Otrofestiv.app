const { chromium } = require('playwright');
const fs=require('fs');
const S='/private/tmp/claude-501/-Users-Juanda-Documents-Otrofestiv-dev/ac36ccd0-a238-46af-a759-d15ea587035c/scratchpad/shots/';
const ST='/private/tmp/claude-501/-Users-Juanda-Documents-Otrofestiv-dev/ac36ccd0-a238-46af-a759-d15ea587035c/scratchpad/state.json';
async function run(fn){
 const b=await chromium.launch();
 const opts={viewport:{width:390,height:844},userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',locale:'es-CO',deviceScaleFactor:2,isMobile:true,hasTouch:true};
 if(fs.existsSync(ST)) opts.storageState=ST;
 const c=await b.newContext(opts);
 const p=await c.newPage();
 p.on('console',m=>{if(m.type()==='error')console.log('[JSERR]',m.text())});
 await p.goto('https://otrofestiv.app',{waitUntil:'domcontentloaded'});
 await p.waitForSelector('html[data-app-ready="1"]',{timeout:30000});
 await p.waitForTimeout(2800);
 try{ await fn(p,S); }catch(e){ console.log('ERR',e.message); await p.screenshot({path:S+'err.png'}); }
 await c.storageState({path:ST});
 await b.close();
}
module.exports={run,S};
