# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Request
# pyrefly: ignore [missing-import]
from fastapi.responses import JSONResponse
# pyrefly: ignore [missing-import]
from app.routers import mainRouter
# pyrefly: ignore [missing-import]
from app.db.database import engine, Base
from app.core.exceptions import (
    PermissionDeniedException,
    InvalidCredentialsException,
    NotFoundException,
    AlreadyExistsException,
    UnauthorizedException,
    SessionException,
    MissingCredentialException,
    ValidationException,
)
from app.models import userModel 

Base.metadata.create_all(bind=engine, checkfirst=True)

app = FastAPI()

app.include_router(mainRouter.router)

async def _custom_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

for exc_class in (
    PermissionDeniedException,
    InvalidCredentialsException,
    NotFoundException,
    AlreadyExistsException,
    UnauthorizedException,
    SessionException,
    MissingCredentialException,
    ValidationException,
):
    app.add_exception_handler(exc_class, _custom_exception_handler)


@app.get("/")
def read_root():
    return {"Hello": "World"}