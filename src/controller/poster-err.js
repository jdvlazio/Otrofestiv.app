// ── src/controller/poster-err.js ──────────────────────────────────────────────────
// p8 Step 7e — Handlers de error de posters (onerror en HTML generado, expuestos vía bridge).

import { TMDB_API_BASE, TMDB_API_KEY, TMDB_IMG, _POSTER_CACHE_PFX } from '../config.js';
import { _buildPosterV16, _secLabel, _sectionColor, makeEventPoster, makeProgramPoster, makeSorpresaPoster } from '../view/components.js';
import { state } from '../state/state.js';

export function _posterGenFallback(img, f){
  if(!f){ img.style.display='none'; return; }
  let gen;
  if(f.title&&f.title.toLowerCase().includes('sorpresa')) gen=makeSorpresaPoster();
  else if(f.type==='event') gen=makeEventPoster(state,f.title,f.duration,f.event_kind);
  else if(f.is_cortos) gen=makeProgramPoster(state,f.title,f.duration,f.section);
  else gen=_buildPosterV16({
    accent: _sectionColor(f.section||''),
    headerLabel: _secLabel(f.section||'')||'FESTIVAL',
    title: f.title,
    num: null
  });
  if(gen) img.src=gen; else img.style.display='none';
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
  ph.textContent='🎬';
  img.parentNode?.replaceChild(ph,img);
}
