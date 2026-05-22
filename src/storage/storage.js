// ── src/storage/storage.js — Fase 8 (PREP, NO CABLEADO) ───────────────────────────────
//
// ⚠ ESTADO: módulo de preparación. NO importado por index.html. Cero impacto
//   runtime/deploy/SW. Wiring real post-Tribeca.
// ⚠ FUENTE DE VERDAD: index.html hasta el wiring. Copia fiel del bloque
//   contiguo marcado. Si cambia en index.html antes del wiring, re-generar.
//
// DEPS EXTERNAS (wiring): festival-state FESTIVAL_STORAGE_KEY (keys scoped por
//   festival). state es Wave 3 — aquí queda ambient.

// ── STORAGE ADAPTER START ────────────────────────────────────────────
// storage — encapsula localStorage I/O para 9 user-state items + 3 global keys.
// User-state methods usan FESTIVAL_STORAGE_KEY como prefix. Global keys NO.
// Cada método maneja serialización por tipo (Set ↔ array, object/array identity).
// Operaciones silent-fail en parse/quota errors (default en reads, no-op en writes) —
//   misma semántica que los try/catch silenciados de los callsites originales.
// NO encapsula: cloud sync (sigue via _cloudSave() en callers), TMDB poster cache,
//   otrofestiv_hint_cambiar, otrofestiv_display_name (Supabase), orf_build (SW staged rollout).
// Posición: este bloque se define AL INICIO de script 3 (antes de _I18N, _lang,
//   FESTIVAL_CONFIG y FESTIVAL_STORAGE_KEY) porque init code de _lang
//   (línea ~3433+) y bootstrap de festival (línea ~4170+) usan storage.getLang()
//   y storage.getActiveFestId() respectivamente. User-state methods cierran sobre
//   FESTIVAL_STORAGE_KEY vía closure — late binding, así que pueden definirse
//   antes de que FESTIVAL_STORAGE_KEY exista.
// Excepción única conocida: línea ~2456 (splash lang preview en script 2, anterior
//   a script 3) — esa línea SÍ usa localStorage.getItem inline porque storage
//   no existe cuando ese script corre. Documentada en spec.md como exception.
// Validate.py check [storage-encapsulation]: cualquier localStorage.(get|set)Item
//   FUERA de los marcadores START/END es un error. Si necesitás añadir un nuevo
//   user-state item, extendé el adapter — NO inline.
export const storage = {
  // ── User state (festival-prefixed) ──
  getWatchlist() { try { const r=localStorage.getItem(FESTIVAL_STORAGE_KEY+'wl'); return r?new Set(JSON.parse(r)):new Set(); } catch(e) { return new Set(); } },
  setWatchlist(s) { try { localStorage.setItem(FESTIVAL_STORAGE_KEY+'wl', JSON.stringify([...s])); } catch(e) {} },

  getWatched() { try { const r=localStorage.getItem(FESTIVAL_STORAGE_KEY+'watched'); return r?new Set(JSON.parse(r)):new Set(); } catch(e) { return new Set(); } },
  setWatched(s) { try { localStorage.setItem(FESTIVAL_STORAGE_KEY+'watched', JSON.stringify([...s])); } catch(e) {} },

  getPrioritized() { try { const r=localStorage.getItem(FESTIVAL_STORAGE_KEY+'prio'); return r?new Set(JSON.parse(r)):new Set(); } catch(e) { return new Set(); } },
  setPrioritized(s) { try { localStorage.setItem(FESTIVAL_STORAGE_KEY+'prio', JSON.stringify([...s])); } catch(e) {} },

  getFilmRatings() { try { const r=localStorage.getItem(FESTIVAL_STORAGE_KEY+'ratings'); return r?JSON.parse(r):{}; } catch(e) { return {}; } },
  setFilmRatings(o) { try { localStorage.setItem(FESTIVAL_STORAGE_KEY+'ratings', JSON.stringify(o)); } catch(e) {} },

  getSavedAgenda() { try { const r=localStorage.getItem(FESTIVAL_STORAGE_KEY+'saved'); return r?JSON.parse(r):null; } catch(e) { return null; } },
  setSavedAgenda(o) { try { localStorage.setItem(FESTIVAL_STORAGE_KEY+'saved', JSON.stringify(o)); } catch(e) {} },

  getAvailability() { try { const r=localStorage.getItem(FESTIVAL_STORAGE_KEY+'av3'); return r?JSON.parse(r):{}; } catch(e) { return {}; } },
  setAvailability(o) { try { localStorage.setItem(FESTIVAL_STORAGE_KEY+'av3', JSON.stringify(o)); } catch(e) {} },

  getLastRemovedSlots() { try { const r=localStorage.getItem(FESTIVAL_STORAGE_KEY+'lastslot'); if(!r) return []; const p=JSON.parse(r); return Array.isArray(p)?p:(p?[p]:[]); } catch(e) { return []; } },
  setLastRemovedSlots(a) { try { localStorage.setItem(FESTIVAL_STORAGE_KEY+'lastslot', JSON.stringify(a)); } catch(e) {} },

  // filmDelays: post-p5.5 NO contiene _hist (separado a filmDelaysHistory).
  // El strip de _hist en lectura permite migración suave para usuarios con storage pre-p5.5.
  getFilmDelays() { try { const r=localStorage.getItem(FESTIVAL_STORAGE_KEY+'delays'); if(!r) return {}; const p=JSON.parse(r); const {_hist:_, ...clean}=p; return clean; } catch(e) { return {}; } },
  setFilmDelays(o) { try { localStorage.setItem(FESTIVAL_STORAGE_KEY+'delays', JSON.stringify(o)); } catch(e) {} },

  // filmDelaysHistory: p5.5 key nuevo. Fallback al _hist anidado del key viejo si aún no se ha persistido el key nuevo (migración one-shot al primer save).
  getFilmDelaysHistory() { try { const r=localStorage.getItem(FESTIVAL_STORAGE_KEY+'delays_hist'); if(r) return JSON.parse(r); const old=localStorage.getItem(FESTIVAL_STORAGE_KEY+'delays'); if(!old) return {}; const parsed=JSON.parse(old); return parsed._hist||{}; } catch(e) { return {}; } },
  setFilmDelaysHistory(h) { try { localStorage.setItem(FESTIVAL_STORAGE_KEY+'delays_hist', JSON.stringify(h)); } catch(e) {} },

  getViewmodes() { try { const r=localStorage.getItem(FESTIVAL_STORAGE_KEY+'viewmodes'); return r?JSON.parse(r):{}; } catch(e) { return {}; } },
  setViewmodes(o) { try { localStorage.setItem(FESTIVAL_STORAGE_KEY+'viewmodes', JSON.stringify(o)); } catch(e) {} },

  // ── Global keys (NO prefix) ──
  getActiveFestId() { return localStorage.getItem('otrofestiv_festival'); },
  setActiveFestId(id) { try { localStorage.setItem('otrofestiv_festival', id); } catch(e) {} },

  getLang() { return localStorage.getItem('otrofestiv_lang'); },
  setLang(l) { try { localStorage.setItem('otrofestiv_lang', l); } catch(e) {} },

  getBuild() { return localStorage.getItem('otrofestiv_build'); },
  setBuild(b) { try { localStorage.setItem('otrofestiv_build', b); } catch(e) {} },
};
// ── STORAGE ADAPTER END ──────────────────────────────────────────────
