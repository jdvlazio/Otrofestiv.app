const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.mouse.click(48,806); await p.waitForTimeout(1500); await p.click("#pmode-manana",{force:true});
  await p.waitForTimeout(1600);
  const el=p.getByText('Three black men',{exact:true}).first();
  await el.evaluate(e=>e.scrollIntoView({block:'center'})); await p.waitForTimeout(500);
  const b=await el.boundingBox(); await p.mouse.click(b.x+5,b.y+b.height/2);
  await p.waitForTimeout(2000);
  const ag=await p.$('[data-action="addSuggestion"]');
  const bb=await ag.boundingBox(); await p.mouse.click(bb.x+bb.width/2,bb.y+bb.height/2);
  await p.waitForTimeout(1500);
  // en el sheet de conflicto: "Agregar"
  await p.mouse.click(195,686);
  await p.waitForTimeout(2000);
  await p.screenshot({path:S+'28-tras-conflicto.png'});
  await p.mouse.click(340,806); await p.waitForTimeout(2500);
  await p.screenshot({path:S+'29-miplan.png'});
  console.log(await p.evaluate(()=>document.body.innerText.split('Omitir')[1].slice(0,1500)));
});
