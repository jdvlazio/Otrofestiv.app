// @ts-check
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  timeout: 30000,
  retries: 1,
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
    command: 'python3 -m http.server 3000',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 10000,
  },
});
// Updated: CI now runs on Node 24 (checkout@v5, setup-node@v5, upload-artifact@v6)
