// Unit test — generadores de pósters editoriales (src/view/components.js).
//
// POR QUÉ EXISTE: los pósters editoriales (sin imagen, SVG generativo) eran el
// "dolor de cabeza" recurrente al montar festivales. Falla de clase: una string
// de usuario con `&`, `<`, `>` o `"` se interpolaba CRUDA dentro de un <text> SVG
// → XML malformado → el navegador lo descarta (naturalWidth 0) → póster roto y
// silencioso. Regresión real: "Opening & Galas" / "Recorrido en Bicicleta".
//
// GUARDARRAÍL: escXML() es la fuente única de escape (components.js). Todo texto
// de usuario que entra a un <text> debe pasar por ella. Estos tests fuerzan
// entradas adversarias por cada generador y exigen XML bien formado.
//
// Carga: import() dinámico del módulo ESM real (sin harness load-domain — estos
// no son fns de dominio puras de index.html, viven en src/view como ESM).

const { test, before } = require('node:test');
const assert = require('node:assert');

let C; // módulo components.js
let H; // módulo helpers.js (posterModel + editorialFrame)
before(async () => {
  // i18n t() lee `_lang` como bare-global (puente de estado; en el browser lo
  // setea main.js). makeSorpresaPoster usa t() → en node hay que proveerlo.
  globalThis._lang = 'es';
  C = await import('../../src/view/components.js');
  H = await import('../../src/view/helpers.js');
});

// state falso: los generadores solo leen snapshot() → {FILMS,_lang,_activeFestId}
const fakeState = { snapshot: () => ({ FILMS: [], _lang: 'es', _activeFestId: 'x' }) };

// Entradas que rompían el XML antes del fix.
const ADVERSARIAL = [
  'Opening & Galas',          // ampersand suelto (la regresión original)
  'A & B & C',                // múltiples ampersands
  'Tom & Jerry "quoted"',     // ampersand + comillas
  '<script>alert(1)</script>',// < y >
  'Café & Té ☕ — Quindío',    // ampersand + emoji + acentos + em dash
  '',                         // vacío
];

// Un `&` que NO sea parte de una entidad válida rompe el parser XML
// independientemente de dónde aparezca → invariante fuerte de buena formación.
const BAD_AMP = /&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)/;

function decodeSVG(dataUri, label) {
  assert.match(dataUri, /^data:image\/svg\+xml,/, `${label}: debe ser data-URI SVG`);
  const payload = dataUri.slice('data:image/svg+xml,'.length);
  const svg = decodeURIComponent(payload); // lanza si el URI quedó malformado
  assert.ok(svg.includes('<svg'), `${label}: el SVG decodificado debe contener <svg`);
  return svg;
}

function assertWellFormed(dataUri, label) {
  const svg = decodeSVG(dataUri, label);
  const m = svg.match(BAD_AMP);
  assert.ok(
    !m,
    `${label}: ampersand sin escapar → XML malformado (naturalWidth 0). ` +
    `Cerca de: «${m ? svg.slice(Math.max(0, m.index - 24), m.index + 24) : ''}»`
  );
  return svg;
}

// ── escXML: la fuente única de escape ────────────────────────────────────────
test('escXML escapa los 4 metacaracteres XML', () => {
  assert.strictEqual(C.escXML('a & b'), 'a &amp; b');
  assert.strictEqual(C.escXML('1 < 2 > 0'), '1 &lt; 2 &gt; 0');
  assert.strictEqual(C.escXML('say "hi"'), 'say &quot;hi&quot;');
});

test('escXML escapa & primero (no doble-escapa el resto)', () => {
  // Si & no fuera primero, '<' → '&lt;' y luego el & de '&lt;' se re-escaparía.
  assert.strictEqual(C.escXML('<&>'), '&lt;&amp;&gt;');
});

test('escXML tolera no-strings y deja pasar lo seguro', () => {
  assert.strictEqual(C.escXML(5), '5');
  assert.strictEqual(C.escXML(null), 'null');
  assert.strictEqual(C.escXML('Quindío ☕ 2026'), 'Quindío ☕ 2026'); // emoji/acentos intactos
});

// ── Generadores × entradas adversarias → XML bien formado ────────────────────
test('makeProgramPoster: XML bien formado con entradas adversarias', () => {
  for (const title of ADVERSARIAL) {
    assertWellFormed(C.makeProgramPoster(fakeState, title, 90, 'Cine Cubano'), `program «${title}»`);
  }
});

test('makeEventPoster: XML bien formado (kind y fallback)', () => {
  for (const title of ADVERSARIAL) {
    assertWellFormed(C.makeEventPoster(fakeState, title, 60, 'masterclass', null), `event/kind «${title}»`);
    assertWellFormed(C.makeEventPoster(fakeState, title, 60, null, 'Conversatorios'), `event/fallback «${title}»`);
  }
});

test('makeSorpresaPoster: XML bien formado', () => {
  assertWellFormed(C.makeSorpresaPoster(), 'sorpresa');
});

test('_buildPosterV16: escapa headerLabel, title y num (ambas variantes)', () => {
  for (const s of ADVERSARIAL) {
    // Variante B (num null) — header y título adversarios
    assertWellFormed(C._buildPosterV16({ accent: '#F59E0B', headerLabel: s, title: s, num: null }), `v16/B «${s}»`);
    // Variante A (num presente)
    assertWellFormed(C._buildPosterV16({ accent: '#E05252', headerLabel: s, title: s, num: 'A & 1' }), `v16/A «${s}»`);
  }
});

// ── Regresión específica: "Opening & Galas" ──────────────────────────────────
test('regresión: el ampersand de "Opening & Galas" queda como &amp;', () => {
  const svg = assertWellFormed(
    C._buildPosterV16({ accent: '#F59E0B', headerLabel: 'Opening & Galas', title: 'Opening & Galas', num: null }),
    'opening-galas'
  );
  assert.ok(svg.includes('Opening &amp; Galas'), 'el & debe renderizarse escapado como &amp;');
  assert.ok(!/Opening & Galas/.test(svg), 'no debe quedar ningún "& " crudo en el SVG');
});

// ── posterModel: unión discriminada (un solo lugar clasifica el póster) ───────
test('posterModel discrimina kind: image / editorial / generative / empty', () => {
  assert.strictEqual(H.posterModel(null).kind, 'empty');
  assert.strictEqual(H.posterModel({ type: 'event', title: 'Gala', section: 'Apertura' }).kind, 'generative');
  assert.strictEqual(H.posterModel({ title: 'Peli', section: 'X', poster: '/assets/x.png' }).kind, 'image');
  // host editorial conocido (cloudfront) → editorial-con-imagen
  const ed = H.posterModel({ title: 'Still', section: 'Cine Cubano', poster: 'https://d1.cloudfront.net/s.jpg' });
  assert.strictEqual(ed.kind, 'editorial');
  assert.ok(ed.accent && ed.src && 'header' in ed, 'editorial trae accent/src/header para el builder');
});

test('posterModel fail-safe: host desconocido NO se marca editorial (no se mete 16:9 en 2:3)', () => {
  // Sin posterSource ni host conocido → image (default seguro), nunca editorial.
  const m = H.posterModel({ title: 'Z', section: 'X', poster: 'https://otro-cdn.example/p.jpg' });
  assert.strictEqual(m.kind, 'image');
});

// ── editorialFrame: builder único del marco editorial-con-imagen ─────────────
// Devuelve los HIJOS del marco; el contenedor aporta poster-ed + --ed-accent.
test('editorialFrame: emite las 3 zonas cuando hay header/img/body', () => {
  const html = H.editorialFrame({ header: 'Cine Cubano', body: 'La Peli', src: 'https://x/y.jpg', title: 'La Peli' });
  assert.ok(html.includes('class="ed-hdr"') && html.includes('class="ed-img"') && html.includes('class="ed-body"'), 'incluye las 3 zonas');
  assert.ok(html.includes('_edPosterErr(this)'), 'usa el onerror unificado editorial');
  assert.ok(!html.includes('poster-ed'), 'NO incluye el wrapper — eso lo pone el contenedor');
});

test('editorialFrame: omite header/body/img vacíos (thumb = banda + img sin label)', () => {
  const thumb = H.editorialFrame({ src: 'https://x/y.jpg', title: 'T' }); // sin header ni body
  assert.ok(thumb.includes('<div class="ed-hdr"></div>'), 'header vacío = banda sin texto');
  assert.ok(!thumb.includes('ed-body'), 'sin body cuando no se pasa');
  const noImg = H.editorialFrame({ header: 'Sec' }); // sin src
  assert.ok(noImg.includes('<div class="ed-img"></div>'), 'ed-img vacío cuando no hay src');
});

test('editorialFrame: body undefined=omite · ""=reserva vacío · texto=título', () => {
  assert.ok(!H.editorialFrame({ src: 'x' }).includes('ed-body'), 'undefined → sin zona body');
  const reserved = H.editorialFrame({ src: 'x', body: '' }); // ended-poster
  assert.ok(reserved.includes('<div class="ed-body"></div>'), '"" → zona vacía que reserva espacio');
  assert.ok(H.editorialFrame({ src: 'x', body: 'Peli' }).includes('<div class="ed-title">Peli</div>'), 'texto → título');
});

test('editorialFrame: escapa body, header y data-title (sin & crudo)', () => {
  const html = H.editorialFrame({ header: 'Tom & Jerry', body: 'A < B & "C"', src: 'https://x/y.jpg', title: 'A & B' });
  assert.ok(!BAD_AMP.test(html), 'ningún & sin escapar en el marco');
  assert.ok(html.includes('data-title="A &amp; B"'), 'data-title escapado');
  assert.ok(html.includes('A &lt; B &amp; &quot;C&quot;'), 'el body escapa <, & y "');
});
