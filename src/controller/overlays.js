// ── src/controller/overlays.js ────────────────────────────────────────────────
// p8 Step 7d-2 — Overlays del controller (leaf): seccion + search + lugar
// dropdowns + fuzzyMatch/normalize (utils de búsqueda). No llama a mutators/
// filters (7d-3); importa view + pipeline + sheets-controller. normTitle vía
// globalThis bridge. Roster/viewstate vía bridge.

import { FILM_CATEGORY_LABEL, FILM_CATEGORY_ORDER, SECTION_ORDER_LIST } from '../config.js';
import { ICONS, _secLabelFull, parseProgramTitle } from '../view/components.js';
import { emptyState, getFilmPoster, vcfg } from '../view/helpers.js';
import { _renderProgramaContent, lugarClose, lugarOutside, render } from '../view/programa.js';
import { t } from '../i18n/i18n.js';
import { _updateProgramaActiveFilter } from './pipeline.js';
import { countryToFlags } from './sheets-controller.js';

export function seccionOpen(){
  const btn = document.getElementById('seccion-btn');
  const r = btn.getBoundingClientRect();
  const drop = document.createElement('div');
  drop.id = 'seccion-drop';
  drop.style.cssText = [
    'position:fixed','top:'+(r.bottom+4)+'px',
    'right:'+(window.innerWidth-r.right)+'px',
    'min-width:200px','max-width:min(300px,90vw)','max-height:55vh',
    'overflow-y:auto','background:var(--surf)','border:1px solid var(--bdr)',
    'border-radius:var(--r)','box-shadow:0 8px 24px rgba(0,0,0,.55)',
    'z-index:9999','animation:lugarFadeIn .12s ease'
  ].join(';');

  const baseFilms = activeDay==='all' ? FILMS : FILMS.filter(f=>f.day===activeDay);
  const films = activeVenue!=='all' ? baseFilms.filter(f=>vcfg(f.venue).short===activeVenue) : baseFilms;

  const secMap={}, secCatMap={}, titleSet={};
  films.forEach(f=>{
    if(!titleSet[f.title]){
      titleSet[f.title]=true;
      const s=f.section||'';
      if(s){ secMap[s]=(secMap[s]||0)+1; if(f.filmCategory) secCatMap[s]=f.filmCategory; }
    }
  });

  // data-s SIEMPRE = section ES (clave de filtro/orden); solo el <span> visible se localiza.
  const _opt=(s,cnt,isActive)=>'<div class="lugar-opt'+(isActive?' on':'')+'" data-s="'+s.replace(/"/g,'&quot;')+'">'
    +'<span>'+_secLabelFull(s)+'</span><span class="lugar-cnt">'+cnt+'</span>'+(isActive?'<span class="txt-amber-ml">✓</span>':'')+'</div>';

  // La opción "todo el programa" NO lleva conteo: el total general sin contexto
  // confunde (no hay referencia). Las opciones individuales sí lo mantienen.
  let html='<div class="lugar-opt'+(activeSec==='all'?' on':'')+'" data-s="all">'
    +'<span>'+t('filter_todo_programa')+'</span>'
    +'</div>';

  const hasCategories=Object.keys(secCatMap).length>0;
  const orderedSecs=Object.keys(secMap).sort((a,b)=>{
    const ia=SECTION_ORDER_LIST.indexOf(a),ib=SECTION_ORDER_LIST.indexOf(b);
    return (ia<0?999:ia)-(ib<0?999:ib);
  });

  if(hasCategories){
    const groups={};
    orderedSecs.forEach(s=>{ const cat=secCatMap[s]||''; if(cat){if(!groups[cat])groups[cat]=[];groups[cat].push(s);} });
    const uncategorized=orderedSecs.filter(s=>!secCatMap[s]);
    FILM_CATEGORY_ORDER.forEach(cat=>{
      if(!groups[cat]) return;
      html+='<div class="sec-drop-hdr">'+(FILM_CATEGORY_LABEL[cat]||cat)+'</div>';
      groups[cat].forEach(s=>{ html+=_opt(s,secMap[s],activeSec===s); });
    });
    uncategorized.forEach(s=>{ html+=_opt(s,secMap[s],activeSec===s); });
  } else {
    orderedSecs.forEach(s=>{ html+=_opt(s,secMap[s],activeSec===s); });
  }

  drop.innerHTML=html;
  drop.addEventListener('click',e=>{
    const opt=e.target.closest('.lugar-opt');
    if(!opt) return;
    const s=opt.dataset.s;
    activeSec=(s==='all'||s===activeSec)?'all':s;
    _programaChipMatchFn=null; programaChip='all';
    seccionClose(); _updateProgramaActiveFilter();
    if(activeMNav==='mnav-cartelera') _renderProgramaContent(true); else render(); // selección sección → scroll al tope
  });
  document.body.appendChild(drop);
  btn.classList.add('on');
  setTimeout(()=>{ document.addEventListener('click',seccionOutside); },0);
}

export function seccionClose(){
  const drop = document.getElementById('seccion-drop');
  if(drop) drop.remove();
  document.removeEventListener('click', seccionOutside);
  const btn = document.getElementById('seccion-btn');
  if(btn) btn.classList.toggle('on', activeSec!=='all');
  const lbl = document.getElementById('seccion-lbl');
  if(lbl) lbl.textContent = _seccionLabel(activeSec);
}

export function seccionOutside(e){
  const drop = document.getElementById('seccion-drop');
  const btn = document.getElementById('seccion-btn');
  if(drop && !drop.contains(e.target) && e.target!==btn && !btn?.contains(e.target)){
    seccionClose();
  }
}

export function seccionToggle(){
  if(document.getElementById('lugar-drop')) lugarClose();
  if(document.getElementById('seccion-drop')) seccionClose();
  else seccionOpen();
}

export function _seccionLabel(sec){
  // Botón mode bar: solo el emoji que ya viene en el nombre de sección
  // Las secciones tienen formato "🏆 Nombre" en todos los festivales
  if(!sec||sec==='all') return t('label_seccion');
  return sec.match(/^\S+/)?.[0] || sec.slice(0,4);
}

export function searchOpen(){
  const overlay = document.getElementById('search-overlay');
  const inp = document.getElementById('search-input');
  if(!overlay) return;
  window.scrollTo({top:0, behavior:'instant'});
  // Posicionar ANTES de mostrar para evitar flash sin top
  const tb = document.querySelector('.topbar');
  const top = tb ? Math.ceil(tb.getBoundingClientRect().bottom) : 88;
  overlay.style.top = top + 'px';
  overlay.style.bottom = '0';
  overlay.style.display = 'flex';
  requestAnimationFrame(()=>{
    overlay.style.opacity = '1';
    searchPositionOverlay();
    if(inp){
      inp.focus();
      // Si hay texto previo, disparar búsqueda inmediatamente
      if(inp.value.trim()) searchQuery();
    }
  });
}

export function searchClose(){
  const overlay = document.getElementById('search-overlay');
  const inp = document.getElementById('search-input');
  const results = document.getElementById('search-results');
  if(overlay){
    overlay.style.opacity = '0';
    setTimeout(()=>{ overlay.style.display = 'none'; }, 150);
  }
  if(inp){ inp.value = ''; inp.blur(); }
  if(results) results.innerHTML = '';
}

export function searchPositionOverlay(){
  const overlay = document.getElementById('search-overlay');
  const results = document.getElementById('search-results');
  if(!overlay || overlay.style.display==='none') return;
  // Overlay: desde topbar hasta el borde inferior de la pantalla (bottom:0)
  // El teclado es UI del sistema — siempre por encima, no interfiere con el overlay
  const tb = document.querySelector('.topbar');
  const top = tb ? Math.ceil(tb.getBoundingClientRect().bottom) : 88;
  overlay.style.top = top + 'px';
  overlay.style.bottom = '0';
  overlay.style.height = 'auto';
  // Padding-bottom en resultados = altura del teclado para que nada quede oculto
  if(results){
    const vv = window.visualViewport;
    const kbH = vv ? Math.max(0, window.innerHeight - vv.height - (vv.offsetTop||0)) : 0;
    results.style.paddingBottom = (kbH + 16) + 'px';
  }
}

export function _searchAll(q){
  // Motor único: fuzzyMatch scoring en títulos + cortos individuales.
  // Reemplaza los tres motores paralelos anteriores.
  if(!q) return[];
  const ql=q.toLowerCase();
  const seen=new Set();
  const results=[];

  // 1. Programas y películas (deduplicados por título)
  const titleMap={};
  FILMS.forEach(f=>{if(!titleMap[f.title]) titleMap[f.title]=f;});
  Object.values(titleMap).forEach(f=>{
    const r1=fuzzyMatch(q,f.title);
    const r2=f.title_en?fuzzyMatch(q,f.title_en):{match:false,score:0};
    const secScore=(f.section||'').toLowerCase().includes(ql)?0.3:0;
    const cntScore=(f.country||'').toLowerCase().includes(ql)?0.2:0;
    const score=Math.max(r1.score,r2.score)+secScore+cntScore;
    if((r1.match||r2.match||secScore||cntScore)&&!seen.has(f.title)){
      seen.add(f.title);
      results.push({...f,_score:score});
    }
  });

  // 2. Cortos individuales dentro de film_list
  FILMS.filter(f=>f.is_cortos&&f.film_list?.length).forEach(prog=>{
    prog.film_list.forEach(item=>{
      const r=fuzzyMatch(q,item.title);
      if(r.match&&!seen.has(item.title)){
        seen.add(item.title);
        results.push({_isCortoItem:true,_prog:prog,_score:r.score,
          title:item.title,country:item.country,duration:item.duration,
          flags:countryToFlags(item.country||''),section:prog.section,is_cortos:false});
      }
    });
  });

  return results.sort((a,b)=>b._score-a._score).slice(0,10);
}

export function searchQuery(){
  const inp = document.getElementById('search-input');
  const results = document.getElementById('search-results');
  if(!inp || !results) return;
  const q = inp.value.trim();

  if(!q){ results.innerHTML = ''; return; }

  const matches = _searchAll(q);

  if(!matches.length){
    results.innerHTML = `<div class="search-empty">${emptyState(ICONS.search,t('search_sin_res_para')+' \u201c'+q+'\u201d')}</div>`;
    return;
  }

  const hasCortos=matches.some(f=>f._isCortoItem);
  const hasFilms=matches.some(f=>!f._isCortoItem);
  const hdr=hasFilms&&hasCortos?t('search_resultados')||'Resultados':hasCortos?t('label_cortos')||'Cortometrajes':t('planear_peliculas');
  results.innerHTML = `<div class="search-section-hdr">${hdr}</div>`
    + matches.map(f=>{
      const{displayTitle,progSuffix}=parseProgramTitle(f.title);
      const poster=getFilmPoster(f)||'';
      const _dur=f.duration!=null?String(f.duration):'';
      const meta=f._isCortoItem
        ?t('label_cortometraje')+(f._prog?' · '+parseProgramTitle(f._prog.title).displayTitle:'')
        :(_dur?_dur.replace(/\s*min\s*$/i,'')+' min':'')+(f.section?' · '+f.section.replace(/^[^ ]+ /,''):'');
      const _q=s=>String(s).replace(/"/g,'&quot;');
      const _siAttrs=f._isCortoItem
        ?`data-action="searchOpenCorto" data-title="${_q(f.title)}" data-country="${_q(f.country||'')}" data-dur="${_q(_dur)}" data-section="${_q(f.section||'')}" data-flags="${_q(f.flags||'🌍')}"`
        :`data-action="searchOpenFilm" data-title="${_q(f.title)}"`;
      return '<div class="search-item" '+_siAttrs+'>'
        +(poster?'<img class="search-item-poster" src="'+poster+'" onerror="this.remove()" alt="" loading="lazy">'
                :'<div class="search-item-poster"></div>')
        +'<div class="search-item-info">'
        +'<div class="search-item-title">'+displayTitle
        +(progSuffix?'<span class="txt-amber-sm"> '+progSuffix+'</span>':'')
        +'</div>'
        +'<div class="search-item-meta">'+meta+'</div>'
        +'</div>'
        +'<div class="search-item-arrow">›</div>'
        +'</div>';
    }).join('');
}

export function lugarOpen(){
  const btn = document.getElementById('lugar-btn');
  const r = btn.getBoundingClientRect();

  // Build dropdown
  const drop = document.createElement('div');
  drop.id = 'lugar-drop';
  drop.style.cssText = [
    'position:fixed',
    'top:'+(r.bottom+4)+'px',
    'right:'+(window.innerWidth-r.right)+'px',
    'min-width:200px',
    'max-width:min(280px,90vw)',
    'max-height:50vh',
    'overflow-y:auto',
    '-webkit-overflow-scrolling:touch',
    'overscroll-behavior:contain',
    'background:var(--surf)',
    'border:1px solid var(--bdr)',
    'border-radius:var(--r)',
    'box-shadow:0 8px 24px rgba(0,0,0,.55)',
    'z-index:9999',
    'animation:lugarFadeIn .12s ease'
  ].join(';');

  // Collect unique venues from FILMS
  // Embedded screenings[] format (Tribeca): expand all screenings, dedupe by title.
  // Flat format (FICCI/AFF): one row per screening, use f.venue directly.
  const venueMap = {};
  const _vSeen = new Set();
  (activeDay==='all'?FILMS:FILMS.filter(f=>f.day===activeDay))
    .forEach(f=>{
      if(f.screenings&&f.screenings.length){
        if(_vSeen.has(f.title)) return;
        _vSeen.add(f.title);
        const rel=activeDay==='all'?f.screenings:f.screenings.filter(s=>s.date===activeDay||s.day===activeDay);
        rel.forEach(s=>{
          const cfg=vcfg(s.venue);const short=cfg.short||s.venue;
          if(!short) return;
          if(!venueMap[short]) venueMap[short]={label:short,count:0,city:cfg.city||''};
          venueMap[short].count++;
        });
      } else {
        const cfg=vcfg(f.venue);const short=cfg.short||f.venue;
        if(!short) return;
        if(!venueMap[short]) venueMap[short]={label:short,count:0,city:cfg.city||''};
        venueMap[short].count++;
      }
    });

  const venues = Object.values(venueMap).sort((a,b)=>b.count-a.count);
  const total = venues.reduce((s,v)=>s+v.count,0);

  // Render options
  const opts = [{label:t('filter_todos_lugares'), count:total, short:'all'}, ...venues.map(v=>({...v,short:v.label}))];
  drop.innerHTML = opts.map(v=>{
    const isActive = (v.short==='all' && activeVenue==='all') || (activeVenue===v.short);
    return '<div class="lugar-opt'+(isActive?' on':'')+'" data-v="'+v.short+'">'
      +(v.short!=='all'?'<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z"/></svg>':'')
      +'<span>'+v.label+'</span>'
      // "todos los lugares" sin conteo (total general sin referencia confunde);
      // los venues individuales sí muestran su número.
      +(v.short!=='all'?'<span class="lugar-cnt">'+v.count+'</span>':'')
      +'</div>';
  }).join('');

  drop.addEventListener('click', e=>{
    const opt = e.target.closest('.lugar-opt');
    if(!opt) return;
    const v = opt.dataset.v;
    activeVenue = (v==='all'||v===activeVenue)?'all':v;
    lugarClose();
    _updateProgramaActiveFilter();
    if(activeMNav==='mnav-cartelera') _renderProgramaContent(true); else render(); // selección lugar → scroll al tope
  });

  document.body.appendChild(drop);
  btn.classList.add('on');

  // Close on outside click
  setTimeout(()=>{
    document.addEventListener('click', lugarOutside);
  }, 0);
  // Close on scroll — dropdown is fixed, button moves with sticky bar
  window.addEventListener('scroll', lugarClose, {passive:true, once:true});
}

export function lugarToggle(){
  if(document.getElementById('seccion-drop')) seccionClose();
  if(document.getElementById('lugar-drop')) lugarClose();
  else lugarOpen();
}

export function fuzzyMatch(query,title){
  const q=normalize(query),t=normalize(title);
  if(t.includes(q)) return{match:true,score:100+q.length};
  let qi=0;for(let i=0;i<t.length&&qi<q.length;i++) if(t[i]===q[qi]) qi++;
  if(qi===q.length) return{match:true,score:qi};
  return{match:false,score:0};
}

export function normalize(str){
  return str.normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();
}
