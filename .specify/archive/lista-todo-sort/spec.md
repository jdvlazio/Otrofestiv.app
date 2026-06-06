# Spec — Lista/TODO: orden cronológico puro

## Qué
En _renderExploreLista() (Lista cuando activeDay==='all'), cambiar el sort
de tipo-primero a cronológico puro.

## Por qué
Lista es consulta operativa, no descubrimiento editorial. El usuario
necesita saber qué hay cuándo. El tipo ya es visible en cada ítem.
Agrupar por tipo en una lista es una decisión técnica, no de producto.

## Orden correcto
day_order → time → tipo (tipo solo como desempate de coincidencia exacta)

## Criterios de aceptación
- [ ] Lista/TODO ordena por day_order → time → tipo
- [ ] Films con múltiples funciones: posicionados por primera función (ya es así)
- [ ] Grid sin cambios
- [ ] Lista día específico sin cambios
