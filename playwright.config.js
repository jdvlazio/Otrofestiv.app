// @ts-check
const { defineConfig, devices } = require('@playwright/test');

// PUERTO POR CORRIDA (6 ago 2026) — la causa raíz del flaky que nos costó meses.
// Playwright MATA el servidor que él levantó al terminar. En local
// `reuseExistingServer` hace que una segunda corrida reuse ese servidor en vez de
// levantar el suyo; si la primera termina antes, se lleva el servidor y la
// segunda se queda hablando con un puerto muerto:
//     net::ERR_CONNECTION_REFUSED → cascada de timeouts de 30s en todo lo que
//     estuviera en vuelo, en specs sin relación entre sí.
// Reproducido a voluntad: la misma suite da 21/21 sola y 1/21 con otra corrida
// solapada. Explica por qué "fallaba distinto cada vez" y por qué los reintentos
// lo tapaban (al 2º intento la otra corrida ya había terminado).
// Con un puerto propio, cada corrida tiene su servidor y no existe la colisión.
// `scripts/test.sh` elige uno libre y aísla también los artefactos.
const PORT = Number(process.env.PW_PORT) || 3000;

module.exports = defineConfig({
  testDir: './tests',
  testIgnore: ['**/unit/**'], // unit tests viven en tests/unit/ y corren con `node --test`
  timeout: 30000,
  // retries: 2 — mitigación del flaky residual (bootstrap-incomplete: "X is not
  // defined" / context destroyed) que workers=1 + gate appReady redujeron pero no
  // eliminaron del todo en los runners de CI. Un 2º retry absorbe el caso raro
  // sin enmascarar fallos reales (un fallo determinista falla los 3 intentos).
  retries: 2,
  // CI = serial. El split a 13+ módulos ESM multiplicó los requests HTTP + el
  // parse/eval por carga de página; con workers paralelos en los runners de
  // 2 núcleos de GitHub Actions eso saturaba CPU/browser y las cargas excedían
  // los timeouts → flaky (#splash-dropdown, FESTIVAL_CONFIG undefined, etc.).
  // Serial = 83/83 determinista. Local conserva paralelismo (undefined → auto).
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { open: 'never' }],
    ['list'],
    ['github'],  // expone fallos como anotaciones en GitHub Actions
    // outputFile por corrida: dos corridas simultáneas se pisaban este archivo
    // (mi primer análisis de fallos salió en blanco por eso). scripts/test.sh lo
    // fija por puerto; el default sirve para la invocación suelta.
    ['json', { outputFile: process.env.PLAYWRIGHT_JSON_OUTPUT_NAME || 'test-results.json' }],
  ],
  use: {
    baseURL: process.env.BASE_URL || `http://localhost:${PORT}`,
    headless: true,
    viewport: { width: 390, height: 844 }, // iPhone 14 — mobile first
    locale: 'es-CO',                              // idioma determinista — evita variaciones de CI runner
  },
  projects: [
    // Suite de comportamiento — SIEMPRE EN MÓVIL (390x844, iPhone 14).
    // ⚠️ REGLA DURA (Juan, 17 jul 2026): la app es mobile-only; NUNCA medir ni
    // revisar en desktop. devices['Desktop Chrome'] PISABA el viewport global
    // (1280px) y toda la suite corrió meses en el layout equivocado — el bug de
    // geometría de tabs se midió mal por esto. El viewport va EXPLÍCITO aquí.
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true },
      testIgnore: /responsive\.spec\.js/,
    },
    // ── Proyectos cross-engine: SOLO el spec responsive (testMatch acota) ──────
    // Razón de ser del Paso 2 del plan de robustez (memoria
    // responsive-robustness-plan): cubrir los 2 motores reales (WebKit/iOS +
    // Blink/Android) × tamaños extremos sin tener los dispositivos. No tocan la
    // suite de comportamiento — sólo miden invariantes de layout deterministas.
    {
      name: 'ios-mobile',      // WebKit @390 — motor de iOS (Safari/WKWebView)
      testMatch: /responsive\.spec\.js/,
      use: { ...devices['iPhone 14'] },
    },
    {
      name: 'android-small',   // Blink @360 — viewport clase Redmi 8 / gama baja
      testMatch: /responsive\.spec\.js/,
      use: { ...devices['Pixel 7'], viewport: { width: 360, height: 640 } },
    },
    {
      name: 'tablet',          // WebKit @768 — iPad; ejercita el media query ≥768px
      testMatch: /responsive\.spec\.js/,
      use: { ...devices['iPad Mini'], viewport: { width: 768, height: 1024 } },
    },
  ],
  webServer: {
    // Servidor CONCURRENTE (ThreadingHTTPServer). El `python3 -m http.server`
    // por defecto es single-thread: con el split a 13+ módulos ESM, cada carga
    // de página dispara 13+ requests HTTP que se encolan contra un único hilo;
    // bajo los workers paralelos de Playwright eso saturaba el server y las
    // cargas superaban el timeout → flaky (#splash-dropdown y otros). Threading
    // sirve los módulos en paralelo y elimina la contención.
    command: `python3 -c "from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler; ThreadingHTTPServer((\'\', ${PORT}), SimpleHTTPRequestHandler).serve_forever()"`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 10000,
  },
});
// Updated: CI now runs on Node 24 (checkout@v5, setup-node@v5, upload-artifact@v6)
