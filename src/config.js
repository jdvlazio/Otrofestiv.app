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
// (El 'Talks' duplicado en SECTION_COLORS se removió en P2.1 — la 2ª entrada
//   #85B7EB ya ganaba, se eliminó la 1ª muerta sin cambio de render.)

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
  // ── FICDEH 2026 (11 ciudades, 12–19 AGO)
  '🧳 Largometraje de Ficción': 'International Fiction Feature',
  '🔍 Largometraje Documental Nacional': 'Colombian Documentary Feature',
  '🌍 Largometraje Documental Internacional': 'International Documentary Feature',
  '🪀 Cortometraje de Ficción Nacional': 'Colombian Fiction Short',
  '🚲 Cortometraje de Ficción Internacional': 'International Fiction Short',
  '🎙️ Cortometraje Documental Nacional': 'Colombian Documentary Short',
  '🏘️ Cine Comunitario Nacional': 'Community Cinema',
  '🕊️ Retrospectiva 10 Años del Acuerdo de Paz': '10 Years of the Peace Agreement',
  '🎟️ Invitadas': 'Guest Films',
  '💬 Charlas que Unen': 'Talks That Unite',
  '🛠️ Formación': 'Workshops',
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
  //   name, city, dates, dates_en, year, keyArt → _renderSplashRail()
  //   storageKey                        → identificar localStorage
  //   festivalEndStr                    → _DEFAULT_FEST_ID
  // keyArt es WRITE-ONCE: el SW cachea /assets/ cache-first para siempre (sobrevive
  // deploys, sin ?v=). Para cambiar el afiche de un festival, usar un filename NUEVO
  // (p.ej. tercertiempo2026-v2.jpg) y actualizar este path — nunca sobreescribir el
  // archivo in-place, o los usuarios recurrentes verán el afiche viejo indefinidamente.
  // Todo lo demás (dayKeys, days, venues, posters, etc.) viene del JSON
  // y se mergea en loadFestival() — el JSON es la fuente única de verdad.
  'ficci65':{
    name:'FICCI 65',fullName:'Festival Internacional de Cine de Cartagena de Indias',city:'Cartagena',country:'CO',dates:'14–19 ABR',dates_en:'APR 14–19',year:2026,timezoneOffset:'-05:00',
    storageKey:'ficci65_',festivalStartStr:'2026-04-14T00:00:00',festivalEndStr:'2026-04-20T02:00:00',
    keyArt:'/assets/keyart/ficci65.jpg',
    films:null,posters:null,lbSlugs:{}
  },
  'aff2026':{
    name:'AFF 2026',fullName:'Alternativa Film Festival',city:'Medellín',country:'CO',dates:'21–29 ABR',dates_en:'APR 21–29',year:2026,timezoneOffset:'-05:00',
    storageKey:'aff2026_',festivalStartStr:'2026-04-21T00:00:00',festivalEndStr:'2026-04-29T23:00:00',
    keyArt:'/assets/keyart/aff2026-v2.jpg',
    films:null,posters:null,lbSlugs:{}
  },
  'tribeca2026':{
    name:'Tribeca Festival',fullName:'Tribeca Festival',tagline:{es:'Festival de Cine de Tribeca',en:'Tribeca Film Festival'},city:'New York',country:'US',dates:'JUN 3–14',dates_en:'JUN 3–14',year:2026,timezoneOffset:'-04:00',
    storageKey:'tribeca2026_',festivalStartStr:'2026-06-03T00:00:00',festivalEndStr:'2026-06-14T23:59:00',
    keyArt:'/assets/keyart/tribeca2026.jpg',
    films:null,posters:null,lbSlugs:{}
  },
  'cinemancia2025':{
    name:'Cinemancia 2025',fullName:'Cinemancia Festival Metropolitano de Cine',city:'Valle de Aburrá',country:'CO',dates:'11–20 SEP',dates_en:'SEP 11–20',year:2025,
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
    keyArt:'/assets/keyart/leviza2026.jpg',
    films:null,posters:null,lbSlugs:{}
  },
  'olhar2026':{
    name:'Olhar de Cinema',displayName:'Olhar de Cinema',fullName:'Olhar de Cinema – Festival Internacional de Curitiba',shortName:'OLHAR',
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
    keyArt:'/assets/keyart/olhar2026-v2.jpg',
    films:null,posters:null,lbSlugs:{}
  },
  'tercertiempo2026': {
    name:'Tercer Tiempo Fest',displayName:'Tercer Tiempo Fest',fullName:'Tercer Tiempo Fest — Festival Mundial de Cine de Fútbol y Deportes',shortName:'TTF',
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
    keyArt:'/assets/keyart/tercertiempo2026-v2.jpg',
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
    keyArt:'/assets/keyart/fantasofest2026.jpg',
    films:null,posters:null,lbSlugs:{}
  },
  // FICDEH ocurre en 11 ciudades, así que `city` es el PAÍS. `country` va vacío
  // a propósito: el splash pinta «CIUDAD, PAÍS» y con ambos daría «COLOMBIA,
  // COLOMBIA». Además, al no coincidir con ninguna sede, el badge
  // venue-municipio y el filtro por ciudad se activan en las 11.
  'ficma2026': {
    name:'FICMA',fullName:'FICMA — Feria Internacional de Cine de Manizales',shortName:'FICMA',
    city:'Manizales',country:'CO',
    dates:'10–17 AGO',dates_en:'AUG 10–17',year:2026,timezoneOffset:'-05:00',
    keyArt:'/assets/keyart/ficma2026.jpg',
    storageKey:'ficma2026_',festivalStartStr:'2026-08-10T00:00:00',festivalEndStr:'2026-08-17T23:59:00',
    festivalDates:{'2026-08-10':'2026-08-10','2026-08-11':'2026-08-11','2026-08-12':'2026-08-12','2026-08-13':'2026-08-13','2026-08-14':'2026-08-14','2026-08-15':'2026-08-15','2026-08-16':'2026-08-16','2026-08-17':'2026-08-17'},
    days:[{k:'2026-08-10',d:10,lbl:'LUN'},{k:'2026-08-11',d:11,lbl:'MAR'},{k:'2026-08-12',d:12,lbl:'MIÉ'},{k:'2026-08-13',d:13,lbl:'JUE'},{k:'2026-08-14',d:14,lbl:'VIE'},{k:'2026-08-15',d:15,lbl:'SÁB'},{k:'2026-08-16',d:16,lbl:'DOM'},{k:'2026-08-17',d:17,lbl:'LUN'}],
    dayKeys:['2026-08-10','2026-08-11','2026-08-12','2026-08-13','2026-08-14','2026-08-15','2026-08-16','2026-08-17'],
    dayShort:{'2026-08-10':'LUN 10','2026-08-11':'MAR 11','2026-08-12':'MIÉ 12','2026-08-13':'JUE 13','2026-08-14':'VIE 14','2026-08-15':'SÁB 15','2026-08-16':'DOM 16','2026-08-17':'LUN 17'},
    dayShort_en:{'2026-08-10':'MON 10','2026-08-11':'TUE 11','2026-08-12':'WED 12','2026-08-13':'THU 13','2026-08-14':'FRI 14','2026-08-15':'SAT 15','2026-08-16':'SUN 16','2026-08-17':'MON 17'},
    dayLong:{'2026-08-10':'Lunes 10 de agosto','2026-08-11':'Martes 11 de agosto','2026-08-12':'Miércoles 12 de agosto','2026-08-13':'Jueves 13 de agosto','2026-08-14':'Viernes 14 de agosto','2026-08-15':'Sábado 15 de agosto','2026-08-16':'Domingo 16 de agosto','2026-08-17':'Lunes 17 de agosto'},
    prioLimit:4,
    // El subtítulo expande la sigla, no repite el nombre: «FICMA» no le dice
    // nada a quien llega de fuera. El lema de la edición —«El jardín de las
    // cosas perdidas»— se lee en el afiche, que está justo encima; ponerlo aquí
    // gastaba la única línea de contexto que tenemos. Mismo criterio que FICDEH.
    tagline:'Feria Internacional de Cine de Manizales',
    films:null,posters:null,lbSlugs:{}
  },
  'ficdeh2026': {
    name:'FICDEH',fullName:'FICDEH — Festival Internacional de Cine por los Derechos Humanos',shortName:'FICDEH',
    city:'Colombia',country:'',
    dates:'12–19 AGO',dates_en:'AUG 12–19',year:2026,timezoneOffset:'-05:00',
    keyArt:'/assets/keyart/ficdeh2026-v2.jpg',
    storageKey:'ficdeh2026_',festivalStartStr:'2026-08-12T00:00:00',festivalEndStr:'2026-08-19T23:00:00',
    festivalDates:{'2026-08-12':'2026-08-12','2026-08-13':'2026-08-13','2026-08-14':'2026-08-14','2026-08-15':'2026-08-15','2026-08-16':'2026-08-16','2026-08-17':'2026-08-17','2026-08-18':'2026-08-18','2026-08-19':'2026-08-19'},
    days:[{k:'2026-08-12',d:12,lbl:'MIÉ'},{k:'2026-08-13',d:13,lbl:'JUE'},{k:'2026-08-14',d:14,lbl:'VIE'},{k:'2026-08-15',d:15,lbl:'SÁB'},{k:'2026-08-16',d:16,lbl:'DOM'},{k:'2026-08-17',d:17,lbl:'LUN'},{k:'2026-08-18',d:18,lbl:'MAR'},{k:'2026-08-19',d:19,lbl:'MIÉ'}],
    dayKeys:['2026-08-12','2026-08-13','2026-08-14','2026-08-15','2026-08-16','2026-08-17','2026-08-18','2026-08-19'],
    dayShort:{'2026-08-12':'MIÉ 12','2026-08-13':'JUE 13','2026-08-14':'VIE 14','2026-08-15':'SÁB 15','2026-08-16':'DOM 16','2026-08-17':'LUN 17','2026-08-18':'MAR 18','2026-08-19':'MIÉ 19'},
    dayShort_en:{'2026-08-12':'WED 12','2026-08-13':'THU 13','2026-08-14':'FRI 14','2026-08-15':'SAT 15','2026-08-16':'SUN 16','2026-08-17':'MON 17','2026-08-18':'TUE 18','2026-08-19':'WED 19'},
    dayLong:{'2026-08-12':'Miércoles 12 de agosto','2026-08-13':'Jueves 13 de agosto','2026-08-14':'Viernes 14 de agosto','2026-08-15':'Sábado 15 de agosto','2026-08-16':'Domingo 16 de agosto','2026-08-17':'Lunes 17 de agosto','2026-08-18':'Martes 18 de agosto','2026-08-19':'Miércoles 19 de agosto'},
    prioLimit:4,eventPosterLabel:['EVENTO',''],
    tagline:'Festival Internacional de Cine por los Derechos Humanos', // espacios duros: fuerzan el corte en «Cine / por los Derechos Humanos»
    ticketing_model:'mixed', // entrada libre en casi todo + boletería en la Cinemateca (ticket_url por función). No va en el JSON: ahí el validador exigiría un ticket_url de raíz y FICDEH no tiene boletería única
    films:null,posters:null,lbSlugs:{}
  },
  'finca2026': {
    // Sin `priority`. Lo llevó unos días para darle visibilidad ante una nota de
    // prensa, y se retira: la REGLA MADRE del splash es la fecha —primero el que
    // empieza antes— y una excepción editorial permanente la erosiona (Juan,
    // 9 ago 2026). Para un empujón puntual, ponerlo y quitarlo; nunca dejarlo.
    name:'FINCA',fullName:'FINCA — Festival Internacional de Cine Ambiental',shortName:'FINCA',
    city:'Buenos Aires',country:'AR',
    dates:'12–19 AGO',dates_en:'AUG 12–19',year:2026,timezoneOffset:'-03:00',
    storageKey:'finca2026_',festivalStartStr:'2026-08-12T00:00:00',festivalEndStr:'2026-08-19T23:30:00',
    festivalDates:{'2026-08-12':'2026-08-12','2026-08-13':'2026-08-13','2026-08-14':'2026-08-14','2026-08-15':'2026-08-15','2026-08-16':'2026-08-16','2026-08-17':'2026-08-17','2026-08-18':'2026-08-18','2026-08-19':'2026-08-19'},
    days:[{k:'2026-08-12',d:12,lbl:'MIÉ'},{k:'2026-08-13',d:13,lbl:'JUE'},{k:'2026-08-14',d:14,lbl:'VIE'},{k:'2026-08-15',d:15,lbl:'SÁB'},{k:'2026-08-16',d:16,lbl:'DOM'},{k:'2026-08-17',d:17,lbl:'LUN'},{k:'2026-08-18',d:18,lbl:'MAR'},{k:'2026-08-19',d:19,lbl:'MIÉ'}],
    dayKeys:['2026-08-12','2026-08-13','2026-08-14','2026-08-15','2026-08-16','2026-08-17','2026-08-18','2026-08-19'],
    dayShort:{'2026-08-12':'MIÉ 12','2026-08-13':'JUE 13','2026-08-14':'VIE 14','2026-08-15':'SÁB 15','2026-08-16':'DOM 16','2026-08-17':'LUN 17','2026-08-18':'MAR 18','2026-08-19':'MIÉ 19'},
    dayShort_en:{'2026-08-12':'WED 12','2026-08-13':'THU 13','2026-08-14':'FRI 14','2026-08-15':'SAT 15','2026-08-16':'SUN 16','2026-08-17':'MON 17','2026-08-18':'TUE 18','2026-08-19':'WED 19'},
    dayLong:{'2026-08-12':'Miércoles 12 de agosto','2026-08-13':'Jueves 13 de agosto','2026-08-14':'Viernes 14 de agosto','2026-08-15':'Sábado 15 de agosto','2026-08-16':'Domingo 16 de agosto','2026-08-17':'Lunes 17 de agosto','2026-08-18':'Martes 18 de agosto','2026-08-19':'Miércoles 19 de agosto'},
    prioLimit:4,eventPosterLabel:['ACTIVIDAD',''],
    keyArt:'/assets/keyart/finca2026.jpg',
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
    keyArt:'/assets/keyart/ficmontanas2026-v2.jpg',
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
  // FINCA 2026 — la sección ES el eje temático que define el propio festival
  // (columna «Sección» de su Excel), no la competencia. Los 3 bloques de cortos
  // mezclan hasta 4 ejes en una misma función, así que conservan el nombre de
  // competencia del festival. La competencia de cada obra vive en `competencia`.
  '⛏️ Extractivismos': 'Perspectivas / Miradas',
  '🪶 Pueblos Originarios': 'Perspectivas / Miradas',
  '🏚️ Foco Tierra y Techo': 'Perspectivas / Miradas',
  '🌿 Biodiversidad': 'Perspectivas / Miradas',
  '✊ FICDH - Derechos Humanos': 'Perspectivas / Miradas',
  '💧 Agua': 'Perspectivas / Miradas',
  '🌾 Soberanía Alimentaria': 'Perspectivas / Miradas',
  '🌡️ Justicia Climática': 'Perspectivas / Miradas',
  '🌋 Cortos Internacionales': 'Cortos / Programas',
  '🐝 FINQUITA · Infancias': 'Cortos / Programas',
  '🌱 Actividades': 'Especiales / Eventos',
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
  '🪶 Cine Indígena': 'Muestra / País',
  // ── FICDEH 2026 (11 ciudades, 12–19 AGO)
  '🧳 Largometraje de Ficción': 'Competencia',
  '🔍 Largometraje Documental Nacional': 'Competencia',
  '🌍 Largometraje Documental Internacional': 'Competencia',
  '🪀 Cortometraje de Ficción Nacional': 'Cortos / Programas',
  '🚲 Cortometraje de Ficción Internacional': 'Cortos / Programas',
  '🎙️ Cortometraje Documental Nacional': 'Cortos / Programas',
  '🏘️ Cine Comunitario Nacional': 'Perspectivas / Miradas',
  '🕊️ Retrospectiva 10 Años del Acuerdo de Paz': 'Retrospectiva / Tributo',
  '🎟️ Invitadas': 'Especiales / Eventos',
  '💬 Charlas que Unen': 'Charlas / Industria',
  '🛠️ Formación': 'Charlas / Industria',
  // FICMA 17 — programa por TEMAS de coleccionismo y ciudad, no por competencias.
  // Las dos de estrenos son la cabecera y llevan colores distintos entre sí; las
  // temáticas comparten «Perspectivas», salvo antigüedades y numismática, que
  // miran al pasado y toman el color de retrospectiva.
  '🎬 Estrenos Nacionales': 'Competencia',
  '🌍 Estrenos Internacionales': 'Muestra / País',
  '🕊️ En alianza con el FICDEH': 'Especiales / Eventos',
  '🎨 Arte': 'Perspectivas / Miradas',
  '🥫 Arte Pop': 'Perspectivas / Miradas',
  '💥 Cómic': 'Perspectivas / Miradas',
  '🎵 Música': 'Perspectivas / Miradas',
  '🏗️ Arquitectura': 'Perspectivas / Miradas',
  '🕰️ Antigüedades': 'Retrospectiva / Tributo',
  '🪙 Numismática': 'Retrospectiva / Tributo',
  '🌱 Medio Ambiente': 'Perspectivas / Miradas',
  '🏛️ Red de Museos': 'Especiales / Eventos',
  // Franja Académica de FICMA — el festival la divide en talleres y charlas.
  '🛠️ Talleres': 'Charlas / Industria',
  '💬 Charlas': 'Charlas / Industria',

  // Cinemancia 2026 (sexta edición). Cinco secciones continúan de Cinemancia
  // 2025 y NO aparecen aquí porque ya estaban con la misma clave: 🏆
  // Competencia central, 🎞️ Competencia de cortometrajes, 💡 Iluminaciones,
  // 🌱 Competencia Nuevas Voces y ✨ Proyecciones Especiales. Las dos últimas
  // se rotulan en Title Case como en 2025 (decisión de Juan, 9 ago 2026)
  // aunque el PDF de este año las escriba en minúscula.
  '⭐ Función inaugural': 'Apertura / Gala',
  '🎬 Función de clausura': 'Clausura',
  '🔺 Programa 1. El espesor de las formas': 'Cortos / Programas',
  '👁️ Programa 2. Teoremas sobre la mirada': 'Cortos / Programas',
  '⚗️ Alquimia de la luz. El cine de Luciana Decker': 'Retrospectiva / Tributo',
  '🃏 Carta blanca': 'Perspectivas / Miradas',
  '🌷 La primavera llega para los que esperan. El cine de José Luis Torres Leiva': 'Retrospectiva / Tributo',
  '🌡️ Febril incisión. El cine de Thomas Fürhapter': 'Retrospectiva / Tributo',
  '🖤 Sick and Dirty. Curaduría de Michael Koresky': 'Perspectivas / Miradas',
  '📼 La sutil materia. Sergio Navarro': 'Retrospectiva / Tributo',
  '🇦🇷 Historia(s) del cine: Argentina. Curaduría de José Miccio': 'Muestra / País',
  '🏆 Competencia Central': 'Competencia',
  '🎞️ Competencia de Cortometrajes': 'Competencia',
};

// mergeFestivalSections(sections) — DATA-DRIVEN (P2.2): un festival declara sus
// secciones en SU JSON (`sections`), no en los 4 mapas de arriba. loadFestival
// llama a esto al cargar → mergea la metadata del festival en los mapas globales,
// SIN tocar los consumidores (siguen leyendo SECTION_COLORS/EN/ARCHETYPES/ORDER_LIST).
// Un festival nuevo = su bloque `sections` en el JSON, cero código.
//   sections: { "🎃 Nombre": { en, color, archetype, order } }
//   - archetype: CLAVE del color (paleta unificada ARCHETYPE_COLORS, POSTERS.md) +
//     del póster editorial. Usar una de las keys existentes de SECTION_ARCHETYPES.
//   - color: SOLO fallback para secciones sin archetype (_sectionColor prioriza el
//     color del arquetipo). en: label EN. order: posición en el programa.
// Idempotente (se puede llamar en cada load). Los festivales viejos sin `sections`
// conservan sus entradas hardcodeadas de arriba (no se re-onboardean).
// COUNTRY_NAMES — ISO-3166 alpha-2 → nombre localizado, para la línea CIUDAD, PAÍS del
// splash. Set acotado a los países con festival (crece 1 línea por país nuevo). Se eligió
// texto sobre bandera: 100% responsive y consistente en todo dispositivo (los emoji de
// bandera no renderizan en Windows; ver deuda opcional de migrar a SVG por ISO).
// Crece UNA línea por país nuevo, y esa línea es fácil de olvidar: FINCA entró con
// country:'AR' sin su entrada acá y el splash mostró «BUENOS AIRES» a secas durante
// toda su publicación — countryName devuelve '' con un ISO desconocido, así que
// festivalLocationLabel se queda con la ciudad y no hay error en ningún lado.
// Lo cazó Juan mirando el splash (9 ago 2026). El guardián [pais-conocido] de
// validate.py exige ahora que todo `country` de FESTIVAL_CONFIG exista en esta tabla.
export const COUNTRY_NAMES = {
  CO: { es:'Colombia',       en:'Colombia' },
  BR: { es:'Brasil',         en:'Brazil' },
  US: { es:'Estados Unidos', en:'United States' },
  AR: { es:'Argentina',      en:'Argentina' },
};
// countryName(iso, lang) — nombre del país o '' si no hay dato / ISO desconocido. Puro.
export function countryName(iso, lang='es'){
  const e = iso && COUNTRY_NAMES[iso];
  return e ? (e[lang] ?? e.es) : '';
}

// festivalLocationLabel — la línea de UBICACIÓN del splash (dueño único).
// Regla: la ciudad NUNCA se repite con el país. Un festival NACIONAL declara el
// país en `city` porque no tiene una sede única —FICDEH 2026 son 11 ciudades—, y
// entonces la línea salía «COLOMBIA, COLOMBIA»: eso no es una ubicación, es un
// error de lectura.
// Se compara contra TODOS los nombres del país, no solo el del idioma activo:
// con la interfaz en inglés, `city:'Brasil'` y país «Brazil» son el mismo lugar
// escrito distinto, y la repetición volvería por la puerta de atrás. La
// comparación ignora acentos y mayúsculas por el mismo motivo.
export function festivalLocationLabel(cfg, lang='es'){
  const ciudad = cfg && cfg.city ? String(cfg.city).trim() : '';
  if(!ciudad) return '';                     // sin ciudad no se inventa el país
  const iso = cfg && cfg.country;
  const pais = countryName(iso, lang);
  if(!pais) return ciudad;
  const norm = s => String(s).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
  const esElPais = Object.values(COUNTRY_NAMES[iso]||{}).some(p=>norm(p)===norm(ciudad));
  return esElPais ? ciudad : `${ciudad}, ${pais}`;
}

export function mergeFestivalSections(sections){
  if(!sections || typeof sections!=='object') return;
  // Insertar en ORDER_LIST respetando `order` (los que ya están no se duplican).
  const byOrder=Object.entries(sections).sort((a,b)=>(a[1]?.order??9999)-(b[1]?.order??9999));
  for(const [name, meta] of byOrder){
    if(!meta) continue;
    if(meta.color)     SECTION_COLORS[name]=meta.color;
    if(meta.en)        SECTION_EN[name]=meta.en;
    if(meta.archetype) SECTION_ARCHETYPES[name]=meta.archetype;
    if(!SECTION_ORDER_LIST.includes(name)) SECTION_ORDER_LIST.push(name);
  }
}