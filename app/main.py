from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
import logging

from app.database import engine, Base
from app.routers import auth_router, user_router
from app.utils.security import limiter
from app.config import get_settings

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application."""
    # Startup
    logger.info("Démarrage du service d'authentification")
    Base.metadata.create_all(bind=engine)
    logger.info("Tables de base de données créées/vérifiées")
    yield
    # Shutdown
    logger.info("Arrêt du service d'authentification")


app = FastAPI(
    title="Auth Service - Decision Collective",
    description="Service d'authentification Magic Link + TOTP",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",  # Dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware pour les headers de sécurité
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Routes
app.include_router(auth_router)
app.include_router(user_router)


@app.get("/")
async def root():
    """Health check."""
    return {"status": "ok", "service": "auth"}


@app.get("/health")
async def health():
    """Health check détaillé."""
    return {
        "status": "healthy",
        "service": "auth-service",
        "version": "1.0.0"
    }


# Gestion des erreurs globales
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erreur non gérée: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erreur interne du serveur"}
    )
