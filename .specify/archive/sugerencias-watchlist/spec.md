# Spec — Sugerencias priorizan watchlist

## Problema
getSuggestions() ordena solo cronológicamente. Los títulos del watchlist
(Bloque 2) quedan mezclados con los de descubrimiento (Bloque 1) sin
jerarquía clara. Con watchlist grande (204 títulos), el usuario ve
sugerencias aleatorias del festival antes que sus propios intereses.

## Solución
1. Marcar cada sugerencia de Bloque 2 con `_isFromWL: true`
2. En el sort final: watchlist primero, luego cronológico
3. Limitar descubrimiento a 2 por hueco para no ahogar el watchlist

## Criterios de aceptación
- [ ] Sugerencias del watchlist aparecen antes que las de descubrimiento
- [ ] Dentro de watchlist: orden cronológico
- [ ] Dentro de descubrimiento: orden cronológico
- [ ] _isRestored (restaurar) siempre primero
- [ ] validate.py 10/10
- [ ] QA: con watchlist lleno, sugerencias empiezan por watchlist
