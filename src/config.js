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
  '🌍 Muestra Internacional': 'International Showcase',
  '🇨🇴 Muestra Nacional':     'National Showcase',
  '🏆 Muestra Local':         'Official Selection · Local',
  '🎓 Formación':             'Workshops & Seminar',
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
  // ── FINCA 2026 (8ª ed., Buenos Aires) — 5 posts del 22 ago en @festivalfinca ──
  // Se leyeron EN EL NAVEGADOR y expandiendo el caption: los cinco llegaban
  // truncados en «… more», y el texto corto no nombra ni una sola premiada.
  //
  // DOS TÍTULOS QUE ARREGLAMOS EN EL CATÁLOGO al cruzar, y los dos eran NUESTROS:
  // «Mora» era «Amora» (se cayó la A inicial) y «Sobre Ruinas» era «Sobre
  // Ruínas». El sidecar finca-2026-funciones.json —lo que mandó el festival—
  // trae las dos bien; se rompieron aguas abajo. «Amora» además se verificó
  // fuera (Cinemateca Brasileira, Mostra SP, IMDb): Ana Petta, Brasil 2025.
  //
  // LOS CORTOS ENLAZAN COMO CUALQUIER OBRA. «Sobre Ruínas» y «Dígale no a los
  // poalets» viven dentro de «Cortometrajes en Competencia Oficial — Programa
  // 2». La primera versión los dejó en obra:null porque el palmarés solo
  // buscaba títulos de nivel superior; Juan lo corrigió el 24 ago: «para eso
  // existe la ficha independiente por película o cortometraje, sin
  // discriminación». Ahora `_palmBuscar` mira también dentro de los programas y
  // el clic abre la ficha del CORTO (openCortoSheet), no la de su envase.
  //
  // «No als poalets» ya no necesita reconciliación: el catálogo lo muestra con
  // su título original desde el 24 ago, cuando se aplicó a FINCA la regla de
  // QAFF (el original manda). Queda UNO: el palmarés dice «How Deep Is Your
  // Love» y el catálogo «¿Cuán profundo es tu amor?» — ahí mostramos el del
  // catálogo, que es el que el usuario vio, hasta que se decida ese caso: es
  // el único de FINCA sin original declarado en nuestros datos.
  //
  // EL PREMIO EXACTO, en `premio`. La primera versión metió el Segundo Premio
  // como una segunda `ganadora` y dio a entender que FINCA premió a dos obras
  // por igual en esa competencia — no lo hizo. `nivel` sigue decidiendo el
  // TAMAÑO (grande = ganadora, pequeña = mención), que es lo visual; `premio`
  // dice el nombre que le puso el festival y se pinta encima del título.
  // Es opcional: la mayoría de categorías tienen una sola ganadora y no lo
  // necesitan. Sirve para lo que venga —Tercer Premio, Premio Especial del
  // Jurado— sin volver a tocar el modelo.

  {fest:'finca2026', categoria:'Premio del Público · Largometrajes Internacionales', nivel:'ganadora',
   titulo:'La vida fracturada', autoria:'Cristian Cartier, Martín Longo, Pablo Piovano, Maximiliano Goldschmidt', obra:'La vida fracturada'},
  {fest:'finca2026', categoria:'Premio del Público · Corto y Mediometrajes Internacionales', nivel:'ganadora',
   titulo:'Ziki', autoria:'Roberta Palmieri, Olga Sargenti', obra:'Ziki'},
  {fest:'finca2026', categoria:'Premio del Público · Documentales Latinoamericanos', nivel:'ganadora',
   titulo:'Amora', autoria:'Ana Petta', obra:'Amora'},

  {fest:'finca2026', categoria:'Largometrajes Internacionales', nivel:'ganadora',
   titulo:'Yintah', autoria:'Jennifer Wickham, Brenda Michell, Michael Toledano', obra:'Yintah'},
  {fest:'finca2026', categoria:'Largometrajes Internacionales', nivel:'mencion',
   titulo:'¿Cuán profundo es tu amor?', autoria:'Eleanor Mortimer', obra:'¿Cuán profundo es tu amor?'},

  {fest:'finca2026', categoria:'Corto y Mediometrajes Internacionales', nivel:'ganadora',
   titulo:'Sobre Ruínas', autoria:'Carol Benjamin', obra:'Sobre Ruínas'},
  {fest:'finca2026', categoria:'Corto y Mediometrajes Internacionales', nivel:'mencion',
   titulo:'No als poalets', autoria:'Laura García Andreu', obra:'No als poalets'},

  {fest:'finca2026', categoria:'Documentales Latinoamericanos', nivel:'ganadora', premio:'Primer Premio',
   titulo:'Karuara, la gente del río', autoria:'Miguel Araoz Cartagena, Stephanie Boyd', obra:'Karuara, la gente del río'},
  {fest:'finca2026', categoria:'Documentales Latinoamericanos', nivel:'ganadora', premio:'Segundo Premio',
   titulo:'Toroboro: el nombre de las plantas', autoria:'Manolo Sarmiento', obra:'Toroboro: el nombre de las plantas'},

  // Premio de la Red Argentina de Festivales y Muestras Audiovisuales (RAFMA),
  // con el nombre del documentalista Edgardo «Pipo» Bechara el Khoury.
  {fest:'finca2026', categoria:'Premio «Edgardo Pipo Bechara el Khoury»', nivel:'ganadora',
   titulo:'La vida fracturada', autoria:'Cristian Cartier, Martín Longo, Pablo Piovano, Maximiliano Goldschmidt', obra:'La vida fracturada'},
  {fest:'finca2026', categoria:'Premio «Edgardo Pipo Bechara el Khoury»', nivel:'mencion',
   titulo:'La granja de la libertad', autoria:'Luciano Militello', obra:'La granja de la libertad'},

  // FICDEH 2026 — 8 posts del 21 ago en @ficdeh, uno por categoría.
  // Tres correcciones sobre la fuente, documentadas porque publicar mal un premio
  // es mentirle al usuario sobre su propio festival:
  //  · «Muerto no» aparecía en la leyenda como Ficción NACIONAL, categoría que ese
  //    mismo día se dio a «Sukua». El ARTE del post dice Internacional, la obra es
  //    brasilera, y el JSON la tiene en la sección Internacional. Gana el arte.
  //  · «Indryd» → «Ingryd» Ríos.  · «My Ggandmother is a skydriver» → grafía normal.
  {fest:'ficdeh2026', categoria:'ImpulsoLab, 10ª edición', nivel:'ganadora',
   titulo:'Eliza', autoria:'Ingryd Ríos', obra:null, tipo:'proyecto'},

  {fest:'ficdeh2026', categoria:'Largometraje de Ficción', nivel:'ganadora',
   titulo:'El verano de Jahia', autoria:'Olivier Meys', obra:'El verano de Jahia'},
  {fest:'ficdeh2026', categoria:'Largometraje de Ficción', nivel:'mencion',
   titulo:'Feito Pipa', autoria:'Allan Deberton', obra:'Feito Pipa'},
  {fest:'ficdeh2026', categoria:'Largometraje de Ficción', nivel:'mencion',
   titulo:'La hija cóndor', autoria:'Álvaro Olmos T.', obra:'La hija cóndor'},

  {fest:'ficdeh2026', categoria:'Largometraje Documental Nacional', nivel:'ganadora',
   titulo:'Hija del volcán', autoria:'Jenifer de la Rosa', obra:'Hija del volcán'},
  {fest:'ficdeh2026', categoria:'Largometraje Documental Nacional', nivel:'mencion',
   titulo:'Soñé su nombre', autoria:'Ángela Carabalí', obra:'Soñé su nombre'},
  {fest:'ficdeh2026', categoria:'Largometraje Documental Nacional', nivel:'mencion',
   titulo:'El valor de la palabra', autoria:'Marta Rodríguez', obra:'El valor de la palabra'},

  // `poster` propio de la entrada: la obra NO está en el catálogo —su ficha en la
  // web del festival no tenía ninguna función, y el pipeline de FICDEH construye
  // DESDE las funciones— pero su afiche oficial sí existe. TMDB 1400379,
  // verificado por director (Kim A. Snyder) y duración (92 min), no por título:
  // hay cinco películas llamadas «The Librarians».
  // Sin este campo cae en Forma A. Que una obra falte en NUESTRO catálogo es una
  // limitación nuestra: usar nuestro dibujo existiendo el suyo empobrece la pieza.
  {fest:'ficdeh2026', categoria:'Largometraje Documental Internacional', nivel:'ganadora',
   titulo:'Los bibliotecarios', autoria:'Kim Snyder', obra:null,
   poster:'/assets/ficdeh/los-bibliotecarios.jpg'},
  {fest:'ficdeh2026', categoria:'Largometraje Documental Internacional', nivel:'mencion',
   titulo:'El silencio de la tierra', autoria:'Frank Gutiérrez', obra:'El silencio de la tierra'},

  {fest:'ficdeh2026', categoria:'Cortometraje de Ficción Nacional', nivel:'ganadora',
   titulo:'Sukua', autoria:'Omar E. Ospina Giraldo', obra:'Sukua'},
  {fest:'ficdeh2026', categoria:'Cortometraje de Ficción Nacional', nivel:'mencion',
   titulo:'Sapos por todos lados', autoria:'Jacobo Alban', obra:'Sapos por todos lados'},
  {fest:'ficdeh2026', categoria:'Cortometraje de Ficción Nacional', nivel:'mencion',
   titulo:'La independencia', autoria:'John Agudelo Suárez', obra:'La independencia'},

  {fest:'ficdeh2026', categoria:'Cortometraje de Ficción Internacional', nivel:'ganadora',
   titulo:'Muerto no', autoria:'Alex Reis', obra:'Muerto no'},
  {fest:'ficdeh2026', categoria:'Cortometraje de Ficción Internacional', nivel:'mencion',
   titulo:'Una torreta en llamas', autoria:'Humberto Flores Jáuregui', obra:'Una torreta en llamas'},
  {fest:'ficdeh2026', categoria:'Cortometraje de Ficción Internacional', nivel:'mencion',
   titulo:'My grandmother is a skydiver', autoria:'Polina Piddubna', obra:'My grandmother is a skydiver'},

  {fest:'ficdeh2026', categoria:'Cortometraje Documental Nacional', nivel:'ganadora',
   titulo:'Madres de nacimiento', autoria:'Gloria Isabel Gómez Ceballos', obra:'Madres de nacimiento'},
  {fest:'ficdeh2026', categoria:'Cortometraje Documental Nacional', nivel:'mencion',
   titulo:'Apotnojushi La Casa del viento', autoria:'Marbel Ina Vanegas Jusayu', obra:'Apotnojushi La Casa del viento'},
  {fest:'ficdeh2026', categoria:'Cortometraje Documental Nacional', nivel:'mencion',
   titulo:'Si La Escombrera hablara', autoria:'Juan Prado', obra:'Si La Escombrera hablara'},

  {fest:'ficdeh2026', categoria:'Cine Comunitario Nacional', nivel:'ganadora',
   titulo:'Por una gota de leche', autoria:'Esteban J. Corzo', obra:'Por una gota de leche'},
];

// ── NOTICES ──────────────────────────────────────────────────────────────────
// date: 'YYYY-MM-DD' de la función original — el banner desaparece al día siguiente
// Para 'rescheduled': añadir newDay, newTime, newVenue
export const NOTICES=[
  // FICDEH 2026 — el sismo del 10 ago 2026 (Chocó, Valle del Cauca, Eje Cafetero).
  // Comunicado oficial del festival el 11 ago: cancelan Quibdó, Cali, Pereira y
  // Manizales «porque nuestros equipos locales están dedicados a labores de
  // rescate y apoyo», y siguen en Armenia, Barranquilla, Bogotá, Cartagena,
  // Medellín, Tunja, Ibagué y +30 municipios.
  //
  // Alcance CIUDAD y no 88 entradas por título: es UN hecho y un solo banner.
  // El festival NO está aplazado —sigue en 7 ciudades—, así que no lleva
  // `status`: eso es para el festival entero (docs/PROTOCOLO.md §2·bis).
  // `note` son sus palabras; `note_en` es traducción nuestra.
  {
    festival:'ficdeh2026',
    type:'cancelled',
    cities:['Quibdó','Cali','Pereira','Manizales'],
    id:'ficdeh-sismo-ciudades',
    note:'FICDEH canceló su programación en <b>Quibdó, Cali, Pereira y Manizales</b> por el sismo. Sigue activa en las demás ciudades.',
    note_en:'FICDEH canceled its programming in Quibdó, Cali, Pereira and Manizales due to the earthquake. It remains active in all other cities.',
    url:'https://www.instagram.com/p/Db6xcU2FGb6/',
  },
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
  'ficma2026': {
    name:'FICMA',fullName:'FICMA — Feria Internacional de Cine de Manizales',shortName:'FICMA',
    city:'Manizales',country:'CO',
    dates:'10–17 AGO',dates_en:'AUG 10–17',year:2026,timezoneOffset:'-05:00',
    keyArt:'/assets/keyart/ficma2026.jpg',
    // APLAZADO por el terremoto de Manizales. Comunicado oficial del festival
    // el 10 ago 2026; la cita son dos párrafos VERBATIM suyos —el cierre y la
    // única información accionable— elegidos por Juan. El EN es traducción
    // nuestra, aprobada por él. Reversión: fechas nuevas + borrar este bloque;
    // los datos del festival nunca se tocaron.
    status:{
      kind:'postponed',
      since:'2026-08-10',
      note:'«Hoy, primero, la vida.» Estaremos anunciando nuevas fechas y actividades.',
      note_en:'«Today, life comes first.» We will be announcing new dates and activities.',
      url:'https://www.instagram.com/p/Db35wc_zR5h/',
    },
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
    // OCULTO todavía (group:'test'), a la espera del aviso de traslado.
    //
    // El festival trasladó LA TOTALIDAD de las proyecciones a Bogotá por el
    // terremoto del 10 ago que golpeó Quibdó y el Chocó — el MISMO sismo que
    // aplazó FICMA. Comunicado del 20 ago: instagram.com/p/DcREogQER9d
    //
    // Ya NO es el caso de agosto —entonces se ocultó porque lo publicado decía
    // Quibdó y no teníamos Bogotá—. Ahora el JSON es el de Bogotá: 44 funciones,
    // 6 sedes, 14–22 SEP. Lo que falta para mostrarlo es la BANDA de traslado,
    // que necesita un `status` nuevo: no es `postponed` (el festival SÍ se hace,
    // en sus fechas) ni el `NOTICES` con `cities` de FICDEH (ese se engancha a
    // funciones de la ciudad cancelada, y aquí Quibdó no tiene ninguna).
    //
    // El afiche se queda: es el suyo, el de la 8ª edición. Dice «14-18
    // SEPTIEMBRE» y el programa llega al 22 — la banda de traslado es lo que
    // explica esa diferencia.
    // TRASLADADO, no aplazado: el festival SÍ se hace y en sus fechas, solo que
    // toda su programación se movió de Quibdó a Bogotá. Por eso `kind:'moved'`,
    // que pinta la banda y NADA más — punto verde, preselección y fechas reales
    // siguen intactos. `note` es nuestra frase con la cita entrecomillada donde
    // son sus palabras (comunicado del 20 ago); `note_en` es traducción nuestra,
    // aprobada por Juan. Reversión: borrar este bloque.
    //
    // El afiche es el suyo y dice «14-18 SEPTIEMBRE» mientras el programa llega
    // al 22: es esta banda la que explica esa diferencia.
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
    name:'SiembraFest',fullName:'SiembraFest — Festival de Cine Colombiano al Campo',shortName:'SIEMBRAFEST',
    city:'Sasaima y Villeta',country:'CO',
    dates:'9–18 SEP',dates_en:'SEP 9–18',year:2026,timezoneOffset:'-05:00',
    storageKey:'siembrafest2026_',festivalStartStr:'2026-09-09T00:00:00',festivalEndStr:'2026-09-18T23:00:00',
    festivalDates:{'2026-09-09':'2026-09-09','2026-09-10':'2026-09-10','2026-09-11':'2026-09-11','2026-09-12':'2026-09-12','2026-09-13':'2026-09-13','2026-09-14':'2026-09-14','2026-09-15':'2026-09-15','2026-09-16':'2026-09-16','2026-09-17':'2026-09-17','2026-09-18':'2026-09-18'},
    days:[{k:'2026-09-09',d:9,lbl:'MIÉ'},{k:'2026-09-10',d:10,lbl:'JUE'},{k:'2026-09-11',d:11,lbl:'VIE'},{k:'2026-09-12',d:12,lbl:'SÁB'},{k:'2026-09-13',d:13,lbl:'DOM'},{k:'2026-09-14',d:14,lbl:'LUN'},{k:'2026-09-15',d:15,lbl:'MAR'},{k:'2026-09-16',d:16,lbl:'MIÉ'},{k:'2026-09-17',d:17,lbl:'JUE'},{k:'2026-09-18',d:18,lbl:'VIE'}],
    dayKeys:['2026-09-09','2026-09-10','2026-09-11','2026-09-12','2026-09-13','2026-09-14','2026-09-15','2026-09-16','2026-09-17','2026-09-18'],
    dayShort:{'2026-09-09':'MIÉ 9','2026-09-10':'JUE 10','2026-09-11':'VIE 11','2026-09-12':'SÁB 12','2026-09-13':'DOM 13','2026-09-14':'LUN 14','2026-09-15':'MAR 15','2026-09-16':'MIÉ 16','2026-09-17':'JUE 17','2026-09-18':'VIE 18'},
    dayShort_en:{'2026-09-09':'WED 9','2026-09-10':'THU 10','2026-09-11':'FRI 11','2026-09-12':'SAT 12','2026-09-13':'SUN 13','2026-09-14':'MON 14','2026-09-15':'TUE 15','2026-09-16':'WED 16','2026-09-17':'THU 17','2026-09-18':'FRI 18'},
    dayLong:{'2026-09-09':'Miércoles 9 de septiembre','2026-09-10':'Jueves 10 de septiembre','2026-09-11':'Viernes 11 de septiembre','2026-09-12':'Sábado 12 de septiembre','2026-09-13':'Domingo 13 de septiembre','2026-09-14':'Lunes 14 de septiembre','2026-09-15':'Martes 15 de septiembre','2026-09-16':'Miércoles 16 de septiembre','2026-09-17':'Jueves 17 de septiembre','2026-09-18':'Viernes 18 de septiembre'},
    prioLimit:5,
    // NO SE PUBLICA: falta la programación entera. El catálogo está completo (84
    // obras en 24 programas) pero sin día·hora·sede no hay films[]. La entrada
    // existe desde ya para que el montaje sea solo ensamblar cuando llegue.
    group:'test',
    // Sasaima y Villeta están a 12 km por la misma vía: es UN territorio de
    // traslado. Sin esto la app diría «es en otra ciudad» en vez de los minutos
    // — el mismo caso que Cinemancia en el Valle de Aburrá. REVISAR cuando
    // lleguen las sedes: el radar dice que Proimágenes lista además Supatá y
    // Anolaima, y eso cambiaría el veredicto.
    metroArea:true,
    keyArt:'/assets/keyart/siembrafest2026-v2.jpg',
    tagline:'Festival de Cine Colombiano al Campo',
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
  // ── SiembraFest 11 · Sasaima y Villeta ────────────────────────────────
  // Nombres VERBATIM del festival; el emoji y el arquetipo son nuestra capa.
  // Sin display EN a propósito: son nombres de autor en español —«Ojo Pelao»,
  // «Cinema Patatús»— y la regla de esta tabla omite las secciones de marca
  // antes que inventarles traducción.
  '🏺 Mujeres que sostienen la vida': 'Perspectivas / Miradas',
  '❤️‍🩹 Amores & Desamores': 'Perspectivas / Miradas',
  '🪶 Estampas': 'Cortos / Programas',
  '👻 Cinema Patatús': 'Muestra / País',
  '🎞️ Buenos, Malos y Feos': 'Cortos / Programas',
  '💀 Muertos de Risa': 'Cortos / Programas',
  '👁️ Ojo Pelao': 'Perspectivas / Miradas',
  '🍲 Sabores en Escena': 'Muestra / País',
  '🗺️ Así es Cundinamarca': 'Muestra / País',
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
  // ── Cinemancia 2026 · Valle de Aburrá ─────────────────────────────────
  '⭐ Función inaugural': 'Apertura / Gala',
  '🎬 Función de clausura': 'Clausura',
  '🏆 Competencia Central': 'Competencia',
  '🎞️ Competencia de Cortometrajes': 'Competencia',
  '🔺 Programa 1. El espesor de las formas': 'Cortos / Programas',
  '👁️ Programa 2. Teoremas sobre la mirada': 'Cortos / Programas',
  '⚗️ Alquimia de la luz. El cine de Luciana Decker': 'Retrospectiva / Tributo',
  '🃏 Carta blanca': 'Perspectivas / Miradas',
  '🌷 La primavera llega para los que esperan. El cine de José Luis Torres Leiva': 'Retrospectiva / Tributo',
  '🌡️ Febril incisión. El cine de Thomas Fürhapter': 'Retrospectiva / Tributo',
  '🖤 Sick and Dirty. Curaduría de Michael Koresky': 'Perspectivas / Miradas',
  '📼 La sutil materia. Sergio Navarro': 'Retrospectiva / Tributo',
  '🇦🇷 Historia(s) del cine: Argentina. Curaduría de José Miccio': 'Muestra / País',
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
  // QAFF 2026 Bogotá. Los NOMBRES son del festival: «DIÁLOGO IMPROBABLE» está
  // impreso en cada una de sus páginas de diálogo y es una de las 15 categorías
  // de su calendario; «Miradas Especiales» es como su web titula la página de
  // fuera de competencia. El arquetipo y el emoji son nuestros.
  '💬 Diálogo Improbable': 'Charlas / Industria',
  '✨ Miradas Especiales': 'Especiales / Eventos',
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
  '🛰️ Apertura': 'Apertura / Gala',
  '🤝 Encuentro': 'Charlas / Industria',
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