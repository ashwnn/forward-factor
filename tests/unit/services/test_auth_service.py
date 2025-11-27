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
    return AsyncMock()


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
# Tests for link_telegram_username
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestLinkTelegram:
    """Test Telegram linking."""
    
    async def test_link_simple(self, mock_db, mock_user):
        """✅ No matching bot user → just update username."""
        # 1. Get user -> found
        # 2. Get bot user -> None
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = mock_user
        
        mock_bot_result = MagicMock()
        mock_bot_result.scalar_one_or_none.return_value = None
        
        mock_db.execute.side_effect = [mock_user_result, mock_bot_result]
        
        user = await AuthService.link_telegram_username("user-123", "new_tg", mock_db)
        
        assert user.telegram_username == "new_tg"
        mock_db.commit.assert_called_once()
    
    async def test_merge_bot_user(self, mock_db, mock_user):
        """✅ Merge bot user subscriptions to web user."""
        # Mock bot user
        bot_user = MagicMock(spec=User)
        bot_user.id = "bot-123"
        bot_user.telegram_chat_id = "chat-123"
        
        # Mock subscriptions
        mock_sub = MagicMock()
        mock_sub.ticker = "AAPL"
        
        # 1. Get user -> found
        # 2. Get bot user -> found
        # 3. Get bot subs -> [mock_sub]
        # 4. Check existing sub -> None
        
        mock_user_res = MagicMock()
        mock_user_res.scalar_one_or_none.return_value = mock_user
        
        mock_bot_res = MagicMock()
        mock_bot_res.scalar_one_or_none.return_value = bot_user
        
        mock_subs_res = MagicMock()
        mock_subs_res.scalars.return_value.all.return_value = [mock_sub]
        
        mock_exist_res = MagicMock()
        mock_exist_res.scalar_one_or_none.return_value = None
        
        mock_db.execute.side_effect = [
            mock_user_res, 
            mock_bot_res, 
            mock_subs_res, 
            mock_exist_res
        ]
        
        user = await AuthService.link_telegram_username("user-123", "bot_user", mock_db)
        
        assert user.telegram_chat_id == "chat-123"
        assert user.telegram_username == "bot_user"
        assert bot_user.status == "merged"
        assert mock_sub.user_id == user.id  # Transferred


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
