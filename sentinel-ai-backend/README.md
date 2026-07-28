# Sentinel AI Backend — Phase 1

FastAPI backend foundation: async PostgreSQL, JWT security helpers, structured logging, health checks.

## Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation)
- Docker + Docker Compose (for containerised setup)

---

## Local Setup

### 1. Install dependencies

```bash
poetry install
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — set SECRET_KEY and DATABASE_URL at minimum
```

Generate a secure secret key:

```bash
openssl rand -hex 32
```

### 3. Start the database (Docker)

```bash
docker compose up db -d
```

### 4. Run migrations

```bash
poetry run alembic upgrade head
```

### 5. Start the API

```bash
poetry run uvicorn app.main:app --reload
```

The API is now available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

---

## Docker Compose (full stack)

```bash
cp .env.example .env   # edit SECRET_KEY
docker compose up --build
```

This starts exactly two containers: `api` (port 8000) and `db` (port 5432).  
Migrations run automatically before the API starts.

---

## Health Check Endpoints

```bash
# Application health
curl http://localhost:8000/api/v1/health

# Database health
curl http://localhost:8000/api/v1/health/db
```

Expected responses:

```json
// GET /api/v1/health → 200
{"status": "ok", "app_name": "Sentinel AI", "version": "0.1.0"}

// GET /api/v1/health/db → 200 (DB up) or 503 (DB down)
{"status": "ok", "database": "reachable"}
```

---

## Running Tests

Tests require a running PostgreSQL instance. Set `TEST_DATABASE_URL` or ensure the default
(`postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel_ai_test`) is reachable.

```bash
# Create the test database first
psql -U sentinel -c "CREATE DATABASE sentinel_ai_test;"

# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --tb=short -v
```

---

## Linting & Type Checking

```bash
poetry run ruff check .
poetry run mypy app/
```

---

## Project Structure

```
app/
├── main.py              # App factory, lifespan, middleware registration
├── core/
│   ├── config.py        # pydantic-settings, lru_cache
│   ├── logging.py       # structlog configuration
│   ├── security.py      # password hashing, JWT helpers
│   └── exceptions.py    # typed HTTP exceptions
├── api/
│   ├── deps.py          # shared FastAPI dependencies
│   └── v1/
│       ├── router.py    # aggregates all v1 routers
│       └── endpoints/
│           ├── health.py   # GET /health, GET /health/db
│           └── auth.py     # STUB: POST /auth/register, /auth/login
├── db/
│   ├── base.py          # DeclarativeBase + model imports
│   ├── session.py       # async engine + get_db()
│   └── init_db.py       # startup connectivity check
├── models/user.py       # User SQLAlchemy model
├── schemas/user.py      # UserCreate, UserRead, UserInDB
├── repositories/        # async CRUD (get_by_id, get_by_email, create)
├── services/            # thin service layer over repositories
└── middleware/
    ├── request_id.py    # X-Request-ID propagation
    └── error_handler.py # global JSON error shape
```
