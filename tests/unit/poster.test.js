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
// La banda va en MAYÚSCULA (unificación Fase B: una sola caja tipográfica); el
// & sigue escapado. El header queda "OPENING &amp; GALAS" en una línea.
test('regresión: el ampersand de "Opening & Galas" queda como &amp;', () => {
  const svg = assertWellFormed(
    C._buildPosterV16({ accent: '#F59E0B', headerLabel: 'Opening & Galas', title: 'Opening & Galas', num: null }),
    'opening-galas'
  );
  assert.ok(svg.includes('OPENING &amp; GALAS'), 'el & de la banda debe renderizarse escapado como &amp;');
  assert.ok(!/OPENING & GALAS/.test(svg), 'no debe quedar ningún "& " crudo en la banda');
});

// ── Clamp de título largo (Netflix/Spotify): ≤4 líneas + elipsis en generativo ─
// Líneas del body = <text> con y>52 (fuera de la banda HDR). Antes un título de
// 80 chars daba 9 líneas minúsculas que llenaban el póster.
function bodyLines(dataUri) {
  const svg = decodeURIComponent(dataUri.replace('data:image/svg+xml,', ''));
  return [...svg.matchAll(/<text[^>]*y="([\d.]+)"[^>]*>([^<]*)<\/text>/g)]
    .filter(m => +m[1] > 52).map(m => m[2]);
}
test('_buildPosterV16: título largo se clampa a ≤4 líneas + "…"', () => {
  const long = 'Tribeca at 25: A Conversation With Co-Founders Jane Rosenthal and Robert De Niro';
  const lines = bodyLines(C._buildPosterV16({ accent: '#EF9F27', headerLabel: 'Gala', title: long, num: null }));
  assert.ok(lines.length <= 4, `body ≤4 líneas (fue ${lines.length})`);
  assert.ok(lines[lines.length - 1].endsWith('…'), 'la última línea truncada termina en "…"');
});
test('_buildPosterV16: título corto NO se toca (sin elipsis)', () => {
  const lines = bodyLines(C._buildPosterV16({ accent: '#EF9F27', headerLabel: 'Gala', title: 'Noga', num: null }));
  assert.deepStrictEqual(lines, ['Noga'], 'título corto = una línea, sin truncar');
});

// ── El CUERPO usa el mismo cortador que la banda (regla de Juan, unificada) ───
// "Recorrido en Bicicleta · Comparsa Cultural" era la regresión: cortaba
// "Recorrido en / Bicicleta" (línea terminando en preposición).
test('_buildPosterV16: el cuerpo respeta la regla de corte (sin débil al final)', () => {
  const cases = [
    ['Recorrido en Bicicleta · Comparsa Cultural', ['Recorrido', 'en Bicicleta', '· Comparsa', 'Cultural']],
    ['Programa de cortos 4', ['Programa', 'de cortos 4']],
    ['¿Qué es la ficción?', ['¿Qué es', 'la ficción?']],
  ];
  for (const [title, expected] of cases) {
    const lines = bodyLines(C._buildPosterV16({ accent: '#378ADD', headerLabel: 'Sec', title, num: null }));
    assert.deepStrictEqual(lines, expected, `corte del cuerpo de "${title}"`);
  }
});

// ── Regla de lecturabilidad del corte de línea de la banda (regla de Juan) ────
// Cada línea con sentido propio; NINGUNA línea (salvo la última) termina en
// palabra débil (conjunción/preposición/artículo) ni en guión suelto.
const _WEAK_END = /\b(?:de|del|la|el|los|las|un|una|y|e|o|u|con|para|por|en|the|of|and|or|to|in|for)$|[–—-]$/i;
test('banda: el corte respeta los ejemplos canónicos de Juan', () => {
  const cases = [
    ['Competencia De Cortometrajes', ['COMPETENCIA', 'DE CORTOMETRAJES']],
    ['¿Qué es la ficción?',          ['¿QUÉ ES', 'LA FICCIÓN?']],
    ['Competencia Nacional de Ficción', ['COMPETENCIA', 'NACIONAL', 'DE FICCIÓN']],
  ];
  for (const [input, expected] of cases) {
    assert.deepStrictEqual(C._bandWrap(input.toUpperCase()), expected, `corte de "${input}"`);
  }
});
test('banda: ninguna línea (salvo la última) termina en palabra débil', () => {
  const labels = [
    'Competencia De Cortometrajes', 'Tributo Ben Rivers', '¿Qué es la ficción?',
    'Competencia Nacional de Ficción', 'International Narrative Competition',
    'Retrospectiva Clásicos – Ópera Prima', 'Según la palabra. El cine de Olivier Godin',
    'Apertura & Galas', 'Awards Screenings', 'Perspectivas',
  ];
  for (const label of labels) {
    const lines = C._bandWrap(label.toUpperCase());
    for (let i = 0; i < lines.length - 1; i++) {
      assert.ok(!_WEAK_END.test(lines[i]), `"${label}" línea ${i + 1} ("${lines[i]}") no debe terminar en palabra débil`);
    }
  }
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

// ── editorialFrame: builder único del marco editorial-con-imagen (anatomía A3) ─
// Devuelve los HIJOS del marco; el contenedor aporta poster-ed + --ed-accent.
// Zona imagen = blur-fill (.ed-blur) + still 16:9 al ras (.ed-still) + scrim
// opcional (.ed-scrim con .ed-title). El título va en el scrim, no en un ed-body.
test('editorialFrame: emite banda + imagen (blur+still) + scrim con título', () => {
  const html = H.editorialFrame({ header: 'Cine Cubano', body: 'La Peli', src: 'https://x/y.jpg', title: 'La Peli' });
  assert.ok(html.includes('class="ed-hdr"') && html.includes('class="ed-img"'), 'incluye banda + imagen');
  assert.ok(html.includes('class="ed-blur"') && html.includes('class="ed-still"'), 'imagen = blur-fill + still 16:9');
  assert.ok(html.includes('class="ed-scrim"') && html.includes('class="ed-title"'), 'título va en el scrim');
  assert.ok(!html.includes('ed-body'), 'ya no hay zona ed-body (fusionada en el scrim)');
  assert.ok(html.includes('_edPosterErr(this)'), 'usa el onerror unificado editorial (en el still)');
  assert.ok(!html.includes('poster-ed'), 'NO incluye el wrapper — eso lo pone el contenedor');
});

test('editorialFrame: omite header/scrim/img vacíos (thumb = banda + img sin título)', () => {
  const thumb = H.editorialFrame({ src: 'https://x/y.jpg', title: 'T' }); // sin header ni body
  assert.ok(thumb.includes('<div class="ed-hdr"></div>'), 'header vacío = banda sin texto');
  assert.ok(thumb.includes('class="ed-still"') && !thumb.includes('ed-scrim'), 'still sí, scrim no (sin body)');
  const noImg = H.editorialFrame({ header: 'Sec' }); // sin src
  assert.ok(noImg.includes('<div class="ed-img"></div>'), 'ed-img vacío cuando no hay src');
});

test('editorialFrame: body undefined/"" → sin scrim · texto → título en scrim', () => {
  assert.ok(!H.editorialFrame({ src: 'x' }).includes('ed-scrim'), 'undefined → sin scrim');
  assert.ok(!H.editorialFrame({ src: 'x', body: '' }).includes('ed-scrim'), '"" (ended-poster) → sin scrim');
  const titled = H.editorialFrame({ src: 'x', body: 'Peli' });
  assert.ok(titled.includes('<div class="ed-scrim"><div class="ed-title">Peli</div></div>'), 'texto → título en scrim');
});

test('editorialFrame: escapa body, header y data-title (sin & crudo)', () => {
  const html = H.editorialFrame({ header: 'Tom & Jerry', body: 'A < B & "C"', src: 'https://x/y.jpg', title: 'A & B' });
  assert.ok(!BAD_AMP.test(html), 'ningún & sin escapar en el marco');
  assert.ok(html.includes('data-title="A &amp; B"'), 'data-title escapado');
  assert.ok(html.includes('A &lt; B &amp; &quot;C&quot;'), 'el body escapa <, & y "');
});
