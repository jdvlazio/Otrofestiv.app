# catalogo/ — el catálogo único de obras

Diseño y reglas: [`docs/CATALOGO-OBRAS.md`](../docs/CATALOGO-OBRAS.md).
Esquema: [`esquema.json`](esquema.json). Lectura e invariantes: `pipeline/catalogo.py`.

| archivo | qué es |
|---|---|
| `obras/<id>.json` | una obra (lo invariante: título original, directores, año, país, sinopsis, afiche, xref, versiones) |
| `procedencia/<id>.json` | de dónde salió cada campo de esa obra |
| `decisiones.json` | decisiones humanas; ganan siempre, también las negativas («no es la misma obra») |
| `fusiones.json` | id absorbido → superviviente; un id nunca se borra |
| `candidatos.json` | pares de obras que pueden ser la misma, pendientes de Juan |
| `revision-fase2.json` | la primera revisión (12 oct): 4 reglas generales, 8 decisiones de identidad y 25 de datos, por título; se convierten en `decisiones.json` al asignar ids |

Fase 3a (12 oct 2026): materializado con `python3 pipeline/catalogo_construir.py --escribir`
(requiere TMDB_API_KEY; caché fuera del repo, en `~/.cache/otrofestiv/`). 2.133 obras desde 4.104
presentaciones de los festivales publicados; 28 decisiones; cada presentación resuelve a UNA obra
(`catalogo.obra_de`). Re-correrlo conserva los ids; si dos obras se reconocen como una, la absorbida
queda en `fusiones.json`. Los festivales todavía no llevan `work_id` (fase 3b).

Fase 3b (12 oct 2026): cada obra de cada festival lleva `work_id` (4.104). `publicar.py` lo pone al
publicar y avisa las obras que el catálogo no tiene; `[presentacion-con-obra]` frena el push hasta
sumarlas con `--escribir`. El enriquecido (`enriquecer.py` y `enriquecer_catalogo.py`) usa
`cascada_obra`: si el catálogo ya reconoce la obra (título + director + año) y tiene ficha TMDB, la toma
sin volver a buscar. Simulado contra lo publicado, cada obra contra el catálogo SIN su propio festival:
0 reconocidas como otra obra, 0 fichas TMDB en conflicto, 365 con la misma ficha y 289 que ganarían una.
