const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.screenshot({path:S+'06-tras-entrar.png'});
  await p.getByText('Mañana',{exact:true}).first().click({force:true});
  await p.waitForTimeout(1800);
  await p.screenshot({path:S+'07-manana.png'});
  console.log('---TEXTO---');
  console.log(await p.evaluate(()=>document.body.innerText.split('Omitir')[1].slice(0,3500)));
});
