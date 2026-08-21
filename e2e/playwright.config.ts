import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: '.',
  timeout: 30000,
  expect: { timeout: 10000 },
  // Auth/profile/i18n specs share one backend user and log in concurrently;
  // a single worker serializes across files (fullyParallel only covers one file).
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'list',

  projects: [
    {
      name: 'backend',
      testMatch: 'backend/**/*.spec.ts',
      use: {
        baseURL: 'http://localhost:8000',
      },
    },
    {
      name: 'frontend',
      testMatch: 'frontend/**/*.spec.ts',
      use: {
        baseURL: 'http://localhost:3000',
        // Pinned so specs stay stable when i18n lands (Spanish default).
        locale: 'es-CO',
      },
    },
  ],
})
