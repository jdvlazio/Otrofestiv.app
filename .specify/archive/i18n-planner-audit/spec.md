# Spec — Auditoría i18n: strings hardcodeados en español

## Qué
Toda string visible al usuario en la app que aparezca en español en modo EN.
El síntoma principal está en Planner, pero el problema toca también Programa y Mi Plan.

## Por qué
Cualquier string hardcodeada en ES rompe la experiencia EN para festivales internacionales
(Tribeca, futuros). La regla es absoluta: cero strings de UI fuera de `t()`.

## Alcance
23 strings identificadas en auditoría sistemática. Dos categorías:

### A — Claves existentes sin usar (5 strings)
Tienen clave en `en.json` pero el código usa texto hardcodeado en español.
Wire a `t()` sin tocar los JSON.

### B — Claves nuevas necesarias (18 strings)
No tienen clave. Requieren añadir a `es.json` + `en.json` + wiring en código.

## Criterio de aceptación
- [ ] Cambiar a EN: todas las strings de UI aparecen en inglés
- [ ] Cambiar a ES: todo sigue igual
- [ ] Sin regresiones en Planner, Mi Plan, Programa
- [ ] `validate.py` pasa

## Copy — todas las keys nuevas aprobadas antes de implementar
