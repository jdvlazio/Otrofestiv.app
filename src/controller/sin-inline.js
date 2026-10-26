// sin-inline.js — SIN HANDLERS EN EL HTML (CSP, 26 oct 2026).
// Los on*="…" del markup obligan a la CSP a aceptar 'unsafe-inline', que es
// justo lo que permite ejecutar código inyectado. Se reemplazan por atributos
// de datos que estos listeners delegados leen:
//   data-enter="accion"  Enter en el campo → ACTION_REGISTRY[accion] (main.js) (como el
//                        botón de al lado; el de la clave de revisión llamaba a
//                        un submitReviewKey global que no existía y Enter no hacía nada)
//   data-err="…"         la imagen que no carga: ocultar · quitar · poster ·
//                        corto · ed (los fallbacks de poster-err.js)
//   data-load="mostrar"  la imagen que carga se muestra (opacity 1)
//   data-buscar          el buscador: input + keyup + keydown diferido, lo mismo
//                        que hacían sus tres handlers
//
// UNA VEZ por imagen: el handler viejo hacía `img.onerror=null`; acá se borra
// el atributo antes de reaccionar, así un fallback que también falla no entra
// en bucle. Y la imagen que falló o cargó ANTES de entrar al documento (armada
// en un contenedor suelto) no avisa a `document`: un MutationObserver la
// revisa al insertarse (complete + naturalWidth).
import { _posterErr, _cortoSheetPosterErr, _edPosterErr } from './poster-err.js';

const AL_FALLAR = {
  ocultar: img => { img.style.visibility = 'hidden'; },
  quitar:  img => { img.remove(); },
  poster:  _posterErr,
  corto:   _cortoSheetPosterErr,
  ed:      _edPosterErr,
};
const AL_CARGAR = { mostrar: img => { img.style.opacity = '1'; } };

function _fallo(img) {
  const f = AL_FALLAR[img.dataset.err];
  if (!f) return;
  delete img.dataset.err; delete img.dataset.load;
  f(img);
}
function _carga(img) {
  const f = AL_CARGAR[img.dataset.load];
  if (!f) return;
  delete img.dataset.load;
  f(img);
}
// La que ya terminó antes de estar en el documento: decidir por su estado.
function _revisar(img) {
  if (!img.complete || !img.getAttribute('src')) return;
  if (img.naturalWidth === 0) { if (img.dataset.err) _fallo(img); }
  else if (img.dataset.load) _carga(img);
}

export function instalarSinInline(registry, buscar) {
  document.addEventListener('keydown', function(e) {
    const t = e.target;
    if (t && t.dataset) {
      if (e.key === 'Enter' && t.dataset.enter) { const h = registry[t.dataset.enter]; if (h) h(t, e); }
      if (t.dataset.buscar) setTimeout(buscar, 0);
    }
  });
  ['input', 'keyup'].forEach(ev => document.addEventListener(ev, function(e) {
    if (e.target && e.target.dataset && e.target.dataset.buscar) buscar();
  }));
  // error y load no burbujean: fase de captura
  document.addEventListener('error', function(e) {
    const t = e.target;
    if (t && t.dataset && t.dataset.err) _fallo(t);
  }, true);
  document.addEventListener('load', function(e) {
    const t = e.target;
    if (t && t.dataset && t.dataset.load) _carga(t);
  }, true);
  new MutationObserver(muts => {
    for (const m of muts) for (const n of m.addedNodes) {
      if (n.nodeType !== 1) continue;
      if (n.tagName === 'IMG') _revisar(n);
      else if (n.querySelectorAll) n.querySelectorAll('img[data-err],img[data-load]').forEach(_revisar);
    }
  }).observe(document.documentElement, { childList: true, subtree: true });
}
