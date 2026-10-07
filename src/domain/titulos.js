// ── src/domain/titulos.js — títulos anteriores de una obra (7 oct 2026) ────────
//
// Todo lo que el usuario guarda de una obra va atado a su TÍTULO: Interés, Plan,
// «la vi», prioridad, calificación, retrasos. Cuando el festival renombra una
// obra («Tránsito» → «Tránsitos», Villa del Cine, PR #1021) lo guardado quedaba
// bajo un título que ya no existe — y publicarCatalogo lo BORRA al filtrar contra
// los títulos vigentes. Sin aviso, sin error.
//
// El dato lo pone Onboarding en el JSON del festival: `titulos_anteriores` en la
// obra, con los títulos con que se publicó antes. La app migra en silencio al
// cargar (decisión de Juan: «sin avisar, es lo justo»).
//
// Puro: sin DOM ni state. Lo usan publicarCatalogo (antes del filtro) y
// _applyCloudRow (la nube puede traer la copia vieja). Idempotente: migrar dos
// veces da lo mismo, así que cada dispositivo puede hacerlo por su cuenta.

// renamesDe(films, norm) — Map título viejo → título vigente.
//   · Un título viejo que SIGUE vigente no se migra (la obra nueva no es esa).
//   · Si dos obras reclaman el mismo título viejo (una obra que se partió en
//     dos), gana la PRIMERA del catálogo: no hay forma de saber cuál era.
export function renamesDe(films, norm = (t) => t) {
  const vigentes = new Set((films || []).map((f) => f.title));
  const ren = new Map();
  (films || []).forEach((f) => {
    (f.titulos_anteriores || []).forEach((viejo) => {
      const v = norm(viejo);
      if (!v || vigentes.has(v) || ren.has(v)) return;
      ren.set(v, f.title);
    });
  });
  return ren;
}

const _set = (s, ren) => {
  if (!s || ![...s].some((t) => ren.has(t))) return null;
  return new Set([...s].map((t) => ren.get(t) || t));
};

const _llaves = (o, ren, llave) => {
  if (!o) return null;
  let cambio = false;
  const out = {};
  // Primero lo que ya está bajo el título vigente: si hay los dos, manda el nuevo.
  Object.entries(o).forEach(([k, v]) => { if (!ren.has(llave(k)[0])) out[k] = v; });
  Object.entries(o).forEach(([k, v]) => {
    const [t, resto] = llave(k);
    if (!ren.has(t)) return;
    cambio = true;
    const nk = ren.get(t) + resto;
    if (!(nk in out)) out[nk] = v;
  });
  return cambio ? out : null;
};
const _porTitulo = (k) => [k, ''];
const _porFuncion = (k) => { const i = k.indexOf('|'); return i < 0 ? [k, ''] : [k.slice(0, i), k.slice(i)]; };

const _entradas = (arr, ren) => {
  if (!arr || !arr.some((e) => e && ren.has(e._title || e.title))) return null;
  return arr.map((e) => {
    const t = e && (e._title || e.title);
    if (!ren.has(t)) return e;
    const n = ren.get(t);
    return { ...e, ...(e._title ? { _title: n } : {}), ...(e.title ? { title: n } : {}) };
  });
};

// migrarEstado(st, ren) — SOLO las claves que cambian, listo para batchUpdate.
// Vacío = nada que migrar (el caso de siempre).
export function migrarEstado(st, ren) {
  const u = {};
  if (!ren || !ren.size || !st) return u;
  ['watchlist', 'watched', 'notWatched', 'prioritized'].forEach((k) => {
    const v = _set(st[k], ren); if (v) u[k] = v;
  });
  const r = _llaves(st.filmRatings, ren, _porTitulo); if (r) u.filmRatings = r;
  ['filmDelays', 'filmDelaysHistory'].forEach((k) => {
    const v = _llaves(st[k], ren, _porFuncion); if (v) u[k] = v;
  });
  if (st.savedAgenda && st.savedAgenda.schedule) {
    const s = _entradas(st.savedAgenda.schedule, ren);
    if (s) u.savedAgenda = { ...st.savedAgenda, schedule: s };
  }
  const l = _entradas(st.lastRemovedSlots, ren); if (l) u.lastRemovedSlots = l;
  return u;
}
