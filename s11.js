const {open,SHOT}=require('./lib');
(async()=>{
const {b,ctx,p}=await open();
await p.locator('button.dtab',{hasText:'18'}).click(); await p.waitForTimeout(900);
await p.locator('text=Yintah').first().click(); await p.waitForTimeout(1500);
console.log(await p.evaluate(()=>[...document.querySelectorAll('button')].map(e=>{const r=e.getBoundingClientRect();return {t:e.innerText.replace(/\n/g,' ').slice(0,30),c:e.className.slice(0,40),vis:r.width>0&&r.height>0,x:Math.round(r.x),y:Math.round(r.y)};}).filter(o=>o.vis&&/Agregar|Inter|Prior/i.test(o.t))));
await b.close();
})();
