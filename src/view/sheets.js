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

export function closeAuthSheet(){
  const s=document.getElementById('auth-sheet');
  if(s){s.classList.remove('open');setTimeout(()=>s.style.display='none',300);}
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
