from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.routers import mainRouter
from app.core.limiter import limiter
from app.core.config import settings
from app.core.exceptions import (
    PermissionDeniedException, InvalidCredentialsException,
    NotFoundException, AlreadyExistsException, UnauthorizedException,
    SessionException, MissingCredentialException, ValidationException,
)

app = FastAPI(
    title="Ticketing System API",
    description="Internal office ticketing system with role-based access control",
    version="1.0.0",
)

# ── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate Limiter ────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Routers ─────────────────────────────────────────────────────────────────
app.include_router(mainRouter.router)

# ── Custom Exception Handlers ───────────────────────────────────────────────
async def _custom_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

for exc_class in (
    PermissionDeniedException, InvalidCredentialsException, NotFoundException,
    AlreadyExistsException, UnauthorizedException, SessionException,
    MissingCredentialException, ValidationException,
):
    app.add_exception_handler(exc_class, _custom_exception_handler)

# ── Health Check ────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health_check():
    """
    Liveness + readiness probe.
    Returns the status of the API, database, and Redis connections.
    """
    status = {"api": "ok", "database": "ok", "redis": "ok"}
    healthy = True

    # Check database
    try:
        from app.db.database import engine
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        status["database"] = "unavailable"
        healthy = False

    # Check Redis
    try:
        from app.db.redis import redis_client
        redis_client.ping()
    except Exception:
        status["redis"] = "unavailable"
        healthy = False

    if healthy:
        return {"status": "healthy", "services": status}
    return JSONResponse(
        status_code=503,
        content={"status": "degraded", "services": status},
    )

@app.get("/")
def read_root():
    return {"message": "Ticketing System API", "docs": "/docs"}