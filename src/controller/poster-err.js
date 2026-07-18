// ── src/controller/poster-err.js ──────────────────────────────────────────────────
// p8 Step 7e — Handlers de error de posters (onerror en HTML generado, expuestos vía bridge).

import { TMDB_API_BASE, TMDB_API_KEY, TMDB_IMG, _POSTER_CACHE_PFX } from '../config.js';
import { _buildPosterV16, _secLabel, _sectionColor, makeEventPoster, makeProgramPoster, makeSorpresaPoster } from '../view/components.js';
import { state } from '../state/state.js';

// Póster generativo para un film f (misma jerarquía que getFilmPoster: sorpresa →
// evento → programa → editorial genérico). Fuente única reusada por los fallbacks.
function _genPosterFor(f){
  if(!f) return null;
  if(f.title&&f.title.toLowerCase().includes('sorpresa')) return makeSorpresaPoster();
  if(f.type==='event') return makeEventPoster(state,f.title,f.duration,f.event_kind,f.section);
  if(f.is_cortos) return makeProgramPoster(state,f.title,f.duration,f.section);
  return _buildPosterV16({
    accent: _sectionColor(f.section||''),
    headerLabel: _secLabel(f.section||'')||'FESTIVAL',
    title: f.title,
    num: null
  });
}

export function _posterGenFallback(img, f){
  const gen=_genPosterFor(f);
  if(gen) img.src=gen; else img.style.display='none';
}

// Falla la imagen de un marco editorial (.poster-ed): reemplaza TODA la pieza por
// un póster generativo (header+cuerpo) en vez de dejar la banda con un hueco.
// Ver editorialFrame (helpers.js). data-title resuelve el film.
export function _edPosterErr(img){
  img.onerror=null;
  const host=img.closest('.poster-ed');
  const title=img.dataset.title||'';
  const f=title?FILMS.find(fi=>fi.title===title):null;
  const gen=_genPosterFor(f);
  if(host&&gen){ host.innerHTML=`<img src="${gen}" style="width:100%;height:100%;object-fit:cover;display:block" alt="">`; return; }
  const wrap=img.parentElement;
  if(wrap) wrap.style.display='none'; else img.style.display='none';
}

export function _posterErr(img){
  img.onerror=null;
  const title=img.dataset.title||'';
  const f=title?FILMS.find(fi=>fi.title===title):null;
  if(!f){img.style.display='none';return;}

  // Check localStorage cache first
  const cacheKey=_POSTER_CACHE_PFX+'err_'+title;
  const cached=localStorage.getItem(cacheKey);
  if(cached){img.src=cached;return;}

  // Show generative immediately
  _posterGenFallback(img,f);

  // Search TMDB async for real poster (only if key available — not in production bundle)
  if(!TMDB_API_KEY) return;
  const query=encodeURIComponent(f.title_en||f.title);
  const yearParam=f.year?'&year='+f.year:'';
  fetch(`${TMDB_API_BASE}/search/movie?api_key=${TMDB_API_KEY}&query=${query}${yearParam}&language=es`)
    .then(r=>r.json())
    .then(data=>{
      const path=data.results?.[0]?.poster_path;
      if(path&&img.isConnected){
        const url=TMDB_IMG+path;
        img.src=url;
        try{localStorage.setItem(cacheKey,url);}catch(e){}
      }
    })
    .catch(()=>{});
}

export function _cortoSheetPosterErr(img){
  img.onerror=null;
  const ph=document.createElement('div');
  ph.className='pel-sheet-poster-ph';
  ph.setAttribute('aria-hidden','true');
  ph.textContent='🎬';
  img.parentNode?.replaceChild(ph,img);
}
