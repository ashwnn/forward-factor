"""Unit tests for Authentication Routes.

This module tests the authentication API endpoints including registration,
login, and Telegram account linking.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import status, HTTPException
from datetime import datetime

# We mock app imports to avoid pydantic errors during test collection
# if the environment is not compatible.
# In a real run, these would be imported normally.
from app.api.routes.auth import router
from app.models.user import User


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = "user-123"
    user.email = "test@example.com"
    user.password_hash = "hashed_password"
    user.created_at = datetime(2025, 1, 1, 12, 0, 0)
    user.status = "active"
    return user


@pytest.fixture
def mock_auth_service():
    """Mock AuthService methods."""
    with patch("app.api.routes.auth.AuthService") as mock:
        yield mock


@pytest.fixture
def mock_settings():
    """Mock app settings."""
    with patch("app.api.routes.auth.settings") as mock:
        mock.registration_enabled = True
        mock.access_token_expire_minutes = 30
        yield mock


@pytest.fixture
def mock_create_token():
    """Mock create_access_token."""
    with patch("app.api.routes.auth.create_access_token") as mock:
        mock.return_value = "mock-token"
        yield mock


# ============================================================================
# Tests for POST /register
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestRegister:
    """Test user registration endpoint."""
    
    async def test_valid_registration(self, mock_db, mock_auth_service, mock_settings, mock_create_token, mock_user):
        """✅ Valid registration → 201 + access token."""
        # Setup mocks
        mock_auth_service.register_user = AsyncMock(return_value=mock_user)
        
        # Import the route handler directly to test logic
        from app.api.routes.auth import register, RegisterRequest
        from fastapi import Request
        
        request_obj = MagicMock(spec=Request)
        register_request = RegisterRequest(email="test@example.com", password="password123")
        
        response = await register(request_obj, register_request, mock_db)
        
        # Verify response
        assert response["access_token"] == "mock-token"
        assert response["user"]["email"] == "test@example.com"
        
        # Verify calls
        mock_auth_service.register_user.assert_called_once_with(
            "test@example.com", "password123", mock_db
        )
    
    async def test_registration_disabled(self, mock_db, mock_settings):
        """✅ Registration disabled → 403."""
        mock_settings.registration_enabled = False
        
        from app.api.routes.auth import register, RegisterRequest
        from fastapi import Request
        
        request_obj = MagicMock(spec=Request)
        register_request = RegisterRequest(email="test@example.com", password="password123")
        
        with pytest.raises(HTTPException) as exc:
            await register(request_obj, register_request, mock_db)
        
        assert exc.value.status_code == status.HTTP_403_FORBIDDEN
    
    async def test_weak_password(self, mock_db, mock_settings):
        """✅ Weak password (< 8 chars) → 400."""
        from app.api.routes.auth import register, RegisterRequest
        from fastapi import Request
        
        request_obj = MagicMock(spec=Request)
        register_request = RegisterRequest(email="test@example.com", password="short")
        
        with pytest.raises(HTTPException) as exc:
            await register(request_obj, register_request, mock_db)
        
        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# Tests for POST /login
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestLogin:
    """Test login endpoint."""
    
    async def test_valid_credentials(self, mock_db, mock_auth_service, mock_create_token, mock_user):
        """✅ Valid credentials → 200 + access token."""
        mock_auth_service.authenticate_user = AsyncMock(return_value=mock_user)
        mock_auth_service.ensure_link_code = AsyncMock(return_value="code-123")
        
        # Mock telegram_chats query result (empty list for this test)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        from app.api.routes.auth import login
        from fastapi.security import OAuth2PasswordRequestForm
        from fastapi import Request
        
        request_obj = MagicMock(spec=Request)
        form_data = MagicMock(spec=OAuth2PasswordRequestForm)
        form_data.username = "test@example.com"
        form_data.password = "password123"
        
        response = await login(request_obj, form_data, mock_db)
        
        assert response["access_token"] == "mock-token"
        assert response["user"]["link_code"] == "code-123"
    
    async def test_invalid_credentials(self, mock_db, mock_auth_service):
        """✅ Invalid credentials → 401."""
        mock_auth_service.authenticate_user = AsyncMock(return_value=None)
        
        from app.api.routes.auth import login
        from fastapi import Request
        
        request_obj = MagicMock(spec=Request)
        form_data = MagicMock()
        form_data.username = "test@example.com"
        form_data.password = "wrong"
        
        with pytest.raises(HTTPException) as exc:
            await login(request_obj, form_data, mock_db)
        
        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Tests for Telegram Linking
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestTelegramLink:
    """Test Telegram linking endpoints."""
    
    async def test_unlink_telegram(self, mock_db, mock_auth_service, mock_user):
        """✅ Unlinks telegram account."""
        updated_user = mock_user
        mock_auth_service.unlink_telegram_username = AsyncMock(return_value=updated_user)
        
        from app.api.routes.auth import unlink_telegram
        
        response = await unlink_telegram(mock_user, mock_db)
        
        # Just verify the service was called
        mock_auth_service.unlink_telegram_username.assert_called_once()


# ============================================================================
# Tests for GET /me
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestGetMe:
    """Test get current user endpoint."""
    
    async def test_get_current_user_info(self, mock_user, mock_db, mock_auth_service):
        """✅ Returns current user info with link code."""
        mock_user.link_code = "code-123"
        mock_auth_service.ensure_link_code = AsyncMock(return_value="code-123")
        
        # Mock telegram_chats query result (empty list for this test)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        from app.api.routes.auth import get_current_user_info
        
        response = await get_current_user_info(mock_user, mock_db)
        
        assert response["email"] == mock_user.email
        assert response["id"] == mock_user.id
        assert response["link_code"] == "code-123"
        assert response["telegram_chats"] == []
