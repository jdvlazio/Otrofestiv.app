// sin-inline.js — SIN HANDLERS EN EL HTML (CSP, 26 oct 2026).
// Los on*="…" del markup obligan a la CSP a aceptar 'unsafe-inline', que es
// justo lo que permite ejecutar código inyectado. Se reemplazan por atributos
// de datos que estos listeners delegados leen:
//   data-enter="accion"  Enter en el campo → ACTION_REGISTRY[accion] (main.js) (como el
//                        botón de al lado; el de la clave de revisión llamaba a
//                        un submitReviewKey global que no existía y Enter no hacía nada)
//   data-err="ocultar"   la imagen que no carga se oculta (fase de captura:
//                        el evento error no burbujea)
//   data-buscar          el buscador: input + keyup + keydown diferido, lo mismo
//                        que hacían sus tres handlers

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
  document.addEventListener('error', function(e) {
    const t = e.target;
    if (t && t.dataset && t.dataset.err === 'ocultar') t.style.visibility = 'hidden';
  }, true);
}
