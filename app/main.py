from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.routers import mainRouter
from app.core.limiter import limiter
from app.core.exceptions import (
    PermissionDeniedException, InvalidCredentialsException,
    NotFoundException, AlreadyExistsException, UnauthorizedException,
    SessionException, MissingCredentialException, ValidationException,
)

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(mainRouter.router)

async def _custom_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

for exc_class in (
    PermissionDeniedException, InvalidCredentialsException, NotFoundException,
    AlreadyExistsException, UnauthorizedException, SessionException,
    MissingCredentialException, ValidationException,
):
    app.add_exception_handler(exc_class, _custom_exception_handler)

@app.get("/")
def read_root():
    return {"Hello": "World"}