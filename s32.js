const {run}=require('./h');
run(async(p,S)=>{
  await p.mouse.click(195,300); await p.waitForTimeout(600);
  await p.click('#splash-enter-btn'); await p.waitForTimeout(2500);
  await p.screenshot({path:S+'40-ciudades.png'});
  await p.click('[data-action="citySheetPick"][data-city="Quibdó"]');
  await p.waitForTimeout(2500);
  await p.screenshot({path:S+'41-quibdo.png'});
  console.log(await p.evaluate(()=>document.body.innerText.split('Omitir')[1].slice(0,800)));
});
