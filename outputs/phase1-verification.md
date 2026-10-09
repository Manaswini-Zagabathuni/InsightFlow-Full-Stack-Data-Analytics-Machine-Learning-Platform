# InsightFlow Phase 1 verification

## Completed scope

- React, TypeScript, Vite, and Tailwind application shell
- FastAPI health endpoint
- SQLAlchemy engine and session configuration
- PostgreSQL and Redis Compose services
- Alembic configuration and Phase 1 baseline migration
- Structured application lifecycle logging
- Environment, Git, Docker, CI, and project documentation

No machine-learning or AI functionality is included.

## Verification results

- Backend tests: 2 passed
- Backend coverage: 93%
- Python dependency check: no broken requirements
- Health endpoint HTTP smoke test: 200 OK and database connected
- Alembic: `0001_initial (head)`
- Frontend test: 1 passed
- TypeScript production build: passed
- Frozen pnpm install: passed after enabling the required esbuild install scripts
- Compose YAML was initially validated for the foundation; the dataset continuation adds the required `worker` service alongside `frontend`, `backend`, `postgres`, and `redis`

## Host limitation

The execution host has no Docker, Docker Compose, Podman, Colima, OrbStack, or Finch binary/daemon. Therefore `docker compose up --build` could not be executed on this host. The Compose service graph, Dockerfiles, health checks, migrations, frontend build, backend runtime, Celery task in eager verification mode, and real HTTP flows were verified independently. Run the documented Compose command on a Docker-enabled machine for the final container-level check.

## Authentication continuation

- Alembic migration `0002_create_users` creates the users table and unique email index.
- Passwords are hashed with bcrypt; response schemas never expose the hash.
- Signed, expiring JWT access tokens protect `/api/users/me` and `/api/auth/logout`.
- Registration, case-insensitive duplicate detection, login, invalid-password handling, missing-token rejection, valid-token access, logout, and validation are tested.
- The frontend includes responsive login/registration screens, protected routes, persistent session restoration, and logout.
- End-to-end API smoke flow passed: register `201`, login `200`, current user `200`, logout `204`.

## Dataset management continuation

- Migration `0003_projects_datasets` creates projects, datasets, and dataset column profiles with ownership foreign keys and cascade behavior.
- CSV files are validated for extension, content type, size, UTF-8 encoding, named/unique headers, and at least one well-formed data row.
- Storage paths use generated user, project, and dataset IDs; client paths never select a destination.
- Celery/Redis handles automatic profiling outside HTTP requests. Profiling persists row/column counts, memory usage, missing values, duplicates, column distributions, IQR outliers, and a transparent quality score.
- The explorer returns at most 100 rows per request and supports pagination, literal search, validated sorting, column information, and per-row missing-value indicators.
- Manual flow passed: register `201` → login `200` → project `201` → upload `202` → profile `ready` with quality `90.5` → filtered/sorted explorer `200`.

## Interactive visualization continuation

- Migration `0004_visualizations` persists project-owned chart configurations while chart values are regenerated from the secure source dataset.
- Bar, line, scatter, histogram, box, donut, and Pearson correlation heatmap payloads are supported.
- Every requested axis and group column is checked against the profiled dataset on the server, with chart-specific numeric and required-axis validation.
- Responses are bounded (points, groups, bins, slices, and outliers) so complete datasets are not sent to the browser.
- The responsive React chart studio includes live column selectors, data-driven Recharts renderers, saved visualization history, reopen, and delete actions.
- Backend suite: 25 passed with 90% aggregate coverage, including all seven chart types, invalid columns/configurations, and ownership.
- Frontend suite: 4 passed. TypeScript production build passed.
- Fresh Alembic upgrade passed through `0004_visualizations (head)`.
- Real HTTP flow passed: health `200` → register `201` → project `201` → CSV upload/profile `202/ready` → scatter save `201` with 9 source points → heatmap save `201` with 16 correlation cells → list 2 saved charts → regenerate saved chart `200` with matching data.

## Machine-learning experimentation continuation

- Migration `0005_experiments` persists experiment configuration, lifecycle status, progress, timestamps, hyperparameters, and per-model metric records.
- Celery/Redis executes training outside FastAPI request workers. The API returns `202` with a queued job, and the frontend polls persisted status/progress.
- Supervised preprocessing is enclosed in each scikit-learn pipeline and fitted after the train/test split; a regression test asserts imputers see only the training-row count.
- Supported classification models: logistic regression, decision tree, random forest, and gradient boosting. Supported regression models: linear regression, ridge, random forest regressor, and gradient boosting regressor. Clustering supports K-Means and DBSCAN.
- XGBoost classifier/regressor options are capability-detected and reported unavailable when the optional package is absent.
- Metrics include accuracy, weighted precision/recall/F1, ROC-AUC where applicable, and confusion matrices for classification; MAE/MSE/RMSE/R² for regression; and silhouette score plus cluster sizes for clustering.
- The responsive Model Lab supports task, target, feature, preprocessing, model, and clustering-parameter selection; live status; comparison tables; and saved experiment history.
- ML-focused backend tests: 10 passed. Complete backend suite: 35 passed with 90% coverage. Frontend suite: 4 passed. Production TypeScript build passed.
- Fresh Alembic upgrade passed through `0005_experiments (head)`.
- Real HTTP flow passed: register `201` → project `201` → CSV upload/profile `202/ready` → two-model classification `202/completed` → two-model regression `202/completed` → K-Means clustering `202/completed` → list 3 saved experiments → reload 2 persisted classification metric records.

## Model explainability continuation

- Migration `0006_explainability` persists explanation payloads with each model metric and safely labels older experiments as requiring a rerun.
- Tree models use Tree SHAP; logistic, linear, and ridge models use Linear SHAP. Computation is bounded to 200 training-background rows and 100 held-out explanation rows.
- One-hot encoded attributions are aggregated back to original dataset columns for understandable global rankings and individual contribution bars.
- A tested held-out permutation-importance fallback supplies global importance if SHAP cannot reliably explain a model; it does not invent individual contributions.
- Clustering explanations are explicitly unavailable because unsupervised cluster labels do not provide a supervised target output for reliable SHAP attribution.
- The frontend shows global model-derived importance, one held-out prediction versus its observed value, baseline-relative feature contributions, and original input values.
- Every panel distinguishes model-derived importance from statistical correlation and states that neither establishes causation.
- Explainability tests cover Tree SHAP, Linear SHAP, persistence and authorization, fallback behavior, clustering behavior, feature aggregation, and non-causal language.
- Complete backend suite: 39 passed with 90% coverage. Frontend suite: 4 passed. Production TypeScript build passed. Fresh migrations reached `0006_explainability (head)`.
- Real HTTP flow passed: dataset upload/profile → decision-tree training `202/completed` → explainability endpoint `200` → Tree SHAP global importance for 4 original features → 4 individual contributions → persisted non-causal warning.

## Optional local assistant continuation

- Added protected `GET /api/assistant/status` and `POST /api/assistant/query` endpoints backed only by a locally configured Ollama server.
- The Ollama integration accepts local hostnames only and has no external API key or paid-provider path.
- Deterministic intent routing limits questions to dataset summaries, missing values, Pearson correlations, basic statistics, saved visualization interpretation, and saved ML experiment summaries.
- The analytics service sends bounded structured JSON: persisted profiles, aggregate correlations, chart digests, metrics, and model-derived importance. It never includes the dataset storage path, complete CSV, or raw rows.
- SQL requests and unsupported general chat are rejected before Ollama invocation. No SQL-generation tool or database execution interface is exposed.
- The React Assistant tab includes availability detection, suggested questions, privacy guidance, local-model labeling, source-section badges, and a clear unavailable state that leaves the rest of the application working.
- Docker Compose reaches a host Ollama service through `host.docker.internal`; Ollama itself remains optional and is not a Compose dependency.
- Assistant-focused backend tests: 13 passed. They cover all six intents, correlation aggregation, privacy guardrails, SQL rejection, unsupported chat, graceful unavailability, continued health, ownership, external-host rejection, real saved visualization/experiment context, and the local Ollama HTTP contract.
- Complete backend suite: 52 passed with 90% aggregate coverage. Dependency consistency check passed.
- Frontend suite: 4 passed. TypeScript production build passed, including the lazy-loaded Assistant panel.
- Docker Compose configuration parsed successfully with backend, frontend, PostgreSQL, Redis, and worker services; the optional host Ollama gateway is configured without adding an Ollama dependency.
- Ollama was not installed or running on the verification host. The available-model and chat paths were verified against a mocked local Ollama API, while the real unavailable path returned a clear `503` and the main health endpoint continued returning `200`.
