import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: '.',
  timeout: 30000,
  expect: { timeout: 10000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
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
      },
    },
  ],
})
