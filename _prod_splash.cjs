const { chromium, devices } = require('@playwright/test');
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ ...devices['iPhone 14'],
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148' });
  const page = await ctx.newPage();
  const errs = [];
  page.on('console', m => { if (m.type() === 'error') errs.push(m.text().slice(0, 300)); });
  page.on('pageerror', e => errs.push('PAGEERROR: ' + String(e).slice(0, 300)));
  await page.goto('https://otrofestiv.app/?nc=' + Date.now(), { waitUntil: 'networkidle', timeout: 45000 });
  await page.waitForTimeout(3500);
  const st1 = await page.evaluate(() => ({
    rail: !!document.querySelector('#splash-rail'),
    cards: document.querySelectorAll('.splash-card').length,
    on: document.querySelectorAll('.splash-card.on').length,
    btn: (() => { const b = [...document.querySelectorAll('button')].find(x => /Entrar|Enter/i.test(x.textContent)); 
      return b && { txt: b.textContent.trim(), disabled: b.disabled, visible: b.offsetHeight > 0 }; })(),
  }));
  console.log('SPLASH:', JSON.stringify(st1));
  // tocar la card de FICDEH y luego Entrar
  await page.evaluate(() => { [...document.querySelectorAll('.splash-card')].find(c => c.dataset.fest === 'ficdeh2026')?.click(); });
  await page.waitForTimeout(800);
  const st2 = await page.evaluate(() => {
    const b = [...document.querySelectorAll('button')].find(x => /Entrar|Enter/i.test(x.textContent));
    return { on: document.querySelectorAll('.splash-card.on').length, disabled: b?.disabled };
  });
  console.log('TRAS TAP CARD:', JSON.stringify(st2));
  await page.evaluate(() => { [...document.querySelectorAll('button')].find(x => /Entrar|Enter/i.test(x.textContent))?.click(); });
  await page.waitForTimeout(3000);
  const st3 = await page.evaluate(() => ({
    splashVisible: (() => { const s = document.querySelector('#splash,.splash'); return s && getComputedStyle(s).display !== 'none' && s.offsetHeight > 0; })(),
    tabs: document.querySelectorAll('[id^=mnav-]').length,
    programa: !!document.querySelector('#cartelera-view, .plist-item, .dtab'),
  }));
  console.log('TRAS ENTRAR:', JSON.stringify(st3));
  console.log('ERRORES:', JSON.stringify(errs.slice(0, 6), null, 1));
  await page.screenshot({ path: '/tmp/prod-splash.png' });
  await browser.close();
})();
