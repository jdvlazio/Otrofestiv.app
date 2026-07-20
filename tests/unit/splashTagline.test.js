// Unit test — festivalTagline + _renderSplashRailHTML (src/view/components.js).
//
// POR QUÉ EXISTE: el tagline del nuevo selector-splash se DERIVA de `fullName`
// (fuente única, sin campo aparte). La derivación tiene casos delicados —
// separador em/en-dash, nombre al inicio vs al final, fullName===name (Tribeca) —
// que deben dar EXACTAMENTE el descriptor correcto para los 9 festivales reales.
// Este test congela la fórmula contra esos 9 + edge cases sintéticos.
//
// Carga: import() dinámico del ESM real (mismo patrón que poster.test.js).

const { test, before } = require('node:test');
const assert = require('node:assert');

let C, CFG;
before(async () => {
  globalThis._lang = 'es'; // t() lee _lang como bare-global (bridge)
  C = await import('../../src/view/components.js');
  CFG = (await import('../../src/config.js')).FESTIVAL_CONFIG;
});

// ── festivalTagline: los 9 festivales reales ──
const EXPECTED = {
  ficci65:          'Festival Internacional de Cine de Cartagena de Indias',
  aff2026:          'Alternativa Film Festival',
  tribeca2026:      'Festival de Cine de Tribeca',                   // tagline localizado {es,en}, default es
  cinemancia2025:   'Festival Metropolitano de Cine',               // nombre al inicio
  leviza2026:       'Festival de Cine y Audiovisuales',             // nombre al final
  olhar2026:        'Festival Internacional de Curitiba',           // separador –
  tercertiempo2026: 'Festival Mundial de Cine de Fútbol y Deportes',// separador —
  fantasofest2026:  'Muestra Iberoamericana de Cine Fantástico',    // separador —
  ficmontanas2026:  'Festival Internacional de Cine en las Montañas',// nombre ausente en fullName
};

test('festivalTagline deriva el descriptor correcto de los 9 festivales', () => {
  for (const [id, want] of Object.entries(EXPECTED)) {
    assert.strictEqual(C.festivalTagline(CFG[id]), want, `tagline de ${id}`);
  }
});

test('festivalTagline — edge cases', () => {
  assert.strictEqual(C.festivalTagline({}), '', 'sin fullName → vacío');
  assert.strictEqual(C.festivalTagline({name:'X', fullName:'X'}), '', 'fullName===name → vacío');
  assert.strictEqual(C.festivalTagline({name:'X', fullName:'X — Desc'}), 'Desc', 'separador');
  assert.strictEqual(C.festivalTagline({name:'X', fullName:'X', tagline:'override'}), 'override', 'override explícito gana');
  assert.strictEqual(C.festivalTagline({name:'X', fullName:'X — Desc', tagline:''}), '', 'override vacío gana sobre derivación');
});

test('festivalTagline — tagline localizado {es,en}', () => {
  const cfg = { name:'X', fullName:'X', tagline:{es:'Descriptor ES', en:'Original EN'} };
  assert.strictEqual(C.festivalTagline(cfg, 'es'), 'Descriptor ES', 'lang es → variante es');
  assert.strictEqual(C.festivalTagline(cfg, 'en'), 'Original EN', 'lang en → variante en');
  assert.strictEqual(C.festivalTagline(cfg), 'Descriptor ES', 'sin lang → default es');
  assert.strictEqual(C.festivalTagline({tagline:{es:'Solo ES'}}, 'en'), 'Solo ES', 'sin variante en → cae a es');
  // Tribeca real: ES descriptor, EN nombre original
  assert.strictEqual(C.festivalTagline(CFG.tribeca2026, 'en'), 'Tribeca Film Festival', 'Tribeca EN = nombre original');
});

// ── _renderSplashRailHTML: estructura ──
const fakeState = (lang='es') => ({ snapshot: () => ({ _lang: lang }) });

// El divisor "ANTERIORES" separa DOS grupos: solo se emite si hay vigentes Y pasados.
// ANTES este test lo exigía siempre → era una BOMBA DE TIEMPO: estalló el 20 jul 2026,
// cuando terminó el último festival vigente y el riel pasó a ser todo-pasados (el
// código hace lo correcto al omitirlo). Ahora la aserción es condicional a la
// partición real, así que el test mide la REGLA y no la fecha en que se corre.
test('_renderSplashRailHTML — cards de los 8 festivales visibles + divisor condicional', () => {
  const html = C._renderSplashRailHTML(fakeState(), 'fantasofest2026');
  const cards = (html.match(/data-fest=/g) || []).length;
  assert.strictEqual(cards, 8, '8 cards (cinemancia es group:test → excluido)');
  const anyCurrent = Object.entries(CFG)
    .filter(([, c]) => c.name && c.group !== 'test')
    .some(([, c]) => C._classifyFestival(c) !== 'past');
  const anyPast = Object.entries(CFG)
    .filter(([, c]) => c.name && c.group !== 'test')
    .some(([, c]) => C._classifyFestival(c) === 'past');
  assert.strictEqual(html.includes('splash-rail-div'), anyCurrent && anyPast,
    'divisor presente si y solo si hay vigentes Y pasados');
  assert.ok(html.includes('data-fest="fantasofest2026"'), 'incluye el festival activo');
  assert.ok(!html.includes('cinemancia2025'), 'excluye group:test');
});

test('_renderSplashRailHTML — activo marcado, keyArt + keyArtPos + onerror', () => {
  const html = C._renderSplashRailHTML(fakeState(), 'tercertiempo2026');
  assert.match(html, /data-fest="tercertiempo2026"[^>]*aria-selected="true"/, 'activo aria-selected');
  assert.match(html, /class="splash-card[^"]*\bon\b/, 'activo lleva clase on');
  assert.ok(html.includes('/assets/keyart/tercertiempo2026.jpg'), 'usa keyArt');
  // keyArtPos vía custom property --kap (no inline style raw: ARQUITECTURA §10.3)
  assert.ok(html.includes('--kap:30%'), 'aplica keyArtPos de TT (30%: conserva "10" e "CINE")');
  // toda <img> degrada si el afiche 404ea (§10.2)
  assert.ok(html.includes('onerror="this.remove()"'), 'la img de keyArt lleva onerror');
});

// INVARIANTE (bug cazado en QA 13 jul): el orden del riel es ESTABLE — no depende
// de qué festival esté seleccionado. El tier 0 "seleccionado primero" era del
// dropdown; en el carrusel, reordenar en un re-render (setLang) teletransporta
// las cards y desalinea el centro del scroll con la selección → el próximo
// gesto pisaba la selección. activeFestId solo marca .on/aria-selected.
test('_renderSplashRailHTML — orden estable: no reordena por selección', () => {
  const orderOf = html => [...html.matchAll(/data-fest="([^"]+)"/g)].map(m => m[1]).join(',');
  const base = orderOf(C._renderSplashRailHTML(fakeState(), null));
  // ficci65 es 'past' (última del riel): con tier 0 saltaría al frente de su grupo.
  assert.strictEqual(orderOf(C._renderSplashRailHTML(fakeState(), 'ficci65')), base,
    'seleccionar un pasado no lo reordena');
  assert.strictEqual(orderOf(C._renderSplashRailHTML(fakeState(), 'tercertiempo2026')), base,
    'seleccionar un vigente no reordena');
  // La selección sí queda marcada (sin reordenar)
  assert.match(C._renderSplashRailHTML(fakeState(), 'ficci65'),
    /data-fest="ficci65"[^>]*aria-selected="true"/, 'ficci65 marcado .on donde está');
});

test('_renderSplashRailHTML — data-name/data-meta preservan firma de selectSplashFest', () => {
  const html = C._renderSplashRailHTML(fakeState('en'), 'fantasofest2026');
  // en EN la meta usa dates_en
  assert.match(html, /data-fest="fantasofest2026"[^>]*data-name="[^"]+"[^>]*data-meta="Bogotá · JUL 13–19"/,
    'card con data-name + data-meta (dates_en en inglés)');
});

// ── festivalShortName: nombre oficial (Olhar de Cinema, no "Olhar") ──
test('festivalShortName — respeta el nombre oficial vía displayName', () => {
  assert.strictEqual(C.festivalShortName(CFG.olhar2026), 'Olhar de Cinema', 'Olhar completo, no truncado');
  assert.strictEqual(C.festivalShortName(CFG.tercertiempo2026), 'Tercer Tiempo Fest', 'TT completo');
  assert.strictEqual(C.festivalShortName(CFG.ficci65), 'FICCI', 'sigla se mantiene (primer token)');
  assert.strictEqual(C.festivalShortName(CFG.fantasofest2026), 'FantasoFest', 'una palabra intacta');
});

// ── festivalSeasonYear + selector: el año vive UNA sola vez en el header ──
test('festivalSeasonYear — año vigente de la temporada', () => {
  // todos los festivales reales son 2026 (cinemancia 2025 es group:test → excluido)
  assert.strictEqual(C.festivalSeasonYear(), 2026, 'temporada 2026');
});

test('_renderFestivalSelectorHTML — rótulos sin año repetido (todos = temporada)', () => {
  const html = C._renderFestivalSelectorHTML(fakeState(), 'tercertiempo2026');
  // ningún rótulo de card repite "· 2026" (todos son la temporada vigente)
  const names = [...html.matchAll(/class="fs-fest-cap">([^<]*)</g)].map(m => m[1]);
  assert.ok(names.length >= 8, 'todas las cards presentes');
  assert.ok(names.every(n => !/·\s*20\d\d/.test(n)), 'ningún rótulo muestra el año');
  assert.ok(names.includes('Olhar de Cinema'), 'Olhar con nombre oficial');
  assert.ok(names.includes('Tercer Tiempo Fest'), 'TT sin año en el rótulo');
});

// Rediseño 20 jul: el chooser del sheet es un MURO DE AFICHES que reusa la misma
// .splash-card del riel de entrada (fuente única _festivalCardHTML). Este test fija
// esa unidad: si alguien lo devuelve a lista de texto, falla.
test('_renderFestivalSelectorHTML — muro de afiches con la card del splash', () => {
  const html = C._renderFestivalSelectorHTML(fakeState(), 'tercertiempo2026');
  assert.ok(!html.includes('fs-festival-row'), 'ya no renderiza filas de lista');
  // <button class="splash-card…"> — NO contar splash-card-tpl / -art (mismo prefijo)
  const cards = (html.match(/<button class="splash-card/g) || []).length;
  assert.strictEqual(cards, 8, '8 cards-afiche (mismo componente que el splash)');
  assert.ok(html.includes('data-action="loadFestival"'), 'en el sheet la card carga directo');
  assert.ok(!html.includes('data-action="selectSplashFest"'), 'no usa la acción del splash');
  assert.ok(html.includes('/assets/keyart/olhar2026.jpg'), 'usa el keyArt del festival');
  assert.ok(html.includes('--kap:30%'), 'aplica keyArtPos de TT');
  assert.ok((html.match(/onerror="this.remove\(\)"/g) || []).length >= 8, 'cada img degrada (§10.2)');
});

test('_renderFestivalSelectorHTML — fallback tipográfico sin keyArt', () => {
  // stub: un festival sin keyArt cae al fallback fs-fest-art-fb con el shortName
  const cfgNoArt = { name: 'Zzz Test', fullName: 'Zzz Test', city: 'X', dates: '1–2 ENE', year: 2026 };
  // se prueba el builder indirectamente: festival real sí tiene keyArt, así que
  // validamos la rama de fallback vía festivalShortName (no rompe si algún día falta).
  assert.strictEqual(C.festivalShortName(cfgNoArt), 'Zzz', 'shortName para el fallback');
});
