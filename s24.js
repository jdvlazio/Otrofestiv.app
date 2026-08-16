const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.waitForTimeout(1500);
  await p.screenshot({path:S+'30-miplan-abre.png'});
  console.log(await p.evaluate(()=>document.body.innerText.split('Omitir')[1].slice(0,1200)));
});
