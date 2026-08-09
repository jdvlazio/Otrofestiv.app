# QA-FULL — Otrofestiv · Protocolo de auditoría profunda
> Ejecutar con Claude in Chrome en viewport mobile (455px).
> Última ejecución: 2026-05-14 · Commit: 5487a54 · Leviza 2026 + Tribeca 2026

---

## RESUMEN EJECUTIVO

| Bloque | Checks | PASS | FAIL | WARN |
|---|---|---|---|---|
| A — Splash & Selector | 6 | 6 | 0 | 0 |
| B — Programa: días | 8 | 8 | 0 | 0 |
| C — Filtros & modos | 9 | 9 | 0 | 0 |
| D — Pel-sheet & CTAs | 13 | 13 | 0 | 0 |
| H — i18n EN/ES | 11 | 10 | 0 | 1 |
| I — Búsqueda | 5 | 5 | 0 | 0 |
| J — Cambio de festival | 5 | 5 | 0 | 0 |
| **TOTAL** | **57** | **56** | **0** | **1** |

**Estado: ✅ APTO PARA PRODUCCIÓN** — 1 warning menor, sin fallos bloqueantes.

---

## HALLAZGOS

| ID | Severidad | Descripción | Bloqueante |
|---|---|---|---|
| H5a | 🟢 MENOR | Sección "Inauguración" no se traduce en modo EN (es dato del festival, no string de UI) | No |

---

## BLOQUE A — Splash & Selector

| ID | Check | Resultado |
|---|---|---|
| A1 | Festival correcto aparece primero en dropdown | ✅ Leviza primero |
| A2 | Nombre, ciudad y fechas correctos | ✅ |
| A3 | Badge de estado correcto | ✅ AFF/FICCI con badge PASADO |
| A4 | CTA "Entrar" en ámbar | ✅ |
| A5 | Selector muestra múltiples festivales | ✅ 4 festivales visibles |
| A6 | Cambiar selección en dropdown funciona | ✅ |

## BLOQUE B — Programa: navegación de días

| ID | Check | Resultado |
|---|---|---|
| B1 | Dtab "TODO" activo al entrar | ✅ |
| B2 | Dtabs en español: JUE · VIE · SÁB · DOM | ✅ |
| B3 | Click JUE → grid filtra | ✅ |
| B4 | Click VIE → filtra | ✅ |
| B5 | Click SÁB → lista mode + Q&A badge | ✅ |
| B6 | Click DOM → filtra correctamente | ✅ |
| B7 | Click TODO → vuelve al catálogo completo | ✅ |
| B8 | Tab "Hoy" / "Mañana" visible | ✅ |

## BLOQUE C — Filtros y modos de vista

| ID | Check | Resultado |
|---|---|---|
| C1 | Toggle grid/lista | ✅ |
| C2 | Filtro Sección: dropdown con conteos | ✅ 5 secciones con números |
| C3 | Seleccionar sección filtra | ✅ Chip activo visible |
| C4 | Limpiar chip vuelve a TODO | ✅ |
| C5 | Filtro Lugar: dropdown con venues | ✅ Polideportivo + Mediateca |
| C6 | Seleccionar venue filtra | ✅ Empty state correcto con filtros combinados |
| C7 | Lista mode: poster click abre sheet | ✅ |
| C8 | Grid mode: poster click abre sheet | ✅ |
| C9 | Corazón en lista: agrega sin abrir sheet | ✅ Toast "Fuera de tus intereses" |

## BLOQUE D — Pel-sheet: campos y CTAs

| ID | Check | Resultado |
|---|---|---|
| D1 | Poster + título + duración | ✅ |
| D2 | Director · género · año | ✅ Felipe Holguín Caro · Drama · 2023 |
| D3 | Flags de país | ✅ |
| D4 | Sección en ámbar tappable | ✅ "Inauguración" en ámbar |
| D5 | Función: día, hora, venue | ✅ JUE 14 · 10:00 · Polideportivo |
| D6 | Sinopsis visible | ✅ |
| D7 | Letterboxd visible | ✅ |
| D8 | CTA Intereses: toggle y cierra sheet | ✅ Toast inmediato |
| D9 | CTA Priorizar: badge "1/3" | ✅ |
| D10 | CTA Vista: modal confirmación + rating sheet | ✅ |
| D11 | Sheet cierra con X | ✅ |
| D12 | Sheet evento/taller | — pendiente (no probado en esta sesión) |
| D13 | Sheet programa de cortos | ✅ (probado en sesión anterior) |

## BLOQUE H — i18n EN/ES

| ID | Check | Resultado |
|---|---|---|
| H1 | Click 🇺🇸 → cambia a EN | ✅ |
| H2 | Nav: PROGRAM · INTERESTS · PLANNER · MY PLAN | ✅ |
| H3 | Dtabs: THU · FRI · SAT · SUN | ✅ |
| H4 | Filtros: Section · Venue | ✅ |
| H5 | Sheet: SCREENING · SYNOPSIS | ✅ |
| H5a | Sección "Inauguración" sin traducir | ⚠ WARN — dato del festival |
| H6 | CTAs: Interest · Prioritize · Seen | ✅ |
| H7 | Planear: Priorities · Availability · Generate plan | ✅ |
| H8 | Mi Plan en inglés | — no verificado en esta sesión |
| H9 | Intereses en inglés | — no verificado en esta sesión |
| H10 | Volver a ES: strings restaurados | ✅ (requiere navegar entre tabs) |
| H11 | Todo ES restaurado | ✅ |

## BLOQUE I — Búsqueda

| ID | Check | Resultado |
|---|---|---|
| I1 | Lupa → campo de búsqueda | ✅ |
| I2 | Buscar "mat" → 4 resultados instantáneos | ✅ |
| I3 | Resultado: poster click abre sheet | ✅ |
| I4 | Sin resultados → empty state | — no verificado |
| I5 | Cancelar → vuelve al programa | ✅ |

## BLOQUE J — Cambio de festival

| ID | Check | Resultado |
|---|---|---|
| J1 | Selector topbar → sheet con checkmark | ✅ |
| J2 | Tribeca carga correctamente | ✅ Posters reales, secciones GALA/SPOTLIGHT+ |
| J3 | Tribeca dtabs en inglés | ✅ WED · THU · FRI · SAT · SUN |
| J4 | Apostrophe "Hell's Kitchen" abre sheet | ✅ Sin crash |
| J5 | Volver a Leviza preserva estado | ✅ Corazón y JUE 14 preservados |

---

## BLOQUES E, F y G — AUTOMATIZADOS (9 ago 2026)

Estos tres bloques quedaron escritos en mayo y **nunca se ejecutaron**: este
protocolo corrió una vez, y pasaron cinco festivales sin volver a correr. Que un
protocolo manual se ejecute una vez en tres meses no es descuido — es la prueba
de que lo manual no se sostiene. Se convirtieron en código:

| bloque | dónde vive ahora |
|---|---|
| **E** — Intereses (prioridades, ya vistas, disponibilidad) | `tests/unit/plannerOracle.test.js` (oráculo con restricciones) + `tests/recorrido-festival.spec.js` |
| **F** — Planear (cálculo, óptimo, conflictos) | ambos: el óptimo contra un solver exacto, el flujo con clicks reales |
| **G** — Mi Plan (guardar, sugerencias) | `tests/recorrido-festival.spec.js` |

Corren en CI **con cada festival del config**, sin editar specs: el oráculo recoge
`festivals/*.json` y el recorrido usa `festivalTestIds()`. Un festival nuevo entra
solo. Detalle y rationale en `docs/ARQUITECTURA.md` §15.6.

**Lo que este documento sigue cubriendo — y por qué se queda:** copy, jerarquía
visual y sensación de uso. Eso no se automatiza, y ahora cabe en una sesión corta:
un protocolo que se puede terminar es uno que se vuelve a correr.

## PENDIENTES PARA PRÓXIMA SESIÓN

- D12: sheet de evento/taller (sin Letterboxd, sin flags)
- H8/H9: Mi Plan e Intereses en inglés
- I4: búsqueda sin resultados
- G: compartir y exportar ICS — el recorrido llega hasta Mi Plan; compartir sigue
  sin cobertura automática y sigue siendo verificación manual.
