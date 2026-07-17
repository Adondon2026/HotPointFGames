const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'line',
  use: {
    baseURL: 'http://127.0.0.1:18080',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    viewport: { width: 390, height: 844 },
  },
  webServer: {
    command: 'python tests/run_e2e_server.py',
    url: 'http://127.0.0.1:18080',
    reuseExistingServer: false,
    timeout: 15000,
  },
});
