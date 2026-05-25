// @ts-check
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  testIgnore: ['**/unit/**'], // unit tests viven en tests/unit/ y corren con `node --test`
  timeout: 30000,
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
    ['json', { outputFile: 'test-results.json' }],
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    headless: true,
    viewport: { width: 390, height: 844 }, // iPhone 14 — mobile first
    locale: 'es-CO',                              // idioma determinista — evita variaciones de CI runner
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    // Servidor CONCURRENTE (ThreadingHTTPServer). El `python3 -m http.server`
    // por defecto es single-thread: con el split a 13+ módulos ESM, cada carga
    // de página dispara 13+ requests HTTP que se encolan contra un único hilo;
    // bajo los workers paralelos de Playwright eso saturaba el server y las
    // cargas superaban el timeout → flaky (#splash-dropdown y otros). Threading
    // sirve los módulos en paralelo y elimina la contención.
    command: 'python3 -c "from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler; ThreadingHTTPServer((\'\', 3000), SimpleHTTPRequestHandler).serve_forever()"',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 10000,
  },
});
// Updated: CI now runs on Node 24 (checkout@v5, setup-node@v5, upload-artifact@v6)
