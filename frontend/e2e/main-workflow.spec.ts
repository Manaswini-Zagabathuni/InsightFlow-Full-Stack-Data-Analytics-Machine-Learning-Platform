import path from 'node:path'

import { expect, test } from '@playwright/test'

test('registers and completes the main analytics workflow', async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`
  await page.goto('/register')
  await page.getByLabel('Full name').fill('End to End Analyst')
  await page.getByLabel('Email address').fill(email)
  await page.getByLabel('Password', { exact: true }).fill('Production123')
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page.getByRole('heading', { name: 'Welcome, End to End Analyst.' })).toBeVisible()

  await page.getByRole('link', { name: 'Projects', exact: true }).click()
  await page.getByRole('button', { name: 'New project' }).click()
  await page.getByLabel('Project name').fill('Automated launch check')
  await page.getByLabel('Description').fill('Critical workflow verification')
  await page.getByRole('button', { name: 'Create project', exact: true }).click()
  await page.getByRole('link', { name: /Automated launch check/ }).click()

  await page.locator('input[type="file"]').setInputFiles(path.join(process.cwd(), 'e2e/fixtures/customers.csv'))
  await page.getByRole('button', { name: 'Upload & profile' }).click()
  await expect(page.getByRole('heading', { name: 'customers' })).toBeVisible()
  await expect(page.getByText('100/100')).toBeVisible({ timeout: 30_000 })

  await page.getByRole('button', { name: 'Explore', exact: true }).click()
  await expect(page.getByRole('table', { name: 'Paginated rows from customers' })).toContainText('Enterprise')

  await page.getByRole('button', { name: 'Visualize', exact: true }).click()
  await page.getByRole('button', { name: 'Generate & save' }).click()
  await expect(page.getByRole('heading', { name: 'Bar of customers' })).toBeVisible()

  await page.getByRole('button', { name: 'Model Lab', exact: true }).click()
  await page.getByLabel('Decision Tree', { exact: true }).check()
  await page.getByLabel('Experiment name').fill('Automated decision tree')
  await page.getByRole('button', { name: 'Start training' }).click()
  await expect(page.getByRole('heading', { name: 'Model comparison' })).toBeVisible({ timeout: 45_000 })
  await expect(page.getByRole('heading', { name: /Why Decision Tree produced its output/ })).toBeVisible()

  await page.getByRole('button', { name: 'Reports', exact: true }).click()
  await page.getByRole('button', { name: 'Generate PDF' }).click()
  await expect(page.getByText(/insightflow-automated-launch-check-.*\.pdf/)).toBeVisible()
})
