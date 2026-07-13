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
// TMDB_API_KEY: vacía en producción — las funciones de enriquecimiento degradan
// silenciosamente (el guard `if(!TMDB_API_KEY) return` corta). Para enriquecer
// posters localmente: setear key en scripts/enrich-festival.py (no commit al
// repo público). Rotar en https://www.themoviedb.org/settings/api
// Importada por controller/festival.js + poster-err.js (binding real, NO global).
export const TMDB_API_KEY = '';
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
  // Olhar de Cinema 2026 (orden curatorial)
  '🎬 Apertura','🏆 Competencia Brasil','🌍 Competencia Internacional','👁️ Nuevas Perspectivas','🌱 Pequeñas Perspectivas','🏞️ Mirada Paranaense','✨ Proyecciones Especiales','🎞️ Clásicos','🏛️ Retrospectiva','🌟 Clausura',
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
  // FICMontañas 2026 — colores por categoría (paleta del póster oficial)
  '🎬 Apertura & Galas':'#EF9F27',
  '🇨🇺 Cine Cubano':'#E24B4A',
  '🎞️ Retrospectiva Leonardo Favio':'#888780',
  '🏔️ Largometraje Cóndor Andino':'#378ADD',
  '🌎 Largometraje Latinoamericano':'#D85A30',
  '🌿 Cine al Natural':'#639922',
  '✨ Exhibiciones Especiales':'#5DCAA5',
  '💬 Conversatorios & Masterclass':'#7F77DD',
  '📽️ Cortometrajes':'#FAC775',
  '🎉 Eventos Especiales':'#E0418A',
};

// ── Display EN de secciones (solo display; la clave sigue siendo `section` ES) ─
// Mismo patrón que SECTION_COLORS/SECTION_ORDER_LIST: keyed por el string ES con
// emoji. Valor = etiqueta EN SIN emoji (igual que el output de _secLabel en ES).
// REGLAS:
//  · Olhar tiene sitio EN oficial → se usan SUS nombres (Opening Film, Young
//    Views, …). Verificado en olhardecinema.com.br/en.
//  · Secciones de marca / nombre propio se OMITEN → fallback al original ES:
//    Mirada Paranaense (Olhar); Costas, Casa Brasil, De Indias, Animación Porosa,
//    Retrospectiva ojoboca, (s)paces of Time (FICCI); Campo indómito…, Según la
//    palabra…, Fragmentos del cielo… (Cinemancia).
//  · Tribeca se omite entero: sus secciones ya están en inglés.
//  · "Impact Hits"/"Industry Days" (AFF) ya están en inglés → se omiten.
export const SECTION_EN = {
  '🔮 Largometrajes': 'Feature Films',
  '🌙 Cortometrajes': 'Short Films',
  '🌱 Raíces del Juego': 'Roots of the Game',
  '🧠 Juego Mental': 'Mind Game',
  '👟 El Rey Puma': 'El Rey Puma',
  '🏅 Más allá del Fútbol': 'Beyond Football',
  '🔥 Barrio Caliente': 'Barrio Caliente',
  '🚴 Pedal y Resistencia': 'Pedal & Resistance',
  '✍️ Fútbol Poético': 'Poetic Football',
  '🏟️ Refugio en la Cancha': 'Refuge on the Pitch',
  '💪 Contra Todo': 'Against All Odds',
  '🔟 El Diego': 'El Diego',
  '⚽ Juegan como Niñas': 'Juegan como Niñas',
  '🗺️ Territorios en Juego': 'Territories at Play',
  '🇧🇷 Brasil: Juego, memoria y pasión': 'Brazil: Game, Memory & Passion',
  '🏘️ Cinematecas Locales': 'Local Cinematheques',
  // Olhar de Cinema (nombres oficiales del sitio EN)
  '🎬 Apertura':'Opening Film',
  '🌟 Clausura':'Closing Film',
  '🏆 Competencia Brasil':'Brazilian Competition',
  '🌍 Competencia Internacional':'International Competition',
  '👁️ Nuevas Perspectivas':'New Perspectives',
  '🌱 Pequeñas Perspectivas':'Young Views',
  '🎞️ Clásicos':'Classics',
  '🏛️ Retrospectiva':'Retrospective',
  // Compartida Olhar + Cinemancia (mismo string con ✨)
  '✨ Proyecciones Especiales':'Special Screenings',
  // Cinemancia (sin sitio EN — traducción mecánica aprobada)
  '⭐ Inauguración':'Opening',
  '🎭 ¿Qué es la ficción?':'What Is Fiction?',
  '🎞️ Competencia de cortometrajes':'Short Film Competition',
  '🏆 Competencia central':'Main Competition',
  '💡 Iluminaciones':'Illuminations',
  '🌱 Competencia Nuevas Voces':'New Voices Competition',
  '🎬 Clausura':'Closing',
  // FICCI (sin sitio EN — traducción mecánica aprobada)
  '🏆 Comp. Cine en los Barrios':'Neighborhood Cinema Competition',
  '📽️ Retrospectiva FICCI Años 60':'FICCI 60s Retrospective',
  '🌎 Comp. Iberoamérica':'Ibero-American Competition',
  '🌍 Internacional':'International',
  '🇨🇴 Comp. Colombia':'Colombia Competition',
  '🇨🇭 Muestra Suiza':'Swiss Showcase',
  '🇪🇸 Muestra España':'Spain Showcase',
  '🇦🇷 Muestra Argentina':'Argentine Showcase',
  '🪶 Cine Indígena':'Indigenous Cinema',
  '✊ Cine Afro':'Afro Cinema',
  '📽️ Retrospectiva Ruth Beckermann':'Ruth Beckermann Retrospective',
  '🎖️ Tributo Ben Rivers':'Ben Rivers Tribute',
  '📽️ Retrospectiva Clásicos – Ópera Prima':'Classics Retrospective – First Films',
  '🌙 Medianoche':'Midnight',
  '⭐ Proyecciones Especiales':'Special Screenings',
  // AFF (solo competencias; Impact Hits / Industry Days ya en inglés)
  '🏆 Competencia Largometrajes':'Feature Film Competition',
  '🎬 Competencia Cortometrajes':'Short Film Competition',
  // Leviza (sin sitio EN — traducción mecánica aprobada)
  '🎬 Inauguración':'Opening',
  '🎞️ Proyecciones':'Screenings',
  '🏆 Competencia Nacional de Ficción':'National Fiction Competition',
  '⭐ Clausura':'Closing',
  '🎓 Talleres':'Workshops',
  // FICMontañas (sin sitio EN — traducción mecánica, pendiente pase Content Design)
  '🎬 Apertura & Galas':'Opening & Galas',
  '🇨🇺 Cine Cubano':'Cuban Cinema',
  '🎞️ Retrospectiva Leonardo Favio':'Leonardo Favio Retrospective',
  '🏔️ Largometraje Cóndor Andino':'Cóndor Andino Feature',
  '🌎 Largometraje Latinoamericano':'Latin American Feature',
  '🌿 Cine al Natural':'Nature Cinema',
  '✨ Exhibiciones Especiales':'Special Screenings',
  '💬 Conversatorios & Masterclass':'Talks & Masterclasses',
  '📽️ Cortometrajes':'Short Films',
  '🎉 Eventos Especiales':'Special Events',
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
    name:'FICCI 65',fullName:'Festival Internacional de Cine de Cartagena de Indias',city:'Cartagena',dates:'14–19 ABR',dates_en:'APR 14–19',year:2026,
    storageKey:'ficci65_',festivalStartStr:'2026-04-14T00:00:00',festivalEndStr:'2026-04-20T02:00:00',
    films:null,posters:null,lbSlugs:{}
  },
  'aff2026':{
    name:'AFF 2026',fullName:'Alternativa Film Festival',city:'Medellín',dates:'21–29 ABR',dates_en:'APR 21–29',year:2026,
    storageKey:'aff2026_',festivalStartStr:'2026-04-21T00:00:00',festivalEndStr:'2026-04-29T23:00:00',
    films:null,posters:null,lbSlugs:{}
  },
  'tribeca2026':{
    name:'Tribeca Festival',fullName:'Tribeca Festival',city:'New York',dates:'JUN 3–14',dates_en:'JUN 3–14',year:2026,timezoneOffset:'-04:00',
    storageKey:'tribeca2026_',festivalStartStr:'2026-06-03T00:00:00',festivalEndStr:'2026-06-14T23:59:00',
    films:null,posters:null,lbSlugs:{}
  },
  'cinemancia2025':{
    name:'Cinemancia 2025',fullName:'Cinemancia Festival Metropolitano de Cine',city:'Valle de Aburrá',dates:'11–20 SEP',dates_en:'SEP 11–20',year:2025,
    storageKey:'cinemancia2025_',festivalStartStr:'2025-09-11T00:00:00',festivalEndStr:'2025-09-20T23:00:00',
    group:'test', // datos preservados como guía para sep 2025 — no visible en splash
    films:null,posters:null,lbSlugs:{}
  },
  'leviza2026':{
    name:'Leviza - Festival de Cine y Audiovisuales',fullName:'Festival de Cine y Audiovisuales Leviza',shortName:'LEVIZA',
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
  },
  'olhar2026':{
    name:'Olhar de Cinema',fullName:'Olhar de Cinema – Festival Internacional de Curitiba',shortName:'OLHAR',
    city:'Curitiba',country:'BR',
    dates:'JUN 4–13',dates_en:'JUN 4–13',year:2026,timezoneOffset:'-03:00',
    storageKey:'olhar2026_',festivalStartStr:'2026-06-04T00:00:00',festivalEndStr:'2026-06-13T23:59:00',
    festivalDates:{'2026-06-04':'2026-06-04','2026-06-05':'2026-06-05','2026-06-06':'2026-06-06','2026-06-07':'2026-06-07','2026-06-08':'2026-06-08','2026-06-09':'2026-06-09','2026-06-10':'2026-06-10','2026-06-11':'2026-06-11','2026-06-12':'2026-06-12','2026-06-13':'2026-06-13'},
    days:[{k:'2026-06-04',d:4,lbl:'JUE'},{k:'2026-06-05',d:5,lbl:'VIE'},{k:'2026-06-06',d:6,lbl:'SÁB'},{k:'2026-06-07',d:7,lbl:'DOM'},{k:'2026-06-08',d:8,lbl:'LUN'},{k:'2026-06-09',d:9,lbl:'MAR'},{k:'2026-06-10',d:10,lbl:'MIÉ'},{k:'2026-06-11',d:11,lbl:'JUE'},{k:'2026-06-12',d:12,lbl:'VIE'},{k:'2026-06-13',d:13,lbl:'SÁB'}],
    dayKeys:['2026-06-04','2026-06-05','2026-06-06','2026-06-07','2026-06-08','2026-06-09','2026-06-10','2026-06-11','2026-06-12','2026-06-13'],
    dayShort:{'2026-06-04':'JUE 4','2026-06-05':'VIE 5','2026-06-06':'SÁB 6','2026-06-07':'DOM 7','2026-06-08':'LUN 8','2026-06-09':'MAR 9','2026-06-10':'MIÉ 10','2026-06-11':'JUE 11','2026-06-12':'VIE 12','2026-06-13':'SÁB 13'},
    dayShort_en:{'2026-06-04':'THU 4','2026-06-05':'FRI 5','2026-06-06':'SAT 6','2026-06-07':'SUN 7','2026-06-08':'MON 8','2026-06-09':'TUE 9','2026-06-10':'WED 10','2026-06-11':'THU 11','2026-06-12':'FRI 12','2026-06-13':'SAT 13'},
    dayLong:{'2026-06-04':'Jueves 4 de junio','2026-06-05':'Viernes 5 de junio','2026-06-06':'Sábado 6 de junio','2026-06-07':'Domingo 7 de junio','2026-06-08':'Lunes 8 de junio','2026-06-09':'Martes 9 de junio','2026-06-10':'Miércoles 10 de junio','2026-06-11':'Jueves 11 de junio','2026-06-12':'Viernes 12 de junio','2026-06-13':'Sábado 13 de junio'},
    prioLimit:5,
    films:null,posters:null,lbSlugs:{}
  },
  'tercertiempo2026': {
    name:'TercerTiempo Fest',fullName:'Tercer Tiempo Fest — Festival Mundial de Cine de Fútbol y Deportes',shortName:'TTF',
    city:'Bogotá',country:'CO',
    dates:'13–19 JUL',dates_en:'JUL 13–19',year:2026,timezoneOffset:'-05:00',
    storageKey:'tercertiempo2026_',festivalStartStr:'2026-07-13T00:00:00',festivalEndStr:'2026-07-19T23:00:00',
    festivalDates:{'2026-07-13':'2026-07-13','2026-07-14':'2026-07-14','2026-07-15':'2026-07-15','2026-07-16':'2026-07-16','2026-07-17':'2026-07-17','2026-07-18':'2026-07-18','2026-07-19':'2026-07-19'},
    days:[{k:'2026-07-13',d:13,lbl:'LUN'},{k:'2026-07-14',d:14,lbl:'MAR'},{k:'2026-07-15',d:15,lbl:'MIÉ'},{k:'2026-07-16',d:16,lbl:'JUE'},{k:'2026-07-17',d:17,lbl:'VIE'},{k:'2026-07-18',d:18,lbl:'SÁB'},{k:'2026-07-19',d:19,lbl:'DOM'}],
    dayKeys:['2026-07-13','2026-07-14','2026-07-15','2026-07-16','2026-07-17','2026-07-18','2026-07-19'],
    dayShort:{'2026-07-13':'LUN 13','2026-07-14':'MAR 14','2026-07-15':'MIÉ 15','2026-07-16':'JUE 16','2026-07-17':'VIE 17','2026-07-18':'SÁB 18','2026-07-19':'DOM 19'},
    dayShort_en:{'2026-07-13':'MON 13','2026-07-14':'TUE 14','2026-07-15':'WED 15','2026-07-16':'THU 16','2026-07-17':'FRI 17','2026-07-18':'SAT 18','2026-07-19':'SUN 19'},
    dayLong:{'2026-07-13':'Lunes 13 de julio','2026-07-14':'Martes 14 de julio','2026-07-15':'Miércoles 15 de julio','2026-07-16':'Jueves 16 de julio','2026-07-17':'Viernes 17 de julio','2026-07-18':'Sábado 18 de julio','2026-07-19':'Domingo 19 de julio'},
    prioLimit:5,eventPosterLabel:['EVENTO',''],
    films:null,posters:null,lbSlugs:{}
  },
  'fantasofest2026': {
    name:'FantasoFest',fullName:'FantasoFest — Muestra Iberoamericana de Cine Fantástico',shortName:'FANTASO',
    city:'Bogotá',country:'CO',
    dates:'13–19 JUL',dates_en:'JUL 13–19',year:2026,timezoneOffset:'-05:00',
    storageKey:'fantasofest2026_',festivalStartStr:'2026-07-13T00:00:00',festivalEndStr:'2026-07-19T23:00:00',
    festivalDates:{'2026-07-13':'2026-07-13','2026-07-14':'2026-07-14','2026-07-15':'2026-07-15','2026-07-16':'2026-07-16','2026-07-17':'2026-07-17','2026-07-18':'2026-07-18','2026-07-19':'2026-07-19'},
    days:[{k:'2026-07-13',d:13,lbl:'LUN'},{k:'2026-07-14',d:14,lbl:'MAR'},{k:'2026-07-15',d:15,lbl:'MIÉ'},{k:'2026-07-16',d:16,lbl:'JUE'},{k:'2026-07-17',d:17,lbl:'VIE'},{k:'2026-07-18',d:18,lbl:'SÁB'},{k:'2026-07-19',d:19,lbl:'DOM'}],
    dayKeys:['2026-07-13','2026-07-14','2026-07-15','2026-07-16','2026-07-17','2026-07-18','2026-07-19'],
    dayShort:{'2026-07-13':'LUN 13','2026-07-14':'MAR 14','2026-07-15':'MIÉ 15','2026-07-16':'JUE 16','2026-07-17':'VIE 17','2026-07-18':'SÁB 18','2026-07-19':'DOM 19'},
    dayShort_en:{'2026-07-13':'MON 13','2026-07-14':'TUE 14','2026-07-15':'WED 15','2026-07-16':'THU 16','2026-07-17':'FRI 17','2026-07-18':'SAT 18','2026-07-19':'SUN 19'},
    dayLong:{'2026-07-13':'Lunes 13 de julio','2026-07-14':'Martes 14 de julio','2026-07-15':'Miércoles 15 de julio','2026-07-16':'Jueves 16 de julio','2026-07-17':'Viernes 17 de julio','2026-07-18':'Sábado 18 de julio','2026-07-19':'Domingo 19 de julio'},
    prioLimit:4,
    films:null,posters:null,lbSlugs:{}
  },
  'ficmontanas2026':{
    name:'Ficmontañas',fullName:'Festival Internacional de Cine en las Montañas',shortName:'FICMONTAÑAS',
    city:'Salento',country:'CO',
    dates:'JUL 1–5',dates_en:'JUL 1–5',year:2026,timezoneOffset:'-05:00',
    storageKey:'ficmontanas2026_',festivalStartStr:'2026-06-30T00:00:00',festivalEndStr:'2026-07-05T22:00:00',
    festivalDates:{'2026-06-30':'2026-06-30','2026-07-01':'2026-07-01','2026-07-02':'2026-07-02','2026-07-03':'2026-07-03','2026-07-04':'2026-07-04','2026-07-05':'2026-07-05'},
    days:[{k:'2026-06-30',d:30,lbl:'MAR'},{k:'2026-07-01',d:1,lbl:'MIÉ'},{k:'2026-07-02',d:2,lbl:'JUE'},{k:'2026-07-03',d:3,lbl:'VIE'},{k:'2026-07-04',d:4,lbl:'SÁB'},{k:'2026-07-05',d:5,lbl:'DOM'}],
    dayKeys:['2026-06-30','2026-07-01','2026-07-02','2026-07-03','2026-07-04','2026-07-05'],
    dayShort:{'2026-06-30':'MAR 30','2026-07-01':'MIÉ 1','2026-07-02':'JUE 2','2026-07-03':'VIE 3','2026-07-04':'SÁB 4','2026-07-05':'DOM 5'},
    dayShort_en:{'2026-06-30':'TUE 30','2026-07-01':'WED 1','2026-07-02':'THU 2','2026-07-03':'FRI 3','2026-07-04':'SAT 4','2026-07-05':'SUN 5'},
    dayLong:{'2026-06-30':'Martes 30 de junio','2026-07-01':'Miércoles 1 de julio','2026-07-02':'Jueves 2 de julio','2026-07-03':'Viernes 3 de julio','2026-07-04':'Sábado 4 de julio','2026-07-05':'Domingo 5 de julio'},
    prioLimit:3,
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

// _DEFAULT_FEST_ID — festival más reciente por festivalEndStr (no por inserción).
// Deriva puro de FESTIVAL_CONFIG. p8 Step 6g: movido aquí desde main.js para que
// view/programa.js lo importe (lookups de NOTICES) sin ciclo. main.js lo importa.
export const _DEFAULT_FEST_ID=(()=>{
  const entries=Object.entries(FESTIVAL_CONFIG).filter(([,c])=>c.festivalEndStr);
  if(!entries.length) return Object.keys(FESTIVAL_CONFIG)[0]||'aff2026';
  return entries.sort((a,b)=>new Date(b[1].festivalEndStr)-new Date(a[1].festivalEndStr))[0][0];
})();

// ── Arquetipos de sección → color (POSTERS.md · paleta unificada) ─────────────
// 9 colores de marca, uno por arquetipo, reusados en los 7 festivales. El color
// SIGNIFICA (misma Competencia = mismo naranja en todos lados). Ver docs/POSTERS.md.
export const ARCHETYPE_COLORS = {
  'Clausura': '#E24B4A',
  'Apertura / Gala': '#EF9F27',
  'Competencia': '#D85A30',
  'Cortos / Programas': '#1D9E75',
  'Retrospectiva / Tributo': '#7F77DD',
  'Charlas / Industria': '#639922',
  'Muestra / País': '#378ADD',
  'Perspectivas / Miradas': '#5DCAA5',
  'Especiales / Eventos': '#E0418A'
};
// Cada sección de cada festival → su arquetipo. Generado por scripts/classify-posters
// (arquetipos) + decisiones de diseño. Sección nueva sin entrada → gate lo caza.
export const SECTION_ARCHETYPES = {
  '🔮 Largometrajes': 'Muestra / País',
  '🌙 Cortometrajes': 'Cortos / Programas',
  '🌱 Raíces del Juego': 'Perspectivas / Miradas',
  '🧠 Juego Mental': 'Perspectivas / Miradas',
  '👟 El Rey Puma': 'Apertura / Gala',
  '🏅 Más allá del Fútbol': 'Muestra / País',
  '🔥 Barrio Caliente': 'Muestra / País',
  '🚴 Pedal y Resistencia': 'Perspectivas / Miradas',
  '✍️ Fútbol Poético': 'Perspectivas / Miradas',
  '🏟️ Refugio en la Cancha': 'Muestra / País',
  '💪 Contra Todo': 'Perspectivas / Miradas',
  '🔟 El Diego': 'Retrospectiva / Tributo',
  '⚽ Juegan como Niñas': 'Apertura / Gala',
  '🗺️ Territorios en Juego': 'Muestra / País',
  '🇧🇷 Brasil: Juego, memoria y pasión': 'Muestra / País',
  '🏘️ Cinematecas Locales': 'Muestra / País',
  '⏳ (s)paces of Time': 'Perspectivas / Miradas',
  '✊ Cine Afro': 'Muestra / País',
  '✨ Exhibiciones Especiales': 'Especiales / Eventos',
  '✨ Impact Hits': 'Perspectivas / Miradas',
  '✨ Proyecciones Especiales': 'Especiales / Eventos',
  '✨ Spotlight+': 'Perspectivas / Miradas',
  '⭐ Clausura': 'Clausura',
  '⭐ Inauguración': 'Apertura / Gala',
  '⭐ Proyecciones Especiales': 'Especiales / Eventos',
  '⭐ Special Events': 'Especiales / Eventos',
  '🇦🇷 Muestra Argentina': 'Muestra / País',
  '🇧🇷 Casa Brasil': 'Muestra / País',
  '🇨🇭 Muestra Suiza': 'Muestra / País',
  '🇨🇴 Comp. Colombia': 'Competencia',
  '🇨🇺 Cine Cubano': 'Muestra / País',
  '🇪🇸 Muestra España': 'Muestra / País',
  '🌊 Costas': 'Muestra / País',
  '🌍 Competencia Internacional': 'Competencia',
  '🌍 Internacional': 'Muestra / País',
  '🌍 International Narrative Competition': 'Competencia',
  '🌎 Comp. Iberoamérica': 'Competencia',
  '🌎 Largometraje Latinoamericano': 'Muestra / País',
  '🌙 Escape From Tribeca': 'Especiales / Eventos',
  '🌙 Medianoche': 'Especiales / Eventos',
  '🌟 Clausura': 'Clausura',
  '🌟 Gala': 'Apertura / Gala',
  '🌱 Competencia Nuevas Voces': 'Competencia',
  '🌱 Pequeñas Perspectivas': 'Perspectivas / Miradas',
  '🌸 Fragmentos del cielo. El cine de Ewelina Rosińska': 'Retrospectiva / Tributo',
  '🌿 Campo indómito: Shinsuke Ogawa': 'Retrospectiva / Tributo',
  '🌿 Cine al Natural': 'Muestra / País',
  '🌿 Free Outdoor Screenings': 'Especiales / Eventos',
  '🎉 Eventos Especiales': 'Especiales / Eventos',
  '🎓 Talleres': 'Charlas / Industria',
  '🎖️ Tributo Ben Rivers': 'Retrospectiva / Tributo',
  '🎙️ Podcasts': 'Charlas / Industria',
  '🎞️ Clásicos': 'Retrospectiva / Tributo',
  '🎞️ Competencia de cortometrajes': 'Competencia',
  '🎞️ Proyecciones': 'Especiales / Eventos',
  '🎞️ Retrospectiva Leonardo Favio': 'Retrospectiva / Tributo',
  '🎨 Animación Porosa': 'Cortos / Programas',
  '🎨 Shorts Programs': 'Cortos / Programas',
  '🎬 Apertura': 'Apertura / Gala',
  '🎬 Apertura & Galas': 'Apertura / Gala',
  '🎬 Clausura': 'Clausura',
  '🎬 Competencia Cortometrajes': 'Competencia',
  '🎬 Inauguración': 'Apertura / Gala',
  '🎬 Spotlight Narrative': 'Perspectivas / Miradas',
  '🎭 ¿Qué es la ficción?': 'Perspectivas / Miradas',
  '🏅 Documentary Competition': 'Competencia',
  '🏆 Comp. Cine en los Barrios': 'Competencia',
  '🏆 Competencia Brasil': 'Competencia',
  '🏆 Competencia Largometrajes': 'Competencia',
  '🏆 Competencia Nacional de Ficción': 'Competencia',
  '🏆 Competencia central': 'Competencia',
  '🏆 U.S. Narrative Competition': 'Competencia',
  '🏔️ Largometraje Cóndor Andino': 'Muestra / País',
  '🏛️ De Indias': 'Muestra / País',
  '🏛️ Retrospectiva': 'Retrospectiva / Tributo',
  '🏞️ Mirada Paranaense': 'Muestra / País',
  '👁️ Nuevas Perspectivas': 'Perspectivas / Miradas',
  '👁️ Viewpoints': 'Perspectivas / Miradas',
  '💡 Iluminaciones': 'Perspectivas / Miradas',
  '💬 Conversatorios & Masterclass': 'Charlas / Industria',
  '📋 Industry Days': 'Charlas / Industria',
  '📖 Según la palabra. El cine de Olivier Godin': 'Retrospectiva / Tributo',
  '📱 NOW': 'Perspectivas / Miradas',
  '📹 Spotlight Documentary': 'Perspectivas / Miradas',
  '📺 TV': 'Especiales / Eventos',
  '📽️ Cortometrajes': 'Cortos / Programas',
  '📽️ Retrospectiva Clásicos – Ópera Prima': 'Retrospectiva / Tributo',
  '📽️ Retrospectiva FICCI Años 60': 'Retrospectiva / Tributo',
  '📽️ Retrospectiva Ruth Beckermann': 'Retrospectiva / Tributo',
  '📽️ Retrospectiva ojoboca': 'Retrospectiva / Tributo',
  '📽️ Reunions & Retrospectives': 'Retrospectiva / Tributo',
  '🗣️ Talks': 'Charlas / Industria',
  '🥇 Awards Screenings': 'Especiales / Eventos',
  '🪶 Cine Indígena': 'Muestra / País'
};