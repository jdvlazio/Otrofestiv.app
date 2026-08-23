const {run}=require('./h');const {enter}=require('./f');
run(async(p,S)=>{
  await enter(p);
  await p.mouse.click(48,806); await p.waitForTimeout(1500); await p.click("#pmode-manana",{force:true}); await p.waitForTimeout(1500);
  await p.mouse.click(150,256); await p.waitForTimeout(2000);
  await p.screenshot({path:S+'42-zoom.png',clip:{x:0,y:265,width:390,height:110}});
});
