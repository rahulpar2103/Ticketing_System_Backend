"""
Integration tests for Ticket services (admin, agent, employee).
"""
import pytest
from app.services.ticketService.admin import ticket_service_admin
from app.services.ticketService.agent import ticket_service_agent
from app.services.ticketService.employee import ticket_service_employee
from app.schemas.ticketSchema import TicketCreate, TicketUpdate
from app.models.ticketModel import TicketStatus, Priority
from app.models.userModel import UserRole
from app.core.exceptions import PermissionDeniedException, NotFoundException, ValidationException
from tests.conftest import make_fake_user, make_db_user, make_db_team, make_db_ticket


class TestAdminCreateTicket:
    def test_admin_creates_ticket(self, db):
        admin = make_db_user(db, role=UserRole.admin, username="admin1", email="adm@t.com")
        db.commit()
        fake = make_fake_user(UserRole.admin, user_id=admin.id)
        data = TicketCreate(title="Bug", description="Broken", priority=Priority.high)
        result = ticket_service_admin.create_ticket(data, db, fake)
        assert result.title == "Bug"

    def test_non_admin_rejected(self, db):
        fake = make_fake_user(UserRole.employee, user_id=1)
        data = TicketCreate(title="Bug", description="Broken", priority=Priority.low)
        with pytest.raises(PermissionDeniedException):
            ticket_service_admin.create_ticket(data, db, fake)

    def test_nonexistent_assignee(self, db):
        admin = make_db_user(db, role=UserRole.admin, username="admin1", email="adm@t.com")
        db.commit()
        fake = make_fake_user(UserRole.admin, user_id=admin.id)
        data = TicketCreate(title="T", description="D", priority=Priority.low, assigned_to=9999)
        with pytest.raises(NotFoundException):
            ticket_service_admin.create_ticket(data, db, fake)


class TestAdminGetTickets:
    def test_get_all(self, db):
        admin = make_db_user(db, role=UserRole.admin, username="admin1", email="adm@t.com")
        make_db_ticket(db, created_by=admin.id)
        make_db_ticket(db, title="Second", created_by=admin.id)
        db.commit()
        fake = make_fake_user(UserRole.admin, user_id=admin.id)
        result = ticket_service_admin.get_all_tickets(db, fake, 10, 0)
        assert len(result["items"]) >= 2

    def test_get_single(self, db):
        admin = make_db_user(db, role=UserRole.admin, username="admin1", email="adm@t.com")
        ticket = make_db_ticket(db, created_by=admin.id, title="Specific")
        db.commit()
        fake = make_fake_user(UserRole.admin, user_id=admin.id)
        result = ticket_service_admin.get_ticket(ticket.id, db, fake)
        assert result.title == "Specific"

    def test_get_nonexistent(self, db):
        fake = make_fake_user(UserRole.admin)
        with pytest.raises(NotFoundException):
            ticket_service_admin.get_ticket(9999, db, fake)


class TestAdminUpdateTicket:
    def test_update_title(self, db):
        admin = make_db_user(db, role=UserRole.admin, username="admin1", email="adm@t.com")
        ticket = make_db_ticket(db, created_by=admin.id)
        db.commit()
        fake = make_fake_user(UserRole.admin, user_id=admin.id)
        result = ticket_service_admin.update_ticket(ticket.id, TicketUpdate(title="New"), db, fake)
        assert result.title == "New"

    def test_resolve_sets_timestamp(self, db):
        admin = make_db_user(db, role=UserRole.admin, username="admin1", email="adm@t.com")
        ticket = make_db_ticket(db, created_by=admin.id)
        db.commit()
        fake = make_fake_user(UserRole.admin, user_id=admin.id)
        result = ticket_service_admin.update_ticket(
            ticket.id, TicketUpdate(status=TicketStatus.resolved), db, fake)
        assert result.resolved_at is not None


class TestEmployeeCreateTicket:
    def test_creates_ticket(self, db):
        emp = make_db_user(db, role=UserRole.employee, username="emp1", email="emp@t.com")
        db.commit()
        fake = make_fake_user(UserRole.employee, user_id=emp.id)
        data = TicketCreate(title="Help", description="Need help", priority=Priority.low)
        result = ticket_service_employee.create_ticket(data, db, fake)
        assert result.title == "Help"

    def test_cannot_set_assignee(self, db):
        emp = make_db_user(db, role=UserRole.employee, username="emp1", email="emp@t.com")
        db.commit()
        fake = make_fake_user(UserRole.employee, user_id=emp.id)
        data = TicketCreate(title="H", description="D", priority=Priority.low, assigned_to=1)
        with pytest.raises(PermissionDeniedException):
            ticket_service_employee.create_ticket(data, db, fake)

    def test_cannot_set_team(self, db):
        emp = make_db_user(db, role=UserRole.employee, username="emp1", email="emp@t.com")
        db.commit()
        fake = make_fake_user(UserRole.employee, user_id=emp.id)
        data = TicketCreate(title="H", description="D", priority=Priority.low, team_id=1)
        with pytest.raises(PermissionDeniedException):
            ticket_service_employee.create_ticket(data, db, fake)


class TestEmployeeUpdateTicket:
    def test_update_title_on_open(self, db):
        emp = make_db_user(db, role=UserRole.employee, username="emp1", email="emp@t.com")
        ticket = make_db_ticket(db, created_by=emp.id, status=TicketStatus.open)
        db.commit()
        fake = make_fake_user(UserRole.employee, user_id=emp.id)
        result = ticket_service_employee.update_ticket(ticket.id, TicketUpdate(title="Updated"), db, fake)
        assert result.title == "Updated"

    def test_cannot_update_title_on_non_open(self, db):
        emp = make_db_user(db, role=UserRole.employee, username="emp1", email="emp@t.com")
        ticket = make_db_ticket(db, created_by=emp.id, status=TicketStatus.in_progress)
        db.commit()
        fake = make_fake_user(UserRole.employee, user_id=emp.id)
        with pytest.raises(PermissionDeniedException):
            ticket_service_employee.update_ticket(ticket.id, TicketUpdate(title="X"), db, fake)

    def test_can_close_open_ticket(self, db):
        emp = make_db_user(db, role=UserRole.employee, username="emp1", email="emp@t.com")
        ticket = make_db_ticket(db, created_by=emp.id, status=TicketStatus.open)
        db.commit()
        fake = make_fake_user(UserRole.employee, user_id=emp.id)
        result = ticket_service_employee.update_ticket(
            ticket.id, TicketUpdate(status=TicketStatus.closed), db, fake)
        assert result.status == TicketStatus.closed

    def test_cannot_change_priority(self, db):
        emp = make_db_user(db, role=UserRole.employee, username="emp1", email="emp@t.com")
        ticket = make_db_ticket(db, created_by=emp.id)
        db.commit()
        fake = make_fake_user(UserRole.employee, user_id=emp.id)
        with pytest.raises(PermissionDeniedException):
            ticket_service_employee.update_ticket(
                ticket.id, TicketUpdate(priority=Priority.urgent), db, fake)

    def test_cannot_edit_others_ticket(self, db):
        emp = make_db_user(db, role=UserRole.employee, username="emp1", email="emp@t.com")
        other = make_db_user(db, role=UserRole.employee, username="emp2", email="emp2@t.com")
        ticket = make_db_ticket(db, created_by=other.id)
        db.commit()
        fake = make_fake_user(UserRole.employee, user_id=emp.id)
        with pytest.raises(PermissionDeniedException):
            ticket_service_employee.update_ticket(ticket.id, TicketUpdate(title="X"), db, fake)


class TestAgentCreateTicket:
    def test_creates_ticket(self, db):
        team = make_db_team(db)
        agent = make_db_user(db, role=UserRole.agent, username="ag1", email="ag@t.com", team_id=team.id)
        db.commit()
        fake = make_fake_user(UserRole.agent, user_id=agent.id, team_id=team.id)
        data = TicketCreate(title="Issue", description="Details", priority=Priority.medium)
        result = ticket_service_agent.create_ticket(data, db, fake)
        assert result.title == "Issue"

    def test_cannot_assign_to_other_team(self, db):
        t1 = make_db_team(db, name="T1")
        t2 = make_db_team(db, name="T2")
        agent = make_db_user(db, role=UserRole.agent, username="ag1", email="ag@t.com", team_id=t1.id)
        other = make_db_user(db, role=UserRole.agent, username="ag2", email="ag2@t.com", team_id=t2.id)
        db.commit()
        fake = make_fake_user(UserRole.agent, user_id=agent.id, team_id=t1.id)
        data = TicketCreate(title="X", description="Y", priority=Priority.low, assigned_to=other.id)
        with pytest.raises(PermissionDeniedException):
            ticket_service_agent.create_ticket(data, db, fake)


class TestAgentUpdateTicket:
    def test_valid_transition(self, db):
        team = make_db_team(db)
        agent = make_db_user(db, role=UserRole.agent, username="ag1", email="ag@t.com", team_id=team.id)
        ticket = make_db_ticket(db, created_by=agent.id, team_id=team.id, status=TicketStatus.open)
        db.commit()
        fake = make_fake_user(UserRole.agent, user_id=agent.id, team_id=team.id)
        result = ticket_service_agent.update_ticket(
            ticket.id, TicketUpdate(status=TicketStatus.in_progress), db, fake)
        assert result.status == TicketStatus.in_progress

    def test_invalid_transition(self, db):
        team = make_db_team(db)
        agent = make_db_user(db, role=UserRole.agent, username="ag1", email="ag@t.com", team_id=team.id)
        ticket = make_db_ticket(db, created_by=agent.id, team_id=team.id, status=TicketStatus.open)
        db.commit()
        fake = make_fake_user(UserRole.agent, user_id=agent.id, team_id=team.id)
        with pytest.raises(ValidationException):
            ticket_service_agent.update_ticket(
                ticket.id, TicketUpdate(status=TicketStatus.closed), db, fake)

    def test_cannot_edit_inaccessible_ticket(self, db):
        t1 = make_db_team(db, name="T1")
        t2 = make_db_team(db, name="T2")
        agent = make_db_user(db, role=UserRole.agent, username="ag1", email="ag@t.com", team_id=t1.id)
        other = make_db_user(db, role=UserRole.agent, username="ag2", email="ag2@t.com", team_id=t2.id)
        ticket = make_db_ticket(db, created_by=other.id, team_id=t2.id)
        db.commit()
        fake = make_fake_user(UserRole.agent, user_id=agent.id, team_id=t1.id)
        with pytest.raises(PermissionDeniedException):
            ticket_service_agent.update_ticket(ticket.id, TicketUpdate(title="X"), db, fake)
