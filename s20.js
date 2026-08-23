const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.click('#pmode-manana',{force:true}); await p.waitForTimeout(1500);
  const titles=['Por una gota de leche','Three black men','Notas sobre un destierro','El silencio de los palafitos'];
  for(const t of titles){
    const el=p.getByText(t,{exact:true}).first();
    await el.evaluate(e=>e.scrollIntoView({block:'center'}));
    await p.waitForTimeout(400);
    const b=await el.boundingBox();
    await p.mouse.click(b.x+5,b.y+b.height/2);
    await p.waitForTimeout(1800);
    // buscar botón Agregar
    const ag=p.getByText('Agregar',{exact:false}).first();
    const vis=await ag.isVisible().catch(()=>false);
    if(vis){const bb=await ag.boundingBox(); await p.mouse.click(bb.x+bb.width/2,bb.y+bb.height/2); await p.waitForTimeout(1500);}
    else console.log('no Agregar for',t);
    await p.screenshot({path:S+'24-'+t.slice(0,8).replace(/ /g,'_')+'.png'});
    // cerrar sheet
    await p.keyboard.press('Escape'); await p.waitForTimeout(400);
    const x=await p.$('[data-action="closePelSheet"]'); if(x){const xb=await x.boundingBox(); if(xb) await p.mouse.click(xb.x+xb.width/2,xb.y+xb.height/2);}
    await p.waitForTimeout(1200);
  }
  await p.mouse.click(340,806); await p.waitForTimeout(2500);
  await p.screenshot({path:S+'25-miplan.png'});
  console.log(await p.evaluate(()=>document.body.innerText.split('Omitir')[1].slice(0,2000)));
});
