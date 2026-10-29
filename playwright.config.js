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
  // retries: 1 (era 2, bajado el 10 ago 2026). Con 2 reintentos la suite reportaba
  // «13 flaky, 0 fallos» y eso se leía como verde; sin reintentos, esa MISMA suite
  // fallaba 11 veces. Los reintentos no distinguían «la máquina estaba ocupada» de
  // «la app falla una de cada tres veces» — tapaban las dos cosas por igual.
  // Uno se conserva: absorbe el caso raro de bootstrap incompleto en los runners
  // de 2 núcleos de CI, y un fallo determinista sigue fallando los dos intentos.
  // La otra mitad del arreglo vive en scripts/test.sh: avisa cuando la máquina
  // está cargada (la causa real del ruido) y nombra los flaky en vez de sumarlos
  // al verde.
  retries: 1,
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
    // Servidor CONCURRENTE y con cola ancha: scripts/servidor-pruebas.py dice por
    // qué (la cola de 5 por defecto cortaba módulos y la app no arrancaba).
    command: `python3 scripts/servidor-pruebas.py ${PORT}`,
    url: `http://localhost:${PORT}`,
    // Con PW_PORT (scripts/test.sh eligió un puerto para ESTA corrida) nunca se
    // reusa un servidor ajeno: si el puerto se ocupó entre la elección y el
    // arranque, falla claro en vez de colgarse del servidor de otra corrida.
    reuseExistingServer: !process.env.CI && !process.env.PW_PORT,
    timeout: 10000,
  },
});
// Updated: CI now runs on Node 24 (checkout@v5, setup-node@v5, upload-artifact@v6)
