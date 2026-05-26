#!/usr/bin/env node
/**
 * generate-claude-md.js — Genera CLAUDE.md leyendo el estado real del repo.
 *
 * Fuentes de verdad:
 *   - FESTIVAL_CONFIG en index.html → lista de festivales
 *   - .specify/features/            → features activas
 *   - git log -1                    → último commit
 *
 * Uso: node scripts/generate-claude-md.js
 * Se ejecuta automáticamente desde bump-version.js antes de cada deploy.
 */

const fs   = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const ROOT = path.join(__dirname, '..');

// ── 1. Último commit ──────────────────────────────────────────────────────────
let lastCommit = '(desconocido)';
try {
  lastCommit = execSync('git log --oneline -1', { cwd: ROOT }).toString().trim();
} catch (_) {}

// ── 2. Festivales desde FESTIVAL_CONFIG ───────────────────────────────────────
// p8 Step 0: FESTIVAL_CONFIG se movió de index.html a src/main.js (módulo).
// p8 Step 1: FESTIVAL_CONFIG se movió a src/config.js (`export const`); el regex
//   `const FESTIVAL_CONFIG={...};// Festival` matchea igual dentro del export.
const _configPath = path.join(ROOT, 'src', 'config.js');
const _mainPath    = path.join(ROOT, 'src', 'main.js');
const indexHtml = fs.existsSync(_configPath)
  ? fs.readFileSync(_configPath, 'utf8')
  : fs.existsSync(_mainPath)
    ? fs.readFileSync(_mainPath, 'utf8')
    : fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

const configBlock = indexHtml.match(/const FESTIVAL_CONFIG=\{([\s\S]*?)\};\/\/ Festival/);
const festivals = [];

if (configBlock) {
  // Extraer cada entrada: 'id':{ name:'...', city:'...', dates:'...', festivalEndStr:'...' }
  const entryRe = /'([a-z0-9]+)':\s*\{([^}]+)\}/g;
  let m;
  while ((m = entryRe.exec(configBlock[1])) !== null) {
    const id    = m[1];
    const block = m[2];
    const get   = (key) => { const r = block.match(new RegExp(key + ":'([^']+)'")); return r ? r[1] : ''; };
    festivals.push({
      id,
      name:         get('name'),
      city:         get('city'),
      dates:        get('dates'),
      festivalEndStr: get('festivalEndStr'),
    });
  }
}

// Determinar estado de cada festival
const now = new Date();
function festivalStatus(f) {
  if (!f.festivalEndStr) return 'desconocido';
  const end = new Date(f.festivalEndStr);
  const diffDays = (end - now) / (1000 * 60 * 60 * 24);
  if (diffDays < -30)  return 'Archivado';
  if (diffDays < 0)    return 'Recién terminado';
  if (diffDays < 60)   return '**Próximo / activo**';
  return 'En desarrollo';
}

const festivalsTable = [
  '| ID | Nombre | Ciudad | Fechas | Estado |',
  '|---|---|---|---|---|',
  ...festivals.map(f =>
    `| \`${f.id}\` | ${f.name} | ${f.city} | ${f.dates} | ${festivalStatus(f)} |`
  )
].join('\n');

// ── 3. Features desde .specify/features/ ─────────────────────────────────────
const featuresDir = path.join(ROOT, '.specify', 'features');
let featuresSection = '_Sin features activas en `.specify/features/`._';

if (fs.existsSync(featuresDir)) {
  const entries = fs.readdirSync(featuresDir)
    .filter(e => {
      const full = path.join(featuresDir, e);
      return fs.statSync(full).isDirectory();
    });

  if (entries.length > 0) {
    featuresSection = entries.map(e => {
      const featureDir = path.join(featuresDir, e);
      const files = fs.readdirSync(featureDir);
      const has = (f) => files.includes(f);
      const phase = has('tasks.md') ? 'tasks' : has('plan.md') ? 'plan' : has('spec.md') ? 'spec' : 'vacío';
      return `- \`${e}/\` — fase actual: **${phase}**`;
    }).join('\n');
  }
}

// ── 4. Generar CLAUDE.md ──────────────────────────────────────────────────────
const generated = `# CLAUDE.md — Otrofestiv
> Generado automáticamente por \`scripts/generate-claude-md.js\`.
> No editar a mano — los cambios se sobreescriben en el próximo deploy.
> Para modificar secciones estáticas, editar el template en el script.
>
> Último commit: \`${lastCommit}\`

---

## Qué es Otrofestiv

PWA mobile-first para planear asistencia a festivales de cine. Permite explorar el programa, armar una watchlist, detectar conflictos de horario y generar un plan optimizado. Vanilla JS/HTML sin dependencias externas; la app se carga como módulo ES desde \`src/main.js\` vía \`index.html\` (en migración a módulos por capas — Fase 8). Desplegado en GitHub Pages.

- **Repo:** \`jdvlazio/Otrofestiv.app\`
- **URL producción:** \`https://otrofestiv.app\`
- **Deploy:** drag-and-drop manual en GitHub web interface

---

## Bootstrap de sesión

\`\`\`bash
git clone https://<GITHUB_TOKEN>@github.com/jdvlazio/Otrofestiv.app.git /home/claude/repo \\
  && cd /home/claude/repo \\
  && git config user.email "claude@anthropic.com" \\
  && git config user.name "Claude"
\`\`\`

Después del clone, leer en este orden:
1. Este archivo (\`CLAUDE.md\`)
2. \`docs/ARQUITECTURA.md\` — diseño, reglas, componentes, patrones
3. Si el trabajo involucra datos de festival: \`docs/SCHEMA.md\`
4. Si el trabajo involucra onboarding de un festival nuevo: \`docs/PIPELINE.md\`

---

## Protocolo de trabajo con Juan

Juan es Product Owner, diseñador y developer. Claude ejecuta; Juan audita y aprueba.

**Reglas inamovibles del proceso:**

1. **Arquitectura antes de ejecución.** Toda decisión no trivial requiere propuesta + aprobación antes de tocar código.
2. **Cambios quirúrgicos.** Solo se modifica lo pedido. Cero modificaciones no solicitadas.
3. **Copy es un artefacto de diseño.** Toda nueva string o corrección requiere discusión semántica con Juan como Content Designer + UX Writer. Sin excepciones.
4. **Validar antes de commitear.** Siempre correr \`python3 validate.py\` antes de proponer un commit.
5. **bump-version antes de deploy.** \`node scripts/bump-version.js\` justo antes de cada push.
6. **Sin regresiones.** Verificar qué cambió y por qué después de cada entrega.

---

## Estado del proyecto

### Festivales (desde \`FESTIVAL_CONFIG\` en \`src/config.js\`)

${festivalsTable}

### Features activas (desde \`.specify/features/\`)

${featuresSection}

---

## Documentación de referencia

| Archivo | Qué contiene |
|---|---|
| \`docs/ARQUITECTURA.md\` | Design system completo, reglas de diseño, mapa de funciones, patrones canónicos |
| \`docs/PIPELINE.md\` | Proceso de onboarding de festivales nuevos (fases, gates, roles) |
| \`docs/SCHEMA.md\` | Schema normativo del JSON de festival |
| \`.specify/memory/constitution.md\` | Rationale de decisiones de arquitectura clave |
| \`.specify/features/\` | Specs y planes de features en desarrollo |
| \`validate.py\` | Validador: JS syntax, divs críticos, CSS, patrones prohibidos |

---

## Reglas críticas (resumen — ver \`docs/ARQUITECTURA.md\` para detalle)

- **CTA primario:** fondo amber sólido, texto negro. Siempre.
- **Pósters:** solo vía \`getFilmPoster(f)\` o \`getCortoItemPoster(item)\`. Nunca directo.
- **Iconos:** solo Lucide. Flags de países y emojis de categoría son la única excepción.
- **Conflictos de horario:** siempre \`screensConflict()\`. Nunca comparaciones manuales.
- **Tokens:** todo valor de spacing, tipografía y radio usa \`var(--)\`. Cero valores raw.
- **Regex en index.html:** prohibido para transformaciones estructurales de >10 ocurrencias.
- **Timezone:** Colombia (UTC-5). Nunca \`toISOString()\` para lógica de fechas.
- **i18n:** la fuente de verdad es \`src/i18n/i18n.js\` (bloque \`_I18N\`, es+en). Toda string nueva va ahí — es lo que lee \`t()\` y lo que valida \`validate.py [i18n-complete]\`. Los \`i18n/*.json\` quedaron desincronizados y NO se consumen en runtime (legacy); no son la fuente. El \`sync-i18n.py\` fue retirado (apuntaba a un \`_I18N\` en \`index.html\` que la Fase 8 movió a \`src/i18n/i18n.js\`).
- **Splash placeholder:** el markup estático de \`#splash-sel-name\`/\`#splash-sel-meta\` en \`index.html\` debe reflejar el festival activo actual (= \`detectActiveFest()\`/\`_DEFAULT_FEST_ID\`). Es solo placeholder pre-JS, pero si queda stale el selector "brinca" del festival viejo al detectado al cargar. **Actualizarlo en cada cambio de festival activo.**

---

## APIs

- **TMDB:** \`$TMDB_API_KEY\` (variable de entorno — nunca hardcodeada)
- **GitHub token:** en el bootstrap command de arriba

---

## Android APK (Play Store)

- **Track:** Closed testing — Alpha
- **versionCode actual:** 3 (subido MAY 14, 2026)
- **Próximo versionCode:** **4** — nunca reutilizar un code ya publicado
- **server.url:** \`https://otrofestiv.app\` — la app carga desde producción, no desde bundle local
- **Para compilar:** Android Studio → Build → Generate Signed Bundle → versionCode en \`android/app/build.gradle\`
- **Para subir:** Play Console → Testing → Closed testing → Alpha → Create new release

---

## CI — GitHub Actions

- **bump-and-validate.yml:** solo corre \`python3 validate.py\`. El bump de versión es responsabilidad local — correr \`node scripts/bump-version.js\` antes de cada push.
- **playwright.yml:** tests de regresión T01–T10, viewport 390×844 (iPhone 14), simTime frozen para festivales activos.
- **promote-ios.yml:** workflow manual para promover \`version.json.android → .ios\` (staged rollout).

---

## Herramientas del pipeline

\`\`\`bash
python3 validate.py                        # validar antes de commitear
node scripts/bump-version.js               # actualizar sw.js + version.json + CLAUDE.md antes de deploy
node scripts/generate-config.js --help     # generar entrada FESTIVAL_CONFIG
python3 scripts/enrich-festival.py --help  # enriquecer JSON con TMDB
python3 scripts/geocode-venues.py --help   # geocodificar venues
\`\`\`
`;

fs.writeFileSync(path.join(ROOT, 'CLAUDE.md'), generated);
console.log('✅ CLAUDE.md generado.');
console.log(`   Festivales: ${festivals.length}`);
console.log(`   Último commit: ${lastCommit}`);
