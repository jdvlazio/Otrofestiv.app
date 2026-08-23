const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.getByText('Mañana',{exact:true}).first().click({force:true});
  await p.waitForTimeout(1500);
  await p.mouse.click(150,290);
  await p.waitForTimeout(2000);
  await p.mouse.click(336,342);
  await p.waitForTimeout(1500);
  await p.screenshot({path:S+'10-zoom-row.png',clip:{x:0,y:280,width:390,height:120}});
  const info=await p.evaluate(()=>{
    const els=[...document.querySelectorAll('*')].filter(e=>e.childElementCount===0&&/En tu Plan/.test(e.textContent));
    return els.map(e=>{const r=e.getBoundingClientRect();const s=getComputedStyle(e);return {t:e.textContent,cls:e.className,r:[r.x,r.y,r.width,r.height],fs:s.fontSize,color:s.color,op:s.opacity,vis:s.visibility}});
  });
  console.log(JSON.stringify(info,null,1));
});
