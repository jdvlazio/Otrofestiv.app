const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.getByText('Mañana',{exact:true}).first().click({force:true});
  await p.waitForTimeout(1500);
  const dump=async(tag)=>{
    const st=await p.evaluate(()=>{
      const rows=[...document.querySelectorAll('[data-action="toggleWLFromList"]')].map(h=>{
        const row=h.closest('div,li,article');
        return {on:h.className, t:(row?row.innerText:'').split('\n')[0]};
      });
      return rows;
    });
    console.log(tag, JSON.stringify(st));
  };
  await dump('antes');
  // toco el corazón de "Héroes del silencio" (primer corto de las 14:00)
  const hs=await p.$$('[data-action="toggleWLFromList"]');
  const b=await hs[1].boundingBox();
  await p.mouse.click(b.x+b.width/2,b.y+b.height/2);
  await p.waitForTimeout(1200);
  await dump('despues');
  await p.screenshot({path:S+'17-un-corto.png'});
});
