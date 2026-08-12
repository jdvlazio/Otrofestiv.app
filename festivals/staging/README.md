# festivals/staging/ — catálogos en pre-onboarding (Etapa A)

Festivales cuyo CATÁLOGO ya se extrajo pero cuya PROGRAMACIÓN aún no existe
(el onboarding en dos etapas: CATÁLOGO → CONEXIÓN, ver docs/PIPELINE.md).

Los validadores (validate.py y validate-festivals.js) escanean SOLO la raíz de
festivals/ — a propósito: sus gates juzgan festivales completos (config, días,
funciones, arquetipos), y un catálogo staged los reprobaría todos por diseño.
Al conectar la programación (Etapa B), el JSON se completa y SE MUEVE a
festivals/ — ahí los gates lo juzgan como bloqueantes normales.

NADA de este directorio se publica: sin entrada en FESTIVAL_CONFIG no existe
para la app.
