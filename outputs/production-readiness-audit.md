# InsightFlow production-readiness audit

Audit date: 2026-10-09

## Verdict

InsightFlow's implemented scope is coherent, testable, and suitable for local development or a controlled demonstration. The full analytical flow works, including an automated browser test. It is not yet deployment-certified for an internet-facing production environment because Docker is unavailable on this review host and CSV operations still load bounded files into process memory.

## What works

- Registration, login, logout, current-user lookup, JWT-protected APIs, ownership checks, and protected frontend navigation.
- Project CRUD, validated private CSV upload, asynchronous profiling, data-quality scoring, column statistics, missing-value and duplicate detection, and paginated exploration.
- Dataset-derived bar, line, scatter, histogram, box, donut, and correlation visualizations with server-side column validation and saved configurations.
- Asynchronous classification, regression, and clustering experiments with train-only preprocessing, persisted metrics, optional XGBoost, model explanations, and explicit correlation/causation boundaries.
- Optional Ollama assistant that receives structured statistics rather than unrestricted SQL or full raw datasets, and fails without taking down the application.
- Project PDF reports containing dataset, quality, visualization, experiment, metric, and model-importance evidence.
- Alembic upgrades a fresh database through `0007_reports`; the expected PostgreSQL-oriented service topology is represented in Compose.

## Problems fixed during the review

- Replaced vulnerable `python-jose`/ECDSA usage with current PyJWT and upgraded vulnerable FastAPI, Starlette, multipart, pytest, and coverage dependencies.
- Added production/staging JWT-secret validation, bounded configuration validation, constant-work login handling for unknown emails, SQLite foreign-key enforcement, complete CSV row-width validation, column-count limits, safer filename normalization, rollback cleanup, private file modes, and secure report download paths.
- Added real report persistence, migration, owned API routes, frontend report history/download UI, and a generated, visually verified PDF report.
- Added structured JSON logging and useful worker/storage failure logging.
- Fixed CORS methods, expired-session handling, stale explorer requests, frontend request errors, dataset selection resets, missing mobile sign-out, form labels, focus states, reduced-motion support, dialog semantics, and table captions.
- Removed the remote font dependency; added nginx request-size parity, security headers, proxy settings, Docker ignore files, a non-root backend image, and single-process worker concurrency.
- Added backend/frontend lint and dependency-audit gates plus Docker image builds to GitHub Actions; expanded environment examples and corrected README setup guidance.
- Replaced `localStorage` token persistence with HttpOnly SameSite cookies and double-submit CSRF protection while retaining bearer-token API access.
- Added nginx request limiting, per-user profiling/training concurrency quotas, CSV row limits, and Celery acknowledgement and execution-time limits.
- Added an automated Playwright test for registration through report generation and fixed the upload form lifecycle bug it exposed.
- Created reviewed initial commit `bf479e2`; local datasets, databases, generated reports, browser artifacts, build output, caches, and `.env` were excluded.

## Verification performed

- Backend: `60 passed` at 89% statement coverage; Ruff, source compilation, and `pip check` passed; `pip-audit` found no known vulnerabilities.
- Frontend: `6 passed`; ESLint clean; TypeScript clean; Vite production build successful; production dependency audit found no known vulnerabilities.
- Browser E2E: Playwright Chromium completed the main workflow in `5.2s` after finding and prompting a fix for the asynchronous upload-form reset bug.
- Database: clean Alembic migration from baseline through `0007_reports`; expected nine application/migration tables present.
- Compose: YAML parsed and all five services, worker concurrency, and upload configuration were structurally checked.
- Manual API flow: register -> login -> project -> upload -> profile -> explore -> visualize -> train -> metrics -> explain -> save -> report/download completed successfully.
- Browser smoke flow: protected login, project UI, ready profile, explorer rows, saved live chart, completed held-out model metrics, SHAP explanation, and generated report were visibly verified; browser console had no warnings or errors.
- PDF: generated report rendered to images and both pages were visually inspected for clipping, overlap, and legibility.
- Secrets/config: `.env` is ignored and absent, `.env.example` contains safe placeholders, and staged/tracked credential-pattern scans found only documented development defaults. Commit `bf479e2` contains no local datasets, databases, generated reports, browser artifacts, or build output.
- Docker: `docker compose build` and `docker compose up --build --detach` could not run because this host has no Docker executable, daemon, Podman, Colima, Finch, or nerdctl. Container execution therefore remains unverified. CI is configured to build, start with health checks, run migrations, execute a live core flow, emit logs, and tear down volumes.

## Known limitations and remaining technical debt

- Logout is stateless token deletion; immediate server-side revocation is not implemented.
- Nginx supplies IP request limits and the application enforces per-user active job quotas. Multi-replica deployments still need a shared gateway/Redis rate limiter and account lockout policy.
- Exploration, visualization, profiling, and reporting use in-process pandas/ReportLab work. The 25 MB, 500-column, and 250,000-row caps bound risk, but larger-scale use needs chunking, columnar storage, and resource/memory isolation.
- Background jobs now use late acknowledgement, worker-loss rejection, single-worker concurrency, and hard/soft time limits. They still lack a durable retry/dead-letter policy, cancellation, and an operational dashboard. Real Redis/Celery behavior was not exercised on this host.
- XGBoost and Ollama remain optional by design. Explanations depend on model/library support and are not causal evidence.
- The committed Playwright suite covers one critical happy path; authorization, error, responsive, and recovery scenarios remain primarily unit/API tested.
- Dependency warnings remain for Starlette's legacy `TestClient` adapter, ReportLab's Python 3.14 compatibility path, and CPU detection in joblib.
- The visualization bundle is relatively large (about 451 kB before gzip) and Recharts 2.x is in maintenance mode.

## Recommended next steps

1. Run `docker compose up --build --detach --wait` and `docker compose exec -T backend python scripts/compose_smoke.py` on a Docker-capable host; fix any container-only issue before release.
2. Observe a passing GitHub Actions run for backend, frontend/Playwright, and Compose workflows, then require those checks on the default branch.
3. Add shared/distributed abuse controls and a server-side session-revocation strategy before a multi-instance public launch.
4. Add production observability and job operations: metrics, tracing, retry/dead-letter handling, cancellation, resource ceilings, backup/restore, and migration rollback drills.
5. Move large-dataset operations to chunked or columnar execution before raising the current input limits.
