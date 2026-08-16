const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.mouse.click(340,806); await p.waitForTimeout(1800);
  await p.mouse.click(268,250); await p.waitForTimeout(1200);
  await p.evaluate(()=>window.scrollBy(0,600)); await p.waitForTimeout(700);
  await p.mouse.click(316,110); // Calendario
  await p.waitForTimeout(2500);
  await p.screenshot({path:S+'38-calendario.png'});
  console.log('--- tras Calendario ---');
  console.log(await p.evaluate(()=>document.body.innerText.split('Omitir')[1].slice(0,500)));
});
