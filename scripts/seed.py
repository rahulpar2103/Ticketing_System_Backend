"""
Seed script — populates the ticketing system with realistic sample data.

Run:  .\\ticket\\Scripts\\python.exe seed.py
"""

from app.db.database import session_local
from app.models.userModel import User, UserRole
from app.models.teamModel import Team
from app.models.ticketModel import Ticket, TicketStatus, Priority
from app.models.commentModel import Comment
from app.core.security import hash_password
from datetime import datetime, timezone, timedelta

db = session_local()

try:
    # ── Teams ───────────────────────────────────────────────────────────────
    teams_data = [
        {"name": "Platform Engineering",  "description": "Infrastructure, CI/CD, and cloud services"},
        {"name": "Frontend",              "description": "Web and mobile UI development"},
        {"name": "Backend",               "description": "API services, databases, and integrations"},
        {"name": "QA & Testing",          "description": "Quality assurance, test automation, and regression"},
        {"name": "DevOps",                "description": "Deployment pipelines, monitoring, and SRE"},
    ]
    teams = []
    for t in teams_data:
        team = Team(**t)
        db.add(team)
        db.flush()
        teams.append(team)
        print(f"  + Team: {team.name} (id={team.id})")

    # ── Users ───────────────────────────────────────────────────────────────
    DEFAULT_PASSWORD = hash_password("Password@123")

    users_data = [
        # Admins (no team)
        {"name": "Rahul Sharma",    "username": "rahul",      "email": "rahul@company.com",     "role": UserRole.admin,    "team_id": None},
        {"name": "Priya Verma",     "username": "priya",      "email": "priya@company.com",     "role": UserRole.admin,    "team_id": None},

        # Agents — Platform Engineering
        {"name": "Ankit Mehta",     "username": "ankit",      "email": "ankit@company.com",     "role": UserRole.agent,    "team_id": teams[0].id},
        {"name": "Sneha Patil",     "username": "sneha",      "email": "sneha@company.com",     "role": UserRole.agent,    "team_id": teams[0].id},

        # Agents — Frontend
        {"name": "Rohan Gupta",     "username": "rohan",      "email": "rohan@company.com",     "role": UserRole.agent,    "team_id": teams[1].id},

        # Agents — Backend
        {"name": "Kavita Joshi",    "username": "kavita",     "email": "kavita@company.com",    "role": UserRole.agent,    "team_id": teams[2].id},
        {"name": "Arun Kumar",      "username": "arun",       "email": "arun@company.com",      "role": UserRole.agent,    "team_id": teams[2].id},

        # Agents — QA
        {"name": "Meera Nair",      "username": "meera",      "email": "meera@company.com",     "role": UserRole.agent,    "team_id": teams[3].id},

        # Agents — DevOps
        {"name": "Vikram Singh",    "username": "vikram",     "email": "vikram@company.com",    "role": UserRole.agent,    "team_id": teams[4].id},

        # Employees (some with teams, some without)
        {"name": "Deepak Rao",      "username": "deepak",     "email": "deepak@company.com",    "role": UserRole.employee, "team_id": teams[0].id},
        {"name": "Pooja Desai",     "username": "pooja",      "email": "pooja@company.com",     "role": UserRole.employee, "team_id": teams[1].id},
        {"name": "Suresh Iyer",     "username": "suresh",     "email": "suresh@company.com",    "role": UserRole.employee, "team_id": teams[2].id},
        {"name": "Nisha Reddy",     "username": "nisha",      "email": "nisha@company.com",     "role": UserRole.employee, "team_id": teams[3].id},
        {"name": "Amit Tiwari",     "username": "amit",       "email": "amit@company.com",      "role": UserRole.employee, "team_id": None},
        {"name": "Lakshmi Pillai",  "username": "lakshmi",    "email": "lakshmi@company.com",   "role": UserRole.employee, "team_id": None},
    ]

    users = []
    for u in users_data:
        user = User(hashed_password=DEFAULT_PASSWORD, **u)
        db.add(user)
        db.flush()
        users.append(user)
        print(f"  + User: {user.username} ({user.role.value}, team_id={user.team_id})")

    # Handy references
    rahul, priya = users[0], users[1]
    ankit, sneha = users[2], users[3]
    rohan = users[4]
    kavita, arun = users[5], users[6]
    meera = users[7]
    vikram = users[8]
    deepak, pooja, suresh, nisha, amit, lakshmi = users[9], users[10], users[11], users[12], users[13], users[14]

    now = datetime.now(timezone.utc)

    # ── Tickets ─────────────────────────────────────────────────────────────
    tickets_data = [
        # Open tickets
        {
            "title": "Login page crashes on mobile Safari",
            "description": "Users on iOS 17 report a white screen after entering credentials. Console shows a TypeError in the auth module. Reproducible on iPhone 15 Pro.",
            "priority": Priority.high,
            "status": TicketStatus.open,
            "created_by": pooja.id,
            "assigned_to": rohan.id,
            "team_id": teams[1].id,
        },
        {
            "title": "Add dark mode toggle to settings page",
            "description": "Feature request: users should be able to switch between light and dark themes from their profile settings. Design mockups are attached in Figma.",
            "priority": Priority.medium,
            "status": TicketStatus.open,
            "created_by": amit.id,
            "assigned_to": None,
            "team_id": None,
        },
        {
            "title": "Database connection pool exhaustion under load",
            "description": "During peak hours (2-4 PM IST), the API starts returning 503 errors. Logs show 'QueuePool limit overflow'. Current pool_size=5, max_overflow=10.",
            "priority": Priority.urgent,
            "status": TicketStatus.open,
            "created_by": rahul.id,
            "assigned_to": kavita.id,
            "team_id": teams[2].id,
        },
        {
            "title": "Export CSV button not working on reports page",
            "description": "Clicking 'Export as CSV' on the analytics dashboard does nothing. No network request is made. Tested on Chrome 125 and Firefox 128.",
            "priority": Priority.medium,
            "status": TicketStatus.open,
            "created_by": lakshmi.id,
            "assigned_to": None,
            "team_id": None,
        },

        # In-progress tickets
        {
            "title": "Migrate CI/CD pipeline from Jenkins to GitHub Actions",
            "description": "Phase 1: Move the build and unit test stages. Phase 2: Add deployment to staging. Current Jenkins config is in /infra/jenkins/. Target completion: end of sprint.",
            "priority": Priority.high,
            "status": TicketStatus.in_progress,
            "created_by": rahul.id,
            "assigned_to": ankit.id,
            "team_id": teams[0].id,
        },
        {
            "title": "Implement rate limiting on public API endpoints",
            "description": "Apply rate limits (100 req/min for authenticated, 20 req/min for anonymous) to all /api/v1/ routes. Use Redis-backed sliding window. Document in API changelog.",
            "priority": Priority.high,
            "status": TicketStatus.in_progress,
            "created_by": priya.id,
            "assigned_to": arun.id,
            "team_id": teams[2].id,
        },
        {
            "title": "Flaky test: test_user_concurrent_sessions",
            "description": "This test fails ~20% of the time in CI. Appears to be a race condition in the session cleanup fixture. Passes locally every time.",
            "priority": Priority.medium,
            "status": TicketStatus.in_progress,
            "created_by": meera.id,
            "assigned_to": meera.id,
            "team_id": teams[3].id,
        },
        {
            "title": "Set up Grafana dashboards for API latency",
            "description": "Create Grafana dashboards pulling from Prometheus metrics. Need panels for: p50/p95/p99 latency, error rate, request throughput, and DB query time.",
            "priority": Priority.medium,
            "status": TicketStatus.in_progress,
            "created_by": vikram.id,
            "assigned_to": vikram.id,
            "team_id": teams[4].id,
        },

        # Resolved tickets
        {
            "title": "Fix N+1 query in ticket listing endpoint",
            "description": "GET /tickets was issuing a separate query for each assigned_user and team. Added joinedload() to the base query. Verified with SQL echo — now 1 query instead of 47.",
            "priority": Priority.high,
            "status": TicketStatus.resolved,
            "created_by": kavita.id,
            "assigned_to": kavita.id,
            "team_id": teams[2].id,
            "resolved_at": now - timedelta(days=2),
        },
        {
            "title": "Update Python to 3.12 across all services",
            "description": "Upgraded base Docker images and CI runners. All tests pass. Performance improved ~5% on JSON serialization benchmarks. No breaking changes.",
            "priority": Priority.low,
            "status": TicketStatus.resolved,
            "created_by": sneha.id,
            "assigned_to": ankit.id,
            "team_id": teams[0].id,
            "resolved_at": now - timedelta(days=5),
        },

        # Closed tickets
        {
            "title": "Onboarding docs are outdated",
            "description": "The README still references the old Vagrant setup. Updated with Docker Compose instructions, .env.example, and quickstart guide.",
            "priority": Priority.low,
            "status": TicketStatus.closed,
            "created_by": deepak.id,
            "assigned_to": sneha.id,
            "team_id": teams[0].id,
        },
        {
            "title": "Password reset email not sending",
            "description": "SMTP credentials had expired. Rotated credentials and added health check for the email service. Verified reset flow end-to-end.",
            "priority": Priority.urgent,
            "status": TicketStatus.closed,
            "created_by": nisha.id,
            "assigned_to": arun.id,
            "team_id": teams[2].id,
        },
        {
            "title": "Accessibility audit — WCAG 2.1 AA compliance",
            "description": "Ran axe-core on all pages. Fixed 23 issues: missing alt text, low contrast buttons, missing ARIA labels on modals. All pages now pass AA.",
            "priority": Priority.medium,
            "status": TicketStatus.closed,
            "created_by": rohan.id,
            "assigned_to": pooja.id,
            "team_id": teams[1].id,
        },
    ]

    tickets = []
    for t in tickets_data:
        resolved_at = t.pop("resolved_at", None)
        ticket = Ticket(**t)
        if resolved_at:
            ticket.resolved_at = resolved_at
        db.add(ticket)
        db.flush()
        tickets.append(ticket)
        print(f"  + Ticket #{ticket.id}: {ticket.title[:50]}... [{ticket.status.value}]")

    # ── Comments ────────────────────────────────────────────────────────────
    comments_data = [
        # Comments on "Login page crashes on mobile Safari"
        {"comment": "I can reproduce this on my iPhone 14 as well. Happens only on Safari, Chrome on iOS works fine.", "ticket_id": tickets[0].id, "user_id": pooja.id},
        {"comment": "Looks like it's the new WebKit strict mode. I'll patch the auth module to handle the stricter CSP headers.", "ticket_id": tickets[0].id, "user_id": rohan.id},
        {"comment": "Fix is ready on branch `fix/safari-auth`. Can someone on QA verify?", "ticket_id": tickets[0].id, "user_id": rohan.id},

        # Comments on "DB connection pool exhaustion"
        {"comment": "I've increased pool_size to 10 and max_overflow to 20 as a temporary fix. Monitoring now.", "ticket_id": tickets[2].id, "user_id": kavita.id},
        {"comment": "The real fix should be to add connection pooling via PgBouncer. Let's plan that for next sprint.", "ticket_id": tickets[2].id, "user_id": rahul.id},

        # Comments on "Migrate CI/CD to GitHub Actions"
        {"comment": "Phase 1 is done. Build + test pipeline runs in ~4 minutes vs 12 minutes on Jenkins. PR is up for review.", "ticket_id": tickets[4].id, "user_id": ankit.id},
        {"comment": "Reviewed the workflow file. Looks good, just add a matrix strategy for Python 3.11 and 3.12.", "ticket_id": tickets[4].id, "user_id": sneha.id},
        {"comment": "Done. Also added caching for pip dependencies — cuts another 90 seconds off.", "ticket_id": tickets[4].id, "user_id": ankit.id},

        # Comments on "Rate limiting"
        {"comment": "Using a sliding window with Redis sorted sets. Much more accurate than the fixed-window approach.", "ticket_id": tickets[5].id, "user_id": arun.id},
        {"comment": "Make sure we return proper 429 responses with Retry-After headers.", "ticket_id": tickets[5].id, "user_id": priya.id},

        # Comments on "Flaky test"
        {"comment": "Found the issue — the fixture was sharing a session across threads. Switching to function-scoped sessions.", "ticket_id": tickets[6].id, "user_id": meera.id},

        # Comments on "Grafana dashboards"
        {"comment": "Draft dashboards are live at grafana.internal/d/api-latency. Feedback welcome.", "ticket_id": tickets[7].id, "user_id": vikram.id},
        {"comment": "Can you add an alert rule for p99 > 500ms? We want to catch regressions early.", "ticket_id": tickets[7].id, "user_id": rahul.id},

        # Comments on "Fix N+1 query" (resolved)
        {"comment": "Before: 47 queries, 320ms. After: 1 query with JOINs, 18ms. Massive improvement.", "ticket_id": tickets[8].id, "user_id": kavita.id},
        {"comment": "Great work! Marking as resolved. Let's keep an eye on it in production.", "ticket_id": tickets[8].id, "user_id": priya.id},

        # Comments on "Password reset email not sending" (closed)
        {"comment": "Root cause: the SMTP credentials expired on May 1st and nobody noticed because there was no monitoring.", "ticket_id": tickets[11].id, "user_id": arun.id},
        {"comment": "Added a health check endpoint that pings the SMTP server every 5 minutes. Alert goes to #ops-alerts.", "ticket_id": tickets[11].id, "user_id": arun.id},
        {"comment": "Verified the full reset flow — email received within 10 seconds. Closing this.", "ticket_id": tickets[11].id, "user_id": nisha.id},

        # Comments on "Accessibility audit" (closed)
        {"comment": "Full report is in Confluence: /wiki/accessibility-audit-q2. 23 issues found, all fixed.", "ticket_id": tickets[12].id, "user_id": pooja.id},
        {"comment": "Excellent work. This was long overdue. Closing.", "ticket_id": tickets[12].id, "user_id": rohan.id},
    ]

    for c in comments_data:
        comment = Comment(**c)
        db.add(comment)
        db.flush()
        print(f"  + Comment on ticket #{c['ticket_id']} by user #{c['user_id']}")

    db.commit()
    print(f"\n{'='*60}")
    print(f"  Seed complete!")
    print(f"  Teams:    {len(teams)}")
    print(f"  Users:    {len(users)}  (password for all: Password@123)")
    print(f"  Tickets:  {len(tickets)}")
    print(f"  Comments: {len(comments_data)}")
    print(f"{'='*60}")

except Exception as e:
    db.rollback()
    print(f"\nX Seed failed: {e}")
    raise
finally:
    db.close()
