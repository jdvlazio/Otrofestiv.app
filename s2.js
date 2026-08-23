const {run}=require('./h');
run(async(p,S)=>{
  // como usuario: toco "Entrar" con el dedo
  await p.mouse.click(195,601);
  await p.waitForTimeout(1200);
  await p.screenshot({path:S+'02a-tras-tocar-entrar.png'});
  const dis=await p.$eval('#splash-enter-btn',e=>e.disabled);
  console.log('sigue disabled?',dis);
  // ahora toco el afiche
  await p.mouse.click(195,300);
  await p.waitForTimeout(1200);
  console.log('tras tocar afiche disabled?',await p.$eval('#splash-enter-btn',e=>e.disabled));
  await p.screenshot({path:S+'02b-afiche.png'});
  await p.click('#splash-enter-btn');
  await p.waitForTimeout(3000);
  await p.screenshot({path:S+'03-home.png'});
  console.log(await p.evaluate(()=>document.body.innerText.slice(0,2000)));
});
