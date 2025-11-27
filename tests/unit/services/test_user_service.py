"""Unit tests for UserService.

This module tests user management logic including creation and settings updates.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Mock imports
from app.services.user_service import UserService
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
    user.telegram_chat_id = "chat-123"
    user.telegram_username = "tg_user"
    return user


@pytest.fixture
def mock_settings():
    """Create mock user settings."""
    settings = MagicMock(spec=UserSettings)
    settings.ff_threshold = 0.1
    return settings


@pytest.fixture
def mock_app_settings():
    """Mock app configuration."""
    with patch("app.services.user_service.app_settings") as mock:
        mock.default_ff_threshold = 0.1
        mock.default_min_open_interest = 100
        mock.default_min_volume = 50
        mock.default_max_bid_ask_pct = 0.05
        mock.default_sigma_fwd_floor = 0.05
        mock.default_stability_scans = 2
        mock.default_cooldown_minutes = 120
        mock.default_timezone = "UTC"
        yield mock


# ============================================================================
# Tests for get_or_create_user
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestGetOrCreateUser:
    """Test get or create user."""
    
    async def test_existing_user(self, mock_db, mock_user):
        """✅ Existing user found → return user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        user = await UserService.get_or_create_user(mock_db, "chat-123")
        
        assert user == mock_user
        mock_db.add.assert_not_called()
    
    async def test_update_username(self, mock_db, mock_user):
        """✅ Update telegram_username if different."""
        mock_user.telegram_username = "old_name"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        user = await UserService.get_or_create_user(mock_db, "chat-123", "new_name")
        
        assert user.telegram_username == "new_name"
        mock_db.commit.assert_called_once()
    
    async def test_create_new_user(self, mock_db, mock_app_settings):
        """✅ New user → create with default settings."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        user = await UserService.get_or_create_user(mock_db, "chat-new", "new_user")
        
        assert user.telegram_chat_id == "chat-new"
        assert user.telegram_username == "new_user"
        
        # Verify creation of user and settings
        assert mock_db.add.call_count == 2
        mock_db.commit.assert_called_once()


# ============================================================================
# Tests for update_user_settings
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestUpdateUserSettings:
    """Test update user settings."""
    
    async def test_update_fields(self, mock_db, mock_settings):
        """✅ Update provided kwargs only."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = mock_settings
        mock_db.execute.return_value = mock_result
        
        updated = await UserService.update_user_settings(
            mock_db, "user-123", ff_threshold=0.5, unknown_field="ignored"
        )
        
        assert updated.ff_threshold == 0.5
        # Unknown field should be ignored (or at least not crash if hasattr check works)
        # The mock object accepts any attribute set, but the code checks hasattr
        
        mock_db.commit.assert_called_once()


# ============================================================================
# Tests for get_discovery_users
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestGetDiscoveryUsers:
    """Test get_discovery_users method."""
    
    async def test_returns_discovery_enabled_users(self, mock_db):
        """✅ Return user IDs with discovery_mode=True."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("user-1",), ("user-2",), ("user-3",)]
        mock_db.execute.return_value = mock_result
        
        user_ids = await UserService.get_discovery_users(mock_db)
        
        assert user_ids == ["user-1", "user-2", "user-3"]
    
    async def test_returns_empty_list_if_no_users(self, mock_db):
        """✅ Return empty list if no users have discovery mode enabled."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result
        
        user_ids = await UserService.get_discovery_users(mock_db)
        
        assert user_ids == []
