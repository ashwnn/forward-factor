"""Authentication API routes."""
from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.database import get_db
from app.core.auth import create_access_token, get_current_user
from app.core.config import settings
from app.services.auth_service import AuthService
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["authentication"])
logger = logging.getLogger(__name__)


# Request/Response Models
class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response with access token."""
    access_token: str
    token_type: str = "bearer"
    user: dict


class LinkTelegramRequest(BaseModel):
    """Request to link Telegram username."""
    telegram_username: str


class UserResponse(BaseModel):
    """User information response."""
    id: str
    email: Optional[str]
    telegram_chat_id: Optional[str]
    telegram_username: Optional[str]
    created_at: str
    status: str


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user with email and password.
    
    Returns an access token upon successful registration.
    """
    logger.info(f"Registration request received for email: {request.email}")
    
    # Check if registration is enabled
    if not settings.registration_enabled:
        logger.warning(f"Registration attempt rejected - registrations disabled: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="New user registrations are currently disabled"
        )
    
    # Validate password strength
    if len(request.password) < 8:
        logger.warning(f"Registration failed - weak password: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Register user
    logger.debug(f"Calling AuthService.register_user for: {request.email}")
    user = await AuthService.register_user(request.email, request.password, db)
    
    # Create access token
    logger.debug(f"Creating access token for user: {user.id}")
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    
    logger.info(f"✓ User registered successfully: {request.email} (ID: {user.id})")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "created_at": user.created_at.isoformat()
        }
    }


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password.
    
    Returns an access token upon successful authentication.
    """
    user = await AuthService.authenticate_user(form_data.username, form_data.password, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "telegram_username": user.telegram_username,
            "created_at": user.created_at.isoformat()
        }
    }


@router.post("/link-telegram", response_model=UserResponse)
async def link_telegram(
    request: LinkTelegramRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Link a Telegram username to the current user's account.
    
    Requires authentication.
    """
    user = await AuthService.link_telegram_username(
        str(current_user.id),
        request.telegram_username,
        db
    )
    
    return {
        "id": str(user.id),
        "email": user.email,
        "telegram_chat_id": user.telegram_chat_id,
        "telegram_username": user.telegram_username,
        "created_at": user.created_at.isoformat(),
        "status": user.status
    }


@router.post("/unlink-telegram", response_model=UserResponse)
async def unlink_telegram(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Unlink Telegram account from the current user.
    
    Requires authentication.
    """
    user = await AuthService.unlink_telegram_username(
        str(current_user.id),
        db
    )
    
    return {
        "id": str(user.id),
        "email": user.email,
        "telegram_chat_id": user.telegram_chat_id,
        "telegram_username": user.telegram_username,
        "created_at": user.created_at.isoformat(),
        "status": user.status
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    
    Requires authentication.
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "telegram_chat_id": current_user.telegram_chat_id,
        "telegram_username": current_user.telegram_username,
        "created_at": current_user.created_at.isoformat(),
        "status": current_user.status
    }
