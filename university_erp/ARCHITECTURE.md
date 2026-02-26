# University ERP System — Architecture & Guide

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Directory Layout](#directory-layout)
4. [Component Deep-Dive](#component-deep-dive)
5. [Data Flow](#data-flow)
6. [Database Schema](#database-schema)
7. [API Reference](#api-reference)
8. [How to Run](#how-to-run)
9. [Testing](#testing)
10. [Configuration](#configuration)
11. [Security Notes](#security-notes)

---

## Overview

A University Enterprise Resource Planning system built with a multi-layer architecture:

- **Rust (Axum)** — High-performance, type-safe API server handling all CRUD, validation, and database access.
- **FastAPI (Python)** — Lightweight frontend server rendering Jinja2 templates. Proxies all data requests to the Rust API. Never accesses the database.
- **Python Core** — Domain models, ETL pipeline framework, and utility libraries.
- **PostgreSQL** — Relational database with strict constraints and indexing.
- **Docker Compose** — One-command orchestration of all services.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        BROWSER                                │
│                    http://localhost:8000                       │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTP (HTML pages)
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              FastAPI Frontend (port 8000)                      │
│                                                                │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐          │
│  │ dashboard   │  │ students    │  │ courses      │          │
│  │ .html       │  │ .html       │  │ .html        │          │
│  └─────────────┘  └─────────────┘  └──────────────┘          │
│                                                                │
│  Jinja2 templates ─ system fonts ─ minimalist CSS              │
│  Proxies data via httpx to Rust API                            │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTP/JSON (internal)
                       ▼
┌──────────────────────────────────────────────────────────────┐
│               Rust API Server (port 3000)                     │
│                                                                │
│  ┌────────┐ ┌────────────┐ ┌──────────┐ ┌──────────────┐    │
│  │ CRUD   │ │ Validation │ │ Search   │ │ Analytics    │    │
│  │ ops    │ │ & errors   │ │ (ILIKE)  │ │ (aggregates) │    │
│  └────────┘ └────────────┘ └──────────┘ └──────────────┘    │
│  ┌────────────────────────────────────────────┐              │
│  │ AUTH: Argon2 hashing + JWT (24h tokens)    │              │
│  │ Roles: admin | student | faculty           │              │
│  └────────────────────────────────────────────┘              │
│                                                                │
│  Axum + SQLx + Serde + Tower (CORS, tracing)                  │
│  All business logic and data access lives here.                │
└──────────────────────┬───────────────────────────────────────┘
                       │ SQL (connection pool)
                       ▼
┌──────────────────────────────────────────────────────────────┐
│               PostgreSQL 16 (port 5432)                       │
│                                                                │
│  users ─ departments ─ faculty ─ students ─ courses ─         │
│  enrollments ─ etl_runs                                       │
│  UUID PKs ─ CHECK constraints ─ indexes ─ triggers            │
└──────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│     Python ETL Worker (optional, on-demand)         │
│     CSV/JSON/DB extractors, transformers,           │
│     validators, loaders, pipeline orchestrator      │
└────────────────────────────────────────────────────┘
```

---

## Directory Layout

```
university_erp/
│
├── rust_api/                      # Rust backend (Axum)
│   ├── Cargo.toml                 # Dependencies
│   ├── Dockerfile                 # Multi-stage build
│   ├── .env                       # Local dev environment
│   └── src/
│       ├── main.rs                # Entry point, router, DB pool
│       ├── auth.rs                # JWT + Argon2 (register, login, middleware)
│       ├── config.rs              # Env-based configuration
│       ├── db.rs                  # PgPool type alias
│       ├── models.rs              # All structs + DTOs
│       ├── errors.rs              # AppError -> JSON responses
│       └── handlers/
│           ├── mod.rs             # Route mounting
│           ├── students.rs        # CRUD, enroll, grade, search
│           ├── courses.rs         # CRUD with validation
│           ├── departments.rs     # List departments
│           ├── analytics.rs       # Dashboard stats, dept summary
│           └── health.rs          # Liveness probe
│
├── web_app/                       # FastAPI frontend
│   ├── app.py                     # Routes, httpx proxy
│   ├── Dockerfile                 # Uvicorn container
│   ├── requirements.txt           # fastapi, httpx, jinja2
│   ├── static/
│   │   └── style.css              # Minimalist stylesheet
│   └── templates/
│       ├── base.html              # Layout + sidebar nav + user info
│       ├── login.html             # Login form
│       ├── register.html          # Registration form
│       ├── dashboard.html         # Stats + dept table
│       ├── students.html          # Search, add, table
│       ├── courses.html           # Add, table
│       └── departments.html       # Card grid
│
├── python_core/                   # Domain logic + ETL
│   ├── __init__.py
│   ├── base.py                    # Abstract base classes
│   ├── models/
│   │   ├── student.py             # Student domain model
│   │   ├── course.py              # Course domain model
│   │   ├── department.py          # Department domain model
│   │   ├── enrollment.py          # Enrollment domain model
│   │   └── faculty.py             # Faculty domain model
│   ├── etl/
│   │   ├── extractor.py           # CSV, JSON, DB extractors
│   │   ├── transformer.py         # Data transformers
│   │   ├── validator.py           # Schema + data validators
│   │   ├── loader.py              # DB, CSV, JSON loaders
│   │   └── pipeline.py            # ETL orchestrator
│   ├── repository/
│   │   ├── base_repo.py           # PostgresRepository base
│   │   └── student_repo.py        # Student-specific queries
│   ├── services/
│   │   ├── student_service.py     # Student business logic
│   │   └── analytics_service.py   # Analytics aggregation
│   └── utils/
│       ├── exceptions.py          # 12 custom exception types
│       └── logger.py              # Rotating file logger
│
├── database/
│   └── init.sql                   # PostgreSQL schema (7 tables incl. users)
│
├── tests/
│   ├── test_models.py             # 35 model tests
│   ├── test_etl.py                # 24 ETL tests
│   └── test_services.py           # 11 service/exception tests
│
├── config/
│   └── settings.yaml              # Python worker config
│
├── main.py                        # Python ETL worker entry point
├── requirements.txt               # Python deps (pyyaml, psycopg2, pika)
├── Dockerfile                     # Python worker image
├── docker-compose.yml             # Orchestration
└── ARCHITECTURE.md                # This file
```

---

## Component Deep-Dive

### Rust API Server

**Framework:** Axum 0.7 (by the Tokio team)
**Database driver:** SQLx (compile-time checked SQL, async, connection pooling)

Key design decisions:
- All input validation happens at the Rust layer (type-safe with `serde::Deserialize`)
- Every error maps to a structured JSON response via `AppError -> IntoResponse`
- Connection pooling: max 20 connections to Postgres
- CORS enabled for all origins (configurable for production)
- Request tracing via `tower_http::TraceLayer`

**Student handler features:**
- Duplicate email detection before insert
- Enrollment with course capacity validation
- Grade assignment with valid-grade whitelist (A through F)
- ILIKE search across first_name, last_name, email

### FastAPI Frontend

**Framework:** FastAPI with Jinja2 templates
**HTTP client:** httpx (async)

Key design decisions:
- **Zero database access** — all data comes from the Rust API via httpx
- Server-rendered HTML (no JavaScript frameworks, no client-side rendering)
- Forms use standard HTML `<form>` with POST + redirect pattern
- System font stack, white background, 1px gray borders — human-looking design

### Python Core

**Principles:** Strict OOP, encapsulation, no global state

- Abstract base classes define contracts for models, repos, services, and ETL
- ETL components are hot-swappable via `settings.yaml`
- `ChainedTransformer` composes multiple transformers in sequence
- `ETLPipeline` orchestrator dynamically resolves class names from config

### PostgreSQL Schema

6 tables with:
- UUID primary keys (no sequential IDs exposed)
- Foreign key constraints with `ON DELETE CASCADE`
- CHECK constraints (GPA range, credit range, valid status enums)
- B-tree indexes on email, department_id, status
- Auto-updating `updated_at` trigger

---

## Data Flow

### Reading Data (e.g., student list)

```
1. Browser requests GET /students
2. FastAPI receives request
3. FastAPI calls httpx.get("http://rust_api:3000/api/students")
4. Rust handler queries: SELECT * FROM students ORDER BY created_at DESC
5. SQLx returns rows, Serde serializes to JSON
6. FastAPI receives JSON, passes to Jinja2 template
7. Template renders HTML table
8. Browser displays the page
```

### Writing Data (e.g., add student)

```
1. User fills form, submits POST /students/add
2. FastAPI extracts form fields
3. FastAPI calls httpx.post("http://rust_api:3000/api/students", json=data)
4. Rust handler validates input (type checks, duplicate email)
5. SQLx executes INSERT INTO students ... RETURNING *
6. Rust returns 200 with new student JSON
7. FastAPI redirects to GET /students (303)
8. Browser shows updated student list
```

---

## Database Schema

```sql
departments    (id UUID PK, name, code UNIQUE, budget, created_at, updated_at)
      │
      ├──► faculty      (id UUID PK, first_name, last_name, email UNIQUE,
      │                   department_id FK, rank, status, created_at, updated_at)
      │
      ├──► students     (id UUID PK, first_name, last_name, email UNIQUE,
      │                   date_of_birth, department_id FK, gpa CHECK 0-4,
      │                   status, created_at, updated_at)
      │
      └──► courses      (id UUID PK, code UNIQUE, title, department_id FK,
                          credits CHECK 1-6, capacity CHECK > 0,
                          status, created_at, updated_at)

enrollments   (id UUID PK, student_id FK, course_id FK, semester,
               grade, status, created_at, updated_at)
               UNIQUE(student_id, course_id, semester)
```

---

## API Reference

Base URL: `http://localhost:3000/api`

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create account (username, email, password, role) |
| POST | `/auth/login` | Login → returns JWT token (24h) |
| GET | `/auth/me` | Get current user (requires Bearer token) |

### Data (all routes)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/students` | List students (pagination: `?limit=50&offset=0`) |
| GET | `/students/:id` | Get single student |
| POST | `/students` | Create student |
| PUT | `/students/:id` | Update student |
| DELETE | `/students/:id` | Remove student |
| POST | `/students/:id/enroll` | Enroll in course |
| POST | `/students/:id/grade` | Assign grade |
| GET | `/students/search/:q` | Search by name/email |
| GET | `/courses` | List courses |
| GET | `/courses/:id` | Get single course |
| POST | `/courses` | Create course |
| PUT | `/courses/:id` | Update course |
| DELETE | `/courses/:id` | Remove course |
| GET | `/departments` | List departments |
| GET | `/faculty` | List faculty with pagination |
| GET | `/faculty/:id` | Get single faculty member |
| GET | `/enrollments` | List enrollments / retrieve student's enrollments |
| POST | `/enrollments/enroll` | Enroll a student in a course |
| DELETE | `/enrollments/:id/drop` | Drop an enrollment |
| GET | `/analytics/dashboard` | Stats (totals, avg GPA) |
| GET | `/analytics/departments` | Per-department summary |
| GET | `/analytics/top-students` | Students with GPA >= 3.5 |
| GET | `/health` | Service + DB health check |

### Request/Response Examples

**Create student:**
```json
POST /api/students
{
  "first_name": "Farhan",
  "last_name": "Umar",
  "email": "farhan@university.edu",
  "date_of_birth": "2000-01-15"
}
```

**Enroll in course:**
```json
POST /api/students/{id}/enroll
{
  "course_id": "uuid-of-course",
  "semester": "Spring 2026"
}
```

**Assign grade:**
```json
POST /api/students/{id}/grade
{
  "course_id": "uuid-of-course",
  "grade": "A"
}
```

---

## How to Run

### Prerequisites

- [Docker Desktop](https://docker.com/products/docker-desktop/) installed and running.

### Start Everything

```bash
cd "university_erp"
docker compose up -d
```

This starts 3 services:

| Service | URL | Purpose |
|---------|-----|---------|
| PostgreSQL | `localhost:5432` | Database (auto-creates schema) |
| Rust API | `localhost:3000` | Backend API |
| FastAPI | `localhost:8000` | Web frontend |

### First boot

The first `docker compose up` will:
1. Pull Postgres 16 Alpine image
2. Build the Rust binary inside Docker (~2–3 min first time)
3. Build the FastAPI image (~30 sec)
4. Run `database/init.sql` to create all 6 tables
5. Start all services

### Open the Dashboard

```
http://localhost:8000
```

You'll be redirected to the **login page**. Register a new account or sign in.

Pages available (after login):
- `/login` — Login page
- `/register` — Create account (choose role: student/faculty/admin)
- `/` — Dashboard (stats + department table)
- `/students` — Student list, search, add
- `/courses` — Course list, add
- `/faculty` — Faculty list with rank/status
- `/enrollments` — View/manage enrollments (role-gated)
- `/departments` — Department cards
- `/logout` — Sign out

### Useful Commands

```bash
# See logs
docker compose logs -f

# See just Rust API logs
docker compose logs rust_api -f

# Check API health
curl http://localhost:3000/api/health

# Stop everything
docker compose down

# Stop + delete database data
docker compose down -v

# Run Python tests
python -m pytest tests/ -v

# Run ETL worker (optional)
docker compose --profile etl up python_worker
```

---

## Testing

### Python Core Tests

```bash
python -m pytest tests/ -v
```

**70 tests, 3 suites:**

| Suite | Tests | Coverage |
|-------|-------|----------|
| `test_models.py` | 35 | All 5 domain models — creation, validation, business logic, serialization |
| `test_etl.py` | 24 | All extractors, transformers, validators, loaders, pipeline |
| `test_services.py` | 11 | Exception hierarchy, ValidationResult |

### API Testing (Manual)

```bash
# Create a department first
curl -X POST http://localhost:3000/api/departments -H "Content-Type: application/json" \
  -d '{"name":"Computer Science","code":"CS","budget":2400000}'

# Create a student
curl -X POST http://localhost:3000/api/students -H "Content-Type: application/json" \
  -d '{"first_name":"Farhan","last_name":"Umar","email":"farhan@uni.edu","date_of_birth":"2000-01-15"}'

# List students
curl http://localhost:3000/api/students

# Dashboard stats
curl http://localhost:3000/api/analytics/dashboard
```

---

## Configuration

### Rust API (environment variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `API_PORT` | `3000` | Server port |
| `RUST_LOG` | `info` | Log level (debug, info, warn, error) |
| `JWT_SECRET` | `erp-jwt-secret-change-in-prod` | Secret for signing JWT tokens |

### FastAPI (environment variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `RUST_API_URL` | `http://localhost:3000` | Rust API base URL |

### Python Worker (settings.yaml)

Controls ETL pipeline module registry, database connection, and logging. Supports `${VAR:-default}` syntax for environment variable overrides.

---

## Security Notes

- **JWT authentication** — users must login to access any page; tokens expire in 24 hours
- **Argon2 password hashing** — industry-standard, memory-hard algorithm (no bcrypt/MD5)
- **Role-based access** — users are admin, student, or faculty (middleware available: `require_auth`, `require_admin`)
- **httpOnly cookies** — JWT stored as httpOnly cookie, not in localStorage (XSS-safe)
- Database credentials are environment variables, never hardcoded in source
- All input validation happens in the Rust layer (type-safe deserialization)
- Duplicate detection prevents conflicting records (email/username uniqueness)
- UUID primary keys prevent ID enumeration attacks
- CORS is enabled (restrict `allow_origin` for production)
- SQL injection is prevented by SQLx parameterized queries (no string concatenation)
- FastAPI never touches the database — even if compromised, the Rust API validates everything

### Future improvements

- HTTPS termination via reverse proxy (nginx/caddy)
- Audit logging for data changes
- Password reset flow
