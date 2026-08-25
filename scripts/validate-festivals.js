#!/usr/bin/env node
/**
 * validate-festivals.js
 * Valida la integridad de los JSONs de festival antes de commit.
 *
 * Uso: node scripts/validate-festivals.js [festival-id]
 * Ejemplo: node scripts/validate-festivals.js aff-2026
 *          node scripts/validate-festivals.js  (valida todos)
 *
 * Exit code 0 = OK | Exit code 1 = errores encontrados
 */

const fs = require('fs');
const path = require('path');

// ── SECTION_EN: claves del mapa de display EN (src/config.js, ESM) ─────────────
// El validador es CommonJS y config.js es ESM → no se puede require(). Se parsean
// las CLAVES (strings ES con emoji) del bloque `export const SECTION_EN = {…}`
// para que el check de cobertura [i18n-content-coverage] reconozca qué secciones
// ya tienen traducción de display. Guardado: si falla, el Set queda vacío.
// ── EL CONTRATO DE DATOS ─────────────────────────────────────────────────────
// `pipeline/contrato.json` es el canon EJECUTABLE de una función: tipos,
// formatos, obligatorios y enums. Antes esto vivía repartido entre una lista
// hardcodeada aquí abajo (RULE 5) y la prosa de docs/SCHEMA.md — dos fuentes que
// se desincronizaban en silencio (la doc decía que `duration` era un número
// cuando las 1.194 son el string «90 min»). Ahora hay una sola, y de ella se
// GENERA la doc. Ver scripts/generate-schema-md.js.
const CONTRATO = JSON.parse(
  fs.readFileSync(path.join(__dirname, '..', 'pipeline', 'contrato.json'), 'utf8'));
// Zona del proyecto (Colombia, UTC-5) y NO UTC: con toISOString() crudo, entre
// las 7pm y medianoche de Bogotá `HOY` ya era mañana, así que una excepción
// vencía cinco horas antes y la máquina local discrepaba de CI. Es la regla que
// CLAUDE.md fija («nunca toISOString() para lógica de fechas») y que este
// archivo violaba — el mismo bug que rompió el generador de CLAUDE.md (#682).
const _hoyCO = ms => new Date(ms - 5 * 3600e3).toISOString().slice(0, 10);
const HOY = _hoyCO(Date.now());
// Ventana de aviso: una excepción no puede explotar el día D sin haber avisado.
const PREAVISO = _hoyCO(Date.now() + 14 * 864e5);

// ¿A este festival se le exige el contrato entero? La vigencia la dice la FECHA
// DE CIERRE, no una lista de nombres: un guardián que decide por lista deja de
// mirar en cuanto la lista envejece.
function _exentoDe(campo, fest, finStr) {
  const _fin = String(finStr || '').slice(0, 10);
  const _archivado = _fin && _fin < HOY;
  const _exc = (CONTRATO._excepciones || {})[campo] || {};
  if (_archivado && fest in _exc) return { exento: true };
  const _pend = ((CONTRATO._pendientes || {})[campo] || {})[fest];
  if (_pend) {
    // La excepción con fecha se VENCE SOLA. Una sin fecha se vuelve permanente.
    if (HOY < _pend.migrar_el) return { exento: true, aviso: _pend };
    return { exento: false, vencida: _pend };
  }
  return { exento: false };
}

const SECTION_EN_KEYS = new Set();
// [seccion-sin-arquetipo]: claves de SECTION_ARCHETYPES (src/config.js). Toda
// sección DEBE tener arquetipo o _sectionColor cae a gris ilegible #2C2C2A (el
// bug que reaparece con cada festival nuevo). Guardado: si falla, Set vacío.
const SECTION_ARCHETYPE_KEYS = new Set();
try {
  const _cfgSrc = fs.readFileSync(path.join(__dirname, '..', 'src', 'config.js'), 'utf8');
  const _m = _cfgSrc.match(/export const SECTION_EN\s*=\s*\{([\s\S]*?)\n\};/);
  if (_m) for (const km of _m[1].matchAll(/'([^']*)'\s*:/g)) SECTION_EN_KEYS.add(km[1]);
  const _ma = _cfgSrc.match(/export const SECTION_ARCHETYPES\s*=\s*\{([\s\S]*?)\n\};/);
  if (_ma) for (const km of _ma[1].matchAll(/'([^']*)'\s*:/g)) SECTION_ARCHETYPE_KEYS.add(km[1]);
} catch (e) { /* Sets vacíos → los checks informan 0 cobertura */ }

// [event-kind-conocido]: claves de _kindMapES/_kindMapEN (src/view/components.js).
// Un `event_kind` sin entrada NO falla: makeEventPoster cae al genérico «EVENTO»,
// que es una card que se ve bien y miente. Así vivieron en producción los 8
// talleres de FICMA (kind 'taller', nunca estuvo en el mapa) hasta el día que el
// festival abrió. Los DOS idiomas se leen por separado a propósito: una clave solo
// en ES pasa inadvertida hasta que alguien abre la app en inglés.
// Parser con guardia RUIDOSA: si no encuentra los dos mapas o salen vacíos, el
// check lo dice. Un parser flojo no avisa de menos — avisa mal.
const KIND_KEYS = { es: new Set(), en: new Set() };
let KIND_MAPS_OK = false;
try {
  const _cmp = fs.readFileSync(path.join(__dirname, '..', 'src', 'view', 'components.js'), 'utf8');
  for (const lang of ['ES', 'EN']) {
    const m = _cmp.match(new RegExp('const _kindMap' + lang + '\\s*=\\s*\\{([\\s\\S]*?)\\n  \\};'));
    if (m) for (const km of m[1].matchAll(/'([^']+)'\s*:\s*\{\s*accent/g)) KIND_KEYS[lang.toLowerCase()].add(km[1]);
  }
  KIND_MAPS_OK = KIND_KEYS.es.size > 0 && KIND_KEYS.en.size > 0;
} catch (e) { /* KIND_MAPS_OK queda false → el check se declara ciego */ }

// ── Mapa de países → emoji bandera ───────────────────────────────────────────
const FLAGS_MAP = {
  'Colombia':'🇨🇴','UK':'🇬🇧','Chile':'🇨🇱','Brasil':'🇧🇷','Bolivia':'🇧🇴',
  'México':'🇲🇽','Guatemala':'🇬🇹','Francia':'🇫🇷','EEUU':'🇺🇸','Panamá':'🇵🇦',
  'Venezuela':'🇻🇪','Haití':'🇭🇹','España':'🇪🇸','Argentina':'🇦🇷','Uruguay':'🇺🇾',
  'Perú':'🇵🇪','Ecuador':'🇪🇨','Cuba':'🇨🇺','Paraguay':'🇵🇾','Costa Rica':'🇨🇷',
  'Alemania':'🇩🇪','Italia':'🇮🇹','Portugal':'🇵🇹','Suiza':'🇨🇭','Bélgica':'🇧🇪',
  'Países Bajos':'🇳🇱','Suecia':'🇸🇪','Noruega':'🇳🇴','Dinamarca':'🇩🇰',
  'Polonia':'🇵🇱','Austria':'🇦🇹','Grecia':'🇬🇷','Turquía':'🇹🇷','Israel':'🇮🇱',
  'Irán':'🇮🇷','Corea del Sur':'🇰🇷','Japón':'🇯🇵','China':'🇨🇳','Taiwán':'🇹🇼',
  'India':'🇮🇳','Australia':'🇦🇺','Senegal':'🇸🇳','Palestina':'🇵🇸',
  'Rep. Dominicana':'🇩🇴','Nicaragua':'🇳🇮','Canadá':'🇨🇦','Eslovaquia':'🇸🇰',
  'Estonia':'🇪🇪','Vietnam':'🇻🇳','Bolivia':'🇧🇴','Reino Unido':'🇬🇧',
  'Inglaterra':'🇬🇧','Rumania':'🇷🇴','Hungría':'🇭🇺','Finlandia':'🇫🇮',
  'Namibia':'🇳🇦','Nigeria':'🇳🇬','Marruecos':'🇲🇦','Sudáfrica':'🇿🇦',
  'Estados Unidos':'🇺🇸','Nueva Zelanda':'🇳🇿','USA':'🇺🇸','US':'🇺🇸',
  'Honduras':'🇭🇳','El Salvador':'🇸🇻','Puerto Rico':'🇵🇷','Jamaica':'🇯🇲',
};

// Emojis que NO son banderas de país — usados como sección, no como flags
const NON_FLAG_EMOJIS = new Set([
  '🎬','🎞️','🌐','🌍','🌎','🌊','🎨','⏳','📽️','🏆','⭐','📋','✨','🪶','✊',
  '🎭','🎖️','🏛️','🌙','🌿','💡','🌱','🌸','📖',
]);

// Categorías que legítimamente comparten emoji (subcategorías del mismo concepto)
const SHARED_EMOJI_ALLOWED = ['retrospectiva','retrospect','ciclo','cicl','muestra'];
const isSharedAllowed = (secName) =>
  SHARED_EMOJI_ALLOWED.some(w => secName.toLowerCase().includes(w));

// ── Helpers ──────────────────────────────────────────────────────────────────
function getFlagsFromList(filmList) {
  const seen = [];
  for (const film of filmList) {
    for (const country of (film.country || '').split('/')) {
      const c = country.trim();
      if (c && FLAGS_MAP[c] && !seen.includes(FLAGS_MAP[c])) seen.push(FLAGS_MAP[c]);
    }
  }
  return seen.join('');
}

function sectionEmoji(sec) {
  if (!sec) return '';
  const first = sec.split(' ')[0];
  // Only treat as emoji if it's actually an emoji character (not a word like "Spotlight" or "U.S.")
  const isEmoji = /^\p{Emoji}/u.test(first) && !/^[A-Za-z0-9.]/u.test(first);
  return isEmoji ? first : '';
}

// [day-order-indice] — DEUDA CONOCIDA al introducir la regla (9 ago 2026).
// Mismo patrón que el techo de `module-size`: lo que ya estaba mal queda visible y
// con número, pero solo puede BAJAR. Un festival nuevo entra en 0 o no entra, y
// cualquier función que se agregue a estos cinco tiene que salir bien.
// Sin la lista, la regla dejaría el pipeline trabado hasta corregir cinco JSON
// —cuatro de ellos de festivales ya archivados— y eso, con FICDEH y FINCA
// abriendo el 12, es un riesgo peor que la deuda.
// FICMA es el urgente: 83 de 90, y abre el 10 de agosto.
const DAY_ORDER_DEUDA = {
  // FICMA salió de la lista el 9 ago: su ensamblador ya calcula
  // day_order = dayKeys.indexOf(day). Los cuatro que quedan están archivados.
  'ficmontanas-2026.json': 40,
  'leviza-2026.json': 21,
  'tercertiempo-2026.json': 14,
  'fantasofest-2026.json': 11,
};

// ── Vocabulario de géneros ───────────────────────────────────────────────────
// Se LEE de _GENRE_EN (src/controller/sheets-controller.js), que es el dueño:
// la tabla que la app usa para traducir géneros, con los nombres canónicos de
// TMDB. Copiar la lista acá crearía una segunda verdad que envejece sola.
// Si algún día _GENRE_EN se mueve, este parseo falla RUIDOSO (lista vacía →
// el gate avisa) en vez de dar verde sobre nada.
const GENEROS = (() => {
  try {
    const src = fs.readFileSync(path.join(__dirname, '..', 'src', 'controller', 'sheets-controller.js'), 'utf8');
    const blk = src.match(/const _GENRE_EN = \{([\s\S]*?)\n\};/);
    if (!blk) return new Set();
    const v = new Set();
    for (const m of blk[1].matchAll(/'([^']+)'\s*:\s*'([^']+)'/g)) {
      v.add(m[1].toLowerCase()); v.add(m[2].toLowerCase());
    }
    // Dos que la app usa como género y no viven en la tabla de traducción
    // porque se escriben igual en los dos idiomas.
    v.add('ficción'); v.add('fiction');
    return v;
  } catch { return new Set(); }
})();

// ── Validar un festival ──────────────────────────────────────────────────────
function validateFestival(fname, data) {
  const errors = [];
  const warnings = [];
  // El preaviso YA existía —_exentoDe devuelve `aviso` cuando la excepción sigue
  // viva— y nadie lo leía: caducaba en silencio y aparecía como rojo el día D.
  const _avisados = new Set();
  const _avisar = (ex, campo, fest) => {
    if (!ex.aviso || ex.aviso.migrar_el > PREAVISO) return;
    const _k = `${campo}@${fest}`;
    if (_avisados.has(_k)) return;
    _avisados.add(_k);
    warnings.push(`[contrato-por-vencer] ${_k} deja de perdonarse el ${ex.aviso.migrar_el}`
      + ` — migrar antes de esa fecha o mover la fecha con su razón`);
  };
  const _dayOrderMal = [];

  const hasConfigBlock = !!data.config;
  const cfg = data.config || {};
  const films = data.films || [];
  // dayKeys vive en la RAÍZ del JSON desde el pipeline v2 (config{} salió a
  // src/config.js y es error bloqueante tenerlo acá). Leerlo solo de `cfg` dejaba
  // en cero toda regla que dependiera de él —incluida RULE 1, «el día existe en
  // dayKeys»— y una regla que nunca corre se lee igual que una regla que pasa.
  // Cazado el 9 ago 2026 al estrenar [day-order-indice]: daba verde en los 12.
  const dayKeys = data.dayKeys || cfg.dayKeys || [];

  // CONFIG required fields
  // Festivales NUEVOS (desde Mujeres 2026): config en FESTIVAL_CONFIG de src/config.js, no en el JSON.
  // GATE: config{} en el JSON es un error bloqueante desde el pipeline v2.
  if (data.config && Object.keys(data.config).length > 0) {
    errors.push('GATE BLOQUEANTE: config{} presente en el JSON — mover a FESTIVAL_CONFIG en src/config.js y eliminar este bloque');
  }

  // GATE [genero-unico]: UNA obra, UN género — y de los comunes.
  //
  // Juan, 24 ago 2026: «No me gusta que incluyamos varios géneros en la card.
  // Solo el primero, el principal». Y después, viendo el resultado: «tags no,
  // necesitamos indicar un género, dentro de los más comunes».
  //
  // TIFF traía 859 de 878 obras (97%) con varios, y no eran subgéneros sino
  // ETIQUETAS DE PROGRAMACIÓN del festival mezcladas con el género en el mismo
  // campo: «Asian Cultures, Drama, Directed by Women, Coming of Age». Tomar el
  // primero a secas habría publicado «Asian Cultures» donde va «Drama», en 271
  // fichas.
  //
  // LA REGLA: el PRIMER género de la fuente QUE SEA UN GÉNERO. El orden de la
  // fuente manda; lo que no es género se salta. Si no hay ninguno, el campo
  // queda VACÍO — inventarle un género a una obra es peor que no decir nada.
  //
  // El vocabulario NO se define acá: se LEE de _GENRE_EN (sheets-controller.js),
  // que es el que la app ya usa para traducir géneros y trae los nombres
  // canónicos de TMDB. Duplicarlo sería crear una segunda verdad que se
  // desincroniza — el patrón que ya nos costó el calendario partido.
  for (const f of films) {
    const g = f.genre;
    if (typeof g !== 'string' || !g.trim()) continue;
    if (/[,+]/.test(g)) {
      errors.push(`GATE BLOQUEANTE [genero-unico]: «${f.title}» declara varios géneros `
        + `(«${g}»). Va UNO: el primero de la fuente que sea un género de verdad `
        + `(vocabulario: _GENRE_EN). Si ninguno lo es, dejar el campo vacío.`);
      break;
    }
    if (!GENEROS.has(g.trim().toLowerCase())) {
      warnings.push(`[genero-unico] «${f.title}»: «${g}» no está en el vocabulario de géneros `
        + `(_GENRE_EN). Puede ser una etiqueta del festival colada como género.`);
    }
  }

  // GATE [poster-map-legacy]: el modelo dual posters{}/customPosters{} murió en Fase A.1.
  // Un film = un `poster` inline. Si reaparece un map, el pipeline regresó al modelo viejo.
  for (const mapKey of ['posters', 'customPosters']) {
    if (data[mapKey] && Object.keys(data[mapKey]).length > 0) {
      errors.push(`GATE BLOQUEANTE [poster-map-legacy]: ${mapKey}{} presente — el modelo map murió en Fase A.1. Inline el poster en cada film (scripts/migrate-posters-inline.py) y elimina el mapa.`);
    }
  }

  // GATE [seccion-sin-arquetipo]: toda sección usada (films + cortos anidados)
  // debe tener arquetipo en SECTION_ARCHETYPES o _sectionColor cae a gris ilegible
  // #2C2C2A. Caza secciones nuevas de un festival recién montado ANTES de publicar.
  if (SECTION_ARCHETYPE_KEYS.size > 0) {
    const _secs = new Set();
    (function collect(x) {
      if (Array.isArray(x)) x.forEach(collect);
      else if (x && typeof x === 'object') {
        if (x.section) _secs.add(x.section);
        for (const v of Object.values(x)) collect(v);
      }
    })(data);
    for (const sec of _secs) {
      if (!SECTION_ARCHETYPE_KEYS.has(sec)) {
        errors.push(`GATE BLOQUEANTE [seccion-sin-arquetipo]: sección "${sec}" no está en SECTION_ARCHETYPES (src/config.js) → cae a gris ilegible #2C2C2A. Asignale uno de los 9 arquetipos.`);
      }
    }
  }

  // GATE [sin-procedencia] (opt-in): la doctrina "leer, no inventar" hecha
  // verificable. Un festival montado con el pipeline v2 declara `_provenance:true`
  // en el root → TODO film top-level debe llevar `_src: {url, date}` que registra
  // de dónde salió (URL de la fuente oficial + fecha de extracción). Sin fuente
  // declarada = dato no confiable = ERROR. Los cortos de film_list heredan el
  // _src del bloque salvo que traigan el propio. Festivales pre-v2 (sin el flag)
  // no se ven afectados. La app ignora _src (prefijo _, no se renderiza).
  if (data._provenance === true) {
    const _sinSrc = [];
    for (const f of films) {
      const s = f._src;
      if (!s || typeof s.url !== 'string' || !/^https?:\/\//.test(s.url) || !s.date) {
        _sinSrc.push(f.title || '(sin título)');
      }
    }
    if (_sinSrc.length) {
      errors.push(`GATE BLOQUEANTE [sin-procedencia]: ${_sinSrc.length} film(s) sin _src:{url,date} válido (el festival declara _provenance:true — todo dato lleva fuente): ${_sinSrc.slice(0, 5).join(' · ')}${_sinSrc.length > 5 ? ` … +${_sinSrc.length - 5}` : ''}`);
    }
  }

  // Festivales LEGADOS (FICCI 65, Cinemancia 2025): config en el bloque config{} del JSON.
  if (!hasConfigBlock) {
    warnings.push('Sin bloque config{} — se asume que la configuración está en FESTIVAL_CONFIG en src/config.js (formato nuevo ✓)');
  } else {
    // Solo verificar campos si el JSON tiene bloque config (formato legado)
    const cfgRequired = ['name','shortName','city','dates','storageKey','festivalEndStr'];
    for (const k of cfgRequired) {
      if (!cfg[k]) errors.push(`config.${k} es requerido`);
    }
  }

  // ── Ticketing (campos opcionales del root) ──────────────────────────────────
  if (data.ticket_url != null) {
    if (!data.ticketing_model || !['paid','mixed'].includes(data.ticketing_model))
      errors.push(`ticket_url presente pero ticketing_model falta o no es "paid"/"mixed" (valor: ${JSON.stringify(data.ticketing_model)})`);
    if (typeof data.ticket_url !== 'string' || !data.ticket_url.startsWith('https://'))
      errors.push(`ticket_url debe empezar con https:// (valor: ${JSON.stringify(data.ticket_url)})`);
  } else if (data.ticketing_model != null) {
    // La boletería es POR FUNCIÓN desde FICDEH: un festival puede tener
    // `ticketing_model` en la raíz y el enlace en cada función, que es el caso
    // normal cuando cada sesión se vende aparte (CineAutopsia: 6 enlaces de
    // TuBoleta distintos y una clausura libre). Exigir un ticket_url de raíz
    // obligaba a inventar «el enlace del festival», que no existe.
    const _conEnlace = (data.films || []).filter(f => f.ticket_url).length;
    const _libres = (data.films || []).filter(f => f.is_free === true).length;
    if (!_conEnlace && !_libres)
      errors.push(`ticketing_model presente y NINGUNA función dice cómo se entra `
        + `(ni ticket_url ni is_free) — eliminar ticketing_model o llenar la casilla`);
  }

  // dayKeys must match festivalDates (solo si el JSON define config)
  // Misma sombra que dayKeys: festivalDates vive en la raíz desde el pipeline v2.
  const festDates = data.festivalDates || cfg.festivalDates || {};
  for (const k of dayKeys) {
    if (!festDates[k]) errors.push(`dayKeys tiene '${k}' pero festivalDates no lo tiene`);
  }

  // days[].lbl must be in Spanish (MIÉ, JUE, VIE...) not English (WED, THU, FRI...)
  // Si está en inglés, el switch de idioma no puede traducir los días
  const EN_DAYS = ['MON','TUE','WED','THU','FRI','SAT','SUN'];
  const days = data.days || cfg.days || [];
  for (const day of days) {
    if (day.lbl && EN_DAYS.includes(day.lbl.toUpperCase())) {
      errors.push(`days[].lbl '${day.lbl}' está en inglés — debe ser español (LUN/MAR/MIÉ/JUE/VIE/SÁB/DOM). El switch de idioma no funcionará.`);
    }
  }

  // Track sections
  const emojiToSections = {}; // emoji → [section names]
  const sectionStrings = {};  // sec_name → Set of exact strings

  const _seenTitles = new Set();   // title-only: para detectar multi-función (informativo)
  const _seenSlots  = new Set();   // title+day+time: duplicado real (bloqueante)
  for (const film of films) {
    const title = film.title || '?';
    const sec = film.section || '';
    const isEvent = film.type === 'event';
    const isCortos = !!film.is_cortos;

    // ── RULE 1: day must exist in dayKeys ─────────────────────────────────
    // 'TBD' es un marcador DELIBERADO: la función existe y el festival aún no
    // anunció su fecha (Tribeca la usa junto con time:'TBD'). No es un día roto,
    // es la ausencia de día dicha en voz alta — y la app la trata aparte.
    // Esta rama estuvo dormida hasta el 9 ago 2026: dayKeys se leía solo de
    // config{}, que el pipeline v2 sacó del JSON, así que la lista venía vacía y
    // la regla no comparaba nada.
    if (film.day && film.day !== 'TBD' && dayKeys.length && !dayKeys.includes(film.day)) {
      errors.push(`"${title}": day='${film.day}' no existe en dayKeys`);
    }

    // ── RULE 1c: el nombre corto no puede ser ambiguo entre ciudades ──────
    // [short-ambiguo] — el `short` es una ETIQUETA, no una identidad. Dentro de una
    // misma ciudad varias sedes lo comparten a propósito (las salas de un edificio),
    // pero si el MISMO short aparece en DOS ciudades, cualquier lógica que agrupe por
    // él las funde: en FICDEH «Cinema Local» (Bogotá y Cali) y «Alianza Francesa»
    // (Barranquilla y Cartagena) hacían que elegir una trajera las funciones de la
    // otra, que el conteo de la ciudad no cuadrara y que la sede DESAPARECIERA de la
    // lista de la segunda (9 ago 2026, en producción). El código ya no se deja
    // engañar —la clave es (ciudad, short)— pero el dato sigue siendo ambiguo para
    // un ojo humano: dos filas idénticas en dos ciudades distintas.
    // Aviso, no error: puede ser legítimo (una cadena con sede en dos ciudades).
    // Lo que no puede es pasar inadvertido.

    // ── RULE 1b: day_order ES el índice del día en dayKeys ────────────────
    // [day-order-indice] — `day_order` no es un número libre: es el índice del día
    // (0 = primer día), y así lo trata TODA la app. Ordena las funciones de la
    // ficha, las filas de Mi Plan, el «próximo» del Programa (day_order*1440+hora)
    // y el plan que arma el planeador. Con el valor equivocado no hay error visible
    // — solo un orden que miente.
    //
    // Cazado el 9 ago 2026 al auditar la geometría del bloque de sesiones: la ficha
    // del taller de Leviza listaba JUE 14 · SÁB 16 · VIE 15. La revisión encontró
    // FICMA con 83 de 90 funciones fuera de índice, a un día de abrir. El patrón
    // era usar day_order como contador correlativo por función, no como día.
    //
    // `loader.js` ya lo recalcula cuando un aviso reprograma una función — esa es
    // la definición viva del campo; acá se exige lo mismo en el dato de origen.
    if (film.day && film.day_order != null && dayKeys.length) {
      const _esperado = dayKeys.indexOf(film.day);
      if (_esperado >= 0 && film.day_order !== _esperado) {
        _dayOrderMal.push(`"${title}" (${film.day}): day_order=${film.day_order}, esperado ${_esperado}`);
      }
    }

    // ── RULE 2: is_cortos must have film_list ─────────────────────────────
    // GUARD anti-recaída (jun 2026): un bloque is_cortos VACÍO es una cáscara que
    // invisibiliza cortos que SÍ están en el festival (pasó con los 49 cortos
    // "pausados"). Error bloqueante: o trae su film_list, o no lleva is_cortos.
    if (isCortos && (!film.film_list || film.film_list.length === 0)) {
      errors.push(`"${title}": is_cortos:true pero film_list vacío (cáscara — agregar los cortos o quitar is_cortos)`);
    }

    // ── RULE 3: is_cortos flags must be derived from film_list ────────────
    if (isCortos && film.film_list && film.film_list.length > 0) {
      const derived = getFlagsFromList(film.film_list);
      const current = film.flags || '';
      if (derived && (NON_FLAG_EMOJIS.has(current) || current === '' || current === 'Varios')) {
        warnings.push(`"${title}": flags='${current}' debería ser '${derived}' (derivado de film_list)`);
      }
    }

    // ── RULE 4: section emoji uniqueness ──────────────────────────────────
    if (sec) {
      const emoji = sectionEmoji(sec);
      const secName = sec.slice(emoji.length).trim();
      if (emoji) {
        // Solo advertir si el emoji de sección ES una bandera de país (regional indicators)
        // Los emojis decorativos (🌟, 📹, 🎬, etc.) son válidos como identificadores de sección
        const isFlagEmoji = /^\p{Regional_Indicator}\p{Regional_Indicator}/u.test(emoji);
        if (isFlagEmoji) {
          const secNameLower = secName.toLowerCase();
          const isCountrySection = ['muestra','comp.','casa','cortos','cine'].some(w => secNameLower.includes(w));
          if (!isCountrySection) {
            warnings.push(`"${title}": sección usa emoji de bandera como identificador: ${emoji}`);
          }
        }
      }
      if (emoji) {
        if (!emojiToSections[emoji]) emojiToSections[emoji] = new Set();
        emojiToSections[emoji].add(secName);
      }
      if (secName) {
        if (!sectionStrings[secName]) sectionStrings[secName] = new Set();
        sectionStrings[secName].add(sec);
      }
    }

    // ── RULE 5: required film fields ──────────────────────────────────────
    // Excepción CATÁLOGO: un bloque is_cortos marcado `unscheduled` con su
    // film_list vive en buscador/Explorar SIN día/hora — la jornada se asigna
    // cuando el festival publique la programación. No exige day/time/venue/day_order.
    const isUnscheduledCatalog = isCortos && film.unscheduled && film.film_list && film.film_list.length > 0;
    // Los obligatorios y sus formatos salen del CONTRATO, no de una lista escrita
    // aquí: si el canon cambia, cambia en un solo archivo y la doc se regenera.
    const _fest = fname.replace(/\.json$/, '');
    const _fin = (data.festivalEndStr || '');
    for (const [_k, _spec] of Object.entries(CONTRATO.campos)) {
      const _v = film[_k];
      const _ex = _exentoDe(_k, _fest, _fin);
      if (_spec.obligatorio && !isUnscheduledCatalog && (_v === undefined || _v === '')) {
        if (!_ex.exento) errors.push(`"${title}": campo '${_k}' requerido (contrato)`);
        continue;
      }
      if (_v === undefined || _v === null || _v === '') continue;
      if (_spec.formato && !new RegExp(_spec.formato).test(String(_v))) {
        const _msg = `"${title}": '${_k}' = ${JSON.stringify(String(_v).slice(0, 28))} no cumple el formato del contrato (${_spec.formato})`;
        if (_ex.vencida) errors.push(`${_msg} — la excepción venció el ${_ex.vencida.migrar_el}`);
        else if (!_ex.exento) errors.push(_msg);
        else _avisar(_ex, _k, _fest);
      }
      if (_spec.enum && !_spec.enum.includes(_v)) {
        errors.push(`"${title}": '${_k}' = ${JSON.stringify(_v)} fuera del contrato (${_spec.enum.join(' | ')})`);
      }
      if (_spec.tipo === 'boolean' && typeof _v !== 'boolean') {
        errors.push(`"${title}": '${_k}' debe ser booleano de verdad, llegó ${typeof _v} — la app compara con === true`);
      }
      if (_spec.tipo === 'number' && typeof _v !== 'number') {
        const _m = `"${title}": '${_k}' debe ser número, llegó ${typeof _v}`;
        if (_ex.vencida) errors.push(`${_m} — la excepción venció el ${_ex.vencida.migrar_el}`);
        else if (!_ex.exento) errors.push(_m);
      }
      if (_spec.exige && _v && !(Array.isArray(film[_spec.exige]) ? film[_spec.exige].length : film[_spec.exige])) {
        errors.push(`"${title}": '${_k}' exige '${_spec.exige}' no vacío (contrato)`);
      }
    }

    // ── RULE 5a: duplicado real (mismo título+día+hora+SEDE) ─────────────
    // La sede entra en la clave: en un festival multiciudad la misma obra se
    // proyecta a la misma hora en ciudades distintas y eso NO es duplicado
    // (FICDEH 2026: 14 casos legítimos en 11 ciudades). Duplicado real es
    // repetir título+día+hora en LA MISMA sede, que sí es imposible.
    if (film.title) {
      _seenTitles.add(film.title);
      const _slot = `${film.title}|${film.day||''}|${film.time||''}|${film.venue||''}`;
      if (_seenSlots.has(_slot)) errors.push(`GATE BLOQUEANTE: funcion duplicada (mismo título+día+hora+sede) — '${film.title.slice(0,55)}'`);
      else _seenSlots.add(_slot);
    }
    // ── RULE 5b: titulo en ALLCAPS ───────────────────────────────────────
    if (film.title) {
      const _ws = film.title.split(' ');
      const _uw = _ws.filter(w => w.length > 2 && /^[A-ZÁÉÍÓÚÑÜ]+$/.test(w));
      if (_uw.length >= 3) {
        errors.push(`GATE BLOQUEANTE: titulo ALLCAPS — '${film.title.slice(0,55)}' — convertir a Title Case`);
      }
    }
    // ── RULE 6: event without type:event ──────────────────────────────────
    if (!isEvent && !isCortos && !film.director) {
      const secLower = (sec || '').toLowerCase();
      const isEventSec = ['industry','taller','panel','workshop','masterclass',
        'clausura','inaugurac','conferencia','ceremonia','academia'].some(w => secLower.includes(w));
      if (isEventSec) {
        warnings.push(`"${title}": parece un evento (sección=${sec}) pero no tiene type:'event'`);
      }
    }

    // ── RULE 7: flags con non-flag emojis ────────────────────────────────
    if (!isEvent && !isCortos && film.flags) {
      for (const char of [...film.flags]) {
        if (NON_FLAG_EMOJIS.has(char)) {
          warnings.push(`"${title}": flags='${film.flags}' contiene emoji no-bandera '${char}'`);
          break;
        }
      }
    }

    // ── RULE 8: screenings[] integridad ──────────────────────────────────
    // Aplica a festivales con múltiples funciones por film (formato Tribeca/Jardín)
    if (Array.isArray(film.screenings) && film.screenings.length) {
      const _venues = data.venues || {};
      const _hasVenues = Object.keys(_venues).length > 0;
      film.screenings.forEach((s, i) => {
        if (!s.day && !s.date) {
          errors.push(`"${title}": screenings[${i}] no tiene 'day' ni 'date' — mostraría UNDEFINED en UI`);
        }
        if (_hasVenues && s.venue && !_venues[s.venue]) {
          warnings.push(`"${title}": screenings[${i}].venue "${s.venue}" no está en venues{}`);
        }
      });
    }
  }
  // ════════ CHECKS DE CORRUPCIÓN (revisión crítica Olhar — detectan dato MALO, no solo ausente) ════════
  // DEUDA DECLARADA de duplicados (19 ago 2026), y solo puede encoger. Al bajar
  // estos dos checks a film_list —hasta hoy solo miraban el nivel de función—
  // salieron a la luz duplicados VIEJOS en dos festivales ya publicados. No son
  // el error que buscamos; son deuda con nombre:
  //   · tercertiempo-2026 — «Raíces del Juego» y «Programa de cortos: Raíces
  //     del juego» son la MISMA sesión anotada dos veces, con dos archivos de
  //     afiche idénticos y títulos que difieren. Comparten pieza con razón.
  //   · tribeca-2026 — siete cortos llevan el mismo texto de relleno («Un
  //     cortometraje en competencia en Tribeca 2026»). Es un stub que nunca se
  //     completó, no una sinopsis robada. Se arregla cosechando sus sinopsis.
  // Un festival nuevo NO entra acá: si duplica, se corrige antes de publicar.
  const _DEUDA_DUP = new Set(['tercertiempo-2026', 'tribeca-2026']);
  const dup = [];
  // [posters-duplicados] ERROR — dos films con TÍTULO DISTINTO y misma URL de poster.
  // (El mismo título repetido = misma película en formato 1-entrada-por-función, legítimo.
  //  La comparación de título es case-insensitive: difiere solo en mayúsculas = mismo film.)
  // Recorre los DOS niveles: la función y cada obra de su film_list. Mirar solo
  // el nivel de arriba era el punto ciego — en CineAutopsia dos CORTOS llevaban
  // el mismo afiche y este check pasó en verde, porque los cortos viven dentro
  // de film_list. Lo vio Juan a ojo en una hoja de contactos, no el guardián.
  //
  // Y compara el CONTENIDO, no solo la ruta: los dos archivos se llamaban
  // distinto —squander.jpg y ahol-a-kek-...jpg— y eran byte a byte el mismo
  // JPEG. Comparar la cadena decía que estaba todo bien.
  {
    const norm = t => (t || '?').trim().toLowerCase();
    const todos = [];
    for (const f of films) {
      todos.push(f);
      if (Array.isArray(f.film_list)) for (const o of f.film_list) if (o && typeof o === 'object') todos.push(o);
    }
    const crypto = require('crypto');
    const huella = new Map();          // ruta local → hash del archivo
    const clave = p => {
      if (!p.startsWith('/assets/')) return p;
      if (huella.has(p)) return huella.get(p);
      let k = p;
      try { k = 'sha1:' + crypto.createHash('sha1').update(fs.readFileSync('.' + p)).digest('hex'); }
      catch (e) { /* si no abre, lo dice [poster-mirado]; acá vale la ruta */ }
      huella.set(p, k);
      return k;
    };
    // Una función de UNA sola obra comparte su afiche con ella: eso no es dato
    // corrupto, es la misma pieza. Se exime solo el par padre↔hija directa.
    const propio = new Set();
    for (const f of films) {
      const pf = (f.poster || '').trim();
      if (!pf) continue;
      for (const o of (f.film_list || [])) if (o && (o.poster || '').trim() === pf) propio.add(o);
    }
    // ARTE DE SECCIÓN: repetirse es su NATURALEZA, no corrupción. Es la pieza
    // que el festival usa en redes para una retrospectiva o un foco, y cubre a
    // la vez todos los programas de esa sección que no tienen afiche propio —
    // en Cinemancia 2026, 12 tarjetas con 6 artes. Se reconoce por el nombre
    // del archivo (`seccion-*`), que declara la intención: un póster de obra
    // nunca se llama así. Un duplicado accidental entre dos obras sigue siendo
    // error, que es lo que este gate nació para cazar.
    const esArteDeSeccion = (p) => /\/seccion-[^/]+$/.test(p);
    const seen = new Map();
    for (const f of todos) {
      const p = (f.poster || '').trim();
      if (!p || propio.has(f) || esArteDeSeccion(p)) continue;
      const k = clave(p);
      if (seen.has(k) && seen.get(k).n !== norm(f.title)) dup.push(`[posters-duplicados] "${(f.title||'?').slice(0,40)}" comparte poster con "${seen.get(k).t.slice(0,40)}" (título distinto) — dato corrupto`);
      else if (!seen.has(k)) seen.set(k, { n: norm(f.title), t: f.title || '?' });
    }
  }
  // ── Gates de posters (estrategia editorial, POSTERS.md §5/§8) ─────────────
  // Poster-holders = films top-level + cortos anidados en film_list.
  const posterHolders = [];
  for (const f of films) {
    posterHolders.push(f);
    if (Array.isArray(f.film_list)) for (const s of f.film_list) if (s && typeof s === 'object') posterHolders.push(s);
  }
  // [poster-source] ERROR — poster inline sin posterSource. Obliga a correr el
  // clasificador por aspecto (classify-posters.py) → ningún landscape se cuela
  // como portrait recortado ni ningún roto llega a producción sin detectarse.
  {
    for (const f of posterHolders) {
      const p = (f.poster || '').trim();
      if (p && !f.posterSource) {
        errors.push(`[poster-source] "${(f.title||'?').slice(0,40)}" tiene poster sin posterSource — correr: python3 scripts/classify-posters.py <id> --apply`);
      }
    }
  }
  // [poster-host] WARNING — poster http fuera de la whitelist (fuentes frágiles:
  // hotlink bloqueado / links muertos). Descargar y re-hostear en /assets/<id>/.
  {
    const ALLOWED = ['image.tmdb.org', 'd13jj08vfqimqg.cloudfront.net', 'supabase.co'];
    const check = (title, p) => {
      if (!p || !String(p).startsWith('http')) return;
      let host = ''; try { host = new URL(p).host; } catch { return; }
      if (!ALLOWED.some(a => host === a || host.endsWith('.' + a) || host.endsWith(a))) {
        warnings.push(`[poster-host] "${(title||'?').slice(0,40)}": host '${host}' fuera de whitelist (tmdb/cloudfront/supabase) — re-hostear en /assets/<id>/`);
      }
    };
    for (const f of posterHolders) check(f.title, f.poster);
    const maps = { ...(data.posters || {}), ...(data.customPosters || {}) };
    for (const [k, v] of Object.entries(maps)) check(k, v);
  }

  // [sinopsis-duplicada] ERROR — dos films con TÍTULO DISTINTO y misma synopsis o synopsis_en.
  // Mismo punto ciego que en [posters-duplicados]: hay que bajar a film_list.
  // En CineAutopsia dos PARES de cortos compartían sinopsis —la web del
  // festival publica el cuerpo de una obra bajo la ficha de otra— y este check
  // pasó en verde las tres veces que corrió.
  for (const fld of ['synopsis', 'synopsis_en']) {
    const norm = t => (t || '?').trim().toLowerCase();
    const todos = [];
    for (const f of films) {
      todos.push(f);
      if (Array.isArray(f.film_list)) for (const o of f.film_list) if (o && typeof o === 'object') todos.push(o);
    }
    const seen = new Map();
    for (const f of todos) {
      const s = (f[fld] || '').trim();
      if (!s) continue;
      if (seen.has(s) && seen.get(s).n !== norm(f.title)) dup.push(`[sinopsis-duplicada] "${(f.title||'?').slice(0,40)}" comparte ${fld} con "${seen.get(s).t.slice(0,40)}" (título distinto) — cross-contaminación`);
      else if (!seen.has(s)) seen.set(s, { n: norm(f.title), t: f.title || '?' });
    }
  }
  // Los duplicados son ERROR salvo en los festivales con deuda declarada, donde
  // quedan como WARNING para que sigan a la vista sin bloquear a los demás.
  if (dup.length) {
    if (_DEUDA_DUP.has(String(fname).replace(/\.json$/, ''))) warnings.push(...dup.map(d => d + ' [deuda declarada]'));
    else errors.push(...dup);
  }
  // [year-sospechoso] WARNING — year > festival_year+1 y el film no es clásico/retro declarado
  {
    const festYear = data.year || 0;
    for (const f of films) {
      if (typeof f.year === 'number' && festYear && f.year > festYear + 1) {
        const isClassic = /cl[aá]ssic|retro|classic/i.test(f.section || '');
        if (!isClassic) warnings.push(`[year-sospechoso] "${(f.title||'?').slice(0,40)}": year=${f.year} > ${festYear+1} y sección no es clásico/retro — posible outlier`);
      }
    }
  }
  // [slot-sin-agrupar] WARNING — ≥2 films distintos en el mismo (day,time,venue) sin is_cortos/is_programa
  {
    const slotMap = {};
    for (const f of films) {
      const isProg = !!(f.is_cortos || f.is_programa);
      const scr = (Array.isArray(f.screenings) && f.screenings.length)
        ? f.screenings : [{ day: f.day, time: f.time, venue: f.venue }];
      for (const s of scr) {
        const key = `${s.day||''}|${s.time||''}|${s.venue||''}`;
        if (key === '||') continue;
        (slotMap[key] = slotMap[key] || []).push({ t: f.title || '?', isProg });
      }
    }
    for (const [key, list] of Object.entries(slotMap)) {
      const uniq = [...new Set(list.map(x => x.t))];
      if (uniq.length >= 2 && !list.some(x => x.isProg)) {
        warnings.push(`[slot-sin-agrupar] ${uniq.length} films comparten slot (${key}) sin is_cortos/is_programa: ${uniq.slice(0,4).map(t=>t.slice(0,22)).join(', ')} — posible programa sin modelar`);
      }
    }
  }
  // [sala-mixta] ERROR — en un mismo (day,time,venue), unas entradas traen `sala`
  // y otras no, y TODAS son de formato corto. Esa es la firma de un programa de
  // cortos partido en dos: el anclaje agrupa por día|hora|sede|SALA, así que la
  // que trae sala queda fuera del bloque y la duración se cuenta de menos.
  // Cazado el 17 ago 2026 con FICDEH (17 AGO 17:30, Cinemateca de Bogotá): cinco
  // cortos que suman 86 min, «La independencia» con sala «Sala Capital» y las
  // otras cuatro sin sala → el bloque valía 66. Y no era solo el número: esa obra
  // no contaba como conflicto con sus compañeras, el planificador podía agendar
  // dos de la misma función, y el aviso de la ficha decía «va con otras 3 obras»
  // cuando eran cuatro.
  // NO se marca cuando hay largos o eventos en la mezcla: ahí dos salas distintas
  // a la misma hora en la misma sede son reales (una peli en Sala 2 y un taller en
  // Laboratorio 1 y 2), y dividir es lo correcto.
  {
    const CORTO_MAX = 45; // min — mismo umbral de formato corto que usa el catálogo
    // DEUDA AL INTRODUCIR LA REGLA (17 ago 2026). Estas cuatro funciones de FICDEH
    // ya estaban mal cuando se escribió el guardián, y el dato es del festival:
    // arreglarlas exige la guía oficial, no una corazonada. Se degradan a WARNING
    // para no bloquear a los demás chats con una deuda ajena; cualquier caso NUEVO
    // falla en duro. Se saca de acá en cuanto Onboarding confirme las salas.
    // VACÍO desde el 17 ago 2026: las cuatro funciones de FICDEH que nacieron
    // con este guardián quedaron resueltas contra la agenda oficial de la
    // Cinemateca de Bogotá, que publica la SALA que el sitio de FICDEH no da.
    // Cualquier caso nuevo falla en duro, que es como debe ser.
    const DEUDA_SALA = new Set([]);
    const _mins = (d) => parseInt(String(d || '').trim(), 10) || 0;
    const salaMap = {};
    for (const f of films) {
      const scr = (Array.isArray(f.screenings) && f.screenings.length)
        ? f.screenings : [{ day: f.day, time: f.time, venue: f.venue, sala: f.sala }];
      for (const s of scr) {
        const key = `${s.day||''}|${s.time||''}|${s.venue||''}`;
        if (key === '||') continue;
        (salaMap[key] = salaMap[key] || []).push({
          t: f.title || '?', sala: (s.sala || f.sala || '').trim(), min: _mins(f.duration) });
      }
    }
    for (const [key, list] of Object.entries(salaMap)) {
      if (list.length < 2) continue;
      // Se mira SOLO el subconjunto de formato corto. Exigir que TODA la función
      // fuera corta dejaba escapar el caso que originó el guardián: en la misma
      // sede y hora había además un taller de 180 min en otra sala —legítimo— y
      // eso bastaba para callar la mezcla entre los cinco cortos.
      const cortos = list.filter(x => x.min > 0 && x.min <= CORTO_MAX);
      if (cortos.length < 2) continue;
      const conSala = cortos.filter(x => x.sala);
      const sinSala = cortos.filter(x => !x.sala);
      if (!conSala.length || !sinSala.length) continue;
      const _msg = `[sala-mixta] en ${key} hay ${cortos.length} obras de formato corto y solo ${conSala.length} trae(n) sala `
        + `(${conSala.map(x => `${x.t.slice(0,20)}→"${x.sala}"`).join(', ')}) — el bloque se parte y la duración se cuenta de menos. `
        + `O la sala va en todas, o en ninguna.`;
      if (DEUDA_SALA.has(key)) warnings.push(_msg + ' [DEUDA conocida — pendiente de verificar contra la guía oficial]');
      else errors.push('GATE BLOQUEANTE ' + _msg);
    }
  }
  // [sinopsis-truncada] WARNING — exactamente 200 chars (huella de og:description truncada — trampa A2)
  for (const f of films) {
    for (const fld of ['synopsis', 'synopsis_en']) {
      if ((f[fld] || '').length === 200) warnings.push(`[sinopsis-truncada] "${(f.title||'?').slice(0,40)}": ${fld} tiene exactamente 200 chars — posible og:description truncada`);
    }
  }

  const venuesDef = data.venues || {};
  const venueKeys = Object.keys(venuesDef);
  for (const [vname, vdata] of Object.entries(venuesDef)) {
    const hasLat = vdata.lat !== null && vdata.lat !== undefined;
    const hasLng = vdata.lng !== null && vdata.lng !== undefined;
    if (hasLat && !hasLng) {
      errors.push(`venue "${vname}": tiene lat pero falta lng — geocoding incompleto. Correr scripts/geocode-venues.py`);
      totalErrors++;
    }
    if (!hasLat && hasLng) {
      errors.push(`venue "${vname}": tiene lng pero falta lat — geocoding incompleto`);
      totalErrors++;
    }
    if (!hasLat && !hasLng) {
      warnings.push(`venue "${vname}": sin coordenadas GPS — travelWarn usará tiempo por defecto`);
    }
  }

  // ── RULE 9: film.venue match en venues{} ─────────────────────────────────
  // Garantiza que el worker (exact match) y el main thread (prefix) coincidan
  const sortedKeys = [...venueKeys].sort((a,b) => b.length - a.length);
  function findVenueKey(v) {
    if (venuesDef[v]) return v;
    return sortedKeys.find(k => v.startsWith(k) || v.includes(k)) || null;
  }
  if (venueKeys.length > 0) {
    for (const film of data.films || []) {
      const v = film.venue;
      if (!v) continue;
      if (!venuesDef[v]) {
        // No exact match — check prefix
        const prefixMatch = findVenueKey(v);
        if (!prefixMatch) {
          errors.push(`"${(film.title||'?').slice(0,40)}": venue "${v}" no encontrado en venues{}`);
          totalErrors++;
        } else {
          warnings.push(`"${(film.title||'?').slice(0,40)}": venue "${v}" → prefix match a "${prefixMatch}" (worker usará prefix match)`);
        }
      }
    }
  }

  // ── RULE 9: i18n key parity ──────────────────────────────────────────────────
  // Los archivos es.json y en.json deben tener exactamente las mismas claves.
  // Una clave faltante produce strings en inglés cuando el usuario tiene ES.
  try {
    const repoRoot = path.join(__dirname, '..');
    const esPath = path.join(repoRoot, 'i18n', 'es.json');
    const enPath = path.join(repoRoot, 'i18n', 'en.json');
    if (fs.existsSync(esPath) && fs.existsSync(enPath)) {
      const esKeys = new Set(Object.keys(JSON.parse(fs.readFileSync(esPath, 'utf8'))));
      const enKeys = new Set(Object.keys(JSON.parse(fs.readFileSync(enPath, 'utf8'))));
      const missingInEs = [...enKeys].filter(k => !esKeys.has(k));
      const missingInEn = [...esKeys].filter(k => !enKeys.has(k));
      if (missingInEs.length) {
        errors.push(`i18n: ${missingInEs.length} claves en en.json faltan en es.json: ${missingInEs.slice(0,5).join(', ')}${missingInEs.length>5?'…':''}`);
      }
      if (missingInEn.length) {
        errors.push(`i18n: ${missingInEn.length} claves en es.json faltan en en.json: ${missingInEn.slice(0,5).join(', ')}${missingInEn.length>5?'…':''}`);
      }
    }
  } catch(e) { /* i18n files optional */ }

  // ── RULE 4 (cont): check emoji clashes ───────────────────────────────────
  for (const [emoji, secNames] of Object.entries(emojiToSections)) {
    if (secNames.size > 1) {
      const names = [...secNames];
      const allShared = names.every(isSharedAllowed);
      if (!allShared) {
        errors.push(`Emoji '${emoji}' compartido por secciones distintas: ${names.map(s=>`'${s}'`).join(', ')}`);
      }
      // Retrospectivas y ciclos pueden compartir emoji — solo warning
      else {
        warnings.push(`Emoji '${emoji}' compartido por subcategorías (permitido): ${names.map(s=>`'${s}'`).join(', ')}`);
      }
    }
  }

  // ── RULE 8: section string must be identical across all films ─────────────
  for (const [secName, strings] of Object.entries(sectionStrings)) {
    if (strings.size > 1) {
      errors.push(`Sección '${secName}' tiene strings distintos: ${[...strings].map(s=>`'${s}'`).join(' | ')}`);
    }
  }

  // ── [i18n-content-coverage] WARNING — cobertura de traducción de CONTENIDO ──
  // Detecta huecos de localización en el contenido del festival (no en strings de
  // UI). Solo WARNING, no bloquea. Reporta conteos por festival. No corrige nada.
  {
    const solos = (data.films || []).filter(f =>
      f.type !== 'event' && !f.is_cortos && !f.is_programa);
    const withSyn = solos.filter(f => f.synopsis);

    // (a) synopsis_es faltante cuando el origen no es español (synopsis_lang !== 'es')
    const needEs = withSyn.filter(f => (f.synopsis_lang || '') !== 'es');
    const missEs = needEs.filter(f => !f.synopsis_es);
    if (missEs.length) {
      const langs = [...new Set(needEs.map(f => f.synopsis_lang || '(no declarado)'))];
      const note = langs.length === 1 && langs[0] !== '(no declarado)'
        ? `origen ${langs[0]} — requiere traducción ES`
        : `synopsis_lang ${langs.join('/')} — verificar idioma de origen`;
      warnings.push(`[i18n-content-coverage] ${missEs.length}/${needEs.length} films sin synopsis_es (${note})`);
    } else if (needEs.length) {
      warnings.push(`[i18n-content-coverage] synopsis_es: 0/${needEs.length} films sin synopsis_es ✓`);
    }

    // (b) synopsis_en faltante cuando existe synopsis
    const missEn = withSyn.filter(f => !f.synopsis_en);
    if (missEn.length) {
      warnings.push(`[i18n-content-coverage] ${missEn.length}/${withSyn.length} films sin synopsis_en`);
    }

    // (c) title_en faltante cuando el festival usa title_en (tiene al menos uno)
    const festUsesTitleEn = solos.some(f => f.title_en);
    if (festUsesTitleEn) {
      const missTitleEn = solos.filter(f => !f.title_en);
      if (missTitleEn.length) {
        warnings.push(`[i18n-content-coverage] ${missTitleEn.length}/${solos.length} films sin title_en (el festival usa title_en)`);
      }
    }

    // (d) cobertura de section_en — informativo (no bloqueante).
    // Se compara la sección COMPLETA (string ES con emoji = clave del mapa) contra
    // SECTION_EN. Las que no tienen entrada son intencionales: inglés nativo
    // (Tribeca, "Impact Hits"/"Industry Days") o nombre de marca que se mantiene
    // en el idioma original (Mirada Paranaense, Costas, Campo indómito…). Por eso
    // es [info] y no un gap: no se inventan traducciones de marca.
    const secsFull = [...new Set((data.films || []).map(f => f.section || '').filter(Boolean))];
    const secsSinEn = secsFull.filter(s => !SECTION_EN_KEYS.has(s));
    const _cov = secsFull.length - secsSinEn.length;
    if (secsSinEn.length) {
      warnings.push(`[i18n-content-coverage] section_en: ${_cov}/${secsFull.length} secciones con display EN — ${secsSinEn.length} sin entrada (inglés nativo o marca intencional) [info]: ${secsSinEn.join(' · ')}`);
    } else if (secsFull.length) {
      warnings.push(`[i18n-content-coverage] section_en: ${secsFull.length}/${secsFull.length} secciones con display EN ✓`);
    }
  }

  // ── [synopsis-length] WARNING — sinopsis inusualmente larga ──
  // Sin tope DURO: Olhar/Tribeca tienen sinopsis largas por diseño (no hay regla
  // ~270 a nivel proyecto). Warn GENEROSO (>600) para cazar lo egregio — un copy
  // sin condensar o un dump de 1000+ chars — sin spamear. Silencioso cuando está
  // limpio (no infla el conteo de warnings; Ficmontañas, máx 269, da 0).
  const _SYN_MAX = 600;
  const _longSyn = [];
  for (const f of (data.films || [])) {
    for (const fld of ['synopsis', 'synopsis_en']) {
      const v = f[fld] || '';
      if (v.length > _SYN_MAX) _longSyn.push(`${(f.title || '?').slice(0, 36)}·${fld}=${v.length}`);
    }
  }
  if (_longSyn.length) {
    warnings.push(`[synopsis-length] ${_longSyn.length} sinopsis > ${_SYN_MAX} chars (revisar/condensar): ${_longSyn.slice(0, 4).join(', ')}${_longSyn.length > 4 ? ` +${_longSyn.length - 4} más` : ''}`);
  }

  // [event-kind-conocido] — todo event_kind del dato debe existir en LOS DOS mapas
  // de makeEventPoster; si no, la card cae al genérico «EVENTO» sin fallar nada.
  if (!KIND_MAPS_OK) {
    errors.push('[event-kind-conocido] no pude leer _kindMapES/_kindMapEN de src/view/components.js '
      + '— el check está CIEGO, no aprobando: revisar el parser antes de confiar en este resultado');
  } else {
    const _kindFalta = {};
    (data.films || []).forEach(f => {
      const k = f.event_kind;
      if (!k) return;
      const falta = ['es', 'en'].filter(l => !KIND_KEYS[l].has(k));
      if (falta.length) (_kindFalta[k] = _kindFalta[k] || { n: 0, langs: falta }).n++;
    });
    Object.entries(_kindFalta).forEach(([k, v]) => {
      errors.push(`[event-kind-conocido] event_kind "${k}" (${v.n} actividad(es)) no está en `
        + `_kindMap${v.langs.map(l => l.toUpperCase()).join('/')} — esas cards muestran el genérico `
        + `«EVENTO» en vez del nombre de la actividad. Agregar la clave en src/view/components.js`);
    });
  }

  // [short-ambiguo] — mismo short en dos ciudades (ver RULE 1c).
  const _porShort = {};
  Object.entries(data.venues || {}).forEach(([k, v]) => {
    const sh = (v && v.short) || k;
    const ci = (v && v.city) || '';
    (_porShort[sh] = _porShort[sh] || new Set()).add(ci);
  });
  const _ambiguos = Object.entries(_porShort).filter(([, c]) => c.size > 1)
    .map(([sh, c]) => `"${sh}" en ${[...c].join(' y ')}`);
  if (_ambiguos.length) {
    warnings.push(`[short-ambiguo] ${_ambiguos.length} nombre(s) corto(s) repetido(s) entre ciudades: `
      + _ambiguos.slice(0, 3).join(' · ') + (_ambiguos.length > 3 ? ` +${_ambiguos.length - 3} más` : '')
      + ' — el filtro los distingue por (ciudad, short), pero en pantalla son dos filas iguales: conviene diferenciar el short');
  }

  // [day-order-indice] — se reporta AGREGADO: 83 líneas sueltas no se leen, un
  // número contra su techo sí. Sobre el techo = error; en el techo = warning que
  // recuerda la deuda con su nombre.
  const _techo = DAY_ORDER_DEUDA[fname] || 0;
  if (_dayOrderMal.length > _techo) {
    errors.push(`[day-order-indice] ${_dayOrderMal.length} función(es) con day_order ≠ índice del día en dayKeys (techo ${_techo}). `
      + `day_order ordena ficha, Mi Plan, Programa y el plan generado: con el valor equivocado el orden miente sin dar error. `
      + `Ejemplos: ${_dayOrderMal.slice(0, 3).join(' · ')}${_dayOrderMal.length > 3 ? ` +${_dayOrderMal.length - 3} más` : ''}`);
  } else if (_dayOrderMal.length > 0) {
    warnings.push(`[day-order-indice] ${_dayOrderMal.length} función(es) con day_order fuera de índice (deuda conocida, techo ${_techo}). `
      + `Recalcular: day_order = dayKeys.indexOf(day). Al corregirlo, bajar el techo en DAY_ORDER_DEUDA.`);
  } else if (_techo > 0) {
    warnings.push(`[day-order-indice] deuda saldada (0 de ${_techo}) — bajá su techo a 0 en DAY_ORDER_DEUDA.`);
  }

  return { errors, warnings };
}

// ── Main ─────────────────────────────────────────────────────────────────────
const festivalsDir = path.join(__dirname, '..', 'festivals');
const targetId = process.argv[2]; // optional: validate single festival

const files = fs.readdirSync(festivalsDir)
  .filter(f => f.endsWith('.json') && !f.startsWith('_'))
  .filter(f => !targetId || f === targetId + '.json' || f === targetId);

if (files.length === 0) {
  console.error(`No se encontró festival: ${targetId}`);
  process.exit(1);
}

let totalErrors = 0;
let totalWarnings = 0;
const results = [];

for (const fname of files) {
  const fpath = path.join(festivalsDir, fname);
  let data;
  try {
    data = JSON.parse(fs.readFileSync(fpath, 'utf8'));
  } catch (e) {
    console.error(`✗ ${fname}: JSON inválido — ${e.message}`);
    totalErrors++;
    continue;
  }

  const { errors, warnings } = validateFestival(fname, data);

  // ── Poster coverage check ─────────────────────────────────────────────────
  // Un film tiene poster REAL (no generativo) si getFilmPoster (helpers.js) lo
  // resolvería a una imagen — es decir, si se cumple CUALQUIERA de la misma
  // prioridad del runtime: customPosters{} → posters{} → f.poster, todos
  // casados por título apóstrofe-normalizado (normKey). Antes el cálculo sumaba
  // f.poster + el COUNT crudo de posters{} e IGNORABA customPosters{}, por lo
  // que festivales que hospedan los posters ahí (FICCI, AFF, Cinemancia,
  // Tribeca) reportaban cobertura falsa-baja (FICCI 63% siendo 100%). Ver
  // docs/POSTERS.md — fuente única de la regla de cobertura.
  const _normKey = s => String(s || '').replace(/[‘’‚‛′ʼ]/g, "'");
  const _coveredKeys = new Set(
    [...Object.keys(data.customPosters || {}), ...Object.keys(data.posters || {})].map(_normKey)
  );
  const filmableFilms = (data.films || []).filter(f =>
    f.type !== 'event' && !f.is_cortos
  );
  const _isCovered = f => (f.poster && f.poster !== '') || _coveredKeys.has(_normKey(f.title));
  const totalPosters = filmableFilms.filter(_isCovered).length;
  if (filmableFilms.length > 0) {
    const _pPct = Math.round(totalPosters / filmableFilms.length * 100);
    if (totalPosters === 0) {
      errors.push(`GATE BLOQUEANTE: cobertura de poster 0% — ${filmableFilms.length} films sin imagen. Ejecutar scraping og:image + TMDB estricto.`);
    } else if (_pPct < 95) {
      warnings.push(`Cobertura de poster: ${_pPct}% (${totalPosters}/${filmableFilms.length}) — recomendado ≥95%. Revisar films sin imagen.`);
    }
  }

  // ── [poster-empty-film] — poster:"" explícito en film real ─────────────────
  // poster:"" (string vacío deliberado) en un film NO-programa/NO-cortos que
  // tampoco está en posters{}/customPosters{} = ERROR: lo deja en placeholder
  // generativo de forma silenciosa. Distinto de poster AUSENTE (festivales que
  // resuelven vía posters{}). La intención correcta es imagen real o no poner el
  // campo — nunca string vacío. Ver docs/POSTERS.md.
  for (const f of filmableFilms) {
    if (f.is_programa) continue;
    if (f.poster === '' && !_coveredKeys.has(_normKey(f.title))) {
      errors.push(`[poster-empty-film] '${(f.title || '').slice(0, 50)}' tiene poster:"" y no está en posters{}/customPosters{} — usar imagen real o quitar el campo (no string vacío).`);
    }
  }

  // ── Genre coverage ≥ 80% ─────────────────────────────────────────────────
  const _auditFilms = (data.films || []).filter(f => f.type !== 'event' && !f.is_cortos && !f.title?.startsWith('Shorts:'));
  const _withGenre  = _auditFilms.filter(f => f.genre && f.genre.trim());
  if (_auditFilms.length > 0) {
    const _gPct = Math.round(_withGenre.length / _auditFilms.length * 100);
    if (_gPct < 80) warnings.push(`Cobertura de género: ${_gPct}% (${_withGenre.length}/${_auditFilms.length}) — recomendado ≥80%. Ejecutar enriquecimiento TMDB estricto.`);
  }
  // ── Duration anomalies ────────────────────────────────────────────────────
  for (const f of (data.films || [])) {
    if (!f.duration && f.duration !== 0) continue;
    const _d = parseInt(String(f.duration).replace(/[^0-9]/g,''));
    if (!isNaN(_d) && (_d <= 0 || _d > 400)) warnings.push(`Duración anómala: '${(f.title||'').slice(0,40)}' — ${f.duration}`);
  }
  totalErrors += errors.length;
  totalWarnings += warnings.length;
  results.push({ fname, errors, warnings });
}

// ── Cross-festival checks ────────────────────────────────────────────────────
let hasIssues = false;
// storageKey debe ser único entre todos los festivales — colisión = datos mezclados.
// NOTA: festivales nuevos (sin config{} en JSON) tienen storageKey en FESTIVAL_CONFIG.
// Esta check solo cubre festivales legados con config{} en el JSON.
const storageKeyMap = {}; // storageKey → [fnames that use it]
for (const { fname } of results) {
  const fpath = path.join(festivalsDir, fname);
  try {
    const data = JSON.parse(fs.readFileSync(fpath, 'utf8'));
    const sk = (data.config || {}).storageKey;
    if (sk) {
      if (!storageKeyMap[sk]) storageKeyMap[sk] = [];
      storageKeyMap[sk].push(fname);
    }
  } catch (e) { /* JSON parse errors already reported above */ }
}
const skErrors = [];
for (const [sk, fnames] of Object.entries(storageKeyMap)) {
  if (fnames.length > 1) {
    skErrors.push(`storageKey '${sk}' compartida por: ${fnames.join(', ')}`);
    totalErrors++;
  }
}
if (skErrors.length) {
  hasIssues = true;
  console.log('\n── Cross-festival ──');
  for (const e of skErrors) console.log(`  ✗ ERROR:   ${e}`);
}

// ── [poster-editorial-unique] + Output (async: importa makeProgramPoster ESM) ──
(async () => {
  // [poster-editorial-unique] ERROR — dos programas (is_cortos/is_programa) del
  // MISMO festival que renderizan un poster editorial generativo IDÉNTICO.
  // Usa la función REAL makeProgramPoster (no una réplica) → cero falsos positivos:
  // si dos programas se ven iguales, es un error real. Solo aplica a programas SIN
  // poster propio (los que efectivamente rinden el editorial generativo).
  let makeProgramPoster = null;
  try {
    const _cu = require('url').pathToFileURL(path.join(__dirname, '..', 'src', 'view', 'components.js')).href;
    ({ makeProgramPoster } = await import(_cu));
  } catch (e) {
    console.error(`⚠ [poster-editorial-unique] no se pudo importar makeProgramPoster: ${e.message}`);
  }
  if (makeProgramPoster) {
    const _mockState = { snapshot: () => ({ FILMS: [] }) };
    for (const r of results) {
      let data;
      try { data = JSON.parse(fs.readFileSync(path.join(festivalsDir, r.fname), 'utf8')); } catch (e) { continue; }
      const progs = (data.films || []).filter(f => (f.is_cortos || f.is_programa) && !f.poster);
      const seen = {}; // svg → Set(títulos)
      for (const p of progs) {
        const svg = makeProgramPoster(_mockState, p.title, p.duration || '', p.section || '');
        (seen[svg] = seen[svg] || new Set()).add(p.title);
      }
      for (const titles of Object.values(seen)) {
        if (titles.size > 1) {
          r.errors.push(`[poster-editorial-unique] ${titles.size} programas con poster editorial idéntico: ${[...titles].join(' | ')}`);
          totalErrors++;
        }
      }
    }
  }

  // ── [poster-serie-consistente] — la serie se ve como serie ──────────────────
  // Regla de las portadas de playlists dinámicas de Apple («easily identified as
  // being part of a series»), adoptada 24 ago 2026 (auditoría Apple Music,
  // mejora #4): los programas numerados de una MISMA sección cuyo título solo
  // difiere en el ordinal deben renderizar la MISMA composición — solo cambia el
  // número. Hoy es cierto por plantilla; sin este check, nada lo protege: un
  // recorte de rótulo que aplique a unos y no a otros (pasó con el eco de
  // «Programa N»), una firma que entre en uno solo, o un color desviado rompen
  // la serie en silencio.
  // Es el INVERSO de [poster-editorial-unique]: aquel prohíbe idénticos entre
  // programas distintos; este exige idénticos-salvo-el-ordinal dentro de la serie.
  // NORMALIZACIÓN (para comparar sin falsos positivos): se enmascaran los
  // valores numéricos de atributos (coordenadas/tamaños — cambian legítimamente
  // si un ordinal es más ancho) y las corridas de dígitos del texto (el ordinal
  // mismo). Queda la estructura, el orden de elementos, los colores y las
  // strings — que es exactamente lo que define «la misma composición».
  if (makeProgramPoster) {
    const _mockState = { snapshot: () => ({ FILMS: [] }) };
    const _mascara = (svg) => decodeURIComponent(String(svg))
      .replace(/"[\d.\-]+"/g, '"#"')
      .replace(/\d+/g, 'N');
    for (const r of results) {
      let data;
      try { data = JSON.parse(fs.readFileSync(path.join(festivalsDir, r.fname), 'utf8')); } catch (e) { continue; }
      const progs = (data.films || []).filter(f => (f.is_cortos || f.is_programa) && !f.poster && /\d/.test(f.title || ''));
      const series = {};
      for (const p of progs) {
        const clave = (p.section || '') + '::' + String(p.title).replace(/\d+/g, 'N');
        (series[clave] = series[clave] || []).push(p);
      }
      for (const [clave, miembros] of Object.entries(series)) {
        if (miembros.length < 2) continue;
        const vistos = new Map(); // svg enmascarado → primer título
        for (const p of miembros) {
          const m = _mascara(makeProgramPoster(_mockState, p.title, p.duration || '', p.section || ''));
          if (!vistos.size) { vistos.set(m, p.title); continue; }
          if (!vistos.has(m)) {
            r.errors.push(`[poster-serie-consistente] la serie «${clave.split('::')[1]}» (${clave.split('::')[0]}) se rompe: «${p.title}» no comparte composición con «${[...vistos.values()][0]}»`);
            totalErrors++;
            break;
          }
        }
      }
    }
  }

  // ── Output ───────────────────────────────────────────────────────────────────
  for (const { fname, errors, warnings } of results) {
    if (errors.length === 0 && warnings.length === 0) {
      console.log(`✓ ${fname}`);
      continue;
    }
    hasIssues = true;
    console.log(`\n── ${fname} ──`);
    for (const e of errors)   console.log(`  ✗ ERROR:   ${e}`);
    for (const w of warnings) console.log(`  ⚠ WARNING: ${w}`);
  }

  console.log(`\n${'─'.repeat(50)}`);
  console.log(`Festivales: ${files.length} | Errores: ${totalErrors} | Warnings: ${totalWarnings}`);

  if (totalErrors > 0) {
    console.log('\n✗ Validación fallida — corregir errores antes de commit\n');
    process.exit(1);
  } else if (totalWarnings > 0) {
    console.log('\n⚠ Validación OK con warnings — revisar antes de publicar\n');
    process.exit(0);
  } else {
    console.log('\n✓ Validación completa — todos los festivales OK\n');
    process.exit(0);
  }
})();
