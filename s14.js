const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.mouse.click(48,806); await p.waitForTimeout(1200);
  await p.getByText('Mañana',{exact:true}).first().click({force:true});
  await p.waitForTimeout(1500);
  for(let i=1;i<11;i++){
    const hs=await p.$$('[data-action="toggleWLFromList"]');
    const h=hs.filter(async()=>true)[i]; if(!h)break;
    const vis=await h.isVisible().catch(()=>false); if(!vis){console.log('skip',i);continue;}
    const b=await h.boundingBox(); if(!b){console.log('nobox',i);continue;}
    await p.mouse.click(b.x+b.width/2,b.y+b.height/2);
    await p.waitForTimeout(500);
  }
  await p.waitForTimeout(1200);
  await p.screenshot({path:S+'15-hearts.png'});
  await p.mouse.click(146,806); await p.waitForTimeout(2200);
  await p.screenshot({path:S+'16-intereses.png'});
  console.log(await p.evaluate(()=>document.body.innerText.split('Omitir')[1].slice(0,1800)));
});
