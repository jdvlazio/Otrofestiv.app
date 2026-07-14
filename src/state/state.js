// ── src/state/state.js — Fase 8 Step 2 (CABLEADO) ────────────────────────────
//
// ESTADO: importado por src/main.js (Step 2). Contenedor central de los 19
//   globals del roster. Fuente única de verdad: `_data` (propio del container).
//
// D-INFRA-4 (Wave 3): el MIRROR fue ELIMINADO. Antes el container espejaba a
//   19 `let` globals (setters/readers espejo + lazy-seeding). Ahora el
//   container POSEE `_data` directamente; main.js instala un bridge
//   (Object.defineProperty sobre globalThis) que rutea cada bare-global del
//   roster a state.get/set. Una sola dirección: bare-global → state.
//
// Auto-contenido: cero referencias ambient. Importable/testeable directo.
//
// Exports: state — { get, snapshot, set, update, batchUpdate, transaction,
//   subscribe, subscribeRender, _addToSet, _delFromSet, _omit }.

// Roster — las 19 keys de estado que el container administra. El bridge de
// main.js expone exactamente estas como propiedades de globalThis.
const _ROSTER = new Set([
  '_activeFestId', 'FILMS', 'FESTIVAL_DATES', 'FESTIVAL_END',
  'FESTIVAL_STORAGE_KEY', 'PRIO_LIMIT', 'TZ_OFFSET', 'FESTIVAL_TRANSPORT',
  'watchlist', 'watched', 'prioritized', 'filmRatings', 'filmDelays',
  'filmDelaysHistory', 'savedAgenda', 'availability', 'lastRemovedSlots',
  '_lang', '_simTime',
]);

// Expuesto para la fitness function de FESTIVAL_STATE (festival-context.js): el
// test afirma que toda key por-festival declarada está en el roster.
export const STATE_ROSTER = _ROSTER;

export const state = (() => {
  // Single source of truth — el container posee los valores. Sembrado vía el
  // bridge: las (ex-)declaraciones `let X = init` de main.js pasaron a ser
  // `X = init` bare → globalThis.X setter → state.set('X', init). Así cada key
  // se puebla cuando su línea de init ejecuta (timing idéntico al previo).
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
    get(key) { return _data[key]; },
    snapshot() { return Object.assign({}, _data); },

    // ── Escrituras ──
    set(key, value) {
      if (!_ROSTER.has(key)) throw new Error('[state] unknown key: ' + key);
      _data[key] = value;
      if (_batchDepth > 0) { _dirty.add(key); return; }
      _notify(key);
      _runRenderSubs([key]);
    },

    update(key, fn) {
      this.set(key, fn(_data[key]));
    },

    batchUpdate(updates) {
      const keys = Object.keys(updates);
      if (keys.length === 0) return;
      // Validar keys ANTES de aplicar — fail-fast sin estado parcial
      for (const k of keys) {
        if (!_ROSTER.has(k)) throw new Error('[state] unknown key: ' + k);
      }
      // Snapshot pre-batch para rollback
      const snapshot = {};
      for (const k of keys) snapshot[k] = _data[k];

      _batchDepth++;
      try {
        for (const k of keys) {
          _data[k] = updates[k];
          _dirty.add(k);
        }
      } catch (e) {
        // Rollback: state restaurado desde snapshot
        for (const k of keys) _data[k] = snapshot[k];
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
