// ══ Preamble — UI constants, Capgo check, FILMS[], POSTERS{} ══

// ══════════════════════════════════════════════════════════════════
// FUENTE ÚNICA DE VERDAD — Textos del UI
// ══════════════════════════════════════════════════════════════════
    rescheduled: 'REPROGRAMADA',
    qa:          'Q&A',
    inscription: 'INSCRIPCIÓN',
  },
  travel: {
    walking: 'a pie',
    transit: 'en carro',
  },
  empty: {
    noActivity:  'Nada en tu plan este día',
    noResults:   'Sin actividades para este filtro',
    noPending:   'Sin actividades pendientes',
    planCovered: 'Tu agenda está bien cubierta. No hay más actividades que quepan.',
    allPassed:   'Todas las actividades de tu plan ya pasaron',
    overlap:     'Hay actividades con horario solapado',
  },
};

// ── Capgo: confirma que el bundle cargó correctamente ──────────
// Sin esta llamada, Capgo hace rollback automático a los 10s.
// El guard ?. asegura que en web (GitHub Pages) no hay error.
if(window.Capacitor?.Plugins?.CapacitorUpdater){
  window.Capacitor.Plugins.CapacitorUpdater.notifyAppReady();
}

// ═══════════════════════════════════════════════════════════════
// 1 · DATOS DEL FESTIVAL
//     FILMS, POSTERS, CUSTOM_POSTERS, FICCI_POSTER_URL
// ═══════════════════════════════════════════════════════════════



/* ── POSTER GENERATIVO — identidad Otrofestiv para programas ──────────
   REGLA CANÓNICA — nunca romper sin justificación explícita:

   PRIORIDAD DE POSTER (en todo contexto — grilla, card, Mi Plan):
     1. Poster real (CUSTOM_POSTERS > SHORT_IMGS > POSTERS/TMDB)
     2. Poster generativo (solo si no hay real)
     3. Placeholder vacío (surf-2) — nunca negro

   TIPOS DE POSTER GENERATIVO — mismo _buildPosterSVG, misma plantilla:
     · Competencia cortos → header teal  · l1:'COMPETENCIA' · l2:'CORTOMETRAJES'
     · Programa cortos   → header teal  · l1:'PROGRAMA'    · l2:'CORTOMETRAJES'
     · Evento/Industry   → header ámbar · l1:'INDUSTRY'    · l2:'DAYS'

   REGLA DE DETECCIÓN:
     f.type === 'event'  → makeEventPoster()
     f.is_cortos === true → getPosterSrc(title,true) || makeProgramPoster(title,dur,section)
     resto               → getPosterSrc(title,false) || null

   ONERROR: siempre this.remove() — nunca this.style.opacity=0
   TÍTULO: limpiar prefijos redundantes en makeProgramPoster()
────────────────────────────────────────────────────────────────────── */
function _buildPosterSVG(o){
