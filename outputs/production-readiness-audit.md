# InsightFlow production-readiness audit

Audit date: 2026-10-09

## Verdict

InsightFlow's implemented scope is coherent, testable, and suitable for local development or a controlled demonstration. The full analytical flow works. It is not yet deployment-certified for an internet-facing production environment because Docker is unavailable on this review host, browser tokens are stored in `localStorage`, abuse controls are absent, and CSV operations still load bounded files into process memory.

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

## Verification performed

- Backend: `57 passed`, 89% statement coverage; Ruff clean; Python compilation clean; `pip check` clean; `pip-audit` found no known vulnerabilities.
- Frontend: `6 passed`; ESLint clean; TypeScript clean; Vite production build successful; production dependency audit found no known vulnerabilities.
- Database: clean Alembic migration from baseline through `0007_reports`; expected nine application/migration tables present.
- Compose: YAML parsed and all five services, worker concurrency, and upload configuration were structurally checked.
- Manual API flow: register -> login -> project -> upload -> profile -> explore -> visualize -> train -> metrics -> explain -> save -> report/download completed successfully.
- Browser smoke flow: protected login, project UI, ready profile, explorer rows, saved live chart, completed held-out model metrics, SHAP explanation, and generated report were visibly verified; browser console had no warnings or errors.
- PDF: generated report rendered to images and both pages were visually inspected for clipping, overlap, and legibility.
- Secrets/config: `.env` is ignored and absent, `.env.example` exists, and a working-tree credential-pattern scan found only documented development placeholders. This repository currently has no Git `HEAD` or tracked files, so there is no commit history to scan.
- Docker: `docker compose build` and `docker compose up --build --detach` were attempted but could not run because this host has no `docker` executable or daemon. Container execution therefore remains unverified locally; CI now builds both images.

## Known limitations and remaining technical debt

- JWTs persist in `localStorage`; an HttpOnly, Secure, SameSite cookie plus CSRF strategy would reduce token exposure to XSS.
- Logout is stateless token deletion; immediate server-side revocation is not implemented.
- Authentication and expensive endpoints have no rate limiting, lockout, quota, or per-user concurrency controls.
- Exploration, visualization, profiling, and reporting use in-process pandas/ReportLab work. The 25 MB upload and 500-column caps bound risk, but larger-scale use needs chunking, columnar storage, and resource/time limits.
- Background jobs have no durable retry/dead-letter policy, cancellation, or operational dashboard. Tests use eager execution; real Redis/Celery behavior was not exercised on this host.
- XGBoost and Ollama remain optional by design. Explanations depend on model/library support and are not causal evidence.
- Frontend tests cover authentication routing and reports but not every interactive studio; the successful full-flow browser check is manual rather than a committed end-to-end suite.
- Dependency warnings remain for Starlette's legacy `TestClient` adapter, ReportLab's Python 3.14 compatibility path, and CPU detection in joblib.
- The visualization bundle is relatively large (about 451 kB before gzip) and Recharts 2.x is in maintenance mode.
- The repository needs an initial reviewed commit before GitHub Actions can provide durable evidence.

## Recommended next steps

1. Run `docker compose up --build` on a Docker-capable host and exercise PostgreSQL, Redis, API, worker, and nginx together; fix any container-only issue before release.
2. Move browser authentication to hardened cookies and add rate limits, request/job quotas, and structured security-event logging.
3. Add a Playwright end-to-end suite for the critical flow and run it against Compose in CI.
4. Add production observability and job operations: metrics, tracing, retry/dead-letter handling, resource ceilings, backup/restore, and migration rollback drills.
5. Create the initial commit only after reviewing the current untracked working tree and configure protected CI gates on the default branch.
