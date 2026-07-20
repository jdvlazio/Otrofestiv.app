# DESIGN.md — Contrato normativo de diseño · Otrofestiv

> Fuente de verdad **visual** de la app. Es a los cambios de CSS lo que `CLAUDE.md`
> es a la arquitectura. **Antes de cualquier cambio de CSS en componentes de lista,
> leer este documento.**
>
> Mantenido a mano (no autogenerado). Cada decisión canónica nueva la aprueba el
> Product Owner (Juan) antes de implementarse.

---

## 0 · Regla de uso (LEER PRIMERO)

> **Antes de cualquier cambio de CSS en componentes de lista, leer este documento.
> Cualquier valor que no esté aquí requiere decisión explícita del Product Owner
> antes de implementar.**

Corolarios:
- No introducir valores nuevos de color/tamaño/peso para datos ya tipados aquí
  (título, venue/meta, sección, hora). Si un componente necesita desviarse, es una
  **excepción** y va a la §5 con su razón — aprobada por el PO.
- Cero valores raw de spacing/tipografía/radio: todo vía `var(--…)` (regla heredada
  de CLAUDE.md). Las excepciones raw existentes están listadas en §5.
- Este documento describe el **canónico aprobado**, no el estado histórico. Si el
  código difiere, el código está mal.
- **Fuente ejecutable de la verdad**: cada regla de diseño tiene un guardián en
  `validate.py` (o un `.spec.js` de Playwright) que rompe el build si se viola.
  Este doc es la referencia legible; los guardianes son la aplicación. Índice de
  guardianes de diseño en §8 (por tema) y en los comentarios de `validate.py`.

---

## 1 · Tokens del sistema

Valores resueltos, extraídos de `:root` en `index.html`.

### Spacing (escala base-2)
| Token | Valor | Uso |
|---|---|---|
| `--sp-1` | 4px | micro: gaps inline, separaciones mínimas |
| `--sp-2` | 8px | xs: gaps entre elementos, padding vertical de ítems |
| `--sp-3` | 12px | sm: padding componentes pequeños |
| `--sp-4` | 16px | md: padding lateral de ítems de lista |
| `--sp-5` | 24px | lg: padding secciones y contenedores |
| `--sp-6` | 32px | xl: separación entre secciones |
| `--sp-7` | 48px | empty-state hero |
| `--sp-btn` | 14px | padding vertical de botones primarios full-width |

### Tipografía — tamaños
| Token | Valor | Uso típico |
|---|---|---|
| `--t-badge` | 8px | badges diminutos |
| `--t-xs` | 9px | metadata densa (excepción calendario) |
| `--t-label` | 10px | etiquetas, **sección (terciario)** |
| `--t-sm` | 11px | **venue/meta (secundario)**, subtítulos |
| `--t-caption` | 12px | captions |
| `--t-base` | 13px | **título (primario)**, cuerpo |
| `--t-md` | 16px | hora destacada, inputs (anti-zoom iOS) |
| `--t-lg` | 20px | números de día, headings |
| `--t-display` | 30px | display |
| `--t-icon` | 15px | íconos inline (corazón) |
| `--flag-size` | 13px (= `--t-base`) | flags/emojis de país |

### Tipografía — pesos
| Token | Valor | Uso |
|---|---|---|
| `--w-thin` | 400 | **texto secundario (venue/meta)** — peso base |
| `--w-regular` | 500 | cuerpo intermedio |
| `--w-semi` | 600 | **sección (terciario)**, énfasis suave |
| `--w-bold` | 700 | **título (primario)**, separador de hora |
| `--w-display` | 800 | display / wordmark |

> Nota de naming: `--w-thin` = 400 es el peso **base** del cuerpo (el nombre "thin"
> es un legado del token, no implica un peso ultraligero). Es el peso canónico del
> texto secundario.

### Radios
| Token | Valor |
|---|---|
| `--r-sm` | 4px |
| `--r-md` | 8px |
| `--r` | 12px |
| `--r-sheet` | 28px (squircle generoso — 18 jul 2026) |
| `--r-handle` | 2px |
| `--r-pill` | 999px |

### Color — superficies (negros CÁLIDOS, 18 jul 2026)
Sesgo ~1.5% hacia el ámbar (R≥G≥B), misma luminancia que la paleta neutra
anterior — la app deja de compartir fondo con cualquier dark mode genérico.
Gris neutro puro PROHIBIDO en superficies (guardián `[warm-neutrals]`).
| Token | Valor |
|---|---|
| `--bg` | #0B0A08 |
| `--surf` | #151311 |
| `--surf-2` | #1B1917 |
| `--surf-3` | #201E1B |
| `--card-a` | #1F1D1A |
| `--card-b` | #24211E |
| `--card-p` | #151311 |

### Color — bordes (dos niveles semánticos)
| Token | Valor | Uso |
|---|---|---|
| `--bdr` | #2B2825 | chrome estructural: nav, headers, separadores fuertes |
| `--bdr-l` | #1F1D1A | separación de contenido: filas de lista (el tono de TODA divisoria de lista) |

### Color — texto
| Token | Valor | Contraste sobre `--bg` | Rol |
|---|---|---|---|
| `--white` | #F0EDE8 | ~16:1 | **primario** (título) |
| `--white-60` | rgba(240,237,232,.6) | ~9:1 | **terciario** (sección) |
| `--white-65` | rgba(240,237,232,.65) | — | variantes |
| `--white-45` | rgba(240,237,232,.45) | — | deshabilitado |
| `--white-30` | rgba(240,237,232,.3) | — | muy tenue |
| `--gray` | #888888 | **~5.6:1 (pasa WCAG AA)** | **secundario** (venue/meta) |
| `--gray2` | #555555 | **~2.7:1 (falla AA)** | de-énfasis fuerte / íconos no críticos |
| `--gray3` | #444444 | — | placeholders de input |

### Color — acentos
| Token | Valor | Uso |
|---|---|---|
| `--amber` | #F59E0B | acento primario, hora, CTA, estado activo |
| `--amber-d` | #D97706 | amber oscuro |
| `--green` | #3AAA6E | "en curso" / visto / ahora |
| `--event-blue` | rgb(107,155,209) | eventos en calendario (talleres/industria) |
| `--red` | #E05252 | conflicto / destructivo |
| `--yellow` | #E5A020 | duración larga / advertencia |
| `--black` | #000 | texto sobre amber (CTA) |

Opacidades de amber disponibles: `-06 -08 -10 -12 -20 -30 -35 -40 -50 -55 -60 -70 -85`.
Familias análogas para green / red / yellow / event-blue / overlay.

### Transiciones
| Token | Valor | Uso |
|---|---|---|
| `--tr-fast` | 100ms ease | hover de color |
| `--tr-base` | 150ms ease | micro-interacción (botones, badges) |
| `--tr-smooth` | 200ms ease | overlays, opacidades |
| `--tr-enter` | 300ms ease-out | entradas al DOM |
| `--sheet-in` | transform .38s cubic-bezier(.34,1.56,.64,1) | apertura SPRING de TODO bottom-sheet |
| `--sheet-out` | transform .3s cubic-bezier(.32,0,.67,0) | cierre ease-in de TODO bottom-sheet |

Los 9 bottom-sheets usan `--sheet-in`/`--sheet-out` (guardián `[sheet-spring]`);
un sheet nuevo con curva propia rompe el build.

### Pósters (ratio 2:3)
| Token | Dimensión | Uso |
|---|---|---|
| `--poster-xs-w/h` | 56×84 | thumbnail de lista (Programa, Mi Plan, Planear) |
| `--poster-md-w/h` | 72×108 | chip standalone (prio strip) |
| `--poster-lg-w/h` | 96×144 | card descubrimiento / sheet |

### Fuente
`--font: 'Plus Jakarta Sans', sans-serif;` (con fallback calibrado `Plus Jakarta Sans Fallback`).

---

## 2 · Componente canónico `film-list-item`

Cuatro contextos muestran una película en lista (Programa, Intereses, Planear,
Mi Plan). Comparten un **núcleo canónico** y difieren solo en **variantes
controladas por contexto**.

### 2.0 · Núcleo constante (los 4 contextos)

| Elemento | Valor canónico |
|---|---|
| **Poster** | `56×84` (`--poster-xs`) · `border-radius:var(--r-sm)` · `background:var(--surf-2)` |
| **Título** | `font-size:var(--t-base)` · `font-weight:var(--w-bold)` · `color:var(--white)` |
| **Venue/meta** | `font-size:var(--t-sm)` · `font-weight:var(--w-thin)` · `color:var(--gray)` |
| **Sección** (donde aplique) | `font-size:var(--t-label)` · `font-weight:var(--w-semi)` · `color:var(--white-60)` |
| **gap interno** | `var(--sp-3)` |
| **align-items** | `flex-start` |
| **Offset horizontal del poster** | **16px** desde el borde de pantalla en los 4 (vía padding del item o del contenedor — ver §2.6) |

### 2.0.1 · Variantes por contexto

| Variante | Hora | Acciones | Divisor |
|---|---|---|---|
| **`--program`** (`.plist-item`) | header sticky agrupador (`.plist-time-hdr`, `t-label`/`w-bold`/`amber`) — agrupa funciones del mismo slot | ♥ corazón (toggle watchlist) | `border-bottom` por item |
| **`--interests`** (`.int-item`) | — (no aplica; muestra días/próxima) | ★ priorizar + ✓ vista | `border-bottom` por item |
| **`--plan-edit`** (`#ag-result .saved-item`, Planear) | **protagonista en info**: `t-md`/`w-bold`/`amber`, dentro de `.saved-info` arriba del título | Cambiar (switch, gris) + Quitar (X, rojo) | **sin divisor por item** — agrupa por día (border-top en day landmark) |
| **`--plan-saved`** (`.mplan-row`, Mi Plan) | **protagonista en info**: `t-md`/`w-bold`/`amber`, dentro de `.mplan-ri` arriba del título (tappable, sin subrayado) | Quitar (X, rojo) | **sin divisor por item** — agrupa por día |
| **`--plan-saved`** (`.suggestion-item`, Sugerencias en Mi Plan) | **protagonista en info**: `t-md`/`w-bold`/`amber`, dentro de `.suggestion-info` arriba del título | + Añadir / ↩ Restaurar (`.suggestion-add`, pill) | `border-bottom` por item (sub-lista corta, no agrupa por día) |

> **Decisiones A–D (PR sistema unificado, aprobadas por el PO):**
> - **A — Hora:** Planear y Mi Plan unifican a `t-md`/`w-bold`/`amber` dentro de info, arriba del título. Mi Plan pierde el subrayado punteado de la hora — sigue tappable (`toggleFilmAlternatives`); el affordance es el contexto, no el subrayado.
> - **B — Offset horizontal:** **16px** en los 4. Programa y Planear ya estaban; Intereses bajó 32→16 (item flush, `.ag-view` aporta los 16) y Mi Plan 29→16 (la lista del día salió del card `.mplan-wrap`).
> - **C — align-items:** `flex-start` en los 4 (Mi Plan dejó de ser `center`).
> - **D — Divisor:** Planear y Mi Plan **agrupan por día sin divisor por item**. Programa e Intereses mantienen `border-bottom` por item (no agrupan).

### 2.1–2.5 · Anatomía por contexto

Valores **canónicos aprobados** por contexto:

### 2.1 · `.plist-item` — Programa día (lista de horarios)

| Clase | Propiedades canónicas |
|---|---|
| `.plist-item` | `display:flex; align-items:flex-start; gap:var(--sp-3); padding:var(--sp-2) var(--sp-4); border-bottom:1px solid var(--bdr-l)` |
| `.plist-poster` | `56×84; border-radius:var(--r-sm); background:var(--surf-2); object-fit:cover; flex-shrink:0` |
| `.plist-info` | `flex:1; min-width:0` |
| `.plist-title` | **`font-size:var(--t-base); font-weight:var(--w-bold); color:var(--white)`**; `margin-bottom:2px; display:flex; align-items:center; gap:var(--sp-1)` |
| `.plist-title-txt` | `flex:1; min-width:0` + ellipsis |
| `.plist-meta` | **`font-size:var(--t-sm); font-weight:var(--w-thin); color:var(--gray)`**; `margin-bottom:var(--sp-1)` |
| `.plist-sec` | **`font-size:var(--t-label); font-weight:var(--w-semi); color:var(--white-60)`**; `margin-top:2px; letter-spacing:.2px` |
| `.plist-heart` | `font-size:var(--t-icon); color:var(--amber); padding:6px; border-radius:50%; align-self:center` |
| `.plist-time-hdr` | **`font-size:var(--t-label); font-weight:var(--w-bold); color:var(--amber)`**; `padding:var(--sp-1) var(--sp-3) var(--sp-1); background:var(--surf); border-top:1px solid var(--bdr); letter-spacing:.5px; position:sticky` — **sin border-bottom**. `background:var(--surf)` **requerido por `position:sticky`** — sin él el texto flota sobre posters al scrollear |

### 2.2 · `.int-item` — Intereses

| Clase | Propiedades canónicas |
|---|---|
| `.int-item` | `display:flex; align-items:flex-start; gap:var(--sp-3); padding:var(--sp-2) var(--sp-4); border-bottom:1px solid var(--bdr-l)` |
| `.int-item-poster` | `56×84; border-radius:var(--r-sm); background:var(--surf-2); flex-shrink:0` |
| `.int-item-info` | `flex:1; min-width:0` |
| `.int-item-title` | **`font-size:var(--t-base); font-weight:var(--w-bold); color:var(--white)`**; `margin-bottom:2px` |
| `.int-item-days` | `margin-bottom:2px; line-height:1.3` |
| `.int-item-meta` | **`font-size:var(--t-sm); font-weight:var(--w-thin); color:var(--gray)`**; `margin-bottom:var(--sp-1)` |
| `.int-item-sec` | **`font-size:var(--t-label); font-weight:var(--w-semi); color:var(--white-60)`**; `margin-bottom:var(--sp-1)` |
| `.int-item-actions` | `display:flex; flex-direction:column; align-items:center; align-self:center` |

### 2.3 · `#ag-result .saved-item` — **Planear** (plan calculado, variante `--plan-edit`)

> ⚠️ `.saved-item` se renderiza vía `mkAgendaRow` **solo en Planear** (`#ag-result`),
> NO en Mi Plan. Mi Plan usa `.mplan-row` (§2.5). Los valores abajo son los
> overrides scoped a `#ag-result`; la regla base `.saved-item` (sin scope) es legado.

| Clase | Propiedades canónicas (`#ag-result`) |
|---|---|
| `.saved-item` | `display:flex; align-items:flex-start; gap:var(--sp-3); padding:var(--sp-3) 0; border-bottom:none` (agrupa por día) |
| `.saved-time` (hora, dentro de `.saved-info`) | **`font-size:var(--t-md); font-weight:var(--w-bold); color:var(--amber)`**; `margin-bottom:2px; letter-spacing:normal` |
| `.saved-info` | `flex:1; min-width:0` |
| `.saved-title` | **`font-size:var(--t-base); font-weight:var(--w-bold); color:var(--white)`** |
| `.saved-venue` | **`font-size:var(--t-sm); font-weight:var(--w-thin); color:var(--gray)`**; `margin-top:2px` |
| `.lb-poster`/`-ph` | `56×84; border-radius:var(--r-sm)` |
| `.col-end` acciones | Cambiar (`.ag-fi-btn`, switch, gris) + Quitar (`.ag-fi-btn.del`, X, `color:var(--red); opacity:.7`) |
| `.ag-day-label` (day landmark) | `border-top:1px solid var(--bdr-l)` (separa días); `.first` sin border; nombre `t-md`/`w-semi`/`white` + `count-badge` |

### 2.5 · `.mplan-row` — **Mi Plan** (lista del día, variante `--plan-saved`)

> La lista del día vive **fuera** del card `.mplan-wrap` (que conserva solo el
> calendario semanal) → lista plana alineada con los otros tabs (poster a 16px).

| Clase | Propiedades canónicas |
|---|---|
| `.mplan-row` | `display:flex; align-items:flex-start; gap:var(--sp-3); padding:var(--sp-3) 0; border-bottom:none` (agrupa por día) |
| `.mplan-row.active` | `background:var(--amber-08)` (sin border-left que desplace) |
| `.mplan-ri` (info) | `flex:1; min-width:0` — contiene hora → endtime → título → venue |
| `.mplan-t1` (hora, tappable) | **`font-size:var(--t-md); font-weight:var(--w-bold); color:var(--amber)`**; `margin-bottom:2px`; **sin subrayado**; `data-action="toggleFilmAlternatives"` (Cambiar) |
| `.mplan-t2` (endtime/★/en curso) | `font-size:var(--t-xs); color:var(--gray2)` |
| `.mplan-rtitle` | **`font-size:var(--t-base); font-weight:var(--w-bold); color:var(--white)`** |
| `.mplan-rvenue` | **`font-size:var(--t-sm); color:var(--gray)`** |
| `.col-end` acción | Quitar (`.ag-fi-btn.del`, X) |
| `.mplan-list-hdr` (day landmark) | `align-items:baseline; justify-content:space-between; padding:var(--sp-2) 0`; sin borde (Mi Plan muestra un solo día); nombre `t-md`/`w-semi`/`white` (`.mplan-day-name`) + `count-badge` |

### 2.6 · Mecánica del offset de 16px

El poster queda a 16px del borde en los 4, pero la fuente del inset difiere:
- **Programa**: contenedor `.programa-list` flush (0) + item `padding-left:var(--sp-4)` = 16.
- **Intereses / Planear / Mi Plan**: viven dentro de `.ag-view` (`padding-x:var(--sp-4)` = 16); el item va flush (`padding-x:0`) y hereda los 16 del contenedor.
- Mi Plan: la lista se sacó del card `.mplan-wrap` para no sumar el borde del card al inset.

### 2.7 · `.mplan-wk-block` — Mi Plan, calendario semanal (EXCEPCIÓN — ver §5)

Bloque posicionado en absoluto sobre una timeline px-precisa, con fondo teñido.
**No sigue el canónico de listas planas** por su contexto de densidad.

| Clase | Propiedades (excepción documentada) |
|---|---|
| `.mplan-wk-block` | `position:absolute; padding:5px 6px 5px 10px` (raw, ver §5); `border-left:3px solid; border-radius:var(--r-md)`; fondo vía modificadores (`amber-10/-20/-06`, `event-blue-08`) |
| `.mplan-wk-time` | `font-size:var(--t-xs); color:var(--gray)` — gris sobre fondo amber-tinted (EXCEPCIÓN) |
| `.mplan-wk-title` | `font-size:var(--t-sm); font-weight:var(--w-semi); color:var(--white); line-height:1.3` |
| `.mplan-wk-venue` | `font-size:var(--t-xs); color:var(--gray); margin-top:3px` — `t-xs` (EXCEPCIÓN al `t-sm` canónico) |

---

## 3 · Decisiones de diseño aprobadas (canónicas)

Aprobadas por el PO. Ya reflejadas en §2 y aplicadas en `index.html`.

| # | Componente · propiedad | Canónico |
|---|---|---|
| 1 | `.plist-item` padding | `var(--sp-2) var(--sp-4)` (8/16) — paridad lateral con `.int-item` |
| 2 | `.plist-meta` | `gray` / `w-thin` 400 / `t-sm` 11px |
| 3 | `.plist-sec` | `t-label` 10px / `white-60` / `w-semi` (ya conforme — sin cambio) |
| 4 | `.int-item-meta` | `gray` / `w-thin` 400 / `t-sm` 11px |
| 5 | `.int-item-sec` | `t-label` 10px / `white-60` / `w-semi` (sube de `t-xs` a `t-label`) |
| 6 | `.saved-venue` | `gray` / `w-thin` 400 **explícito** / `t-sm` 11px |
| 7 | `.plist-poster` bg | `var(--surf-2)` (antes `surf-3`) — paridad con `.int-item-poster` |
| 8 | `.plist-time-hdr` | `background:var(--surf)` (requerido por `position:sticky`), sin `border-bottom`, `border-top:1px solid var(--bdr)`, `font-weight:var(--w-bold)` (700, antes 800) |
| 9 | `.mplan-wk-venue` | **EXCEPCIÓN** — contexto calendario denso, valores propios (`t-xs`) |
| 10 | `.mplan-wk-time` | **EXCEPCIÓN** — `gray` sobre fondo amber-tinted |

**Rationale del color secundario (`gray` #888 sobre `gray2` #555):** `#555` da
~2.7:1 de contraste sobre `--bg` → **falla WCAG AA** (mín. 4.5:1 para texto pequeño).
`#888` da ~5.6:1 → **pasa AA**. A 11px + peso 400, la legibilidad pesa más que el
de-énfasis extremo. Por eso el canónico de venue/meta es `gray`.

---

## 8 · Modernización visual (campaña 18 jul 2026)

Rediseño aprobado por el PO, en producción, cada pieza con su guardián ejecutable.

### 8.1 · Chrome de vidrio (`[chrome-glass]`)
El chrome (topbar + nav inferior) es **una lámina de vidrio translúcido**, no un
muro. `.topbar::before` y `.main-nav` (fixed) llevan `background:rgba(14,13,12,.5/.55)`
+ `backdrop-filter:blur(28px) saturate(200%)` → el contenido pasa como color
difuminado bajo el chrome. Reglas: **alpha ≤ 0.6** y `backdrop-filter` presente;
**cero `border` opaco** en las piezas del chrome (topbar, nav, mode-bar, nav-row,
hdr-ag, fs/pv/search headers). El chrome se separa por aire y jerarquía, no por líneas.

### 8.2 · Motion — sheets, skeletons, bloom (`[sheet-spring]`)
- **Sheets**: apertura `--sheet-in` (spring con mini-rebote), cierre `--sheet-out`
  (ease-in). Los 9 bottom-sheets suscritos; curva propia = build roto.
- **Skeletons**: `.poster-card`/`.plist-poster`/`.c-film-thumb` muestran un shimmer
  (`@keyframes poster-skel`, 8 ciclos, anulado por `prefers-reduced-motion`)
  mientras carga la imagen; la imagen hace fade-in encima.
- **Bloom ambiental**: el color de la ficha (§8.4) FLORECE con `--amb-o` (@property,
  transición .6s), no aparece de golpe; prewarm del muestreo en `pointerdown`.

### 8.3 · Color ambiental de la ficha (`[poster-ambient]`)
El header de la ficha respira el color dominante del póster. `posterAmbient()` en
`view/helpers.js` es el **ÚNICO sampler** (canvas 24×24, dominante por ÁREA
`sat×frecuencia` con piso .12, clamp sat ≤.55 / lum .30–.42 a la paleta). CORS
negado o data-URI → fallback al acento de sección. `getImageData` fuera de
helpers.js o `--amb` a mano = build roto. Safari iOS: muestrear con URL propia
(TMDB→w92) para no heredar la entrada de caché sin-CORS del `<img>`.

### 8.4 · Botones — regla dueña única (`[button-canon]`)
- **PRIMARIO**: UNA regla CSS dueña (amber sólido / negro / `--r-pill` / `--sp-btn`
  / `t-base` / `w-bold` / hover .88). 10 clases suscritas; un primario nuevo se
  SUMA al selector, no re-declara. `w-display` prohibido en botones.
- **CANCEL**: una regla dueña (texto `--gray` `t-sm` `w-semi`, sin caja).
- **Secundario/terciario**: outline pill 1px `--bdr`, texto informativo SIEMPRE
  `--gray` (nunca `gray2`), radio pill.
- **ESTADO ACTIVO**: clase `.on` ÚNICA — `.active`/`.selected` prohibidos.

### 8.5 · Iconos — ver `docs/ICONS.md`
Fuente única `ICONS` (`components.js`); `aria-hidden` de fábrica; escala icono ≈
texto (11 en t-label/t-xs, 13 base, 14–16 icon-only); stroke 1.75 universal;
`currentColor` (excepto ámbar de sec-hdr). Semántica: **★ = calificación**
(`[star-semantics]`), **🔖 bookmark = prioridad**, ♥ = interés, ✓ = visto.
**Días y horas NO llevan icono** (eje de tiempo, no categoría). Guardianes
`[icon-single-source]`, `[star-semantics]`.

### 8.6 · Divisorias — líneas solo funcionales
Divisoria decorativa (coronar sheets, separar zonas del chrome) = PROHIBIDA. Solo
sobreviven las **funcionales de lista** (`--bdr-l` entre ítems, con `:last-child`
sin borde): entre películas de un programa, opciones de menú, funciones sin
confirmar. Toda divisoria de lista usa `--bdr-l` (el tenue), nunca `--bdr`.

### 8.7 · Banderas de país (`[country-flags]`)
`countryToFlags()` parte por coma Y barra (no por guion: "Guinea-Bissau" es un
país). En festivales vivos, todo país debe producir bandera (mapeado en
`_COUNTRY_FLAGS` o campo `flags` autorizado) — nunca globo 🌍.

### 8.8 · Ficha — el título le hace sitio a la X (`sheet-close.spec.js`)
`.pel-sheet-title::before` es un espaciador flotante que reserva la esquina
sup-der (44px de la X de cerrar); el título largo envuelve alrededor en la 1ª
línea. Guardián mide el TEXTO real (Range) con título largo → solape con la X = 0.

### 8.10 · Transición de póster compartido — hero morph (`[poster-morph]`)
Al abrir la ficha desde un póster del grid, el póster **se transforma** en el de
la ficha (View Transitions API): morphea posición+forma+radio y **LLEGA desde
blur→foco + opacidad** (no salta — enfoca al aterrizar). El contenido de la ficha
entra con fade-up escalonado y el color ambiental (§8.3) florece sincronizado al
aterrizaje. Cableado en `main.js` (`_openPelMorph`, envuelve `openPelSheet` en
`startViewTransition`). **Degrada solo**: sin `startViewTransition` (Safari<18) o
`prefers-reduced-motion` → apertura normal con spring. Curva `cubic-bezier(.22,.61,.36,1)`.

### 8.11 · Elegir festival — muro de afiches en las DOS superficies (`[festival-chooser-canon]`)
Origen: feedback real de un usuario (20 jul 2026) — *"¿cómo vuelvo al menú donde
estaban los festivales?"*. Había **dos implementaciones de la misma decisión**: el
riel de afiches de la entrada y una lista de texto (miniaturas de 27px) en el sheet
→ no se reconocían como el mismo lugar.

- **Fuente única:** `_festivalCardHTML` (`view/components.js`) construye la card-afiche.
  La usan `_renderSplashRailHTML` (entrada) y `_renderFestivalSelectorHTML` (sheet).
  Lo ÚNICO que difiere es la acción: el splash **selecciona** (el usuario confirma con
  "Entrar"); el sheet **carga directo** (no hay confirmación).
- **Rótulo bajo cada afiche** (`.fs-fest-cap`): el muro solo no basta para escanear —
  quien no reconoce el póster necesita el nombre. Conserva la escaneabilidad de la
  lista sin volver a ella; el afiche sigue mandando la jerarquía.
  El rótulo usa el **nombre oficial completo** (`cfg.name`), NO el corto: bajo un
  afiche, `festivalShortName` truncaba al primer término ("Tribeca", "Leviza", "AFF").
  Tampoco `cfg.fullName` — el oficial largo no cabe. Mismo criterio que sentó Leviza:
  *"crece una línea pero es más claro"*. Card a 158px y rótulo hasta 3 líneas.
- **El header es un CONTROL, no un título:** nombre + chevron viven juntos dentro de
  `.hdr-fest-pill`; las fechas quedan **fuera**, como dato. Antes el nombre estaba
  tipografiado como título de pantalla y el chevron colgaba al otro extremo, pegado a
  las fechas → se leía como control de fecha. Sacar el chevron de la píldora revierte
  el problema (el guardián lo bloquea).

### 8.9 · Geometría FLUSH (`geometry.spec.js` G01)
El primer contenido de cada tab —y de la sub-vista TODO— arranca PEGADO al chrome
(gap ≤ 2px). Bandas de sección del grid full-bleed (±2px). Medición SIEMPRE en
viewport móvil 390×844.

---

## 4 · Reglas de derivación

Jerarquía tipográfica para **listas planas** (plist / int / saved):

| Rol | Color | Peso | Tamaño |
|---|---|---|---|
| **Primario** (título) | `--white` (#F0EDE8) | `--w-bold` (700) | `--t-base` (13px) |
| **Secundario** (venue/meta) | `--gray` (#888) | `--w-thin` (400) | `--t-sm` (11px) |
| **Terciario** (sección) | `--white-60` | `--w-semi` (600) | `--t-label` (10px) |

Reglas universales:
- **Texto primario:** `--white` siempre.
- **Texto secundario (venue/meta):** `--gray` / `--w-thin` / `--t-sm` — universal en
  listas planas. Peso **declarado explícito** (no heredar el default del browser).
- **Texto terciario (sección):** `--white-60` / `--w-semi` / `--t-label` — universal
  donde aplique.
- **Placeholder de póster:** `--surf-2` siempre (thumbnail principal de lista).
- **Separadores de hora:** `background:var(--surf)` (requerido por `position:sticky`
  — sin él el texto flota sobre posters al scrollear), `border-top:1px solid var(--bdr)`,
  sin `border-bottom`, `font-weight:var(--w-bold)`.

---

## 5 · Excepciones documentadas

Desviaciones **intencionales** del canónico, con razón explícita. Aprobadas por el PO.

| Componente | Desviación | Razón |
|---|---|---|
| `.mplan-wk-venue` | `t-xs` (9px) en vez del `t-sm` (11px) canónico | Bloque de calendario semanal denso: múltiples eventos en columnas estrechas con altura px-precisa. 11px desbordaría. |
| `.mplan-wk-time` | `color:var(--gray)` sobre fondo amber-tinted (no amber) | La hora ya está implícita en la posición vertical del bloque (timeline). El gris evita competir con el `border-left` de color de estado. |
| `.mplan-wk-block` | `padding:5px 6px 5px 10px` (valores raw) | Layout px-preciso sobre timeline absoluta; los tokens base-2 (8/12/16) no encajan en la densidad del calendario. Única excepción raw aprobada en componentes de lista. |
| `.plist-poster-stack .ps-back/.ps-front` | `background:var(--surf-3)` | Variante de póster apilado (programas con varios títulos); fondo del offset decorativo, **no** es el placeholder principal. **Pendiente de revisión del PO** si debe alinearse a `surf-2`. |

---

## 7 · Capitalización (sistema de 4 categorías)

Toda string de UI cae en una de 4 categorías. La capitalización se decide por
**ROL**, no por idioma — la misma key usa la misma categoría en es/en/pt.

| Categoría | Regla | Cuándo | Ejemplos |
|---|---|---|---|
| **ALLCAPS** | TODO MAYÚSCULAS | navegación (bottom nav), días abreviados, badges de estado | PROGRAMA · LUN · GRATIS · CANCELADA · REPROG. · AHORA · Q&A · EQUIPO PRESENTE |
| **Title Case** | Cada Palabra Mayúscula | nombres propios de la app, días largos, premieres | Tu Plan · Mi Plan · Intereses · Prioridades · Viernes · World Premiere |
| **Sentence case** | Solo Primera mayúscula | headers de sección, CTAs, descripciones, toasts, mensajes | Disponibilidad · Sugerencias · Añadir · "Tu plan puede estar desactualizado" |
| **minúscula** | todo minúscula | fragmentos que se concatenan en oraciones | min · anterior · función · "está en tu plan." |

### 7.1 · Distinción clave: metadata (ALLCAPS) vs headers de app (Title/Sentence)

La decisión de diseño (opción B) mantiene **dos lenguajes visuales** separados:

- **Metadata / estado / navegación** → **ALLCAPS**. Son etiquetas de sistema:
  badges (GRATIS, CANCELADA, PASADO), nav (PROGRAMA), días-chip (LUN), estado
  en vivo (AHORA, EN CURSO).
- **Headers de la app** → **NO ALLCAPS** (Title o Sentence). Son títulos de
  sección que el usuario lee como contenido: Disponibilidad, Sugerencias,
  Prioridades, Intereses, Tu Plan. Render vía `.sec-hdr` / `.int-section-hdr-lbl`
  — **sin** `text-transform`.

### 7.2 · Secciones de festival (caso especial)

Las **secciones del programa del festival** (Spotlight+, Gala, U.S. Narrative
Competition…) vienen del **JSON del festival**, no de i18n. Se muestran en
**ALLCAPS vía `text-transform:uppercase`** en CSS (`.carta-sr-section`,
`.poster-grid-sep`) — el string original conserva su capitalización editorial.
Esto las agrupa visualmente con la metadata sin alterar el dato fuente.

### 7.3 · Reglas de borde

- **"Plan" / "Mi Plan" / "Tu Plan"** son nombre propio → siempre Title Case,
  incluso dentro de oraciones y CTAs ("Calcular mi Plan", "Tu Plan aparece aquí").
- **Nombres de tab/sección** (Intereses, Prioridades, Sugerencias, Ya vistas,
  Programa) → Title Case incluso mid-sentence ("Se moverá a Ya vistas en Intereses").
- **Premieres** (World / International / U.S. / New York Premiere) → término de
  industria de festivales; **se mantiene en inglés en los 3 idiomas** (decisión
  intencional, no traducir).
- **Días**: cortos ALLCAPS (chips de nav: LUN/MON/SEG), largos Title Case
  (landmarks: Lunes/Monday/Segunda).
- **Badges con `·`**: la parte tras el símbolo sigue la regla del badge (ALLCAPS).
- **Labels del sheet header** (sinopsis/función/descripción): se guardan en
  **minúscula**; el CSS aplica `text-transform:uppercase` en el header del sheet.
  No capitalizar en la string.
- **Nombres de idioma** (`lang_es`="Español"): en su propio idioma, en los 3.
- **Badges "short"**: cuando un badge tiene variante corta para chips compactos
  (notice_reprog_short = "REPROG."), sigue siendo ALLCAPS como el full. No hay
  variante Title Case de un badge.

---

## 6 · Relación con CLAUDE.md

- `CLAUDE.md` → contrato de **arquitectura** (capas, patrones, reglas de proceso).
- `DESIGN.md` (este) → contrato **visual** (tokens, anatomía de componentes,
  jerarquía tipográfica).

Ambos son fuente de verdad. Ante un cambio visual, este documento manda; ante un
cambio estructural, manda CLAUDE.md.
