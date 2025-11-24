"""FastAPI application for analytics and monitoring."""
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings
from app.services import SignalService
from typing import List, Optional
import logging
import time
import sys

# Import routers
from app.api.routes import auth, watchlist, settings as settings_router, signals

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Forward Factor Signal Bot API", version="1.0.0")


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Application starting up...")
    
    # Create admin account if configured
    if settings.admin_email and settings.admin_password:
        logger.info(f"Checking for admin account: {settings.admin_email}")
        from app.core.database import get_async_session
        from app.services.auth_service import AuthService
        from app.models.user import User
        from sqlalchemy import select
        
        async with get_async_session() as db:
            try:
                # Check if admin already exists
                result = await db.execute(select(User).where(User.email == settings.admin_email))
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    logger.info(f"✓ Admin account already exists: {settings.admin_email}")
                else:
                    # Create admin account
                    logger.info(f"Creating admin account: {settings.admin_email}")
                    admin_user = await AuthService.register_user(
                        settings.admin_email,
                        settings.admin_password,
                        db
                    )
                    logger.info(f"✓ Admin account created successfully: {admin_user.email} (ID: {admin_user.id})")
            except Exception as e:
                logger.error(f"✗ Failed to create admin account: {e}", exc_info=True)
    else:
        logger.info("No admin account configured (ADMIN_EMAIL/ADMIN_PASSWORD not set)")
    
    logger.info("Application startup complete")


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and responses."""
    start_time = time.time()
    
    # Log request
    logger.info(f"→ {request.method} {request.url.path}")
    logger.debug(f"  Headers: {dict(request.headers)}")
    logger.debug(f"  Query params: {dict(request.query_params)}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response
        logger.info(f"← {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")
        
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"← {request.method} {request.url.path} - ERROR after {process_time:.3f}s: {str(e)}")
        raise

# Add global exception handler to ensure CORS headers are sent even on errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions and ensure CORS headers are sent."""
    logger.error(f"Unhandled exception in {request.method} {request.url.path}")
    logger.error(f"Exception type: {type(exc).__name__}")
    logger.error(f"Exception message: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.log_level == "DEBUG" else "Internal server error"
        },
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        }
    )

# Configure CORS
logger.info(f"Configuring CORS with origins: {settings.cors_origins_list}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(auth.router)
app.include_router(watchlist.router)
app.include_router(settings_router.router)
app.include_router(signals.router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "ff-signal-bot-api"}


@app.get("/signals")
async def get_signals(
    ticker: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent signals (public endpoint for backward compatibility).
    
    Args:
        ticker: Optional ticker filter
        limit: Number of signals to return
    """
    signals = await SignalService.get_recent_signals(db, ticker, limit)
    
    return {
        "count": len(signals),
        "signals": [
            {
                "id": str(signal.id),
                "ticker": signal.ticker,
                "ff_value": signal.ff_value,
                "front_dte": signal.front_dte,
                "back_dte": signal.back_dte,
                "as_of_ts": signal.as_of_ts.isoformat(),
                "quality_score": signal.quality_score
            }
            for signal in signals
        ]
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.backend_port)
