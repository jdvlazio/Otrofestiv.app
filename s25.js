const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.waitForTimeout(1200);
  await p.mouse.click(278,127); // DOM 16 en la tira
  await p.waitForTimeout(1800);
  await p.screenshot({path:S+'31-dom16.png'});
  await p.evaluate(()=>window.scrollBy(0,700)); await p.waitForTimeout(900);
  await p.screenshot({path:S+'32-dom16-abajo.png'});
  console.log(await p.evaluate(()=>document.body.innerText.split('Omitir')[1].slice(0,1500)));
});
