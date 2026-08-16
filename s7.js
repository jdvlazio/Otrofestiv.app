const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.getByText('Mañana',{exact:true}).first().click({force:true});
  await p.waitForTimeout(1500);
  await p.mouse.click(150,290);
  await p.waitForTimeout(2000);
  await p.mouse.click(336,342); // + Agregar
  await p.waitForTimeout(1800);
  await p.screenshot({path:S+'09-tras-agregar.png'});
  console.log(await p.evaluate(()=>document.body.innerText.split('Omitir')[1].slice(0,700)));
});
