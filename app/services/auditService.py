from sqlalchemy.orm import Session
from app.models.auditModel import AuditLog
from app.models.userModel import User
import json

def log_audit_event(db: Session, ticket_id: int, current_user: User, action: str, changes: dict = None):
    """
    Records an action performed on a ticket in the audit_logs table.
    """
    changes_str = json.dumps(changes) if changes else None
    
    log = AuditLog(
        ticket_id=ticket_id,
        user_id=current_user.id if current_user else None,
        action=action,
        changes=changes_str
    )
    db.add(log)
    # The session should be committed by the caller (or flushed if within a larger transaction)

def get_ticket_audit_logs(ticket_id: int, db: Session, current_user: User, limit: int, offset: int):
    """
    Retrieve audit history for a ticket. We do a basic access check based on role.
    """
    from app.services.ticketService.utils import _load_ticket
    from app.core.exceptions import PermissionDeniedException, NotFoundException
    from app.schemas.pagination import PaginatedResponse
    from app.models.userModel import UserRole
    
    ticket = _load_ticket(db, ticket_id)
    if not ticket:
        raise NotFoundException(f"Ticket {ticket_id} not found")
        
    # Check access: Admin gets all, Agent gets team's/own, Employee gets own
    if current_user.role == UserRole.employee:
        if ticket.created_by != current_user.id and ticket.assigned_to != current_user.id:
            raise PermissionDeniedException("You don't have access to this ticket's history")
    elif current_user.role == UserRole.agent:
        if ticket.team_id != current_user.team_id and ticket.created_by != current_user.id and ticket.assigned_to != current_user.id:
            raise PermissionDeniedException("You don't have access to this ticket's history")
            
    query = db.query(AuditLog).filter(AuditLog.ticket_id == ticket_id).order_by(AuditLog.created_at.desc())
    total = query.count()
    logs = query.offset(offset).limit(limit).all()
    
    formatted_logs = []
    for log in logs:
        formatted_logs.append({
            "id": log.id,
            "ticket_id": log.ticket_id,
            "user_id": log.user_id,
            "username": log.user.username if log.user else None,
            "action": log.action,
            "changes": json.loads(log.changes) if log.changes else None,
            "created_at": log.created_at
        })
        
    return PaginatedResponse(
        items=formatted_logs,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit < total)
    )
