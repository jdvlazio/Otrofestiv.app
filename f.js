module.exports.enter=async(p)=>{
  if(await p.$('#splash-enter-btn')){
    const dis=await p.$eval('#splash-enter-btn',e=>e.disabled).catch(()=>false);
    if(dis){await p.mouse.click(195,300);await p.waitForTimeout(500);}
    await p.click('#splash-enter-btn'); await p.waitForTimeout(2500);
  }
  if(await p.$('#city-sheet.open')){ await p.click('[data-action="citySheetPick"][data-city="Bogotá"]'); await p.waitForTimeout(1800);}
};
