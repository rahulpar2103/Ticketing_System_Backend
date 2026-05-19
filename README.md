# Ticketing System — Internal Office Help Desk API

A backend REST API for managing internal support tickets in an organization. Built with **FastAPI**, it implements strict role-based access control across three user roles — **Admin**, **Agent**, and **Employee** — with Redis caching, JWT authentication, and per-role business logic enforced at the service layer.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [Access Control Matrix](#access-control-matrix)
- [Folder Structure](#folder-structure)
- [Setup and Installation](#setup-and-installation)
- [Environment Variables](#environment-variables)
- [Running the App](#running-the-app)
- [Database Migrations](#database-migrations)
- [Seeding Sample Data](#seeding-sample-data)
- [API Endpoints](#api-endpoints)
- [Testing](#testing)
- [Implementation Details](#implementation-details)
- [Future Improvements](#future-improvements)

---

## Overview

This system is designed for an **internal office environment** where:

- **Admins** have full control — they create user accounts, manage teams, and oversee all tickets and comments across the organization.
- **Agents** work within their assigned team — they can view, create, and manage tickets scoped to their team, assign tickets to teammates, and follow a strict status workflow.
- **Employees** have limited access — they raise tickets, track their own issues, and can comment on tickets they're involved in.

All account creation is admin-controlled. There is no self-registration.

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

## Features

- **JWT Authentication** — login with username or email; tokens verified on every protected route
- **Role-Based Access Control** — three roles with strictly scoped permissions enforced at the service layer
- **Ticket Lifecycle** — state machine for status transitions with role-specific rules
- **Search & Filtering** — tickets searchable by keyword (title/description), filterable by status, priority; users searchable by name/username/email, filterable by role, team, active status
- **Sorting** — all list endpoints support `sort_by` and `order` query params with field validation
- **Pagination Metadata** — all list endpoints return `{ items, total, limit, offset, has_more }` instead of bare arrays
- **CORS Middleware** — configurable allowed origins for frontend integration
- **Redis Caching** — detail responses cached with prefix-based invalidation on mutations
- **Rate Limiting** — per-endpoint limits via `slowapi` (e.g., 5/min on login, 30/min on reads)
- **Health Check** — `GET /health` checks API, database, and Redis connectivity
- **Soft Deletes** — users, teams, and tickets are deactivated via `is_active` flag; tickets deletable by all roles with role-specific rules
- **Background Tasks** — welcome emails sent asynchronously on user creation
- **Alembic Migrations** — schema changes are versioned and reproducible

---

## Access Control Matrix

### Users

| Action | Admin | Agent | Employee |
|---|:---:|:---:|:---:|
| Create user account | ✅ | ❌ | ❌ |
| List all users | ✅ | ❌ | ❌ |
| View any user by ID | ✅ | ❌ | ❌ |
| View own profile | ✅ | ✅ | ✅ |
| View teammate's profile | ✅ | ✅ (same team only) | ❌ |
| Update any user (name, email, role, team) | ✅ | ❌ | ❌ |
| Soft-delete a user | ✅ | ❌ | ❌ |
| Reactivate a soft-deleted user | ✅ | ❌ | ❌ |
| Reset any user's password (no current password needed) | ✅ | ❌ | ❌ |
| Change own password (requires current password) | ✅ via reset | ✅ | ✅ |

### Teams

| Action | Admin | Agent | Employee |
|---|:---:|:---:|:---:|
| Create team | ✅ | ❌ | ❌ |
| List all teams | ✅ | ❌ | ❌ |
| View any team by ID | ✅ | ❌ | ❌ |
| View own team | ✅ | ✅ | ✅ (if assigned) |
| Update team (name, description) | ✅ | ❌ | ❌ |
| Delete team (soft-delete + cascade) | ✅ | ❌ | ❌ |
| Reactivate a soft-deleted team | ✅ | ❌ | ❌ |
| View team stats (ticket counts, member count) | ✅ | ❌ | ❌ |
| View team members | ✅ (any team) | ✅ (own team) | ✅ (own team) |

### Tickets

| Action | Admin | Agent | Employee |
|---|:---:|:---:|:---:|
| Create ticket | ✅ (assign to anyone/any team) | ✅ (assign within own team) | ✅ (no assignee/team) |
| View all tickets | ✅ | ❌ | ❌ |
| View own tickets (created/assigned/team) | ✅ | ✅ | ✅ (created or assigned only) |
| View ticket by ID | ✅ (any) | ✅ (accessible¹) | ✅ (created or assigned) |
| View tickets by team | ✅ (any team) | ✅ (own team) | ❌ |
| View tickets assigned to a specific user | ✅ | ❌ | ❌ |
| Search/filter/sort tickets | ✅ (all tickets) | ✅ (accessible tickets) | ✅ (own tickets) |
| Edit title/description | ✅ | ✅ (own created only) | ✅ (own created, open status only) |
| Change priority | ✅ | ✅ (team tickets) | ❌ |
| Change status | ✅ (any transition) | ✅ (valid transitions²) | ✅ (open → closed, resolved → closed) |
| Assign/reassign user | ✅ (any user) | ✅ (own team members) | ❌ |
| Change team | ✅ | ✅ (transfers allowed³) | ❌ |
| Unassign user (`assigned_to = -1`) | ✅ | ✅ (team tickets) | ❌ |
| Remove team (`team_id = 0`) | ✅ | ❌ | ❌ |
| Delete ticket (soft-delete) | ✅ (any ticket) | ✅ (accessible tickets) | ✅ (own open tickets only) |
| Reactivate a soft-deleted ticket | ✅ | ❌ | ❌ |
| View ticket stats (by status/priority) | ✅ | ❌ | ❌ |

> ¹ **Accessible** for agents = ticket they created, are assigned to, or belongs to their team.  
> ² **Valid transitions** for agents: `open → in_progress → resolved → closed` (strict state machine).  
> ³ Agent can transfer a ticket to a different team, but the current assignee is cleared.

### Comments

| Action | Admin | Agent | Employee |
|---|:---:|:---:|:---:|
| Create comment on a ticket | ✅ (any ticket) | ✅ (accessible tickets) | ✅ (own tickets) |
| View comments on a ticket | ✅ (any ticket) | ✅ (accessible tickets) | ✅ (own tickets) |
| View single comment by ID | ✅ | ✅ (accessible tickets) | ✅ (own tickets) |
| Edit a comment | ✅ (any comment) | ✅ (own comments only) | ✅ (own comments only) |
| Delete a comment | ✅ (any comment) | ✅ (own comments only) | ✅ (own comments only) |

### Ticket Status Transitions by Role

```
Admin:    Can set any status freely (no restrictions)

Agent:    open ──→ in_progress ──→ resolved ──→ closed
          (strict sequential, no skipping)

Employee: open ──→ closed       (cancel / no longer needed)
          resolved ──→ closed   (confirm fix)
```

---

## Folder Structure

```
.
├── app/
│   ├── alembic/                  # Migration scripts
│   │   └── versions/             # One file per migration
│   ├── core/
│   │   ├── config.py             # Settings loaded from .env (pydantic-settings)
│   │   ├── email.py              # Email sending (stub/background task)
│   │   ├── exceptions.py         # Custom exception classes
│   │   ├── limiter.py            # slowapi Limiter instance
│   │   └── security.py           # Password hashing, JWT encode/decode
│   ├── db/
│   │   ├── database.py           # SQLAlchemy engine, session, Base
│   │   └── redis.py              # Redis client + safe helper functions
│   ├── dependencies/
│   │   ├── db.py                 # get_db() dependency
│   │   └── user.py               # get_current_user() + OAuth2 scheme
│   ├── models/
│   │   ├── commentModel.py       # Comment ORM model
│   │   ├── teamModel.py          # Team ORM model
│   │   ├── ticketModel.py        # Ticket ORM model + Status/Priority enums
│   │   └── userModel.py          # User ORM model + UserRole enum
│   ├── routers/
│   │   ├── auth.py               # POST /auth/login, POST /auth/register
│   │   ├── comments.py           # Comment CRUD routes
│   │   ├── mainRouter.py         # Aggregates all routers
│   │   ├── teams.py              # Team CRUD routes
│   │   ├── tickets.py            # Ticket CRUD routes
│   │   └── users.py              # User CRUD + password routes
│   ├── schemas/
│   │   ├── commentSchema.py      # CommentCreate, CommentUpdate, CommentResponse
│   │   ├── pagination.py         # PaginatedResponse[T] generic wrapper
│   │   ├── teamSchema.py         # TeamCreate, TeamUpdate, TeamResponse
│   │   ├── ticketSchema.py       # TicketCreate, TicketUpdate, TicketResponse
│   │   └── userSchema.py         # UserCreate, UserUpdate, UserResponse, etc.
│   ├── services/
│   │   ├── commentService/       # admin.py, agent.py, employee.py, utils.py
│   │   ├── teamService/          # admin.py, agent.py, employee.py
│   │   ├── ticketService/        # admin.py, agent.py, employee.py, utils.py
│   │   └── userServices/         # admin.py, agent.py, employee.py, auth.py
│   ├── .env                      # Environment variables (not committed)
│   ├── .env.example              # Template for .env
│   ├── alembic.ini               # Alembic configuration
│   └── main.py                   # FastAPI app, CORS, health check, exception handlers
├── scripts/
│   └── seed.py                   # Database seed script with sample data
├── tests/
│   ├── conftest.py               # Shared fixtures, DB setup, role-based TestClients
│   ├── test_auth_routes.py       # Auth endpoint tests
│   ├── test_auth_service.py      # Auth service unit tests
│   ├── test_comment_routes.py    # Comment endpoint tests
│   ├── test_comment_services.py  # Comment service unit tests
│   ├── test_schemas.py           # Pydantic schema validation tests
│   ├── test_security.py          # JWT and password hashing tests
│   ├── test_team_routes.py       # Team endpoint tests
│   ├── test_team_services.py     # Team service unit tests
│   ├── test_ticket_routes.py     # Ticket endpoint tests
│   ├── test_ticket_services.py   # Ticket service unit tests
│   ├── test_user_routes.py       # User endpoint tests
│   └── test_user_services.py     # User service unit tests
├── pytest.ini
├── requirements.txt
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
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# Install packages
pip install -r requirements.txt
```

---

## Environment Variables

Copy the template and fill in your values:

```bash
cp app/.env.example app/.env
```

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg2://user:pass@localhost:5432/ticketing_db` |
| `TEST_DATABASE_URL` | Test database connection string | `postgresql+psycopg2://user:pass@localhost:5432/ticketing_test` |
| `DB_POOL_SIZE` | SQLAlchemy connection pool size | `5` |
| `DB_MAX_OVERFLOW` | Max overflow connections | `10` |
| `DEBUG` | Enable SQL echo logging | `true` |
| `SECRET_KEY` | JWT signing key (min 32 chars) | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry | `300` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `CORS_ORIGINS` | Allowed origins (JSON array) | `["http://localhost:3000"]` |

---

## Running the App

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

| URL | Description |
|---|---|
| `http://localhost:8000/docs` | Interactive Swagger UI |
| `http://localhost:8000/redoc` | ReDoc documentation |
| `http://localhost:8000/health` | Health check (API + DB + Redis) |

---

## Database Migrations

```bash
# Apply all migrations
alembic -c app/alembic.ini upgrade head

# Create a new migration after model changes
alembic -c app/alembic.ini revision --autogenerate -m "describe_your_change"
```

### Migration History

| Revision | Description |
|---|---|
| `5f7370578a15` | Initial schema (users, teams, tickets, comments) |
| `15107cde5f31` | Add `is_active` to tickets |
| `1e20803a61b8` | Add `resolved_at` to tickets |
| `7fb6b4390738` | Make `is_active` non-nullable with backfill |
| `f16a2694d019` | Add unique constraint to `teams.name` |

---

## Seeding Sample Data

Populate the database with realistic office data (5 teams, 15 users, 13 tickets, 20 comments):

```bash
python scripts/seed.py
```

All seeded users share the password: `Password@123`

| Role | Users |
|---|---|
| Admin | `rahul`, `priya` |
| Agent | `ankit`, `sneha`, `rohan`, `kavita`, `arun`, `meera`, `vikram` |
| Employee | `deepak`, `pooja`, `suresh`, `nisha`, `amit`, `lakshmi` |

---

## API Endpoints

### Authentication

| Method | Endpoint | Description | Auth |
|---|---|---|:---:|
| `POST` | `/auth/login` | Login with username/email + password | No |
| `POST` | `/auth/logout` | Revoke current access token | All roles |
| `POST` | `/auth/register` | Create a new user account | Admin |

### Users

| Method | Endpoint | Description | Auth |
|---|---|---|:---:|
| `GET` | `/users/me` | Get current user's profile | All roles |
| `GET` | `/users` | List all users (paginated, searchable, filterable, sortable) | Admin |
| `GET` | `/users/{id}` | Get user by ID | Role-scoped |
| `PATCH` | `/users/{id}` | Update user profile | Admin |
| `DELETE` | `/users/{id}` | Soft-delete user | Admin |
| `PATCH` | `/users/{id}/reactivate` | Re-enable a soft-deleted user | Admin |
| `PATCH` | `/users/{id}/password` | Change own password | Agent, Employee |
| `PATCH` | `/users/{id}/reset-password` | Reset any user's password | Admin |

#### User Query Parameters

| Parameter | Type | Description |
|---|---|---|
| `search` | `string` | Search by name, username, or email (case-insensitive) |
| `role` | `string` | Filter by role (comma-separated, e.g. `admin,agent`) |
| `team_id` | `int` | Filter by team (use `0` for unassigned) |
| `is_active` | `bool` | Filter by active status |
| `sort_by` | `string` | Sort field: `created_at`, `updated_at`, `name`, `username`, `email`, `role` |
| `order` | `string` | `asc` or `desc` (default: `desc`) |

### Teams

| Method | Endpoint | Description | Auth |
|---|---|---|:---:|
| `POST` | `/teams` | Create a team | Admin |
| `GET` | `/teams` | List all teams (paginated, sortable) | Admin |
| `GET` | `/teams/{id}` | Get team by ID | Role-scoped |
| `PUT` | `/teams/{id}` | Update team | Admin |
| `DELETE` | `/teams/{id}` | Soft-delete team (cascades to users/tickets) | Admin |
| `PATCH` | `/teams/{id}/reactivate` | Re-enable a soft-deleted team | Admin |
| `GET` | `/teams/{id}/stats` | Get team ticket stats (by status, member count) | Admin |
| `GET` | `/teams/{id}/members` | List team members (paginated, sortable) | Role-scoped |

### Tickets

| Method | Endpoint | Description | Auth |
|---|---|---|:---:|
| `POST` | `/tickets` | Create a ticket | All roles |
| `GET` | `/tickets` | List tickets (paginated, searchable, filterable, sortable) | All roles |
| `GET` | `/tickets/created-by-me` | Tickets created by current user | All roles |
| `GET` | `/tickets/assigned-to-me` | Tickets assigned to current user | All roles |
| `GET` | `/tickets/team/{team_id}` | Tickets for a team | Admin, Agent |
| `GET` | `/tickets/user/{user_id}/assigned` | Tickets assigned to a specific user | Admin |
| `GET` | `/tickets/stats` | Ticket stats by status/priority (optional `?team_id=`) | Admin |
| `GET` | `/tickets/{id}` | Get ticket by ID | Role-scoped |
| `PATCH` | `/tickets/{id}` | Update ticket | Role-scoped |
| `DELETE` | `/tickets/{id}` | Soft-delete ticket | Role-scoped |
| `PATCH` | `/tickets/{id}/reactivate` | Re-enable a soft-deleted ticket | Admin |

#### Ticket Query Parameters

| Parameter | Type | Description |
|---|---|---|
| `search` | `string` | Search in title and description (case-insensitive) |
| `status` | `string` | Filter by status (comma-separated, e.g. `open,in_progress`) |
| `priority` | `string` | Filter by priority (comma-separated, e.g. `high,urgent`) |
| `sort_by` | `string` | Sort field: `created_at`, `updated_at`, `priority`, `status`, `title` |
| `order` | `string` | `asc` or `desc` (default: `desc`) |

### Comments

| Method | Endpoint | Description | Auth |
|---|---|---|:---:|
| `POST` | `/tickets/{id}/comments` | Add comment to a ticket | Role-scoped |
| `GET` | `/tickets/{id}/comments` | List comments (paginated, sortable) | Role-scoped |
| `GET` | `/comments/{id}` | Get single comment | Role-scoped |
| `PATCH` | `/comments/{id}` | Edit a comment | Role-scoped |
| `DELETE` | `/comments/{id}` | Delete a comment | Role-scoped |

### Pagination Response Format

All list endpoints return a paginated response:

```json
{
  "items": [...],
  "total": 42,
  "limit": 10,
  "offset": 0,
  "has_more": true
}

### System

| Method | Endpoint | Description | Auth |
|---|---|---|:---:|
| `GET` | `/` | API info | No |
| `GET` | `/health` | Health check (API + DB + Redis) | No |

---

## Testing

Tests use a separate PostgreSQL database (`TEST_DATABASE_URL`) with per-test transaction rollback for isolation. Redis is automatically mocked.

```bash
# Run all 203 tests
pytest

# Verbose output
pytest -v

# Run a specific test file
pytest tests/test_ticket_services.py -v
```

### Test Architecture

- **`conftest.py`** — creates schema once per session, provides `db` fixture with transaction rollback, auto-mocks Redis, provides role-specific `TestClient` fixtures (`admin_client`, `agent_client`, `employee_client`)
- **Service tests** — test business logic directly against the DB
- **Route tests** — test HTTP endpoints via `TestClient`
- **Schema tests** — validate Pydantic field validators
- **Security tests** — JWT creation, verification, and expiry

### Test Coverage

| Module | Test File | Tests |
|---|---|---|
| Auth (service) | `test_auth_service.py` | User creation, login, duplicate detection |
| Auth (routes) | `test_auth_routes.py` | Login endpoint, register endpoint |
| Users (service) | `test_user_services.py` | CRUD for all 3 roles, password changes |
| Users (routes) | `test_user_routes.py` | HTTP-level role enforcement |
| Teams (service) | `test_team_services.py` | Create, read, update, delete, members |
| Teams (routes) | `test_team_routes.py` | HTTP-level role enforcement |
| Tickets (service) | `test_ticket_services.py` | CRUD, status transitions, assignment rules |
| Tickets (routes) | `test_ticket_routes.py` | HTTP-level role enforcement |
| Comments (service) | `test_comment_services.py` | CRUD, ownership checks |
| Comments (routes) | `test_comment_routes.py` | HTTP-level role enforcement |
| Schemas | `test_schemas.py` | Field validation, length limits, empty strings |
| Security | `test_security.py` | Password hashing, JWT tokens |

---

## Implementation Details

### Role Enforcement

Each service method checks `current_user.role` against `UserRole` enum values as its first operation and raises `PermissionDeniedException` if the role doesn't match. Role checks live in the service layer, not just on routes, so business logic is testable without going through HTTP. Routers dispatch to the correct role-specific service using a `_get_*_service()` lookup.

### Redis Caching

Responses are cached with structured keys like `tickets:all:10:0` or `comments:ticket:5:10:0`. On any mutation, affected keys are invalidated using `delete_by_prefix()`, which performs a Redis `SCAN` + `DELETE`. All Redis operations use `safe_*` wrappers that swallow exceptions — the app degrades gracefully without Redis.

### Ticket Assignment Validation

When assigning a ticket to a user and a team simultaneously, the system validates that the user belongs to that team. If only a user is provided (no team), the ticket's `team_id` is auto-populated from the user's team. Sentinel values signal explicit removal: `assigned_to = -1` to unassign a user, `team_id = 0` to remove team assignment (admin only).

### Soft Deletes

Users, teams, and tickets are never hard-deleted. Setting `is_active = False` removes them from all queries. Deleting a team cascades: all users in the team have their `team_id` cleared, and all active tickets for that team have their `team_id` and `assigned_to` cleared to prevent stale references. Soft-deleted resources can be re-enabled via `PATCH /{resource}/{id}/reactivate` (admin only).

### `resolved_at` Tracking

When a ticket's status is set to `resolved`, the `resolved_at` timestamp is automatically recorded in UTC. This happens in both the admin and agent ticket services.

---

## Future Improvements

- **Email integration** — replace the print stub `send_welcome_email` with a real SMTP client
- **Containerization** — Dockerfile and docker-compose for PostgreSQL, Redis, and the API
- **Refresh tokens** — current JWTs have no refresh mechanism
- **Audit logging** — track who changed what on a ticket
- **WebSocket notifications** — real-time updates when tickets are assigned or status changes
- **Bulk operations** — update/delete multiple tickets at once
