const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.mouse.click(48,806); await p.waitForTimeout(1200);
  await p.getByText('Mañana',{exact:true}).first().click({force:true});
  await p.waitForTimeout(1500);
  const rows=await p.evaluate(()=>[...document.querySelectorAll('.film-row,[data-action="openFilm"],.prog-row')].slice(0,30).map(e=>({c:e.className,t:e.innerText.split('\n')[0]})));
  console.log(JSON.stringify(rows,null,0).slice(0,1500));
});
