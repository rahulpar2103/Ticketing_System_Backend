"""
Integration tests for Comment services (admin, agent, employee).
"""
import pytest
from app.services.commentService.admin import admin_comment_service
from app.services.commentService.agent import agent_comment_service
from app.services.commentService.employee import employee_comment_service
from app.schemas.commentSchema import CommentCreate, CommentUpdate
from app.models.userModel import UserRole
from app.models.ticketModel import TicketStatus, Priority
from app.core.exceptions import PermissionDeniedException, NotFoundException
from tests.conftest import make_fake_user, make_db_user, make_db_team, make_db_ticket, make_db_comment


class TestAdminCommentCreate:
    def test_admin_creates_comment(self, db):
        admin = make_db_user(db, role=UserRole.admin, username="adm", email="adm@t.com")
        ticket = make_db_ticket(db, created_by=admin.id)
        db.commit()
        fake = make_fake_user(UserRole.admin, user_id=admin.id)
        result = admin_comment_service.create_comment(
            ticket.id, CommentCreate(comment="Looks good"), db, fake)
        assert result.comment == "Looks good"
        assert result.ticket_id == ticket.id

    def test_admin_comment_on_nonexistent_ticket(self, db):
        fake = make_fake_user(UserRole.admin)
        with pytest.raises(NotFoundException):
            admin_comment_service.create_comment(
                9999, CommentCreate(comment="X"), db, fake)

    def test_non_admin_rejected(self, db):
        fake = make_fake_user(UserRole.employee)
        with pytest.raises(PermissionDeniedException):
            admin_comment_service.create_comment(
                1, CommentCreate(comment="X"), db, fake)


class TestAdminCommentRead:
    def test_get_ticket_comments(self, db):
        admin = make_db_user(db, role=UserRole.admin, username="adm", email="adm@t.com")
        ticket = make_db_ticket(db, created_by=admin.id)
        make_db_comment(db, ticket_id=ticket.id, user_id=admin.id, comment="C1")
        make_db_comment(db, ticket_id=ticket.id, user_id=admin.id, comment="C2")
        db.commit()
        fake = make_fake_user(UserRole.admin, user_id=admin.id)
        result = admin_comment_service.get_ticket_comments(ticket.id, db, fake, 10, 0)
        assert len(result["items"]) == 2

    def test_get_single_comment(self, db):
        admin = make_db_user(db, role=UserRole.admin, username="adm", email="adm@t.com")
        ticket = make_db_ticket(db, created_by=admin.id)
        comment = make_db_comment(db, ticket_id=ticket.id, user_id=admin.id, comment="Hello")
        db.commit()
        fake = make_fake_user(UserRole.admin, user_id=admin.id)
        result = admin_comment_service.get_comment(comment.id, db, fake)
        assert result.comment == "Hello"


class TestAdminCommentUpdate:
    def test_admin_updates_comment(self, db):
        admin = make_db_user(db, role=UserRole.admin, username="adm", email="adm@t.com")
        ticket = make_db_ticket(db, created_by=admin.id)
        comment = make_db_comment(db, ticket_id=ticket.id, user_id=admin.id)
        db.commit()
        fake = make_fake_user(UserRole.admin, user_id=admin.id)
        result = admin_comment_service.update_comment(
            comment.id, CommentUpdate(comment="Edited"), db, fake)
        assert result.comment == "Edited"
        assert result.is_edited is True


class TestAdminCommentDelete:
    def test_admin_deletes_comment(self, db):
        admin = make_db_user(db, role=UserRole.admin, username="adm", email="adm@t.com")
        ticket = make_db_ticket(db, created_by=admin.id)
        comment = make_db_comment(db, ticket_id=ticket.id, user_id=admin.id)
        db.commit()
        fake = make_fake_user(UserRole.admin, user_id=admin.id)
        result = admin_comment_service.delete_comment(comment.id, db, fake)
        assert "deleted" in result["message"]

    def test_delete_nonexistent(self, db):
        fake = make_fake_user(UserRole.admin)
        with pytest.raises(NotFoundException):
            admin_comment_service.delete_comment(9999, db, fake)


class TestAgentCommentCreate:
    def test_agent_comments_on_own_ticket(self, db):
        team = make_db_team(db)
        agent = make_db_user(db, role=UserRole.agent, username="ag", email="ag@t.com", team_id=team.id)
        ticket = make_db_ticket(db, created_by=agent.id, team_id=team.id)
        db.commit()
        fake = make_fake_user(UserRole.agent, user_id=agent.id, team_id=team.id)
        result = agent_comment_service.create_comment(
            ticket.id, CommentCreate(comment="On it"), db, fake)
        assert result.comment == "On it"

    def test_agent_cannot_comment_on_inaccessible_ticket(self, db):
        t1 = make_db_team(db, name="T1")
        t2 = make_db_team(db, name="T2")
        agent = make_db_user(db, role=UserRole.agent, username="ag", email="ag@t.com", team_id=t1.id)
        other = make_db_user(db, role=UserRole.admin, username="adm", email="adm@t.com")
        ticket = make_db_ticket(db, created_by=other.id, team_id=t2.id)
        db.commit()
        fake = make_fake_user(UserRole.agent, user_id=agent.id, team_id=t1.id)
        with pytest.raises(PermissionDeniedException):
            agent_comment_service.create_comment(
                ticket.id, CommentCreate(comment="X"), db, fake)


class TestAgentCommentUpdate:
    def test_agent_can_edit_own_comment(self, db):
        team = make_db_team(db)
        agent = make_db_user(db, role=UserRole.agent, username="ag", email="ag@t.com", team_id=team.id)
        ticket = make_db_ticket(db, created_by=agent.id, team_id=team.id)
        comment = make_db_comment(db, ticket_id=ticket.id, user_id=agent.id)
        db.commit()
        fake = make_fake_user(UserRole.agent, user_id=agent.id, team_id=team.id)
        result = agent_comment_service.update_comment(
            comment.id, CommentUpdate(comment="Fixed"), db, fake)
        assert result.comment == "Fixed"

    def test_agent_cannot_edit_others_comment(self, db):
        team = make_db_team(db)
        agent = make_db_user(db, role=UserRole.agent, username="ag", email="ag@t.com", team_id=team.id)
        other = make_db_user(db, role=UserRole.agent, username="ag2", email="ag2@t.com", team_id=team.id)
        ticket = make_db_ticket(db, created_by=agent.id, team_id=team.id)
        comment = make_db_comment(db, ticket_id=ticket.id, user_id=other.id)
        db.commit()
        fake = make_fake_user(UserRole.agent, user_id=agent.id, team_id=team.id)
        with pytest.raises(PermissionDeniedException):
            agent_comment_service.update_comment(
                comment.id, CommentUpdate(comment="X"), db, fake)


class TestEmployeeCommentCreate:
    def test_employee_comments_on_own_ticket(self, db):
        emp = make_db_user(db, role=UserRole.employee, username="emp", email="emp@t.com")
        ticket = make_db_ticket(db, created_by=emp.id)
        db.commit()
        fake = make_fake_user(UserRole.employee, user_id=emp.id)
        result = employee_comment_service.create_comment(
            ticket.id, CommentCreate(comment="Thanks"), db, fake)
        assert result.comment == "Thanks"

    def test_employee_cannot_comment_on_others_ticket(self, db):
        emp = make_db_user(db, role=UserRole.employee, username="emp", email="emp@t.com")
        other = make_db_user(db, role=UserRole.admin, username="adm", email="adm@t.com")
        ticket = make_db_ticket(db, created_by=other.id)
        db.commit()
        fake = make_fake_user(UserRole.employee, user_id=emp.id)
        with pytest.raises(PermissionDeniedException):
            employee_comment_service.create_comment(
                ticket.id, CommentCreate(comment="X"), db, fake)
