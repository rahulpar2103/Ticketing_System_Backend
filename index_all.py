import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.db.database import session_local
from app.models.ticketModel import Ticket
from app.models.commentModel import Comment
from app.services import rag_service

def index_all():
    db = session_local()
    try:
        print("Indexing all existing tickets...")
        tickets = db.query(Ticket).all()
        print(f"Found {len(tickets)} tickets.")
        for i, t in enumerate(tickets):
            success = rag_service.index_ticket(db, t)
            if success:
                print(f"Indexed ticket {t.id} ({i+1}/{len(tickets)})")
            else:
                print(f"Failed to index ticket {t.id} (check if GEMINI_API_KEY is configured)")
                
        print("\nIndexing all existing comments...")
        comments = db.query(Comment).all()
        print(f"Found {len(comments)} comments.")
        for i, c in enumerate(comments):
            success = rag_service.index_comment(db, c)
            if success:
                print(f"Indexed comment {c.id} ({i+1}/{len(comments)})")
            else:
                print(f"Failed to index comment {c.id}")
                
        print("\nIndexing complete!")
    finally:
        db.close()

if __name__ == "__main__":
    index_all()
