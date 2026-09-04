# CLAUDE.md — Otrofestiv
> Generado automáticamente por `scripts/generate-claude-md.js`.
> No editar a mano — los cambios se sobreescriben al regenerar.
> Para modificar secciones estáticas, editar el template en el script.
>
> El hash del último commit NO va acá a propósito: cambiaba en cada rama y hacía
> de este archivo un conflicto garantizado por PR, sin aportar nada que `git log`
> no diga mejor.

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
4. Si el trabajo involucra onboarding de un festival nuevo: `pipeline/PROTOCOLO.md` — **es EL proceso**.
   Antes de escribir una línea, tener abiertos `pipeline/correr.py` (el runner),
   `pipeline/enriquecer.py` (TMDB verificado + Letterboxd + pósters, un comando) y
   `pipeline/festival.plan.example.json` (la plantilla del plan). Si vas a hacer a mano
   algo que tiene comando, para. `docs/PIPELINE.md` es la doctrina de TMDB/LB y el
   historial de errores: manda en su tema, no es el proceso.

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
7. **Código de la app acá, datos del festival allá.** El trabajo está partido en dos
   chats con worktrees separados. La pregunta que decide dónde va un cambio es una
   sola: *¿esto es código o es un festival?*

| | Dueño | Qué toca | Ramas |
|---|---|---|---|
| **Main** | código de la app | `src/`, `validate.py`, `tests/`, `scripts/` | `feat/*`, `fix/*` |
| **Onboarding** | datos de festival | `festivals/`, `assets/`, `src/config.js` | `feat/<festival>-catalogo` |

**Quien es dueño de la rama la lleva hasta el final: push _y_ merge.** El trabajo no
se parte a la mitad entre dos chats — así nace la pregunta «¿y ahora quién mergea?».
Juan autoriza en el chat dueño de la rama.

Si un cambio necesita las dos cosas (un campo nuevo en el dato + soporte en la app),
van **dos PR, primero el de app**: así el dato nunca llega a producción antes que el
código que sabe leerlo. El workflow `frontera.yml` lo verifica; para la excepción
deliberada existe la etiqueta `frontera-ok`.

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
| `tercertiempo2026` | Tercer Tiempo Fest | Bogotá | 13–19 JUL | Archivado |
| `fantasofest2026` | FantasoFest | Bogotá | 13–19 JUL | Archivado |
| `ficma2026` | FICMA | Manizales | 10–17 AGO | desconocido |
| `ficdeh2026` | FICDEH | Colombia | 12–19 AGO | Recién terminado |
| `finca2026` | FINCA | Buenos Aires | 12–19 AGO | Recién terminado |
| `cinemancia2026` | Cinemancia | Valle de Aburrá | 3–12 SEP | **Próximo / activo** |
| `cineautopsia2026` | CineAutopsia | Bogotá | 21–29 AGO | Recién terminado |
| `vartex2026` | Vartex | Medellín | 19–22 AGO | Recién terminado |
| `qaff2026` |  |  |  | desconocido |
| `tiff2026` | TIFF | Toronto | 10–20 SEP | **Próximo / activo** |
| `ficmontanas2026` | Ficmontañas | Salento | JUL 1–5 | Archivado |
| `siembrafest2026` | SiembraFest | Sasaima y Villeta | 9–18 SEP | **Próximo / activo** |

### Features activas (desde `.specify/features/`)

_Sin features activas en `.specify/features/`._

---

## Documentación de referencia

| Archivo | Qué contiene |
|---|---|
| `docs/ARQUITECTURA.md` | Design system completo, reglas de diseño, mapa de funciones, patrones canónicos |
| `pipeline/PROTOCOLO.md` | EL proceso de onboarding: fuente → producción (pasos, formato intermedio, checklist) |
| `docs/PIPELINE.md` | Doctrina de enrichment (TMDB/LB) + historial de errores — manda en su tema |
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
- **Splash — REGLA MADRE del orden (9 ago 2026):** dentro de cada tier el riel ordena **por FECHA**: los próximos, el que **empieza antes primero**; los que están en curso, el que **termina antes**; los pasados, el más reciente. Existe un campo `priority` en `FESTIVAL_CONFIG` que desempata antes que la fecha — **es para un empujón puntual y se QUITA después**. Lo llevó FINCA unos días por una nota de prensa y se retiró: una excepción editorial permanente erosiona la regla. Ojo: cuando dos festivales arrancan a la MISMA hora (FICDEH y FINCA, ambos 12 AGO 00:00) el desempate lo decide el orden de declaración en el config, que es estable pero no es una decisión — si importa, hay que declararla.
- **Splash — qué va en el tagline:** el subtítulo **expande la sigla**, no repite el nombre ni trae el lema de la edición. «FICMA» no le dice nada a quien llega de fuera → `Feria Internacional de Cine de Manizales`. El lema del año se lee en el afiche, que está justo encima; ponerlo ahí gasta la única línea de contexto disponible. Mismo criterio en FICDEH.

---

## APIs

- **TMDB:** `$TMDB_API_KEY` (variable de entorno — nunca hardcodeada)
- **GitHub token:** en el bootstrap command de arriba

---

## Las apps en las tiendas

**Las DOS están PUBLICADAS y disponibles al público**, aprobadas y verificadas
desde hace tiempo. No están en pruebas cerradas.

- **iOS:** https://apps.apple.com/co/app/otrofestiv/id6769367002 — gratis.
  `IPHONEOS_DEPLOYMENT_TARGET = 26.0` (proyecto nativo en iCloud `10_iOS`).
- **Android:** https://play.google.com/store/apps/details?id=app.otrofestiv.mobile

> ⚠️ Este bloque decía «Closed testing — Alpha» mucho después de que ambas apps
> estuvieran publicadas, y el dato de versionCode se quedó en JUN 2026. Un
> ayudante que lea este archivo como contexto —que es lo que este archivo ES—
> concluye que la app no se puede instalar, y de ahí saca diagnósticos falsos
> sobre por qué no hay usuarios. Pasó el 15 ago 2026.
> **El estado de las tiendas se consulta en App Store Connect y Play Console,
> no acá.** Lo que vive acá son los enlaces y el procedimiento; el ESTADO no,
> porque este archivo no puede saberlo y mentir es peor que callar.

- **server.url:** `https://otrofestiv.app` — la app carga desde producción, no desde bundle local
- **Para compilar (Android):** Android Studio → Build → Generate Signed Bundle → versionCode en `android/app/build.gradle`
- **versionCode:** nunca reutilizar uno ya publicado — el actual se consulta en Play Console

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
sh scripts/install-hooks.sh                # UNA VEZ por clon/worktree: hooks + driver de merge
python3 validate.py                        # validar antes de commitear
node scripts/bump-version.js               # actualizar index.html + main.js + sw.js + version.json antes de deploy
node scripts/generate-claude-md.js         # regenerar este archivo cuando cambie el estado del proyecto
node scripts/generate-config.js --help     # generar entrada FESTIVAL_CONFIG
python3 scripts/enrich-festival.py --help  # enriquecer JSON con TMDB
python3 scripts/geocode-venues.py --help   # geocodificar venues
```
