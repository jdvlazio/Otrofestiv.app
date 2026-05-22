// ── src/config.js — Fase 8 Step 1 (CABLEADO) ─────────────────────────────────
//
// ESTADO: importado por src/main.js (Step 1). Fuente única de verdad para
//   constantes de configuración + datos de festival. main.js hace
//   `import { … } from './config.js'` y ya no define estas constantes.
//
// CONTENIDO:
//   - Infra estática: URLs TMDB, constantes de scheduling, taxonomía de
//     secciones, mapa de colores.
//   - Festival-data: FESTIVAL_CONFIG / VENUES / NOTICES (movidas en Step 1 al
//     cablear → desaparece el riesgo de drift que existía durante el prep).
//
// EXCLUIDAS (viven en otros módulos, no aquí):
//   - TMDB_API_KEY → env-injected (vacío en source)
//   - _SB_URL / _SB_KEY → credenciales (publishable key)
//   - BUILD_VERSION → gestionado por bump-version.js (duplicar rompe el stamp)
//   - ICONS / LB_SVG → presentacionales → view/components.js (§12 del DAG)
//   - _DEFAULT_FEST_ID / DAY_KEYS / FESTIVAL_DATES → derivados / festival-state
//     (se quedan en main.js; leen FESTIVAL_CONFIG vía el import).
//
// NOTA: incluye un bug pre-existente conocido en SECTION_COLORS ('Talks'
//   duplicado) — NO se corrige aquí (el fix, si se decide, es trabajo aparte
//   con discusión de diseño).

// ── TMDB (URLs estáticas) ────────────────────────────────────────────────────
export const TMDB_IMG = "https://image.tmdb.org/t/p/w185";
export const TMDB_API_BASE = 'https://api.themoviedb.org/3';
export const TMDB_POSTER_BASE = 'https://image.tmdb.org/t/p/w500';
export const _POSTER_CACHE_PFX = 'orf_poster_v1_';

// ── Constantes numéricas de scheduling ───────────────────────────────────────
export const FESTIVAL_BUFFER = 15;        // min entre funciones: salida sala + intro siguiente
export const MAX_REMEMBERED_SLOTS = 5;
export const DEFAULT_DURATION_MIN = 90;

// ── Taxonomía de secciones (orden para el dropdown plano) ────────────────────
export const SECTION_ORDER_LIST = [
  // Con emoji
  '🌟 Gala','✨ Spotlight+','🏆 U.S. Narrative Competition',
  '🌍 International Narrative Competition','🏅 Documentary Competition',
  '🎬 Spotlight Narrative','📹 Spotlight Documentary','👁️ Viewpoints',
  '🌙 Escape From Tribeca','📽️ Reunions & Retrospectives','🗣️ Talks',
  '🎙️ Podcasts','⭐ Special Events','📱 NOW','📺 TV','🎨 Shorts Programs',
  '🌿 Free Outdoor Screenings',
  // Sin emoji (festivales legacy)
  'Gala','Spotlight+','U.S. Narrative Competition',
  'International Narrative Competition','Documentary Competition',
  'Spotlight Narrative','Spotlight Documentary','Viewpoints',
  'Escape From Tribeca','Reunions & Retrospectives','Storytellers',
  'Talks','Special Events','NOW','TV','Shorts Programs',
  'Free Outdoor Screenings','Shorts'
];

// ── Orden de categorías para el dropdown agrupado ────────────────────────────
export const FILM_CATEGORY_ORDER = ['Films','TV','Talks','NOW','Podcasts'];
export const FILM_CATEGORY_LABEL = {
  'Films':'Films','TV':'TV','Talks':'Talks','NOW':'NOW','Podcasts':'Podcasts'
};

// ── Mapa canónico de colores por sección ─────────────────────────────────────
// Consistente entre festivales: misma sección → mismo color.
export const SECTION_COLORS = {
  // Con emoji (Tribeca 2026+)
  '🌟 Gala':'#EF9F27',
  '✨ Spotlight+':'#5DCAA5',
  '🎬 Spotlight Narrative':'#7F77DD',
  '📹 Spotlight Documentary':'#1D9E75',
  '🏆 U.S. Narrative Competition':'#D85A30',
  '🌍 International Narrative Competition':'#378ADD',
  '🏅 Documentary Competition':'#639922',
  '👁️ Viewpoints':'#AFA9EC',
  '🌙 Escape From Tribeca':'#E24B4A',
  '📽️ Reunions & Retrospectives':'#888780',
  '🗣️ Talks':'#FAC775',
  '🎙️ Podcasts':'#85B7EB',
  '📱 NOW':'#5DCAA5',
  '📺 TV':'#B4B2A9',
  '⭐ Special Events':'#EF9F27',
  '🥇 Awards Screenings':'#BA7517',
  '🎨 Shorts Programs':'#1D9E75',
  '🌿 Free Outdoor Screenings':'#97C459',
  '✂️ Shorts':'#888780',
  // Sin emoji (AFF, FICCI, Cinemancia — compatibilidad)
  'Gala':'#EF9F27',
  'Spotlight+':'#5DCAA5',
  'Spotlight Narrative':'#7F77DD',
  'Spotlight Documentary':'#1D9E75',
  'U.S. Narrative Competition':'#D85A30',
  'International Narrative Competition':'#378ADD',
  'Documentary Competition':'#639922',
  'Viewpoints':'#AFA9EC',
  'Escape From Tribeca':'#E24B4A',
  'Reunions & Retrospectives':'#888780',
  'Storytellers':'#FAC775',
  'Talks':'#FAC775',
  'Talks':'#85B7EB',
  'NOW':'#5DCAA5',
  'TV':'#B4B2A9',
  'Special Events':'#EF9F27',
  'Awards Screenings':'#BA7517',
  'Shorts Programs':'#1D9E75',
  'Free Outdoor Screenings':'#97C459',
  'Shorts':'#888780',
};

// ── NOTICES ──────────────────────────────────────────────────────────────────
// date: 'YYYY-MM-DD' de la función original — el banner desaparece al día siguiente
// Para 'rescheduled': añadir newDay, newTime, newVenue
export const NOTICES=[
];

// ── FESTIVAL_CONFIG ────────────────────────────────────────────────────────
// Orden: cronológico ascendente por fecha de inicio.
// _DEFAULT_FEST_ID toma el festival más reciente por festivalEndStr.
//
// Campos opcionales importantes:
//   prioLimit  — máximo de funciones priorizadas (default: 5 si se omite)
//   group:'test' — aparece en sección separada del selector; omitir para festivales regulares
//   eventPosterLabel — ['LÍNEA1','LÍNEA2'] para el poster generativo de eventos
//
// Al agregar festival: también actualizar FESTIVALS en tools/enricher.html
export const FESTIVAL_CONFIG={
  // ── Bootstrap mínimo por festival ────────────────────────────────────────
  // Campos requeridos ANTES del fetch (usados por splash y _DEFAULT_FEST_ID):
  //   name, city, dates, dates_en, year → _renderSplashDropdown()
  //   storageKey                        → identificar localStorage
  //   festivalEndStr                    → _DEFAULT_FEST_ID
  // Todo lo demás (dayKeys, days, venues, posters, etc.) viene del JSON
  // y se mergea en loadFestival() — el JSON es la fuente única de verdad.
  'ficci65':{
    name:'FICCI 65',city:'Cartagena',dates:'14–19 ABR',dates_en:'APR 14–19',year:2026,
    storageKey:'ficci65_',festivalStartStr:'2026-04-14T00:00:00',festivalEndStr:'2026-04-20T02:00:00',
    films:null,posters:null,lbSlugs:{}
  },
  'aff2026':{
    name:'AFF 2026',city:'Medellín',dates:'21–29 ABR',dates_en:'APR 21–29',year:2026,
    storageKey:'aff2026_',festivalStartStr:'2026-04-21T00:00:00',festivalEndStr:'2026-04-29T23:00:00',
    films:null,posters:null,lbSlugs:{}
  },
  'tribeca2026':{
    name:'Tribeca Festival',city:'New York',dates:'JUN 3–14',dates_en:'JUN 3–14',year:2026,
    storageKey:'tribeca2026_',festivalStartStr:'2026-06-03T00:00:00',festivalEndStr:'2026-06-14T23:59:00',
    films:null,posters:null,lbSlugs:{}
  },
  'cinemancia2025':{
    name:'Cinemancia 2025',city:'Valle de Aburrá',dates:'11–20 SEP',dates_en:'SEP 11–20',year:2025,
    storageKey:'cinemancia2025_',festivalStartStr:'2025-09-11T00:00:00',festivalEndStr:'2025-09-20T23:00:00',
    group:'test', // datos preservados como guía para sep 2025 — no visible en splash
    films:null,posters:null,lbSlugs:{}
  },
  'leviza2026':{
    name:'Leviza - Festival de Cine y Audiovisuales',shortName:'LEVIZA',
    city:'Zapatoca',country:'CO',
    dates:'14–17 MAY',dates_en:'MAY 14–17',year:2026,timezoneOffset:'-05:00',
    storageKey:'leviza2026_',festivalStartStr:'2026-05-14T00:00:00',festivalEndStr:'2026-05-17T23:00:00',
    festivalDates:{'JUE 14':'2026-05-14','VIE 15':'2026-05-15','SÁB 16':'2026-05-16','DOM 17':'2026-05-17'},
    days:[{k:'JUE 14',d:14,lbl:'JUE'},{k:'VIE 15',d:15,lbl:'VIE'},{k:'SÁB 16',d:16,lbl:'SÁB'},{k:'DOM 17',d:17,lbl:'DOM'}],
    dayKeys:['JUE 14','VIE 15','SÁB 16','DOM 17'],
    dayShort:{'JUE 14':'JUE 14','VIE 15':'VIE 15','SÁB 16':'SÁB 16','DOM 17':'DOM 17'},
    dayShort_en:{'JUE 14':'THU 14','VIE 15':'FRI 15','SÁB 16':'SAT 16','DOM 17':'SUN 17'},
    prioLimit:5,
    films:null,posters:null,lbSlugs:{}
  }
};// Festival data loaded async from festivals/<id>.json via loadFestival()

// ── VENUES ───────────────────────────────────────────────────────────────────
export const VENUES={
  'Teatro Adolfo Mejía':{short:'Teatro Adolfo Mejía'},
  'Plaza Bocagrande':      {short:'Plaza Bocagrande'},
  'CC Caribe Plaza':    {short:'CC Caribe Plaza'},
  'Auditorio Nido':     {short:'Auditorio Nido'},
  'Plaza Proclamación': {short:'Plaza Proclamación'},
  'C. Convenciones':    {short:'C. de Convenciones'},
  'Unibac':             {short:'Unibac'},
  'AECID':              {short:'AECID'},
};
