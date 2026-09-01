// ── src/view/feedback.js — Fase 8 Step 6b (CABLEADO) ────────────────────────
//
// ESTADO: importado por src/main.js (Step 6b). Notificaciones al usuario:
//   toasts, modales de acción/conflicto, label de sim-time.
//
// DEPS: i18n(t); components(parseProgramTitle). festival-state via STATE BRIDGE:
//   DAY_KEYS, FESTIVAL_DATES, FESTIVAL_END, _lang.

import { t } from "../i18n/i18n.js";
import { parseProgramTitle } from "./components.js";

export const _SIM_TOTAL=()=>((_simFestEnd()-_simFestStart())/60000)||1;

// _toastArriba — DUEÑO ÚNICO de dónde aterriza el toast. El toast vive a 62px
// del borde inferior, encima de la barra de tabs; y las hojas son TODAS
// bottom-anchored, así que con una abierta caía justo sobre sus controles:
// medido en la hoja de calificación, tapaba 38 de los 84px del área de
// estrellas —la mitad de abajo— y con showActionToast (pointer-events:all)
// además interceptaba el toque. Con una hoja abierta el aviso se va ARRIBA,
// donde no hay nada que tocar. `.open` es la marca que usan todas las hojas
// (city, fs, auth, pel, pv-rating): se verificó una por una.
export function _toastArriba(t){
  if(!t) return;
  t.classList.toggle('arriba', !!document.querySelector('[id$="-sheet"].open, [id$="-overlay"].open'));
}

export function showToast(msg,type='info',duration=2800){
  let t=document.getElementById('prio-toast');
  if(!t){t=document.createElement('div');t.id='prio-toast';document.body.appendChild(t);}
  t.className='prio-toast '+type;_toastArriba(t);t.innerHTML=msg;t.style.opacity='1';t.style.pointerEvents='none';
  clearTimeout(t._to);t._to=setTimeout(()=>{t.style.opacity='0';},duration);
}

// `opts.altLabel`+`opts.altCb` añaden una TERCERA acción entre el primario y el
// cancelar. Nace de un hallazgo adversarial: un modal ofrecía «Verla otra vez» y
// «Cambiar de función», y el segundo estaba cableado a cerrar y nada más — la
// segunda intención que el modal prometía era inalcanzable. El 5.º argumento
// (`cancelLabel`) es SOLO una etiqueta: renombrar el cancelar no le da conducta.
// Quien necesita dos intenciones + salida necesita tres botones de verdad.
export function showActionModal(title,body,label,cb,cancelLabel,opts){_showModal(title,body,label,cb,'confirm',cancelLabel,opts);}

export function showConflictModal(conflicts, onConfirm){
  const existing=document.getElementById('conflict-modal');if(existing) existing.remove();
  const names=conflicts.map(s=>{
    const{displayTitle}=parseProgramTitle(s._title||'');
    return`<b>${s.time} ${displayTitle.length>30?displayTitle.slice(0,28)+'…':displayTitle}</b>`;
  }).join('<br>');
  // LA CONSECUENCIA, NO SOLO EL CONFLICTO (30 ago 2026). Con un taller el modal
  // decía la verdad a medias: nombraba la ÚNICA sesión que choca con la franja
  // —correcto—, pero al aceptar se van las DOS, porque un bloque entra y sale
  // entero. El usuario decidía sin saber qué perdía. El modal de quitar del Plan
  // ya dice «Se quitarán las N sesiones»: acá se usa la MISMA frase, que además
  // ya está traducida. Y por eso el intro genérico —«Esta función choca con»— no
  // sirve para un taller: «función» es solo una proyección (regla de vocabulario).
  const _bloques=[...new Set(conflicts.filter(s=>s._title&&(typeof FILMS!=='undefined')
    &&FILMS.some(f=>f.title===s._title&&f.is_recurring)).map(s=>s._title))];
  const _avisoBloque=_bloques.map(tt=>{
    const n=FILMS.filter(f=>f.title===tt&&f.is_recurring&&f.day&&f.time).length;
    return n>1?`<div>${t('bloque_quitar_aviso',{n})}</div>`:'';
  }).join('');
  const modal=document.createElement('div');
  modal.id='conflict-modal';modal.className='conflict-modal';
  modal.innerHTML=`<div class="conflict-modal-box">
    <div class="conflict-modal-hdr">${t('conflict_plan_titulo')}</div>
    <div class="conflict-modal-body">
      <div>${_bloques.length?t('conflict_choca_intro_bloque'):t('conflict_choca_intro')}<br>${names}</div>
      ${_avisoBloque}
      <div>${t('plan_continuar_quitar')}</div>
    </div>
    <div class="conflict-modal-btns">
      <button class="conflict-modal-btn confirm" id="conflict-ok">${t('plan_quitar_continuar')}</button>
      <button class="conflict-modal-btn cancel" id="conflict-cancel">${t('search_cancelar')}</button>
    </div>
  </div>`;
  document.body.appendChild(modal);
  document.getElementById('conflict-cancel').onclick=()=>modal.remove();
  document.getElementById('conflict-ok').onclick=()=>{
    modal.remove();
    onConfirm();
  };
}

export function updateSimLabel(val){
  const d=new Date(_simFestStart().getTime()+Math.round(val/1000*_SIM_TOTAL())*60000);
  const el=document.getElementById('sim-label');
  if(el) el.textContent=d.toLocaleString(_lang==='en'?'en-US':'es',{weekday:'short',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});
}

export function _showModal(title,body,label,cb,cls,cancelLabel,opts){
  const p=document.getElementById('conflict-modal');if(p)p.remove();
  // La acción del medio solo existe si trae ETIQUETA y CONDUCTA. Exigir las dos
  // es deliberado: un botón con etiqueta y sin callback es el bug que originó
  // esto. Sin ambas, el modal queda idéntico al de dos botones de siempre.
  const _alt=opts&&opts.altLabel&&typeof opts.altCb==='function';
  const m=document.createElement('div');m.id='conflict-modal';m.className='conflict-modal';
  m.innerHTML=`<div class="conflict-modal-box">
    <div class="conflict-modal-hdr">${title}</div>
    <div class="conflict-modal-body">${body}</div>
    <div class="conflict-modal-btns">
      <button class="conflict-modal-btn ${cls}" id="cm-ok">${label}</button>
      ${_alt?`<button class="conflict-modal-btn alt" id="cm-alt">${opts.altLabel}</button>`:''}
      <button class="conflict-modal-btn cancel" id="cm-c">${cancelLabel||t('misc_cancelar')}</button>
    </div></div>`;
  document.body.appendChild(m);
  document.getElementById('cm-c').onclick=()=>m.remove();
  document.getElementById('cm-ok').onclick=()=>{m.remove();cb();};
  if(_alt) document.getElementById('cm-alt').onclick=()=>{m.remove();opts.altCb();};
  m.addEventListener('click',e=>{if(e.target===m)m.remove();});
}

export function _simFestStart(){const k=DAY_KEYS[0];const d=FESTIVAL_DATES[k];return d?new Date(d+'T09:00:00'):new Date();}

export function _simFestEnd(){return FESTIVAL_END||new Date();}
