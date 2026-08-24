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
  // La sección puede partirse en varias líneas (§6.0: la tipografía se ajusta al
  // espacio), así que se afirma el ESCAPE —que es lo que la regresión protege—
  // y no que las tres palabras queden contiguas.
  assert.ok(svg.includes('&amp;'), 'el & debe renderizarse escapado como &amp;');
  assert.ok(!/>[^<]*&(?!amp;|lt;|gt;|quot;|#)/.test(svg), 'no debe quedar ningún & crudo dentro de un <text>');
});

// ── Clamp de título largo (Netflix/Spotify): ≤4 líneas + elipsis en generativo ─
// Líneas del body = <text> con y>52 (fuera de la banda HDR). Antes un título de
// 80 chars daba 9 líneas minúsculas que llenaban el póster.
function bodyLines(dataUri) {
  // Selección por COLOR DE RELLENO, no por geometría: la anatomía §6.0 movió el
  // título al pie y el `y>52` de antes (alto de la banda muerta) empezó a contar
  // líneas de sección. El título es el único texto en #F0EDE8.
  const svg = decodeURIComponent(String(dataUri).replace('data:image/svg+xml,', ''));
  return [...svg.matchAll(/<text[^>]*fill="#F0EDE8"[^>]*>([^<]*)<\/text>/g)].map(m => m[1]);
}test('_buildPosterV16: título largo se clampa a ≤4 líneas + "…"', () => {
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
test('editorialFrame (forma B §6.0): filete + sección + campo 16:9 + pie', () => {
  const html = H.editorialFrame({ header: 'Cine Cubano', body: 'La Peli', src: 'https://x/y.jpg', title: 'La Peli', dato: '96 min' });
  assert.ok(html.includes('class="ed-fil"') && html.includes('class="ed-hdr"'), 'filete de sección + sección');
  assert.ok(html.includes('class="ed-img"') && html.includes('class="ed-still"'), 'campo de imagen con el still');
  assert.ok(!html.includes('ed-blur'), 'el blur murió: ensuciaba el negro y competía con la imagen');
  assert.ok(!html.includes('ed-scrim'), 'el scrim murió: el título ya no va encima de la imagen');
  assert.ok(html.includes('class="ed-foot"') && html.includes('class="ed-title"'), 'título anclado al pie');
  assert.ok(html.includes('class="ed-dato"') && html.includes('96 min'), 'el dato vive en el pie');
  assert.ok(html.includes('_edPosterErr(this)'), 'usa el onerror unificado editorial (en el still)');
  assert.ok(!html.includes('poster-ed'), 'NO incluye el wrapper — eso lo pone el contenedor');
});

test('editorialFrame: omite header/scrim/img vacíos (thumb = banda + img sin título)', () => {
  const thumb = H.editorialFrame({ src: 'https://x/y.jpg', title: 'T' }); // sin header ni body
  assert.ok(thumb.includes('<div class="ed-hdr"></div>'), 'sección vacía = sin texto');
  assert.ok(thumb.includes('class="ed-still"') && !thumb.includes('ed-title'), 'still sí, título no (sin body)');
  const noImg = H.editorialFrame({ header: 'Sec' }); // sin src
  assert.ok(noImg.includes('<div class="ed-img"></div>'), 'ed-img vacío cuando no hay src');
});

test('editorialFrame: body undefined/"" → sin título · texto → título al pie', () => {
  assert.ok(!H.editorialFrame({ src: 'x' }).includes('ed-title'), 'undefined → sin título');
  assert.ok(!H.editorialFrame({ src: 'x', body: '' }).includes('ed-title'), '"" (ended-poster) → sin título');
  const titled = H.editorialFrame({ src: 'x', body: 'Peli' });
  assert.ok(titled.includes('<div class="ed-title">Peli</div>'), 'texto → título en el pie (§6.0)');
});

test('editorialFrame: escapa body, header y data-title (sin & crudo)', () => {
  const html = H.editorialFrame({ header: 'Tom & Jerry', body: 'A < B & "C"', src: 'https://x/y.jpg', title: 'A & B' });
  assert.ok(!BAD_AMP.test(html), 'ningún & sin escapar en el marco');
  assert.ok(html.includes('data-title="A &amp; B"'), 'data-title escapado');
  assert.ok(html.includes('A &lt; B &amp; &quot;C&quot;'), 'el body escapa <, & y "');
});

// ── Miniatura vs tapa: el halo y el campo centrado son SOLO de la miniatura ───
// Juan, 19 ago: los cortos dentro de un programa se veían huecos. El pie se
// llena con la obra desenfocada, pero solo donde hay hueco — en la tapa (con
// sección y título) ese espacio ya está ocupado y el halo sería decoración.
test('editorialFrame: la miniatura centra el campo; el halo va en AMBAS', () => {
  // Este test decía «la tapa NO lleva halo: el hueco lo llenan título y dato».
  // Esa premisa murió el 24 ago 2026: Juan la refutó EN PANTALLA — el still
  // termina en 66,67%, el título arranca en 86,4%, y entre medio hay 23,6px de
  // negro muerto en una card de 120. El halo llena ese vacío también en el
  // póster grande, con su propia ancla (ed-halo-full, 66,67%) para no dejar la
  // costura de 2,08% que dejaría el ancla de la miniatura.
  const mini = H.editorialFrame({ src: 'https://x/y.jpg', title: 'T' });        // sin header ni body
  assert.ok(mini.includes('class="ed-halo"') && !mini.includes('ed-halo-full'),
    'la miniatura conserva su halo con el ancla de siempre (68,75%)');
  assert.ok(mini.includes('ed-img ed-img-mid'), 'y el campo centrado');

  const tapa = H.editorialFrame({ header: 'Sec', body: 'Una obra', src: 'https://x/y.jpg', title: 'T' });
  assert.ok(tapa.includes('ed-halo ed-halo-full'),
    'el póster grande lleva halo anclado a SU campo — el vacío ya no es diseño');
  assert.ok(!tapa.includes('ed-img-mid'), 'y no centra el campo');

  const sinSrc = H.editorialFrame({});
  assert.ok(!sinSrc.includes('ed-halo'), 'sin imagen no hay halo que dibujar');
});

// ── La sección nunca se pinta con un color inexistente ───────────────────────
// Regresión real (19 ago): posterParts llamaba a editorialFrame SIN accent, el
// <text> salía con fill="undefined" y el navegador lo pintaba NEGRO sobre fondo
// oscuro. El filete no lo delataba: toma su color del CSS, no de ese argumento.
// El llamador ya pasa el accent; esto cubre el cinturón, por si aparece otro.
test('_edHdrSVG: sin accent cae a un color válido, nunca a "undefined"', () => {
  for (const acc of [undefined, null, '', '   ']) {
    const svg = H._edHdrSVG('Encuentro', acc);
    assert.ok(!/fill="(undefined|null|)"/.test(svg), `accent=${JSON.stringify(acc)} no puede dar fill vacío`);
    assert.ok(/fill="(#[0-9A-Fa-f]{3,8}|var\(--[a-z-]+\))"/.test(svg), 'el fill es un color de verdad');
  }
  assert.ok(H._edHdrSVG('Encuentro', '#3AAA6E').includes('fill="#3AAA6E"'), 'con accent, lo respeta');
});

// ── Póster de FUNCIÓN COMPARTIDA (Tipo 2) — las fronteras, §6.0 ──────────────
// La forma nació de un pedido de Juan (dos afiches dentro del póster propio) y
// se acotó tras dos hallazgos suyos mirando render real:
//   1) un STILL no puede ser módulo: se dibuja dentro del marco editorial, que
//      YA es un póster propio → sería un póster propio dentro de otro;
//   2) el «módulo mudo» para los incompletos se leía como sombra sucia y la
//      tarjeta se hacía pasar por la única obra visible.
// De ahí la regla dura: la Escalera existe SOLO COMPLETA, y solo en Tipo 2.
// Estos casos son las cuatro fronteras; cada uno mata una mutación distinta.
test('slotPosterParts: solo funciones compartidas de 2-3 obras, y solo completas', () => {
  const afiche = (title, poster) => ({ title, poster, posterSource: 'custom', duration: '90 min', section: 'Sec' });
  const still  = (title) => ({ title, poster: '/assets/x/still.jpg', posterSource: 'editorial', duration: '20 min', section: 'Sec' });
  const sinImg = (title) => ({ title, duration: '10 min', section: 'Sec' });

  const dos = [afiche('A', 'https://image.tmdb.org/t/p/w342/a.jpg'), afiche('B', 'https://image.tmdb.org/t/p/w342/b.jpg')];
  const tres = [...dos, afiche('C', 'https://image.tmdb.org/t/p/w342/c.jpg')];

  const p2 = H.slotPosterParts(dos);
  assert.ok(p2, 'dúo completo SÍ recibe tarjeta');
  assert.strictEqual(p2.modules.length, 2, 'dos módulos');
  assert.ok(p2.modules.every(Boolean), 'ningún módulo vacío: la forma es solo completa');
  assert.ok(/<svg[^>]*viewBox="0 0 120 180"/.test(p2.svg), 'dibuja en la retícula de §6.0');
  assert.ok(p2.dato.startsWith('2 obras'), 'el dato declara la pluralidad (única ancla de texto)');
  assert.ok(!/#F0EDE8/.test(p2.svg), 'SIN título interno: no hay texto en blanco de título');

  assert.ok(H.slotPosterParts(tres), 'trío completo SÍ');

  // Fronteras: cada una devuelve null (sin tarjeta), nunca una tarjeta a medias.
  assert.strictEqual(H.slotPosterParts([dos[0], still('S')]), null,
    'un STILL no es afiche: sería un póster propio dentro de otro');
  assert.strictEqual(H.slotPosterParts([dos[0], sinImg('X')]), null,
    'incompleto → sin tarjeta (el módulo mudo murió: se leía como sombra)');
  assert.strictEqual(H.slotPosterParts([...tres, afiche('D', 'https://image.tmdb.org/t/p/w342/d.jpg')]), null,
    '4+ obras → sin tarjeta: mostrar 3 de 4 sería elegir por el festival');
  assert.strictEqual(H.slotPosterParts([dos[0]]), null, 'una sola obra no es función compartida');
  assert.strictEqual(H.slotPosterParts(null), null, 'sin miembros, nada');
});

// ── Auditoría 24 ago 2026 (Cinemancia): mejoras 2, 3 y 5 de la Forma A ────────

test('Forma A — el título no repite la sección: el prefijo exacto se recorta', () => {
  const svg = decodeURIComponent(C._buildPosterV16({
    accent: '#E5A020', headerLabel: 'Competencia de cortometrajes',
    title: 'Competencia de cortometrajes Programa 1', num: null, dato: '71 min' }));
  // SOLO los textos del TÍTULO (fill #F0EDE8) — mirar todos los <text> era
  // decorativo: el quiebre de línea del título SIN recortar también produce una
  // línea final «Programa 1», y la aserción pasaba con la regla muerta. Cazado
  // mutando (if(false) sobrevivía).
  const titulo = [...svg.matchAll(/fill="#F0EDE8"[^>]*>([^<]+)<\/text>|<text(?=[^>]*fill="#F0EDE8")[^>]*>([^<]+)<\/text>/g)]
    .map(m => m[1] || m[2]);
  assert.deepStrictEqual(titulo.join(' ').trim(), 'Programa 1',
    'el título ES «Programa 1» y nada más — la sección ya lo dijo arriba: ' + JSON.stringify(titulo));
});

test('Forma A — sin coincidencia EXACTA de prefijo, el título no se toca', () => {
  // «Retrospectiva Sergio Navarro…» bajo «La sutil materia. Sergio Navarro»:
  // comparten nombre propio pero NO prefijo — adivinar sería peor que repetir.
  const svg = decodeURIComponent(C._buildPosterV16({
    accent: '#7F77DD', headerLabel: 'La sutil materia. Sergio Navarro',
    title: 'Retrospectiva Sergio Navarro Programa 1', num: null, dato: '67 min' }));
  assert.ok(/Retrospectiva/.test(svg), 'el título sobrevive intacto');
});

test('Forma A — si el recorte dejara el título vacío, se conserva el original', () => {
  const svg = decodeURIComponent(C._buildPosterV16({
    accent: '#E5A020', headerLabel: 'Iluminaciones',
    title: 'Iluminaciones', num: null, dato: '' }));
  assert.ok(/Iluminaciones/.test(svg), 'nunca un póster sin título por recortar de más');
});

test('Forma A — la luz hereda el acento de la sección, no el ámbar fijo', () => {
  const svg = decodeURIComponent(C._buildPosterV16({
    accent: '#3AAA6E', headerLabel: 'Iluminaciones',
    title: 'Pere Portabella: legado inmarcesible', num: null, dato: '99 min' }));
  const grad = svg.match(/<radialGradient[\s\S]*?<\/radialGradient>/)[0];
  assert.ok(grad.includes('#3AAA6E'), 'el gradiente usa el acento de sección');
  assert.ok(!grad.includes('#F59E0B'), 'el ámbar fijo murió del gradiente');
});

test('_datoCompuesto — el pie cuenta las obras del « + », y deja en paz lo demás', () => {
  assert.strictEqual(C._datoCompuesto('Oublie pas le gruau + Sol menor', '102 min'),
    '2 obras · 102 min');
  assert.strictEqual(C._datoCompuesto('La tempestá + No contéis con los dedos + Vampir Cuadecuc', '99 min'),
    '3 obras · 99 min');
  assert.strictEqual(C._datoCompuesto('Pere Portabella: legado inmarcesible', '99 min'),
    '99 min', 'una obra sola: el pie de siempre');
  assert.strictEqual(C._datoCompuesto('Chico eléctrico + Solo qu3r3mos un poco de amor', ''),
    '2 obras', 'compuesto sin duración: cuenta igual');
  assert.strictEqual(C._datoCompuesto('Sujo+2', '80 min'),
    '80 min', 'un «+» sin espacios es parte del nombre, no separador');
});

// ── Regla de carga + halo (24 ago 2026, notas de Juan sobre la revisión) ──────

test('_seccionPartes — reconoce la firma estricta y respeta los puntos que no lo son', () => {
  assert.deepStrictEqual(C._seccionPartes('La primavera llega para los que esperan. El cine de José Luis Torres Leiva'),
    {rotulo:'La primavera llega para los que esperan', firma:'El cine de José Luis Torres Leiva'});
  assert.deepStrictEqual(C._seccionPartes('La sutil materia. Sergio Navarro'),
    {rotulo:'La sutil materia', firma:'Sergio Navarro'});
  assert.deepStrictEqual(C._seccionPartes('Historia(s) del cine: Argentina. Curaduría de José Miccio'),
    {rotulo:'Historia(s) del cine: Argentina', firma:'Curaduría de José Miccio'});
  // el punto que NO es firma: «El espesor de las formas» no es un curador
  assert.deepStrictEqual(C._seccionPartes('Programa 1. El espesor de las formas'),
    {rotulo:'Programa 1. El espesor de las formas', firma:null});
});

test('Forma A — la firma va en itálica sobre el dato, y solo cuando se pasa', () => {
  const con = decodeURIComponent(C._buildPosterV16({accent:'#E05252',
    headerLabel:'La primavera llega para los que esperan',
    title:'¿Qué historia es ésta y cuál es su final?', num:null, dato:'74 min',
    firma:'El cine de José Luis Torres Leiva'}));
  assert.ok(/font-style="italic"[^>]*>El cine de José Luis Torres Leiva</.test(con),
    'la firma se pinta en itálica');
  const sin = decodeURIComponent(C._buildPosterV16({accent:'#E05252',
    headerLabel:'La primavera llega para los que esperan',
    title:'A + B', num:null, dato:'2 obras · 74 min'}));
  assert.ok(!/font-style="italic"/.test(sin), 'sin firma no hay itálica');
});

test('Forma A — regla de carga: la sección ya no pasa de 2 líneas', () => {
  const svg = decodeURIComponent(C._buildPosterV16({accent:'#7F77DD',
    headerLabel:'Spring comes for those who wait. The cinema of José Luis Torres Leiva',
    title:'X', num:null, dato:''}));
  const sec = [...svg.matchAll(/fill="#7F77DD"[^>]*>|<text(?=[^>]*fill="#7F77DD")/g)].length;
  const lineasSec = [...svg.matchAll(/<text[^>]*fill="#7F77DD"/g)].length;
  assert.ok(lineasSec <= 2, `sección en ${lineasSec} líneas (techo 2)`);
});

test('Forma B — el halo llena el vacío también en el póster grande', () => {
  const grande = H.editorialFrame({header:'La primavera llega para los que esperan',
    body:'Ver y escuchar', src:'/x.jpg', title:'Ver y escuchar', accent:'#E05252',
    firma:'El cine de José Luis Torres Leiva'});
  assert.ok(grande.includes('ed-halo ed-halo-full'), 'halo con ancla del campo grande');
  assert.ok(grande.includes('class="ed-firma"'), 'la firma vive en el pie');
  const mini = H.editorialFrame({src:'/x.jpg', title:'Corto'});
  assert.ok(mini.includes('class="ed-halo"') && !mini.includes('ed-halo-full'),
    'la miniatura conserva su ancla de siempre (68,75%)');
});

test('makeProgramPoster — el programa curado lleva el rótulo corto, sin firma', () => {
  // Versión 1 de este test tenía aserciones decorativas (un «|| true» incluido)
  // y la mutación «vuelve el rótulo completo» sobrevivía. Ahora se exige lo que
  // importa: NINGÚN texto del póster contiene la firma, y el rótulo no muere
  // en elipsis.
  const st = { snapshot: () => ({ FILMS: [], _lang: 'es' }) };
  const svg = decodeURIComponent(C.makeProgramPoster(st,
    'Sobre cosas que me han pasado + Verano', '110 min',
    '🌷 La primavera llega para los que esperan. El cine de José Luis Torres Leiva'));
  const textos = [...svg.matchAll(/<text[^>]*>([^<]+)<\/text>/g)].map(m => m[1]).join(' | ');
  assert.ok(/LA PRIMAVERA/.test(textos), 'el rótulo está: ' + textos);
  assert.ok(!/CINE DE|CINEMA OF|TORRES LEIVA/i.test(textos),
    'la firma NO aparece en ningún texto del programa (pila → cede): ' + textos);
  assert.ok(!/…/.test(textos), 'ningún texto muere en elipsis: ' + textos);
});

// ─── LA PILA DE OBRAS (mejora 1 de la auditoría de pósters, Juan 24 ago 2026) ──
//
// FALLA DE CLASE: un compuesto llegaba al motor como una frase corrida —
// «La tempestá + No contéis con los dedos + Vampir Cuadecuc» — y _fitLines lo
// partía donde cayera: la línea rompía a mitad de un nombre y el conjunto moría
// en elipsis. Un cartel de programa doble nunca tipografía así: APILA las obras.
//
// Retícula medida con Juan sobre grid y rulers (no a ojo): un bloque por obra,
// todas al MISMO cuerpo, 1u exacto de gap, el «+» dentro de ese gap a 0,6u y al
// margen, en color de sección. Frontera 2–3 obras (la misma de la forma C).
const U16 = 120/8;                       // unidad del viewBox de la Forma A
function _textos(svg){
  return [...decodeURIComponent(svg).matchAll(
    /<text x="([-\d.]+)" y="([-\d.]+)"[^>]*font-size="([\d.]+)"[^>]*fill="([^"]+)"[^>]*>([^<]*)</g)]
    .map(r => ({ x:+r[1], y:+r[2], fs:+r[3], fill:r[4], txt:r[5] }));
}
const ACC = '#3AAA6E';
const _pila = (title, dato) => _textos(C._buildPosterV16(
  { accent:ACC, headerLabel:'Iluminaciones', title, num:null, dato }));
const _cuerpo = rows => rows.filter(r => r.fill === '#F0EDE8');   // el título
const _mas    = rows => rows.filter(r => r.txt === '+');

test('la pila — cada obra es su propio bloque, ninguna línea mezcla dos obras', () => {
  const cuerpo = _cuerpo(_pila('La tempestá + No contéis con los dedos + Vampir Cuadecuc', '3 obras · 99 min'));
  const texto = cuerpo.map(r => r.txt).join(' ');
  assert.ok(!cuerpo.some(r => r.txt.includes('+')),
    'apilado, ningún « + » puede quedar dentro de una línea de título — es su propio bloque');
  assert.ok(!texto.includes('…'), 'apilado, el compuesto entero cabe sin elipsis');
  for (const nombre of ['La tempestá', 'Vampir Cuadecuc'])
    assert.ok(texto.includes(nombre), `falta la obra completa: ${nombre}`);
});

test('la pila — hermanas iguales: todas las obras al mismo cuerpo', () => {
  // La pareja corta+larga es la que DISCRIMINA: con dos nombres cortos, «el menor»
  // y «el mayor» de los ajustes coinciden y el test no probaría nada.
  for (const t of ['Ida + Un título considerablemente más largo que el anterior',
                   'Rancho + Gosse',
                   'La tempestá + No contéis con los dedos + Vampir Cuadecuc']) {
    const fs = new Set(_cuerpo(_pila(t, '')).map(r => r.fs));
    assert.equal(fs.size, 1, `${t} → una obra grita más que su vecina: ${[...fs]}`);
    assert.ok([...fs][0] <= 16, `el cuerpo de la pila no puede pasar de 16: ${[...fs][0]}`);
    // Y que sea EL MENOR, no el mayor: el cuerpo común jamás puede pasarse de lo
    // que aguanta la hermana más angosta por sí sola. (Ajuste solo por ancho —
    // caja alta — para no reproducir en el test la aritmética del presupuesto.)
    const _sola = o => C._fitLines(o,
      { boxW: 97.5, boxH: 1e4, maxLines: 2, fsMax: 16, fsMin: 9, lhRatio: 1.2, lsEm: -0.02 }).fs;
    const _aguanta = Math.min(...t.split(' + ').map(_sola));
    assert.ok([...fs][0] <= _aguanta,
      `${t} → la pila se dibuja a ${[...fs][0]}, más de lo que aguanta su hermana más angosta (${_aguanta})`);
  }
});

test('la pila — el « + » vive en el gap: 0,6u, al margen, en color de sección', () => {
  const mas = _mas(_pila('La tempestá + No contéis con los dedos + Vampir Cuadecuc', ''));
  assert.equal(mas.length, 2, 'dos obras contiguas → un « + » entre ellas');
  for (const m of mas) {
    assert.equal(m.fs, 0.6*U16, 'el « + » mide 0,6u');
    assert.equal(m.x, +(0.75*U16).toFixed(2), 'el « + » se apoya en el margen, como todo el sistema');
    assert.equal(m.fill, ACC, 'el « + » lleva el color de la sección');
  }
});

test('la pila — 1u exacto entre bloques, y el « + » centrado en ese aire', () => {
  const rows = _pila('Rancho + Gosse', '2 obras · 71 min');
  const [a, b] = _cuerpo(rows);                 // una línea por obra
  const lh = a.fs*1.2;
  assert.ok(Math.abs((b.y - a.y) - (lh + U16)) < 0.05,
    `el gap entre bloques debe ser 1u exacto — medido ${((b.y-a.y-lh)/U16).toFixed(3)}u`);
  const centro = a.y + U16/2;                   // mitad del aire
  assert.ok(Math.abs(_mas(rows)[0].y - (centro + 0.6*U16*0.35)) < 0.05,
    'el « + » cae ópticamente en el medio del gap, no en su borde');
});

test('la pila — se apoya en la misma base que cualquier título (§6.0)', () => {
  const base = rows => Math.max(..._cuerpo(rows).map(r => r.y));
  assert.equal(base(_pila('Rancho + Gosse', '2 obras · 71 min')),
               base(_pila('Los bibliotecarios', '92 min')),
    'la pila crece hacia arriba: su última línea comparte base con el título de una sola obra');
});

test('la pila — frontera 2–3: con 4 obras vuelve la forma de siempre', () => {
  const rows = _pila('Rancho + Gosse + Spot uno + Spot dos', '4 obras · 88 min');
  assert.equal(_mas(rows).length, 0,
    'con 4 obras no hay pila: el pie ya dice « 4 obras » y el cuerpo caería a ilegible');
  assert.equal(_mas(_pila('Los bibliotecarios', '92 min')).length, 0,
    'una sola obra nunca se apila');
});

test('la pila — nunca invade el bloque de sección, ni con rótulo de 2 líneas', () => {
  const rows = _textos(C._buildPosterV16({ accent:ACC,
    headerLabel:'La primavera llega para los que esperan',
    // Peor caso hallado por fuerza bruta sobre el espacio de compuestos: tres
    // nombres MEDIANOS bajo un rótulo de 2 líneas. Caben holgados por ancho, así
    // que quien los baja es el presupuesto de alto — es el único input que prueba
    // el techo. Con una caja fija de 2,4u este mismo cartel invade la sección.
    title:'El norte de la mañana + Cantos de la aurora + La casa de la frontera',
    num:null, dato:'3 obras · 140 min' }));
  const secBottom = Math.max(...rows.filter(r => r.fill === ACC && r.txt !== '+').map(r => r.y));
  const pilaTop   = Math.min(..._cuerpo(rows).map(r => r.y - r.fs));   // borde alto de la caja
  assert.ok(pilaTop > secBottom,
    `la pila se metió en la sección: tope ${pilaTop} vs fondo de sección ${secBottom}`);
});

test('la pila — reparto por uso real: el cuerpo es el que manda el ANCHO, no el vecino', () => {
  // El presupuesto se reparte POR USO REAL, no en tercios. Repartido en partes
  // iguales, dos obras de una línea pagaban por la tercera que usaba dos: en
  // «La tempestá + …» sobraban ~3,7u de aire muerto y la pila salía a 10,8 en vez
  // de a 14. La propiedad correcta: el cuerpo común es EL IDEAL POR ANCHO —lo
  // único que de verdad limita a cada obra— salvo que el techo tenga que bajarlo.
  const _idealPorAncho = t => Math.min(16, ...t.split(' + ').map(o => C._fitLines(o,
    { boxW: 97.5, boxH: 1e4, maxLines: 2, fsMax: 16, fsMin: 9, lhRatio: 1.2, lsEm: -0.02 }).fs));
  const _cuerpoDe = (sec, t, dato) => _cuerpo(_textos(C._buildPosterV16(
    { accent:ACC, headerLabel:sec, title:t, num:null, dato })))[0].fs;

  // Sin presión de techo: el cuerpo TIENE que ser el ideal por ancho.
  for (const [sec, t, dato] of [
        ['Iluminaciones', 'La tempestá + No contéis con los dedos + Vampir Cuadecuc', '3 obras · 99 min'],
        ['Iluminaciones', 'Rancho + Gosse', '2 obras · 71 min'],
      ]) {
    const fs = _cuerpoDe(sec, t, dato), ideal = _idealPorAncho(t);
    assert.equal(fs, ideal,
      `${t} → la pila se dibuja a ${fs} pudiendo ir a ${ideal}: la está encogiendo un vecino, no su propio ancho`);
  }

  // Con presión de techo (tres medianos bajo rótulo de 2 líneas) el cuerpo baja
  // por debajo del ideal — y esa bajada es justamente lo que prueba el lazo.
  const SEC2 = 'La primavera llega para los que esperan';
  const T2 = 'El norte de la mañana + Cantos de la aurora + La casa de la frontera';
  assert.ok(_cuerpoDe(SEC2, T2, '3 obras') < _idealPorAncho(T2),
    'el peor caso debería estar limitado por el techo, no por el ancho — si no, dejó de probar el lazo');
});
