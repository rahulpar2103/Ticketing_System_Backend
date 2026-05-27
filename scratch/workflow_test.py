import requests

BASE_URL = "http://localhost:8000"
PASSWORD = "Password@123"

def run_integration_tests():
    print("="*60)
    print("⚡ TICKETING SYSTEM CORE INTEGRATION WORKFLOW TEST SUITE ⚡")
    print("="*60)

    # ────────────────────────────────────────────────────────────────────────
    # 👑 1. ADMIN ROLE TEST (`rahul`)
    # ────────────────────────────────────────────────────────────────────────
    print("\n👑 [1/3] Testing Admin Role Flow (User: rahul)...")
    
    # Login
    session_admin = requests.Session()
    login_resp = session_admin.post(f"{BASE_URL}/auth/login", data={"username": "rahul", "password": PASSWORD})
    assert login_resp.status_code == 200, "Admin login failed"
    token_admin = login_resp.json()["access_token"]
    session_admin.headers.update({"Authorization": f"Bearer {token_admin}"})
    print("[+] Admin successfully authenticated")

    # Fetch stats
    stats_resp = session_admin.get(f"{BASE_URL}/tickets/stats")
    assert stats_resp.status_code == 200, "Failed to retrieve stats"
    print(f"[+] Admin fetched system stats: {stats_resp.json()}")

    # Create a new team
    new_team_payload = {
        "name": f"Integration Testing Squad",
        "description": "Formed to automatically run regression suites."
    }
    team_resp = session_admin.post(f"{BASE_URL}/teams", json=new_team_payload)
    assert team_resp.status_code == 201, "Admin failed to create team"
    created_team = team_resp.json()
    team_id = created_team["id"]
    print(f"[+] Admin successfully created team: {created_team['name']} (id={team_id})")

    # Create a new user (employee)
    new_user_payload = {
        "name": "QA Agent Auto",
        "username": "qa_auto_agent",
        "email": "qa_auto@company.com",
        "password": "Password@123",
        "role": "employee",
        "team_id": team_id
    }
    user_resp = session_admin.post(f"{BASE_URL}/auth/register", json=new_user_payload)
    assert user_resp.status_code == 201, "Admin failed to register new user"
    created_user = user_resp.json()
    print(f"[+] Admin registered a new {created_user['role']}: {created_user['username']} (id={created_user['id']})")

    # Fetch all tickets
    tickets_resp = session_admin.get(f"{BASE_URL}/tickets")
    assert tickets_resp.status_code == 200, "Admin failed to list tickets"
    all_tickets = tickets_resp.json()["items"]
    print(f"[+] Admin retrieved ticket list. Total in page: {len(all_tickets)}")
    first_ticket_id = all_tickets[0]["id"]

    # Post a comment as Admin on first ticket
    comment_payload = {"comment": "Admin verification test comment: Everything is healthy."}
    comment_resp = session_admin.post(f"{BASE_URL}/tickets/{first_ticket_id}/comments", json=comment_payload)
    assert comment_resp.status_code == 201, f"Admin failed to post comment on ticket {first_ticket_id}"
    created_comment = comment_resp.json()
    print(f"[+] Admin posted comment successfully: '{created_comment['comment']}'")

    # Update ticket status to in_progress
    update_payload = {"status": "in_progress"}
    patch_resp = session_admin.patch(f"{BASE_URL}/tickets/{first_ticket_id}", json=update_payload)
    assert patch_resp.status_code == 200, "Admin failed to update ticket status"
    print(f"[+] Admin successfully changed ticket {first_ticket_id} status to {patch_resp.json()['status']}")


    # ────────────────────────────────────────────────────────────────────────
    # 🛡️ 2. AGENT ROLE TEST (`rohan` - Frontend Team)
    # ────────────────────────────────────────────────────────────────────────
    print("\n🛡️ [2/3] Testing Agent Role Flow (User: rohan)...")
    
    session_agent = requests.Session()
    login_resp = session_agent.post(f"{BASE_URL}/auth/login", data={"username": "rohan", "password": PASSWORD})
    assert login_resp.status_code == 200, "Agent login failed"
    token_agent = login_resp.json()["access_token"]
    session_agent.headers.update({"Authorization": f"Bearer {token_agent}"})
    print("[+] Agent successfully authenticated")

    # Check that Agent CANNOT access users list (should return 403)
    users_resp = session_agent.get(f"{BASE_URL}/users")
    assert users_resp.status_code == 403, "Security vulnerability: Agent was allowed to list users!"
    print("[+] Security Guard check passed: Agent is blocked from /users directory (403 Forbidden)")

    # Check that Agent CANNOT access teams creation (should return 403)
    teams_resp = session_agent.post(f"{BASE_URL}/teams", json={"name": "Hacker Team", "description": "xxx"})
    assert teams_resp.status_code == 403, "Security vulnerability: Agent was allowed to create team!"
    print("[+] Security Guard check passed: Agent is blocked from creating teams (403 Forbidden)")

    # Fetch Agent's tickets
    agent_tickets_resp = session_agent.get(f"{BASE_URL}/tickets")
    assert agent_tickets_resp.status_code == 200
    agent_tickets = agent_tickets_resp.json()["items"]
    print(f"[+] Agent retrieved their assigned/team tickets. Count: {len(agent_tickets)}")

    # Add a comment on a ticket as Agent
    agent_comment_resp = session_agent.post(f"{BASE_URL}/tickets/{first_ticket_id}/comments", json={"comment": "Agent rohan is taking a look at this issue now."})
    assert agent_comment_resp.status_code == 201, "Agent failed to comment"
    print(f"[+] Agent commented successfully: '{agent_comment_resp.json()['comment']}'")


    # ────────────────────────────────────────────────────────────────────────
    # 👤 3. EMPLOYEE ROLE TEST (`deepak`)
    # ────────────────────────────────────────────────────────────────────────
    print("\n👤 [3/3] Testing Employee Role Flow (User: deepak)...")

    session_emp = requests.Session()
    login_resp = session_emp.post(f"{BASE_URL}/auth/login", data={"username": "deepak", "password": PASSWORD})
    assert login_resp.status_code == 200, "Employee login failed"
    token_emp = login_resp.json()["access_token"]
    session_emp.headers.update({"Authorization": f"Bearer {token_emp}"})
    print("[+] Employee successfully authenticated")

    # Employee creates a new ticket
    new_ticket_payload = {
        "title": "Automated Employee Bug Report",
        "description": "My local workstation Docker containers are not connecting to redis host.",
        "priority": "high"
    }
    create_ticket_resp = session_emp.post(f"{BASE_URL}/tickets", json=new_ticket_payload)
    assert create_ticket_resp.status_code == 201, "Employee failed to create ticket"
    created_ticket = create_ticket_resp.json()
    emp_ticket_id = created_ticket["id"]
    print(f"[+] Employee created support ticket #{emp_ticket_id}: '{created_ticket['title']}'")

    # Verify Employee CANNOT change ticket priority (should return 403/PermissionDenied)
    bad_update = {"priority": "urgent"}
    bad_resp = session_emp.patch(f"{BASE_URL}/tickets/{emp_ticket_id}", json=bad_update)
    assert bad_resp.status_code in (403, 400), f"Security vulnerability: Employee modified priority! {bad_resp.status_code}"
    print("[+] Security Guard check passed: Employee blocked from changing priority (Forbidden)")

    # Verify Employee CANNOT reassign ticket to another user
    bad_assign = {"assigned_to": 1}
    bad_resp = session_emp.patch(f"{BASE_URL}/tickets/{emp_ticket_id}", json=bad_assign)
    assert bad_resp.status_code in (403, 400)
    print("[+] Security Guard check passed: Employee blocked from reassigning ticket")

    # Employee posts a comment on their ticket
    emp_comment_resp = session_emp.post(f"{BASE_URL}/tickets/{emp_ticket_id}/comments", json={"comment": "Adding extra log lines: redis.exceptions.ConnectionError."})
    assert emp_comment_resp.status_code == 201, "Employee failed to comment on own ticket"
    print(f"[+] Employee added comment successfully to ticket #{emp_ticket_id}")

    # Employee closes their own ticket (allowed transition: open -> closed)
    close_payload = {"status": "closed"}
    close_resp = session_emp.patch(f"{BASE_URL}/tickets/{emp_ticket_id}", json=close_payload)
    assert close_resp.status_code == 200, "Employee failed to close their own ticket"
    print(f"[+] Employee successfully closed ticket #{emp_ticket_id} (Status: {close_resp.json()['status']})")

    print("\n" + "="*60)
    print("🏆 ALL INTEGRATION TESTS PASSED TRIUMPHANTLY! 🏆")
    print("="*60)

if __name__ == "__main__":
    run_integration_tests()
