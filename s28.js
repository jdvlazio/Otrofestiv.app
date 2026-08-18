const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.mouse.click(48,806); await p.waitForTimeout(1500); await p.click("#pmode-manana",{force:true}); await p.waitForTimeout(1500);
  await p.mouse.click(145,237); // "Cinemateca de Bogotá" bajo el título
  await p.waitForTimeout(2000);
  await p.screenshot({path:S+'36-venue.png'});
  const t=await p.evaluate(()=>document.body.innerText.split('Omitir')[1].slice(0,400));
  console.log(t);
  // ahora probar el filtro Lugar
  await p.keyboard.press('Escape');
});
