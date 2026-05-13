from app.db.database import session_local

def get_db():
    db = session_local()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()