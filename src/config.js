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
import { aplicarFichas, fichasGuardadas } from './fichas.js';

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
// FESTIVAL_QA_MIN — los minutos ESTIMADOS de un Q&A. Estaba suelto en tres
// lugares (effectiveDuration, el total del bloque anclado y el aviso de Mi Plan)
// y desde el 16 ago 2026 además se MUESTRA («Q&A ~30 min»): un número que el
// usuario lee no puede tener copias que puedan divergir. Como FESTIVAL_BUFFER,
// el worker del planeador lleva su propia declaración (ver controller/calc.js).
export const FESTIVAL_QA_MIN = 30;        // estimación — la UI la declara, nunca la afirma
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
  // Cortos Cali 2026
  '🌎 Selección Oficial Internacional': 'Official Selection: International',
  '🎬 Selección Oficial Nacional': 'Official Selection: National',
  '🎓 Selección Oficial Internacional Universitaria': 'Official Selection: International Student',
  '📚 Selección Oficial Nacional Universitaria': 'Official Selection: National Student',
  '🌍 Muestra Internacional': 'International Showcase',
  '🇨🇴 Muestra Nacional':     'National Showcase',
  '🏆 Muestra Local':         'Official Selection · Local',
  '🎓 Formación':             'Workshops & Seminar',
  '🔮 Largometrajes': 'Feature Films',
  '🌙 Cortometrajes': 'Short Films',
  '🌱 Raíces del Juego': 'Roots of the Game',
  '🧠 Juego Mental': 'Mind Game',
  '👟 El Rey Puma': 'El Rey Puma',
  '🏅 Más Allá del Fútbol': 'Beyond Football',
  '🔥 Barrio Caliente': 'Barrio Caliente',
  '🚴 Pedal y Resistencia': 'Pedal & Resistance',
  '✍️ Fútbol Poético': 'Poetic Football',
  '🏟️ Refugio en la Cancha': 'Refuge on the Pitch',
  '💪 Contra Todo': 'Against All Odds',
  '🔟 El Diego': 'El Diego',
  '⚽ Juegan como Niñas': 'Juegan como Niñas',
  '🗺️ Territorios en Juego': 'Territories at Play',
  '🇧🇷 Brasil: Juego, Memoria y Pasión': 'Brazil: Game, Memory & Passion',
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
  '🎭 ¿Qué es la Ficción?':'What Is Fiction?',
  '🎞️ Competencia de Cortometrajes':'Short Film Competition',
  '🏆 Competencia Central':'Main Competition',
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
  '🛰️ Apertura': 'Opening · Expanded FullDome',
  '🤝 Encuentro': 'Gathering',
};


// ── PALMARÉS ────────────────────────────────────────────────────────────────
// El palmarés es un dato PROPIO, no derivado de las funciones (decisión de Juan,
// 23 ago 2026). Motivo: lo que un festival premió NO depende de si nosotros
// teníamos su función. Vincularlos era forzar dos hechos distintos a ser uno, y
// hacía que el palmarés heredara los huecos del catálogo — FICDEH premió «Los
// bibliotecarios», una obra que nunca entró a nuestro JSON porque su ficha no
// tenía ninguna función y el pipeline construye el catálogo DESDE las funciones.
//
// `obra` es el título EXACTO en el JSON del festival, o null si no la tenemos.
// Con título → la tarjeta enlaza a su ficha. Sin título → se muestra igual, con
// su afiche propio (Forma A). El palmarés queda completo siempre, y la ausencia
// se ve como pieza nuestra en vez de como un hueco.
//
// `categoria` va VERBATIM del festival — misma regla que las secciones.
// `nivel`: 'ganadora' | 'mencion'.
export const PALMARES=[
  // Vacío a propósito desde el 19 oct 2026: los palmarés viven en el JSON de
  // cada festival (campo `palmares`), con su fuente en
  // festivals/staging/<id>-palmares.json. Lo que quede acá es solo para un
  // festival cuyo JSON todavía no trae el campo.
];

// ── NOTICES ──────────────────────────────────────────────────────────────────
// date: 'YYYY-MM-DD' de la función original — el banner desaparece al día siguiente
// Para 'rescheduled': añadir newDay, newTime, newVenue
export const NOTICES=[
  // Vacío a propósito desde el 19 oct 2026: los avisos viven en el JSON de
  // cada festival (campo `avisos`), con su fuente en
  // festivals/staging/<id>-avisos.json (o en el JSON, si no tiene pipeline). Lo que quede acá es solo para un
  // festival cuyo JSON todavía no trae el campo.
];

// ── FESTIVAL_CONFIG ────────────────────────────────────────────────────────
// Orden: cronológico ascendente por fecha de inicio.
// _DEFAULT_FEST_ID toma el festival más reciente por festivalEndStr.
//
// Campos opcionales importantes:
//   prioLimit  — máximo de funciones priorizadas (default: 5 si se omite)
//   group:'test' — aparece en sección separada del selector; omitir para festivales regulares
//   status:{kind:'postponed', since:'YYYY-MM-DD', note:'…', note_en:'…', url:'…'}
//     — festival APLAZADO (terremoto, paro, clima): se VE con distintivo y banda
//     (note = palabras del festival, verbatim; note_en = traducción nuestra
//     aprobada por Juan, opcional — sin ella el EN muestra el ES intacto) pero
//     no invita a ir: sin punto verde, sin preselección, sin AHORA, sin «hoy».
//     Reversión: fechas nuevas + borrar status. Guardián [festival-aplazado].
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
  'ficpa2026': {
    name:'FICPA',displayName:'FICPA',fullName:'22 FICPA — Festival Internacional de Cine de Pasto',shortName:'FICPA',
    city:'Pasto',country:'CO',
    dates:'13–17 OCT',dates_en:'OCT 13–17',year:2026,timezoneOffset:'-05:00',
    // EL AFICHE OFICIAL de la 22.ª edición (ficpa.co, «AficheActualizado», 23 sep
    // 2026). 9:16 estirado a 2:3 (keyart-estirado).
    keyArt:'/assets/keyart/ficpa2026.jpg',
    // lo que el festival dice de sí mismo; «FICPA» ya es el nombre
    tagline:'Festival Internacional de Cine de Pasto',
    storageKey:'ficpa2026_',festivalStartStr:'2026-10-13T00:00:00',festivalEndStr:'2026-10-17T23:59:00',
    festivalDates:{'2026-10-13':'2026-10-13','2026-10-14':'2026-10-14','2026-10-15':'2026-10-15','2026-10-16':'2026-10-16','2026-10-17':'2026-10-17'},
    days:[{k:'2026-10-13',d:13,lbl:'MAR'},{k:'2026-10-14',d:14,lbl:'MIÉ'},{k:'2026-10-15',d:15,lbl:'JUE'},{k:'2026-10-16',d:16,lbl:'VIE'},{k:'2026-10-17',d:17,lbl:'SÁB'}],
    dayKeys:['2026-10-13','2026-10-14','2026-10-15','2026-10-16','2026-10-17'],
    dayShort:{'2026-10-13':'MAR 13','2026-10-14':'MIÉ 14','2026-10-15':'JUE 15','2026-10-16':'VIE 16','2026-10-17':'SÁB 17'},
    dayShort_en:{'2026-10-13':'TUE 13','2026-10-14':'WED 14','2026-10-15':'THU 15','2026-10-16':'FRI 16','2026-10-17':'SAT 17'},
    dayLong:{'2026-10-13':'Martes 13 de octubre','2026-10-14':'Miércoles 14 de octubre','2026-10-15':'Jueves 15 de octubre','2026-10-16':'Viernes 16 de octubre','2026-10-17':'Sábado 17 de octubre'},
    prioLimit:3,
    films:null,posters:null,lbSlugs:{}
  },
  'villadelcine2026': {
    name:'Villa del Cine',displayName:'Villa del Cine',fullName:'Festival Villa del Cine',
    // displayName porque el nombre es MULTI-PALABRA: sin él, festivalShortName()
    // corta por el primer espacio y el splash lo anunciaba como «Villa».
    // shortName es otra cosa: el slug en mayúscula con que share.js nombra los
    // archivos (otrofestiv-plan-villadelcine.png), como CINEMANCIA o QAFF.
    shortName:'VILLADELCINE',tagline:'Festival de Cine de Villa de Leyva',
    // El subtítulo dice QUÉ ES, no repite el nombre: es la forma de la casa en
    // 18 de 20 festivales (FICMA «Feria Internacional de Cine de Manizales»,
    // CineAutopsia «Festival de Cine Experimental de Bogotá»). Olhar es el
    // precedente exacto: su fullName lleva el nombre y su tagline lo quita.
    // Que repita la CIUDAD con la línea de abajo ya es la norma aprobada en
    // cuatro festivales; repetir el NOMBRE solo lo hace Tribeca, y ahí es
    // deliberado (el título va en inglés y el subtítulo es su nombre en
    // español). Decisión de Juan, 19 sep.
    city:'Villa de Leyva',country:'CO',
    dates:'14–17 OCT',dates_en:'OCT 14–17',year:2026,timezoneOffset:'-05:00',
    // REPROGRAMADO. Lo aplazó el comunicado del 21 sep (incendio del Cerro San
    // Marcos) y el 6 oct publicó su PDF de programación con las fechas nuevas,
    // 14–17 de octubre: se borra el bloque `status` de aplazado, como decía su
    // propia nota de reversión.
    keyArt:'/assets/keyart/villadelcine2026-v4.jpg',
    // v4 (6 oct): el afiche con las fechas nuevas, «14-17 Octubre 2026», del
    // post fijado del festival (p/DduTp5fzUvJ, leído por el embed sin sesión).
    // El post lo monta sobre un fondo de estrellas: se tomó el afiche por sus
    // bordes (2645×3780, a 4,7% de 2:3) y se estiró con compose-keyart.
    // EL AFICHE OFICIAL, EN VERTICAL (v3, 19 sep). La v2 salía de la página 1
    // del PDF de programación, que es APAISADA (609×394 pt, ratio 1,55):
    // estirarla a 2:3 la comprimía un 57% y dejaba la piedra deformada, sin
    // Vía Láctea y sin la franja de patrocinadores. La regla de compose-keyart
    // dice «estirar siempre, nunca recortar», pero se calibró con afiches de
    // 5,7% a 16,3% de desvío: con una fuente apaisada produce otra cosa.
    // La v3 es el afiche vertical que publica el festival (932×1336), a 4,6%
    // de 2:3 — la menor compresión de todo el repo.
    //
    // LA PROGRAMACIÓN SALIÓ EL 18 SEP, cinco días antes de abrir: hasta ese día
    // el botón PROGRAMACIÓN de su web apuntaba a un PDF de 2023. Son 53
    // funciones en 4 sedes, y 22 de ellas son programas de cortos con nombre
    // propio («Nuevas Miradas: UMBRALES»), que es como el festival los agrupa.
    instagram:'festivalvilladelcine', storageKey:'villadelcine2026_',
    festivalStartStr:'2026-10-14T00:00:00',festivalEndStr:'2026-10-17T23:59:00',
    prioLimit:4,ticketing_model:'mixed',
  },
  'ficma2026': {
    name:'FICMA',fullName:'FICMA — Feria Internacional de Cine de Manizales',shortName:'FICMA',
    city:'Manizales',country:'CO',
    dates:'19–26 SEP',dates_en:'SEP 19–26',year:2026,timezoneOffset:'-05:00',
    keyArt:'/assets/keyart/ficma2026-v2.jpg',
    // REPROGRAMADO. El festival se aplazó por el sismo del 10 ago y volvió del
    // 19 al 26 de SEPTIEMBRE, confirmado por sus dos fuentes propias (la bio de
    // @cinemanizales_ficma y laficma.com). El bloque de estado APLAZADO se
    // retiró el 15 sep: el festival ya desmintió el aplazamiento y la banda
    // contradecía su propio anuncio. (El nombre del campo no se escribe aquí a
    // propósito: [festival-aplazado] lo busca por texto y un comentario que lo
    // nombre se lee como si el bloque siguiera puesto.)
    //
    // LA PARRILLA YA ESTÁ COMPLETA. El 18 sep, a un día de abrir, el festival
    // publicó en su home el PDF de programación: 78 páginas, una por función.
    // Son 70 funciones más las 11 actividades de la franja académica, que va
    // aparte (/talleresficma17/). Hasta ese día se armaba post a post desde
    // Instagram y había once: por eso el histórico de esta entrada habla de una
    // programación incompleta.
    //
    // EL AFICHE, corregido el 18 sep. `ficma2026.jpg` era el de antes del sismo
    // y llevaba impreso «10 AL 17 DE AGOSTO». El festival SÍ publicó uno con las
    // fechas nuevas —«19 AL 26 DE SEPTIEMBRE»—: está en su biblioteca de medios
    // desde el 10 de septiembre, como og:image de la home, con el nombre
    // FICMA-17-INSTAGRAM-POST-1.png. Se me pasó al revisar la web y estuve a
    // punto de reclamárselo al festival.
    //
    // Viene en 4:5 (1080×1350), que es el formato de post de Instagram, y es la
    // ÚNICA versión con las fechas buenas: su biblioteca no tiene ninguna 2:3.
    // Se estira, que es la regla del riel (scripts/compose-keyart.py).
    storageKey:'ficma2026_',festivalStartStr:'2026-09-19T00:00:00',festivalEndStr:'2026-09-26T23:59:00',
    festivalDates:{'2026-09-19':'2026-09-19','2026-09-20':'2026-09-20','2026-09-21':'2026-09-21','2026-09-22':'2026-09-22','2026-09-23':'2026-09-23','2026-09-24':'2026-09-24','2026-09-25':'2026-09-25','2026-09-26':'2026-09-26'},
    days:[{k:'2026-09-19',d:19,lbl:'SÁB'},{k:'2026-09-20',d:20,lbl:'DOM'},{k:'2026-09-21',d:21,lbl:'LUN'},{k:'2026-09-22',d:22,lbl:'MAR'},{k:'2026-09-23',d:23,lbl:'MIÉ'},{k:'2026-09-24',d:24,lbl:'JUE'},{k:'2026-09-25',d:25,lbl:'VIE'},{k:'2026-09-26',d:26,lbl:'SÁB'}],
    dayKeys:['2026-09-19','2026-09-20','2026-09-21','2026-09-22','2026-09-23','2026-09-24','2026-09-25','2026-09-26'],
    dayShort:{'2026-09-19':'SÁB 19','2026-09-20':'DOM 20','2026-09-21':'LUN 21','2026-09-22':'MAR 22','2026-09-23':'MIÉ 23','2026-09-24':'JUE 24','2026-09-25':'VIE 25','2026-09-26':'SÁB 26'},
    dayShort_en:{'2026-09-19':'SAT 19','2026-09-20':'SUN 20','2026-09-21':'MON 21','2026-09-22':'TUE 22','2026-09-23':'WED 23','2026-09-24':'THU 24','2026-09-25':'FRI 25','2026-09-26':'SAT 26'},
    dayLong:{'2026-09-19':'Sábado 19 de septiembre','2026-09-20':'Domingo 20 de septiembre','2026-09-21':'Lunes 21 de septiembre','2026-09-22':'Martes 22 de septiembre','2026-09-23':'Miércoles 23 de septiembre','2026-09-24':'Jueves 24 de septiembre','2026-09-25':'Viernes 25 de septiembre','2026-09-26':'Sábado 26 de septiembre'},
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
  'cinemancia2026': {
    name:'Cinemancia',fullName:'Cinemancia — Festival de Cine del Valle de Aburrá',shortName:'CINEMANCIA',
    city:'Valle de Aburrá',country:'CO',
    dates:'3–12 SEP',dates_en:'SEP 3–12',year:2026,timezoneOffset:'-05:00',
    storageKey:'cinemancia2026_',festivalStartStr:'2026-09-03T00:00:00',festivalEndStr:'2026-09-12T23:59:00',
    festivalDates:{'2026-09-03': '2026-09-03', '2026-09-04': '2026-09-04', '2026-09-05': '2026-09-05', '2026-09-06': '2026-09-06', '2026-09-07': '2026-09-07', '2026-09-08': '2026-09-08', '2026-09-09': '2026-09-09', '2026-09-10': '2026-09-10', '2026-09-11': '2026-09-11', '2026-09-12': '2026-09-12'},
    days:[{k: '2026-09-03', d: 3, lbl: 'JUE'}, {k: '2026-09-04', d: 4, lbl: 'VIE'}, {k: '2026-09-05', d: 5, lbl: 'SÁB'}, {k: '2026-09-06', d: 6, lbl: 'DOM'}, {k: '2026-09-07', d: 7, lbl: 'LUN'}, {k: '2026-09-08', d: 8, lbl: 'MAR'}, {k: '2026-09-09', d: 9, lbl: 'MIÉ'}, {k: '2026-09-10', d: 10, lbl: 'JUE'}, {k: '2026-09-11', d: 11, lbl: 'VIE'}, {k: '2026-09-12', d: 12, lbl: 'SÁB'}],
    dayKeys:['2026-09-03', '2026-09-04', '2026-09-05', '2026-09-06', '2026-09-07', '2026-09-08', '2026-09-09', '2026-09-10', '2026-09-11', '2026-09-12'],
    dayShort:{'2026-09-03': 'JUE 3', '2026-09-04': 'VIE 4', '2026-09-05': 'SÁB 5', '2026-09-06': 'DOM 6', '2026-09-07': 'LUN 7', '2026-09-08': 'MAR 8', '2026-09-09': 'MIÉ 9', '2026-09-10': 'JUE 10', '2026-09-11': 'VIE 11', '2026-09-12': 'SÁB 12'},
    dayShort_en:{'2026-09-03': 'THU 3', '2026-09-04': 'FRI 4', '2026-09-05': 'SAT 5', '2026-09-06': 'SUN 6', '2026-09-07': 'MON 7', '2026-09-08': 'TUE 8', '2026-09-09': 'WED 9', '2026-09-10': 'THU 10', '2026-09-11': 'FRI 11', '2026-09-12': 'SAT 12'},
    dayLong:{'2026-09-03': 'Jueves 3 de septiembre', '2026-09-04': 'Viernes 4 de septiembre', '2026-09-05': 'Sábado 5 de septiembre', '2026-09-06': 'Domingo 6 de septiembre', '2026-09-07': 'Lunes 7 de septiembre', '2026-09-08': 'Martes 8 de septiembre', '2026-09-09': 'Miércoles 9 de septiembre', '2026-09-10': 'Jueves 10 de septiembre', '2026-09-11': 'Viernes 11 de septiembre', '2026-09-12': 'Sábado 12 de septiembre'},
    prioLimit:5,
    sharedSlotIsOneScreening:true,
    // Mixto, y lo dice el PDF oficial con todas las letras: «a excepción de las
    // funciones en Cineprox Las Américas y Cine MAMM, las funciones del festival
    // son de entrada libre». En Cineprox las sillas son numeradas y la boleta se
    // compra en taquilla; en Cine MAMM, en el primer piso del museo. El build
    // anterior marcaba las 89 funciones como gratis por igual.
    ticketing_model:'mixed',
    keyArt:'/assets/keyart/cinemancia2026.jpg',
    // Sus seis municipios son el Valle de Aburrá: un solo territorio de
    // traslado. Sin esto, la app se niega a estimar el viaje entre ellos —una
    // regla pensada para FICDEH, que corre en ciudades a cientos de km— y le
    // dice al usuario «es en otra ciudad» en vez de cuántos minutos le faltan.
    metroArea:true,
    // PUBLICADO el 25 AGO 2026, con el visto bueno del festival. Se fueron
    // JUNTAS las dos líneas que lo escondían: la marca de grupo de pruebas y
    // `review`. La segunda no es decorativa —`_esRevisionActiva()` la lee como
    // «esto no se publica» y de ahí cuelgan tres restricciones: no sincroniza,
    // no se comparte y pinta la banda «En revisión»—; además `dismissSplash()`
    // pide la clave con solo ver `review.key`, sin mirar `until` ni el grupo,
    // así que dejarla habría pedido la clave a todo el que entrara.
    tagline:'Festival de Cine del Valle de Aburrá',
    films:null,posters:null,lbSlugs:{}
  },
  'cineautopsia2026': {
    name:'CineAutopsia',fullName:'CineAutopsia — Festival de Cine Experimental de Bogotá',shortName:'CINEAUTOPSIA',
    city:'Bogotá',country:'CO',
    dates:'21–29 AGO',dates_en:'AUG 21–29',year:2026,timezoneOffset:'-05:00',
    storageKey:'cineautopsia2026_',festivalStartStr:'2026-08-21T00:00:00',festivalEndStr:'2026-08-29T23:59:00',
    festivalDates:{'2026-08-21': '2026-08-21', '2026-08-22': '2026-08-22', '2026-08-23': '2026-08-23', '2026-08-24': '2026-08-24', '2026-08-25': '2026-08-25', '2026-08-26': '2026-08-26', '2026-08-27': '2026-08-27', '2026-08-28': '2026-08-28', '2026-08-29': '2026-08-29'},
    days:[{k: '2026-08-21', d: 21, lbl: 'VIE'}, {k: '2026-08-22', d: 22, lbl: 'SÁB'}, {k: '2026-08-23', d: 23, lbl: 'DOM'}, {k: '2026-08-24', d: 24, lbl: 'LUN'}, {k: '2026-08-25', d: 25, lbl: 'MAR'}, {k: '2026-08-26', d: 26, lbl: 'MIÉ'}, {k: '2026-08-27', d: 27, lbl: 'JUE'}, {k: '2026-08-28', d: 28, lbl: 'VIE'}, {k: '2026-08-29', d: 29, lbl: 'SÁB'}],
    dayKeys:['2026-08-21','2026-08-22','2026-08-23','2026-08-24','2026-08-25','2026-08-26','2026-08-27','2026-08-28','2026-08-29'],
    dayShort:{'2026-08-21': 'VIE 21', '2026-08-22': 'SÁB 22', '2026-08-23': 'DOM 23', '2026-08-24': 'LUN 24', '2026-08-25': 'MAR 25', '2026-08-26': 'MIÉ 26', '2026-08-27': 'JUE 27', '2026-08-28': 'VIE 28', '2026-08-29': 'SÁB 29'},
    dayShort_en:{'2026-08-21': 'FRI 21', '2026-08-22': 'SAT 22', '2026-08-23': 'SUN 23', '2026-08-24': 'MON 24', '2026-08-25': 'TUE 25', '2026-08-26': 'WED 26', '2026-08-27': 'THU 27', '2026-08-28': 'FRI 28', '2026-08-29': 'SAT 29'},
    dayLong:{'2026-08-21': 'Viernes 21 de agosto', '2026-08-22': 'Sábado 22 de agosto', '2026-08-23': 'Domingo 23 de agosto', '2026-08-24': 'Lunes 24 de agosto', '2026-08-25': 'Martes 25 de agosto', '2026-08-26': 'Miércoles 26 de agosto', '2026-08-27': 'Jueves 27 de agosto', '2026-08-28': 'Viernes 28 de agosto', '2026-08-29': 'Sábado 29 de agosto'},
    prioLimit:3,
    keyArt:'/assets/keyart/cineautopsia2026-v2.jpg',
    tagline:'Festival de Cine Experimental de Bogotá',
    films:null,posters:null,lbSlugs:{}
  },
  'vartex2026': {
    name:'Vartex',fullName:'Vartex 14 — Muestra de Video y Experimental de Medellín',shortName:'VARTEX',
    city:'Medellín',country:'CO',
    dates:'19–22 AGO',dates_en:'AUG 19–22',year:2026,timezoneOffset:'-05:00',
    storageKey:'vartex2026_',festivalStartStr:'2026-08-19T00:00:00',festivalEndStr:'2026-08-22T23:59:00',
    festivalDates:{'2026-08-19': '2026-08-19', '2026-08-20': '2026-08-20', '2026-08-21': '2026-08-21', '2026-08-22': '2026-08-22'},
    days:[{k: '2026-08-19', d: 19, lbl: 'MIÉ'}, {k: '2026-08-20', d: 20, lbl: 'JUE'}, {k: '2026-08-21', d: 21, lbl: 'VIE'}, {k: '2026-08-22', d: 22, lbl: 'SÁB'}],
    dayKeys:['2026-08-19', '2026-08-20', '2026-08-21', '2026-08-22'],
    dayShort:{'2026-08-19': 'MIÉ 19', '2026-08-20': 'JUE 20', '2026-08-21': 'VIE 21', '2026-08-22': 'SÁB 22'},
    dayShort_en:{'2026-08-19': 'WED 19', '2026-08-20': 'THU 20', '2026-08-21': 'FRI 21', '2026-08-22': 'SAT 22'},
    dayLong:{'2026-08-19': 'Miércoles 19 de agosto', '2026-08-20': 'Jueves 20 de agosto', '2026-08-21': 'Viernes 21 de agosto', '2026-08-22': 'Sábado 22 de agosto'},
    prioLimit:3,
    keyArt:'/assets/keyart/vartex2026-v3.jpg',
    // (nota histórica) Sin keyArt al principio: el afiche del festival está en la lámina 1 de su
    // carrusel y las imágenes de su sitio son apaisadas (1200x630). Estirarlas
    // a 2:3 las aplastaría un 65%, muy lejos de lo que tolera la regla. La card
    // cae al respaldo tipográfico hasta que llegue el afiche en vertical.
    tagline:'Muestra de Video y Experimental',
    films:null,posters:null,lbSlugs:{}
  },
  'qaff2026':{
    // VISIBLE desde el 4 sep 2026, con la banda de TRASLADADO.
    //
    // El festival trasladó LA TOTALIDAD de sus proyecciones a Bogotá por el
    // terremoto del 10 ago que golpeó Quibdó y el Chocó — el MISMO sismo que
    // aplazó FICMA. Comunicado del 20 ago: instagram.com/p/DcREogQER9d
    //
    // Estuvo oculto con `group:'test'` entre el 23 ago y el 4 sep, mientras lo
    // publicado seguía siendo el programa de Quibdó —una ciudad donde ya no se
    // proyecta nada— y no teníamos el de Bogotá. Ya no: el JSON es el de
    // Bogotá, 44 funciones en 6 sedes, y la banda explica el cambio.
    //
    status:{
      kind:'moved',
      since:'2026-08-20',
      note:'Por el terremoto del 10 de agosto, el festival trasladó «excepcionalmente la totalidad de las proyecciones» a Bogotá.',
      note_en:'Due to the August 10 earthquake, the festival "exceptionally relocated all screenings" to Bogotá.',
      url:'https://www.instagram.com/p/DcREogQER9d',
    },
    name:'QAFF',fullName:'QAFF — Quibdó África Film Festival',shortName:'QAFF',
    city:'Bogotá',country:'CO',
    dates:'14–22 SEP',dates_en:'SEP 14–22',year:2026,timezoneOffset:'-05:00',
    keyArt:'/assets/keyart/qaff2026-v2.jpg',
    storageKey:'qaff2026_',festivalStartStr:'2026-09-14T00:00:00',festivalEndStr:'2026-09-22T23:00:00',
    festivalDates:{'2026-09-14':'2026-09-14','2026-09-15':'2026-09-15','2026-09-16':'2026-09-16','2026-09-17':'2026-09-17','2026-09-18':'2026-09-18','2026-09-19':'2026-09-19','2026-09-20':'2026-09-20','2026-09-21':'2026-09-21','2026-09-22':'2026-09-22'},
    days:[{k:'2026-09-14',d:14,lbl:'LUN'},{k:'2026-09-15',d:15,lbl:'MAR'},{k:'2026-09-16',d:16,lbl:'MIÉ'},{k:'2026-09-17',d:17,lbl:'JUE'},{k:'2026-09-18',d:18,lbl:'VIE'},{k:'2026-09-19',d:19,lbl:'SÁB'},{k:'2026-09-20',d:20,lbl:'DOM'},{k:'2026-09-21',d:21,lbl:'LUN'},{k:'2026-09-22',d:22,lbl:'MAR'}],
    dayKeys:['2026-09-14','2026-09-15','2026-09-16','2026-09-17','2026-09-18','2026-09-19','2026-09-20','2026-09-21','2026-09-22'],
    dayShort:{'2026-09-14':'LUN 14','2026-09-15':'MAR 15','2026-09-16':'MIÉ 16','2026-09-17':'JUE 17','2026-09-18':'VIE 18','2026-09-19':'SÁB 19','2026-09-20':'DOM 20','2026-09-21':'LUN 21','2026-09-22':'MAR 22'},
    dayShort_en:{'2026-09-14':'MON 14','2026-09-15':'TUE 15','2026-09-16':'WED 16','2026-09-17':'THU 17','2026-09-18':'FRI 18','2026-09-19':'SAT 19','2026-09-20':'SUN 20','2026-09-21':'MON 21','2026-09-22':'TUE 22'},
    dayLong:{'2026-09-14':'Lunes 14 de septiembre','2026-09-15':'Martes 15 de septiembre','2026-09-16':'Miércoles 16 de septiembre','2026-09-17':'Jueves 17 de septiembre','2026-09-18':'Viernes 18 de septiembre','2026-09-19':'Sábado 19 de septiembre','2026-09-20':'Domingo 20 de septiembre','2026-09-21':'Lunes 21 de septiembre','2026-09-22':'Martes 22 de septiembre'},
    prioLimit:3,eventPosterLabel:['EVENTO',''],
    films:null,posters:null,lbSlugs:{}
  },
  'tiff2026': {
    name:'TIFF',fullName:'TIFF — Toronto International Film Festival',shortName:'TIFF',
    city:'Toronto',country:'CA',
    dates:'10–20 SEP',dates_en:'SEP 10–20',year:2026,timezoneOffset:'-04:00',
    storageKey:'tiff2026_',festivalStartStr:'2026-09-10T00:00:00',festivalEndStr:'2026-09-20T23:59:00',
    festivalDates:{'2026-09-10': '2026-09-10', '2026-09-11': '2026-09-11', '2026-09-12': '2026-09-12', '2026-09-13': '2026-09-13', '2026-09-14': '2026-09-14', '2026-09-15': '2026-09-15', '2026-09-16': '2026-09-16', '2026-09-17': '2026-09-17', '2026-09-18': '2026-09-18', '2026-09-19': '2026-09-19', '2026-09-20': '2026-09-20'},
    days:[{k: '2026-09-10', d: 10, lbl: 'JUE'}, {k: '2026-09-11', d: 11, lbl: 'VIE'}, {k: '2026-09-12', d: 12, lbl: 'SÁB'}, {k: '2026-09-13', d: 13, lbl: 'DOM'}, {k: '2026-09-14', d: 14, lbl: 'LUN'}, {k: '2026-09-15', d: 15, lbl: 'MAR'}, {k: '2026-09-16', d: 16, lbl: 'MIÉ'}, {k: '2026-09-17', d: 17, lbl: 'JUE'}, {k: '2026-09-18', d: 18, lbl: 'VIE'}, {k: '2026-09-19', d: 19, lbl: 'SÁB'}, {k: '2026-09-20', d: 20, lbl: 'DOM'}],
    dayKeys:['2026-09-10', '2026-09-11', '2026-09-12', '2026-09-13', '2026-09-14', '2026-09-15', '2026-09-16', '2026-09-17', '2026-09-18', '2026-09-19', '2026-09-20'],
    dayShort:{'2026-09-10': 'JUE 10', '2026-09-11': 'VIE 11', '2026-09-12': 'SÁB 12', '2026-09-13': 'DOM 13', '2026-09-14': 'LUN 14', '2026-09-15': 'MAR 15', '2026-09-16': 'MIÉ 16', '2026-09-17': 'JUE 17', '2026-09-18': 'VIE 18', '2026-09-19': 'SÁB 19', '2026-09-20': 'DOM 20'},
    dayShort_en:{'2026-09-10': 'THU 10', '2026-09-11': 'FRI 11', '2026-09-12': 'SAT 12', '2026-09-13': 'SUN 13', '2026-09-14': 'MON 14', '2026-09-15': 'TUE 15', '2026-09-16': 'WED 16', '2026-09-17': 'THU 17', '2026-09-18': 'FRI 18', '2026-09-19': 'SAT 19', '2026-09-20': 'SUN 20'},
    dayLong:{'2026-09-10': 'Jueves 10 de septiembre', '2026-09-11': 'Viernes 11 de septiembre', '2026-09-12': 'Sábado 12 de septiembre', '2026-09-13': 'Domingo 13 de septiembre', '2026-09-14': 'Lunes 14 de septiembre', '2026-09-15': 'Martes 15 de septiembre', '2026-09-16': 'Miércoles 16 de septiembre', '2026-09-17': 'Jueves 17 de septiembre', '2026-09-18': 'Viernes 18 de septiembre', '2026-09-19': 'Sábado 19 de septiembre', '2026-09-20': 'Domingo 20 de septiembre'},
    prioLimit:6,
    keyArt:'/assets/keyart/tiff2026-v2.jpg',
    // PUBLICADO el 23 ago 2026, por decisión de Juan. El freno estuvo puesto
    // desde el 17 ago esperando su pase sobre las sinopsis; lo levanta él
    // sabiendo que faltan 20 de 296 —casi todas de cortos experimentales—,
    // 16 años, un afiche y un director. Ninguno rompe una ficha: sale sin
    // sinopsis, no sin obra.
    tagline:'Toronto International Film Festival',
    ticketing_model:'paid', // todas las públicas tienen enlace de Ticketmaster.
    // OJO: el vocabulario de la app es SOLO 'paid' | 'mixed'. Puse 'ticketed',
    // que no existe, y el botón de boletería no se pintó en ninguna de las 637
    // fichas pese a tener el enlace. Lo cazó Juan en pantalla, 13 ago.
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
  },
  'siembrafest2026': {
    // PUBLICADO el 7 sep (Juan). Entra SOLO con Villeta: el PDF de Sasaima no
    // existe —su web dice «muy pronto» y la URL devuelve el HTML comodín,
    // comprobado contra un nombre inventado—.
    //
    // FECHAS 9–18, no 9–17 (Juan, 7 sep). El festival dice 9–18 en su afiche, su
    // bio y su prensa; decir 9–17 porque es lo que nosotros tenemos generaba
    // ruido contra todo lo que el usuario ve afuera. Y no era solo cosmético:
    // `festivalEndStr` estaba en el 17, así que el 18 la app habría declarado
    // TERMINADO un festival que sigue corriendo en Sasaima, con su banda y el
    // modo recuerdo encima.
    //
    // Las PESTAÑAS DE DÍA se quedan en 9 (9–17), que es lo que está programado.
    // Añadir el 18 pintaría «Este día no tiene actividades», y eso sí sería
    // falso: actividades hay, en Sasaima; los que no las tenemos somos nosotros.
    // Cuando salga su programación esto es aditivo: sedes con su `city`, el
    // paraguas en `city` y el día 18. El multiciudad ya existe.
    // VILLETA, del 9 al 17. El festival completo es 9–18 en Sasaima y Villeta
    // (así lo dice su propia bio), pero el PDF de Sasaima no existe todavía: la
    // web dice «muy pronto» y su URL devuelve HTML. Cuando salga vuelven la
    // ciudad «Sasaima y Villeta» y, con ella, probablemente el 18.
    name:'SiembraFest',fullName:'SiembraFest — Festival de Cine Colombiano al Campo',shortName:'SIEMBRAFEST',
    city:'Sasaima y Villeta',country:'CO',
    dates:'9–18 SEP',dates_en:'SEP 9–18',year:2026,timezoneOffset:'-05:00',
    storageKey:'siembrafest2026_',festivalStartStr:'2026-09-09T00:00:00',festivalEndStr:'2026-09-18T23:00:00',
    festivalDates:{'2026-09-09':'2026-09-09','2026-09-10':'2026-09-10','2026-09-11':'2026-09-11','2026-09-12':'2026-09-12','2026-09-13':'2026-09-13','2026-09-14':'2026-09-14','2026-09-15':'2026-09-15','2026-09-16':'2026-09-16','2026-09-17':'2026-09-17','2026-09-18':'2026-09-18'},
    days:[{'k':'2026-09-09','d':9,'lbl':'MIÉ'},{'k':'2026-09-10','d':10,'lbl':'JUE'},{'k':'2026-09-11','d':11,'lbl':'VIE'},{'k':'2026-09-12','d':12,'lbl':'SÁB'},{'k':'2026-09-13','d':13,'lbl':'DOM'},{'k':'2026-09-14','d':14,'lbl':'LUN'},{'k':'2026-09-15','d':15,'lbl':'MAR'},{'k':'2026-09-16','d':16,'lbl':'MIÉ'},{'k':'2026-09-17','d':17,'lbl':'JUE'},{'k':'2026-09-18','d':18,'lbl':'VIE'}],
    dayKeys:['2026-09-09','2026-09-10','2026-09-11','2026-09-12','2026-09-13','2026-09-14','2026-09-15','2026-09-16','2026-09-17','2026-09-18'],
    dayShort:{'2026-09-09':'MIÉ 9','2026-09-10':'JUE 10','2026-09-11':'VIE 11','2026-09-12':'SÁB 12','2026-09-13':'DOM 13','2026-09-14':'LUN 14','2026-09-15':'MAR 15','2026-09-16':'MIÉ 16','2026-09-17':'JUE 17','2026-09-18':'VIE 18'},
    dayShort_en:{'2026-09-09':'WED 9','2026-09-10':'THU 10','2026-09-11':'FRI 11','2026-09-12':'SAT 12','2026-09-13':'SUN 13','2026-09-14':'MON 14','2026-09-15':'TUE 15','2026-09-16':'WED 16','2026-09-17':'THU 17','2026-09-18':'FRI 18'},
    dayLong:{'2026-09-09':'Miércoles 9 de septiembre','2026-09-10':'Jueves 10 de septiembre','2026-09-11':'Viernes 11 de septiembre','2026-09-12':'Sábado 12 de septiembre','2026-09-13':'Domingo 13 de septiembre','2026-09-14':'Lunes 14 de septiembre','2026-09-15':'Martes 15 de septiembre','2026-09-16':'Miércoles 16 de septiembre','2026-09-17':'Jueves 17 de septiembre','2026-09-18':'Viernes 18 de septiembre'},
    prioLimit:4,
    // Sasaima y Villeta están a 12 km por la misma vía: es UN territorio de
    // traslado. Se conserva para cuando Sasaima entre; hoy solo hay Villeta.
    metroArea:true,
    keyArt:'/assets/keyart/siembrafest2026-v2.jpg',
    tagline:'Festival de Cine Colombiano al Campo',
    films:null,posters:null,lbSlugs:{}
  },
  'jardin2026': {
    name:'Festival de Cine de Jardín',displayName:'Festival de Cine de Jardín',
    fullName:'11° Festival de Cine de Jardín — Ecos de Voces Silenciadas',shortName:'JARDÍN',
    city:'Jardín',country:'CO',
    dates:'24–27 SEP',dates_en:'SEP 24–27',year:2026,timezoneOffset:'-05:00',
    // EL AFICHE OFICIAL, estirado a 2:3 como manda la regla del keyArt: ni
    // bandas, ni blur, ni recorte. Viene en 1080×1440 (3:4) del post de
    // anuncio de @festicinejardin —arte de @elgorditoviolento, con los
    // líderes sociales retratados y la basílica—, y de 0,750 a 0,667 el ancho
    // se estrecha un 11%, por debajo del 16% que la doctrina da por
    // imperceptible. Lleva impresas las fechas, así que [keyart-fechas] lo
    // contrasta contra `dates`.
    keyArt:'/assets/keyart/jardin2026.jpg',
    storageKey:'jardin2026_',festivalStartStr:'2026-09-24T00:00:00',festivalEndStr:'2026-09-27T23:59:00',
    festivalDates:{'2026-09-24':'2026-09-24','2026-09-25':'2026-09-25','2026-09-26':'2026-09-26','2026-09-27':'2026-09-27'},
    days:[{k:'2026-09-24',d:24,lbl:'JUE'},{k:'2026-09-25',d:25,lbl:'VIE'},{k:'2026-09-26',d:26,lbl:'SÁB'},{k:'2026-09-27',d:27,lbl:'DOM'}],
    dayKeys:['2026-09-24','2026-09-25','2026-09-26','2026-09-27'],
    dayShort:{'2026-09-24':'JUE 24','2026-09-25':'VIE 25','2026-09-26':'SÁB 26','2026-09-27':'DOM 27'},
    dayShort_en:{'2026-09-24':'THU 24','2026-09-25':'FRI 25','2026-09-26':'SAT 26','2026-09-27':'SUN 27'},
    dayLong:{'2026-09-24':'Jueves 24 de septiembre','2026-09-25':'Viernes 25 de septiembre','2026-09-26':'Sábado 26 de septiembre','2026-09-27':'Domingo 27 de septiembre'},
    prioLimit:5,
    // EL SUBTÍTULO ES EL LEMA DE LA EDICIÓN, no un descriptor. La forma de la
    // casa es que el subtítulo diga QUÉ ES el festival, pero acá el nombre ya
    // lo dice entero («Festival de Cine de Jardín») y repetirlo sería el error
    // que la regla existe para evitar. El lema es lo que el festival pone
    // debajo de su nombre en el afiche.
    tagline:'Ecos de Voces Silenciadas',
    ticketing_model:'mixed', // toda la programación es gratuita (lámina 1 del carrusel); sin ticket_url no se pinta nada
    films:null,posters:null,lbSlugs:{}
  },
  'itagui2026': {
    name:'Festicine Itagüí',displayName:'Festicine Itagüí',
    fullName:'9° Festival Internacional de Cine Ciudad de Itagüí',shortName:'ITAGÜÍ',
    city:'Itagüí',country:'CO',
    dates:'23–27 SEP',dates_en:'SEP 23–27',year:2026,timezoneOffset:'-05:00',
    // EL AFICHE OFICIAL, ENTERO — con su franja de patrocinadores. Elegido por
    // Juan (23 sep) mirando las tres opciones a tamaño de card: recortar el pie
    // ALEJA el afiche del 2:3 en vez de acercarlo, porque le quita altura. Los
    // números: entero 388×515 (ratio 1,327) pide estirar el alto un 13%, dentro
    // de lo aprobado; sin patrocinadores sube a 31% y sin el pie entero a 36%.
    keyArt:'/assets/keyart/itagui2026-v4.jpg',
    // LA EDICIÓN POR ENCIMA DEL LEMA (Juan, 23 sep). El festival tiene lema
    // —«Colombia: cine bien hecho, cine no visto»— pero en el subtítulo pesa
    // más decir QUÉ es y en qué edición va. No repite el nombre de arriba
    // («Festicine Itagüí») ni la ciudad, que ya va en su propia línea.
    tagline:'9° Festival Internacional de Cine',
    storageKey:'itagui2026_',festivalStartStr:'2026-09-23T00:00:00',festivalEndStr:'2026-09-27T23:59:00',
    festivalDates:{'2026-09-23':'2026-09-23','2026-09-24':'2026-09-24','2026-09-25':'2026-09-25','2026-09-26':'2026-09-26','2026-09-27':'2026-09-27'},
    days:[{k:'2026-09-23',d:23,lbl:'MIÉ'},{k:'2026-09-24',d:24,lbl:'JUE'},{k:'2026-09-25',d:25,lbl:'VIE'},{k:'2026-09-26',d:26,lbl:'SÁB'},{k:'2026-09-27',d:27,lbl:'DOM'}],
    dayKeys:['2026-09-23','2026-09-24','2026-09-25','2026-09-26','2026-09-27'],
    dayShort:{'2026-09-23':'MIÉ 23','2026-09-24':'JUE 24','2026-09-25':'VIE 25','2026-09-26':'SÁB 26','2026-09-27':'DOM 27'},
    dayShort_en:{'2026-09-23':'WED 23','2026-09-24':'THU 24','2026-09-25':'FRI 25','2026-09-26':'SAT 26','2026-09-27':'SUN 27'},
    dayLong:{'2026-09-23':'Miércoles 23 de septiembre','2026-09-24':'Jueves 24 de septiembre','2026-09-25':'Viernes 25 de septiembre','2026-09-26':'Sábado 26 de septiembre','2026-09-27':'Domingo 27 de septiembre'},
    prioLimit:3,ticketing_model:'mixed',
    films:null,posters:null,lbSlugs:{}
  },
  'girardota2026': {
    // EL NOMBRE CORTO lo eligió Juan (27 sep): «Festival Audiovisual de Girardota»
    // ocupaba dos líneas en el selector y se cortaba en el encabezado. Es su
    // usuario en redes (@festigirardota); el nombre oficial queda en fullName.
    name:'Festigirardota',displayName:'Festigirardota',
    fullName:'9° Festival Audiovisual de Girardota 2026',shortName:'GIRARDOTA',
    city:'Girardota',country:'CO',
    dates:'30 SEP–4 OCT',dates_en:'SEP 30–OCT 4',year:2026,timezoneOffset:'-05:00',
    // EL AFICHE OFICIAL (@girardotaescultura p/DdSaAR7Jbua, 14 sep 2026), con su
    // franja de organizadores — la versión la elige Juan, como en Itagüí.
    keyArt:'/assets/keyart/girardota2026-v2.jpg',
    // EL LEMA DE LA EDICIÓN, el del afiche. La edición («9° Festival
    // Audiovisual…») ya está en fullName.
    tagline:'Fantasía Tropical',
    instagram:'festigirardota', storageKey:'girardota2026_',festivalStartStr:'2026-09-30T00:00:00',festivalEndStr:'2026-10-04T23:59:00',
    festivalDates:{'2026-09-30':'2026-09-30','2026-10-01':'2026-10-01','2026-10-02':'2026-10-02','2026-10-03':'2026-10-03','2026-10-04':'2026-10-04'},
    days:[{k:'2026-09-30',d:30,lbl:'MIÉ'},{k:'2026-10-01',d:1,lbl:'JUE'},{k:'2026-10-02',d:2,lbl:'VIE'},{k:'2026-10-03',d:3,lbl:'SÁB'},{k:'2026-10-04',d:4,lbl:'DOM'}],
    dayKeys:['2026-09-30','2026-10-01','2026-10-02','2026-10-03','2026-10-04'],
    dayShort:{'2026-09-30':'MIÉ 30','2026-10-01':'JUE 1','2026-10-02':'VIE 2','2026-10-03':'SÁB 3','2026-10-04':'DOM 4'},
    dayShort_en:{'2026-09-30':'WED 30','2026-10-01':'THU 1','2026-10-02':'FRI 2','2026-10-03':'SAT 3','2026-10-04':'SUN 4'},
    dayLong:{'2026-09-30':'Miércoles 30 de septiembre','2026-10-01':'Jueves 1 de octubre','2026-10-02':'Viernes 2 de octubre','2026-10-03':'Sábado 3 de octubre','2026-10-04':'Domingo 4 de octubre'},
    prioLimit:3,
    films:null,posters:null,lbSlugs:{}
  },
  'anibia2026': {
    // EL NOMBRE es el del festival (@anibiafestival: «Anibia»); la edición va en fullName.
    name:'Anibia',displayName:'Anibia',fullName:'Anibia — Festival de Animación 2026',shortName:'ANIBIA',
    city:'Bogotá',country:'CO',
    dates:'20 OCT–1 NOV',dates_en:'OCT 20–NOV 1',year:2026,timezoneOffset:'-05:00',
    storageKey:'anibia2026_',festivalStartStr:'2026-10-20T00:00:00',festivalEndStr:'2026-11-01T23:59:00',
    festivalDates:{'2026-10-20':'2026-10-20','2026-10-21':'2026-10-21','2026-10-22':'2026-10-22','2026-10-23':'2026-10-23','2026-10-24':'2026-10-24','2026-10-25':'2026-10-25','2026-10-26':'2026-10-26','2026-10-27':'2026-10-27','2026-10-28':'2026-10-28','2026-10-29':'2026-10-29','2026-10-30':'2026-10-30','2026-10-31':'2026-10-31','2026-11-01':'2026-11-01'},
    days:[{k:'2026-10-20',d:20,lbl:'MAR'},{k:'2026-10-21',d:21,lbl:'MIÉ'},{k:'2026-10-22',d:22,lbl:'JUE'},{k:'2026-10-23',d:23,lbl:'VIE'},{k:'2026-10-24',d:24,lbl:'SÁB'},{k:'2026-10-25',d:25,lbl:'DOM'},{k:'2026-10-26',d:26,lbl:'LUN'},{k:'2026-10-27',d:27,lbl:'MAR'},{k:'2026-10-28',d:28,lbl:'MIÉ'},{k:'2026-10-29',d:29,lbl:'JUE'},{k:'2026-10-30',d:30,lbl:'VIE'},{k:'2026-10-31',d:31,lbl:'SÁB'},{k:'2026-11-01',d:1,lbl:'DOM'}],
    dayKeys:['2026-10-20','2026-10-21','2026-10-22','2026-10-23','2026-10-24','2026-10-25','2026-10-26','2026-10-27','2026-10-28','2026-10-29','2026-10-30','2026-10-31','2026-11-01'],
    dayShort:{'2026-10-20':'MAR 20','2026-10-21':'MIÉ 21','2026-10-22':'JUE 22','2026-10-23':'VIE 23','2026-10-24':'SÁB 24','2026-10-25':'DOM 25','2026-10-26':'LUN 26','2026-10-27':'MAR 27','2026-10-28':'MIÉ 28','2026-10-29':'JUE 29','2026-10-30':'VIE 30','2026-10-31':'SÁB 31','2026-11-01':'DOM 1'},
    dayShort_en:{'2026-10-20':'TUE 20','2026-10-21':'WED 21','2026-10-22':'THU 22','2026-10-23':'FRI 23','2026-10-24':'SAT 24','2026-10-25':'SUN 25','2026-10-26':'MON 26','2026-10-27':'TUE 27','2026-10-28':'WED 28','2026-10-29':'THU 29','2026-10-30':'FRI 30','2026-10-31':'SAT 31','2026-11-01':'SUN 1'},
    dayLong:{'2026-10-20':'Martes 20 de octubre','2026-10-21':'Miércoles 21 de octubre','2026-10-22':'Jueves 22 de octubre','2026-10-23':'Viernes 23 de octubre','2026-10-24':'Sábado 24 de octubre','2026-10-25':'Domingo 25 de octubre','2026-10-26':'Lunes 26 de octubre','2026-10-27':'Martes 27 de octubre','2026-10-28':'Miércoles 28 de octubre','2026-10-29':'Jueves 29 de octubre','2026-10-30':'Viernes 30 de octubre','2026-10-31':'Sábado 31 de octubre','2026-11-01':'Domingo 1 de noviembre'},
    // EL AFICHE OFICIAL de la edición 2026, ilustrado por Caballo Loco Studio
    // (@anibiafestival p/DdmOKm1m9nq, lámina 1, 1808×2256): estirado a 400×600.
    keyArt:'/assets/keyart/anibia2026-v2.jpg',
    // la palabra del festival («Festival de Animación», en el afiche): dice qué es
    tagline:'Festival de Animación',
    instagram:'anibiafestival',
    // boleta en la Cinemateca Centro (TuBoleta, por función) salvo la inaugural;
    // entrada libre en el resto de sedes
    ticketing_model:'mixed',
    prioLimit:5,eventPosterLabel:['EVENTO',''],
    films:null,posters:null,lbSlugs:{}
  },
  'guatape2026': {
    // EL NOMBRE es el del festival (@guatapefilmfest); la edición va en fullName.
    name:'Guatapé Film Fest',displayName:'Guatapé Film Fest',
    fullName:'Guatapé Film Fest 2026 — 4.ª edición',shortName:'GUATAPÉ',
    city:'Guatapé',country:'CO',
    dates:'21–25 OCT',dates_en:'OCT 21–25',year:2026,timezoneOffset:'-05:00',
    // EL AFICHE OFICIAL de la 4.ª edición, el de la portada de guatapefilmfest.com
    // (assets.cdn.filesafe.space/…/6aaacfd8aabc65fd5d0bac70.jpeg, 1023×1537, 2:3):
    // el original estirado a 400×600, sin bandas ni recorte. El QR es parte del
    // afiche publicado. La v1 era la portada del carrusel de programación (Juan,
    // 18 oct: «no es ese»).
    keyArt:'/assets/keyart/guatape2026-v2.jpg',
    // EL LEMA DE LA 4.ª EDICIÓN
    tagline:'El Reflejo del Cine',
    instagram:'guatapefilmfest', storageKey:'guatape2026_',festivalStartStr:'2026-10-21T00:00:00',festivalEndStr:'2026-10-25T23:59:00',
    festivalDates:{'2026-10-21':'2026-10-21','2026-10-22':'2026-10-22','2026-10-23':'2026-10-23','2026-10-24':'2026-10-24','2026-10-25':'2026-10-25'},
    days:[{k:'2026-10-21',d:21,lbl:'MIÉ'},{k:'2026-10-22',d:22,lbl:'JUE'},{k:'2026-10-23',d:23,lbl:'VIE'},{k:'2026-10-24',d:24,lbl:'SÁB'},{k:'2026-10-25',d:25,lbl:'DOM'}],
    dayKeys:['2026-10-21','2026-10-22','2026-10-23','2026-10-24','2026-10-25'],
    dayShort:{'2026-10-21':'MIÉ 21','2026-10-22':'JUE 22','2026-10-23':'VIE 23','2026-10-24':'SÁB 24','2026-10-25':'DOM 25'},
    dayShort_en:{'2026-10-21':'WED 21','2026-10-22':'THU 22','2026-10-23':'FRI 23','2026-10-24':'SAT 24','2026-10-25':'SUN 25'},
    dayLong:{'2026-10-21':'Miércoles 21 de octubre','2026-10-22':'Jueves 22 de octubre','2026-10-23':'Viernes 23 de octubre','2026-10-24':'Sábado 24 de octubre','2026-10-25':'Domingo 25 de octubre'},
    prioLimit:3,
    films:null,posters:null,lbSlugs:{}
  },
  'cortoscali2026': {
    // EL NOMBRE es el del festival (@cortoscali); la edición va en fullName.
    name:'Cortos Cali',displayName:'Cortos Cali',
    fullName:'XVIII Festival Internacional de Cine Corto de Cali',shortName:'CORTOS CALI',
    city:'Cali',country:'CO',
    dates:'27–30 OCT',dates_en:'OCT 27–30',year:2026,timezoneOffset:'-05:00',
    // EL AFICHE OFICIAL de la edición 18 («Narrativas verticales», diseño de
    // @bengala_zul), del post de @cortoscali p/DdXQi8jgcMY (16 sep, 2160×2704):
    // el original estirado a 400×600, sin bandas ni recorte.
    keyArt:'/assets/keyart/cortoscali2026.jpg',
    // el subtítulo expande el nombre; el lema del año vive en el afiche
    tagline:'Festival Internacional de Cine Corto de Cali',
    instagram:'cortoscali', storageKey:'cortoscali2026_',festivalStartStr:'2026-10-27T00:00:00',festivalEndStr:'2026-10-30T23:59:00',
    festivalDates:{'2026-10-27':'2026-10-27','2026-10-28':'2026-10-28','2026-10-29':'2026-10-29','2026-10-30':'2026-10-30'},
    days:[{k:'2026-10-27',d:27,lbl:'MAR'},{k:'2026-10-28',d:28,lbl:'MIÉ'},{k:'2026-10-29',d:29,lbl:'JUE'},{k:'2026-10-30',d:30,lbl:'VIE'}],
    dayKeys:['2026-10-27','2026-10-28','2026-10-29','2026-10-30'],
    dayShort:{'2026-10-27':'MAR 27','2026-10-28':'MIÉ 28','2026-10-29':'JUE 29','2026-10-30':'VIE 30'},
    dayShort_en:{'2026-10-27':'TUE 27','2026-10-28':'WED 28','2026-10-29':'THU 29','2026-10-30':'FRI 30'},
    dayLong:{'2026-10-27':'Martes 27 de octubre','2026-10-28':'Miércoles 28 de octubre','2026-10-29':'Jueves 29 de octubre','2026-10-30':'Viernes 30 de octubre'},
    prioLimit:3,
    films:null,posters:null,lbSlugs:{}
  },
  'biff2026': {
    name:'BIFF',displayName:'BIFF',fullName:'BIFF 12 — Bogota International Film Festival',shortName:'BIFF',
    city:'Bogotá',country:'CO',
    dates:'8–14 OCT',dates_en:'OCT 8–14',year:2026,timezoneOffset:'-05:00',
    instagram:'biffcol', storageKey:'biff2026_',festivalStartStr:'2026-10-08T00:00:00',festivalEndStr:'2026-10-14T23:59:00',
    festivalDates:{'2026-10-08':'2026-10-08','2026-10-09':'2026-10-09','2026-10-10':'2026-10-10','2026-10-11':'2026-10-11','2026-10-12':'2026-10-12','2026-10-13':'2026-10-13','2026-10-14':'2026-10-14'},
    days:[{k:'2026-10-08',d:8,lbl:'JUE'},{k:'2026-10-09',d:9,lbl:'VIE'},{k:'2026-10-10',d:10,lbl:'SÁB'},{k:'2026-10-11',d:11,lbl:'DOM'},{k:'2026-10-12',d:12,lbl:'LUN'},{k:'2026-10-13',d:13,lbl:'MAR'},{k:'2026-10-14',d:14,lbl:'MIÉ'}],
    dayKeys:['2026-10-08','2026-10-09','2026-10-10','2026-10-11','2026-10-12','2026-10-13','2026-10-14'],
    dayShort:{'2026-10-08':'JUE 8','2026-10-09':'VIE 9','2026-10-10':'SÁB 10','2026-10-11':'DOM 11','2026-10-12':'LUN 12','2026-10-13':'MAR 13','2026-10-14':'MIÉ 14'},
    dayShort_en:{'2026-10-08':'THU 8','2026-10-09':'FRI 9','2026-10-10':'SAT 10','2026-10-11':'SUN 11','2026-10-12':'MON 12','2026-10-13':'TUE 13','2026-10-14':'WED 14'},
    dayLong:{'2026-10-08':'Jueves 8 de octubre','2026-10-09':'Viernes 9 de octubre','2026-10-10':'Sábado 10 de octubre','2026-10-11':'Domingo 11 de octubre','2026-10-12':'Lunes 12 de octubre','2026-10-13':'Martes 13 de octubre','2026-10-14':'Miércoles 14 de octubre'},
    // LA IMAGEN OFICIAL de la edición, del post de @biffcol (DcSJVx7O19W), sin el
    // «Programación» que lleva la portada del PDF (pedido de Juan), 3:4 → 2:3.
    keyArt:'/assets/keyart/biff2026-v3.jpg',
    // la sigla ya es el nombre: el subtítulo dice qué es
    tagline:'Bogota International Film Festival',
    // boleta en la Cinemateca (tuboleta, por función) y en Cine Colombia; entrada
    // libre en la muestra de cortos, las charlas y un cine concierto
    ticketing_model:'mixed',
    prioLimit:5,
    films:null,posters:null,lbSlugs:{}
  },
  'popayan2026': {
    name:'Cine Corto Popayán',displayName:'Cine Corto Popayán',fullName:'17 Festival de Cine Corto de Popayán',shortName:'CINECORTO',
    city:'Popayán',country:'CO',
    dates:'5–11 OCT',dates_en:'OCT 5–11',year:2026,timezoneOffset:'-05:00',
    // EL AFICHE OFICIAL de la edición (@cinecortofest p/DdCljrXoEzp, lámina 1:
    // «5–11 octubre 2026 · teatro Bolívar · entrada libre»). 1:1 estirado a 2:3.
    keyArt:'/assets/keyart/popayan2026-v1.jpg',
    tagline:'Festival de Cortometraje Colombiano',
    instagram:'cinecortofest', storageKey:'popayan2026_',festivalStartStr:'2026-10-05T00:00:00',festivalEndStr:'2026-10-11T23:59:00',
    festivalDates:{'2026-10-05':'2026-10-05','2026-10-06':'2026-10-06','2026-10-07':'2026-10-07','2026-10-08':'2026-10-08','2026-10-09':'2026-10-09','2026-10-10':'2026-10-10','2026-10-11':'2026-10-11'},
    days:[{k:'2026-10-05',d:5,lbl:'LUN'},{k:'2026-10-06',d:6,lbl:'MAR'},{k:'2026-10-07',d:7,lbl:'MIÉ'},{k:'2026-10-08',d:8,lbl:'JUE'},{k:'2026-10-09',d:9,lbl:'VIE'},{k:'2026-10-10',d:10,lbl:'SÁB'},{k:'2026-10-11',d:11,lbl:'DOM'}],
    dayKeys:['2026-10-05','2026-10-06','2026-10-07','2026-10-08','2026-10-09','2026-10-10','2026-10-11'],
    dayShort:{'2026-10-05':'LUN 5','2026-10-06':'MAR 6','2026-10-07':'MIÉ 7','2026-10-08':'JUE 8','2026-10-09':'VIE 9','2026-10-10':'SÁB 10','2026-10-11':'DOM 11'},
    dayShort_en:{'2026-10-05':'MON 5','2026-10-06':'TUE 6','2026-10-07':'WED 7','2026-10-08':'THU 8','2026-10-09':'FRI 9','2026-10-10':'SAT 10','2026-10-11':'SUN 11'},
    dayLong:{'2026-10-05':'Lunes 5 de octubre','2026-10-06':'Martes 6 de octubre','2026-10-07':'Miércoles 7 de octubre','2026-10-08':'Jueves 8 de octubre','2026-10-09':'Viernes 9 de octubre','2026-10-10':'Sábado 10 de octubre','2026-10-11':'Domingo 11 de octubre'},
    prioLimit:3,
    films:null,posters:null,lbSlugs:{}
  },
  'mamut2026': {
    name:'Mamut',displayName:'Mamut',fullName:'Mamut 11 — Festival de Memoria Audiovisual',shortName:'MAMUT',
    city:'Medellín',country:'CO',
    dates:'5–11 OCT',dates_en:'OCT 5–11',year:2026,timezoneOffset:'-05:00',
    // LA IMAGEN OFICIAL de #MAMUT11 (@mamut_festival p/DdCI2ZGkQG-, «La imagen
    // de #MAMUT11 es gracias a @atravesar_un____rio»), sin el «Programación» de
    // la portada del carrusel. 4:5 estirado a 2:3.
    keyArt:'/assets/keyart/mamut2026-v3.jpg',
    // lo que el festival dice de sí mismo; «Mamut» ya es el nombre
    tagline:'Festival de Memoria Audiovisual',
    instagram:'mamut_festival', storageKey:'mamut2026_',festivalStartStr:'2026-10-05T00:00:00',festivalEndStr:'2026-10-11T23:59:00',
    festivalDates:{'2026-10-05':'2026-10-05','2026-10-06':'2026-10-06','2026-10-07':'2026-10-07','2026-10-08':'2026-10-08','2026-10-09':'2026-10-09','2026-10-10':'2026-10-10','2026-10-11':'2026-10-11'},
    days:[{k:'2026-10-05',d:5,lbl:'LUN'},{k:'2026-10-06',d:6,lbl:'MAR'},{k:'2026-10-07',d:7,lbl:'MIÉ'},{k:'2026-10-08',d:8,lbl:'JUE'},{k:'2026-10-09',d:9,lbl:'VIE'},{k:'2026-10-10',d:10,lbl:'SÁB'},{k:'2026-10-11',d:11,lbl:'DOM'}],
    dayKeys:['2026-10-05','2026-10-06','2026-10-07','2026-10-08','2026-10-09','2026-10-10','2026-10-11'],
    dayShort:{'2026-10-05':'LUN 5','2026-10-06':'MAR 6','2026-10-07':'MIÉ 7','2026-10-08':'JUE 8','2026-10-09':'VIE 9','2026-10-10':'SÁB 10','2026-10-11':'DOM 11'},
    dayShort_en:{'2026-10-05':'MON 5','2026-10-06':'TUE 6','2026-10-07':'WED 7','2026-10-08':'THU 8','2026-10-09':'FRI 9','2026-10-10':'SAT 10','2026-10-11':'SUN 11'},
    dayLong:{'2026-10-05':'Lunes 5 de octubre','2026-10-06':'Martes 6 de octubre','2026-10-07':'Miércoles 7 de octubre','2026-10-08':'Jueves 8 de octubre','2026-10-09':'Viernes 9 de octubre','2026-10-10':'Sábado 10 de octubre','2026-10-11':'Domingo 11 de octubre'},
    prioLimit:3,
    films:null,posters:null,lbSlugs:{}
  },
  'filcmar2026': {
    name:'FILCMAR',displayName:'FILCMAR',fullName:'FILCMAR — 8° Festival de Cine de Marinilla',shortName:'FILCMAR',
    city:'Marinilla',country:'CO',
    dates:'9–13 OCT',dates_en:'OCT 9–13',year:2026,timezoneOffset:'-05:00',
    // EL AFICHE OFICIAL de la 8.ª edición, «Érase una vez en Marinilla» (el del
    // post del festival; copia en alta del artículo de CoCrea, colombiacrea.org,
    // sep 2026). 4:5 estirado a 2:3.
    keyArt:'/assets/keyart/filcmar2026-v2.jpg',
    // lo que el festival dice de sí mismo (bio de @filcmar: «8º Festival de Cine de Marinilla»)
    tagline:'Festival de Cine de Marinilla',
    instagram:'filcmar', storageKey:'filcmar2026_',festivalStartStr:'2026-10-09T00:00:00',festivalEndStr:'2026-10-13T23:59:00',
    festivalDates:{'2026-10-09':'2026-10-09','2026-10-10':'2026-10-10','2026-10-11':'2026-10-11','2026-10-12':'2026-10-12','2026-10-13':'2026-10-13'},
    days:[{k:'2026-10-09',d:9,lbl:'VIE'},{k:'2026-10-10',d:10,lbl:'SÁB'},{k:'2026-10-11',d:11,lbl:'DOM'},{k:'2026-10-12',d:12,lbl:'LUN'},{k:'2026-10-13',d:13,lbl:'MAR'}],
    dayKeys:['2026-10-09','2026-10-10','2026-10-11','2026-10-12','2026-10-13'],
    dayShort:{'2026-10-09':'VIE 9','2026-10-10':'SÁB 10','2026-10-11':'DOM 11','2026-10-12':'LUN 12','2026-10-13':'MAR 13'},
    dayShort_en:{'2026-10-09':'FRI 9','2026-10-10':'SAT 10','2026-10-11':'SUN 11','2026-10-12':'MON 12','2026-10-13':'TUE 13'},
    dayLong:{'2026-10-09':'Viernes 9 de octubre','2026-10-10':'Sábado 10 de octubre','2026-10-11':'Domingo 11 de octubre','2026-10-12':'Lunes 12 de octubre','2026-10-13':'Martes 13 de octubre'},
    prioLimit:3,
    films:null,posters:null,lbSlugs:{}
  },
  'ficcali2026': {
    name:'FICCALI',displayName:'FICCALI',fullName:'FICCALI 18 — Festival Internacional de Cine de Cali',shortName:'FICCALI',
    // EL AFICHE OFICIAL de la XVIII edición, de Erick Ortega (@cali_doso_):
    // @festivaldecinecali p/DdAPzU_MU3i, 1440×1920 (3:4) estirado a 2:3.
    keyArt:'/assets/keyart/ficcali2026-v1.jpg',
    tagline:'Festival Internacional de Cine de Cali',
    city:'Cali',country:'CO',
    dates:'16–25 OCT',dates_en:'OCT 16–25',year:2026,timezoneOffset:'-05:00',
    storageKey:'ficcali2026_',festivalStartStr:'2026-10-16T00:00:00',festivalEndStr:'2026-10-25T23:00:00',
    festivalDates:{'2026-10-16':'2026-10-16','2026-10-17':'2026-10-17','2026-10-18':'2026-10-18','2026-10-19':'2026-10-19','2026-10-20':'2026-10-20','2026-10-21':'2026-10-21','2026-10-22':'2026-10-22','2026-10-23':'2026-10-23','2026-10-24':'2026-10-24','2026-10-25':'2026-10-25'},
    days:[{k:'2026-10-16',d:16,lbl:'VIE'},{k:'2026-10-17',d:17,lbl:'SÁB'},{k:'2026-10-18',d:18,lbl:'DOM'},{k:'2026-10-19',d:19,lbl:'LUN'},{k:'2026-10-20',d:20,lbl:'MAR'},{k:'2026-10-21',d:21,lbl:'MIÉ'},{k:'2026-10-22',d:22,lbl:'JUE'},{k:'2026-10-23',d:23,lbl:'VIE'},{k:'2026-10-24',d:24,lbl:'SÁB'},{k:'2026-10-25',d:25,lbl:'DOM'}],
    dayKeys:['2026-10-16','2026-10-17','2026-10-18','2026-10-19','2026-10-20','2026-10-21','2026-10-22','2026-10-23','2026-10-24','2026-10-25'],
    dayShort:{'2026-10-16':'VIE 16','2026-10-17':'SÁB 17','2026-10-18':'DOM 18','2026-10-19':'LUN 19','2026-10-20':'MAR 20','2026-10-21':'MIÉ 21','2026-10-22':'JUE 22','2026-10-23':'VIE 23','2026-10-24':'SÁB 24','2026-10-25':'DOM 25'},
    dayShort_en:{'2026-10-16':'FRI 16','2026-10-17':'SAT 17','2026-10-18':'SUN 18','2026-10-19':'MON 19','2026-10-20':'TUE 20','2026-10-21':'WED 21','2026-10-22':'THU 22','2026-10-23':'FRI 23','2026-10-24':'SAT 24','2026-10-25':'SUN 25'},
    dayLong:{'2026-10-16':'Viernes 16 de octubre','2026-10-17':'Sábado 17 de octubre','2026-10-18':'Domingo 18 de octubre','2026-10-19':'Lunes 19 de octubre','2026-10-20':'Martes 20 de octubre','2026-10-21':'Miércoles 21 de octubre','2026-10-22':'Jueves 22 de octubre','2026-10-23':'Viernes 23 de octubre','2026-10-24':'Sábado 24 de octubre','2026-10-25':'Domingo 25 de octubre'},
    prioLimit:5,eventPosterLabel:['EVENTO',''],
    films:null,posters:null,lbSlugs:{}
  },
  'bhff2026': {
    name:'Bogotá Horror',displayName:'Bogotá Horror',fullName:'Bogotá Horror Film Festival 8',shortName:'BHFF',
    // LA IMAGEN DE LA 8ª EDICIÓN en vertical (la lápida de la convocatoria, sin
    // texto): 582×775 (3:4), de la nota de prensa en mochilawild.com, estirada a
    // 2:3. El festival no publica un afiche vertical propio. Aprobada por Juan (7 oct).
    keyArt:'/assets/keyart/bhff2026-v1.jpg',
    tagline:'Festival de Cine de Horror',
    city:'Bogotá',country:'CO',
    dates:'22–31 OCT',dates_en:'OCT 22–31',year:2026,timezoneOffset:'-05:00',
    storageKey:'bhff2026_',festivalStartStr:'2026-10-22T00:00:00',festivalEndStr:'2026-10-31T23:59:00',
    festivalDates:{'2026-10-22':'2026-10-22','2026-10-23':'2026-10-23','2026-10-24':'2026-10-24','2026-10-25':'2026-10-25','2026-10-26':'2026-10-26','2026-10-27':'2026-10-27','2026-10-28':'2026-10-28','2026-10-29':'2026-10-29','2026-10-30':'2026-10-30','2026-10-31':'2026-10-31'},
    days:[{k:'2026-10-22',d:22,lbl:'JUE'},{k:'2026-10-23',d:23,lbl:'VIE'},{k:'2026-10-24',d:24,lbl:'SÁB'},{k:'2026-10-25',d:25,lbl:'DOM'},{k:'2026-10-26',d:26,lbl:'LUN'},{k:'2026-10-27',d:27,lbl:'MAR'},{k:'2026-10-28',d:28,lbl:'MIÉ'},{k:'2026-10-29',d:29,lbl:'JUE'},{k:'2026-10-30',d:30,lbl:'VIE'},{k:'2026-10-31',d:31,lbl:'SÁB'}],
    dayKeys:['2026-10-22','2026-10-23','2026-10-24','2026-10-25','2026-10-26','2026-10-27','2026-10-28','2026-10-29','2026-10-30','2026-10-31'],
    dayShort:{'2026-10-22':'JUE 22','2026-10-23':'VIE 23','2026-10-24':'SÁB 24','2026-10-25':'DOM 25','2026-10-26':'LUN 26','2026-10-27':'MAR 27','2026-10-28':'MIÉ 28','2026-10-29':'JUE 29','2026-10-30':'VIE 30','2026-10-31':'SÁB 31'},
    dayShort_en:{'2026-10-22':'THU 22','2026-10-23':'FRI 23','2026-10-24':'SAT 24','2026-10-25':'SUN 25','2026-10-26':'MON 26','2026-10-27':'TUE 27','2026-10-28':'WED 28','2026-10-29':'THU 29','2026-10-30':'FRI 30','2026-10-31':'SAT 31'},
    dayLong:{'2026-10-22':'Jueves 22 de octubre','2026-10-23':'Viernes 23 de octubre','2026-10-24':'Sábado 24 de octubre','2026-10-25':'Domingo 25 de octubre','2026-10-26':'Lunes 26 de octubre','2026-10-27':'Martes 27 de octubre','2026-10-28':'Miércoles 28 de octubre','2026-10-29':'Jueves 29 de octubre','2026-10-30':'Viernes 30 de octubre','2026-10-31':'Sábado 31 de octubre'},
    prioLimit:5,eventPosterLabel:['EVENTO',''],
    // Boleta de $7.000 en la Cinemateca de Bogotá; entrada libre hasta completar
    // aforo en las sedes comunitarias (Canal Trece). Sin este campo la app no
    // pintaba ninguna función como paga (revisión del 15 oct 2026).
    ticketing_model:'mixed',
    films:null,posters:null,lbSlugs:{}
  },
  'ficica2026': {
    name:'FICICA',displayName:'FICICA',fullName:'FICICA 2026 — Festival Internacional de Cortometrajes Cine a la Calle',shortName:'FICICA',
    // LA IMAGEN DE LA EDICIÓN: el escudo «FICICA 26» de su web (pin-festival-main,
    // 823×1080), estirado a 2:3. Propuesta, a confirmar con Juan (15 oct).
    keyArt:'/assets/keyart/ficica2026-v2.jpg',
    tagline:'Festival Internacional de Cortometrajes',
    city:'Barranquilla',country:'CO',
    dates:'20–24 OCT',dates_en:'OCT 20–24',year:2026,timezoneOffset:'-05:00',
    storageKey:'ficica2026_',festivalStartStr:'2026-10-20T00:00:00',festivalEndStr:'2026-10-24T23:59:00',
    festivalDates:{'2026-10-20':'2026-10-20','2026-10-21':'2026-10-21','2026-10-22':'2026-10-22','2026-10-23':'2026-10-23','2026-10-24':'2026-10-24'},
    days:[{k:'2026-10-20',d:20,lbl:'MAR'},{k:'2026-10-21',d:21,lbl:'MIÉ'},{k:'2026-10-22',d:22,lbl:'JUE'},{k:'2026-10-23',d:23,lbl:'VIE'},{k:'2026-10-24',d:24,lbl:'SÁB'}],
    dayKeys:['2026-10-20','2026-10-21','2026-10-22','2026-10-23','2026-10-24'],
    dayShort:{'2026-10-20':'MAR 20','2026-10-21':'MIÉ 21','2026-10-22':'JUE 22','2026-10-23':'VIE 23','2026-10-24':'SÁB 24'},
    dayShort_en:{'2026-10-20':'TUE 20','2026-10-21':'WED 21','2026-10-22':'THU 22','2026-10-23':'FRI 23','2026-10-24':'SAT 24'},
    dayLong:{'2026-10-20':'Martes 20 de octubre','2026-10-21':'Miércoles 21 de octubre','2026-10-22':'Jueves 22 de octubre','2026-10-23':'Viernes 23 de octubre','2026-10-24':'Sábado 24 de octubre'},
    prioLimit:3,eventPosterLabel:['EVENTO',''],
    films:null,posters:null,lbSlugs:{}
  },
  'ficidi2026': {
    name:'FICIDI',displayName:'FICIDI',fullName:'IV FICIDI — Festival Internacional de Cine Diverso',shortName:'FICIDI',
    // EL AFICHE OFICIAL de la IV edición («POST POSTER FICIDI IV», Drive de
    // recursos visuales del festival, 29 oct 2026), 4:5 estirado a 2:3.
    keyArt:'/assets/keyart/ficidi2026-v2.jpg',
    tagline:'Festival Internacional de Cine Diverso',
    city:'Barranquilla',country:'CO',
    instagram:'festivaldecinediverso',
    dates:'3–7 NOV',dates_en:'NOV 3–7',year:2026,timezoneOffset:'-05:00',
    storageKey:'ficidi2026_',festivalStartStr:'2026-11-03T00:00:00',festivalEndStr:'2026-11-07T23:59:00',
    festivalDates:{'2026-11-03':'2026-11-03','2026-11-04':'2026-11-04','2026-11-05':'2026-11-05','2026-11-06':'2026-11-06','2026-11-07':'2026-11-07'},
    days:[{k:'2026-11-03',d:3,lbl:'MAR'},{k:'2026-11-04',d:4,lbl:'MIÉ'},{k:'2026-11-05',d:5,lbl:'JUE'},{k:'2026-11-06',d:6,lbl:'VIE'},{k:'2026-11-07',d:7,lbl:'SÁB'}],
    dayKeys:['2026-11-03','2026-11-04','2026-11-05','2026-11-06','2026-11-07'],
    dayShort:{'2026-11-03':'MAR 3','2026-11-04':'MIÉ 4','2026-11-05':'JUE 5','2026-11-06':'VIE 6','2026-11-07':'SÁB 7'},
    dayShort_en:{'2026-11-03':'TUE 3','2026-11-04':'WED 4','2026-11-05':'THU 5','2026-11-06':'FRI 6','2026-11-07':'SAT 7'},
    dayLong:{'2026-11-03':'Martes 3 de noviembre','2026-11-04':'Miércoles 4 de noviembre','2026-11-05':'Jueves 5 de noviembre','2026-11-06':'Viernes 6 de noviembre','2026-11-07':'Sábado 7 de noviembre'},
    prioLimit:3,eventPosterLabel:['EVENTO',''],
    films:null,posters:null,lbSlugs:{}
  },
  'mambe2026': {
    // EL NOMBRE es el del festival (@festivalmambe); la edición va en fullName.
    name:'MAMBE',displayName:'MAMBE',fullName:'Festival MAMBE 2026 — 13.ª edición',shortName:'MAMBE',
    // EL AFICHE OFICIAL de la 13.ª edición (p/DfAg8PnFmir, lámina 1, 27 oct 2026,
    // «Diseño Poster: @mariana_medina.ph»), 3:4 estirado a 2:3.
    keyArt:'/assets/keyart/mambe2026-v2.jpg',
    // PENDIENTE DE JUAN: del pie de la programación («Cinco días de cine ambiental y étnico»)
    tagline:'Cine Ambiental y Étnico',
    city:'Florencia',country:'CO',
    instagram:'festivalmambe',
    dates:'3–7 NOV',dates_en:'NOV 3–7',year:2026,timezoneOffset:'-05:00',
    storageKey:'mambe2026_',festivalStartStr:'2026-11-03T00:00:00',festivalEndStr:'2026-11-07T23:59:00',
    festivalDates:{'2026-11-03':'2026-11-03','2026-11-04':'2026-11-04','2026-11-05':'2026-11-05','2026-11-06':'2026-11-06','2026-11-07':'2026-11-07'},
    days:[{k:'2026-11-03',d:3,lbl:'MAR'},{k:'2026-11-04',d:4,lbl:'MIÉ'},{k:'2026-11-05',d:5,lbl:'JUE'},{k:'2026-11-06',d:6,lbl:'VIE'},{k:'2026-11-07',d:7,lbl:'SÁB'}],
    dayKeys:['2026-11-03','2026-11-04','2026-11-05','2026-11-06','2026-11-07'],
    dayShort:{'2026-11-03':'MAR 3','2026-11-04':'MIÉ 4','2026-11-05':'JUE 5','2026-11-06':'VIE 6','2026-11-07':'SÁB 7'},
    dayShort_en:{'2026-11-03':'TUE 3','2026-11-04':'WED 4','2026-11-05':'THU 5','2026-11-06':'FRI 6','2026-11-07':'SAT 7'},
    dayLong:{'2026-11-03':'Martes 3 de noviembre','2026-11-04':'Miércoles 4 de noviembre','2026-11-05':'Jueves 5 de noviembre','2026-11-06':'Viernes 6 de noviembre','2026-11-07':'Sábado 7 de noviembre'},
    prioLimit:3,eventPosterLabel:['EVENTO',''],
    films:null,posters:null,lbSlugs:{}
  },
  'fantasmagoria2026': {
    name:'Fantasmagoría',displayName:'Fantasmagoría',fullName:'Fantasmagoría 8 — Festival Internacional de Cine Fantástico y de Terror de Medellín',shortName:'FANTASMAGORÍA',
    city:'Medellín',country:'CO',
    // 14–25 OCT: así lo dice su cartelera oficial (cartelerafantasmagoria.fan,
    // «del 14 al 25 de octubre») y su base v2 abre el 14 con dos actividades
    dates:'14–25 OCT',dates_en:'OCT 14–25',year:2026,timezoneOffset:'-05:00',
    // EL PÓSTER OFICIAL de la 8.ª edición (@mfantasmagoria p/DayyyJGFK86, lámina 1,
    // obra de Bastián Velásquez). 4:5 estirado a 2:3.
    keyArt:'/assets/keyart/fantasmagoria2026-v1.jpg',
    tagline:'Festival de Cine Fantástico y de Terror',
    // boleta en Colombo Americano, CineProx y MAMM (cobro especial); lo demás, libre
    ticketing_model:'mixed',
    storageKey:'fantasmagoria2026_',festivalStartStr:'2026-10-14T00:00:00',festivalEndStr:'2026-10-25T23:59:00',
    festivalDates:{'2026-10-14':'2026-10-14','2026-10-15':'2026-10-15','2026-10-16':'2026-10-16','2026-10-17':'2026-10-17','2026-10-18':'2026-10-18','2026-10-19':'2026-10-19','2026-10-20':'2026-10-20','2026-10-21':'2026-10-21','2026-10-22':'2026-10-22','2026-10-23':'2026-10-23','2026-10-24':'2026-10-24','2026-10-25':'2026-10-25'},
    days:[{k:'2026-10-14',d:14,lbl:'MIÉ'},{k:'2026-10-15',d:15,lbl:'JUE'},{k:'2026-10-16',d:16,lbl:'VIE'},{k:'2026-10-17',d:17,lbl:'SÁB'},{k:'2026-10-18',d:18,lbl:'DOM'},{k:'2026-10-19',d:19,lbl:'LUN'},{k:'2026-10-20',d:20,lbl:'MAR'},{k:'2026-10-21',d:21,lbl:'MIÉ'},{k:'2026-10-22',d:22,lbl:'JUE'},{k:'2026-10-23',d:23,lbl:'VIE'},{k:'2026-10-24',d:24,lbl:'SÁB'},{k:'2026-10-25',d:25,lbl:'DOM'}],
    dayKeys:['2026-10-14','2026-10-15','2026-10-16','2026-10-17','2026-10-18','2026-10-19','2026-10-20','2026-10-21','2026-10-22','2026-10-23','2026-10-24','2026-10-25'],
    dayShort:{'2026-10-14':'MIÉ 14','2026-10-15':'JUE 15','2026-10-16':'VIE 16','2026-10-17':'SÁB 17','2026-10-18':'DOM 18','2026-10-19':'LUN 19','2026-10-20':'MAR 20','2026-10-21':'MIÉ 21','2026-10-22':'JUE 22','2026-10-23':'VIE 23','2026-10-24':'SÁB 24','2026-10-25':'DOM 25'},
    dayShort_en:{'2026-10-14':'WED 14','2026-10-15':'THU 15','2026-10-16':'FRI 16','2026-10-17':'SAT 17','2026-10-18':'SUN 18','2026-10-19':'MON 19','2026-10-20':'TUE 20','2026-10-21':'WED 21','2026-10-22':'THU 22','2026-10-23':'FRI 23','2026-10-24':'SAT 24','2026-10-25':'SUN 25'},
    dayLong:{'2026-10-14':'Miércoles 14 de octubre','2026-10-15':'Jueves 15 de octubre','2026-10-16':'Viernes 16 de octubre','2026-10-17':'Sábado 17 de octubre','2026-10-18':'Domingo 18 de octubre','2026-10-19':'Lunes 19 de octubre','2026-10-20':'Martes 20 de octubre','2026-10-21':'Miércoles 21 de octubre','2026-10-22':'Jueves 22 de octubre','2026-10-23':'Viernes 23 de octubre','2026-10-24':'Sábado 24 de octubre','2026-10-25':'Domingo 25 de octubre'},
    prioLimit:5,
    films:null,posters:null,lbSlugs:{}
  },
  'midbo2026': {
    name:'MIDBO',displayName:'MIDBO',fullName:'28 MIDBO — Muestra Internacional Documental de Bogotá',shortName:'MIDBO',
    city:'Bogotá',country:'CO',
    dates:'27 OCT–4 NOV',dates_en:'OCT 27–NOV 4',year:2026,timezoneOffset:'-05:00',
    // EL AFICHE OFICIAL de la 28 MIDBO, «Sonido imprescindible» (Marta Rodríguez
    // fotografiada por Jorge Silva en el rodaje de Chircales), @midbo_doc
    // p/DeSf11QJ-Mp, 9 oct 2026. 3:4 estirado a 2:3 (keyart-estirado).
    keyArt:'/assets/keyart/midbo2026.jpg',
    // lo que el festival dice de sí mismo; «MIDBO» ya es el nombre
    tagline:'Muestra Internacional Documental de Bogotá',
    instagram:'midbo_doc', storageKey:'midbo2026_',festivalStartStr:'2026-10-27T00:00:00',festivalEndStr:'2026-11-04T23:59:00',
    festivalDates:{'2026-10-27':'2026-10-27','2026-10-28':'2026-10-28','2026-10-29':'2026-10-29','2026-10-30':'2026-10-30','2026-10-31':'2026-10-31','2026-11-01':'2026-11-01','2026-11-02':'2026-11-02','2026-11-03':'2026-11-03','2026-11-04':'2026-11-04'},
    days:[{k:'2026-10-27',d:27,lbl:'MAR'},{k:'2026-10-28',d:28,lbl:'MIÉ'},{k:'2026-10-29',d:29,lbl:'JUE'},{k:'2026-10-30',d:30,lbl:'VIE'},{k:'2026-10-31',d:31,lbl:'SÁB'},{k:'2026-11-01',d:1,lbl:'DOM'},{k:'2026-11-02',d:2,lbl:'LUN'},{k:'2026-11-03',d:3,lbl:'MAR'},{k:'2026-11-04',d:4,lbl:'MIÉ'}],
    dayKeys:['2026-10-27','2026-10-28','2026-10-29','2026-10-30','2026-10-31','2026-11-01','2026-11-02','2026-11-03','2026-11-04'],
    dayShort:{'2026-10-27':'MAR 27','2026-10-28':'MIÉ 28','2026-10-29':'JUE 29','2026-10-30':'VIE 30','2026-10-31':'SÁB 31','2026-11-01':'DOM 1','2026-11-02':'LUN 2','2026-11-03':'MAR 3','2026-11-04':'MIÉ 4'},
    dayShort_en:{'2026-10-27':'TUE 27','2026-10-28':'WED 28','2026-10-29':'THU 29','2026-10-30':'FRI 30','2026-10-31':'SAT 31','2026-11-01':'SUN 1','2026-11-02':'MON 2','2026-11-03':'TUE 3','2026-11-04':'WED 4'},
    dayLong:{'2026-10-27':'Martes 27 de octubre','2026-10-28':'Miércoles 28 de octubre','2026-10-29':'Jueves 29 de octubre','2026-10-30':'Viernes 30 de octubre','2026-10-31':'Sábado 31 de octubre','2026-11-01':'Domingo 1 de noviembre','2026-11-02':'Lunes 2 de noviembre','2026-11-03':'Martes 3 de noviembre','2026-11-04':'Miércoles 4 de noviembre'},
    prioLimit:5,
    ticketing_model:'mixed', // boletería de la Cinemateca en TuBoleta ($7.000 + servicio, ticket_url por función) + entrada libre en las demás sedes; el seminario, gratis con inscripción
    films:null,posters:null,lbSlugs:{}
  },
  'mubibogota2026': {
    name:'MUBI Fest',displayName:'MUBI Fest',fullName:'MUBI Fest Bogotá 2026',shortName:'MUBI Fest',
    city:'Bogotá',country:'CO',
    dates:'24–25 OCT',dates_en:'OCT 24–25',year:2026,timezoneOffset:'-05:00',
    // EL ARTE OFICIAL de Bogotá: el reel de @mubilat del 10 sep (DdHG4RVEsOy),
    // 9:16 recortado por arriba a 2:3 por indicación de Juan (14 oct)
    keyArt:'/assets/keyart/mubibogota2026.jpg',
    // lo que el festival dice de sí mismo en su arte: «Ve gran cine»
    tagline:'Ve Gran Cine',
    instagram:'mubilat', storageKey:'mubibogota2026_',festivalStartStr:'2026-10-24T00:00:00',festivalEndStr:'2026-10-25T23:59:00',
    festivalDates:{'2026-10-24':'2026-10-24','2026-10-25':'2026-10-25'},
    days:[{k:'2026-10-24',d:24,lbl:'SÁB'},{k:'2026-10-25',d:25,lbl:'DOM'}],
    dayKeys:['2026-10-24','2026-10-25'],
    dayShort:{'2026-10-24':'SÁB 24','2026-10-25':'DOM 25'},
    dayShort_en:{'2026-10-24':'SAT 24','2026-10-25':'SUN 25'},
    dayLong:{'2026-10-24':'Sábado 24 de octubre','2026-10-25':'Domingo 25 de octubre'},
    prioLimit:5,
    ticketing_model:'mixed', // al aire libre gratis; seis funciones en sala con boleta en Entradas Inteligentes (enlace por función)
    eventPosterLabel:['EVENTO',''],
    films:null,posters:null,lbSlugs:{}
  },
  'funza2026': {
    name:'Festival de Cine Funza',displayName:'Festival de Cine Funza',fullName:'4.º Festival de Cine Funza 2026',shortName:'FUNZA',
    city:'Funza',country:'CO',
    dates:'18–21 NOV',dates_en:'NOV 18–21',year:2026,timezoneOffset:'-05:00',
    // EL AFICHE OFICIAL de la 4.ª edición («Ojos siempre abiertos»), 2:3 de origen,
    // llevado a 400×600 (keyart-estirado). Lo mandó el festival a Juan el 25 oct
    keyArt:'/assets/keyart/funza2026.jpg',
    // PROPUESTA a Juan (25 oct): dice qué es sin repetir el nombre; el lema vive en el afiche
    tagline:'',
    storageKey:'funza2026_',festivalStartStr:'2026-11-18T00:00:00',festivalEndStr:'2026-11-21T23:59:00',
    festivalDates:{'2026-11-18':'2026-11-18','2026-11-19':'2026-11-19','2026-11-20':'2026-11-20','2026-11-21':'2026-11-21'},
    days:[{k:'2026-11-18',d:18,lbl:'MIÉ'},{k:'2026-11-19',d:19,lbl:'JUE'},{k:'2026-11-20',d:20,lbl:'VIE'},{k:'2026-11-21',d:21,lbl:'SÁB'}],
    dayKeys:['2026-11-18','2026-11-19','2026-11-20','2026-11-21'],
    dayShort:{'2026-11-18':'MIÉ 18','2026-11-19':'JUE 19','2026-11-20':'VIE 20','2026-11-21':'SÁB 21'},
    dayShort_en:{'2026-11-18':'WED 18','2026-11-19':'THU 19','2026-11-20':'FRI 20','2026-11-21':'SAT 21'},
    dayLong:{'2026-11-18':'Miércoles 18 de noviembre','2026-11-19':'Jueves 19 de noviembre','2026-11-20':'Viernes 20 de noviembre','2026-11-21':'Sábado 21 de noviembre'},
    prioLimit:3,eventPosterLabel:['EVENTO',''],
    films:null,posters:null,lbSlugs:{}
  },
  'miradas2026': {
    name:'Miradas Medellín',displayName:'Miradas Medellín',fullName:'Miradas Medellín 2026 — Festival de cine y artes audiovisuales',shortName:'MIRADAS',
    city:'Medellín',country:'CO',
    dates:'3–8 NOV',dates_en:'NOV 3–8',year:2026,timezoneOffset:'-05:00',
    // LA PORTADA de la programación oficial (PDF de la Alcaldía, 20 oct 2026, pág. 1):
    // el arte de la edición con «MIRADAS MDE 2026». Estirada a 400×600 (keyart-estirado)
    keyArt:'/assets/keyart/miradas2026-v1.jpg',
    // el descriptor que el festival imprime junto a su nombre (portada del PDF)
    tagline:'Festival de Cine y Artes Audiovisuales',
    storageKey:'miradas2026_',festivalStartStr:'2026-11-03T00:00:00',festivalEndStr:'2026-11-08T23:59:00',
    festivalDates:{'2026-11-03':'2026-11-03','2026-11-04':'2026-11-04','2026-11-05':'2026-11-05','2026-11-06':'2026-11-06','2026-11-07':'2026-11-07','2026-11-08':'2026-11-08'},
    days:[{k:'2026-11-03',d:3,lbl:'MAR'},{k:'2026-11-04',d:4,lbl:'MIÉ'},{k:'2026-11-05',d:5,lbl:'JUE'},{k:'2026-11-06',d:6,lbl:'VIE'},{k:'2026-11-07',d:7,lbl:'SÁB'},{k:'2026-11-08',d:8,lbl:'DOM'}],
    dayKeys:['2026-11-03','2026-11-04','2026-11-05','2026-11-06','2026-11-07','2026-11-08'],
    dayShort:{'2026-11-03':'MAR 3','2026-11-04':'MIÉ 4','2026-11-05':'JUE 5','2026-11-06':'VIE 6','2026-11-07':'SÁB 7','2026-11-08':'DOM 8'},
    dayShort_en:{'2026-11-03':'TUE 3','2026-11-04':'WED 4','2026-11-05':'THU 5','2026-11-06':'FRI 6','2026-11-07':'SAT 7','2026-11-08':'SUN 8'},
    dayLong:{'2026-11-03':'Martes 3 de noviembre','2026-11-04':'Miércoles 4 de noviembre','2026-11-05':'Jueves 5 de noviembre','2026-11-06':'Viernes 6 de noviembre','2026-11-07':'Sábado 7 de noviembre','2026-11-08':'Domingo 8 de noviembre'},
    prioLimit:5,eventPosterLabel:['EVENTO',''],
    films:null,posters:null,lbSlugs:{}
  },
  'narrarelfuturo2026': {
    name:'#NarrarElFuturo',fullName:'#NarrarElFuturo — Festival de Cine & Nuevos Medios',shortName:'NEF',
    city:'Bogotá',country:'CO',
    dates:'15–20 SEP',dates_en:'SEP 15–20',year:2026,timezoneOffset:'-05:00',
    keyArt:'/assets/keyart/narrarelfuturo2026-v2.jpg',
    storageKey:'narrarelfuturo2026_',festivalStartStr:'2026-09-15T00:00:00',festivalEndStr:'2026-09-20T23:00:00',
    festivalDates:{'2026-09-15':'2026-09-15','2026-09-16':'2026-09-16','2026-09-17':'2026-09-17','2026-09-18':'2026-09-18','2026-09-19':'2026-09-19','2026-09-20':'2026-09-20'},
    days:[{k:'2026-09-15',d:15,lbl:'MAR'},{k:'2026-09-16',d:16,lbl:'MIÉ'},{k:'2026-09-17',d:17,lbl:'JUE'},{k:'2026-09-18',d:18,lbl:'VIE'},{k:'2026-09-19',d:19,lbl:'SÁB'},{k:'2026-09-20',d:20,lbl:'DOM'}],
    dayKeys:['2026-09-15','2026-09-16','2026-09-17','2026-09-18','2026-09-19','2026-09-20'],
    dayShort:{'2026-09-15':'MAR 15','2026-09-16':'MIÉ 16','2026-09-17':'JUE 17','2026-09-18':'VIE 18','2026-09-19':'SÁB 19','2026-09-20':'DOM 20'},
    dayShort_en:{'2026-09-15':'TUE 15','2026-09-16':'WED 16','2026-09-17':'THU 17','2026-09-18':'FRI 18','2026-09-19':'SAT 19','2026-09-20':'SUN 20'},
    dayLong:{'2026-09-15':'Martes 15 de septiembre','2026-09-16':'Miércoles 16 de septiembre','2026-09-17':'Jueves 17 de septiembre','2026-09-18':'Viernes 18 de septiembre','2026-09-19':'Sábado 19 de septiembre','2026-09-20':'Domingo 20 de septiembre'},
    prioLimit:5,eventPosterLabel:['EVENTO',''],
    tagline:'Festival de Cine & Nuevos Medios',
    ticketing_model:'mixed', // entrada libre (Tadeo, Fontanar, Sala VR) + boletería de la Cinemateca (ticket_url por función) + inscripción en los talleres
    films:null,posters:null,lbSlugs:{}
  },
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

// FICHAS DEL ALMACÉN (Etapa 2·B1, 19 oct 2026): la última copia vista se aplica
// ACÁ, antes de derivar nada (_DEFAULT_FEST_ID, la portada), para que el arranque ya
// vea el afiche, las fechas o el festival nuevo publicados sin pasar por la app.
// La copia fresca la baja datos-fuente.js (refrescarFichas) y queda para la próxima.
aplicarFichas(FESTIVAL_CONFIG, fichasGuardadas());

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
  // ── Miradas Medellín 2026 · Medellín (índice del PDF oficial) ─────────
  '🏙️ Cine Hecho en Medellín': 'Muestra / País',
  '🇨🇴 Cine Colombiano': 'Muestra / País',
  '🌎 Cine Iberoamericano': 'Perspectivas / Miradas',
  '🎞️ Programas de Cortos': 'Cortos / Programas',
  '🎥 Retrospectiva Fernando Eimbcke': 'Retrospectiva / Tributo',
  '👨‍👩‍👧 Cine Familiar': 'Especiales / Eventos',
  '🤟 Cine Accesible': 'Especiales / Eventos',
  '🏘️ Cine Comunitario - Hecho en Medellín': 'Muestra / País',
  '🗂️ Cine Memoria': 'Retrospectiva / Tributo',
  '🌀 Cine Expandido - Hecho en Medellín': 'Especiales / Eventos',
  '🪐 Cine en el Domo': 'Especiales / Eventos',
  '🚚 Cinemateca Móvil': 'Especiales / Eventos',
  '🛠️ Talleres de Desarrollo y Mediación de Audiencias': 'Charlas / Industria',
  '🤝 Días de Industria': 'Charlas / Industria',
  '🎆 Evento de Clausura': 'Clausura',
  // ── Festival de Cine Funza 2026 · Funza (el «Componente» de la agenda) ─
  '📚 Literatura / Artes Escénicas / Cine': 'Especiales / Eventos',
  '💬 Conversatorio': 'Charlas / Industria',
  '🎞️ Exhibición Cinematográfica': 'Muestra / País',
  '🛠️ Formación Especializada': 'Charlas / Industria',
  '🤝 Encuentro Departamental': 'Charlas / Industria',
  '📡 Comunicaciones': 'Charlas / Industria',
  '🎥 Audiovisuales / Cine': 'Charlas / Industria',
  '📷 Fotografía / Narrativas': 'Charlas / Industria',
  '📱 Circulación / Industria': 'Charlas / Industria',
  '🎤 Conversatorio / Clausura': 'Clausura',
  '🏆 Premiación': 'Especiales / Eventos',
  // ── Cortos Cali 2026 · Cali ───────────────────────────────────────────
  '🌎 Selección Oficial Internacional': 'Competencia',
  '🎬 Selección Oficial Nacional': 'Competencia',
  '🎓 Selección Oficial Internacional Universitaria': 'Competencia',
  '📚 Selección Oficial Nacional Universitaria': 'Competencia',
  '🎤 Masterclass': 'Charlas / Industria',
  // ── Anibia 2026 · Bogotá ───────────────────────────────────────────────
  '🌋 Surgentes': 'Perspectivas / Miradas',
  '🎨 Con Acento Nacional': 'Competencia',
  '🎞️ Día Internacional de la Animación': 'Charlas / Industria',
  '🌊 Costa a Costa': 'Muestra / País',
  '🔗 Conexión': 'Retrospectiva / Tributo',
  '🚂 Todxs a Bordo': 'Especiales / Eventos',
  '🎙️ Conexión de Largo Aliento': 'Charlas / Industria',
  '💬 Charla': 'Charlas / Industria',
  '🎻 Cine Concierto & Panel': 'Especiales / Eventos',
  '🖼️ Exposición': 'Especiales / Eventos',
  // ── Festival MAMBE 2026 · Florencia ───────────────────────────────────
  '🌿 Proyecciones': 'Muestra / País',
  // ── Guatapé Film Fest 2026 · Guatapé ──────────────────────────────────
  '🎬 Película Inaugural': 'Apertura / Gala',
  '🏆 Competencia Internacional de Largometraje': 'Competencia',
  '🏅 Competencia Internacional de Cortometrajes': 'Competencia',
  '🎓 Competencia Nacional de Cine Universitario': 'Competencia',
  '🎞️ Muestra de Cine Colombiano': 'Muestra / País',
  '🤝 Muestra de Cine Comunitario Colombiano': 'Muestra / País',
  '🦋 Rumbo a los Macondo': 'Perspectivas / Miradas',
  '🌎 FIACINE': 'Muestra / País',
  '🌙 Cinema Luna': 'Especiales / Eventos',
  '🏡 Muestra Local': 'Muestra / País',
  '👻 Terror': 'Especiales / Eventos',
  '🪞 El Reflejo del Cine': 'Muestra / País',
  // («🎪 Actividades» ya está, con el mismo arquetipo)
  // ── Villa del Cine 12 · Villa de Leyva ─────────────────────────────────
  '👁️ Nuevas Miradas': 'Perspectivas / Miradas',
  '🗺️ Territorios': 'Muestra / País',
  '🌀 Narrativas Divergentes': 'Cortos / Programas',
  '🌱 Lenguajes Emergentes': 'Cortos / Programas',
  '🪁 Programación Infantil': 'Cortos / Programas',
  '🎬 Industria': 'Charlas / Industria',
  '🎓 Ruta Académica': 'Charlas / Industria',
  '🏆 Rumbo a los Macondo': 'Especiales / Eventos',
  '🎞️ Exhibición Especial': 'Retrospectiva / Tributo',
  '🎞️ Exhibición Patrimonial': 'Retrospectiva / Tributo',   // Villa del Cine, PDF del 6 oct (Aquileo Venganza)
  '🇨🇴 Competencia Largometrajes Nacionales': 'Competencia',   // FICCALI 18
  '🌍 Competencia Largometrajes Internacionales': 'Competencia',   // FICCALI 18
  '🎬 Competencia Cortometraje Nacional': 'Competencia',   // FICCALI 18
  '🏙️ Cali Ciudad Abierta': 'Muestra / País',   // FICCALI 18
  '🪶 Vanguardias Afro e Indígenas': 'Perspectivas / Miradas',   // FICCALI 18
  '🎵 Plano Sonoro': 'Cortos / Programas',   // FICCALI 18
  '🏘️ Cine Sin Límites': 'Especiales / Eventos',   // FICCALI 18
  '🎞️ Muestras de Muestras': 'Cortos / Programas',   // FICCALI 18
  '🧒 Muestra Infantil': 'Especiales / Eventos',   // FICCALI 18
  '🔍 Zoom': 'Perspectivas / Miradas',   // FICCALI 18
  '🔦 Foco Claire Simon': 'Retrospectiva / Tributo',   // FICCALI 18
  '🏛️ Clásicos': 'Retrospectiva / Tributo',   // FICCALI 18 (🎞️ ya es Muestras de Muestras)
  '🌀 Plano General': 'Muestra / País',   // FICCALI 18
  '🎶 ¡Que Viva la Música!': 'Especiales / Eventos',   // FICCALI 18
  '📽️ Proyecciones': 'Especiales / Eventos',   // FICCALI 18
  '🎓 Académico': 'Charlas / Industria',   // FICCALI 18
  '🤝 Conexiones': 'Charlas / Industria',   // FICCALI 18
  '🎉 Inauguración': 'Apertura / Gala',   // Bogotá Horror 8
  '🇨🇴 Franja Nacional': 'Competencia',   // Bogotá Horror 8
  '🌍 Franja Internacional': 'Cortos / Programas',   // Bogotá Horror 8
  '🌙 Clausura': 'Clausura',   // Bogotá Horror 8
  '🎙️ Comunicaciones': 'Charlas / Industria',
  // ── Festival de Cine de Jardín 11 · Jardín, Antioquia ──────────────────
  '🎬 Muestra Central': 'Muestra / País',
  '🔮 Caleidoscopio': 'Competencia',
  // ── 9° Festival Internacional de Cine Ciudad de Itagüí ─────────────────
  '🌍 Otras Miradas: Muestra Internacional': 'Muestra / País',
  '🇨🇴 Colombia: Cine Bien Hecho. Cine No Visto': 'Muestra / País',
  '🧒 Festicine, Festiniños': 'Perspectivas / Miradas',
  '🎪 Actividades': 'Especiales / Eventos',
  // ── 9° Festival Audiovisual de Girardota ──────────────────────────────
  '🎬 Proyecciones': 'Muestra / País',
  // Cine Corto Popayán 17 (29 sep 2026)
  '📽️ Selección Oficial Documental': 'Competencia',
  '🏔️ Selección Oficial Cauca': 'Competencia',
  '🌀 Selección Oficial Experimental': 'Competencia',
  '🪶 Selección Oficial Indígena': 'Competencia',
  '🥁 Selección Oficial Afro': 'Competencia',
  '✏️ Selección Oficial Animación': 'Competencia',
  '🤝 Selección Oficial Comunitario': 'Competencia',
  '🎬 Selección Oficial Ficción': 'Competencia',
  // la Infantil llegó con la parrilla del 6 oct (sábado 10, Teatro Bolívar)
  '🎈 Selección Oficial Infantil': 'Competencia',
  '🌎 Muestra de Cortos Internacionales': 'Muestra / País',
  '🏘️ CineCorto en el Barrio': 'Cortos / Programas',
  '🏡 Cine Corto al Barrio': 'Cortos / Programas',
  // MUBI Fest Bogotá 2026 (las etiquetas de las tarjetas de mubifest.com)
  '🎬 Estreno MUBI': 'Muestra / País',
  '🌙 Función al Aire Libre': 'Especiales / Eventos',
  '🔎 Foco': 'Retrospectiva / Tributo',
  '🎞️ Restaurada': 'Retrospectiva / Tributo',
  '🎙️ Charla en Vivo': 'Charlas / Industria',
  '🎲 Al Aire Libre': 'Especiales / Eventos',
  '📚 MUBI Library': 'Especiales / Eventos',
  // FICPA 2026 (la Selección Oficial y los dos menús del sitio)
  '🌍 Ecos del Mundo': 'Competencia',
  '💓 Latidos del Cine Colombiano': 'Competencia',
  '🎨 Cámaras de Barniz': 'Competencia',
  '🌀 Churo Cósmico': 'Perspectivas / Miradas',
  '🗺️ Programación Alterna': 'Muestra / País',
  '🎓 Academia': 'Charlas / Industria',
  '💼 Industria': 'Charlas / Industria',
  '🏆 Clausura': 'Clausura',
  // MIDBO 2026 (las categorías madre de midbo.co)
  '🏆 Competencia Nacional de Largometraje Documental': 'Competencia',
  '🎞️ Competencia Nacional de Cortometraje Documental': 'Competencia',
  '🌎 Competencia Iberoamericana de Largometraje Documental': 'Competencia',
  '📽️ Competencia Iberoamericana de Cortometraje Documental': 'Competencia',
  '🌍 Panorama Internacional de Largometraje Documental': 'Muestra / País',
  '🗺️ Panorama Internacional de Cortometraje Documental': 'Muestra / País',
  '🇨🇴 Panorama Nacional de Documental': 'Muestra / País',
  '🪞 Espejos: Gestos de Reparación': 'Perspectivas / Miradas',
  '✨ Programas Especiales': 'Especiales / Eventos',
  '🔎 Foco Claire Simon': 'Retrospectiva / Tributo',
  '🔍 Foco Ignacio Agüero': 'Retrospectiva / Tributo',
  '🎯 Foco Santiago Álvarez': 'Retrospectiva / Tributo',
  '🕰️ Retrospectiva: Sara Gómez': 'Retrospectiva / Tributo',
  '🏅 Homenaje a Pablo Mora Calderón. Premio ALADOS a Toda una Vida': 'Retrospectiva / Tributo',
  '🇫🇷 Comptoir du Doc': 'Muestra / País',
  '🏘️ CREAndo Documental en los Barrios': 'Cortos / Programas',
  '🎙️ Encuentro Pensar lo Real': 'Charlas / Industria',
  '🔊 Documental Expandido': 'Especiales / Eventos',
  '🧒 Cine Corto Familiar': 'Cortos / Programas',
  '🎤 Actividades': 'Charlas / Industria',
  // Fantasmagoría 8 (29 sep 2026)
  '🕯️ Aniversario 30 Años': 'Retrospectiva / Tributo',
  '👽 Aniversario 40 Años': 'Retrospectiva / Tributo',
  '🩸 Aniversario 50 Años': 'Retrospectiva / Tributo',
  '📖 Club de la Medianoche': 'Especiales / Eventos',
  '🦜 Colombia es Fantástica': 'Muestra / País',
  '🎉 Evento Inaugural': 'Apertura / Gala',
  '🌙 Evento de Clausura': 'Clausura',
  '🛸 Expediente Fantasmagoría': 'Especiales / Eventos',
  '🎓 Fantasmagoría Académica': 'Charlas / Industria',
  '🌕 Homenaje a Luigi Cozzi': 'Retrospectiva / Tributo',
  '🤝 Jornada Fantasmeet': 'Charlas / Industria',
  '🎲 Jornada Juegos de Mesa Fantastable': 'Especiales / Eventos',
  '🦄 La Marmita del Hechicero': 'Especiales / Eventos',
  '🐉 Muestra Asiática El Oriente Es Rojo': 'Muestra / País',
  '🎞️ Muestra Catalana': 'Muestra / País',
  '🧸 Muestra Fantasmagoritos': 'Especiales / Eventos',
  // FILCMAR 8 · Marinilla (1 oct 2026)
  '🎓 6.º Competencia Universitaria': 'Competencia',
  '🌎 Competencia Latinoamericana': 'Competencia',
  '🌙 Competencia Espíritu del Trasnoche': 'Competencia',
  '✏️ Cinescuela': 'Muestra / País',
  '🐄 Viejos Secretos del Nuevo Oeste': 'Muestra / País',
  '📚 Programación Académica': 'Charlas / Industria',
  '🐎 Programación MORA': 'Charlas / Industria',
  '🐓 Programación Cultural': 'Especiales / Eventos',
  '🌀 Muestra Weird y Experimental': 'Perspectivas / Miradas',
  '💥 Muestra de Acción A Quemarropa': 'Perspectivas / Miradas',
  '🦯 Muestra Especial': 'Especiales / Eventos',   // autodescripción para personas con discapacidad visual
  '📚 Noche de Librerías': 'Especiales / Eventos',
  '📼 Retrospectiva Cristian Ponce': 'Retrospectiva / Tributo',
  '🗃️ Archivo Fantasmagoría': 'Retrospectiva / Tributo',   // Fantasmagoría, base v2 (Jairo Pinilla)
  '🔦 Retrospectiva Tilman Singer': 'Retrospectiva / Tributo',
  '🌶️ Sangre Latina': 'Perspectivas / Miradas',
  '🏰 Selección Asedio: Las Murallas del Miedo': 'Perspectivas / Miradas',
  '🌎 Selección Latinoamericana de Cortometrajes': 'Competencia',   // Premio «Jairo Pinilla», con jurado
  '🎬 Selección Oficial Cortometrajes': 'Competencia',
  '🎥 Selección Oficial Largometrajes Documentales': 'Competencia',
  '🏆 Selección Oficial Largometrajes de Ficción': 'Competencia',
  '✏️ Selección de Cortometrajes Animados': 'Competencia',   // Premio «Gritos Animados», con jurado
  '🇨🇴 Selección de Cortometrajes Colombianos': 'Competencia',   // Premio «Madremonte», con jurado
  // BIFF 12 (29 sep 2026)
  '🇨🇴 Colombia Viva': 'Muestra / País',
  '✨ Espíritu Joven': 'Competencia',   // compite por el Premio de la Juventud
  '🎩 Masters': 'Perspectivas / Miradas',
  '👻 Fantasmas del Pasado': 'Perspectivas / Miradas',
  '✊ Clases de Lucha': 'Perspectivas / Miradas',
  '🧬 Relatos Mutantes': 'Perspectivas / Miradas',
  '🎞️ Retrospectiva Rei Pictures': 'Retrospectiva / Tributo',
  '🧒 BIFF Kids': 'Especiales / Eventos',
  '🎻 Cine Conciertos': 'Especiales / Eventos',
  '🎬 Muestra de Cortometrajes BIFF Bang': 'Cortos / Programas',
  '🎤 Charlas Abiertas BIFF Bang': 'Charlas / Industria',
  // el Bogotá Creative Connect (biff.co/eventos_Paneles.php, 6 oct)
  '🎙️ Paneles de Industria': 'Charlas / Industria',
  // ── TIFF 2026 · Toronto ────────────────────────────────────────────────
  '📺 Primetime': 'Especiales / Eventos',
  '🔎 Discovery': 'Perspectivas / Miradas',
  '🎯 Centrepiece': 'Muestra / País',
  '⭐ Special Presentations': 'Muestra / País',
  '🎩 Gala Presentations': 'Apertura / Gala',
  '🌙 Midnight Madness': 'Especiales / Eventos',
  '🏆 Platform': 'Competencia',
  '〰️ Wavelengths': 'Perspectivas / Miradas',
  '🎥 TIFF Docs': 'Perspectivas / Miradas',
  '🎙️ In Conversation With...': 'Charlas / Industria',
  '🏛️ TIFF Classics': 'Retrospectiva / Tributo',
  '🎪 Special Events': 'Especiales / Eventos',
  '✂️ Short Cuts': 'Cortos / Programas',
  // ── FICIDI 2026 · Barranquilla ──
  '🏳️‍🌈 Selección Oficial': 'Cortos / Programas',
  '✨ Proyección Especial': 'Especiales / Eventos',
  // ── FICICA 2026 · Barranquilla (las cuatro categorías de su programación) ──
  '🎬 Exhibiciones': 'Cortos / Programas',
  '🤝 Industria': 'Charlas / Industria',
  '✨ Eventos Especiales': 'Apertura / Gala',
  // ── Cinemancia 2026 · Valle de Aburrá ─────────────────────────────────
  '⭐ Función Inaugural': 'Apertura / Gala',
  '🎬 Función de Clausura': 'Clausura',
  '🔺 Programa 1. El Espesor de las Formas': 'Cortos / Programas',
  '👁️ Programa 2. Teoremas sobre la Mirada': 'Cortos / Programas',
  '⚗️ Alquimia de la luz. El cine de Luciana Decker': 'Retrospectiva / Tributo',
  '🃏 Carta blanca': 'Perspectivas / Miradas',
  '🌷 La Primavera Llega para los que Esperan. El Cine de José Luis Torres Leiva': 'Retrospectiva / Tributo',
  '🌡️ Febril Incisión. El Cine de Thomas Fürhapter': 'Retrospectiva / Tributo',
  '🖤 Sick and Dirty. Curaduría de Michael Koresky': 'Perspectivas / Miradas',
  '📼 La Sutil Materia. Sergio Navarro': 'Retrospectiva / Tributo',
  '🇦🇷 Historia(s) del Cine: Argentina. Curaduría de José Miccio': 'Muestra / País',
  // VARTEX 14 — muestra de video y experimental, Medellín.
  '🌍 Muestra Internacional': 'Muestra / País',
  '🇨🇴 Muestra Nacional':     'Muestra / País',
  '🏆 Muestra Local':         'Competencia',
  '🎓 Formación':             'Charlas / Industria',
  // ── CineAutopsia 2026 · Bogotá ────────────────────────────────────────
  '🔬 Destacados': 'Competencia',
  '🌀 Panorama': 'Muestra / País',
  '🔮 Largometrajes': 'Muestra / País',
  '🌙 Cortometrajes': 'Cortos / Programas',
  '🌱 Raíces del Juego': 'Perspectivas / Miradas',
  '🧠 Juego Mental': 'Perspectivas / Miradas',
  '👟 El Rey Puma': 'Apertura / Gala',
  '🏅 Más Allá del Fútbol': 'Muestra / País',
  '🔥 Barrio Caliente': 'Muestra / País',
  '🚴 Pedal y Resistencia': 'Perspectivas / Miradas',
  '✍️ Fútbol Poético': 'Perspectivas / Miradas',
  '🏟️ Refugio en la Cancha': 'Muestra / País',
  '💪 Contra Todo': 'Perspectivas / Miradas',
  '🔟 El Diego': 'Retrospectiva / Tributo',
  '⚽ Juegan como Niñas': 'Apertura / Gala',
  '🗺️ Territorios en Juego': 'Muestra / País',
  '🇧🇷 Brasil: Juego, Memoria y Pasión': 'Muestra / País',
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
  '🌸 Fragmentos del Cielo. El Cine de Ewelina Rosińska': 'Retrospectiva / Tributo',
  '🌿 Campo Indómito: Shinsuke Ogawa': 'Retrospectiva / Tributo',
  '🌿 Cine al Natural': 'Muestra / País',
  '🌿 Free Outdoor Screenings': 'Especiales / Eventos',
  '🎉 Eventos Especiales': 'Especiales / Eventos',
  '🎓 Talleres': 'Charlas / Industria',
  // QAFF 2026 Bogotá. Los NOMBRES son del festival: «DIÁLOGO IMPROBABLE» está
  // impreso en cada una de sus páginas de diálogo y es una de las 15 categorías
  // de su calendario; «Miradas Especiales» es como su web titula la página de
  // fuera de competencia. El arquetipo y el emoji son nuestros.
  '💬 Diálogo Improbable': 'Charlas / Industria',
  '✨ Miradas Especiales': 'Especiales / Eventos',
  '🎖️ Tributo Ben Rivers': 'Retrospectiva / Tributo',
  '🎙️ Podcasts': 'Charlas / Industria',
  '🎞️ Clásicos': 'Retrospectiva / Tributo',
  '🎞️ Competencia de Cortometrajes': 'Competencia',
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
  '🎭 ¿Qué es la Ficción?': 'Perspectivas / Miradas',
  '🏅 Documentary Competition': 'Competencia',
  '🏆 Comp. Cine en los Barrios': 'Competencia',
  '🏆 Competencia Brasil': 'Competencia',
  '🏆 Competencia Largometrajes': 'Competencia',
  '🏆 Competencia Nacional de Ficción': 'Competencia',
  '🏆 Competencia Central': 'Competencia',
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
  '📖 Según la Palabra. El Cine de Olivier Godin': 'Retrospectiva / Tributo',
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
  // FICMA 17 · REPROGRAMADO (19–26 SEP). Las secciones de la parrilla nueva son
  // OTRAS: el festival ya no titula por temas de coleccionismo sino por tipo de
  // función. Las de agosto se dejan abajo mientras el festival no reanuncie el
  // resto — sus obras vuelven con ellas.
  '🎬 Función de apertura': 'Apertura / Gala',
  '✨ Función Inaugural': 'Apertura / Gala',
  '🇨🇴 Estrenos Cine Colombiano': 'Competencia',
  '🎞️ Cine Colombiano': 'Muestra / País',
  '⚡ Cortometrajes': 'Cortos / Programas',
  '📽️ Cine Clásico Colombiano': 'Retrospectiva / Tributo',
  // «🛠️ Talleres» ya está más abajo, con la de agosto: se reusa, no se duplica.

  // FICMA 17 — programa por TEMAS de coleccionismo y ciudad, no por competencias.
  // Las dos de estrenos son la cabecera y llevan colores distintos entre sí; las
  // temáticas comparten «Perspectivas», salvo antigüedades y numismática, que
  // miran al pasado y toman el color de retrospectiva.
  '🎬 Estrenos Nacionales': 'Competencia',
  '🌍 Estrenos Internacionales': 'Muestra / País',
  '🕊️ En alianza con el FICDEH': 'Especiales / Eventos',
  '🎨 Arte': 'Perspectivas / Miradas',
  // El PDF de programación de septiembre la escribe «POP ART»; en agosto era
  // «Arte Pop». Se conservan las dos: la vieja sigue en el JSON archivado.
  '🥫 Arte Pop': 'Perspectivas / Miradas',
  '🥫 Pop Art': 'Perspectivas / Miradas',
  '💥 Cómic': 'Perspectivas / Miradas',
  '🎵 Música': 'Perspectivas / Miradas',
  '🏗️ Arquitectura': 'Perspectivas / Miradas',
  '🕰️ Antigüedades': 'Retrospectiva / Tributo',
  '🪙 Numismática': 'Retrospectiva / Tributo',
  '🌱 Medio Ambiente': 'Perspectivas / Miradas',
  '🏛️ Red de Museos': 'Especiales / Eventos',
  // Las tres que estrenó la parrilla de septiembre. «Estrenos Locales» es la
  // muestra de realizadores de Manizales y el Eje Cafetero: compite, como las
  // otras dos de estrenos. Las funciones especiales y la fiesta de clausura no
  // son cine en sala —un concierto, una noche de vinilos, una fiesta— y toman
  // el color de eventos.
  '🏔️ Estrenos Locales': 'Competencia',
  '✨ Funciones Especiales': 'Especiales / Eventos',
  '🎉 Fiesta de Clausura': 'Especiales / Eventos',
  // Franja Académica de FICMA — el festival la divide en talleres y charlas.
  '🛠️ Talleres': 'Charlas / Industria',
  // #NarrarElFuturo 2026 (Bogotá, 15–20 SEP): las temáticas con que el propio
  // festival filtra su programa, más «Sala VR», que es como llama a la instalación.
  '🎬 Proyecciones & Largos': 'Competencia',
  '⚡ Muestra de Cortos': 'Cortos / Programas',
  '🛠️ Talleres & Formación': 'Charlas / Industria',
  '🥽 Sala VR': 'Especiales / Eventos',
  '🎙️ Charlas': 'Charlas / Industria',
  '💬 Charlas': 'Charlas / Industria',
  '🛰️ Apertura': 'Apertura / Gala',
  '🤝 Encuentro': 'Charlas / Industria',
  // SiembraFest 2026 (11°). Emoji alineado con la iconografia que el propio
  // festival publico en su story del 12 ago 2026; los tres arquetipos tematicos
  // se corrigieron (estaban como industria y apertura).
  '🏺 Mujeres que Sostienen la Vida': 'Perspectivas / Miradas',
  '❤️‍🩹 Amores & Desamores': 'Perspectivas / Miradas',
  '👻 Cinema Patatús': 'Perspectivas / Miradas',
  '💀 Muertos de Risa': 'Perspectivas / Miradas',
  '🎞️ Buenos, Malos y Feos': 'Perspectivas / Miradas',
  '👁️ Ojo Pelao': 'Cortos / Programas',
  '🍲 Sabores en Escena': 'Perspectivas / Miradas',
  // Tres franjas que aparecen en el PROGRAMA impreso de Villeta (4 sep) y que
  // la selección oficial no listaba: no son secciones de obras, son bandas del
  // festival. «Película Invitada» trae una película fuera de selección;
  // «SiembraLAB» son los tres talleres y «LABRA» la cosecha del proceso de
  // formación. Nombre verbatim; el emoji y el arquetipo, nuestros.
  '🎟️ Película Invitada': 'Especiales / Eventos',
  '🛠️ SiembraLAB': 'Charlas / Industria',
  '🌱 LABRA': 'Charlas / Industria',
  '🪶 Estampas': 'Muestra / País',
  '🗺️ Así es Cundinamarca': 'Muestra / País',
  // QAFF 2026 (8ª edición, «NOIR»). Secciones curatoriales del propio festival,
  // con los emoji aprobados por Juan el 2 ago; los nombres EN salen del nav de su sitio.
  '🖼️ Muestra Artística': 'Especiales / Eventos',
  '🌧️ Imaginarios Afrodisruptivos': 'Perspectivas / Miradas',
  '🌊 Fronteras Latam': 'Muestra / País',
  '🛶 Panorama Colombiano': 'Muestra / País',
  '☕ Panorama Diaspórica': 'Muestra / País',
  '🪞 Prisma Femenino': 'Perspectivas / Miradas',
  '🌳 Panorama Africano': 'Muestra / País',
  '🪕 Otra Mirada': 'Perspectivas / Miradas',
  '🗄️ Diálogo Improbable': 'Charlas / Industria',
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
  CA: { es:'Canadá',         en:'Canada' },
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