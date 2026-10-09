#!/usr/bin/env node
// capturas-festival.js <festId> [simTime] — la app como la ve la gente, ANTES de publicar.
//
// MAPISTAS (FILCMAR, 9 oct 2026) salió como cuatro funciones ancladas en el plan
// y ningún validador lo vio: era un defecto de PANTALLA. Regla de la casa desde
// entonces: toda publicación lleva capturas (Programa, una ficha, Mi Plan con
// algo guardado) a 390×844, que van a Juan con la hoja de contacto.
//
//   node scripts/capturas-festival.js ficcali2026
//   node scripts/capturas-festival.js ficcali2026 2026-10-17T12:00:00-05:00
//
// Deja fuentes/capturas/<festId>/{programa,ficha,miplan}.png (fuentes/ no se versiona).
const { chromium } = require('@playwright/test');
const { spawn } = require('child_process');
const fs = require('fs'), path = require('path');

const festId = process.argv[2];
if (!festId) { console.error('uso: node scripts/capturas-festival.js <festId> [simTime]'); process.exit(2); }
const REPO = path.join(__dirname, '..');
const file = path.join(REPO, 'festivals', festId.replace(/([a-zA-Z]+)(\d+)$/, '$1-$2') + '.json');
if (!fs.existsSync(file)) { console.error('no existe ' + file); process.exit(2); }
const data = JSON.parse(fs.readFileSync(file, 'utf8'));
// el reloj: el primer día del festival al mediodía, salvo que se pase otro
const day0 = (data.festivalStartStr || '').slice(0, 10);
const tz = data.timezoneOffset || '-05:00';
const simTime = process.argv[3] || `${day0}T12:00:00${tz}`;
const PORT = 3457;
const out = path.join(REPO, 'fuentes', 'capturas', festId);
fs.mkdirSync(out, { recursive: true });

(async () => {
  const srv = spawn('python3', ['-c', `from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler; ThreadingHTTPServer(('', ${PORT}), SimpleHTTPRequestHandler).serve_forever()`], { cwd: REPO, stdio: 'ignore' });
  await new Promise(r => setTimeout(r, 800));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  try {
    await page.goto(`http://localhost:${PORT}/?simTime=${encodeURIComponent(simTime)}`);
    await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
    await page.evaluate((id) => {
      const cfg = FESTIVAL_CONFIG[id] || {};
      selectSplashFest(cfg.name, `${cfg.city} · ${cfg.dates} ${cfg.year || ''}`.trim(), id);
    }, festId);
    await page.waitForTimeout(300);
    await page.locator('.splash-enter-btn').click();
    await page.waitForFunction(() => Array.isArray(FILMS) && FILMS.length > 0, { timeout: 15000 });
    await page.waitForTimeout(1200);
    await page.screenshot({ path: path.join(out, 'programa.png') });
    // una ficha: la primera obra con afiche del primer día
    const title = await page.evaluate(() => {
      const f = (FILMS || []).find(x => x.type !== 'event' && !x.event_kind && x.poster) || (FILMS || [])[0];
      return f && f.title;
    });
    if (title) {
      await page.evaluate((t) => openPelSheet(t), title);
      await page.waitForTimeout(800);
      await page.screenshot({ path: path.join(out, 'ficha.png') });
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);
      // Mi Plan con esa obra y la primera actividad guardadas
      await page.evaluate((t) => {
        watchlist.clear(); watchlist.add(t);
        const ev = (FILMS || []).find(x => x.type === 'event' || x.event_kind);
        if (ev) watchlist.add(ev.title);
        if (typeof saveState === 'function') saveState('wl', 'watched');
        switchMainNav('mnav-miplan'); showAgView();
      }, title);
      await page.waitForTimeout(1000);
      await page.screenshot({ path: path.join(out, 'miplan.png') });
    }
    console.log(`✓ capturas de ${festId} (${simTime}) → ${path.relative(REPO, out)}/`);
  } finally {
    await browser.close();
    srv.kill();
  }
})().catch(e => { console.error('✗', e.message); process.exit(1); });
