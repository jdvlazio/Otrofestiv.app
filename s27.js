const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.mouse.click(340,806); await p.waitForTimeout(1800);
  await p.mouse.click(268,250); await p.waitForTimeout(1500);
  await p.evaluate(()=>window.scrollBy(0,600)); await p.waitForTimeout(800);
  // tocar la sede
  await p.mouse.click(160,251);
  await p.waitForTimeout(2000);
  await p.screenshot({path:S+'35-sede.png'});
  console.log(await p.evaluate(()=>document.body.innerText.split('Omitir')[1].slice(0,700)));
});
