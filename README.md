# InsightFlow

This repository contains the InsightFlow platform foundation, authentication, project/dataset management, interactive visualization, asynchronous machine-learning experimentation, explainability, downloadable PDF reporting, and an optional local dataset assistant.


## Included

- React 18, TypeScript, Vite, and Tailwind CSS frontend
- FastAPI backend with structured startup/shutdown logging
- SQLAlchemy database engine and session factory
- PostgreSQL 16 development database
- Alembic migration environment and initial baseline revision
- Redis 7 broker for Celery profiling and training workers
- Dockerfiles and Docker Compose orchestration
- Typed environment configuration via `pydantic-settings`
- Backend health endpoint that executes a real database query
- Registration, login, logout, bcrypt password hashing, JWT access tokens, and current-user authorization
- HttpOnly browser session cookies with SameSite and double-submit CSRF protection; bearer tokens remain supported for API clients
- Persistent protected frontend routing with responsive login and registration screens
- User-owned project creation, listing, opening, renaming, and deletion
- Secure CSV upload with generated storage paths and strict validation
- Bounded upload rows/columns and per-user profiling/training concurrency limits
- Redis/Celery background profiling with persisted column statistics and transparent data-quality scores
- Server-side dataset exploration with pagination, search, sorting, column metadata, and missing-value indicators
- Interactive bar, line, scatter, histogram, box, donut, and correlation-heatmap charts generated from uploaded CSV data
- Server-validated chart configuration and project-owned saved visualizations
- Asynchronous classification, regression, and clustering experiments dispatched through Celery
- Leakage-safe scikit-learn preprocessing pipelines for imputation, scaling, and one-hot encoding
- Persisted experiment status, configuration, hyperparameters, and per-model metrics
- Persisted Tree SHAP and Linear SHAP explanations with global importance and held-out-row contributions
- Authorized project PDF reports generated from persisted profiles, visualizations, metrics, and explanations
- Optional local Ollama assistant grounded only in structured InsightFlow analytics
- Deterministic question routing with no raw-row transfer, SQL generation, or paid external LLM dependency
- Backend authentication tests and frontend route tests
- Basic GitHub Actions workflows
- `.env.example`, `.gitignore`, `.gitattributes`, and `.editorconfig`

## Architecture

```text
Browser
  │
  ▼
React/Vite frontend :5173
  │ /api/* through nginx
  ▼
FastAPI backend :8000
  ├── SQLAlchemy ── PostgreSQL :5432
  ├── chart queries ── bounded dataset aggregations
  ├── structured analytics ── optional local Ollama :11434
  └── profiling/training jobs ── Redis :6379 ── Celery worker
```


Redis brokers real background dataset-profiling jobs to the Celery worker. Tests use Celery eager mode so the same task is deterministic without a broker.

## Start with Docker

Requirements: Docker Engine with the Compose plugin.

```bash
cp .env.example .env
docker compose up --build
```

For a detached, health-gated launch followed by the live core-flow verification:

```bash
docker compose up --build --detach --wait
docker compose exec -T backend python scripts/compose_smoke.py
```

Services:

- Frontend: <http://localhost:5173>
- Backend health: <http://localhost:8000/api/health>
- OpenAPI documentation: <http://localhost:8000/api/docs>

Expected health response:

```json
{
  "status": "healthy",
  "service": "insightflow-api",
  "version": "0.1.0",
  "database": "connected"
}
```

Stop the environment with:

```bash
docker compose down
```

Use `docker compose down -v` only when you intentionally want to delete local PostgreSQL data.

## Environment configuration

| Variable | Purpose | Default |
|---|---|---|
| `POSTGRES_PASSWORD` | Local PostgreSQL password | Development fallback in Compose |
| `DATABASE_URL` | SQLAlchemy connection URL | SQLite outside Docker; PostgreSQL in Compose |
| `REDIS_URL` | Redis broker for background profiling | `redis://localhost:6379/0` |
| `CORS_ORIGINS` | Comma-separated browser origins | Local frontend origins |
| `ENVIRONMENT` | Runtime environment label | `development` |
| `LOG_LEVEL` | Application log level | `INFO` |
| `JWT_SECRET` | Signs JWT access tokens | Development fallback in Compose |
| `ACCESS_TOKEN_MINUTES` | JWT lifetime in minutes | `60` |
| `UPLOAD_DIR` | Private dataset and report storage root | `uploads` |
| `MAX_UPLOAD_BYTES` | Maximum CSV upload size | `26214400` |
| `MAX_CSV_COLUMNS` | Maximum accepted CSV columns | `500` |
| `MAX_CSV_ROWS` | Maximum accepted nonblank CSV rows | `250000` |
| `MAX_ACTIVE_PROFILES_PER_USER` | Concurrent queued/profiling datasets per user | `3` |
| `MAX_ACTIVE_EXPERIMENTS_PER_USER` | Concurrent queued/training experiments per user | `2` |
| `PROFILE_JOB_TIME_LIMIT_SECONDS` | Hard profiling job limit | `300` |
| `TRAINING_JOB_TIME_LIMIT_SECONDS` | Hard training job limit | `1800` |
| `OLLAMA_BASE_URL` | Local Ollama server; Compose uses the host gateway | `http://localhost:11434` outside Docker |
| `OLLAMA_MODEL` | Locally installed open model | `gemma4:e2b` |
| `OLLAMA_TIMEOUT_SECONDS` | Local generation timeout | `60` |

Never commit `.env`. The tracked `.env.example` contains configuration names without production credentials. Staging and production startup fails when a known development JWT secret is used.

## Database migrations

The backend container runs migrations before starting FastAPI:

```bash
alembic upgrade head
```

The initial migration is the empty Phase 1 baseline. Migration `0002_create_users` creates users, `0003_projects_datasets` creates projects/datasets and persisted column profiles, `0004_visualizations` creates saved chart configurations, `0005_experiments` creates ML experiments and metrics, `0006_explainability` persists explanation payloads, and `0007_reports` tracks generated PDF files. Tables are never created from application startup code.

Create a future migration from `backend/` with:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Local development without Docker

Backend:

```bash
cp .env.example .env
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
```

The non-Docker default uses SQLite so the API can be exercised without PostgreSQL. Dataset profiling and model training still require Redis and a Celery worker. Start a local Redis server, then run this from a second activated backend terminal:

```bash
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO --concurrency=1
```

For a lightweight API-only session, set `CELERY_TASK_ALWAYS_EAGER=true`; background jobs then execute synchronously and should not be used as a production configuration. Docker Compose always uses PostgreSQL, Redis, and a separate worker.

Frontend:

```bash
cd frontend
corepack enable
pnpm install
pnpm dev
```

Vite proxies `/api` requests to `http://localhost:8000` in development.

## Optional local AI assistant

The assistant is an enhancement, not an application dependency. Without Ollama, authentication, projects, uploads, profiling, exploration, visualizations, experiments, and explainability continue normally. The Assistant tab displays a clear unavailable state and a retry action.

1. [Download Ollama](https://ollama.com/download) for macOS, Windows, or Linux and open it. On Linux, run `ollama serve` if the server is not already active.
2. Download the configured local model:

   ```bash
   ollama pull gemma4:e2b
   ```

3. Confirm the local server and model:

   ```bash
   curl http://localhost:11434/api/tags
   ```

4. Start InsightFlow. Docker Compose uses `http://host.docker.internal:11434` through an explicit host-gateway mapping. For a backend launched directly on the host, use:

   ```bash
   export OLLAMA_BASE_URL=http://localhost:11434
   export OLLAMA_MODEL=gemma4:e2b
   uvicorn app.main:app --reload
   ```

To use another locally installed open model, run `ollama pull <model>` and set `OLLAMA_MODEL=<model>`. InsightFlow accepts only local Ollama hostnames; it does not accept an external LLM URL or API key.

The initial question set covers dataset summaries, missing values, Pearson correlations, basic column statistics, saved visualization interpretation, and saved ML experiment summaries. FastAPI classifies the question before model invocation and builds a bounded JSON context from persisted profiles, aggregate correlation results, chart digests, metrics, and model-derived importance. It never sends the complete CSV or raw rows to Ollama, and it does not expose a SQL-generation or database-query tool.

Ollama responses are instructed to distinguish correlation, model importance, and causal claims. The assistant may explain available evidence, but it must not claim that association or feature importance proves causation.

## Tests and builds

```bash
cd backend
ruff check app tests alembic scripts
pytest --cov=app
pip-audit -r requirements.txt

cd ../frontend
pnpm lint
pnpm test
pnpm build
pnpm audit --prod
pnpm exec playwright install chromium
INSIGHTFLOW_PYTHON=../backend/.venv/bin/python pnpm e2e
```

Backend tests cover registration, cookie and bearer authentication, CSRF enforcement, credentials, authorization, project and dataset ownership, resource limits, upload/profiling/exploration, visualization validation, asynchronous ML dispatch, all built-in learning algorithms, preprocessing, leakage boundaries, metrics persistence, explainability, report generation/download authorization, assistant guardrails, the health response, and the database check. The Playwright test covers the browser workflow from registration through report generation.

GitHub Actions run backend lint/tests/source compilation/dependency auditing, frontend lint/unit tests/type checking/production compilation/Playwright, and a Docker Compose startup plus live API workflow on pushes and pull requests. Workflow configuration is not evidence of a passing remote run until GitHub Actions has executed it.

## Verification status

As of 2026-10-09, backend tests, frontend unit tests, linting, type checking, the Vite build, dependency audits, Alembic migrations, and the Playwright critical-flow test have run successfully on the review host. The Playwright flow used SQLite and eager Celery execution.

Docker commands could not run on the review host because Docker and compatible runtimes are not installed. The Compose workflow is configured to build images, wait for all service health checks, run migrations through the backend startup command, and execute `backend/scripts/compose_smoke.py` against PostgreSQL, Redis, FastAPI, Celery, and nginx. Treat Compose as unverified until that workflow or the commands below complete successfully on a Docker-capable machine.

## Repository structure

```text
backend/
  alembic/             migration environment and revisions
  app/api/             authentication routes and authorization dependency
  app/core/            typed configuration
  app/db/              SQLAlchemy engine and sessions
  app/models/          SQLAlchemy domain models
  app/services/        profiling, visualization, ML, explainability, assistant, and PDF reporting
  app/main.py          FastAPI application and health endpoint
  tests/               backend tests
  scripts/             live Compose verification
frontend/
  e2e/                 Playwright critical workflow
  src/App.tsx          public and protected routes
  src/context/         persistent authentication state
  src/pages/           authentication and protected analytics workspaces
  src/components/      application shell and visualization studio
  src/index.css        Tailwind styles
.github/workflows/     CI checks
docker-compose.yml     local service orchestration
```

## Phase boundary

The Compose stack includes frontend, backend, PostgreSQL, Redis, and a single-concurrency Celery worker. Ollama remains an optional host service and is not a required Compose dependency. Authentication exposes `/api/auth/register`, `/api/auth/login`, `/api/auth/logout`, and protected `/api/users/me`. Project, dataset, visualization, experiment, report, and assistant APIs are documented through OpenAPI at `/api/docs`; all resource access is authorized against the current owner. Visualization responses are bounded, ML training reads secure stored CSV files only inside the worker, reports use persisted analytical results rather than raw rows, and the assistant receives structured aggregates rather than raw dataset rows.

## Project reports

The Reports tab generates an owned, downloadable PDF snapshot. It includes project information, dataset overview, data-quality findings, column profiles, saved visualization configurations, model metrics, model-derived feature importance, and bounded conclusions. Report text explicitly distinguishes statistical association and model behavior from causal claims.

Generated files are stored under the same private project storage boundary as uploaded datasets. `POST /api/reports/{project_id}` generates a report, `GET /api/reports/project/{project_id}` lists report history, and `GET /api/reports/{report_id}/download` performs an authenticated download. Report metadata never exposes the server storage path.

## Machine-learning experiments

The project Model Lab supports classification (logistic regression, decision tree, random forest, gradient boosting), regression (linear regression, ridge, random forest, gradient boosting), and clustering (K-Means, DBSCAN). XGBoost options appear in the model catalog only when the optional `xgboost` package is installed in both API and worker environments.

Supervised experiments create the train/test split before fitting the preprocessing pipeline. Imputers, scalers, and one-hot encoders are therefore fitted only on training rows, then applied unchanged to held-out rows. Clustering has no target or held-out evaluation and fits preprocessing to the selected unsupervised feature matrix.

`POST /api/experiments` persists a queued experiment and dispatches `insightflow.train_experiment`; clients poll `GET /api/experiments/{id}`. Results and per-model metrics remain available through the project history and `/api/experiments/{id}/metrics`.

## Model explainability

Compatible supervised models generate bounded SHAP explanations inside the background training worker. Tree-based estimators use Tree SHAP and linear estimators use Linear SHAP. If a compatible SHAP explainer fails, InsightFlow falls back to held-out permutation importance and explicitly leaves individual contributions unavailable. Clustering explanations are marked unavailable because cluster assignments have no supervised target output to explain reliably.

Each explanation stores original-column global importance, one representative held-out prediction, its observed value, model baseline, signed feature contributions, and input values. One-hot encoded contributions are aggregated back to their original categorical column so the display remains understandable.

The interface labels feature importance as model-derived. It separately explains that correlation measures statistical association and that neither model importance nor correlation establishes causation. InsightFlow does not present these explanations as causal effects.

Saved explanations are included with experiment metrics and available from `GET /api/experiments/{id}/explainability`. Migration `0006_explainability` adds persisted explanation payloads; experiments created before that migration display an explicit rerun message.


