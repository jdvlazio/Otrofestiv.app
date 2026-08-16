const {open,SHOT}=require('./lib');
const want=['La vida fracturada','Mora','¿Cuán profundo es tu amor?','Tierra que habla','El amor duerme en la calle','El costo del crecimiento','Qué perforado está mi valle'];
(async()=>{
const {b,ctx,p}=await open();
for(const d of ['16','17','18','19']){
 await p.locator('button.dtab',).nth(["12","13","14","15","16","17","18","19"].indexOf(d)+1).click(); await p.waitForTimeout(900);
 for(const title of want){
   const n=await p.evaluate((t)=>{
     const rows=[...document.querySelectorAll('body *')].filter(e=>e.offsetParent&&e.innerText&&e.innerText.trim().startsWith(t)&&e.children.length===0);
     return rows.length;
   },title);
   if(!n) continue;
   // find heart button in same row
   const ok=await p.evaluate((t)=>{
     const el=[...document.querySelectorAll('body *')].find(e=>e.offsetParent&&e.children.length===0&&e.innerText.trim()===t);
     if(!el) return 'no-title';
     let row=el; for(let i=0;i<6&&row;i++){ const btn=row.querySelector&&row.querySelector('button[class*=fav],button[class*=heart],button[aria-label*="nter"],button[data-action*="fav"],button[data-action*="interes"]'); if(btn){btn.click();return 'clicked:'+btn.className;} row=row.parentElement;}
     return 'no-heart';
   },title);
   console.log(d,title,ok);
 }
}
await p.waitForTimeout(1000);
await ctx.storageState({path:'../state.json'});
await b.close();
})();
