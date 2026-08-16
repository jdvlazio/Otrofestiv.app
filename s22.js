const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.click('#pmode-manana',{force:true}); await p.waitForTimeout(1500);
  const titles=['Feito Pipa','Por una gota de leche','Three black men','Notas sobre un destierro','El silencio de los palafitos'];
  for(const t of titles){
    const el=p.getByText(t,{exact:true}).first();
    await el.evaluate(e=>e.scrollIntoView({block:'center'})); await p.waitForTimeout(400);
    const b=await el.boundingBox(); await p.mouse.click(b.x+5,b.y+b.height/2);
    await p.waitForTimeout(1800);
    const ag=await p.$('[data-action="addSuggestion"]');
    if(ag){const bb=await ag.boundingBox(); await p.mouse.click(bb.x+bb.width/2,bb.y+bb.height/2); await p.waitForTimeout(1600);}
    else console.log('sin Agregar:',t);
    await p.screenshot({path:S+'26-'+t.slice(0,10).replace(/[ ,]/g,'_')+'.png'});
    const cl=await p.$('[data-action="closePelSheet"]');
    if(cl){const cb=await cl.boundingBox(); if(cb) await p.mouse.click(cb.x+cb.width/2,cb.y+cb.height/2);}
    await p.waitForTimeout(1300);
  }
  await p.mouse.click(340,806); await p.waitForTimeout(2500);
  await p.screenshot({path:S+'27-miplan.png'});
  console.log(await p.evaluate(()=>document.body.innerText.split('Omitir')[1].slice(0,1800)));
});
