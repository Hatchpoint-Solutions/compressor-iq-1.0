# CompressorIQ — Prioritized Enhancement Backlog

Last updated: 2026-03-29

## Priority 1: Critical (Production Blockers)

### 1.1 Authentication & Authorization
- Add JWT or OAuth2 bearer token authentication
- Role-based access control (admin, technician, viewer)
- Protect all mutation endpoints (POST, PUT, DELETE)
- Rate limiting on recommendation generation endpoints
- **Effort**: Medium | **Impact**: High

### 1.2 Alembic Migration Baseline
- Generate initial migration from current models (`alembic revision --autogenerate`)
- Stop relying on `create_all` in production
- Add migration CI check (ensure `alembic check` passes before deploy)
- **Effort**: Low | **Impact**: High

### 1.3 Docker & Deployment
- Add `Dockerfile` for backend (multi-stage build)
- Add `docker-compose.yml` for local dev (app + PostgreSQL)
- Add `Dockerfile` for frontend (Next.js)
- Health check endpoint already exists — wire into container health
- **Effort**: Medium | **Impact**: High

### 1.4 CI/CD Pipeline
- GitHub Actions workflow: lint → test → build → deploy
- Run `pytest` on PR merge
- Run `alembic check` to catch migration drift
- Lint with `ruff` or `flake8`
- **Effort**: Medium | **Impact**: High

---

## Priority 2: High (Quality & Reliability)

### 2.1 Request Logging Middleware
- Log method, path, status code, duration for every request
- Correlation ID header for tracing across services
- **Effort**: Low | **Impact**: Medium

### 2.2 Input Validation Hardening
- Validate path parameter formats (UUID format for IDs)
- Add max length constraints on free-text request fields
- Validate `source_directory` path doesn't traverse outside allowed dirs
- **Effort**: Low | **Impact**: Medium

### 2.3 Test Coverage Gaps
- Add tests for `service_events/stats` endpoint (uses PostgreSQL-specific `to_char`)
- Add tests for import pipeline via API (`POST /api/imports/run`)
- Add tests for `analytics` routes
- Add edge case tests: empty DB, concurrent imports
- Add test for `_SkipRow` exception path in import pipeline
- Target: 80%+ line coverage
- **Effort**: Medium | **Impact**: High

### 2.4 Database Connection Resilience
- Add connection retry logic on startup
- Add health check that verifies DB connectivity
- Consider connection pool monitoring
- **Effort**: Low | **Impact**: Medium

### 2.5 Split `import_service.py` (668 Lines)
- Extract `_normalise_and_persist` into a dedicated `persistence_service.py`
- Extract `ImportReport` into `import_report.py`
- Keep orchestrator thin — delegates to specialized modules
- **Effort**: Medium | **Impact**: Medium

---

## Priority 3: Medium (Feature Enhancements)

### 3.1 Vector/Embedding Similarity Search
- Add sentence-transformer embeddings for technician notes
- Store embeddings in pgvector column
- Augment `similarity_service.py` scoring with embedding distance
- Expected: significant improvement in cross-machine case matching
- **Effort**: High | **Impact**: High

### 3.2 Feedback-Driven Learning
- Use `FeedbackOutcome` data to weight action recommendations
- Compute per-issue-category resolution rates from feedback
- Boost recommended actions that historically resolve issues
- **Effort**: Medium | **Impact**: High

### 3.3 Multi-Compressor Import Support
- Test with multiple compressor units in one spreadsheet
- Ensure `compressor_type` and `model` are populated from data
- Add compressor family analytics (cross-fleet patterns)
- **Effort**: Medium | **Impact**: Medium

### 3.4 Frontend Test Coverage
- Add Vitest/Jest for React component tests
- Add Playwright/Cypress for E2E browser tests
- **Effort**: Medium | **Impact**: Medium

### 3.5 API Versioning
- Add `/api/v1/` prefix to all routes
- Document versioning strategy in README
- **Effort**: Low | **Impact**: Low

### 3.6 Async Database Operations
- Migrate from sync SQLAlchemy to async (`asyncpg` + `AsyncSession`)
- Use `async def` route handlers
- Benefits: better concurrent request handling under load
- **Effort**: High | **Impact**: Medium

---

## Priority 4: Low (Nice-to-Have)

### 4.1 OpenAPI Schema Enhancements
- Add request/response examples to all schemas
- Add operation IDs to all routes
- Generate SDK from OpenAPI spec
- **Effort**: Low | **Impact**: Low

### 4.2 Monitoring & Observability
- Add Prometheus metrics endpoint
- Track recommendation generation latency
- Track import pipeline throughput
- Dashboard with Grafana or similar
- **Effort**: Medium | **Impact**: Medium

### 4.3 Data Export
- CSV export endpoint for service events
- PDF report generation for recommendations
- **Effort**: Medium | **Impact**: Low

### 4.4 Notification System
- Alert on high-severity recurrence signals
- Email/Slack notification when confidence is low
- **Effort**: Medium | **Impact**: Low

### 4.5 Typing Consistency
- Standardize on `X | None` (Python 3.10+) throughout codebase
- Remove all `Optional[X]` usage for consistency
- Add `py.typed` marker for downstream type checking
- **Effort**: Low | **Impact**: Low

---

## Technical Debt Inventory

| Item | Location | Severity | Notes |
|------|----------|----------|-------|
| Circular imports resolved via bottom-of-file imports | `models/*.py` | Low | Works but fragile; consider registry pattern |
| `normalizer_mod()` lazy import hack | `import_service.py:664` | Low | Indicates tight coupling |
| `_SkipRow` exception for flow control | `import_service.py` | Low | Now properly caught; consider return-value approach |
| `RecommendationResponse` field aliases | `recommendation_schemas.py` | Low | `reasoning` vs `explanation` naming is confusing |
| SQLite vs PostgreSQL test divergence | `conftest.py` vs prod | Medium | `to_char` in stats endpoint only works on Postgres |
| No request timeout / cancel support | Routes | Medium | Long imports can hang without timeout |
| `test_api.py` is a manual script | `backend/test_api.py` | Low | Should be converted to pytest or removed |
