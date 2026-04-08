# CompressorIQ — Compressor Service Intelligence Platform

A production-quality data ingestion and management layer for compressor maintenance records. Ingests historical service data from spreadsheets, normalizes it into a structured PostgreSQL schema, and exposes it via a FastAPI REST API with full import audit traceability.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    DATA INGESTION PIPELINE                              │
│  ┌────────────┐  ┌──────────┐  ┌───────────┐  ┌────────────────────┐  │
│  │ Discovery  │→ │ Workbook │→ │ Mapping & │→ │ Validation &       │  │
│  │ (files)    │  │ Reader   │  │ Normalize │  │ Persistence        │  │
│  └────────────┘  └──────────┘  └───────────┘  └────────────────────┘  │
│  ┌────────────┐  ┌──────────┐  ┌───────────┐  ┌────────────────────┐  │
│  │ Dedup      │  │ Issue    │  │ Audit     │  │ Import Report      │  │
│  │ (hash)     │  │ Logger   │  │ Trail     │  │ Generation         │  │
│  └────────────┘  └──────────┘  └───────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│              DATABASE (PostgreSQL)                                       │
│                                                                         │
│  ┌─── Import Zone ────┐  ┌── Master Zone ──┐  ┌── Event Zone ───────┐ │
│  │ import_batches      │  │ compressors     │  │ service_events      │ │
│  │ import_files        │  │ sites           │  │ service_event_      │ │
│  │ import_sheets       │  │ technicians     │  │   actions/notes/    │ │
│  │ raw_service_rows    │  │ issue_categories│  │   measurements      │ │
│  │ import_issue_log    │  │ action_types    │  │                     │ │
│  └─────────────────────┘  └─────────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    REST API (FastAPI)                                    │
│  POST /api/imports/run           GET /api/imports/{id}                  │
│  GET  /api/imports/{id}/issues   GET /api/service-events               │
│  GET  /api/service-events/{id}   GET /api/compressors                  │
│  GET  /api/compressors/{id}      GET /api/dashboard/summary            │
└─────────────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic |
| Database | PostgreSQL (SQLite for tests) |
| Ingestion | pandas, openpyxl |
| Validation | Pydantic v2 |
| Testing | pytest |

**End-user help:** full manual [`USER_MANUAL.md`](USER_MANUAL.md) (manager + technician); shorter guide [`USER_GUIDE.md`](USER_GUIDE.md). In the app: **User manual** in the sidebar.

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 14+

### 1. Database Setup

```bash
createdb compressoriq
```

### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Configure database URL (edit .env if needed)
# Default: postgresql://postgres:postgres@localhost:5432/compressoriq

# Seed the database with the MC6068 maintenance spreadsheet
python seed_data.py

# Start the API server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### 3. Run Tests

```bash
cd backend
python -m pytest tests/ -v
```

### 4. Run an Import via API

```bash
curl -X POST http://127.0.0.1:8001/api/imports/run \
  -H "Content-Type: application/json" \
  -d '{"source_directory": "path/to/files"}'
```

## API Endpoints

### Import Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/imports/run` | Trigger import from directory or file list |
| GET | `/api/imports/` | List all import batches |
| GET | `/api/imports/{batch_id}` | Batch detail with files and issue counts |
| GET | `/api/imports/{batch_id}/issues` | Paginated issue list (filterable by severity/type) |
| GET | `/api/imports/{batch_id}/files` | Files processed in batch |
| GET | `/api/imports/{batch_id}/raw-rows` | Raw rows for audit |

### Service Events

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/service-events/` | Paginated list with filters |
| GET | `/api/service-events/{id}` | Full detail with actions, notes, measurements |
| GET | `/api/service-events/categories` | Distinct event categories |
| GET | `/api/service-events/stats` | Aggregate statistics |

### Compressors

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/compressors/` | List all compressors |
| GET | `/api/compressors/{id}` | Detail with stats |
| GET | `/api/compressors/{id}/timeline` | Service event timeline |
| GET | `/api/compressors/{id}/issues` | Issue frequency analysis |

### Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/summary` | Overview metrics |
| GET | `/api/dashboard/recent-events` | Latest events |
| GET | `/api/dashboard/recurring-issues` | Top issue categories |

### Recommendations (Intelligence)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/recommendations/generate/{event_id}` | Generate recommendation for event |
| POST | `/api/recommendations/generate` | Generate recommendation for machine |
| GET | `/api/recommendations/machine/{machine_id}` | Historical recommendations |
| GET | `/api/recommendations/{id}` | Full recommendation detail |
| PUT | `/api/recommendations/{id}/status` | Update recommendation status |
| PUT | `/api/recommendations/workflow-step/{id}` | Update workflow step |

### Feedback

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/feedback/` | Submit technician outcome feedback |
| GET | `/api/feedback/event/{event_id}` | Get feedback for an event |
| GET | `/api/feedback/` | List all feedback entries |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics/summary/{machine_id}` | Full analytics summary for a machine |

## Project Structure

```
backend/
├── app/
│   ├── api/routes/
│   │   ├── imports.py            # Import management endpoints
│   │   ├── service_events.py     # Service event CRUD + filtering
│   │   ├── compressors.py        # Compressor asset endpoints
│   │   └── dashboard.py          # Dashboard aggregation
│   ├── core/
│   │   ├── config.py             # Application settings
│   │   └── database.py           # SQLAlchemy engine + session
│   ├── models/
│   │   ├── import_models.py      # Import/audit zone (5 tables)
│   │   ├── master_models.py      # Master/reference zone (6 tables)
│   │   ├── event_models.py       # Core event zone (4 tables)
│   │   └── analytics_models.py   # Future extension hooks (4 tables)
│   ├── schemas/
│   │   ├── import_schemas.py         # Import API schemas
│   │   ├── event_schemas.py          # Event API schemas
│   │   ├── compressor_schemas.py     # Compressor API schemas
│   │   ├── dashboard_schemas.py      # Dashboard schemas
│   │   ├── recommendation_schemas.py # Intelligence API schemas
│   │   └── common.py                 # Shared (pagination)
│   ├── services/
│   │   ├── recommendation_service.py # Intelligence orchestrator
│   │   ├── ingestion/
│   │   │   ├── file_discovery.py     # Stage 1: Find files
│   │   │   ├── workbook_reader.py    # Stage 2-3: Read workbooks
│   │   │   ├── source_mapper.py      # Stage 5: Column mapping
│   │   │   ├── normalizer.py         # Stage 6: Value normalization
│   │   │   ├── validator.py          # Stage 7: Business rules
│   │   │   ├── issue_logger.py       # Stage 9: Issue persistence
│   │   │   ├── deduplication.py      # Stage 7: Duplicate detection
│   │   │   └── import_service.py     # Orchestrator (all stages)
│   │   └── intelligence/
│   │       ├── analytics_service.py  # Layer 1: Descriptive analytics
│   │       ├── rules_engine.py       # Layer 2: Issue inference
│   │       ├── similarity_service.py # Layer 3: Similar case retrieval
│   │       ├── workflow_service.py   # Layer 4: Workflow generation
│   │       ├── confidence_service.py # Layer 5: Confidence scoring
│   │       ├── explanation_service.py# Layer 5b: Evidence explanations
│   │       └── keyword_normalization.py # Action/keyword vocabulary
│   └── utils/
│       └── hashing.py               # SHA-256 file/row fingerprinting
├── alembic/                          # Database migrations
├── tests/
│   ├── test_file_discovery.py        # 4 tests
│   ├── test_normalizer.py            # 28 tests
│   ├── test_validator.py             # 8 tests
│   ├── test_deduplication.py         # 5 tests
│   ├── test_import_pipeline.py       # 8 integration tests
│   ├── test_intelligence.py          # 30+ intelligence layer tests
│   └── test_api_routes.py            # API route integration tests
├── docs/
│   ├── data_model.md
│   ├── import_pipeline.md
│   ├── source_mapping.md
│   └── data_quality_rules.md
├── seed_data.py                      # Database seeding script
├── requirements.txt
└── alembic.ini
```

## Intelligence Engine

The intelligence layer is a 6-layer stack that generates evidence-based maintenance recommendations:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    INTELLIGENCE STACK                                    │
│                                                                         │
│  Layer 1: analytics_service     — action/issue frequency, recurrence   │
│  Layer 2: rules_engine          — issue inference from keywords/rules  │
│  Layer 3: similarity_service    — weighted multi-factor case matching  │
│  Layer 4: workflow_service      — prescriptive step-by-step workflows  │
│  Layer 5: confidence_service    — 6-factor explainable scoring         │
│  Layer 5b: explanation_service  — evidence-based plain-language text   │
│                                                                         │
│  Orchestrator: recommendation_service.py                               │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Features

- **Explainable confidence**: every score breaks down into 6 auditable factors
- **Evidence-based explanations**: every sentence references actual data points
- **Prescriptive workflows**: step-by-step guides with rationale and required evidence
- **Similar case matching**: weighted scoring across machine, category, keywords, recency
- **Recurrence detection**: identifies repeat actions, escalation patterns, chronic issues
- **Fallback behavior**: graceful degradation when data is sparse (low-confidence notes + triage workflows)
- **Feedback loop**: technicians submit outcomes to improve future resolution rate scoring

## Data Model

**23 tables** across 4 zones — see [docs/data_model.md](backend/docs/data_model.md) for full schema.

### Source Data

- **305 rows** from `Unit MC6068 Maintenance.xlsx` (single compressor, 6 years of data)
- **19 source columns**, 5 always empty
- **Rich free-text technician notes** with embedded dates, names, run hours, and action descriptions

### Key Design Decisions

1. **Raw data is always preserved** — `raw_service_rows` stores every source cell as JSON
2. **Every normalized record traces back** — via `import_batch_id`, `import_file_id`, `raw_row_id`
3. **Transformations are explicit** — see [docs/source_mapping.md](backend/docs/source_mapping.md)
4. **Issues are never silently swallowed** — see [docs/data_quality_rules.md](backend/docs/data_quality_rules.md)
5. **Imports are idempotent** — file hash + row fingerprint + order number uniqueness
6. **Schema supports multiple compressors** — even though current data is single-unit

## Development

### Environment Setup

```bash
# Copy example environment file and fill in your values
cp backend/.env.example backend/.env

# Install dependencies
cd backend && pip install -r requirements.txt
```

### Database Migrations

In development, tables are auto-created via `Base.metadata.create_all`.
For production, use Alembic:

```bash
cd backend

# Generate a new migration after model changes
alembic revision --autogenerate -m "description of change"

# Apply migrations
alembic upgrade head
```

### Running Tests

```bash
cd backend

# All tests
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_intelligence.py -v

# With coverage
python -m pytest tests/ --cov=app --cov-report=term-missing
```

### Configuration

All configuration is via environment variables (or `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://...` | Database connection string |
| `UPLOAD_DIR` | `data/uploads` | File upload directory |
| `SOURCE_DATA_DIR` | (empty) | Default data source directory |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `CORS_ORIGINS` | `localhost:3000` | Allowed CORS origins (JSON list) |

## Documentation

- [Data Model](backend/docs/data_model.md) — full schema with all tables and columns
- [Import Pipeline](backend/docs/import_pipeline.md) — 10-stage pipeline design
- [Source Mapping](backend/docs/source_mapping.md) — column-by-column transformation rules
- [Data Quality Rules](backend/docs/data_quality_rules.md) — validation rules and severity levels
