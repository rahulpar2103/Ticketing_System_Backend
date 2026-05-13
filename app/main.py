# pyrefly: ignore [missing-import]
from fastapi import FastAPI
from app.routers import mainRouter
from app.db.database import engine, Base
from app.core.exceptions import PermissionDeniedException, InvalidCredentialsException, NotFoundException, AlreadyExistsException, UnauthorizedException, SessionException, MissingCredentialException, ValidationException
from app.models.userModel import User
from app.models.ticketModel import Ticket
from app.models.teamModel import Team

Base.metadata.create_all(bind=engine,checkfirst=True)

app = FastAPI()

app.include_router(mainRouter.router)

app.add_exception_handler(PermissionDeniedException,PermissionDeniedException)
app.add_exception_handler(InvalidCredentialsException,InvalidCredentialsException)
app.add_exception_handler(NotFoundException,NotFoundException)
app.add_exception_handler(AlreadyExistsException,AlreadyExistsException)
app.add_exception_handler(UnauthorizedException,UnauthorizedException)
app.add_exception_handler(SessionException,SessionException)
app.add_exception_handler(MissingCredentialException,MissingCredentialException)
app.add_exception_handler(ValidationException,ValidationException)


@app.get("/")
def read_root():
    return {"Hello": "World"}
