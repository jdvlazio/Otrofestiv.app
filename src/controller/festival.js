// ── src/controller/festival.js ────────────────────────────────────────────────────
// p8 Step 7e — Lifecycle de splash/selector de festival + auto-resolve posters. POSTERS/CUSTOM_POSTERS vía bridge.

import { FESTIVAL_CONFIG, TMDB_API_BASE, TMDB_API_KEY, TMDB_POSTER_BASE, _DEFAULT_FEST_ID, _POSTER_CACHE_PFX } from '../config.js';
import { _renderFestivalSelectorHTML, _renderSplashDropdownHTML } from '../view/components.js';
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

export function selectSplashFest(name,meta,festId){
  _splashSelectedFestId=festId||_DEFAULT_FEST_ID;
  const n=document.getElementById('splash-sel-name');
  const m=document.getElementById('splash-sel-meta');
  // Quitar data-i18n: ya no es placeholder, es el nombre elegido. Sin esto,
  // un re-_applyI18nDOM (ej. cambio de idioma en el splash) lo pisaría con "Elegí uno".
  if(n){ n.textContent=name; n.removeAttribute('data-i18n'); }
  if(m) m.textContent=meta;
  document.querySelectorAll('.splash-drop-item').forEach(el=>el.classList.remove('selected'));
  const active=document.querySelector('.splash-drop-item[data-fest="'+_splashSelectedFestId+'"]');
  if(active) active.classList.add('selected');
  const dd=document.getElementById('splash-dropdown');
  const btn=document.getElementById('splash-sel-btn');
  if(dd) dd.style.display='none';
  // Quitar 'placeholder' (gris→blanco bold) y 'compact' (la barra mínima crece y
  // muestra el nombre elegido). Ambas reglas viven en el CSS del selector.
  if(btn){ btn.classList.remove('open'); btn.classList.remove('placeholder'); btn.classList.remove('compact'); }
  // Habilitar "Entrar" — ya hay un festival elegido.
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
