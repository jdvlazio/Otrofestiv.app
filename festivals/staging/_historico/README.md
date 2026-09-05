# `staging/_historico/` — sidecars fuera del camino

Derivados que ningún paso vivo lee y que **no** son los canónicos del PROTOCOLO
(`-crudo`, `-correcciones`, `-build`, que son fuente aunque nadie los lea).

Se archivan y no se borran por coherencia con `pipeline/_historico/`: 29 de
estos 35 los nombra el script que los produjo o consumió, y ese script está
archivado, no borrado. Archivar la herramienta y tirar su dato deja las dos
mitades inservibles. Uno además está citado en el `_provenance` de
`festivals/ficdeh-2026.json`: es el rastro de cómo se armó un dato publicado.

`[staging-huerfano]` vigila que la carpeta de arriba solo tenga canónicos o
sidecars que un paso vivo lea; esta subcarpeta queda fuera de su recorrido, como
`pipeline/_historico/` queda fuera del suyo.
