import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  projects: [
    {
      name: 'setup',
      testMatch: /auth\.setup\.ts/,
      use: { baseURL: 'http://localhost:5173' },
    },
    {
      name: 'ui',
      testMatch: /ui-features\.spec\.ts/,
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:5173',
        headless: true,
        storageState: 'tests/e2e/.auth/admin.json',
        screenshot: 'only-on-failure',
      },
    },
  ],
})
