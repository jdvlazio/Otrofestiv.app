# Spec — Títulos truncados en header Mi Plan + Planner chips

## Problema
JS hardcodea slices agresivos (14-16 chars) antes de que el CSS
pueda manejar el overflow. Resultado: "Opening Night: E..." en vez
de mostrar todo el texto posible dado el espacio real disponible.

## Causa
slice(0,14) y slice(0,16) no tienen en cuenta el ancho real del
contenedor. El CSS ya tiene text-overflow:ellipsis (ctx-prio-name)
y -webkit-line-clamp:2 (prio-chip-title) que manejan el overflow
correctamente sin necesitar corte en JS.

## Fix
- ctx-prio-chip (Mi Plan header): eliminar slice → CSS ellipsis
- prio-chip-title (Planner strip): subir límite 14→22 chars 
  (line-clamp:2 permite más texto, 2 líneas)
- ctx-prio-name en Planner contextual (L6478): eliminar slice → CSS
- Misma lógica para todas las variantes de truncado en Mi Plan

## Criterios
- [ ] "Opening Night: Alicia Keys" visible sin corte artificial
- [ ] Planner chips muestran 2 líneas completas
- [ ] Sin overflow visual (CSS ya lo maneja)
- [ ] Aplica en todos los festivales
