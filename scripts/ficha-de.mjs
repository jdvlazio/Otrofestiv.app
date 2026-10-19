// ficha-de.mjs <id-de-la-app> — imprime la FICHA de un festival (Etapa 2·B1):
// los campos de CAMPOS_FICHA tal como están en FESTIVAL_CONFIG (src/config.js).
// La usa pipeline/publicar-datos.py para publicarla al índice del almacén.
// Sale con 3 si el festival no está en la app (no hay ficha que publicar).
import { FESTIVAL_CONFIG } from '../src/config.js';
import { CAMPOS_FICHA } from '../src/fichas.js';
const id = process.argv[2];
const c = FESTIVAL_CONFIG[id];
if (!c) process.exit(3);
const f = {};
for (const k of CAMPOS_FICHA) if (c[k] !== undefined) f[k] = c[k];
process.stdout.write(JSON.stringify(f, null, 1) + '\n');
