const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.screenshot({path:S+'11-abre-en.png'});
  await p.mouse.click(48,806); // PROGRAMA
  await p.waitForTimeout(1500);
  await p.getByText('Mañana',{exact:true}).first().click({force:true});
  await p.waitForTimeout(1500);
  await p.screenshot({path:S+'12-prog-manana-con-plan.png'});
  const info=await p.evaluate(()=>{
    const els=[...document.querySelectorAll('*')].filter(e=>e.childElementCount===0&&/En tu Plan/i.test(e.textContent));
    return els.map(e=>{const r=e.getBoundingClientRect();const s=getComputedStyle(e);return {t:e.textContent.trim(),cls:e.className,r:[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)],fs:s.fontSize,color:s.color,op:s.opacity}});
  });
  console.log(JSON.stringify(info));
});
