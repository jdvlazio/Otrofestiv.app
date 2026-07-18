# CLAUDE.md — Otrofestiv
> Generado automáticamente por `scripts/generate-claude-md.js`.
> No editar a mano — los cambios se sobreescriben en el próximo deploy.
> Para modificar secciones estáticas, editar el template en el script.
>
> Último commit: `d37f6f2 feat(recuerdo)+design(hdr-C): Modo Recuerdo por obra + Compartir mi festival + Prioridades fuera de Planear + encabezados a banda (estilo C)`

---

## Qué es Otrofestiv

PWA mobile-first para planear asistencia a festivales de cine. Permite explorar el programa, armar una watchlist, detectar conflictos de horario y generar un plan optimizado. Vanilla JS/HTML sin dependencias externas; la app se carga como módulo ES desde `src/main.js` vía `index.html` (en migración a módulos por capas — Fase 8). Desplegado en GitHub Pages.

- **Repo:** `jdvlazio/Otrofestiv.app`
- **URL producción:** `https://otrofestiv.app`
- **Deploy:** automático — GitHub Pages sirve la raíz de `main` (build legacy). Cada push/merge a `main` dispara el deploy. No hay paso manual.

---

## Bootstrap de sesión

```bash
git clone https://<GITHUB_TOKEN>@github.com/jdvlazio/Otrofestiv.app.git /home/claude/repo \
  && cd /home/claude/repo \
  && git config user.email "claude@anthropic.com" \
  && git config user.name "Claude"
```

Después del clone, leer en este orden:
1. Este archivo (`CLAUDE.md`)
2. `docs/ARQUITECTURA.md` — diseño, reglas, componentes, patrones
3. Si el trabajo involucra datos de festival: `docs/SCHEMA.md`
4. Si el trabajo involucra onboarding de un festival nuevo: `docs/PIPELINE.md`

---

## Protocolo de trabajo con Juan

Juan es Product Owner, diseñador y developer. Claude ejecuta; Juan audita y aprueba.

**Reglas inamovibles del proceso:**

1. **Arquitectura antes de ejecución.** Toda decisión no trivial requiere propuesta + aprobación antes de tocar código.
2. **Cambios quirúrgicos.** Solo se modifica lo pedido. Cero modificaciones no solicitadas.
3. **Copy es un artefacto de diseño.** Toda nueva string o corrección requiere discusión semántica con Juan como Content Designer + UX Writer. Sin excepciones.
4. **Validar antes de commitear.** Siempre correr `python3 validate.py` antes de proponer un commit.
5. **bump-version antes de deploy.** `node scripts/bump-version.js` justo antes de cada push.
6. **Sin regresiones.** Verificar qué cambió y por qué después de cada entrega.

---

## Estado del proyecto

### Festivales (desde `FESTIVAL_CONFIG` en `src/config.js`)

| ID | Nombre | Ciudad | Fechas | Estado |
|---|---|---|---|---|
| `ficci65` | FICCI 65 | Cartagena | 14–19 ABR | Archivado |
| `aff2026` | AFF 2026 | Medellín | 21–29 ABR | Archivado |
| `tribeca2026` | Tribeca Festival |  |  | desconocido |
| `cinemancia2025` | Cinemancia 2025 | Valle de Aburrá | 11–20 SEP | Archivado |
| `leviza2026` | Leviza - Festival de Cine y Audiovisuales | Zapatoca | 14–17 MAY | Archivado |
| `olhar2026` | Olhar de Cinema | Curitiba | JUN 4–13 | Archivado |
| `tercertiempo2026` | Tercer Tiempo Fest | Bogotá | 13–19 JUL | **Próximo / activo** |
| `fantasofest2026` | FantasoFest | Bogotá | 13–19 JUL | **Próximo / activo** |
| `ficmontanas2026` | Ficmontañas | Salento | JUL 1–5 | Recién terminado |

### Features activas (desde `.specify/features/`)

_Sin features activas en `.specify/features/`._

---

## Documentación de referencia

| Archivo | Qué contiene |
|---|---|
| `docs/ARQUITECTURA.md` | Design system completo, reglas de diseño, mapa de funciones, patrones canónicos |
| `docs/PIPELINE.md` | Proceso de onboarding de festivales nuevos (fases, gates, roles) |
| `docs/SCHEMA.md` | Schema normativo del JSON de festival |
| `.specify/memory/constitution.md` | Rationale de decisiones de arquitectura clave |
| `.specify/features/` | Specs y planes de features en desarrollo |
| `validate.py` | Validador: JS syntax, divs críticos, CSS, patrones prohibidos |

---

## Reglas críticas (resumen — ver `docs/ARQUITECTURA.md` para detalle)

- **CTA primario:** fondo amber sólido, texto negro. Siempre.
- **Pósters:** solo vía `getFilmPoster(f)` o `getCortoItemPoster(item)`. Nunca directo.
- **Iconos:** solo Lucide. Flags de países y emojis de categoría son la única excepción.
- **Conflictos de horario:** siempre `screensConflict()`. Nunca comparaciones manuales.
- **Tokens:** todo valor de spacing, tipografía y radio usa `var(--)`. Cero valores raw.
- **Regex en index.html:** prohibido para transformaciones estructurales de >10 ocurrencias.
- **Timezone:** Colombia (UTC-5). Nunca `toISOString()` para lógica de fechas.
- **i18n:** la fuente de verdad es `src/i18n/i18n.js` (bloque `_I18N`, es+en). Toda string nueva va ahí — es lo que lee `t()` y lo que valida `validate.py [i18n-complete]`. Los `i18n/*.json` quedaron desincronizados y NO se consumen en runtime (legacy); no son la fuente. El `sync-i18n.py` fue retirado (apuntaba a un `_I18N` en `index.html` que la Fase 8 movió a `src/i18n/i18n.js`).
- **Splash selector — carrusel de afiches (rediseño jul 2026):** el splash elige festival desde un **riel horizontal de pósters** (`#splash-rail`, cards `.splash-card[data-fest]` con `keyArt` de `FESTIVAL_CONFIG`), no un dropdown. Orden: vigentes primero (brillo pleno) → divisor `.splash-rail-div` "ANTERIORES" → pasados (atenuados). El bloque `#splash-info` muestra 4 líneas derivadas del festival centrado/elegido: nombre / tagline (`festivalTagline`, derivado de `fullName`) / CIUDAD (punto verde si en curso) / FECHAS·AÑO. **Regla de preselección (5 jul 2026, preservada):** con EXACTAMENTE 1 festival en curso (`_classifyFestival`==="ongoing") el riel lo **pre-selecciona** (card `.on`, "Entrar" habilitado). Con 0 o 2+ en curso → sin selección: el info muestra el primer festival como preview y "Entrar" queda `disabled` hasta que el usuario elija (scroll-snap centra → `_selectCenteredCard`, o tap → `selectSplashFest()` marca `.on`, llena el info y habilita "Entrar"). Riel + info viven dentro de `.splash-action` (uno de los 3 actores animados) → la animación del splash no cambia.

---

## APIs

- **TMDB:** `$TMDB_API_KEY` (variable de entorno — nunca hardcodeada)
- **GitHub token:** en el bootstrap command de arriba

---

## Android APK (Play Store)

- **Track:** Closed testing — Alpha
- **versionCode actual:** 7 (subido JUN 4, 2026)
- **Próximo versionCode:** **8** — nunca reutilizar un code ya publicado
- **server.url:** `https://otrofestiv.app` — la app carga desde producción, no desde bundle local
- **Para compilar:** Android Studio → Build → Generate Signed Bundle → versionCode en `android/app/build.gradle`
- **Para subir:** Play Console → Testing → Closed testing → Alpha → Create new release

### Checklist OBLIGATORIO antes de cada build de APK (lección del v6/v7 congelado)

El repo nativo (`~/Otrofestiv.app`) empaqueta una copia de la web en `www/` →
`android/app/src/main/assets/public/`. **Esa copia NO se sincroniza sola**: el
v6/v7 de Play Store se compiló con un bundle de JUN 2 y los testers quedaron
congelados en código viejo pese a los deploys web. Antes de CADA build:

1. **Refrescar `www/`** con la web actual (desde el repo web en `main` limpio):
   copiar `index.html`, `sw.js`, `version.json`, `manifest.json`, iconos, y
   rsync `src/`, `festivals/`, `i18n/`, `assets/`.
2. **`npx cap copy android`** (regenera `assets/public/` + `assets/capacitor.config.json`).
3. **Verificar el bundle compilado:** `grep 'main.js?v=' android/app/src/main/assets/public/index.html`
   debe coincidir con el build de `version.json` en producción.
4. **Verificar server.url compilado:** `android/app/src/main/assets/capacitor.config.json`
   debe contener `"url": "https://otrofestiv.app"`. Sin él, el APK sirve el
   bundle local para siempre, sin ningún mecanismo de update (Capgo fue
   eliminado — `.specify/memory/constitution.md`).
5. **Subir versionCode** en `android/app/build.gradle` (nunca reutilizar).

> ⚠️ El repo nativo comparte remote con el repo web — **NUNCA commitear/pushear
> desde `~/Otrofestiv.app`** (clobbearía `main` de producción). Su config vive
> solo en working tree; `build.js` del nativo es legacy pre-Fase 8 (no usar).

---

## CI — GitHub Actions

- **bump-and-validate.yml:** corre `python3 validate.py` **y** los unit tests de dominio (`node --test tests/unit/*.test.js`) — ambos deben pasar para que el job quede verde. (Pese al nombre, NO hace bump: el bump de versión es responsabilidad local — correr `node scripts/bump-version.js` antes de cada push.) Ojo: cambiar la firma/deps de una fn de dominio (ej. un nuevo `import` interno) suele requerir actualizar `tests/lib/load-domain.js` (DEFAULT_FNS) además del test.
- **playwright.yml:** tests de regresión T01–T10, viewport 390×844 (iPhone 14), simTime frozen para festivales activos.
- **Update iOS/Android:** `bump-version.js` avanza `version.json.ios` junto con `.android` (mismo build, sin staged rollout). El cliente recarga vía poll de `version.json` en cada reapertura.

---

## Herramientas del pipeline

```bash
python3 validate.py                        # validar antes de commitear
node scripts/bump-version.js               # actualizar sw.js + version.json + CLAUDE.md antes de deploy
node scripts/generate-config.js --help     # generar entrada FESTIVAL_CONFIG
python3 scripts/enrich-festival.py --help  # enriquecer JSON con TMDB
python3 scripts/geocode-venues.py --help   # geocodificar venues
```
