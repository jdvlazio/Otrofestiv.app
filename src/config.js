// ── src/config.js — Fase 8 Wave 1 (PREP, NO CABLEADO) ────────────────────────
//
// ⚠ ESTADO: módulo de preparación. NO está importado por index.html todavía.
//   Cero impacto en runtime/deploy/SW. El wiring real ocurre en Wave 1 post-
//   Tribeca (convierte el bootstrap a módulos + regla SW network-first /src/).
//
// ⚠ FUENTE DE VERDAD: hasta el wiring, las constantes VIVAS son las de
//   index.html. Este archivo es un mirror preparado. Si una constante cambia
//   en index.html antes del wiring, actualizar aquí también (o mover atómico
//   al wiring). Riesgo de drift gestionado: solo incluye constantes de baja
//   volatilidad (infra estática + taxonomía).
//
// EXCLUIDAS del prep (se mueven en el wiring atómico, no aquí):
//   - FESTIVAL_CONFIG / VENUES / NOTICES → festival-data de alto drift (pipeline
//     de onboarding las edita; duplicar = trampa de drift)
//   - TMDB_API_KEY → env-injected (vacío en source)
//   - _SB_URL / _SB_KEY → credenciales (publishable key)
//   - BUILD_VERSION → gestionado por bump-version.js (duplicar rompe el stamp)
//   - ICONS / LB_SVG → presentacionales → view/components.js (§12 del DAG)
//   - _DEFAULT_FEST_ID / DAY_KEYS / FESTIVAL_DATES → derivados / festival-state
//
// NOTA: copia fiel de index.html. Incluye un bug pre-existente conocido en
//   SECTION_COLORS ('Talks' duplicado) — NO se corrige aquí (prep = copia
//   exacta; el fix, si se decide, es trabajo aparte con discusión de diseño).

// ── TMDB (URLs estáticas) ────────────────────────────────────────────────────
export const TMDB_IMG = "https://image.tmdb.org/t/p/w185";
export const TMDB_API_BASE = 'https://api.themoviedb.org/3';
export const TMDB_POSTER_BASE = 'https://image.tmdb.org/t/p/w500';
export const _POSTER_CACHE_PFX = 'orf_poster_v1_';

// ── Constantes numéricas de scheduling ───────────────────────────────────────
export const FESTIVAL_BUFFER = 15;        // min entre funciones: salida sala + intro siguiente
export const MAX_REMEMBERED_SLOTS = 5;
export const DEFAULT_DURATION_MIN = 90;

// ── Taxonomía de secciones (orden para el dropdown plano) ────────────────────
export const SECTION_ORDER_LIST = [
  // Con emoji
  '🌟 Gala','✨ Spotlight+','🏆 U.S. Narrative Competition',
  '🌍 International Narrative Competition','🏅 Documentary Competition',
  '🎬 Spotlight Narrative','📹 Spotlight Documentary','👁️ Viewpoints',
  '🌙 Escape From Tribeca','📽️ Reunions & Retrospectives','🗣️ Talks',
  '🎙️ Podcasts','⭐ Special Events','📱 NOW','📺 TV','🎨 Shorts Programs',
  '🌿 Free Outdoor Screenings',
  // Sin emoji (festivales legacy)
  'Gala','Spotlight+','U.S. Narrative Competition',
  'International Narrative Competition','Documentary Competition',
  'Spotlight Narrative','Spotlight Documentary','Viewpoints',
  'Escape From Tribeca','Reunions & Retrospectives','Storytellers',
  'Talks','Special Events','NOW','TV','Shorts Programs',
  'Free Outdoor Screenings','Shorts'
];

// ── Orden de categorías para el dropdown agrupado ────────────────────────────
export const FILM_CATEGORY_ORDER = ['Films','TV','Talks','NOW','Podcasts'];
export const FILM_CATEGORY_LABEL = {
  'Films':'Films','TV':'TV','Talks':'Talks','NOW':'NOW','Podcasts':'Podcasts'
};

// ── Mapa canónico de colores por sección ─────────────────────────────────────
// Consistente entre festivales: misma sección → mismo color.
export const SECTION_COLORS = {
  // Con emoji (Tribeca 2026+)
  '🌟 Gala':'#EF9F27',
  '✨ Spotlight+':'#5DCAA5',
  '🎬 Spotlight Narrative':'#7F77DD',
  '📹 Spotlight Documentary':'#1D9E75',
  '🏆 U.S. Narrative Competition':'#D85A30',
  '🌍 International Narrative Competition':'#378ADD',
  '🏅 Documentary Competition':'#639922',
  '👁️ Viewpoints':'#AFA9EC',
  '🌙 Escape From Tribeca':'#E24B4A',
  '📽️ Reunions & Retrospectives':'#888780',
  '🗣️ Talks':'#FAC775',
  '🎙️ Podcasts':'#85B7EB',
  '📱 NOW':'#5DCAA5',
  '📺 TV':'#B4B2A9',
  '⭐ Special Events':'#EF9F27',
  '🥇 Awards Screenings':'#BA7517',
  '🎨 Shorts Programs':'#1D9E75',
  '🌿 Free Outdoor Screenings':'#97C459',
  '✂️ Shorts':'#888780',
  // Sin emoji (AFF, FICCI, Cinemancia — compatibilidad)
  'Gala':'#EF9F27',
  'Spotlight+':'#5DCAA5',
  'Spotlight Narrative':'#7F77DD',
  'Spotlight Documentary':'#1D9E75',
  'U.S. Narrative Competition':'#D85A30',
  'International Narrative Competition':'#378ADD',
  'Documentary Competition':'#639922',
  'Viewpoints':'#AFA9EC',
  'Escape From Tribeca':'#E24B4A',
  'Reunions & Retrospectives':'#888780',
  'Storytellers':'#FAC775',
  'Talks':'#FAC775',
  'Talks':'#85B7EB',
  'NOW':'#5DCAA5',
  'TV':'#B4B2A9',
  'Special Events':'#EF9F27',
  'Awards Screenings':'#BA7517',
  'Shorts Programs':'#1D9E75',
  'Free Outdoor Screenings':'#97C459',
  'Shorts':'#888780',
};
