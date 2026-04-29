// ══ Cartelera — renderVbar, renderSbar, rating stars ══
// SOURCE: index.html L6443-6568

/* ── RENDER — CARTELERA: filtros, grid horario, grid película ────────── */
function renderVbar(){
  const panel=document.getElementById('vdr-panel');
  const trigBtn=document.getElementById('vdr-btn');
  const lbl=document.getElementById('vdr-label');
  if(!panel) return;
  panel.innerHTML='';
  const dayFilms=programaSubMode==='explorar'?FILMS:FILMS.filter(f=>f.day===activeDay);
  const vs=[...new Set(dayFilms.map(f=>vcfg(f.venue).short))];
  const mkOpt=(html,isOn,cb)=>{
    const b=document.createElement('button');
    b.className='fdr-opt'+(isOn?' on':'');
    b.innerHTML=html;
    b.onclick=e=>{e.stopPropagation();cb();};
    panel.appendChild(b);
  };
  mkOpt(`Todos los lugares <span class="fdr-cnt">${dayFilms.length}</span>`,activeVenue==='all',()=>{activeVenue='all';selectedIdx=null;setHint(null);closeDropdowns();_updateProgramaActiveFilter();if(programaSubMode==='explorar')_renderProgramaContent();else render();});
  vs.forEach(vk=>{
    const cfg=Object.values(VENUES).find(c=>c.short===vk)||VENUES['C. Convenciones'];
    const cnt=dayFilms.filter(f=>vcfg(f.venue).short===vk).length;
    mkOpt(`${ICONS.pin} ${vk} <span class="fdr-cnt">${cnt}</span>`,activeVenue===vk,()=>{activeVenue=activeVenue===vk?'all':vk;selectedIdx=null;setHint(null);closeDropdowns();_updateProgramaActiveFilter();if(programaSubMode==='explorar')_renderProgramaContent();else render();});
  });
  if(lbl) lbl.textContent=activeVenue==='all'?'Lugar':activeVenue;
  if(trigBtn) trigBtn.classList.toggle('active',activeVenue!=='all');
}
function renderSbar(){
  const panel=document.getElementById('sdr-panel');
  const trigBtn=document.getElementById('sdr-btn');
  const lbl=document.getElementById('sdr-label');
  if(!panel) return;
  panel.innerHTML='';
  // En Explorar: mostrar todas las secciones. En Hoy/Mañana: filtrar por día
  const isExplorar=programaSubMode==='explorar';
  let dayF=isExplorar?FILMS:FILMS.filter(f=>f.day===activeDay);
  if(activeVenue!=='all') dayF=dayF.filter(f=>vcfg(f.venue).short===activeVenue);
  const secs=[...new Set(dayF.map(f=>f.section))].sort();
  // Siempre mostrar 'Categoría' cuando el filtro viene de chip
  if(lbl) lbl.textContent=activeSec==='all'||activeSec==='_chip_'?'Categoría':(activeSec.length>18?activeSec.slice(0,16)+'…':activeSec);
  if(trigBtn) trigBtn.classList.toggle('active',activeSec!=='all'&&activeSec!=='_chip_');
  const mkOpt=(html,isOn,cb)=>{
    const b=document.createElement('button');
    b.className='fdr-opt'+(isOn?' on':'');
    b.innerHTML=html;
    b.onclick=e=>{e.stopPropagation();cb();};
    panel.appendChild(b);
  };
  mkOpt(`Todas las categorías <span class="fdr-cnt">${dayF.length}</span>`,activeSec==='all',()=>{activeSec='all';selectedIdx=null;setHint(null);closeDropdowns();render();});
  secs.forEach(sec=>{
    const cnt=dayF.filter(f=>f.section===sec).length;
    mkOpt(`${sec} <span class="fdr-cnt">${cnt}</span>`,activeSec===sec,()=>{activeSec=activeSec===sec?'all':sec;selectedIdx=null;setHint(null);closeDropdowns();render();});
  });
  // label y active ya seteados al principio
}
function setHint(film){
  const el=document.getElementById('hint');
  if(!film){el.textContent='';el.classList.remove('active');el.style.padding='0 18px';return;}
  const end=toMin(film.time)+parseDur(film.duration)+10;
  // Info de conflicto: cuántas otras funciones solapan en este horario
  const conflictCount=vis?vis.filter((f2,j)=>{
    if(j===selectedIdx) return false;
    const s2=toMin(f2.time),e2=s2+parseDur(f2.duration);
    const s=toMin(film.time)-10,e=toMin(film.time)+parseDur(film.duration)+10;
    return s2>s&&s2<e;
  }).length:0;
  const conflictInfo=conflictCount>0?` · ${conflictCount} función${conflictCount>1?'es':''}  solapan`:'';
  el.innerHTML=`${ICONS.clock} ${minToStr(toMin(film.time))} – ${minToStr(end)}${conflictInfo} · Toca de nuevo para cerrar`;
  el.style.padding='8px 18px';
  el.classList.add('active');
}

function applyStates(vis){
  document.querySelectorAll('.card').forEach((card,i)=>{
    card.classList.remove('selected','conflict');
    if(selectedIdx===null) return;
    if(i===selectedIdx) card.classList.add('selected');
    else{
      const fStart=toMin(vis[i].time),sel=vis[selectedIdx];
      const s=toMin(sel.time)-10,e=toMin(sel.time)+parseDur(sel.duration)+10;
      if(fStart>s&&fStart<e) card.classList.add('conflict');
    }
  });
}

// ── Orden oficial FICCI 65 (Letterboxd) ── largometrajes primero, cortos al final
const SECTION_ORDER_LF=[
  '🇨🇴 Comp. Colombia',
  '🌎 Comp. Iberoamérica',
  '⏳ (s)paces of Time',
  '🌍 Internacional',
  '✊ Cine Afro',
  '🪶 Cine Indígena',
  '🏆 Comp. Cine en los Barrios',
  '🌙 Medianoche',
  '🇪🇸 Muestra España',
  '🇨🇭 Muestra Suiza',
  '🇦🇷 Muestra Argentina',
  '📽️ Retrospectiva Ruth Beckermann',
  '📽️ Retrospectiva FICCI Años 60',
  '📽️ Retrospectiva Clásicos – Ópera Prima',
  '🎖️ Tributo Ben Rivers',
  '🇧🇷 Casa Brasil',
  '⭐ Proyecciones Especiales',
];

function updateHorarioPrioBtn(title){
  const inPrio=prioritized.has(title);
  document.querySelectorAll('.horario-prio-btn[data-title="'+CSS.escape(title)+'"]').forEach(btn=>{
    btn.className='card-strip-btn horario-prio-btn'+(inPrio?' prio-on':'');
    btn.innerHTML=(inPrio?ICONS.starFill:ICONS.star)+' Prio.';
  });
}
/* ── RATING SHEET ── */
let _ratingTitle='';

function starSVG(fill){
  // fill: 'none' | 'half' | 'full'
  const id='rs'+Math.random().toString(36).slice(2,6);
  const grad=fill==='half'
    ?`<defs><linearGradient id="${id}"><stop offset="50%" stop-color="var(--amber)"/><stop offset="50%" stop-color="transparent"/></linearGradient></defs>`
    :'';
  const fillVal=fill==='none'?'none':fill==='full'?'var(--amber)':`url(#${id})`;
  const stroke=fill==='none'?'var(--gray)':'var(--amber)';
  return`<svg width="28" height="28" viewBox="0 0 24 24" style="display:block;flex-shrink:0">${grad}<polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="${fillVal}" stroke="${stroke}" stroke-width="1.5" stroke-linejoin="round"/></svg>`;
}

