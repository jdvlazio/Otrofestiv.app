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

Fase 0 (12 oct 2026): vacío a propósito. La fase 1 lo construye desde los festivales publicados.
