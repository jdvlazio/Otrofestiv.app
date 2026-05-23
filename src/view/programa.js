// ── src/view/programa.js — Fase 8 Step 6c (CABLEADO) ────────────────────────
//
// ESTADO: importado por src/main.js (Step 6c). Builders del programa view:
//   banner de avisos (notices) + chips de filtro. Scope STRICT (D-6C-2): solo
//   los builders foundational. El programa RENDER pesado (renderProgramaList,
//   renderPeliculaView, _renderProgramaContent) es controller-coupled → Wave 7.
//
// DEPS: state(state.js), i18n(t), config(NOTICES). festival/view-state via STATE
//   BRIDGE (bare-global): _activeFestId, _DEFAULT_FEST_ID, _dismissedNotices,
//   programaChip, _programaChipMatchFn (bridgeados en main.js TEST BRIDGE, D-6C-1).
//   Los handlers _dismissNotice/setProgramaChip (data-action) viven en main.js.

import { state } from "../state/state.js";
import { t } from "../i18n/i18n.js";
import { NOTICES } from "../config.js";

export function _computeProgramaChips(state){
  const {FILMS} = state.snapshot();
  const titleSet={};
  FILMS.forEach(f=>{if(!titleSet[f.title])titleSet[f.title]=f;});
  const allFilms=Object.values(titleSet);
  const secMap={};
  allFilms.forEach(f=>{const s=f.section||'';if(s) secMap[s]=(secMap[s]||0)+1;});
  const secChips=Object.entries(secMap)
    .sort((a,b)=>b[1]-a[1])
    .map(([sec,cnt])=>({
      id:'sec_'+sec.replace(/[^a-zA-Z0-9]/g,'_').slice(0,30),
      label:sec, match:s=>s===sec, count:cnt
    }));
  return [{id:'all',label:'Todo',match:null,count:allFilms.length},...secChips];
}

export function renderProgramaChipsHTML(state){
  const chips=_computeProgramaChips(state);
  return chips.map(chip=>{
    const isOn=chip.id==='all'?programaChip==='all':
      (_programaChipMatchFn&&chip.match&&_programaChipMatchFn.toString()===chip.match.toString());
    const label=chip.id==='all'?chip.label:`${chip.label}<span class="ml-1 count-badge cb-neutral">${chip.count}</span>`;
    return`<div class="pchip${isOn?' on':''}" data-chip="${chip.id}"
         data-action="setProgramaChip" data-chip="${chip.id}">${label}</div>`;
  }).join('');
}

export function getActiveNotices(){
  const festId=(_activeFestId||_DEFAULT_FEST_ID);
  const today=new Date(); today.setHours(0,0,0,0);
  return NOTICES.filter(n=>{
    if(n.festival!==festId) return false;
    if(_dismissedNotices.has(n.title)) return false;
    // Banner desaparece al día siguiente de la función cancelada
    if(n.date){
      const funcDate=new Date(n.date+'T00:00:00');
      funcDate.setDate(funcDate.getDate()+1); // día siguiente
      if(today>=funcDate) return false;
    }
    return true;
  });
}

export function renderNoticesBannerHTML(state){
  const active=getActiveNotices();
  if(!active.length) return '';
  return active.map(n=>{
    const label=n.type==='cancelled'?t('notice_cancelada'):t('notice_reprogramada');
    const msgCancelled=`<span>${t('plan_fecha_pendiente')}</span>`;
    const msgRescheduled=n.newDay&&n.newTime?`${t('notice_nueva_funcion')} <span class="txt-white60">${n.newDay} · ${n.newTime}${n.newVenue?' · '+n.newVenue:''}</span>`:'';
    const msg=n.type==='cancelled'?msgCancelled:msgRescheduled;
    const safeTitle=n.title.length>32?n.title.slice(0,30)+'…':n.title;
    return`<div class="notice-banner">
      <div class="notice-banner-dot"></div>
      <div class="notice-banner-body">
        <div class="notice-banner-label">AVISO DEL FESTIVAL</div>
        <div class="notice-banner-text"><b class="txt-white60-semi">${safeTitle}</b> · <span>${label.toLowerCase()}</span>. ${msg}</div>
      </div>
      <button class="notice-banner-close" data-action="_dismissNotice" data-title="${n.title.replace(/"/g,'&quot;')}">✕</button>
    </div>`;
  }).join('');
}

export function renderNoticesBanner(){
  const el=document.getElementById('notices-banner');
  if(!el) return;
  el.innerHTML=renderNoticesBannerHTML(state);
}
