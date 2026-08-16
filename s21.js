const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.click('#pmode-manana',{force:true}); await p.waitForTimeout(1500);
  const el=p.getByText('Three black men',{exact:true}).first();
  await el.evaluate(e=>e.scrollIntoView({block:'center'})); await p.waitForTimeout(400);
  const b=await el.boundingBox(); await p.mouse.click(b.x+5,b.y+b.height/2);
  await p.waitForTimeout(1800);
  console.log(await p.evaluate(()=>[...document.querySelectorAll('#pel-sheet [data-action], .pel-sheet [data-action], [data-action]')].filter(e=>e.offsetParent&&/agreg|add|plan/i.test(e.dataset.action+e.innerText)).map(e=>({a:e.dataset.action,t:e.innerText.slice(0,30),y:Math.round(e.getBoundingClientRect().y)}))));
});
