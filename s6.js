const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.getByText('Mañana',{exact:true}).first().click({force:true});
  await p.waitForTimeout(1500);
  await p.mouse.click(150,290); // Feito Pipa
  await p.waitForTimeout(2200);
  await p.screenshot({path:S+'08-ficha.png'});
  console.log(await p.evaluate(()=>document.body.innerText.split('Omitir')[1].slice(0,2000)));
});
