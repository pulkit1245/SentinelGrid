/**
 * Log in once and save auth state to avoid login rate-limit (5/min).
 */
import { test as setup, expect } from '@playwright/test'

const AUTH_FILE = 'tests/e2e/.auth/admin.json'

setup('authenticate as admin', async ({ page }) => {
  await page.goto('/login')
  await page.fill('#email', 'admin@sentinelgrid.demo')
  await page.fill('#password', 'Demo@1234')
  await page.click('#btn-login')
  await page.waitForURL('**/dashboard', { timeout: 15000 })
  await expect(page.getByRole('heading', { name: /Operations Command Centre/i })).toBeVisible()
  await page.context().storageState({ path: AUTH_FILE })
})

export { AUTH_FILE }
