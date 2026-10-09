// ── src/view/recap.js — «Tu festival» (#1055, F2) ─────────────────────────────
// La tarjeta de recorrido de Mi Plan terminado y las piezas de texto que la
// historia 9:16 reutiliza. Un solo dueño de CÓMO se dice el recorrido: la
// pantalla y la imagen no pueden contar lo mismo con palabras distintas.
//
// Regla de oro (festivalRecap): lo que viene null no se dice. Cada parte del
// recorrido se omite sola; si no queda ninguna, no hay línea.

import { t } from '../i18n/i18n.js';
import { starsText, getFilmPoster, getCortoItemPoster } from './helpers.js';
import { parseProgramTitle } from './components.js';

// recapTitular(rec) → {verbo, n, unidad}. «obras» si todo lo visto se califica;
// «actividades» si hubo eventos (talleres, charlas): el paraguas correcto.
export function recapTitular(rec){
  const n=rec.actividades;
  const unidad=rec.eventos
    ? (n===1?t('misc_actividad'):t('misc_actividades'))
    : (n===1?t('recap_u_obra'):t('recap_u_obras'));
  return {verbo:t('plan_viste_n'), n, unidad};
}

// recorridoPartes(rec) → [{n, unidad}] en orden fijo: días · sedes|ciudades ·
// horas · países. Multiciudad (≥2 ciudades): se dicen ciudades, no sedes.
export function recorridoPartes(rec){
  const p=[];
  const u=(n,uno,varios)=>({n, unidad:t(n===1?uno:varios)});
  if(rec.dias) p.push(u(rec.dias,'recap_u_dia','recap_u_dias'));
  if(rec.ciudades&&rec.ciudades>1) p.push(u(rec.ciudades,'recap_u_ciudad','recap_u_ciudades'));
  else if(rec.sedes) p.push(u(rec.sedes,'recap_u_sede','recap_u_sedes'));
  if(rec.horas) p.push({n:rec.horas, unidad:t('recap_u_horas')});
  if(rec.paises) p.push(u(rec.paises,'recap_u_pais','recap_u_paises'));
  return p;
}

// recapPoster(o) — el afiche de una obra del recap (obra suelta o corto de un programa).
export function recapPoster(o){
  return o.film&&o.film._prog ? getCortoItemPoster(o.film) : getFilmPoster(o.film);
}

// renderRecapExtraHTML(rec) — lo que va debajo del titular en Mi Plan terminado:
// la línea de recorrido y «Tus mejores» (hasta 3, con estrellas).
export function renderRecapExtraHTML(rec){
  const partes=recorridoPartes(rec);
  const linea=partes.length?`<div class="recap-recorrido">${partes.map(p=>`<span><b>${p.n}</b> ${p.unidad}</span>`).join('<span class="recap-sep">·</span>')}</div>`:'';
  const top=rec.top.length?`<div class="recap-mejores">
      <div class="recap-eyebrow">${t('recap_tus_mejores')}</div>
      <div class="recap-top">${rec.top.map((o,i)=>{
        const src=recapPoster(o)||'';
        const {displayTitle:dt}=parseProgramTitle(o.title);
        const safe=dt.replace(/</g,'&lt;');
        return `<div class="recap-top-item">
          <span class="recap-top-n">${i+1}</span>
          ${src?`<img class="recap-top-poster" src="${src}" alt="" loading="lazy" onerror="this.remove()">`:'<span class="recap-top-poster"></span>'}
          <span class="recap-top-txt"><span class="recap-top-title">${safe}</span><span class="recap-top-stars">${starsText(o.rating)}</span></span>
        </div>`;}).join('')}</div>
    </div>`:'';
  return linea+top;
}
