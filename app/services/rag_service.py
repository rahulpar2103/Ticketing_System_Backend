import logging
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from app.core.config import settings
from app.models.userModel import User, UserRole
from app.models.ticketModel import Ticket
from app.models.commentModel import Comment
from app.models.vectorDocumentModel import VectorDocument

logger = logging.getLogger(__name__)

# Configure Gemini
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY is not set. Chatbot responses will fall back to unconfigured mode.")

def get_embedding(text: str, task_type: str = "retrieval_document") -> Optional[List[float]]:
    """Generate vector embedding using Google's text-embedding-004 model."""
    if not settings.GEMINI_API_KEY:
        return None
    try:
        response = genai.embed_content(
            model=settings.EMBEDDING_MODEL,
            content=text,
            task_type=task_type
        )
        return response.get("embedding")
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        return None

def format_ticket_text(ticket: Ticket) -> str:
    """Format ticket fields into a single context document for embedding."""
    created_by = ticket.created_by_user.username if ticket.created_by_user else "Unknown"
    assigned_to = ticket.assigned_user.username if ticket.assigned_user else "Unassigned"
    team_name = ticket.team.name if ticket.team else "None"
    
    return (
        f"Ticket ID: {ticket.id}\n"
        f"Title: {ticket.title}\n"
        f"Description: {ticket.description}\n"
        f"Status: {ticket.status.value if hasattr(ticket.status, 'value') else ticket.status}\n"
        f"Priority: {ticket.priority.value if hasattr(ticket.priority, 'value') else ticket.priority}\n"
        f"Created By: {created_by}\n"
        f"Assigned To: {assigned_to}\n"
        f"Team: {team_name}\n"
        f"Created At: {ticket.created_at}\n"
    )

def format_comment_text(comment: Comment) -> str:
    """Format comment fields into a single context document for embedding."""
    author = comment.user.username if comment.user else "Unknown"
    ticket_title = comment.ticket.title if comment.ticket else "Unknown Ticket"
    
    return (
        f"Comment on Ticket ID {comment.ticket_id} (Title: '{ticket_title}')\n"
        f"Author: {author}\n"
        f"Comment Content: {comment.comment}\n"
        f"Created At: {comment.created_at}\n"
    )


def index_ticket(db: Session, ticket: Ticket) -> bool:
    """Embed and index a ticket into the vector_documents table."""
    text = format_ticket_text(ticket)
    embedding = get_embedding(text, task_type="retrieval_document")
    if not embedding:
        return False
    
    # Check if vector document already exists
    existing = db.execute(
        select(VectorDocument).where(
            VectorDocument.document_type == "ticket",
            VectorDocument.reference_id == ticket.id
        )
    ).scalar_one_or_none()
    
    metadata = {
        "ticket_id": ticket.id,
        "created_by": ticket.created_by,
        "team_id": ticket.team_id,
        "assigned_to": ticket.assigned_to,
        "status": ticket.status.value if hasattr(ticket.status, 'value') else ticket.status
    }
    
    if existing:
        existing.content = text
        existing.embedding = embedding
        existing.metadata_json = metadata
    else:
        doc = VectorDocument(
            document_type="ticket",
            reference_id=ticket.id,
            content=text,
            embedding=embedding,
            metadata_json=metadata
        )
        db.add(doc)
    
    db.commit()
    return True

def index_comment(db: Session, comment: Comment) -> bool:
    """Embed and index a ticket comment into the vector_documents table."""
    text = format_comment_text(comment)
    embedding = get_embedding(text, task_type="retrieval_document")
    if not embedding:
        return False
    
    # Check if vector document already exists
    existing = db.execute(
        select(VectorDocument).where(
            VectorDocument.document_type == "comment",
            VectorDocument.reference_id == comment.id
        )
    ).scalar_one_or_none()
    
    ticket = comment.ticket
    metadata = {
        "comment_id": comment.id,
        "ticket_id": comment.ticket_id,
        "created_by": ticket.created_by if ticket else None,
        "team_id": ticket.team_id if ticket else None,
        "assigned_to": ticket.assigned_to if ticket else None,
        "comment_author_id": comment.user_id
    }
    
    if existing:
        existing.content = text
        existing.embedding = embedding
        existing.metadata_json = metadata
    else:
        doc = VectorDocument(
            document_type="comment",
            reference_id=comment.id,
            content=text,
            embedding=embedding,
            metadata_json=metadata
        )
        db.add(doc)
    
    db.commit()
    return True

def delete_vector_document(db: Session, doc_type: str, ref_id: int):
    """Delete a document from vector_documents."""
    existing = db.execute(
        select(VectorDocument).where(
            VectorDocument.document_type == doc_type,
            VectorDocument.reference_id == ref_id
        )
    ).scalar_one_or_none()
    if existing:
        db.delete(existing)
        db.commit()

def search_similar_documents(db: Session, query: str, user: User, limit: int = 5) -> List[VectorDocument]:
    """Retrieve semantically relevant documents filtered by the user's role profile."""
    query_embedding = get_embedding(query, task_type="retrieval_query")
    if not query_embedding:
        return []
    
    # Build query
    stmt = select(VectorDocument)
    
    # Apply profile security filters
    if user.role == UserRole.admin:
        # Admins can view everything
        pass
    elif user.role == UserRole.agent:
        # Agents can view tickets assigned to their team, tickets created by them, or tickets assigned to them
        stmt = stmt.where(
            or_(
                VectorDocument.metadata_json['team_id'].as_integer() == user.team_id,
                VectorDocument.metadata_json['created_by'].as_integer() == user.id,
                VectorDocument.metadata_json['assigned_to'].as_integer() == user.id
            )
        )
    else:  # Employee
        # Employees can ONLY view tickets they created or where they are assigned (if any)
        stmt = stmt.where(
            or_(
                VectorDocument.metadata_json['created_by'].as_integer() == user.id,
                VectorDocument.metadata_json['assigned_to'].as_integer() == user.id
            )
        )
        
    # Order by cosine distance (pgvector operator `<=>` is cosine_distance)
    stmt = stmt.order_by(VectorDocument.embedding.cosine_distance(query_embedding)).limit(limit)
    
    results = db.execute(stmt).scalars().all()
    return list(results)

def generate_chatbot_response(db: Session, query: str, chat_history: List[Dict[str, str]], user: User) -> str:
    """Retrieve relevant context and generate response using Gemini."""
    if not settings.GEMINI_API_KEY:
        return "I apologize, but my AI core is currently not configured with an API key. Please contact your administrator to set GEMINI_API_KEY in the environment."
        
    try:
        # 1. Retrieve profile-scoped documents
        docs = search_similar_documents(db, query, user, limit=5)
        context_blocks = [doc.content for doc in docs]
        
        # 2. Build system instructions and context
        context_str = "\n---\n".join(context_blocks) if context_blocks else "No relevant tickets or comments found in the database."
        
        system_instruction = (
            f"You are a helpful Ticketing System Assistant. You are interacting with '{user.name}' who has the role '{user.role.value}'.\n"
            f"Here is some relevant context from the ticketing system database (only matching tickets and discussions they are allowed to see):\n"
            f"===\n"
            f"{context_str}\n"
            f"===\n"
            f"INSTRUCTIONS:\n"
            f"- Answer the user's questions truthfully and clearly based on the provided database context.\n"
            f"- Respect their user role '{user.role.value}'. If the context is empty, politely inform them that you couldn't find any relevant tickets under their profile access.\n"
            f"- Use Markdown formatting for your response (e.g., bullet points, bolding, code segments, tables if relevant).\n"
            f"- Maintain a polite, helpful, and professional tone."
        )
        
        # 3. Configure Gemini Model
        model = genai.GenerativeModel(
            model_name=settings.LLM_MODEL,
            system_instruction=system_instruction
        )
        
        # 4. Map chat history to Gemini's expected format: [{'role': 'user'|'model', 'parts': [text]}]
        gemini_history = []
        for msg in chat_history[-10:]:  # Keep last 10 messages for context
            role = "user" if msg.get("role") == "user" else "model"
            gemini_history.append({
                "role": role,
                "parts": [msg.get("content", "")]
            })
            
        # 5. Start chat session and generate response
        chat = model.start_chat(history=gemini_history)
        response = chat.send_message(query)
        return response.text
        
    except Exception as e:
        logger.error(f"Error in RAG generation: {str(e)}", exc_info=True)
        return f"An error occurred while processing your request: {str(e)}"
