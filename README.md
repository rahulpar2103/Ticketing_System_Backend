# SupportFlow - Internal Help Desk API

A production-grade backend REST API for managing internal support tickets. Built with **FastAPI** and **PostgreSQL**, it features role-based access control across three user tiers, real-time WebSocket updates, SLA tracking, S3 file attachments, async email delivery via Celery, and a comprehensive test suite - all containerized with Docker and deployed with CI/CD.

**Live API:** [https://ticketing-system-backend-wpux.onrender.com](https://ticketing-system-backend-wpux.onrender.com)
&nbsp;|&nbsp; **Frontend Repo:** [Ticketing_System_Frontend](https://github.com/Anonymous21-03/Ticketing_System_Frontend)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Language | Python 3.12+ |
| ORM | SQLAlchemy 2.0 (Core + ORM) |
| Database | PostgreSQL 15 |
| Migrations | Alembic |
| Caching | Redis 7 |
| Auth | JWT (PyJWT) + bcrypt via passlib, token blacklisting via Redis |
| Validation | Pydantic v2, pydantic-settings |
| Rate Limiting | slowapi |
| Testing | pytest (209+ tests), FastAPI TestClient |
| File Storage | AWS S3 (presigned URL upload/download) |
| Email | SMTP (AWS SES) via Celery async tasks |
| Task Queue | Celery with Redis broker |
| Real-time | WebSockets + Redis Pub/Sub |
| Logging | Structured JSON logging (custom formatter) |
| Containerization | Docker, Docker Compose |
| CI/CD | GitHub Actions (automated test suite on every push/PR) |
| Deployment | Render (backend), Vercel (frontend) |

---

## Features

### Authentication & Security
- JWT token-based authentication with login via username or email
- Token revocation/logout via Redis blocklist - revoked tokens are rejected on subsequent requests
- Role-based access control enforced at the **service layer**, not just routes - business logic is testable without HTTP
- Per-endpoint rate limiting (e.g., 5/min on login, 30/min on reads, 20/min on mutations)

### Ticket Lifecycle & SLA
- Four-status state machine: `open → in_progress → resolved → closed` with role-specific transition rules
- SLA management: auto-calculates `due_at` deadlines based on priority tiers (low: 48h, medium: 24h, high: 12h, urgent: 4h)
- Lazy SLA breach detection: marks overdue tickets as breached on query
- `resolved_at` timestamp auto-recorded when status transitions to resolved

### Real-Time Updates
- WebSocket endpoint with JWT-based authentication
- Redis Pub/Sub broadcasts ticket creates, updates, deletes, and comment events to all connected clients
- Frontend receives instant toast notifications and live data refreshes

### File Attachments
- S3-backed file upload using two-step presigned URL flow (presign → upload to S3 → confirm)
- Presigned download URLs generated on demand for secure, time-limited access
- Uploader or admin can delete attachments (S3 object + DB record)

### RBAC - Three User Roles

| Capability | Admin | Agent | Employee |
|---|:---:|:---:|:---:|
| Create user accounts | ✅ | ❌ | ❌ |
| View/manage all users, teams, tickets | ✅ | ❌ | ❌ |
| Manage tickets within assigned team | ✅ | ✅ | ❌ |
| Assign/reassign tickets to team members | ✅ | ✅ | ❌ |
| Create tickets and comment on own tickets | ✅ | ✅ | ✅ |
| Change priority | ✅ | ✅ | ❌ |
| Set any status freely | ✅ | ❌ | ❌ |
| Status transitions (strict state machine) | - | ✅ | Limited |

> **Agent transitions:** `open → in_progress → resolved → closed` (strict sequential)
> **Employee transitions:** `open → closed`, `resolved → closed` only

### Soft Deletes & Reactivation
- Users, teams, and tickets are never hard-deleted - `is_active = false` removes them from queries
- Team deletion cascades: clears `team_id` and `assigned_to` on affected users/tickets
- Admin-only reactivation endpoints to restore any soft-deleted resource

### Search, Filter & Pagination
- Full-text search on tickets (title + description) and users (name, username, email)
- Multi-value filters: status, priority, role, team, active status (comma-separated)
- Configurable sorting with `sort_by` and `order` on all list endpoints
- Paginated response format: `{ items, total, limit, offset, has_more }`

### Audit Trails
- Records `CREATED`, `UPDATED`, and `DELETED` events with JSON change diffs
- Ticket operation and audit log commit in a single DB transaction
- Viewable per-ticket audit history endpoint with role-scoped access

### Email & Background Tasks
- Welcome emails sent asynchronously on user creation via Celery + Redis
- HTML email templates with credentials delivered through AWS SES SMTP
- Celery worker runs alongside the API in the Docker entrypoint

### Observability
- Structured JSON request logging with method, path, status code, response time, and client IP
- Custom exception hierarchy with centralized handlers - all errors return consistent JSON responses
- Health check endpoint (`GET /health`) probes API, PostgreSQL, and Redis connectivity

---

## Folder Structure

```
.
├── app/
│   ├── alembic/                  # Alembic migration scripts
│   ├── core/
│   │   ├── celery_app.py         # Celery configuration (Redis broker)
│   │   ├── config.py             # pydantic-settings from .env
│   │   ├── email.py              # SMTP email sender + HTML templates
│   │   ├── exceptions.py         # Custom exception classes (8 types)
│   │   ├── limiter.py            # slowapi rate limiter instance
│   │   ├── logger.py             # Structured JSON log formatter
│   │   ├── s3.py                 # boto3 S3 helpers (presign, head, delete)
│   │   ├── security.py           # Password hashing, JWT encode/decode
│   │   ├── sla.py                # SLA tier calculations + breach updater
│   │   └── websocket.py          # WebSocket manager + Redis Pub/Sub listener
│   ├── db/
│   │   ├── database.py           # SQLAlchemy engine, session, Base
│   │   └── redis.py              # Redis client + safe_* helper wrappers
│   ├── dependencies/             # FastAPI DI: get_db(), get_current_user()
│   ├── models/                   # SQLAlchemy ORM models (6 tables)
│   ├── routers/                  # API route definitions (8 modules)
│   ├── schemas/                  # Pydantic request/response schemas
│   ├── services/                 # Business logic split by role (admin/agent/employee)
│   └── tasks/                    # Celery async tasks (email)
├── tests/                        # pytest test suite (14 test files)
├── scripts/seed.py               # Database seeder (5 teams, 15 users, 13 tickets)
├── .github/workflows/ci-cd.yml   # GitHub Actions CI pipeline
├── Dockerfile                    # Python 3.14-slim container
├── docker-compose.yml            # FastAPI + PostgreSQL + Redis
├── entrypoint.sh                 # Runs migrations, starts Celery + Uvicorn
└── requirements.txt
```

---

## Setup and Installation

### Prerequisites

- Python 3.12+
- PostgreSQL (two databases: one for dev, one for tests)
- Redis

### Install Dependencies

```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

### Environment Variables

Copy the template and fill in your values:

```bash
cp app/.env.example app/.env
```

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg2://user:pass@localhost:5432/ticketing_db` |
| `TEST_DATABASE_URL` | Test database connection | `postgresql+psycopg2://user:pass@localhost:5432/ticketing_test` |
| `SECRET_KEY` | JWT signing key (min 32 chars) | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `AWS_ACCESS_KEY_ID` | AWS credentials for S3 | `AKIA...` |
| `S3_BUCKET_NAME` | S3 bucket for attachments | `my-ticketing-attachments` |
| `SMTP_HOST` | AWS SES SMTP endpoint | `email-smtp.us-east-1.amazonaws.com` |

---

## Running the App

### Option 1: Local

```bash
uvicorn app.main:app --reload
```

### Option 2: Docker (Recommended)

```bash
docker compose up -d
docker compose logs -f web

# Run tests inside the container
docker compose exec web pytest

# Seed sample data
docker compose exec web python scripts/seed.py
```

| URL | Description |
|---|---|
| `http://localhost:8000/docs` | Interactive Swagger UI |
| `http://localhost:8000/redoc` | ReDoc API documentation |
| `http://localhost:8000/health` | Health check (API + DB + Redis) |

---

## API Endpoints

### Auth

| Method | Endpoint | Description | Auth |
|---|---|---|:---:|
| `POST` | `/auth/login` | Login (username/email + password) | No |
| `POST` | `/auth/logout` | Revoke token via Redis blocklist | Yes |
| `POST` | `/auth/register` | Create user (triggers async welcome email) | Admin |

### Users - 8 endpoints

`GET /users/me` · `GET /users` · `GET /users/{id}` · `PATCH /users/{id}` · `DELETE /users/{id}` · `PATCH /users/{id}/reactivate` · `PATCH /users/{id}/password` · `PATCH /users/{id}/reset-password`

### Teams - 8 endpoints

`POST /teams` · `GET /teams` · `GET /teams/{id}` · `PUT /teams/{id}` · `DELETE /teams/{id}` · `PATCH /teams/{id}/reactivate` · `GET /teams/{id}/stats` · `GET /teams/{id}/members`

### Tickets - 12 endpoints

`POST /tickets` · `GET /tickets` · `GET /tickets/created-by-me` · `GET /tickets/assigned-to-me` · `GET /tickets/team/{id}` · `GET /tickets/user/{id}/assigned` · `GET /tickets/stats` · `GET /tickets/{id}` · `PATCH /tickets/{id}` · `DELETE /tickets/{id}` · `PATCH /tickets/{id}/reactivate` · `GET /tickets/{id}/history`

### Comments - 5 endpoints

`POST /tickets/{id}/comments` · `GET /tickets/{id}/comments` · `GET /comments/{id}` · `PATCH /comments/{id}` · `DELETE /comments/{id}`

### Attachments - 5 endpoints

`POST /tickets/{id}/attachments/presign` · `POST /tickets/{id}/attachments/{aid}/confirm` · `GET /tickets/{id}/attachments` · `GET /tickets/{id}/attachments/{aid}/download` · `DELETE /tickets/{id}/attachments/{aid}`

### WebSocket

`WS /ws?token=<jwt>` - Authenticated WebSocket for real-time ticket and comment updates

---

## Testing

Tests use a separate PostgreSQL database with per-test transaction rollback. Redis is auto-mocked.

```bash
pytest -v
```

| Test File | Covers |
|---|---|
| `test_auth_service.py` / `test_auth_routes.py` | User creation, login, duplicate detection, HTTP endpoints |
| `test_user_services.py` / `test_user_routes.py` | CRUD for all 3 roles, password changes |
| `test_team_services.py` / `test_team_routes.py` | Create, read, update, delete, members, cascade |
| `test_ticket_services.py` / `test_ticket_routes.py` | CRUD, status transitions, assignment rules |
| `test_comment_services.py` / `test_comment_routes.py` | CRUD, ownership checks |
| `test_sla.py` | SLA tier calculations, breach detection |
| `test_schemas.py` | Pydantic field validation, length limits |
| `test_security.py` | JWT creation, verification, expiry, password hashing |

### CI/CD

GitHub Actions runs the full test suite on every push and PR to `master` with containerized PostgreSQL and Redis service containers.

---

## Seeding Sample Data

```bash
python scripts/seed.py
```

All seeded users share the password: `Password@123`

| Role | Usernames |
|---|---|
| Admin | `rahul`, `priya` |
| Agent | `ankit`, `sneha`, `rohan`, `kavita`, `arun`, `meera`, `vikram` |
| Employee | `deepak`, `pooja`, `suresh`, `nisha`, `amit`, `lakshmi` |
