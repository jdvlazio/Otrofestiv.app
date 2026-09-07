// ── src/view/sheets.js — Fase 8 Step 6b (CABLEADO) ──────────────────────────
//
// ESTADO: importado por src/main.js (Step 6b). Lifecycle de paneles (sheets):
//   open/close foundational sin estado mutable compartido. Los sheets pesados
//   (pel, rating, conflict, av) que arrastran el render pipeline o comparten
//   estado con handlers de Wave 7 se DIFIEREN.
//
// DEPS: i18n(t). festival-state via STATE BRIDGE: _sbUser.
// Invocados vía data-action (ACTION_REGISTRY arrows en main.js resuelven el
//   binding importado) — sin exposición globalThis nueva.

import { t } from "../i18n/i18n.js";
import { storage } from '../storage/storage.js';
import { FESTIVAL_CONFIG } from "../config.js";
import { ICONS, festivalShortName } from "./components.js";
import { festivalCities } from "./helpers.js";
import { festivalEnded } from "../domain/time.js";

export function openAuthSheet(){
  if(_sbUser){_showSignedInSheet();return;}
  const s=document.getElementById('auth-sheet');
  if(s){
    s.style.display='flex';
    setTimeout(()=>s.classList.add('open'),10);
    // Aplicar i18n al abrir — garantiza subtítulos en el idioma activo
    s.querySelectorAll('[data-i18n]').forEach(el=>{el.textContent=t(el.dataset.i18n);});
    s.querySelectorAll('[data-i18n-ph]').forEach(el=>{el.placeholder=t(el.dataset.i18nPh);});
  }
}

// _esRevisionActiva — ¿el festival ABIERTO ahora es uno en revisión? Dueño único
// de la pregunta: de acá cuelgan las tres restricciones (no sincronizar, no
// compartir, banner). Se pregunta por el festival activo, no por el elegido en
// el splash, porque las restricciones aplican mientras se está DENTRO.
export function _esRevisionActiva(){
  const cfg=FESTIVAL_CONFIG[globalThis._activeFestId]||{};
  return !!(cfg.review&&cfg.review.key);
}

// Enciende/apaga el banner de revisión.
//
// NO en el splash: ahí el aviso ya lo da el separador «En revisión» del riel, y
// repetirlo abajo es decir dos veces lo mismo en una pantalla que se lee de un
// golpe (lo levantó Juan al revisarlo). loadFestival() lo enciende cuando el
// splash TODAVÍA está en pantalla —tarda 830 ms en irse— así que la condición
// no puede ser solo «el festival es de revisión»: también tiene que no haber
// splash. Se vuelve a pintar cuando el splash se retira.
export function _pintarBannerRevision(){
  const b=document.getElementById('review-banner');
  if(!b) return;
  const haySplash=!!document.getElementById('otrofestiv-splash');
  b.classList.toggle('on', _esRevisionActiva() && !haySplash);
}

// ── Clave de un festival en revisión ─────────────────────────────────────────
// Un festival que aún no se publica, abierto a su propio equipo para que lo vea
// en la app real antes que nadie. La clave vive en config.js —en el bundle— a
// propósito: protege de entrar por accidente, no de alguien decidido, y para
// esto eso basta. El permiso caduca solo (review.until); no hay que acordarse
// de revocarlo.
//
// Se recuerda por festival y no globalmente: entrar a uno no abre los otros.

export function _reviewDesbloqueado(festId){
  try{ return storage.getReviewOk().includes(festId); }
  catch(e){ return false; }
}

function _recordarReview(festId){
  try{
    storage.addReviewOk(festId);
  }catch(e){}
}

let _reviewPendiente=null;   // festId esperando clave

export function openReviewSheet(festId){
  _reviewPendiente=festId;
  const s=document.getElementById('review-sheet');
  if(!s) return;
  const inp=document.getElementById('review-key-inp');
  const msg=document.getElementById('review-msg');
  if(inp) inp.value='';
  if(msg) msg.textContent='';
  s.style.display='flex';
  setTimeout(()=>{s.classList.add('open'); if(inp) inp.focus();},10);
}

export function closeReviewSheet(){
  _reviewPendiente=null;
  const s=document.getElementById('review-sheet');
  if(s){s.classList.remove('open');setTimeout(()=>s.style.display='none',300);}
}

// Devuelve el festId desbloqueado, o null. Quien llama decide qué hacer con él
// —acá no se entra a ningún festival: esta hoja solo valida.
export function submitReviewKey(){
  const festId=_reviewPendiente;
  const inp=document.getElementById('review-key-inp');
  const msg=document.getElementById('review-msg');
  const dada=(inp&&inp.value||'').trim();
  const real=((FESTIVAL_CONFIG[festId]||{}).review||{}).key||'';
  if(!festId||!real) { closeReviewSheet(); return null; }
  if(dada&&dada.toLowerCase()===String(real).toLowerCase()){
    _recordarReview(festId);
    closeReviewSheet();
    return festId;
  }
  if(msg) msg.textContent=t('review_err');
  if(inp){ inp.value=''; inp.focus(); }
  return null;
}

export function closeAuthSheet(){
  const s=document.getElementById('auth-sheet');
  if(s){s.classList.remove('open');setTimeout(()=>s.style.display='none',300);}
}

// ── Sheet de CIUDAD (festivales multiciudad) ─────────────────────────────────
// FICDEH 2026: 387 funciones en 11 ciudades. Quien entra desde Quibdó veía 140
// funciones de Bogotá que no puede alcanzar. Se pregunta UNA vez, al entrar al
// Programa, y la respuesta queda como contexto (ver keepCityOnly / cityFilter).
//
// SALTEABLE a propósito ("ver todas"): hay quien solo quiere mirar el programa
// completo — prensa, equipo del festival, curiosos. Forzar la elección los
// expulsa. Elegir "ver todas" también se recuerda (valor 'all'), así que la
// pregunta no vuelve.
//
// La lista sale de festivalCities() — el MISMO dueño que el nivel de ciudades
// del filtro de Lugar, así que las dos vistas nunca pueden divergir. Cada fila
// muestra su VENTANA DE FECHAS derivada de las funciones de esa ciudad: en un
// festival itinerante (Tercer Tiempo: DeKalb → Bogotá → CDMX en fechas
// distintas) cada ciudad tiene la suya, y así se lee sin campos nuevos.
export function openCitySheet(){
  const sh=document.getElementById('city-sheet');
  if(!sh) return;
  const cities=festivalCities(FILMS);
  if(cities.length<2) return;               // no multiciudad → no hay nada que preguntar
  // Festival TERMINADO → tampoco hay nada que preguntar (Juan, 4 sep 2026).
  // «¿A cuál ciudad vas?» está en futuro, y era lo primero y ÚNICO que veía
  // quien abría un festival pasado: medido en FICDEH, la hoja ocupa 390x844
  // —el viewport entero— con z-index 9999, así que además se comía el toque a
  // las pestañas. Lo que se retira es la PREGUNTA, no la posibilidad: el filtro
  // de Lugar sigue ofreciendo las mismas ciudades para releer el programa de
  // una (decisión de Juan; T177 vigila las dos mitades).
  // Se descarta acá, junto al otro caso de «no hay nada que preguntar», y no en
  // el disparador: así vale para cualquiera que la abra, no solo para el arranque.
  if(festivalEnded()) return;
  const cfg=FESTIVAL_CONFIG[_activeFestId]||{};
  // El afiche da la identidad; por eso el sheet NO repite el nombre del festival
  // (el usuario acaba de elegirlo en el splash). Si no hay keyArt, cae al
  // fallback tipográfico del riel — misma degradación que la card del splash.
  const art=document.getElementById('city-sheet-art');
  art.innerHTML=cfg.keyArt
    ?`<img class="splash-card-art" src="${cfg.keyArt}" alt="" onerror="this.remove()">`
    :`<span class="splash-card-fb">${festivalShortName(cfg)||cfg.name||''}</span>`;
  document.getElementById('city-sheet-label').textContent=t('city_sheet_label');
  // SIN conteo de funciones (Juan, 7 ago): en el filtro el número dice "vas a ver
  // N si filtrás por esto" — es la consecuencia de la acción. Acá se leería como
  // "el festival tiene N en Bogotá", una afirmación sobre el FESTIVAL que no
  // podemos sostener: montamos lo que montamos, y a veces menos de lo que el
  // festival programa. Además mezclaría proyecciones con charlas y talleres, así
  // que ni "funciones" ni "actividades" sería correcto.
  // SIN pin: en el filtro de Lugar el pin es de las SEDES; las ciudades no lo
  // llevan. Misma gramática acá.
  // SIN ventana de fechas (Juan, 7 ago): en un festival simultáneo todas dirían
  // casi lo mismo y es repetición visual. Los tabs de día siguen siendo los del
  // festival ENTERO —la madre— y un día sin funciones en tu ciudad simplemente
  // se ve vacío. La ciudad se elige por su nombre, nada más.
  // CON marca de caída (Juan, 2 sep 2026): la pregunta que abre la app ofrecía
  // las ciudades del sismo con la misma tipografía que las vivas. La fila sigue
  // siendo TOCABLE —no se oculta, se dice— y al entrar el banner explica con las
  // palabras del festival; lo que cambia es que ahora se sabe antes de elegir.
  // La palabra es la MISMA del rótulo de ese banner (notice_cancelada), así que
  // la pregunta y la respuesta se nombran igual y no hace falta copy nuevo.
  document.getElementById('city-sheet-list').innerHTML=cities.map(c=>
    `<div class="lugar-opt city" data-action="citySheetPick" data-city="${String(c.name).replace(/"/g,'&quot;')}">
      <span>${c.name}</span>${c.cancelled?`<span class="lugar-canc">${t('notice_cancelada')}</span>`:''}${ICONS.chevronR}
    </div>`).join('')
  // La salida es una fila más de la lista (como "todos los lugares" en el filtro),
  // no un "cancelar": no está cancelando nada, está eligiendo la otra opción.
  +`<div class="lugar-opt escape" data-action="citySheetAll">${t('city_sheet_todas')}</div>`;
  sh.style.display='flex';
  setTimeout(()=>sh.classList.add('open'),10);
}

export function closeCitySheet(){
  const sh=document.getElementById('city-sheet');
  if(sh){sh.classList.remove('open');setTimeout(()=>sh.style.display='none',300);}
}

export function closeAvSheet(){
  const ov=document.getElementById('av-sheet-overlay');
  if(ov) ov.style.display='none';
}

export function openFestivalSheet(){
  const ov=document.getElementById('fs-overlay');
  const sh=document.getElementById('fs-sheet');
  if(ov) ov.classList.add('open');
  if(sh) sh.classList.add('open');
}

export function closeFestivalSheet(){
  const ov=document.getElementById('fs-overlay');
  const sh=document.getElementById('fs-sheet');
  if(ov) ov.classList.remove('open');
  if(sh) sh.classList.remove('open');
}

export function closePVRating(){
  const overlay=document.getElementById('pv-rating-overlay');
  const sheet=document.getElementById('pv-rating-sheet');
  if(overlay) overlay.classList.remove('open');
  if(sheet){
    sheet.classList.remove('open');
    setTimeout(()=>{ if(!sheet.classList.contains('open')) sheet.style.display='none'; },350);
  }
}

export function closePrioLimit(){
  document.getElementById('prio-limit-overlay').classList.remove('open');
  document.getElementById('prio-limit-sheet').classList.remove('open');
}

export function _showSignedInSheet(){
  const s=document.getElementById('auth-sheet');
  document.getElementById('auth-sheet-step1').style.display='none';
  document.getElementById('auth-sheet-step2').style.display='none';
  document.getElementById('auth-sheet-step3').style.display='block';
  document.getElementById('auth-signed-email').textContent=_sbUser?.email||'';
  if(s){s.style.display='flex';setTimeout(()=>s.classList.add('open'),10);}
}
