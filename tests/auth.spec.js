// @ts-check
// auth.spec.js — Auth sheet: abrir, cerrar, email, delete account UI.
// No testea autenticación real (requiere Supabase) — testea UI y flujos.
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival } = require('./helpers');

// A01 — Botón de cuenta abre auth sheet
test('A01 — botón cuenta abre auth sheet', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.locator('#auth-btn').click();
  await page.waitForSelector('#auth-sheet.open', { timeout: 5000 });
  expect(await page.locator('#auth-sheet.open').count()).toBe(1);
});

// A02 — Auth sheet se cierra al hacer click en overlay
test('A02 — auth sheet se cierra al cerrar', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => openAuthSheet());
  await page.waitForSelector('#auth-sheet.open', { timeout: 5000 });
  await page.evaluate(() => closeAuthSheet());
  await expect(page.locator('#auth-sheet.open')).toHaveCount(0, { timeout: 5000 });
});

// A03 — Auth sheet tiene campo de email
test('A03 — auth sheet tiene campo de email', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => openAuthSheet());
  await page.waitForSelector('#auth-sheet.open', { timeout: 5000 });
  const emailInput = page.locator('#auth-sheet input[type="email"], #auth-sheet input[type="text"]');
  await expect(emailInput).toBeVisible({ timeout: 5000 });
});

// A04 — Auth sheet muestra botón eliminar cuando usuario está autenticado
// Simula estado signed-in via JS (no requiere sesión real de Supabase)
test('A04 — auth sheet tiene botón eliminar cuenta', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  // Simular estado autenticado: mostrar step3 directamente
  await page.evaluate(() => {
    document.getElementById('auth-sheet-step1').style.display = 'none';
    document.getElementById('auth-sheet-step2').style.display = 'none';
    document.getElementById('auth-sheet-step3').style.display = 'block';
    const s = document.getElementById('auth-sheet');
    s.style.display = 'flex';
    setTimeout(() => s.classList.add('open'), 10);
  });
  await page.waitForSelector('#auth-sheet.open', { timeout: 5000 });
  await expect(page.locator('#auth-delete-btn')).toBeVisible({ timeout: 5000 });
});

// A05 — Primer tap en eliminar cambia el texto a confirmación
// Simula estado signed-in via JS — no requiere sesión real de Supabase
test('A05 — primer tap eliminar cuenta pide confirmación', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => {
    document.getElementById('auth-sheet-step1').style.display = 'none';
    document.getElementById('auth-sheet-step2').style.display = 'none';
    document.getElementById('auth-sheet-step3').style.display = 'block';
    const s = document.getElementById('auth-sheet');
    s.style.display = 'flex';
    setTimeout(() => s.classList.add('open'), 10);
    // Simular _sbUser para que deleteAccount() pase el guard
    _sbUser = { email: 'test@test.com', id: 'test-id' };
  });
  await page.waitForSelector('#auth-sheet.open', { timeout: 5000 });
  const btn = page.locator('#auth-delete-btn');
  await expect(btn).toBeVisible({ timeout: 5000 });
  const textAntes = await btn.textContent();
  await btn.click();
  await page.waitForTimeout(300);
  const textDespues = await btn.textContent();
  expect(textDespues).not.toEqual(textAntes);
});

// A06 — Auth sheet no tiene errores JS al abrir
test('A06 — auth sheet abre sin errores JS', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.evaluate(() => openAuthSheet());
  await page.waitForSelector('#auth-sheet.open', { timeout: 5000 });
  await page.waitForTimeout(200);
  expect(errors).toHaveLength(0);
});

// A07 — Auth sheet en Tribeca también abre correctamente
test('A07 — auth sheet funciona en Tribeca', async ({ page }) => {
  await enterFestival(page, 'tribeca2026');
  await page.evaluate(() => openAuthSheet());
  await page.waitForSelector('#auth-sheet.open', { timeout: 5000 });
  expect(await page.locator('#auth-delete-btn').count()).toBeGreaterThan(0);
});
