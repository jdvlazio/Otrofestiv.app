# La obra

> Aprobado por Juan, 24 nov 2026. La película es el insumo principal: única y
> verificada. El festival agrega la función y el lugar.

## Qué es de quién

| De la obra (una vez, en el almacén) | Del festival (cada función) |
|---|---|
| identidad, título original, dirección, año, países, género, sinopsis ES y EN, afiche, Letterboxd/TMDB | sección, día, hora, sede, sala, título impreso, duración de la copia, premiere, Q&A, entradas |

## La regla de cada campo

Un dato entra **por lista o por forma**, o no entra. Vacío es mejor que falso.
Dueño: `pipeline/ficha_obra.py`; guardián `[ficha-obra]`.

| Campo | Regla |
|---|---|
| País | Nombre de la lista ISO (`pipeline/paises.json`, con los de `NOMBRE`) separado por «, ». Históricos: URSS, Yugoslavia, Checoslovaquia |
| Género | **Uno**, de la lista cerrada de 21. VR e IA son formato, no género. No existen «Ficción», «Thriller» ni «Sátira» |
| Dirección | Nombres separados por «, »; sin cargos ni notas |
| Año | Número, el del primer estreno |
| Sinopsis ES | Cuenta la obra, en español, cierra la frase; corta: `[sinopsis-larga]` |
| Sinopsis EN | En inglés, cierra la frase, no habla del festival |
| Sinopsis ES y EN | Si hay una, está la otra: `[sinopsis-par]` |
| Duración | «N min» (es de la copia) |
| Letterboxd / TMDB | forma del slug / número |
| Afiche | archivo que existe |

Que sea el **mismo** en todos los festivales: `[obra-unica]`. Que sea **verdad**:
la identidad contra su fuente (en construcción, paso 2 y 3 del plan).

## El plan (24 nov 2026)

1. Reglas y guardianes por campo. 2. Identidad por identificador. 3. Tribeca e
identidades dudosas. 4. Limpiar país, género, dirección, año, duración. 5. Errores
de criterio, con hoja. 6. Sinopsis. 7. La obra como fuente. 8. Deshacer y
originales. 9. Prueba final: rearmar un festival terminado y comparar.

## Deshacer

Cada decisión de `catalogo/decisiones.json` guarda en `antes` lo que publicaba cada
festival, tal como lo escribía (texto, número o ruta; el `valor` puede ir en otra
forma, p. ej. ISO). Si publicaba dos valores, es una lista. Sin `antes`: la decisión
no reemplazó ningún valor o es anterior y no se pudo recuperar.
