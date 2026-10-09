import { defineConfig } from '@playwright/test'

const python = process.env.INSIGHTFLOW_PYTHON || 'python'

export default defineConfig({
  testDir: './e2e',
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: `export DATABASE_URL=sqlite:////private/tmp/insightflow-playwright.db CELERY_TASK_ALWAYS_EAGER=true UPLOAD_DIR=/private/tmp/insightflow-playwright-uploads PYTHONPATH=../backend; ${python} -m alembic -c ../backend/alembic.ini upgrade head && ${python} -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
      url: 'http://127.0.0.1:8000/api/health',
      timeout: 120_000,
      reuseExistingServer: false,
    },
    {
      command: 'pnpm dev',
      url: 'http://127.0.0.1:5173',
      timeout: 120_000,
      reuseExistingServer: false,
    },
  ],
})
