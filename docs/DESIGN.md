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
| `--r-sheet` | 20px |
| `--r-handle` | 2px |
| `--r-pill` | 999px |

### Color — superficies
| Token | Valor |
|---|---|
| `--bg` | #0A0A0A |
| `--surf` | #141414 |
| `--surf-2` | #1A1A1A |
| `--surf-3` | #1F1F1F |
| `--card-a` | #1E1E1E |
| `--card-b` | #232323 |
| `--card-p` | #141414 |

### Color — bordes (dos niveles semánticos)
| Token | Valor | Uso |
|---|---|---|
| `--bdr` | #2A2A2A | chrome estructural: nav, headers, separadores fuertes |
| `--bdr-l` | #1E1E1E | separación de contenido: filas de lista |

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

### Pósters (ratio 2:3)
| Token | Dimensión | Uso |
|---|---|---|
| `--poster-xs-w/h` | 56×84 | thumbnail de lista (Programa, Mi Plan, Planear) |
| `--poster-md-w/h` | 72×108 | chip standalone (prio strip) |
| `--poster-lg-w/h` | 96×144 | card descubrimiento / sheet |

### Fuente
`--font: 'Plus Jakarta Sans', sans-serif;` (con fallback calibrado `Plus Jakarta Sans Fallback`).

---

## 2 · Componentes de lista — anatomía canónica

Cuatro componentes muestran la misma información (título / venue·duración /
sección / hora) en contextos distintos. Valores **canónicos aprobados**:

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
| `.plist-time-hdr` | **`font-size:var(--t-label); font-weight:var(--w-bold); color:var(--amber)`**; `padding:var(--sp-1) var(--sp-3) var(--sp-1); border-top:1px solid var(--bdr); letter-spacing:.5px; position:sticky` — **sin background, sin border-bottom** |

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

### 2.3 · `.saved-item` — Mi Plan (lista)

| Clase | Propiedades canónicas |
|---|---|
| `.saved-item` | `display:flex; align-items:center; gap:var(--sp-2); padding:var(--sp-3) 0; border-bottom:1px solid var(--bdr-l)` |
| `.saved-time` | `font-size:var(--t-md); color:var(--amber); letter-spacing:.5px; min-width:40px` |
| `.saved-info` | `flex:1; min-width:0` |
| `.saved-title` | **`font-size:var(--t-base); font-weight:var(--w-bold); color:var(--white)`**; `line-height:1.3` |
| `.saved-venue` | **`font-size:var(--t-sm); font-weight:var(--w-thin); color:var(--gray)`** (peso declarado explícito); `margin-top:1px` |

> `.saved-item` usa `align-items:center` y `gap:var(--sp-2)` por su layout (hora a la
> izquierda como columna fija). El padding lateral es `0` porque vive dentro de un
> contenedor con padding propio. No se considera desviación del canónico de texto.

### 2.4 · `.mplan-wk-block` — Mi Plan, calendario semanal (EXCEPCIÓN — ver §5)

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
| 8 | `.plist-time-hdr` | sin `background`, sin `border-bottom`, `border-top:1px solid var(--bdr)`, `font-weight:var(--w-bold)` (700, antes 800) |
| 9 | `.mplan-wk-venue` | **EXCEPCIÓN** — contexto calendario denso, valores propios (`t-xs`) |
| 10 | `.mplan-wk-time` | **EXCEPCIÓN** — `gray` sobre fondo amber-tinted |

**Rationale del color secundario (`gray` #888 sobre `gray2` #555):** `#555` da
~2.7:1 de contraste sobre `--bg` → **falla WCAG AA** (mín. 4.5:1 para texto pequeño).
`#888` da ~5.6:1 → **pasa AA**. A 11px + peso 400, la legibilidad pesa más que el
de-énfasis extremo. Por eso el canónico de venue/meta es `gray`.

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
- **Separadores de hora:** sin background, `border-top:1px solid var(--bdr)`,
  `font-weight:var(--w-bold)`.

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

## 6 · Relación con CLAUDE.md

- `CLAUDE.md` → contrato de **arquitectura** (capas, patrones, reglas de proceso).
- `DESIGN.md` (este) → contrato **visual** (tokens, anatomía de componentes,
  jerarquía tipográfica).

Ambos son fuente de verdad. Ante un cambio visual, este documento manda; ante un
cambio estructural, manda CLAUDE.md.
