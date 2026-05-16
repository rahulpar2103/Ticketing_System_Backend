# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from app.db.database import get_db
# pyrefly: ignore [missing-import]
from app.models.commentModel import Comment
# pyrefly: ignore [missing-import]
from app.schemas.commentSchemas import CommentCreate, CommentResponse
# pyrefly: ignore [missing-import]
from app.services.auth_services import get_current_user
# pyrefly: ignore [missing-import]
from app.models.userModel import User


router = APIRouter(prefix="/comments/admin", tags=["Admin Comment"])


@router.post("/create", response_model=CommentResponse)
def create_comment(comment: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pass

@router.get("/", response_model=CommentResponse)
def get_all_comments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pass

@router.get("/{comment_id}", response_model=CommentResponse)
def get_comment(comment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pass
    
@router.post("/update/{comment_id}", response_model=CommentResponse)
def update_comment(comment_id: int, comment: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pass

@router.post("/delete/{comment_id}", response_model=CommentResponse)
def delete_comment(comment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pass
