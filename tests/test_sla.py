import pytest
from datetime import datetime, timezone, timedelta
from app.services.ticketService.admin import ticket_service_admin
from app.services.ticketService.agent import ticket_service_agent
from app.services.ticketService.employee import ticket_service_employee
from app.schemas.ticketSchema import TicketCreate, TicketUpdate
from app.models.ticketModel import TicketStatus, Priority, Ticket
from app.models.userModel import UserRole
from app.core.sla import calculate_due_at, update_expired_slas, SLA_TIERS
from tests.conftest import make_fake_user, make_db_user, make_db_team, make_db_ticket

class TestSLAIntegration:
    def test_sla_calculated_on_creation(self, db):
        admin = make_db_user(db, role=UserRole.admin, username="admin_sla1", email="adm_sla1@t.com")
        db.flush()
        fake = make_fake_user(UserRole.admin, user_id=admin.id)
        
        # Test Urgent Priority (4 Hours)
        data = TicketCreate(title="Urgent Ticket", description="Do it fast", priority=Priority.urgent)
        result = ticket_service_admin.create_ticket(data, db, fake)
        assert result.due_at is not None
        # Check that due_at is roughly created_at + 4 hours
        time_diff = result.due_at - result.created_at
        assert abs(time_diff.total_seconds() - 4 * 3600) < 5
        assert result.sla_breached is False

        # Test Low Priority (48 Hours)
        data_low = TicketCreate(title="Low Ticket", description="Take your time", priority=Priority.low)
        result_low = ticket_service_admin.create_ticket(data_low, db, fake)
        assert result_low.due_at is not None
        time_diff_low = result_low.due_at - result_low.created_at
        assert abs(time_diff_low.total_seconds() - 48 * 3600) < 5
        assert result_low.sla_breached is False

    def test_sla_recalculated_on_priority_change(self, db):
        admin = make_db_user(db, role=UserRole.admin, username="admin_sla2", email="adm_sla2@t.com")
        db.flush()
        fake = make_fake_user(UserRole.admin, user_id=admin.id)
        
        # Initial creation as low priority (48 hours SLA)
        data = TicketCreate(title="Flexible Priority", description="Change me", priority=Priority.low)
        created = ticket_service_admin.create_ticket(data, db, fake)
        initial_due = created.due_at
        
        # Update priority to urgent (4 hours SLA)
        updated = ticket_service_admin.update_ticket(
            created.id, TicketUpdate(priority=Priority.urgent), db, fake
        )
        assert updated.due_at is not None
        assert updated.due_at < initial_due
        time_diff = updated.due_at - updated.created_at
        assert abs(time_diff.total_seconds() - 4 * 3600) < 5

    def test_sla_breach_marked_on_resolution(self, db):
        admin = make_db_user(db, role=UserRole.admin, username="admin_sla3", email="adm_sla3@t.com")
        db.flush()
        fake = make_fake_user(UserRole.admin, user_id=admin.id)
        
        # Create ticket
        data = TicketCreate(title="To Be Resolved", description="Test", priority=Priority.urgent)
        created = ticket_service_admin.create_ticket(data, db, fake)
        
        # Manually alter the ticket creation and due dates to be in the past
        ticket_record = db.query(Ticket).filter(Ticket.id == created.id).first()
        past_time = datetime.now(timezone.utc) - timedelta(hours=5)
        ticket_record.created_at = past_time
        ticket_record.due_at = past_time + timedelta(hours=4)  # Urgent SLA = 4h
        db.flush()
        
        # Resolve the ticket now (which is 1 hour after the due date)
        resolved = ticket_service_admin.update_ticket(
            created.id, TicketUpdate(status=TicketStatus.resolved), db, fake
        )
        assert resolved.resolved_at is not None
        assert resolved.sla_breached is True

    def test_lazy_sla_breach_detection(self, db):
        admin = make_db_user(db, role=UserRole.admin, username="admin_sla4", email="adm_sla4@t.com")
        db.flush()
        fake = make_fake_user(UserRole.admin, user_id=admin.id)
        
        # Create an urgent ticket (4h SLA)
        data = TicketCreate(title="Breached Open Ticket", description="Past deadline", priority=Priority.urgent)
        created = ticket_service_admin.create_ticket(data, db, fake)
        
        # Manually backdate the created_at and due_at to make it currently overdue
        ticket_record = db.query(Ticket).filter(Ticket.id == created.id).first()
        past_time = datetime.now(timezone.utc) - timedelta(hours=6)
        ticket_record.created_at = past_time
        ticket_record.due_at = past_time + timedelta(hours=4)
        ticket_record.sla_breached = False
        db.flush()
        
        # Trigger dynamic update using get_ticket
        fetched = ticket_service_admin.get_ticket(created.id, db, fake)
        assert fetched.sla_breached is True
        
        # Query DB directly to verify changes persisted
        persisted = db.query(Ticket).filter(Ticket.id == created.id).first()
        assert persisted.sla_breached is True

    def test_ticket_stats_includes_breach_count(self, db):
        admin = make_db_user(db, role=UserRole.admin, username="admin_sla5", email="adm_sla5@t.com")
        db.flush()
        fake = make_fake_user(UserRole.admin, user_id=admin.id)
        
        # Create a breached ticket
        data = TicketCreate(title="Stat Breach", description="Breached", priority=Priority.urgent)
        created = ticket_service_admin.create_ticket(data, db, fake)
        ticket_record = db.query(Ticket).filter(Ticket.id == created.id).first()
        past_time = datetime.now(timezone.utc) - timedelta(hours=6)
        ticket_record.created_at = past_time
        ticket_record.due_at = past_time + timedelta(hours=4)
        db.flush()
        
        # Fetch stats - this will run dynamic update and should include the breach count
        stats = ticket_service_admin.get_ticket_stats(db, fake)
        assert stats["sla_breached"] >= 1
