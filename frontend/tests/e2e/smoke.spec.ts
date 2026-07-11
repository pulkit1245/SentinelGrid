import { test, expect } from '@playwright/test';

test('smoke test login and dashboard', async ({ page }) => {
  await page.goto('http://localhost:5173/');
  
  // Should redirect to login
  await expect(page).toHaveURL(/.*\/login/);
  
  // Fill credentials
  await page.fill('input[type="email"]', 'officer@sentinelgrid.demo');
  await page.fill('input[type="password"]', 'Demo@1234');
  
  // Submit
  await page.click('button[type="submit"]');
  
  // Should redirect to dashboard
  await expect(page).toHaveURL(/.*\/dashboard/);
  
  // Check for dashboard heading
  await expect(page.locator('h1')).toContainText('Operations Command Centre');
});
