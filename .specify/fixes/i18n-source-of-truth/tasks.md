# Tasks — Arreglo i18n (fuente de verdad + paridad)

Contexto: sync-i18n.py roto (apuntaba a _I18N en index.html, movido a
src/i18n/i18n.js en Fase 8). Runtime (i18n.js) era la fuente de verdad de facto;
JSONs desincronizados (39 keys solo en runtime). Auditoría → fix en 2 pasos.

## Paso 1 (PR #64) — neutralizar landmine
- [x] Borrar scripts/sync-i18n.py (regeneraba desde index.html; un "fix" ingenuo
      habría borrado las 39 keys solo-runtime → regresión).
- [x] CLAUDE.md (template): fuente de verdad i18n = src/i18n/i18n.js.
- [x] validate.py OK antes/después. No tocó runtime ni JSON.

## Paso 2 (este PR) — backfill + guardrail
- [x] 1. Identificar orphans comparando runtime vs JSON (39: auth/export/fs/label/
      misc/plan/splash). Valores es+en extraídos de i18n.js.
- [x] 2. Backfill de las 39 a i18n/es.json + en.json + strings-reference.json
      (append textual, sin reformatear el resto). 305→344 keys en es/en.json.
- [x] 3. validate.py [i18n-parity]: falla si una key está en ES y no en EN (o
      viceversa) dentro de src/i18n/i18n.js. Lee el runtime, no los JSON.
- [x] 4. Verificación: paridad es/en ya estaba OK (344/344) → check verde.
      Negative test: key fantasma inyectada → check falla; revertido → verde.
- [x] 5. validate.py 29/30 OK (warning único = tasks-sync pre-existente).

## Nota
Los JSON siguen siendo legacy NO consumido en runtime (el SW los cachea, nada
los lee). El backfill los deja completos como referencia/traducción; la fuente
de verdad sigue siendo i18n.js. No se reactivó ningún pipeline JSON→runtime.
