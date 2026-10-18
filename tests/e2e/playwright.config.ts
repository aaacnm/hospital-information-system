import { defineConfig, devices } from '@playwright/test';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const e2eDirectory = dirname(fileURLToPath(import.meta.url));
const rootDirectory = resolve(e2eDirectory, '../..');

export default defineConfig({
  testDir: e2eDirectory,
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: [
    ['list'],
    ['html', { outputFolder: resolve(rootDirectory, 'playwright-report'), open: 'never' }],
  ],
  use: {
    baseURL: process.env.E2E_WEB_URL || 'http://127.0.0.1:4173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    ...devices['Desktop Chrome'],
  },
  webServer: [
    {
      command: 'python serve_backend.py',
      cwd: e2eDirectory,
      url: 'http://127.0.0.1:8000/health',
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 4173',
      cwd: resolve(rootDirectory, 'frontend'),
      url: 'http://127.0.0.1:4173/login',
      env: { VITE_API_BASE_URL: 'http://127.0.0.1:8000/api' },
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
    },
  ],
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});

