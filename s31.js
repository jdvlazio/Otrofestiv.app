const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  p.on('download',d=>console.log('DOWNLOAD:',d.suggestedFilename()));
  await enter(p);
  await p.mouse.click(340,806); await p.waitForTimeout(1800);
  await p.mouse.click(268,250); await p.waitForTimeout(1200);
  await p.evaluate(()=>window.scrollBy(0,600)); await p.waitForTimeout(700);
  await p.mouse.click(316,110); await p.waitForTimeout(3000);
  console.log('--- ahora Compartir ---');
  await p.mouse.click(220,110); await p.waitForTimeout(3000);
  await p.screenshot({path:S+'39-compartir.png'});
  console.log(await p.evaluate(()=>document.body.innerText.split('Omitir')[1].slice(0,400)));
});
