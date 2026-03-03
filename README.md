# Real time Database pipeline simulator 

## Architecture

```
Browser ──► FastAPI (8000) ──► Rust API (3000) ──► PostgreSQL
                ↕ WebSocket           ↕ AMQP
            Live Terminal      RabbitMQ ──► Python Worker
```

| Service | Tech | Role |
|---------|------|------|
| **Rust API** | Axum, SQLx, Lapin | REST API, WebSocket broadcast, RabbitMQ publisher |
| **Python Worker** | Pika, Psycopg2 | Consumes tasks, generates fake data, bulk inserts |
| **Web Frontend** | FastAPI, Jinja2 | Server-rendered UI, REST/WebSocket proxy |
| **Database** | PostgreSQL 16 | 7 tables with UUID PKs, constraints, and triggers |
| **Message Queue** | RabbitMQ 3 | Decouples API from data generation pipeline |

## Features

- **Live Execution Terminal** — WebSocket-powered real-time log stream during data ingestion
- **Data Ingestion Simulator** — Generate 10 to 100K student records with one click
- **System Analysis Dashboard** — Live CPU, memory, and TCP connection charts
- **Full CRUD API** — Students, courses, departments, faculty, enrollments
- **JWT Authentication** — Argon2 password hashing with role-based access (admin/student/faculty)
- **Analytics** — Dashboard stats, per-department summaries, top students by GPA

## Quick Start

### Prerequisites

- [Docker Desktop](https://docker.com/products/docker-desktop/)

### Run

```bash
cd university_erp
docker compose up -d
```

First boot builds the Rust binary (~3 min) and sets up everything automatically.

Open **http://localhost:8000** → click a batch size → watch the terminal stream logs in real-time.

### GitHub Codespaces

Click **Code → Codespaces → Create codespace on master**. The devcontainer auto-builds everything. Open the forwarded **port 8000** when ready.

## Services

| URL | Service |
|-----|---------|
| http://localhost:8000 | Web UI (Terminal Simulator, System Analysis) |
| http://localhost:3000/api | Rust REST API |
| http://localhost:15672 | RabbitMQ Management (guest/guest) |
| http://localhost:5432 | PostgreSQL (erp_admin/erp_secret_2026) |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/students` | List students (`?limit=50&offset=0`) |
| POST | `/api/students` | Create student |
| PUT | `/api/students/:id` | Update student |
| DELETE | `/api/students/:id` | Remove student |
| POST | `/api/students/:id/enroll` | Enroll in course |
| POST | `/api/students/:id/grade` | Assign grade |
| GET | `/api/courses` | List courses |
| POST | `/api/courses` | Create course |
| GET | `/api/departments` | List departments |
| GET | `/api/faculty` | List faculty |
| GET | `/api/enrollments` | List enrollments |
| POST | `/api/enrollments/enroll` | Enroll student |
| GET | `/api/analytics/dashboard` | Dashboard stats |
| GET | `/api/analytics/departments` | Per-department summary |
| GET | `/api/analytics/top-students` | Top GPA students |
| POST | `/api/simulate` | Dispatch data generation job |
| GET | `/api/ws` | WebSocket (live metrics stream) |
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Login → JWT |
| GET | `/api/health` | Health check |

## Data Pipeline

```
Click "10K" → Rust API publishes to RabbitMQ → Python Worker consumes
→ Generates 10K fake students → Bulk INSERT into PostgreSQL
→ Worker publishes metrics to RabbitMQ → Rust broadcasts via WebSocket
→ Browser terminal shows real-time logs
```

## Project Structure

```
university_erp/
├── rust_api/src/          Axum API server (auth, handlers, models)
├── web_app/               FastAPI frontend (templates, static, proxy)
├── python_core/           Domain models, ETL, repositories, services
├── database/              init.sql (schema) + seed.sql (sample data)
├── .devcontainer/         GitHub Codespaces config
├── main.py                Python worker entry point
├── docker-compose.yml     All 5 services orchestrated
└── config/settings.yaml   Python worker configuration
```

## Tech Stack

**Backend:** Rust (Axum, SQLx, Lapin, Argon2, JWT) · Python (Pika, Psycopg2, Faker)
**Frontend:** FastAPI · Jinja2 · Vanilla JS · Chart.js
**Infrastructure:** Docker Compose · PostgreSQL 16 · RabbitMQ 3 · WebSockets

## Commands

```bash
docker compose up -d              # Start all services
docker compose logs -f            # Watch all logs
docker compose logs rust_api -f   # Watch Rust API logs
docker compose down               # Stop everything
docker compose down -v            # Stop + delete database
docker compose build rust_api     # Rebuild after code changes
python -m pytest tests/ -v        # Run Python tests (70 tests)
```

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — detailed architecture guide, data flow, and security notes
- [SCALABILITY_BLUEPRINT.md](SCALABILITY_BLUEPRINT.md) — scaling strategies and design patterns
