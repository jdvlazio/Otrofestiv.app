const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.mouse.click(243,806); await p.waitForTimeout(2000);
  const d=p.getByText('Disponibilidad',{exact:true}).first();
  const b=await d.boundingBox(); console.log('disp',b);
  await p.mouse.click(b.x+b.width/2,b.y+b.height/2);
  await p.waitForTimeout(1500);
  await p.screenshot({path:S+'23-disp.png'});
  console.log(await p.evaluate(()=>document.body.innerText.split('Omitir')[1].slice(0,900)));
});
