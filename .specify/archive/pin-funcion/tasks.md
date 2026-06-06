# Tasks — Pin de función

> Estado de cierre. Diseño completo en `spec.md`; análisis en `ANALYSIS.md`.

## Mitad B — añadir función específica al Plan desde el sheet ✅ COMPLETA

Mergeada en **PR #175** (`feat(sheet): añadir función específica al Plan desde el pel-sheet`).

- [x] Botón "Añadir" por fila en el pel-sheet (`addSuggestion` con lógica add / swap / no-op)
- [x] Indicador "En tu Plan" (amber + check) en la función ya comprometida
- [x] Disponible desde las 4 tabs; conflicto resuelto vía `openConflictSheet`
- [x] No toca `schedule.js`, worker ni SW
- [x] i18n `plan_en_tu_plan` (es/en/pt); reusa `misc_anadir`
- [x] Tests Playwright AF01 (add) · AF02 ("En tu Plan") · AF03 (swap)

## Mitad A — restricción dura pre-generación (solver) — ⏸ DIFERIDA INDEFINIDAMENTE

**Mejora opcional, NO deuda.** El botón "Añadir" de Mitad B cubre el flujo dominante
(generar → ajustar la función en sitio, con protección de conflicto al editar).

Valor único que aportaría (no urgente): que la función elegida (a) **sobreviva una
regeneración completa** y (b) sea **restricción dura alrededor de la cual el solver
optimiza** el resto del Plan. Diagnóstico de cobertura: ver `ANALYSIS.md`/`spec.md`
(el solver `computeScenarios` lee `[...watchlist]`, es ciego a `savedAgenda`).

Requeriría tocar `src/domain/schedule.js` + el worker (`src/controller/calc.js`)
→ por eso quedó fuera del alcance durante Tribeca. **No se planifica ejecución**
salvo decisión explícita posterior. Diseño listo en `spec.md` §3 y §8.3.
