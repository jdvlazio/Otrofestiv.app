// ══ Render helpers — parseProgramTitle, badges, stack ══
// SOURCE: index.html L4149-4198

// ── RENDER FILM LIST ──
// Utility: extraer displayTitle y progSuffix de cualquier título de programa
function parseProgramTitle(t){
  let displayTitle=t, progSuffix='';
  const f=FILMS.find(fi=>fi.title===t);
  if(f?.is_cortos){
    // "Cortos: Familia 12+" → displayTitle="Familia 12+"
    if(t.match(/^Cortos:\s*/i)){
      displayTitle=t.replace(/^Cortos:\s*/i,'');
    } else if(t.startsWith('Prog.')){
      const m=t.match(/^(Prog\.[^—–]+)\s*[—–]\s*(.+)$/);
      if(m){displayTitle=m[2].trim();progSuffix=m[1].trim();}
    } else {
      const m=t.match(/^(.+?)\s*[—–]\s*(Prog\..*)$/);
      if(m){displayTitle=m[1];progSuffix=m[2];}
    }
    if(progSuffix&&!/\d/.test(progSuffix)) progSuffix='';
  }
  return{displayTitle,progSuffix};
}


// ═══════════════════════════════════════════════════════════════
// 11 · RENDER — MI AGENDA
//      renderPrioStrip, renderFilmListHTML, renderSavedAgendaHTML
//      renderSimPanel, renderNextStrip, renderUnconfirmed
// ═══════════════════════════════════════════════════════════════
function renderPrioStrip(){
  if(!prioritized.size) return '';
  const chips=[...prioritized].map(t=>{
    const f=FILMS.find(fi=>fi.title===t);
    const p=getFilmPoster(f);
    const _safeChipT=t.replace(/'/g,"\'");
    const img=p?`<img class="prio-chip-poster" src="${p}" loading="eager" style="object-fit:cover;cursor:pointer" onclick="event.stopPropagation();openPelSheet('${_safeChipT}')" onerror="this.outerHTML='<div class=prio-chip-ph>🎬</div>'" alt="">`:`<div class="prio-chip-ph">${ICONS.star}</div>`;
    const{displayTitle,progSuffix}=parseProgramTitle(t);
    const short=displayTitle.length>16?displayTitle.slice(0,14)+'…':displayTitle;
    const allPast=!festivalEnded()&&!FILMS.some(f=>f.title===t&&!screeningPassed(f));
    return`<div class="prio-chip${allPast?' past':''}">
      ${img}
      <button class="prio-chip-rm" data-prio-title="${t.replace(/"/g,'&quot;')}" onclick="event.stopPropagation();togglePriority(this.dataset.prioTitle)" title="Quitar prioridad">${ICONS.x}</button>
      <div class="prio-chip-title">${short}${progSuffix?`<span class="prog-suffix">${progSuffix}</span>`:''}</div>
    </div>`;
  }).join('');
  return`<div class="prio-strip">
    <div class="sec-hdr">${ICONS.star} Prioridades <span class="intereses-cnt">${prioritized.size}/${PRIO_LIMIT}</span></div>
    <div class="prio-strip-row">${chips}</div>
  </div>`;
}

