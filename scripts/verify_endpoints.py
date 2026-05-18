"""
Full live endpoint verification script.
Hits every endpoint against a running server and reports pass/fail.
"""
import httpx
import sys

BASE = "http://127.0.0.1:8000"
results = []


def test(method, path, expected, **kwargs):
    r = getattr(httpx, method)(f"{BASE}{path}", **kwargs, timeout=10)
    status = "OK" if r.status_code == expected else f"FAIL({r.status_code})"
    results.append((status, method.upper(), path, r.status_code, expected))
    tag = "[OK]" if "OK" in status else f"[FAIL expected={expected} got={r.status_code}]"
    print(f"  {tag:30s} {method.upper():6s} {path}")
    if "FAIL" in status:
        try:
            print(f"       -> {r.json()}")
        except Exception:
            print(f"       -> {r.text[:200]}")
    return r


print("=" * 65)
print("  LIVE ENDPOINT VERIFICATION")
print("=" * 65)

# ── 1. SYSTEM ──────────────────────────────────────────────────────
print("\n--- System ---")
test("get", "/", 200)
r = test("get", "/health", 200)
health = r.json()
print(f"       Health: {health}")

# ── 2. AUTH ─────────────────────────────────────────────────────────
print("\n--- Auth ---")
r = test("post", "/auth/login", 200, data={"username": "rahul", "password": "Password@123"})
admin_token = r.json()["access_token"]
admin_h = {"Authorization": f"Bearer {admin_token}"}

r = test("post", "/auth/login", 200, data={"username": "ankit", "password": "Password@123"})
agent_token = r.json()["access_token"]
agent_h = {"Authorization": f"Bearer {agent_token}"}

r = test("post", "/auth/login", 200, data={"username": "deepak", "password": "Password@123"})
emp_token = r.json()["access_token"]
emp_h = {"Authorization": f"Bearer {emp_token}"}

test("post", "/auth/login", 401, data={"username": "rahul", "password": "wrong"})
test("post", "/auth/login", 200, data={"username": "rahul@company.com", "password": "Password@123"})

# ── 3. USERS ────────────────────────────────────────────────────────
print("\n--- Users (Admin) ---")
r = test("get", "/users", 200, headers=admin_h)
all_users = r.json()
deepak_id = next(u["id"] for u in all_users if u["username"] == "deepak")
ankit_id = next(u["id"] for u in all_users if u["username"] == "ankit")

test("get", "/users?limit=3&offset=0", 200, headers=admin_h)
test("get", f"/users/{deepak_id}", 200, headers=admin_h)
test("get", "/users/99999", 404, headers=admin_h)

print("\n--- Users (Agent) ---")
test("get", "/users", 403, headers=agent_h)
test("get", f"/users/{ankit_id}", 200, headers=agent_h)  # own profile

print("\n--- Users (Employee) ---")
test("get", "/users", 403, headers=emp_h)
test("get", f"/users/{deepak_id}", 200, headers=emp_h)    # own profile
test("get", f"/users/1", 403, headers=emp_h)               # other user blocked

# ── 4. TEAMS ────────────────────────────────────────────────────────
print("\n--- Teams (Admin) ---")
test("get", "/teams", 200, headers=admin_h)
test("get", "/teams/1", 200, headers=admin_h)
test("get", "/teams/1/members", 200, headers=admin_h)
test("get", "/teams/99999", 404, headers=admin_h)

print("\n--- Teams (Agent) ---")
# Find agent's team
agent_profile = httpx.get(f"{BASE}/users/{ankit_id}", headers=agent_h, timeout=10).json()
agent_team = agent_profile["team_id"]
test("get", f"/teams/{agent_team}", 200, headers=agent_h)    # own team
test("get", f"/teams/{agent_team}/members", 200, headers=agent_h)  # own team members
test("get", "/teams", 403, headers=agent_h)                  # list all blocked

print("\n--- Teams (Employee) ---")
test("get", "/teams", 403, headers=emp_h)

# ── 5. TICKETS ──────────────────────────────────────────────────────
print("\n--- Tickets (Admin) ---")
test("get", "/tickets", 200, headers=admin_h)
test("get", "/tickets/created-by-me", 200, headers=admin_h)
test("get", "/tickets/assigned-to-me", 200, headers=admin_h)
test("get", "/tickets/1", 200, headers=admin_h)
test("get", "/tickets/99999", 404, headers=admin_h)
test("get", "/tickets/team/1", 200, headers=admin_h)
test("get", f"/tickets/user/{ankit_id}/assigned", 200, headers=admin_h)

print("\n--- Tickets (Agent) ---")
test("get", "/tickets", 200, headers=agent_h)
test("get", "/tickets/created-by-me", 200, headers=agent_h)
test("get", "/tickets/assigned-to-me", 200, headers=agent_h)
test("get", f"/tickets/team/{agent_team}", 200, headers=agent_h)

print("\n--- Tickets (Employee) ---")
test("get", "/tickets", 200, headers=emp_h)
test("get", "/tickets/created-by-me", 200, headers=emp_h)
test("get", "/tickets/assigned-to-me", 200, headers=emp_h)

# Create ticket as employee
print("\n--- Ticket CRUD (Employee) ---")
r = test("post", "/tickets", 201, headers=emp_h, json={
    "title": "Printer not working", "description": "3rd floor printer is jammed", "priority": "low"
})
emp_ticket_id = r.json()["id"]

# Update title while open
test("patch", f"/tickets/{emp_ticket_id}", 200, headers=emp_h, json={"title": "Printer jammed on 3rd floor"})

# Employee can't change priority
test("patch", f"/tickets/{emp_ticket_id}", 403, headers=emp_h, json={"priority": "high"})

# Employee can't reassign
test("patch", f"/tickets/{emp_ticket_id}", 403, headers=emp_h, json={"assigned_to": 1})

# Close ticket (open -> closed)
test("patch", f"/tickets/{emp_ticket_id}", 200, headers=emp_h, json={"status": "closed"})

# ── Employee confirm fix (resolved -> closed) ──
print("\n--- Ticket Confirm Fix (resolved -> closed) ---")
r = test("post", "/tickets", 201, headers=emp_h, json={
    "title": "VPN disconnects randomly", "description": "Drops every 15 min", "priority": "high"
})
fix_ticket_id = r.json()["id"]
test("patch", f"/tickets/{fix_ticket_id}", 200, headers=admin_h, json={"status": "in_progress"})
test("patch", f"/tickets/{fix_ticket_id}", 200, headers=admin_h, json={"status": "resolved"})
test("patch", f"/tickets/{fix_ticket_id}", 200, headers=emp_h, json={"status": "closed"})

# Employee can't do invalid transitions
r2 = test("post", "/tickets", 201, headers=emp_h, json={
    "title": "Test bad transition", "description": "Test", "priority": "low"
})
bad_id = r2.json()["id"]
test("patch", f"/tickets/{bad_id}", 400, headers=emp_h, json={"status": "in_progress"})  # open -> in_progress blocked

# ── Agent ticket workflow ──
print("\n--- Agent Ticket Workflow ---")
r = test("post", "/tickets", 201, headers=agent_h, json={
    "title": "Server restart needed", "description": "Memory leak on prod-1", "priority": "urgent", "assigned_to": ankit_id
})
agent_ticket_id = r.json()["id"]
test("patch", f"/tickets/{agent_ticket_id}", 200, headers=agent_h, json={"status": "in_progress"})
test("patch", f"/tickets/{agent_ticket_id}", 200, headers=agent_h, json={"status": "resolved"})
test("patch", f"/tickets/{agent_ticket_id}", 200, headers=agent_h, json={"status": "closed"})

# ── 6. COMMENTS ─────────────────────────────────────────────────────
print("\n--- Comments ---")
# Use the emp_ticket_id (employee created it, it's closed but they should still be able to comment)
r = test("post", f"/tickets/{emp_ticket_id}/comments", 201, headers=emp_h, json={"comment": "Still having this issue"})
emp_comment_id = r.json()["id"]

test("get", f"/tickets/{emp_ticket_id}/comments", 200, headers=emp_h)
test("get", f"/comments/{emp_comment_id}", 200, headers=emp_h)

# Edit own comment
test("patch", f"/comments/{emp_comment_id}", 200, headers=emp_h, json={"comment": "Updated: issue persists"})

# Delete own comment (new feature!)
test("delete", f"/comments/{emp_comment_id}", 200, headers=emp_h)

# Admin comments on any ticket
r = test("post", "/tickets/1/comments", 201, headers=admin_h, json={"comment": "Admin checking in"})
admin_comment_id = r.json()["id"]
test("delete", f"/comments/{admin_comment_id}", 200, headers=admin_h)

# Agent comment
r = test("post", f"/tickets/{agent_ticket_id}/comments", 201, headers=agent_h, json={"comment": "Restarted the server"})
agent_comment_id = r.json()["id"]
test("delete", f"/comments/{agent_comment_id}", 200, headers=agent_h)

# ── 7. ADMIN USER MANAGEMENT ───────────────────────────────────────
print("\n--- Admin User Management ---")
r = test("post", "/auth/register", 201, headers=admin_h, json={
    "name": "Temp User", "username": "tempuser", "email": "temp@company.com",
    "password": "StrongPass@123", "role": "employee"
})
new_user_id = r.json()["id"]

test("patch", f"/users/{new_user_id}", 200, headers=admin_h, json={"name": "Renamed User"})
test("patch", f"/users/{new_user_id}/reset-password", 200, headers=admin_h, json={"new_password": "ResetPass@789"})

# Verify new password works
test("post", "/auth/login", 200, data={"username": "tempuser", "password": "ResetPass@789"})

test("delete", f"/users/{new_user_id}", 200, headers=admin_h)

# ── 8. PASSWORD CHANGE ──────────────────────────────────────────────
print("\n--- Password Change ---")
test("patch", f"/users/{ankit_id}/password", 200, headers=agent_h, json={
    "current_password": "Password@123", "new_password": "AgentNewPass@123"
})
# Verify new password
test("post", "/auth/login", 200, data={"username": "ankit", "password": "AgentNewPass@123"})

# ── SUMMARY ─────────────────────────────────────────────────────────
print("\n" + "=" * 65)
passed = sum(1 for s, *_ in results if s == "OK")
failed = sum(1 for s, *_ in results if s != "OK")
print(f"  TOTAL: {len(results)} | PASSED: {passed} | FAILED: {failed}")
if failed:
    print("\n  FAILURES:")
    for s, m, p, got, exp in results:
        if s != "OK":
            print(f"    {m:6s} {p}  expected={exp} got={got}")
print("=" * 65)
sys.exit(1 if failed else 0)
