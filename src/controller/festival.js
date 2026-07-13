// ── src/controller/festival.js ────────────────────────────────────────────────────
// p8 Step 7e — Lifecycle de splash/selector de festival + auto-resolve posters. POSTERS/CUSTOM_POSTERS vía bridge.

import { FESTIVAL_CONFIG, TMDB_API_BASE, TMDB_API_KEY, TMDB_POSTER_BASE, _DEFAULT_FEST_ID, _POSTER_CACHE_PFX } from '../config.js';
import { _renderFestivalSelectorHTML, _renderSplashDropdownHTML, _renderSplashRailHTML, _classifyFestival, festivalShortName, festivalTagline } from '../view/components.js';
import { _langDates, setPosters } from '../view/helpers.js';
import { render } from '../view/programa.js';
import { state } from '../state/state.js';

export function toggleSplashDropdown(){
  const dd=document.getElementById('splash-dropdown');
  const btn=document.getElementById('splash-sel-btn');
  if(!dd||!btn) return;
  const open=dd.style.display==='none';
  dd.style.display=open?'block':'none';
  btn.classList.toggle('open',open);
  if(open){
    // Acotar la altura al espacio disponible bajo el botón → scroll interno.
    // Sin esto, los nombres oficiales + el expand de "anteriores" hacen crecer el
    // dropdown más allá del viewport (el splash es position:fixed, no scrollea) y
    // los items de abajo quedan inalcanzables. La barra-padre no cambia de top al
    // expandir un item, así que basta calcular una vez al abrir.
    const top=dd.getBoundingClientRect().top;
    dd.style.maxHeight=Math.max(160, window.innerHeight - top - 16)+'px';
  }
}

export function _togglePastFest(item){
  // Solo el chevron llega acá → toggle colapso/expansión del item pasado.
  // El tap en el título/cuerpo dispara selectSplashFest (no esto).
  if(!item) return;
  item.classList.toggle('past-open');
}

export function _renderSplashDropdown(activeFestId){
  const dd=document.getElementById('splash-dropdown');
  if(!dd) return;
  dd.innerHTML=_renderSplashDropdownHTML(state, activeFestId);
  // Update selected button meta with language-aware dates
  const _activeCfg=FESTIVAL_CONFIG[activeFestId];
  const _selMeta=document.getElementById('splash-sel-meta');
  const _selName=document.getElementById('splash-sel-name');
  if(_activeCfg && _selMeta){
    _selMeta.textContent=`${_activeCfg.city} · ${_langDates(_activeCfg)} ${_activeCfg.year||''}`.trim();
  }
  if(_activeCfg && _selName) _selName.textContent=_activeCfg.name;
}

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
  const html=_renderFestivalSelectorHTML(state, activeFestId);
  container.innerHTML=html;
  container.innerHTML=html;
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
  if(tagEl){ const t=festivalTagline(cfg); tagEl.textContent=t; tagEl.style.display=t?'':'none'; }
  if(cityEl) cityEl.innerHTML=(cls==='ongoing'?'<span class="live-dot"></span>':'')+String(cfg.city||'').toUpperCase();
  if(datesEl){
    const dates=_langDates(cfg);
    datesEl.textContent=(dates+(cls==='past'&&cfg.year?' · '+cfg.year:'')).toUpperCase();
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
// Cablea (idempotente) el scroll-snap: al soltar el riel, la card centrada se elige.
export function _renderSplashRail(activeFestId){
  const rail=document.getElementById('splash-rail');
  if(rail){
    rail.innerHTML=_renderSplashRailHTML(state, activeFestId);
    if(!rail.dataset.snapWired){
      rail.dataset.snapWired='1';
      let _tmo;
      rail.addEventListener('scroll',()=>{
        clearTimeout(_tmo);
        _tmo=setTimeout(()=>_selectCenteredCard(rail),90);
      },{passive:true});
    }
  }
  const previewId=activeFestId || document.querySelector('.splash-card')?.dataset.fest || null;
  _fillSplashInfo(previewId);
}

// selectSplashFest — el usuario (o la preselección) elige un festival. Marca la
// card, puebla el info y habilita "Entrar". name/meta se conservan en la firma
// (dispatcher data-action + TEST BRIDGE + tests) aunque el info se deriva del festId.
export function selectSplashFest(name,meta,festId){
  _splashSelectedFestId=festId||_DEFAULT_FEST_ID;
  document.querySelectorAll('.splash-card').forEach(el=>{el.classList.remove('on');el.setAttribute('aria-selected','false');});
  const card=document.querySelector('.splash-card[data-fest="'+_splashSelectedFestId+'"]');
  if(card){ card.classList.add('on'); card.setAttribute('aria-selected','true'); }
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
