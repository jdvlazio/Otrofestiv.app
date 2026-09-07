# `_historico/` — scripts que ningún plan invoca

Acá vive lo que sirvió para montar un festival y **ya no forma parte del camino**.
La regla es mecánica y la vigila `[pipeline-huerfano]` en `validate.py`:

> Un `pipeline/<festival>-*.py` está vivo solo si algún `pipeline/*.plan.json`
> lo nombra en un `cmd`. Eso es literalmente lo que `correr.py` ejecuta.
> Lo demás se archiva acá.

La cita en un `_provenance` de `festivals/` **no** cuenta: es historia de cómo se
hizo el dato, no una invocación. Por eso están acá scripts que los JSON aún
mencionan.

**Se archiva, no se borra** (decisión de Juan, 5 sep 2026): el camino queda
limpio y el trabajo queda a mano. Para revivir uno, movelo de vuelta a
`pipeline/` y nombralo en el `plan.json` de su festival — si no lo nombrás, el
guardián lo devuelve acá.

Archivados el 5 sep 2026: 32 scripts (cinemancia-2026, ficdeh-2026, ficma-2026, qaff-2026, tiff-2026).
