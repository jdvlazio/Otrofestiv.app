# Spec — Separadores de sección en Grid TODO

## Qué
En el Grid (modo TODO/ALL de Programa), añadir un separador visual entre grupos de sección para que el usuario pueda orientarse editorialmente mientras explora.

## Por qué
El Grid ya ordena por sección (SECTION_ORDER_LIST), pero sin separadores el límite entre secciones es invisible — especialmente cuando una sección termina en mitad de fila. El usuario no puede leer la estructura editorial del festival mientras scrollea.

## Comportamiento esperado
- Cada vez que cambia la sección en el grid, aparece una fila completa con el nombre de la sección
- El separador ocupa las 4 columnas del grid
- Es puramente orientacional: sin interacción, sin color de acción, sin sticky
- Solo visible en modo TODO (activeDay === 'all'). En modo día específico, el grid ya es pequeño y no lo necesita
- Solo visible en vista Grid (no en Lista — Lista tiene sus propios separadores de hora)

## Lo que NO es
- No es navegación ni filtro
- No usa amber (semántica de acción)
- No es sticky
- No replica el separador de hora de Lista

## Criterios de aceptación
- [ ] Separador visible entre cada sección en TODO
- [ ] Texto = nombre de sección sin emoji, uppercase, `--gray2`
- [ ] Span de 4 columnas completo
- [ ] Desaparece al activar filtro de día específico
- [ ] Sin regresiones en Lista, filtros de sección/venue, ni en otros festivales
