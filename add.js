const {run}=require('./h');const {enter}=require('./f');
const T=process.argv[2];
run(async(p,S)=>{
  await enter(p);
  await p.mouse.click(48,806); await p.waitForTimeout(1500); await p.click("#pmode-manana",{force:true});
  await p.waitForTimeout(1600);
  const el=p.getByText(T,{exact:true}).first();
  await el.evaluate(e=>e.scrollIntoView({block:'center'})); await p.waitForTimeout(500);
  const b=await el.boundingBox(); await p.mouse.click(b.x+5,b.y+b.height/2);
  await p.waitForTimeout(2000);
  const ag=await p.$('[data-action="addSuggestion"]');
  if(!ag){console.log('SIN AGREGAR');await p.screenshot({path:S+'x-'+T.slice(0,8)+'.png'});return;}
  const bb=await ag.boundingBox(); await p.mouse.click(bb.x+bb.width/2,bb.y+bb.height/2);
  await p.waitForTimeout(2000);
  await p.screenshot({path:S+'add-'+T.slice(0,12).replace(/[ ,]/g,'_')+'.png'});
  console.log(await p.evaluate(()=>document.body.innerText.split('Omitir')[1].slice(0,600)));
});
