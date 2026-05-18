# Help Desk Ticket Management System

A backend REST API for managing support tickets in an organization. Built with FastAPI, it implements role-based access control across three user roles (**admin**, **agent**, and **employee**) with Redis caching, JWT authentication, and per-role business logic enforced at the service layer.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Folder Structure](#folder-structure)
- [Setup and Installation](#setup-and-installation)
- [Environment Variables](#environment-variables)
- [Running the App](#running-the-app)
- [Database Migrations](#database-migrations)
- [API Usage](#api-usage)
- [Testing](#testing)
- [Implementation Details](#implementation-details)
- [Future Improvements](#future-improvements)

---

## Overview

This system allows employees to raise support tickets, agents to manage and resolve them within their team scope, and admins to oversee everything. Each role has its own set of routes, enforced both at the router and the service layer. The project follows a clean separation of concerns: routers handle HTTP, services hold all business logic, and schemas govern validation.

---

## Features

- **JWT Authentication**: login with username or email; tokens are verified on every protected route
- **Role-Based Access Control**: three roles (admin, agent, employee) each with strictly scoped permissions
- **Ticket Lifecycle Management**: state machine for ticket status transitions; agents follow `open → in_progress → resolved → closed`
- **Redis Caching**: list and detail responses are cached with prefix-based invalidation on mutations
- **Rate Limiting**: per-endpoint rate limits via `slowapi` (e.g., 5/min on login, 30/min on reads)
- **Soft Deletes**: users, teams, and tickets are deactivated via `is_active` flag rather than hard-deleted
- **Background Tasks**: welcome emails are sent asynchronously on user creation
- **Paginated Responses**: all list endpoints accept `limit` and `offset` query params
- **Alembic Migrations**: schema changes are versioned and reproducible

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| ORM | SQLAlchemy (Core + ORM) |
| Database | PostgreSQL |
| Migrations | Alembic |
| Caching | Redis |
| Auth | JWT (`PyJWT`), `passlib` + `bcrypt` |
| Validation | Pydantic v2 |
| Rate Limiting | `slowapi` |
| Testing | `pytest`, `FastAPI TestClient` |
| Settings | `pydantic-settings` (`.env` file) |

---

## Folder Structure

```
.
├── app/
│   ├── alembic/                  # Migration scripts
│   │   └── versions/             # One file per migration
│   ├── core/
│   │   ├── config.py             # Settings loaded from .env
│   │   ├── email.py              # Email sending (stub/background task)
│   │   ├── exceptions.py         # Custom exception classes
│   │   ├── limiter.py            # slowapi Limiter instance
│   │   └── security.py           # Password hashing, JWT encode/decode
│   ├── db/
│   │   ├── database.py           # SQLAlchemy engine, session, Base
│   │   └── redis.py              # Redis client + safe helper functions
│   ├── dependencies/
│   │   ├── db.py                 # get_db() dependency
│   │   └── user.py               # get_current_user() dependency
│   ├── models/
│   │   ├── commentModel.py
│   │   ├── teamModel.py
│   │   ├── ticketModel.py
│   │   └── userModel.py
│   ├── routers/
│   │   ├── commentRouters/       # admin.py, agent.py, employee.py
│   │   ├── teamRouters/          # admin.py, agent.py, employee.py
│   │   ├── ticketRouters/        # admin.py, agent.py, employee.py
│   │   ├── userRouters/          # admin.py, agent.py, employee.py, auth.py
│   │   └── mainRouter.py         # Aggregates all routers
│   ├── schemas/
│   │   ├── commentSchema.py
│   │   ├── teamSchema.py
│   │   ├── ticketSchema.py
│   │   └── userSchema.py
│   ├── services/
│   │   ├── commentService/       # admin.py, agent.py, employee.py, utils.py
│   │   ├── teamService/          # admin.py, agent.py, employee.py
│   │   ├── ticketService/        # admin.py, agent.py, employee.py, utils.py
│   │   └── userServices/         # admin.py, agent.py, employee.py, auth.py
│   ├── alembic.ini
│   └── main.py
├── tests/
│   ├── conftest.py
│   ├── test_auth_service.py
│   ├── test_security.py
│   └── test_user_routes.py
├── pytest.ini
└── README.md
```

---

## Setup and Installation

### Prerequisites

- Python 3.11+
- PostgreSQL (two databases: one for development, one for testing)
- Redis

### Install dependencies

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

> **Note:** A `requirements.txt` is not included in this repository. You can generate one from the imports across the codebase. Key packages: `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `psycopg2-binary`, `redis`, `pyjwt`, `passlib[bcrypt]`, `pydantic-settings`, `pydantic[email]`, `slowapi`, `pytest`, `httpx`.

---

## Environment Variables

Create a file at `app/.env`:

```env
# Primary database
DATABASE_URL=postgresql://user:password@localhost:5432/helpdesk_db

# Test database (used by pytest)
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/helpdesk_test_db

# Connection pool
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# App
DEBUG=true

# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Redis
REDIS_URL=redis://localhost:6379
```

---

## Running the App

```bash
# Run the development server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

---

## Database Migrations

```bash
# Apply all migrations to bring the schema up to date
cd app
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "describe_your_change"
```

Migration history:
1. `5f7370578a15` - Initial schema (users, teams, tickets, comments)
2. `15107cde5f31` - Add `is_active` to tickets
3. `1e20803a61b8` - Add `resolved_at` to tickets
4. `7fb6b4390738` - Make `is_active` non-nullable on users and teams (backfill existing rows)

---

## API Usage

### Authentication

```
POST /login
```

Accepts `application/x-www-form-urlencoded` (OAuth2 password flow). The `username` field accepts either a username or email address.

Returns:
```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```

Include the token in subsequent requests:
```
Authorization: Bearer <token>
```

### Route Prefixes by Role

| Domain | Admin | Agent | Employee |
|---|---|---|---|
| Users | `/users/admin/` | `/users/agent/` | `/users/employee/` |
| Teams | `/teams/admin/` | `/teams/agent/` | `/teams/employee/` |
| Tickets | `/tickets/admin/` | `/tickets/agent/` | `/tickets/employee/` |
| Comments | `/comments/admin/` | `/comments/agent/` | `/comments/employee/` |

User creation is at `POST /create` (admin only).

### Role Capabilities Summary

**Admin**
- Full CRUD on users, teams, tickets, and comments
- Can assign tickets to any user/team
- Can update ticket status freely
- Can update any user's password without knowing the current one

**Agent**
- View, create, and update tickets they created, are assigned to, or that belong to their team
- Can only assign tickets to members of their own team
- Status transitions follow a strict state machine: `open → in_progress → resolved → closed`
- Can edit/delete only their own comments
- Can view their own team and teammates

**Employee**
- Can create tickets (no assignee or team on creation)
- Can edit title/description only while the ticket is `open`
- Can only close their own open tickets (`open → closed`); no other status changes
- Cannot change priority, reassign, or transfer tickets
- Can comment on tickets they created or are assigned to; can edit but not delete their comments
- Can only view their own profile

---

## Testing

Tests use a separate PostgreSQL database and roll back each test in a transaction to keep them isolated.

```bash
pytest
```

To run with verbose output:
```bash
pytest -v
```

### Test Setup

`tests/conftest.py` creates the full schema against `TEST_DATABASE_URL` once per session and tears it down afterward. Each test gets a fresh database session wrapped in a rolled-back transaction. FastAPI's dependency injection is overridden to inject the test session and a fake authenticated user.

```python
# Override user in a specific test
app.dependency_overrides[get_current_user] = lambda: make_fake_user(UserRole.employee)
```

### Current Test Coverage

- `test_security.py` - password hashing and verification
- `test_auth_service.py` - user creation, duplicate detection, invalid username format
- `test_user_routes.py` - HTTP-level route tests for user creation and role enforcement

---

## Implementation Details

### Role enforcement pattern

Each service method checks `current_user.role.value` as its first operation and raises `PermissionDeniedException` immediately if the role doesn't match. This means role checks live in the service layer, not just on the route, so business logic is testable without going through HTTP.

### Redis caching

Responses are cached with structured keys like `tickets:all:10:0` or `comments:ticket:5:10:0`. On any mutation, affected keys are invalidated using `delete_by_prefix()`, which performs a Redis `SCAN` + `DELETE`. Cache failures are swallowed silently, so the app degrades gracefully without Redis.

### Ticket assignment validation

When assigning a ticket to a user and a team simultaneously, the system validates that the user belongs to that team. If only a user is provided (no team), the ticket's `team_id` is auto-populated from the user's team. Sentinel values are used to signal explicit removal: `assigned_to = -1` to unassign a user, `team_id = 0` to remove a team assignment (admin only for the latter).

### Soft deletes

Users, teams, and tickets are never hard-deleted. Setting `is_active = False` removes them from all queries. Deleting a team also clears related ticket and user caches to prevent stale data.

### `resolved_at` tracking

When a ticket's status is set to `resolved`, the `resolved_at` timestamp is automatically recorded in UTC. This happens in both the admin and agent ticket services.

---

## Future Improvements

- **Email integration**: the current `send_welcome_email` is a print stub; replace with a real SMTP client (e.g., `fastapi-mail`)
- **Refresh tokens**: current JWTs are single-use with no refresh mechanism
- **Pagination metadata**: responses return arrays only; a wrapper with `total`, `page`, and `pages` would be more useful for frontend consumers
- **Search and filtering**: tickets and users can only be fetched by ID or listing; adding status/priority/date filters would be practical
- **Audit logging**: no history is kept of who changed what on a ticket
- **OpenAPI documentation**: route descriptions, examples, and response models could be filled in for better auto-generated docs
- **Docker / docker-compose**: no containerization setup is included
