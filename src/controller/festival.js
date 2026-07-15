// ── src/controller/festival.js ────────────────────────────────────────────────────
// p8 Step 7e — Lifecycle de splash/selector de festival + auto-resolve posters. POSTERS/CUSTOM_POSTERS vía bridge.

import { FESTIVAL_CONFIG, TMDB_API_BASE, TMDB_API_KEY, TMDB_POSTER_BASE, _DEFAULT_FEST_ID, _POSTER_CACHE_PFX, countryName } from '../config.js';
import { _renderFestivalSelectorHTML, _renderSplashRailHTML, _classifyFestival, festivalShortName, festivalTagline, festivalSeasonYear } from '../view/components.js';
import { _langDates, setPosters } from '../view/helpers.js';
import { render } from '../view/programa.js';
import { state } from '../state/state.js';

export function _togglePastFestRow(row, id){
  // Toggle colapso/expansión — siempre. Nunca carga el festival.
  const isOpen=row.classList.contains('past-open');
  if(!isOpen){
    // Colapsar cualquier otro abierto antes de expandir
    document.querySelectorAll('.fs-festival-row.past.past-open')
      .forEach(el=>el.classList.remove('past-open'));
  }
  row.classList.toggle('past-open', !isOpen);
}

export function _renderFestivalSelector(activeFestId){
  const container=document.getElementById('fs-festival-list');
  if(!container) return;
  container.innerHTML=_renderFestivalSelectorHTML(state, activeFestId);
  // Año de temporada: ancla única en el header del sheet (no repetido por fila).
  const seasonEl=document.getElementById('fs-season');
  if(seasonEl){ const y=festivalSeasonYear(); seasonEl.textContent=y?String(y):''; }
}

// _fillSplashInfo — puebla el bloque de info del selector-splash (4 líneas:
// nombre / tagline / CIUDAD / FECHAS · AÑO-si-pasado) desde el festId. El punto
// verde marca "en curso". Fuente única: FESTIVAL_CONFIG + festivalTagline.
function _fillSplashInfo(festId){
  const cfg=festId&&FESTIVAL_CONFIG[festId];
  const nameEl=document.getElementById('splash-info-name');
  const tagEl=document.getElementById('splash-info-tag');
  const cityEl=document.getElementById('splash-info-city');
  const datesEl=document.getElementById('splash-info-dates');
  if(!cfg){ [nameEl,tagEl,cityEl,datesEl].forEach(el=>{if(el)el.textContent='';}); return; }
  const cls=_classifyFestival(cfg);
  if(nameEl) nameEl.textContent=festivalShortName(cfg);
  // El slot del tagline se mantiene SIEMPRE en flujo (aunque vacío) — su min-height
  // reserva una línea para que CIUDAD/FECHA no brinquen entre festivales. Se pasa el
  // idioma para los taglines localizados (Tribeca: ES descriptor / EN nombre original).
  if(tagEl) tagEl.textContent=festivalTagline(cfg, state.snapshot()._lang);
  if(cityEl){
    // CIUDAD, PAÍS — el país se resuelve por ISO (config.countryName) y se localiza.
    const _lang=state.snapshot()._lang;
    const _pais=countryName(cfg.country,_lang);
    const _loc=cfg.city ? (_pais ? `${cfg.city}, ${_pais}` : String(cfg.city)) : '';
    cityEl.innerHTML=(cls==='ongoing'?'<span class="live-dot"></span>':'')+_loc.toUpperCase();
  }
  if(datesEl){
    // El año NO se repite en cada fecha: vive UNA vez como divisor de temporada en el
    // riel (festivalSeasonYear). La fecha solo muestra su año si DIFIERE de la temporada
    // (desambiguar un pasado de otro año). Misma regla que el título de fila del selector.
    const dates=_langDates(cfg);
    const _season=festivalSeasonYear();
    const _showYear=cfg.year && cfg.year!==_season;
    datesEl.textContent=(dates+(_showYear?' · '+cfg.year:'')).toUpperCase();
  }
}

// _selectCenteredCard — tras el scroll-snap, selecciona la card más cercana al
// centro del riel (el gesto de arrastrar = elegir). Ignora el divisor (no es card).
function _selectCenteredCard(rail){
  const mid=rail.getBoundingClientRect().left+rail.clientWidth/2;
  let best=null,bd=Infinity;
  rail.querySelectorAll('.splash-card').forEach(c=>{
    const r=c.getBoundingClientRect();
    const d=Math.abs(r.left+r.width/2-mid);
    if(d<bd){bd=d;best=c;}
  });
  const cur=rail.querySelector('.splash-card.on')?.dataset.fest;
  if(best && best.dataset.fest!==cur){
    selectSplashFest(best.dataset.name,best.dataset.meta,best.dataset.fest);
  }
}

// _renderSplashRail — renderiza el riel de afiches + puebla el info. `activeFestId`
// = el marcado .on (preselección); si es null, el info muestra el PRIMER festival
// del riel como preview (sin selección → "Entrar" sigue disabled: regla 5 jul).
// Cablea (idempotente) la selección-por-scroll GATEADA por gesto de usuario.
export function _renderSplashRail(activeFestId){
  // Encabezado de temporada: el año (festivalSeasonYear) como paraguas SOBRE el riel,
  // abarcando vigentes + anteriores. Se oculta si no hay año (defensivo).
  const seasonEl=document.getElementById('splash-season');
  if(seasonEl){ const y=festivalSeasonYear(); seasonEl.textContent=y?String(y):''; seasonEl.style.display=y?'':'none'; }
  const rail=document.getElementById('splash-rail');
  if(rail){
    rail.innerHTML=_renderSplashRailHTML(state, activeFestId);
    // Re-render con selección (p.ej. setLang): re-centrar la card .on para que
    // el centro del scroll y la selección queden alineados. selectSplashFest ya
    // centra, pero aquí la marca .on vino del HTML (activeFestId), no de un tap.
    const onCard=rail.querySelector('.splash-card.on');
    if(onCard) onCard.scrollIntoView({inline:'center',block:'nearest'});
    if(!rail.dataset.snapWired){
      rail.dataset.snapWired='1';
      // GATE DE GESTO: solo un ARRASTRE real del usuario (pointer/touch sobre el
      // riel) puede elegir por scroll. Sin esto, el re-snap programático del
      // render (0 vigentes → divisor descentra → snap mandatory dispara scroll)
      // auto-seleccionaba sin interacción, y el focus-scroll del teclado (Tab
      // entre cards) pisaba la selección explícita. El teclado elige activando la
      // card enfocada (Enter → selectSplashFest), no por scroll.
      let _tmo, _armed=false;
      const _arm=()=>{ _armed=true; };
      rail.addEventListener('pointerdown',_arm,{passive:true});
      rail.addEventListener('touchstart',_arm,{passive:true});
      rail.addEventListener('scroll',()=>{
        if(!_armed) return;
        clearTimeout(_tmo);
        _tmo=setTimeout(()=>{ _armed=false; _selectCenteredCard(rail); },90);
      },{passive:true});
    }
  }
  const previewId=activeFestId || document.querySelector('.splash-card')?.dataset.fest || null;
  _fillSplashInfo(previewId);
}

// selectSplashFest — el usuario (o la preselección) elige un festival. Marca la
// card, la centra en el riel, puebla el info y habilita "Entrar". CENTRAR vive
// aquí (única dueña de la selección): así todo caller —tap, preselección de boot,
// TEST BRIDGE, futuros deep-links— deja el centro del scroll alineado con la .on
// sin tener que recordarlo (si divergen, el próximo scroll pisaría la selección).
// name/meta se conservan en la firma (dispatcher data-action + TEST BRIDGE + tests)
// aunque el info se deriva del festId.
export function selectSplashFest(name,meta,festId){
  _splashSelectedFestId=festId||_DEFAULT_FEST_ID;
  document.querySelectorAll('.splash-card').forEach(el=>{el.classList.remove('on');el.setAttribute('aria-selected','false');});
  const card=document.querySelector('.splash-card[data-fest="'+_splashSelectedFestId+'"]');
  if(card){
    card.classList.add('on'); card.setAttribute('aria-selected','true');
    // Instant (sin behavior:'smooth'): snap mandatory pelea el smooth programático.
    card.scrollIntoView({inline:'center',block:'nearest'});
  }
  _fillSplashInfo(_splashSelectedFestId);
  const enterBtn=document.getElementById('splash-enter-btn');
  if(enterBtn) enterBtn.disabled=false;
}

export async function _autoResolveFestivalPosters(){
  if(!LB_SLUGS||!TMDB_API_KEY) return;
  const seen=new Set();
  const candidates=[];
  for(const f of FILMS){
    if(seen.has(f.title)) continue;
    if(f.type==='event'||f.is_cortos) continue;
    if(!LB_SLUGS[f.title]) continue;
    if(CUSTOM_POSTERS&&CUSTOM_POSTERS[f.title]) continue; // customPosters tienen prioridad
    seen.add(f.title);
    candidates.push(f);
  }
  if(!candidates.length) return;
  let updated=0;
  for(const film of candidates){
    const slug=LB_SLUGS[film.title];
    const cacheKey=_POSTER_CACHE_PFX+slug;
    let posterPath=null;
    try{posterPath=localStorage.getItem(cacheKey);}catch(e){}
    if(!posterPath){
      try{
        const q=encodeURIComponent(film.title_en||film.title);
        const yr=film.year?'&year='+film.year:'';
        const url=TMDB_API_BASE+'/search/movie?api_key='+TMDB_API_KEY+'&query='+q+yr+'&language=en-US';
        const resp=await fetch(url);
        if(!resp.ok) continue;
        const data=await resp.json();
        posterPath=data.results?.[0]?.poster_path||null;
        if(posterPath){try{localStorage.setItem(cacheKey,posterPath);}catch(e){}}
      }catch(e){continue;}
      await new Promise(r=>setTimeout(r,120)); // rate limit ~8 req/s
    }
    if(posterPath){
      const fullUrl=TMDB_POSTER_BASE+posterPath;
      if(POSTERS[film.title]!==fullUrl){POSTERS[film.title]=fullUrl;updated++;}
    }
  }
  if(updated>0){
    setPosters(POSTERS);
    requestAnimationFrame(()=>{try{render();}catch(e){console.warn('[render] rAF render failed',e);}});
  }
}
