# Sistema de iconos — Otrofestiv

> Auditoría profunda + canon (18 jul 2026). Guardianes en `validate.py`:
> `[icon-single-source]`, `[star-semantics]`, `[chrome-glass]` (strokes/colores).

## Fuente única

Todo glifo de UI sale del objeto **`ICONS`** en `src/view/components.js`.
Nunca escribir un `<svg>` inline en `src/view/*.js` ni `src/controller/*.js`:
el guardián `[icon-single-source]` rompe el build si reaparece un glifo migrado
(chevronD, clock, pin, alert, moon, x, check) inline fuera de `components.js`.

**Excepciones legítimas** (identidad propia, NO son iconos de UI genéricos):
- `starSVG(fill)` — renderer de **estrellas de calificación** con half-fill
  (gradiente). Es la fuente única del rating; su polígono coincide con
  `ICONS.star` pero añade la lógica de relleno. Vive en `components.js`.
- Estrellas de rating del venue-sheet (`sheets-controller.js`) — misma familia
  rating, con gradiente parametrizado.
- `LB_SVG` — logo de Letterboxd (marca, colores hardcodeados permitidos).
- Generadores de póster (`_buildPosterV16`, `makeEventPoster`…) — producen SVG
  como imagen, no como icono.
- **Shell HTML estático** de `index.html` (header, nav, cierres de sheet): esos
  `<svg>` se pintan ANTES de que arranque el JS, así que no pueden referenciar
  `ICONS` en runtime. Se mantienen inline como excepción documentada; su path
  debe coincidir con el de `ICONS` (misma silueta).

## Anatomía

- **viewBox** `0 0 24 24` uniforme. **stroke-width `1.75`** universal (único).
- **Color**: `currentColor` — el icono hereda el color del texto/contexto. Única
  divergencia intencional: `.sec-hdr>svg` es ámbar mientras la etiqueta es
  `--white-60` (sistema de acento). Prohibido color hardcodeado (usar tokens).
- **aria-hidden**: TODO icono de `ICONS` es `aria-hidden="true" focusable="false"`
  de fábrica (decorativo). El nombre accesible lo lleva el botón contenedor.

## Escala (icono ≈ tamaño del texto vecino)

| Familia de texto | Tamaño icono | Cómo |
|---|---|---|
| t-base (13) — sec-hdr, listas | **13** | base de `ICONS` |
| t-label / t-xs (9–11) — eyebrows, warn, badges | **11** | `.ctx-eyebrow svg`, `.sec-hdr.sm>svg`, `.mplan-warn-row svg` |
| micro-arrows de navegación | **9** | `.mplan-nav-day-arrow svg`, `.mplan-wk-col-arrow svg` |
| icon-only (botones sin texto) | **14–16** | tamaño propio del botón |

## Semántica — un glifo, un concepto

- **★ estrella = CALIFICACIÓN** (convención universal del cine). NUNCA prioridad.
- **🔖 bookmark = PRIORIDAD** ("marcado para no perdérmelo"). `ICONS.bookmark` /
  `ICONS.bookmarkFill`. Guardián `[star-semantics]`: `★`/`ICONS.star` en una línea
  de prioridad (togglePriority, cta_priorizar, lbl_prioridades…) rompe el build.
- **♥ corazón = INTERÉS**. **✓ check = visto/confirmado**. **🕐 clock = horario**.
- Vocabulario oficial: leyenda en `src/main.js`.

## Accesibilidad e interacción

- Botones icon-only: nombre accesible obligatorio (`aria-label` / `data-i18n-aria`).
- Área táctil ≥ 44px. Botones aislados usan expander `::after{inset:-14px}`
  (notice-close, poster-wl-dot, prio-chip-rm, av-pill-rm). Pares adyacentes NO se
  expanden (robo de taps entre vecinos).
- Foco: `:focus-visible` global ámbar (`outline:2px solid var(--amber)`).
- Emojis funcionales (🎬 placeholder, banderas de idioma) → `aria-hidden`.

## Pendiente

- Migración del shell HTML estático a un populado por JS (hoy inline por timing
  de arranque — excepción documentada arriba).
