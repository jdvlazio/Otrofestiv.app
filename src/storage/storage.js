// ── src/storage/storage.js — Fase 8 Step 3 (CABLEADO) ─────────────────────────
//
// ESTADO: importado por src/main.js (Step 3). Encapsula TODO el I/O de
//   localStorage de la app. Único namespace de persistencia.
//
// DEPS: FESTIVAL_STORAGE_KEY (prefix de los user-state keys, scoped por festival)
//   se lee como bare-global → resuelto por el STATE BRIDGE de main.js (Step 2)
//   → state.get('FESTIVAL_STORAGE_KEY'). Late-binding: los métodos cierran sobre
//   el nombre, así que funcionan aunque el bridge/valor existan al call-time.
// NO encapsula (se quedan inline en main.js, vía _cloudSave/excepciones): cloud
//   sync, TMDB poster cache, otrofestiv_hint_cambiar, otrofestiv_display_name,
//   orf_build (SW staged rollout), splash lang preview (index.html, pre-módulo).
// Las wrappers saveX/loadState (orquestan storage + _cloudSave + notifications)
//   NO viven aquí — son controller-level (→ Wave 7).

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

  // ── Cloud-sync metadata (F0 — multi-dispositivo) ──
  // cloud_synced_at: el updated_at de la última fila que este dispositivo empujó
  //   o bajó con éxito. cloud_dirty: hay mutaciones locales aún sin subir.
  // El boot-load usa ambos para no pisar ediciones locales ni datos ya frescos.
  // `key` opcional: escribe/lee los flags de un festival ESPECÍFICO (no el activo).
  // _doCloudSave lo usa para no marcar el festival equivocado cuando el upsert async
  // resuelve tras un cambio de festival. Default = FESTIVAL_STORAGE_KEY (activo).
  getCloudSyncedAt(key) { try { return localStorage.getItem((key||FESTIVAL_STORAGE_KEY)+'cloud_at')||null; } catch(e) { return null; } },
  setCloudSyncedAt(ts, key) { try { localStorage.setItem((key||FESTIVAL_STORAGE_KEY)+'cloud_at', ts); } catch(e) {} },
  getCloudDirty(key) { try { return localStorage.getItem((key||FESTIVAL_STORAGE_KEY)+'cloud_dirty')==='1'; } catch(e) { return false; } },
  setCloudDirty(v, key) { try { localStorage.setItem((key||FESTIVAL_STORAGE_KEY)+'cloud_dirty', v?'1':'0'); } catch(e) {} },

  // ── Global keys (NO prefix) ──
  getActiveFestId() { return localStorage.getItem('otrofestiv_festival'); },
  setActiveFestId(id) { try { localStorage.setItem('otrofestiv_festival', id); } catch(e) {} },

  // Idioma: clave v2 (12 jul 2026). La clave vieja 'otrofestiv_lang' se IGNORA
  // a propósito: quedó contaminada por la era del bug de mezcla (toques al
  // selector para "arreglar" la mezcla dejaban un override accidental
  // persistido para siempre, pisando el idioma del celular — el default
  // correcto). Regla: el idioma del DISPOSITIVO manda en el arranque; solo una
  // elección explícita POSTERIOR en el toggle (que escribe v2) lo pisa.
  getLang() { return localStorage.getItem('otrofestiv_lang_v2'); },
  setLang(l) { try { localStorage.setItem('otrofestiv_lang_v2', l); localStorage.removeItem('otrofestiv_lang'); } catch(e) {} },

  getBuild() { return localStorage.getItem('otrofestiv_build'); },
  setBuild(b) { try { localStorage.setItem('otrofestiv_build', b); } catch(e) {} },
};
// ── STORAGE ADAPTER END ──────────────────────────────────────────────
