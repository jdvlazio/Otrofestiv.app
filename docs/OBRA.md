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

**Tres sinopsis por obra:** la original (`catalogo/originales.json`: texto, idioma y
fuente; no se edita), la corta en español y la corta en inglés. Que sean de ESA
película: `[sello-obra]`. El sello lo comprueba una máquina (`pipeline/sello_fuente.py`): el
original tiene que estar letra por letra en su fuente, y la fuente tiene que ser de esa obra
(su ficha de TMDB, o su título o su dirección cerca del texto). El almacén no es fuente de sí
mismo. Lo publicado de cada obra es lo que dice la obra: `[obra-al-dia]` (el legado, solo baja).
Las listas de lo pendiente no crecen a mano: `[deuda-solo-baja]` las compara con main.
Dónde se busca la fuente de una sinopsis lo decide el código (`pipeline/buscar_sinopsis.py`:
fuentes guardadas, Instagram guardado, TMDB, Letterboxd, IMDb, web oficial, Filmaffinity y
consultas web fijas) y queda escrito en `catalogo/busquedas/`. Una obra se declara sin fuente
(`catalogo/sin-fuente.json`) solo con la búsqueda completa: `[busqueda-completa]`.

Que sea el **mismo** en todos los festivales: `[obra-unica]`. Que sea **verdad**:
la identidad contra su fuente (en construcción, paso 2 y 3 del plan).

## El plan (24 nov 2026)

1. Reglas y guardianes por campo. 2. Identidad por identificador. 3. Tribeca e
identidades dudosas. 4. Limpiar país, género, dirección, año, duración. 5. Errores
de criterio, con hoja. 6. Sinopsis. 7. La obra como fuente. 8. Deshacer y
originales. 9. Prueba final: rearmar un festival terminado y comparar.

## Deshacer

Cada decisión de `catalogo/decisiones/` guarda en `antes` lo que publicaba cada
festival, tal como lo escribía (texto, número o ruta; el `valor` puede ir en otra
forma, p. ej. ISO). Si publicaba dos valores, es una lista. Sin `antes`: la decisión
no reemplazó ningún valor o es anterior y no se pudo recuperar.

## La obra es la fuente (paso 7)

En un festival nuevo, dirección, año, país, género, sinopsis, afiche, TMDB y Letterboxd
salen de `catalogo/decisiones/`; el festival pone la función y el lugar. El JSON que
lee la app se publica completo, pero se arma: `pipeline/obra_fuente.py`. Guardián
`[obra-fuente]`. Los festivales anteriores están en `catalogo/obra-fuente-legado.json`
(solo baja); sus obras se revisan cuando vuelvan en un festival nuevo.

Echar atrás una decisión: `python3 pipeline/deshacer.py <work_id> <campo> --escribir`.
Sellar exige el original guardado (`sello_obra.py --original`).
