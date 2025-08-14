"""Main FastAPI application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time

from core.config import settings
from core.database import init_db, check_database_health
from middleware.auth import AuthMiddleware
from routers import auth, search, parcels, exports, admin, llm
from services.providers import check_provider_health
from services.background_jobs import get_background_job_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("Starting Backyard Builder Finder API")
    await init_db()
    
    # Check database health
    if not await check_database_health():
        logger.error("Database health check failed")
    else:
        logger.info("Database is healthy")
    
    # Check provider health
    provider_health = check_provider_health()
    logger.info(f"Provider health: {provider_health}")
    
    # Initialize background job processing if queue provider is available
    try:
        job_service = get_background_job_service()
        if job_service.queue_provider:
            await job_service.start_processing()
            logger.info("Background job processing started")
        else:
            logger.warning("Queue provider not available, background jobs disabled")
    except Exception as e:
        logger.error(f"Failed to start background job processing: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Multi-tenant SaaS for finding buildable backyard spaces",
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_REDOC else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(AuthMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add process time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(parcels.router, prefix="/api/parcels", tags=["Parcels"])
app.include_router(exports.router, prefix="/api/exports", tags=["Exports"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(llm.router, prefix="/api/llm", tags=["LLM"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_healthy = await check_database_health()
    provider_health = check_provider_health()
    
    # Determine overall health
    overall_healthy = db_healthy and not provider_health.get("error")
    
    return {
        "status": "healthy" if overall_healthy else "degraded",
        "database": "connected" if db_healthy else "disconnected",
        "providers": provider_health,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "configuration": {
            "storage_provider": settings.STORAGE_PROVIDER,
            "queue_provider": settings.QUEUE_PROVIDER,
            "secrets_provider": settings.SECRETS_PROVIDER,
            "metrics_provider": settings.METRICS_PROVIDER
        }
    }


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors."""
    logger.error(f"Internal error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)