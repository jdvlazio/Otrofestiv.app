const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.mouse.click(48,806); await p.waitForTimeout(1500); await p.click("#pmode-manana",{force:true}); await p.waitForTimeout(1500);
  await p.mouse.click(323,105); // Lugar
  await p.waitForTimeout(1800);
  await p.screenshot({path:S+'37-lugar.png'});
  console.log(await p.evaluate(()=>document.body.innerText.split('Omitir')[1].slice(0,900)));
});
