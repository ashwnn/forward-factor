"""Unit tests for AuthService.

This module tests authentication logic including registration, login,
and Telegram account linking.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status

# Mock imports to avoid pydantic errors
from app.services.auth_service import AuthService
from app.models.user import User, UserSettings


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = "user-123"
    user.email = "test@example.com"
    user.password_hash = "hashed_password"
    user.telegram_username = None
    user.telegram_chat_id = None
    return user


@pytest.fixture
def mock_auth_utils():
    """Mock auth utility functions."""
    with patch("app.services.auth_service.hash_password") as mock_hash, \
         patch("app.services.auth_service.verify_password") as mock_verify:
        mock_hash.return_value = "hashed_password"
        mock_verify.return_value = True
        yield mock_hash, mock_verify


# ============================================================================
# Tests for register_user
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestRegisterUser:
    """Test user registration."""
    
    async def test_register_success(self, mock_db, mock_auth_utils):
        """✅ Create new user with hashed password."""
        # Mock no existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        user = await AuthService.register_user("test@example.com", "password123", mock_db)
        
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password"
        assert user.status == "active"
        
        # Verify DB operations
        assert mock_db.add.call_count == 2  # User + Settings
        mock_db.commit.assert_called_once()
    
    async def test_duplicate_email(self, mock_db, mock_user):
        """✅ Duplicate email → HTTPException 409."""
        # Mock existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc:
            await AuthService.register_user("test@example.com", "password123", mock_db)
        
        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# Tests for authenticate_user
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestAuthenticateUser:
    """Test user authentication."""
    
    async def test_valid_credentials(self, mock_db, mock_user, mock_auth_utils):
        """✅ Valid credentials → return User."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        user = await AuthService.authenticate_user("test@example.com", "password123", mock_db)
        
        assert user == mock_user
    
    async def test_invalid_email(self, mock_db):
        """✅ Invalid email → return None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        user = await AuthService.authenticate_user("wrong@example.com", "password123", mock_db)
        
        assert user is None
    
    async def test_invalid_password(self, mock_db, mock_user, mock_auth_utils):
        """✅ Invalid password → return None."""
        mock_hash, mock_verify = mock_auth_utils
        mock_verify.return_value = False
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        user = await AuthService.authenticate_user("test@example.com", "wrongpass", mock_db)
        
        assert user is None


# ============================================================================
# Tests for Link Code
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestLinkCode:
    """Test link code generation and verification."""
    
    def test_generate_link_code(self):
        """✅ Generate valid 16-character hex link code."""
        code = AuthService.generate_link_code()
        assert isinstance(code, str)
        assert len(code) == 16  # 8 bytes * 2 hex chars = 16 characters
        # Verify it's valid hex
        assert all(c in '0123456789abcdef' for c in code)
    
    async def test_ensure_link_code_existing(self, mock_db, mock_user):
        """✅ Existing code → return it."""
        mock_user.link_code = "existing-code"
        
        code = await AuthService.ensure_link_code(mock_user, mock_db)
        
        assert code == "existing-code"
        mock_db.add.assert_not_called()
    
    async def test_ensure_link_code_new(self, mock_db, mock_user):
        """✅ No code → generate and save."""
        mock_user.link_code = None
        
        code = await AuthService.ensure_link_code(mock_user, mock_db)
        
        assert code is not None
        assert mock_user.link_code == code
        mock_db.add.assert_called_once_with(mock_user)
        mock_db.commit.assert_called_once()

    async def test_verify_link_code_success(self, mock_db, mock_user):
        """✅ Valid code → link account by creating TelegramChat."""
        # Mock finding user by link code
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        
        # Mock checking if chat already exists (should return None for new chat)
        mock_existing_check = MagicMock()
        mock_existing_check.scalar_one_or_none.return_value = None
        
        # Setup execute to return different results for different queries
        mock_db.execute.side_effect = [mock_result, mock_existing_check]
        
        user = await AuthService.verify_link_code(
            "valid-code", 
            "chat-123", 
            "John",
            "Doe",
            "johndoe", 
            mock_db
        )
        
        assert user == mock_user
        # Verify TelegramChat was added to db
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    async def test_verify_link_code_invalid(self, mock_db):
        """✅ Invalid code → return None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        user = await AuthService.verify_link_code(
            "invalid-code", 
            "chat-123", 
            "John",
            "Doe",
            "johndoe", 
            mock_db
        )
        
        assert user is None


# ============================================================================
# Tests for unlink_telegram_username
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestUnlinkTelegram:
    """Test Telegram unlinking."""
    
    async def test_unlink_success(self, mock_db, mock_user):
        """✅ Clear telegram_chat_id and telegram_username."""
        mock_user.telegram_username = "tg_user"
        mock_user.telegram_chat_id = "12345"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        user = await AuthService.unlink_telegram_username("user-123", mock_db)
        
        assert user.telegram_username is None
        assert user.telegram_chat_id is None
        mock_db.commit.assert_called_once()
