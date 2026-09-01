// ── src/controller/loader.js ──────────────────────────────────────────────────────
// p8 Step 8d-4 — loadFestival + dismissSplash (festival data load + splash dismiss).
// Orquestador: carga JSON del festival → puebla roster/viewstate (vía bridge) +
// helpers (setters) → render inicial. dismissSplash llama loadFestival y revela la
// app. Sink puro (solo main.js lo importa: ACTION_REGISTRY + Object.assign + IIFE
// detección-festival). Escribe bridge globals en runtime (no eval-time).

import { FESTIVAL_CONFIG, NOTICES, mergeFestivalSections } from '../config.js';
import { parseDur } from '../domain/time.js';
import { lruTouch } from '../lru.js';
import { DAY_ABBR, DAY_NUM, _classifyFestival, festivalShortName } from '../view/components.js';
import { DAYS, DAY_SHORT_EN, _langDates, setCustomPosters, setDayShort, setDayShortEn, setPosters, keepCityOnly } from '../view/helpers.js';
import { closeFestivalSheet, openCitySheet, openReviewSheet, _reviewDesbloqueado, _pintarBannerRevision } from '../view/sheets.js';
import { showToast } from '../view/feedback.js';
import { _renderProgramaContent, lugarClose, scrollDtabsToActive } from '../view/programa.js';
import { _fixStickyOffset, renderAgenda } from '../view/agenda.js';
import { loadState, _cloudLoad, _cloudSave, subscribePlanCloud, _flushCloudSave } from './persistence.js';
import { report } from '../telemetry.js';
import { subscribeDelaysCloud } from './delays-cloud.js';
import { renderFestBar } from './festival.js';
import { _updateProgramaActiveFilter, initProgramaModeBar, showAgView, showDayView, switchMainNav, _syncPmodeTabs } from './pipeline.js';
import { seccionClose } from './overlays.js';
import { setProgramaView } from './handlers.js';
import { dayFullyPassed, simTodayStr } from '../domain/time.js';
import { _djb2, explodeScreenings, normTitle, sealSharedSlots, validateFilm } from '../domain/film.js';
import { syncScheduleWithCatalog } from '../domain/schedule.js';
import { state } from '../state/state.js';
import { deriveClear } from '../state/festival-context.js';
import { storage } from '../storage/storage.js';
import { t } from '../i18n/i18n.js';
import { _autoResolveFestivalPosters, _renderFestivalSelector, renderPostponedBanner } from './festival.js';

// Fetch del JSON de festival con timeout + reintentos (AbortController).
// GitHub Pages a veces entrega los headers (200) pero el cuerpo se cuelga → el
// r.json() nunca resuelve y loadFestival queda colgado con FILMS=0: grid vacío,
// sin error ni 404 (cazado por synthetic monitoring, ~10-20% de cargas en frío).
// El timeout aborta el cuerpo colgado y reintenta. cache:'no-store' se mantiene
// (datos siempre frescos); el reintento cubre el stall transitorio del CDN.
export async function _fetchFestivalJson(url, tries=3, timeoutMs=6000){
  let lastErr;
  for(let i=0;i<tries;i++){
    const ctrl=new AbortController();
    const to=setTimeout(function(){ ctrl.abort(); }, timeoutMs);
    try{
      const r=await fetch(url,{cache:'no-store',signal:ctrl.signal});
      if(!r.ok) throw new Error('HTTP '+r.status+' — '+url);
      const json=await r.json(); // bajo el mismo timeout: si el cuerpo se cuelga, aborta
      clearTimeout(to);
      return json;
    }catch(e){
      clearTimeout(to);
      lastErr=e;
      // Backoff con jitter entre reintentos (no tras el último): si no, los 3
      // intentos caen en la MISMA ventana de congestión de la red del cine y
      // fallan juntos. ~0.6s, ~1.2s + jitter → cruzan la ventana sin alargar de más.
      if(i<tries-1) await new Promise(r=>setTimeout(r, 600*Math.pow(2,i)+Math.random()*400));
    }
  }
  throw lastErr;
}

// Token de generación de carga: cada loadFestival incrementa _loadGen y captura el
// suyo. Tras cada await se re-verifica _gen===_loadGen; si una carga MÁS NUEVA
// arrancó mientras esperábamos (fetch del JSON en red lenta de cine, o el rAF), la
// vieja ABORTA antes de swapear estado o suscribir la nube. Sin esto, "gana el
// último en RESOLVER, no el último tap": elegís B, A resuelve tarde y pisa todo.
// Bug cazado en la auditoría de festivales simultáneos.
let _loadGen=0;

// ── LRU del cache de festivales en memoria ─────────────────────────────────────
// cfg.films/posters/customPosters/lbSlugs se cachean por sesión (~80KB c/u) para no
// re-fetchear al volver. Sin cota, un usuario que recorre MUCHOS festivales en una
// sesión acumula memoria sin límite (riesgo en iPhone viejo / WKWebView). El LRU
// mantiene hasta _FEST_CACHE_CAP festivales cacheados y evicta el menos-usado
// (limpia su cfg.films → re-fetch al volver). El festival activo (recién tocado a
// MRU) NUNCA se evicta. Esto quita el "techo de 3": los festivales EN CURSO /
// mostrados son ilimitados; solo se acota cuántos JSON viven en RAM a la vez.
const _FEST_CACHE_CAP = 8;
let _festCacheOrder = [];

// _touchFestivalCache — aplica el LRU (decisión pura en src/lru.js): registra `id`
// como recién usado y limpia el cache en memoria de los festivales evictados.
function _touchFestivalCache(id){
  const { order, evict } = lruTouch(_festCacheOrder, id, _FEST_CACHE_CAP);
  _festCacheOrder = order;
  for(const vid of evict){
    const v = FESTIVAL_CONFIG[vid];
    if(v){ v.films=null; v.posters=null; v.customPosters=null; v.lbSlugs=null; }
  }
}


// ── INGESTA: JSON crudo → cfg sellado. DUEÑO ÚNICO (24 ago 2026) ─────────────
// Compartida por loadFestival (carga/cambio de festival) y por el refresco de
// datos en caliente (live-refresh.js). Extraerla evita el segundo camino de
// ingesta que la auditoría de caminos duplicados prohibió: los avisos (NOTICES),
// los slots compartidos y la explosión se sellan ACÁ o no se sellan.
export function _ingerirDatosFestival(id, cfg, data){
  // HUELLA CRUDA — SE TOMA ACÁ, ANTES DE TOCAR NADA (24 ago 2026). La ingesta
  // MUTA `data`: explodeScreenings devuelve los MISMOS objetos que data.films
  // (no copias), así que la duración automática de los programas, sealSharedSlots
  // y los avisos de NOTICES escriben sobre el JSON recién bajado. Tomar la huella
  // al final la dejaba distinta de la de un JSON fresco → el refresco en caliente
  // creía ver un cambio en CADA tick y re-renderizaba el grid cada 10 minutos:
  // los pósters titilaban (Juan lo vio en su teléfono). Medido: muta en 4 de 17
  // festivales (FICDEH, FICMA, FINCA, QAFF) — los que tienen slots compartidos,
  // avisos o programas sin duración propia.
  // Por lo mismo `_rawFilms` es una COPIA: es el lado «viejo» del diff y con las
  // mutaciones puestas reportaría como cambio lo que solo fue nuestro sellado
  // (una función reprogramada por NOTICES se vería «movida» contra el JSON nuevo).
  const _crudo=JSON.stringify(data);
  cfg._rawHash=_djb2(_crudo);
  cfg._rawFilms=JSON.parse(_crudo).films;
  cfg._rawDayKeys=(data.dayKeys||cfg.dayKeys||[]).slice();
  // ── Explosión de screenings[] → objetos planos por función ──
  // Dueño: explodeScreenings (domain/film.js) — compartido con el oráculo
  // del planeador, que necesita ejercer el MISMO catálogo que producción.
  const exploded=explodeScreenings(data.films);
  // Duración automática para is_programa
  exploded.forEach(f=>{
    if(f.is_programa&&f.film_list&&f.film_list.length&&!f.duration){
      const mins=f.film_list.reduce((acc,item)=>{
        const m=parseInt((item.duration||"").replace(/[^0-9]/g,""))||0;
        return acc+m;
      },0);
      if(mins>0) f.duration=mins+" min";
    }
  });
  // ── ANCLAJE DE FUNCIÓN (opt-in: root `sharedSlotIsOneScreening`) ────────
  // Algunos festivales programan DOS obras en una misma función: mismo día,
  // hora y sala, una detrás de la otra (FINCA 2026: 6 casos, verificados
  // contra su documento día por día — una sola cabecera de hora para las
  // dos). Sin esto la app las trata como funciones rivales: las declara en
  // conflicto (falso: con una entrada ves ambas) y cree que salís al
  // terminar la primera, así que te ofrece otra función a la que no llegás.
  // NO se puede derivar para todos: en sedes multisala (Tribeca) misma
  // hora+sede es OTRA sala = otra función. Por eso el festival lo declara.
  // Se marca acá, una vez, y el dominio solo lee los campos.
  if(data.sharedSlotIsOneScreening) sealSharedSlots(exploded); // dueño: domain/film.js (compartido con el oráculo)
  // ── AVISOS: cancelada / reprogramada, SELLADOS en la función ────────────
  // Antes el aviso se resolvía por búsqueda en cada superficie (la ficha, el
  // listado y la card lo buscaban por su cuenta en NOTICES) y el
  // PLANIFICADOR no lo miraba nunca: armaba el día alrededor de funciones
  // canceladas y de horas que ya no existían. Se sella acá, una vez, igual
  // que _slotKey — y todos los consumidores lo leen del dato.
  //
  // Reprogramada: la VERDAD es la hora nueva (decisión de Juan, 30 jul 2026).
  // Se aplica al dato y queda `_movedFrom` con la vieja para poder decir de
  // dónde viene. Mantener la hora vieja en pantalla y pedirle al
  // planificador que la ignore es la doble verdad que ya nos costó bugs.
  const _avisos=NOTICES.filter(n=>n.festival===id);
  if(_avisos.length){
    const _dk=data.dayKeys||[];
    exploded.forEach(f=>{
      if(f.info) return;
      // `date` (día de la función original) desambigua cuando una obra tiene
      // varias funciones y solo una cambió. Sin `date` → aplica a todas.
      // Tres alcances, de más ancho a más fino (modelo de tres niveles,
      // docs/PROTOCOLO.md): CIUDADES → título+fecha → título.
      // `cities` nace del sismo del 11 ago 2026: FICDEH canceló Quibdó, Cali,
      // Pereira y Manizales —88 de 444 funciones, 27 sedes, 10 obras que solo
      // se veían ahí— y siguió en las otras 7 ciudades. Por título habrían sido
      // 88 entradas y 88 banners para UN solo hecho.
      // La ciudad se lee del venue CRUDO (data.venues), no de venueCity():
      // ese helper OCULTA la ciudad cuando coincide con la del festival — es
      // para mostrar, no para identificar.
      const _city=((data.venues||{})[f.venue]||{}).city||'';
      const n=_avisos.find(x=>
        Array.isArray(x.cities)
          ? (!!_city && x.cities.includes(_city))
          : (x.title===f.title&&(!x.date||x.date===f.day)));
      if(!n) return;
      if(n.type==='cancelled'){
        f._cancelled=true;
        // La causa ya vive UNA vez en el banner: la card no la repite. Sin
        // esto arrastraba «Pendiente nueva fecha», que se escribió para
        // REPROGRAMADA y en una cancelación por tragedia es una promesa falsa.
        if(n.note) f._cancelExplained=true;
        return;
      }
      if(n.type==='rescheduled'&&(n.newDay||n.newTime||n.newVenue)){
        f._movedFrom={day:f.day,time:f.time,venue:f.venue};
        if(n.newDay){
          f.day=n.newDay;
          // day_order es el índice en dayKeys: sin recalcularlo, la función
          // movida se ordena en su día viejo.
          const _i=_dk.indexOf(n.newDay); if(_i>=0) f.day_order=_i;
        }
        if(n.newTime) f.time=n.newTime;
        if(n.newVenue) f.venue=n.newVenue;
      }
    });
  }
  cfg.films=exploded; // Cacheado en sesión — evita re-fetch al volver al festival.
  // Límite recomendado: ≤5 festivales simultáneos (~80KB c/u). LRU si escala a 8+.
  cfg.posters=data.posters||{};
  cfg.customPosters=data.customPosters||{};
  cfg.lbSlugs=data.lbSlugs||{};
  // ── Un solo dueño por tipo de dato (17 jul 2026) ────────────────────
  // IDENTIDAD (nombre, ciudad, fechas…): el dueño es FESTIVAL_CONFIG
  // (src/config.js) — el JSON solo RELLENA huecos de festivales legacy y
  // nunca pisa un valor que config ya tiene. Motivo: el JSON con
  // "TercerTiempo" pegado pisaba el nombre oficial en todo lo runtime
  // (export del Diario, share, ICS) aunque config estuviera bien.
  // CONTENIDO (días, secciones, ticketing…): el dueño es el JSON.
  // Gate: validate.py [festival-name-parity]. Nada pisa storageKey.
  const _identFields=['name','shortName','city','dates','dates_en','year',
    'timezoneOffset'];
  // `festivalDates` PASÓ de identidad a contenido (Juan, 23 ago 2026).
  // Estaba archivado junto al nombre y la ciudad, así que el JSON solo podía
  // rellenarlo si config lo tenía vacío — pero `days`/`dayKeys`, que son LA
  // MISMA COSA (el calendario del festival), sí los pisa el JSON. El
  // calendario quedaba partido en dos dueños: CineAutopsia dibujaba 8 días en
  // la tira y `FESTIVAL_DATES` solo conocía 4. Los otros cuatro no existían
  // para el reloj — `dayFullyPassed` devolvía false por `if(!dateStr)`, así
  // que el VIE 21 nunca se atenuó, sus funciones nunca contaron como pasadas,
  // y el 25/26/27 habrían roto la detección de HOY estando el festival vivo.
  // El calendario tiene un solo dueño, y es el JSON — como el resto del
  // contenido. Gate: validate.py [calendario-entero].
  const _contentFields=['days','dayKeys','dayShort','dayShort_en',
    'dayLong','prioLimit','eventPosterLabel','group','ticket_url','ticketing_model',
    'sections','festivalDates']; // P2.2 — secciones data-driven desde el JSON del festival
  _contentFields.forEach(k=>{ if(data[k]!=null) cfg[k]=data[k]; });
  _identFields.forEach(k=>{ if(data[k]!=null&&cfg[k]==null) cfg[k]=data[k]; });
  // Snapshot de identidad ya resuelta — el bloque config{} legacy de abajo
  // tampoco puede pisarla (solo rellenar lo que siga faltando).
  const _identSnap={}; _identFields.forEach(k=>{ if(cfg[k]!=null) _identSnap[k]=cfg[k]; });
  // ── LEGADO: festivales anteriores con bloque config{} en el JSON ──────
  // Festivales nuevos (desde Mujeres 2026) NO deben incluir config{} en el JSON —
  // toda la configuración va en FESTIVAL_CONFIG en index.html.
  // Este bloque existe solo para compatibilidad con festivales anteriores.
  if(data.config){
    const _knownLegacy=['ficci65','cinemancia2025'];
    if(!_knownLegacy.includes(id)){
      console.warn(`[loadFestival] '${id}' tiene bloque config{} en el JSON — los festivales nuevos deben configurarse solo en FESTIVAL_CONFIG (index.html). El bloque config{} se ignora para festivales nuevos.`);
    } else {
      Object.assign(cfg, data.config);
      // Restaurar campos críticos — Object.assign puede pisarlos si config los tiene vacíos
      Object.assign(cfg, _identSnap); // identidad: config.js sigue mandando
      cfg.films=exploded;
      cfg.lbSlugs=data.lbSlugs||cfg.lbSlugs||{};
      cfg.posters=data.posters||cfg.posters||{};
      cfg.customPosters=data.customPosters||cfg.customPosters||{};
    }
  }
  // Absorber venues desde raíz del JSON (AFF/FICCI los tienen hardcodeados; otros festivales los traen aquí)
  if(data.venues) cfg.venues=data.venues;
  if(data.transport) cfg.transport=data.transport;

}

// URL del JSON del festival — dueño único (la convención festId→archivo vivía
// inline y el refresco la habría duplicado).
export function festivalJsonUrl(id){
  // Convierte festivalId a nombre de archivo: ficci65→ficci-65, aff2026→aff-2026
  return 'festivals/'+id.replace(/([a-zA-Z]+)(\d+)$/,'$1-$2')+'.json';
}


// ── PUBLICACIÓN: cfg sellado → state (FILMS + derivados). DUEÑO ÚNICO ────────
// Compartida por loadFestival y el refresco en caliente. Todo lo que depende del
// catálogo publicado vive acá: validación, filtro de prensa, poda de listas
// contra títulos válidos, pase de `past` en la tira y el re-derive del plan
// (syncScheduleWithCatalog — el plan guarda la ELECCIÓN, el catálogo manda el
// resto). Un refresco que no pase por acá dejaría media app mirando el catálogo
// viejo — es la lección de [guardianes-datos-sede]: el dato debe SOBREVIVIR el
// camino completo.
export function publicarCatalogo(id, cfg){
  const _computedPrioLimit = Math.min(8, Math.max(3, Math.round((cfg.dayKeys||[]).length / 2)));
  // _newFilms y _validTitles computados local — no se leen de state.
  // Esto permite que FILMS y los user-state filtrados estén en el MISMO
  // batch atómico. Subscribers post-Fase 6 verán "festival activo y user-state
  // consistente con sus films" en una sola notificación.
  // normTitle: normaliza comillas tipográficas en títulos. Punto único.
  const _mapped = (cfg.films||[]).map(f=>({...f,title:normTitle(f.title)}));
  // ── Validación de datos (domain puro: validateFilm) — particiona drop/keep ──
  // drop (sin title) → excluido de FILMS. errors (day/time) → conservado + logeado.
  // warnings (section/venue/duration) → conservado + default. Diagnóstico agregado
  // SIEMPRE (incluso si todo OK) para no procesar datos malformados en silencio.
  const _newFilms=[]; let _dropCount=0; const _filmErrors=[], _filmWarnings=[];
  for(const f of _mapped){
    const v=validateFilm(f, cfg.dayKeys, cfg.venues);
    if(v.drop){ _dropCount++; console.error(`[loadFestival/${id}] film DROP:`, f, v.errors); continue; }
    if(v.errors.length) _filmErrors.push({title:f.title, errors:v.errors});
    if(v.warnings.length) _filmWarnings.push({title:f.title, warnings:v.warnings});
    _newFilms.push(f);
  }
  console.group(`[loadFestival] ${id} — validación de ${_mapped.length} films`);
  console.log(`OK: ${_newFilms.length-_filmErrors.length} · con errores (conservados): ${_filmErrors.length} · con warnings: ${_filmWarnings.length} · dropeados: ${_dropCount}`);
  if(_filmErrors.length) console.error('Films con errores de datos:', _filmErrors);
  if(_filmWarnings.length) console.warn('Films con warnings:', _filmWarnings);
  console.groupEnd();
  // ── PRENSA E INDUSTRIA — se decide ACÁ, no en cada vista ─────────────────
  // Las funciones con `audience:'press'` son pases de acreditados: el público
  // general no puede entrar. TIFF 2026 trae 247 (audienceType «Press & Market»
  // en su endpoint) sobre obras que YA tienen función pública.
  //
  // El filtro vive en este punto —el único sitio donde FILMS se publica— porque
  // sus 171 consumidores lo leen de ahí: apagado, esas funciones NO EXISTEN para
  // nadie. Filtrar por-vista habría dejado al planificador armando el día
  // alrededor de pases a los que no se puede entrar, y a screensConflict
  // declarando choques contra funciones invisibles.
  //
  // `_todasLasFunciones` guarda la lista COMPLETA en el cfg (que ya cachea la
  // sesión) para que el interruptor re-derive sin volver a pedir el JSON.
  cfg._todasLasFunciones = _newFilms;
  cfg._tienePrensa = _newFilms.some(f=>f.audience==='press');
  _restaurarPrensa(cfg);   // la preferencia de ESTE festival, antes de publicar
  const _visibles = _filtrarPorAudiencia(_newFilms);
  const _validTitles = new Set(_visibles.map(f=>f.title));
  state.batchUpdate({
    _activeFestId: id,
    FILMS: _visibles,
    FESTIVAL_DATES: cfg.festivalDates,
    PRIO_LIMIT: cfg.prioLimit || _computedPrioLimit,
    TZ_OFFSET: cfg.timezoneOffset || '-05:00',
    FESTIVAL_TRANSPORT: cfg.transport || 'transit',
    watchlist: new Set([...state.get('watchlist')].filter(t=>_validTitles.has(t))),
    watched: new Set([...state.get('watched')].filter(t=>_validTitles.has(t))),
    prioritized: new Set([...state.get('prioritized')].filter(t=>_validTitles.has(t))),
  });
  // El banner se decide acá y no en cada tab: `_activeFestId` acaba de quedar
  // fijado, y este es el único momento en que la respuesta puede cambiar.
  _pintarBannerRevision();
  _sincronizarBotonPrensa();  // el botón solo existe si el festival trae pases

  // ── Pase de `past` sobre la tira de días ──────────────────────────────────
  // AHORA, no antes: dayFullyPassed necesita el calendario (FESTIVAL_DATES) y las
  // funciones (FILMS) de ESTE festival, y las dos cosas acaban de publicarse en
  // el batchUpdate de arriba. Hecho en el DOM build, leía los del festival
  // anterior. Un solo dueño de la verdad — la función de dominio — evaluado
  // cuando la verdad existe. Gate: validate.py [calendario-entero].
  document.querySelectorAll('.dtab[data-day]').forEach(b=>{
    if(b.dataset.day!=='all') b.classList.toggle('past', dayFullyPassed(b.dataset.day));
  });

  // ► SYNC DEL PLAN CONTRA EL CATÁLOGO ───────────────────────────────
  // El hydrate de savedAgenda (BATCH 2) corre ANTES de que exista FILMS, así
  // que trae la copia congelada tal cual se guardó. Acá, con el catálogo ya
  // sellado (slots + avisos), cada entrada se re-deriva de su función viva:
  // el plan guarda la ELECCIÓN (título+día+hora), el catálogo manda el resto.
  // Solo persiste en LOCAL: es una corrección derivada e idempotente — subirla
  // a la nube crearía ping-pong entre dispositivos que se normalizan solos.
  if(savedAgenda&&savedAgenda.schedule&&savedAgenda.schedule.length){
    state.update('savedAgenda', a=>({...a, schedule: syncScheduleWithCatalog(a.schedule, _newFilms)}));
    storage.setSavedAgenda(state.get('savedAgenda'));
  }
}

export async function loadFestival(id){
  const _gen=++_loadGen;
  // Subir YA cualquier edición pendiente del festival que estás dejando (con sus
  // globals, aún los actuales) antes de swapear el estado — si no, el debounce
  // dispararía luego con los globals del festival nuevo y la edición vieja se perdía.
  _flushCloudSave();
  // Resetear filtros al cambiar festival
  activeVenue='all';activeSec='all';programaChip='all';_programaChipMatchFn=null;
  lugarClose();
  seccionClose();
  requestAnimationFrame(_fixStickyOffset); // recalculate after festival name changes topbar height
  // Si no está en FESTIVAL_CONFIG, intentar cargar config desde JSON
  if(!FESTIVAL_CONFIG[id]){
    FESTIVAL_CONFIG[id]={films:null,posters:null};
  }
  const cfg=FESTIVAL_CONFIG[id];
  if(!cfg){console.warn('Festival desconocido:',id);return;}
  // Guard: storageKey es crítico — sin él los datos van a localStorage con clave 'undefined'
  if(!cfg.storageKey){
    console.error(`[loadFestival] '${id}' no tiene storageKey en FESTIVAL_CONFIG — abortando.`);
    showToast(t('error_festival_nd'),'error');
    return false;
  }
  // ── Fase 1: cargar datos del festival desde JSON si no están en memoria ──
  if(!cfg.films){
    try{
      // Sin banner de error: el catch externo muestra el toast y reporta a Sentry.
      // (El banner rojo fixed nunca se removía → quedaba tapando el topbar tras un
      // retry exitoso.)
      const data=await _fetchFestivalJson(festivalJsonUrl(id));
      _ingerirDatosFestival(id, cfg, data);

    }catch(e){
      console.error('Error cargando festival '+id+':',e);
      report(e,'loadFestival:'+id); // visible en Sentry (antes se tragaba en silencio)
      showToast(t('toast_conexion'),'error',5000);
      return false;
    }
    // El fetch pudo tardar (red del festival): si otra carga arrancó mientras tanto,
    // abortar ANTES de swapear cualquier estado — la carga nueva ya está en curso.
    if(_gen!==_loadGen) return false;
  }
  // Guard: dayKeys y days son requeridos — sin ellos el UI de calendario crashea
  // (movido pre-batch en p5.5 para que el fallo no deje state parcialmente swapeado)
  if(!cfg.dayKeys||!cfg.days||!cfg.days.length){
    console.error(`[loadFestival] '${id}' no tiene dayKeys/days en FESTIVAL_CONFIG.`);
    showToast(t('error_festival_nd'),'error',6000);
    return false;
  }
  // Guard: festivalDates ({dayKey:isoDate}) → FESTIVAL_DATES. Sin él screeningPassed
  // y el match de día se rompen (FESTIVAL_DATES[day]=undefined en todo).
  if(!cfg.festivalDates||typeof cfg.festivalDates!=='object'){
    console.error(`[loadFestival] '${id}' no tiene festivalDates en FESTIVAL_CONFIG.`);
    showToast(t('error_festival_nd'),'error',6000);
    return false;
  }
  // Guard: festivalEndStr → FESTIVAL_END (new Date). Inválido → Invalid Date →
  // festivalEnded() y toda la lógica temporal se rompen silenciosamente.
  if(!cfg.festivalEndStr||isNaN(new Date(cfg.festivalEndStr).getTime())){
    console.error(`[loadFestival] '${id}' no tiene festivalEndStr válido en FESTIVAL_CONFIG.`);
    showToast(t('error_festival_nd'),'error',6000);
    return false;
  }
  // LRU del cache: este festival pasa a MRU; si se excede el cap, evicta el menos
  // usado (nunca este). cfg.films ya está seteado (fetch o cache) llegados acá.
  _touchFestivalCache(id);
  // Secciones data-driven (P2.2): si el festival trae `sections` en su JSON,
  // mergear su metadata (color/en/archetype/order) en los mapas globales antes de
  // renderizar. Idempotente. Festivales viejos sin `sections` no cambian nada.
  mergeFestivalSections(cfg.sections);
  // ── Non-roster cfg apply (legacy) ──────────────────────────────────
  // Estos globals no están en el state roster (Fase 5.5). Siguen como
  // asignaciones directas hasta Fase 8.
  POSTERS=cfg.posters;
  LB_SLUGS=cfg.lbSlugs||{};
  DAY_KEYS=cfg.dayKeys;
  setDayShortEn(cfg.dayShort_en||cfg.dayShort);
  // Si el festival no tiene dayShort en español (ej. Tribeca: valores en inglés),
  // construirlo desde las fechas ISO usando el día de la semana.
  const _EN_TO_ES={'SUN':'DOM','MON':'LUN','TUE':'MAR','WED':'MIÉ','THU':'JUE','FRI':'VIE','SAT':'SÁB'};
  const _needsTranslation = Object.values(cfg.dayShort||{}).some(v=>
    /^(MON|TUE|WED|THU|FRI|SAT|SUN)/.test(v)
  );
  let _esShort;
  if(_needsTranslation){
    const _translated={};
    Object.entries(cfg.dayShort||{}).forEach(([k,v])=>{
      const enAbb=v.split(' ')[0];
      const num=v.split(' ')[1]||'';
      const esAbb=_EN_TO_ES[enAbb]||enAbb;
      _translated[k]=num?esAbb+' '+num:esAbb;
    });
    _esShort=_translated;
  } else {
    _esShort=cfg.dayShort||{};
  }
  setDayShort(_esShort);
  CUSTOM_POSTERS=cfg.customPosters||{};
  setCustomPosters(CUSTOM_POSTERS);
  setPosters(POSTERS);
  // Mutar DAYS en sitio (const) + regenerar DAY_ABBR/DAY_NUM
  DAYS.length=0;
  cfg.days.forEach(d=>DAYS.push(d));
  Object.keys(DAY_ABBR).forEach(k=>delete DAY_ABBR[k]);
  Object.keys(DAY_NUM).forEach(k=>delete DAY_NUM[k]);
  cfg.days.forEach(d=>{DAY_ABBR[d.k]=d.lbl;DAY_NUM[d.k]=d.d;});
  // PRIO_LIMIT: lo computa publicarCatalogo (batch 3) — regla round(días/2), cap [3,8].

  // ► BATCH 1 — transition + clear ───────────────────────────────────
  // FESTIVAL_STORAGE_KEY debe estar al new fest ANTES de batch 2 (loadState
  // lee storage prefijado). FESTIVAL_END debe estar antes del day-tab DOM
  // build (dayFullyPassed lo lee). festivalEndStr ('…T23:59:00') se ancla a la
  // zona del festival vía cfg.timezoneOffset → FESTIVAL_END es un instante
  // ABSOLUTO correcto desde cualquier dispositivo (festivalEnded compara contra
  // simNow absoluto). Sin offset (festivales viejos) cae a hora local — equivalente
  // para audiencia en la misma zona.
  //
  // El clear de los 9 estados por-festival se DERIVA de FESTIVAL_STATE
  // (festival-context.js): agregar un estado nuevo por-festival lo auto-incluye
  // acá → imposible olvidar su reset al cambiar de festival (por construcción).
  // availability es POR-FESTIVAL: su empty siembra {blocks:[]} por dayKey; loadState
  // (batch 2) hidrata desde el storage prefijado. NO hereda blocks del festival
  // anterior — antes, dos festivales con dayKeys idénticos (TT/FantasoFest 13–19 JUL)
  // sangraban disponibilidad y luego divergían. Auditoría de festivales simultáneos.
  state.batchUpdate({
    FESTIVAL_STORAGE_KEY: cfg.storageKey,
    FESTIVAL_END: new Date(cfg.festivalEndStr+(cfg.timezoneOffset||'')),
    // Viaja junto a FESTIVAL_END porque es su corrección: festivalEnded() es pura
    // aritmética contra esa fecha, y un festival APLAZADO la cruza igual — FICMA
    // habría entrado en Modo Recuerdo el 18 ago, pidiéndole a la gente calificar
    // películas que nunca vio. Ver domain/time.js festivalEnded.
    FESTIVAL_POSTPONED: !!(cfg.status&&cfg.status.kind==='postponed'),
    ...deriveClear(cfg),
  });
  // Rebuild day tabs DOM
  const _dt=document.getElementById('dtabs');
  if(_dt){
    _dt.innerHTML='';
    // ── dtab "TODO" — muestra todo el programa sin filtro de día ──
      const todoBtn=document.createElement('button');
      todoBtn.className='dtab on';
      todoBtn.dataset.day='all';
      todoBtn.style.cssText='display:flex;align-items:center;justify-content:center;padding:0 14px';
      todoBtn.innerHTML='<span data-i18n="bar_todo" style="font-size:var(--t-sm);font-weight:700;letter-spacing:.08em;text-transform:uppercase">'+t('bar_todo')+'</span>';
      todoBtn.onclick=()=>{
        activeDay='all';activeVenue=keepCityOnly(activeVenue);activeSec='all';selectedIdx=null;
        cartelaMode='horario';
        setProgramaView('grid'); // TODO → siempre Grid
        document.querySelectorAll('.dtab').forEach(t=>t.classList.toggle('on',t.dataset.day==='all'));
        _syncPmodeTabs(); // la píldora Hoy/Mañana espeja al día activo (acá: ninguno)
        _renderProgramaContent(true); // cambio de día (TODO) → scroll al tope
        _updateProgramaActiveFilter();
        if(activeMNav!=='mnav-cartelera') switchMainNav('mnav-cartelera');
      };
      // Separador visual entre TODO y días de fecha
      const todoSep=document.createElement('div');
      todoSep.style.cssText='width:1px;background:var(--bdr);margin:6px 0;flex-shrink:0';
      _dt.appendChild(todoBtn);
      _dt.appendChild(todoSep);

      cfg.days.forEach(day=>{
      const btn=document.createElement('button');
      // Sin `past` acá: en este punto FESTIVAL_DATES todavía es el del festival
      // ANTERIOR (se publica en el batchUpdate, ~60 líneas más abajo), así que
      // dayFullyPassed cortaba en `if(!dateStr) return false` y NINGÚN día se
      // atenuaba nunca, en ningún festival. Se marca después del puente, cuando
      // el calendario y FILMS ya son los de este festival. Ver el pase de `past`.
      btn.className='dtab';
      btn.dataset.day=day.k;
      const _dtabLblES=day.lbl;
      const _dtabLblEN=(DAY_SHORT_EN[day.k]||'').split(' ')[0]||day.lbl;
      const _dtabLbl=_lang==='en'?_dtabLblEN:_dtabLblES;
      btn.dataset.lblEs=_dtabLblES;
      btn.dataset.lblEn=_dtabLblEN;
      btn.innerHTML=`<span class="dtab-date">${_dtabLbl}</span><span class="dtab-name">${day.d}</span>`;
      btn.onclick=()=>{
        activeDay=day.k;activeVenue=keepCityOnly(activeVenue);selectedIdx=null;
        setProgramaView('list'); // día específico → siempre Lista (horarios/planificación)
        document.querySelectorAll('.dtab').forEach(t=>t.classList.toggle('on',t.dataset.day===day.k));
        _syncPmodeTabs(); // la píldora Hoy/Mañana espeja al día elegido
        _renderProgramaContent(true); // cambio de día específico → scroll al tope
        _updateProgramaActiveFilter();
        if(activeMNav!=='mnav-cartelera') switchMainNav('mnav-cartelera');
      };
      _dt.appendChild(btn);
    });
  }
  // Reset UI state (non-roster, sin cambios)
  activeDay=cfg.dayKeys[0];
  activeVenue='all';activeSec='all';selectedIdx=null;
  cachedResult=null; // invalidar cache del festival anterior — evita mostrar escenarios de otro festival
  programaSubMode='hoy';cartelaMode='horario';activeDay='all';programaViewMode='grid';
  miPlanViewStart=0;activeMiPlanDay=0;

  // ► BATCH 2 — hidrate desde storage del nuevo fest ─────────────────
  // loadState() internamente hace state.batchUpdate con los 9 user-state keys
  // (watchlist/watched/prioritized/filmRatings/availability/savedAgenda/
  // lastRemovedSlots/filmDelays/filmDelaysHistory).
  loadState();

  // ► BATCH 3 — publicación del catálogo (dueño único: publicarCatalogo) ────
  publicarCatalogo(id, cfg);

  // ► CIUDAD RECORDADA (festivales multiciudad) ──────────────────────────────
  // La ciudad es CONTEXTO, no un filtro más: quien está en Quibdó sigue en Quibdó
  // la próxima vez que abre la app. Se restaura solo si (a) hay una guardada para
  // ESTE festival y (b) sigue existiendo en sus sedes — si el festival cambió su
  // programación y esa ciudad ya no está, se descarta en silencio en vez de dejar
  // el programa vacío. Cambiarla o quitarla es un tap en el filtro de Lugar.
  // Tres estados: '' = nunca preguntado (dispara el sheet) · 'all' = eligió ver
  // todas (no filtra, pero no se vuelve a preguntar) · 'city:X' = su ciudad.
  const _savedCity=storage.getCityFilter();
  if(_savedCity&&_savedCity!=='all'){
    const _c=_savedCity.slice(5);
    const _existe=Object.values(cfg.venues||{}).some(v=>v&&v.city===_c);
    if(_existe) activeVenue=_savedCity; else storage.setCityFilter('');
  }
  // El sheet se abre DESPUÉS del primer render del programa (rAF doble): si se
  // abriera antes, el usuario ve el sheet sobre una pantalla vacía y no entiende
  // de qué le están hablando. Ver openCitySheet: se auto-descarta si el festival
  // no es multiciudad, así que acá no hace falta repetir la condición.
  if(!storage.getCityFilter()){
    requestAnimationFrame(()=>requestAnimationFrame(()=>openCitySheet()));
  }

  // Set active day to today
  // Aplazado: NO aterrizar en «Hoy» aunque el calendario diga que el festival va —
  // sus fechas viejas siguen en el dato a propósito. Se abre como un festival
  // futuro: grilla completa, sin «hoy». (El mismo estado ya silencia AHORA y la
  // rehidratación del plan vía _classifyFestival/isNowShowing.)
  const _postponed=!!(cfg.status&&cfg.status.kind==='postponed');
  const _ts=simTodayStr();
  const _ni=_postponed?-1:DAY_KEYS.findIndex(d=>FESTIVAL_DATES[d]===_ts);
  if(_ni>=0){
    activeDay=DAY_KEYS[_ni];
    programaSubMode='hoy'; // Durante el festival → ir directo a Hoy
  }
  // Regla global inamovible: navegación por día específico → lista por defecto
  programaViewMode=activeDay==='all'?'grid':'list';
  // Update fest-bar
  renderFestBar(cfg);
  // Banda APLAZADO — dueño único: renderPostponedBanner (festival.js). Se llama
  // SIEMPRE (limpia sola si no aplica; cambio de festival la retira) y también
  // desde setLang, porque la banda persiste y el cambio de idioma no pasa por acá.
  renderPostponedBanner(cfg);
  // Re-render festival selector con el nuevo festival activo
  _renderFestivalSelector(id);
  // Persist choice
  storage.setActiveFestId(id);
  // Avisar al reloj el festival en curso (F1.6). Inerte fuera del wrapper iOS.
  window.__otfPushWatchFestival?.();
  // Retraso colaborativo (Fase B): (re)suscribir a los reportes de este festival.
  // Fire-and-forget — no bloquea el render; el badge se pinta al llegar datos.
  subscribeDelaysCloud();
  // Render — await dos rAFs: primero renderiza, segundo confirma el paint
  closeFestivalSheet();
  switchMainNav('mnav-cartelera');
  await new Promise(resolve=>requestAnimationFrame(()=>{showDayView();requestAnimationFrame(resolve);}));
  // Si otra carga arrancó durante el doble-rAF, abortar antes de disparar el trabajo
  // async de nube (_cloudLoad/subscribePlanCloud) — sería del festival equivocado.
  if(_gen!==_loadGen) return false;
  // Posicionar la barra de días en el día activo (hoy, durante el festival).
  // El render fija activeDay + la clase .on, pero no scrollea #dtabs → sin esto
  // la barra arranca en el día 1 con el día de hoy fuera de pantalla. Corre tras
  // el doble-rAF (barra ya pintada y medible). Mismo patrón que filterByDay.
  scrollDtabsToActive();
  // Tab de aterrizaje contextual (regla de Juan, 17 jul): DURANTE el festival, si el
  // usuario YA tiene plan, su pantalla de trabajo es Mi Plan — aterrizar ahí. Sin plan
  // (o festival futuro/pasado) → Programa, como siempre: un Mi Plan vacío no invita a
  // nada; el programa sí. Cartelera queda inicializada debajo (showDayView arriba) para
  // que volver a ella sea instantáneo. El auto-salto de 30 min (main.js) sigue siendo
  // un caso más fuerte de esta misma regla.
  if(_classifyFestival(cfg)==='ongoing' && savedAgenda&&savedAgenda.schedule&&savedAgenda.schedule.length){
    switchMainNav('mnav-miplan');
    showAgView();
  }
  // Resolver posters via TMDB en background — no bloquea la UI
  _autoResolveFestivalPosters().catch(()=>{});
  // F0 sync multi-dispositivo: si el usuario está firmado (no anónimo), bajar el
  // plan de la nube para ESTE festival con guard (no pisa ediciones locales sin
  // subir ni datos ya frescos — ver _cloudLoad). Boot y cambio de festival pasan
  // por acá → cubre "edito en el iPhone, abro en el iPad/Watch y veo lo último".
  // Fire-and-forget; re-renderiza la vista activa al aplicar la nube.
  const _u=state.get('_sbUser');
  if(_u&&!_u.is_anonymous){
    _cloudLoad({guard:true}).then((applied)=>{
      // Si el boot-load NO aplicó nube y hay edición local sin subir (dirty —
      // p.ej. el upsert falló offline en la sala), re-empujarla AHORA. Antes
      // quedaba pendiente hasta que el usuario mutara algo de nuevo, y mientras
      // tanto este dispositivo también ignoraba el Realtime entrante.
      if(!applied && storage.getCloudDirty()) _cloudSave();
      showDayView(); _renderProgramaContent();
    }).catch(()=>{});
    // F0.5: sync EN VIVO — al cambiar el plan en otro dispositivo (o el Watch),
    // aplicar el cambio sin reabrir. Idempotente por (user, festival).
    subscribePlanCloud();
  }
}

// backToSplash — el wordmark como "volver al inicio" (patrón de toda app web).
// Decisión de Juan (20 jul 2026), opción A: se sale del splash con "Entrar" (que
// pre-selecciona el festival en curso), sin botón de cancelar.
// POR QUÉ UN RELOAD y no re-mostrar el nodo: dismissSplash() hace s.remove() — el
// splash NO queda oculto, se elimina del DOM. Recrearlo a mano (markup + animación
// de entrada + re-cableado del riel) sería una segunda implementación del arranque,
// justo lo que venimos eliminando.
// NO hace falta guardar antes: cada mutación ya persiste en localStorage en el
// momento en que ocurre (saveWL/saveWatched/saveRating… escriben síncrono), así que
// recargar no pierde nada. Una subida a la nube en vuelo tampoco se pierde: queda
// cloud_dirty persistido y el re-push del próximo boot la sube.
export function backToSplash(){
  location.reload();
}

export function dismissSplash(){
  // Sin festival elegido no hay a dónde entrar. El botón "Entrar" está disabled
  // hasta que se elige (selectSplashFest lo habilita); guard defensivo por si
  // el click llega igual.
  if(!_splashSelectedFestId) return;
  // Festival EN REVISIÓN: pide clave una vez por festival. Se comprueba acá, en
  // el único punto por el que se entra a un festival, y no en la card: así no
  // hay dos caminos que puedan divergir. La hoja solo valida; entrar es asunto
  // de esta función, que se vuelve a llamar cuando la clave es correcta.
  const _cfgSel=FESTIVAL_CONFIG[_splashSelectedFestId]||{};
  if(_cfgSel.review&&_cfgSel.review.key&&!_reviewDesbloqueado(_splashSelectedFestId)){
    openReviewSheet(_splashSelectedFestId);
    return;
  }
  const s=document.getElementById('otrofestiv-splash');
  const btn=document.querySelector('.splash-enter-btn');
  if(btn) btn.classList.add('loading');
  loadFestival(_splashSelectedFestId)
    .then(ok=>{
      if(ok===false){
        if(btn) btn.classList.remove('loading'); // reset spinner — el error ya se mostró con toast
        return;
      }
      // 150ms para que el compositor de iOS se asiente antes de revelar
      setTimeout(()=>{
        if(s){s.classList.add('fade-out');setTimeout(()=>{s.remove();
          // El splash ya no está: ahora sí puede aparecer el banner de revisión.
          _pintarBannerRevision();// FIX iOS compositor (especialmente Leviza/festival activo):
          // initProgramaModeBar() corrió bajo el splash → reflowó el topbar →
          // compositor cacheó nav en posición incorrecta. Re-ejecutar DESPUÉS de
          // quitar el splash fuerza el reflow en viewport abierto → posición correcta.
          // Luego translateY(0)→'' en doble rAF hace flush definitivo del compositor.
          (function(){
            if(typeof initProgramaModeBar==='function') initProgramaModeBar();
            if(typeof _fixStickyOffset==='function') _fixStickyOffset();
            const _nav=document.getElementById('main-nav');
            if(!_nav) return;
            _nav.style.transform='translateY(0)';
            requestAnimationFrame(function(){
              requestAnimationFrame(function(){
                _nav.style.transform='';
              });
            });
          })();},680);}
        if(btn) btn.classList.remove('loading');
      },150);
    })
    .catch(e=>{
      console.error('Error init festival:',e);
      if(btn) btn.classList.remove('loading');
    });
}

// ── el filtro de audiencia y su interruptor ─────────────────────────────────
// Un solo dueño para las dos direcciones: al cargar (arriba) y al conmutar.
export function _filtrarPorAudiencia(films){
  return showPress ? films : films.filter(f=>f.audience!=='press');
}

// Conmuta Prensa e Industria y RE-PUBLICA FILMS desde la lista completa que el
// cfg ya tiene cacheada — sin volver a pedir el JSON ni re-validar.
// Se persiste por festival: quien tiene acreditación la tiene toda la semana.
export function togglePressScreenings(){
  const cfg = FESTIVAL_CONFIG[state.get('_activeFestId')];
  if(!cfg || !cfg._tienePrensa) return;
  const nuevo = !showPress;
  showPress = nuevo;
  storage.setShowPress(cfg.storageKey, nuevo);
  const _vis = _filtrarPorAudiencia(cfg._todasLasFunciones||[]);
  state.batchUpdate({ FILMS: _vis });
  _sincronizarBotonPrensa();

  // ── AL ENCENDER, LLEVAR A DONDE SE VE LO AÑADIDO ─────────────────────────
  // El grid de Explorar es un catálogo de OBRAS: una tarjeta por obra, y
  // ninguna obra existe solo en prensa. Ahí el interruptor no puede añadir
  // NADA — antes solo reordenaba, y ahora (con el representante anclado a lo
  // público) no se mueve. Las funciones añadidas son visibles donde la unidad
  // es la función: la vista Lista, que además exige un día concreto.
  //
  // Así que al ENCENDER desde una vista que no puede mostrarlas, se salta a
  // Lista y, si estábamos en «todos los días», al primer día CON pases. Al
  // apagar no se devuelve a nadie a ningún sitio: quedarse donde uno está es
  // menos sorprendente que un segundo salto.
  if(nuevo){
    const _conPrensa = new Set(_vis.filter(f=>f.audience==='press').map(f=>f.day));
    if(_conPrensa.size && (programaViewMode!=='list' || activeDay==='all')){
      if(activeDay==='all' || !_conPrensa.has(activeDay)){
        const _d = (cfg.dayKeys||[]).find(d=>_conPrensa.has(d));
        if(_d){
          activeDay = _d;
          document.querySelectorAll('.dtab').forEach(t=>t.classList.toggle('on', t.dataset.day===_d));
          _syncPmodeTabs();
        }
      }
      setProgramaView('list');   // ya re-renderiza y sube al tope
      _updateProgramaActiveFilter();
      return;
    }
  }
  _updateProgramaActiveFilter();
  _renderProgramaContent();
  // Y la vista del PLAN, si es la que está en pantalla (30 ago 2026). El
  // interruptor es un insumo del plan —entró a planInputSignature—, así que
  // apagarlo lo deja DESACTUALIZADO; pero acá solo se repintaba Programa, y el
  // aviso «plan desactualizado» no aparecía hasta que otra cosa disparara un
  // render. Marcado por dentro y mudo por fuera es lo mismo que no marcarlo:
  // el usuario seguía viendo un pase de acreditados al que ya no puede entrar.
  const _agv=document.getElementById('ag-view');
  if(_agv&&_agv.classList.contains('visible')) renderAgenda();
}

// Lee la preferencia guardada de ESTE festival. La llama loadFestival antes de
// publicar FILMS, para que la primera pintura ya sea la correcta.
export function _restaurarPrensa(cfg){
  let v = false;
  v = storage.getShowPress(cfg.storageKey);
  showPress = v;
}

// El botón solo EXISTE en festivales que tienen pases de prensa, y refleja su
// estado con la clase `.on` — el mismo estado único que el resto de la barra.
export function _sincronizarBotonPrensa(){
  const b = document.getElementById('prensa-btn');
  if(!b) return;
  const cfg = FESTIVAL_CONFIG[state.get('_activeFestId')];
  const hay = !!(cfg && cfg._tienePrensa);
  b.style.display = hay ? '' : 'none';
  b.classList.toggle('on', hay && !!showPress);
  b.setAttribute('aria-pressed', String(hay && !!showPress));
}
