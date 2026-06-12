import logging
import re
from typing import List, Dict, Any, Optional

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from pydantic import Field

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, or_, func, exists, and_

from app.core.config import settings
from app.models.userModel import User, UserRole
from app.models.ticketModel import Ticket
from app.models.commentModel import Comment
from app.models.vectorDocumentModel import VectorDocument

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LangChain Embeddings & LLM (lazy-initialized singletons)
# ---------------------------------------------------------------------------
_embeddings_model: Optional[GoogleGenerativeAIEmbeddings] = None
_llm: Optional[ChatGoogleGenerativeAI] = None


def _get_embeddings() -> Optional[GoogleGenerativeAIEmbeddings]:
    """Return the shared LangChain embeddings instance (lazy init)."""
    global _embeddings_model
    if _embeddings_model is not None:
        return _embeddings_model
    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is not set. Embeddings will be unavailable.")
        return None
    _embeddings_model = GoogleGenerativeAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        task_type="retrieval_document",
    )
    return _embeddings_model


def _get_llm() -> Optional[ChatGoogleGenerativeAI]:
    """Return the shared LangChain LLM instance (lazy init)."""
    global _llm
    if _llm is not None:
        return _llm
    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is not set. LLM will be unavailable.")
        return None
    _llm = ChatGoogleGenerativeAI(
        model=settings.LLM_MODEL,
        temperature=0.7,
    )
    return _llm


# ---------------------------------------------------------------------------
# Public embedding helper  (same signature as before)
# ---------------------------------------------------------------------------
def get_embedding(text: str, task_type: str = "retrieval_document") -> Optional[List[float]]:
    """Generate vector embedding using Google's embedding model via LangChain."""
    embeddings = _get_embeddings()
    if not embeddings:
        return None
    try:
        if task_type == "retrieval_query":
            return embeddings.embed_query(text)
        else:
            return embeddings.embed_documents([text])[0]
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        return None


# ---------------------------------------------------------------------------
# Ticket / Comment text formatters  (unchanged)
# ---------------------------------------------------------------------------
def format_ticket_text(ticket: Ticket) -> str:
    """Format ticket fields into a single context document for embedding."""
    created_by = ticket.created_by_user.username if ticket.created_by_user else "Unknown"
    assigned_to = ticket.assigned_user.username if ticket.assigned_user else "Unassigned"
    team_name = ticket.team.name if ticket.team else "None"
    sla_status = "Breached" if ticket.sla_breached else "Within SLA"
    
    return (
        f"Ticket ID: {ticket.id}\n"
        f"Title: {ticket.title}\n"
        f"Description: {ticket.description}\n"
        f"Status: {ticket.status.value if hasattr(ticket.status, 'value') else ticket.status}\n"
        f"Priority: {ticket.priority.value if hasattr(ticket.priority, 'value') else ticket.priority}\n"
        f"Created By: {created_by}\n"
        f"Assigned To: {assigned_to}\n"
        f"Team: {team_name}\n"
        f"SLA Status: {sla_status}\n"
        f"Due At: {ticket.due_at or 'Not set'}\n"
        f"Resolved At: {ticket.resolved_at or 'Not resolved'}\n"
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


# ---------------------------------------------------------------------------
# Indexing functions  (same signature, uses LangChain embeddings internally)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Query routing & role-based filtering  (unchanged)
# ---------------------------------------------------------------------------
def _should_use_direct_db_context(query: str) -> bool:
    """Detect if the query requires full database context rather than semantic search."""
    patterns = [
        # Aggregations / counts
        r"how many", r"count", r"total", r"number of",
        r"list all", r"show all", r"all tickets",
        r"breached", r"sla", r"overdue",
        r"summary", r"overview", r"statistics", r"stats",
        # Personal / role-based listings
        r"assigned to me", r"created by me", r"creted by me", r"my tickets", r"my open", r"my assigned",
        r"by me", r"assigned to", r"created by",
        # Specific ticket IDs
        r"ticket\s*#?\d+", r"id\s*#?\d+", r"#\d+"
    ]
    q_lower = query.lower()
    return any(re.search(p, q_lower) for p in patterns)


def _build_role_filter(stmt, user: User, model_class=Ticket):
    """Apply role-based access filter to a query and exclude inactive tickets."""
    if hasattr(model_class, 'is_active'):
        stmt = stmt.where(model_class.is_active == True)
        
    if user.role == UserRole.agent:
        stmt = stmt.where(
            or_(
                model_class.team_id == user.team_id,
                model_class.created_by == user.id,
                model_class.assigned_to == user.id,
            )
        )
    elif user.role != UserRole.admin:
        stmt = stmt.where(
            or_(
                model_class.created_by == user.id,
                model_class.assigned_to == user.id,
            )
        )
    return stmt


# ---------------------------------------------------------------------------
# Statistics & direct-DB context  (unchanged)
# ---------------------------------------------------------------------------
def _get_ticket_statistics(db: Session, user: User) -> str:
    """Compute exact aggregate statistics via SQL for accurate counts."""
    from app.models.teamModel import Team

    # Base query with role filter
    base = select(Ticket)
    base = _build_role_filter(base, user)

    tickets = db.execute(base).scalars().all()
    if not tickets:
        return "STATISTICS: No tickets found.\n"

    total = len(tickets)

    # Count by status
    status_counts: Dict[str, int] = {}
    priority_counts: Dict[str, int] = {}
    sla_breached_count = 0
    sla_ok_count = 0
    team_counts: Dict[str, int] = {}
    unassigned_count = 0

    for t in tickets:
        # Status
        s = t.status.value if hasattr(t.status, 'value') else str(t.status)
        status_counts[s] = status_counts.get(s, 0) + 1

        # Priority
        p = t.priority.value if hasattr(t.priority, 'value') else str(t.priority)
        priority_counts[p] = priority_counts.get(p, 0) + 1

        # SLA
        if t.sla_breached:
            sla_breached_count += 1
        else:
            sla_ok_count += 1

        # Unassigned
        if t.assigned_to is None:
            unassigned_count += 1

    lines = [
        "=== EXACT DATABASE STATISTICS (use these numbers, do NOT count manually) ===",
        f"Total Tickets: {total}",
        "",
        "By Status:",
    ]
    for status_name in ["open", "in_progress", "resolved", "closed"]:
        count = status_counts.get(status_name, 0)
        lines.append(f"  {status_name}: {count}")
    not_resolved = total - status_counts.get("resolved", 0) - status_counts.get("closed", 0)
    lines.append(f"  NOT resolved (open + in_progress): {not_resolved}")

    lines.append("")
    lines.append("By Priority:")
    for prio_name in ["urgent", "high", "medium", "low"]:
        count = priority_counts.get(prio_name, 0)
        lines.append(f"  {prio_name}: {count}")

    lines.append("")
    lines.append(f"SLA Breached: {sla_breached_count}")
    lines.append(f"SLA Within Target: {sla_ok_count}")
    lines.append(f"Unassigned Tickets: {unassigned_count}")
    lines.append("=== END STATISTICS ===")

    return "\n".join(lines)


def _get_direct_ticket_context(db: Session, user: User) -> str:
    """Fetch ALL tickets (role-filtered) directly from DB with pre-computed statistics."""
    stmt = select(Ticket).options(
        joinedload(Ticket.created_by_user),
        joinedload(Ticket.assigned_user),
        joinedload(Ticket.team),
    )
    stmt = _build_role_filter(stmt, user)

    tickets = db.execute(stmt).unique().scalars().all()
    if not tickets:
        return "No tickets found in the system."

    # Pre-computed statistics the LLM can trust
    stats = _get_ticket_statistics(db, user)

    # Individual ticket details
    blocks = [format_ticket_text(t) for t in tickets]
    ticket_details = "\n---\n".join(blocks)

    return f"{stats}\n\n=== INDIVIDUAL TICKET DETAILS ===\n{ticket_details}"


# ---------------------------------------------------------------------------
# Vector similarity search  (unchanged logic)
# ---------------------------------------------------------------------------
def search_similar_documents(db: Session, query: str, user: User, limit: int = 15) -> List[VectorDocument]:
    """Retrieve semantically relevant documents filtered by the user's role profile."""
    query_embedding = get_embedding(query, task_type="retrieval_query")
    if not query_embedding:
        return []
    
    from app.models.ticketModel import Ticket
    from app.models.commentModel import Comment
    
    # Check that the vector document refers to an active ticket:
    # 1. If document_type == 'ticket', the ticket itself must be active
    # 2. If document_type == 'comment', the comment's ticket must be active
    ticket_is_active = exists().where(
        and_(
            Ticket.id == VectorDocument.reference_id,
            Ticket.is_active == True
        )
    )
    comment_ticket_is_active = exists().where(
        and_(
            Comment.id == VectorDocument.reference_id,
            Comment.ticket_id == Ticket.id,
            Ticket.is_active == True
        )
    )
    
    # Build query
    stmt = select(VectorDocument).where(
        or_(
            and_(VectorDocument.document_type == 'ticket', ticket_is_active),
            and_(VectorDocument.document_type == 'comment', comment_ticket_is_active)
        )
    )
    
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


# ---------------------------------------------------------------------------
# Custom LangChain Retriever  (NEW — wraps existing retrieval logic)
# ---------------------------------------------------------------------------
class TicketingRetriever(BaseRetriever):
    """
    Custom LangChain retriever that wraps the ticketing system's
    dual-path retrieval strategy (direct DB vs. vector search)
    with full role-based access control.
    """
    db: Any = Field(exclude=True)
    user: Any = Field(exclude=True)

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        """Retrieve documents using the appropriate strategy."""
        if _should_use_direct_db_context(query):
            # For counting / listing / metadata queries — fetch all from DB
            context_str = _get_direct_ticket_context(self.db, self.user)
            logger.info("Using direct DB context for metadata / aggregation query")
            return [Document(page_content=context_str, metadata={"source": "direct_db"})]
        else:
            # For specific questions — use semantic vector search
            docs = search_similar_documents(self.db, query, self.user, limit=15)
            if not docs:
                return [Document(page_content="No relevant tickets or comments found in the database.", metadata={"source": "vector_search"})]
            return [
                Document(page_content=doc.content, metadata={"source": "vector_search", "doc_type": doc.document_type, "ref_id": doc.reference_id})
                for doc in docs
            ]


# ---------------------------------------------------------------------------
# LangChain RAG Chain builder
# ---------------------------------------------------------------------------
def _build_rag_chain(db: Session, user: User):
    """Build the full LangChain RAG chain with history-aware retrieval."""
    llm = _get_llm()
    retriever = TicketingRetriever(db=db, user=user)

    # --- Step 1: History-aware retriever ---
    # Reformulates the user's query using chat history for better retrieval
    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "Given a chat history and the latest user question which might reference "
         "context in the chat history, formulate a standalone question which can be "
         "understood without the chat history. Do NOT answer the question, just "
         "reformulate it if needed and otherwise return it as is."),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )

    # --- Step 2: QA chain with system prompt ---
    qa_system_prompt = (
        "You are a helpful Ticketing System Assistant. "
        "You are interacting with '{user_name}' who has the role '{user_role}'.\n"
        "Here is the COMPLETE and AUTHORITATIVE context from the ticketing system "
        "database (only data they are allowed to see):\n"
        "===\n"
        "{context}\n"
        "===\n"
        "INSTRUCTIONS:\n"
        "- Answer the user's questions truthfully and clearly based ONLY on the "
        "provided database context above.\n"
        "- When asked to count tickets, count EVERY ticket in the context that "
        "matches the criteria. Do NOT miss any.\n"
        "- SLA Status field tells you if a ticket has breached its SLA ('Breached') "
        "or not ('Within SLA').\n"
        "- Respect their user role '{user_role}'. If the context is empty, politely "
        "inform them that you couldn't find any relevant tickets under their profile "
        "access.\n"
        "- Use Markdown formatting for your response (e.g., bullet points, bolding, "
        "code segments, tables if relevant).\n"
        "- Maintain a polite, helpful, and professional tone."
    )

    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", qa_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    document_chain = create_stuff_documents_chain(llm, qa_prompt)
    return create_retrieval_chain(history_aware_retriever, document_chain)


# ---------------------------------------------------------------------------
# Main entry point  (same signature as before)
# ---------------------------------------------------------------------------
def generate_chatbot_response(db: Session, query: str, chat_history: List[Dict[str, str]], user: User) -> str:
    """Retrieve relevant context and generate response using LangChain + Gemini."""
    if not settings.GEMINI_API_KEY:
        return (
            "I apologize, but my AI core is currently not configured with an API key. "
            "Please contact your administrator to set GEMINI_API_KEY in the environment."
        )
        
    try:
        # 1. Build the RAG chain
        rag_chain = _build_rag_chain(db, user)

        # 2. Convert chat history to LangChain message objects
        lc_history = []
        for msg in chat_history[-10:]:  # Keep last 10 messages for context
            if msg.get("role") == "user":
                lc_history.append(HumanMessage(content=msg.get("content", "")))
            else:
                lc_history.append(AIMessage(content=msg.get("content", "")))

        # 3. Invoke the chain
        result = rag_chain.invoke({
            "input": query,
            "chat_history": lc_history,
            "user_name": user.name,
            "user_role": user.role.value,
        })

        return result["answer"]
        
    except Exception as e:
        logger.error(f"Error in RAG generation: {str(e)}", exc_info=True)
        return f"An error occurred while processing your request: {str(e)}"
