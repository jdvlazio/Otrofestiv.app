const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.mouse.click(243,806); await p.waitForTimeout(2000);
  const btn=p.getByText('Calcular mi Plan',{exact:true}).first();
  const b=await btn.boundingBox();
  await p.mouse.click(b.x+b.width/2,b.y+b.height/2);
  await p.waitForTimeout(4000);
  const ni=p.getByText('NO INCLUIDAS',{exact:false}).first();
  await ni.evaluate(e=>e.scrollIntoView({block:'start'}));
  await p.waitForTimeout(800);
  await p.screenshot({path:S+'21-no-incluidas.png'});
  // abrir Disponibilidad
  await p.mouse.click(195,141); await p.waitForTimeout(1200);
  await p.screenshot({path:S+'22-disponibilidad.png'});
});
