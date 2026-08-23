const {run}=require('./h');
run(async(p,S)=>{
  await p.mouse.click(195,300); await p.waitForTimeout(600);
  await p.click('#splash-enter-btn'); await p.waitForTimeout(2500);
  await p.mouse.click(195,322); // Bogotá
  await p.waitForTimeout(2500);
  await p.screenshot({path:S+'04-prog-bogota.png'});
  console.log(await p.evaluate(()=>document.body.innerText.slice(0,1200)));
});
