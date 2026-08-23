const {run}=require('./h');
run(async(p,S)=>{
  await p.mouse.click(90,105); // "Mañana"
  await p.waitForTimeout(1800);
  await p.screenshot({path:S+'05-manana.png'});
  const t=await p.evaluate(()=>{const m=document.querySelector('#programa,main,#tab-programa');return document.body.innerText});
  console.log(t.split('Omitir')[1].slice(0,3000));
});
