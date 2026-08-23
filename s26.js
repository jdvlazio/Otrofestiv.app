const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.mouse.click(340,806); await p.waitForTimeout(1800); // MI PLAN
  await p.mouse.click(268,250); // cabecera DOM 16 del mini-calendario
  await p.waitForTimeout(1800);
  await p.screenshot({path:S+'33-plan-dom16.png'});
  await p.evaluate(()=>window.scrollBy(0,600)); await p.waitForTimeout(800);
  await p.screenshot({path:S+'34-plan-dom16-b.png'});
  console.log(await p.evaluate(()=>document.body.innerText.split('Omitir')[1].slice(0,1200)));
});
