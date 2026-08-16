const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  if(await p.$('#pmode-manana')) await p.click('#pmode-manana',{force:true});
  await p.waitForTimeout(1500);
  for(const i of [0,7,8,9,10]){
    const hs=await p.$$('[data-action="toggleWLFromList"]');
    const h=hs[i];
    await h.evaluate(e=>e.scrollIntoView({block:'center'}));
    await p.waitForTimeout(400);
    const b=await h.boundingBox();
    await p.mouse.click(b.x+b.width/2,b.y+b.height/2);
    await p.waitForTimeout(900);
  }
  await p.mouse.click(146,806); await p.waitForTimeout(2200);
  await p.screenshot({path:S+'18-intereses.png'});
  console.log(await p.evaluate(()=>document.body.innerText.split('Omitir')[1].slice(0,1500)));
});
