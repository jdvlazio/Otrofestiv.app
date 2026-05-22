// ── src/state/state.js — Fase 8 (PREP, NO CABLEADO) ───────────────────────────────
//
// ⚠ ESTADO: módulo de preparación. NO importado por index.html. Cero impacto
//   runtime/deploy/SW. Wiring real post-Tribeca.
// ⚠ FUENTE DE VERDAD: index.html hasta el wiring. Copia fiel del bloque
//   contiguo marcado. Si cambia en index.html antes del wiring, re-generar.
//
// ⚠⚠ D-INFRA-4: este bloque incluye el MIRROR de globals (_MIRROR_TARGETS /
//   _MIRROR_READERS + late-binding a los 19 let globals). El WIRING (Wave 3)
//   ELIMINA el mirror — el container pasa a poseer _data directamente y los
//   reads migran a state.get(). Esta copia es FIEL al estado actual (con
//   mirror); NO es la forma final. El mirror referencia los 19 globals
//   (watchlist, FILMS, etc.) como ambient — sin definir aquí (unwired, no
//   ejecuta). Exports: subscribe, subscribeRender, transaction, set, update,
//   batchUpdate, get, snapshot.

// ── STATE MIRROR START ───────────────────────────────────────────────
// state — contenedor central para los 19 globals que componen el estado de
// la app. Estrategia "mirror": toda escritura va por state.set/update/batchUpdate,
// que actualiza tanto el state interno como el global espejo. Lecturas siguen
// yendo al global directo (sin tocar readers en p5.5 — eso es p5.6).
//
// Invariante: ∀k ∈ ROSTER, state.get(k) === <global k>. Enforced por
// validate.py [state-mirror]: cualquier escritura a un global del roster fuera
// de este bloque es un error (con whitelist documentada para declaraciones
// iniciales y el template literal del worker boundary).
//
// Atomicidad: batchUpdate aplica TODO el batch al state + mirrors antes de
// notificar cualquier subscriber. Cero estado parcial visible para subscribers.
// Reentrada soportada (subscriber puede llamar set/update/batchUpdate). Rollback
// si _MIRROR_TARGETS[k] throws.
//
// Helpers immutable expuestos (_addToSet, _delFromSet, _omit) para reemplazar
// patrones de mutación in-place en los callsites migrados.
//
// Posición: justo después del storage adapter, antes de _I18N. Los globals
// del roster (FILMS, watchlist, etc.) se declaran DESPUÉS de este bloque en
// el flujo del script — el mirror funciona vía closure late-binding sobre
// los let-bindings del módulo.
export const state = (() => {
  // _MIRROR_TARGETS: setter por key → asigna al `let` del módulo.
  // _MIRROR_READERS: getter por key → lee el `let` actual del módulo.
  // Late-binding via closure — funciona aunque el global se declare después.
  // _MIRROR_READERS es necesario porque mientras p5.5 está migrando, muchos
  // globals se reasignan via legacy code (no via state.set). Lazy fallback en
  // state.get/update/batchUpdate consulta el global vivo si _data no tiene la
  // key todavía — preservando la invariante state.get(k) === <global k>.
  const _MIRROR_TARGETS = {
    _activeFestId:        v => { _activeFestId = v; },
    FILMS:                v => { FILMS = v; },
    FESTIVAL_DATES:       v => { FESTIVAL_DATES = v; },
    FESTIVAL_END:         v => { FESTIVAL_END = v; },
    FESTIVAL_STORAGE_KEY: v => { FESTIVAL_STORAGE_KEY = v; },
    PRIO_LIMIT:           v => { PRIO_LIMIT = v; },
    TZ_OFFSET:            v => { TZ_OFFSET = v; },
    FESTIVAL_TRANSPORT:   v => { FESTIVAL_TRANSPORT = v; },
    watchlist:            v => { watchlist = v; },
    watched:              v => { watched = v; },
    prioritized:          v => { prioritized = v; },
    filmRatings:          v => { filmRatings = v; },
    filmDelays:           v => { filmDelays = v; },
    filmDelaysHistory:    v => { filmDelaysHistory = v; },
    savedAgenda:          v => { savedAgenda = v; },
    availability:         v => { availability = v; },
    lastRemovedSlots:     v => { lastRemovedSlots = v; },
    _lang:                v => { _lang = v; },
    _simTime:             v => { _simTime = v; },
  };
  const _MIRROR_READERS = {
    _activeFestId:        () => _activeFestId,
    FILMS:                () => FILMS,
    FESTIVAL_DATES:       () => FESTIVAL_DATES,
    FESTIVAL_END:         () => FESTIVAL_END,
    FESTIVAL_STORAGE_KEY: () => FESTIVAL_STORAGE_KEY,
    PRIO_LIMIT:           () => PRIO_LIMIT,
    TZ_OFFSET:            () => TZ_OFFSET,
    FESTIVAL_TRANSPORT:   () => FESTIVAL_TRANSPORT,
    watchlist:            () => watchlist,
    watched:              () => watched,
    prioritized:          () => prioritized,
    filmRatings:          () => filmRatings,
    filmDelays:           () => filmDelays,
    filmDelaysHistory:    () => filmDelaysHistory,
    savedAgenda:          () => savedAgenda,
    availability:         () => availability,
    lastRemovedSlots:     () => lastRemovedSlots,
    _lang:                () => _lang,
    _simTime:             () => _simTime,
  };

  function _seedKey(key) {
    // Si _data no tiene la key, pull el valor actual del global mirror.
    // Idempotente — después de la primera lectura, _data tiene la key y
    // las futuras escrituras (state.set) mantienen el sync.
    if (!(key in _data) && _MIRROR_READERS[key]) {
      _data[key] = _MIRROR_READERS[key]();
    }
  }

  const _data = Object.create(null);
  const _subs = new Map();             // Map<key, Set<callback>>  — genérico (value, key)
  const _renderSubs = new Map();       // Map<key, Set<renderFn>>  — pipeline render (p7d), deduped arg-less
  let _batchDepth = 0;
  const _dirty = new Set();

  function _notify(key) {
    const subs = _subs.get(key);
    if (!subs) return;
    // Snapshot del set para tolerar unsubscribe durante la iteración
    [...subs].forEach(cb => { try { cb(_data[key], key); } catch(e) { console.error('[state] subscriber error:', e); } });
  }

  // Render pipeline (p7d): colecta render fns de las keys afectadas, dedup vía
  // Set (una render fn suscrita a N keys de un batch corre 1×), ejecuta arg-less.
  function _runRenderSubs(keys) {
    const fns = new Set();
    for (const k of keys) {
      const subs = _renderSubs.get(k);
      if (subs) subs.forEach(fn => fns.add(fn));
    }
    [...fns].forEach(fn => { try { fn(); } catch(e) { console.error('[render] subscriber error:', e); } });
  }

  return {
    // ── Lecturas ──
    get(key) { _seedKey(key); return _data[key]; },
    snapshot() {
      // Seed todas las keys del roster para que el snapshot refleje los globals
      Object.keys(_MIRROR_READERS).forEach(_seedKey);
      return Object.assign({}, _data);
    },

    // ── Escrituras ──
    set(key, value) {
      if (!(key in _MIRROR_TARGETS)) throw new Error('[state] unknown key: ' + key);
      _data[key] = value;
      _MIRROR_TARGETS[key](value);
      if (_batchDepth > 0) { _dirty.add(key); return; }
      _notify(key);
      _runRenderSubs([key]);
    },

    update(key, fn) {
      _seedKey(key);
      this.set(key, fn(_data[key]));
    },

    batchUpdate(updates) {
      const keys = Object.keys(updates);
      if (keys.length === 0) return;
      // Validar keys ANTES de aplicar — fail-fast sin estado parcial
      for (const k of keys) {
        if (!(k in _MIRROR_TARGETS)) throw new Error('[state] unknown key: ' + k);
      }
      // Seed pre-snapshot para que rollback restaure al global vivo si _data
      // aún no tenía la key (no a undefined)
      for (const k of keys) _seedKey(k);
      // Snapshot pre-batch para rollback
      const snapshot = {};
      for (const k of keys) snapshot[k] = _data[k];

      _batchDepth++;
      try {
        for (const k of keys) {
          _data[k] = updates[k];
          _MIRROR_TARGETS[k](updates[k]);
          _dirty.add(k);
        }
      } catch (e) {
        // Rollback: state + mirrors restaurados desde snapshot
        for (const k of keys) {
          _data[k] = snapshot[k];
          _MIRROR_TARGETS[k](snapshot[k]);
        }
        // Remover dirty solo de claves de ESTE batch (otras pueden quedar dirty del padre)
        for (const k of keys) _dirty.delete(k);
        _batchDepth--;
        throw e;
      }
      _batchDepth--;

      if (_batchDepth === 0) {
        const toNotify = [..._dirty];
        _dirty.clear();
        for (const k of toNotify) _notify(k);
        _runRenderSubs(toNotify);   // deduped a través de TODAS las dirty keys
      }
    },

    // ── transaction (p7d) — agrupa mutaciones secuenciales ──
    // Difiere notify + render hasta el final del fn, igual que batchUpdate pero
    // para mutaciones SECUENCIALES con lógica intermedia (set/update/batchUpdate
    // anidados). El pipeline render dispara 1× al cerrar. Reusa _batchDepth.
    transaction(fn) {
      _batchDepth++;
      try {
        fn();
      } finally {
        _batchDepth--;
        if (_batchDepth === 0) {
          const toNotify = [..._dirty];
          _dirty.clear();
          for (const k of toNotify) _notify(k);
          _runRenderSubs(toNotify);   // deduped, 1×
        }
      }
    },

    // ── Subscribe ──
    subscribe(key, cb) {
      if (!_subs.has(key)) _subs.set(key, new Set());
      _subs.get(key).add(cb);
      return () => _subs.get(key)?.delete(cb);
    },

    // ── Subscribe render (p7d) — canal de pipeline, deduped, arg-less ──
    // Registra una render fn contra múltiples keys. En un batch que toca varias
    // de esas keys, la fn corre 1× (dedup). Separado del subscribe genérico
    // para preservar su contrato (value, key).
    subscribeRender(keys, renderFn) {
      for (const k of keys) {
        if (!_renderSubs.has(k)) _renderSubs.set(k, new Set());
        _renderSubs.get(k).add(renderFn);
      }
      return () => keys.forEach(k => _renderSubs.get(k)?.delete(renderFn));
    },

    // ── Helpers immutable (expuestos para callsites migrados) ──
    _addToSet(s, t) { return s.has(t) ? s : new Set([...s, t]); },
    _delFromSet(s, t) { if (!s.has(t)) return s; const n = new Set(s); n.delete(t); return n; },
    _omit(o, k) { if (!(k in o)) return o; const { [k]:_, ...rest } = o; return rest; },
  };
})();
// ── STATE MIRROR END ─────────────────────────────────────────────────
