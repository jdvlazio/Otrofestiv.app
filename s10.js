const {open,SHOT}=require('./lib');
(async()=>{
const {b,ctx,p}=await open();
await p.locator('button.dtab',{hasText:'18'}).click(); await p.waitForTimeout(900);
await p.locator('text=Yintah').first().click(); await p.waitForTimeout(1200);
const box=await p.evaluate(()=>{const el=[...document.querySelectorAll('button')].find(e=>e.offsetParent&&/Agregar/.test(e.innerText)&&!e.className.includes('conflict')&&!e.className.includes('suggestion'));const r=el.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,cls:el.className};});
console.log(box);
await p.mouse.click(box.x,box.y);
await p.waitForTimeout(1500);
await p.screenshot({path:SHOT+'12-tras-agregar.png'});
console.log(await p.evaluate(()=>[...document.querySelectorAll('button')].filter(e=>e.offsetParent&&/Inter|Agregar|Prioriz|Quitar|plan/i.test(e.innerText)).map(e=>e.innerText.replace(/\n/g,' ')+' ['+e.className+']')));
await ctx.storageState({path:'../state.json'});
await b.close();
})();
