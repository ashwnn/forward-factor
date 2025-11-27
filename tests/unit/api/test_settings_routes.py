"""Unit tests for Settings Routes.

This module tests the settings API endpoints including retrieval and updates.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import status, HTTPException

# Mock imports
from app.api.routes.settings import router
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
    return user


@pytest.fixture
def mock_user_service():
    """Mock UserService."""
    with patch("app.api.routes.settings.UserService") as mock:
        yield mock


@pytest.fixture
def mock_settings():
    """Create mock user settings."""
    settings = MagicMock(spec=UserSettings)
    settings.ff_threshold = 0.1
    settings.dte_pairs = [{"front": 30, "back": 60, "front_tol": 5, "back_tol": 10}]
    settings.vol_point = "ATM"
    settings.min_open_interest = 100
    settings.min_volume = 50
    settings.max_bid_ask_pct = 0.05
    settings.sigma_fwd_floor = 0.05
    settings.stability_scans = 2
    settings.cooldown_minutes = 120
    settings.quiet_hours = {"enabled": False, "start": "22:00", "end": "08:00"}
    settings.preferred_structure = "term_structure"
    settings.timezone = "UTC"
    settings.scan_priority = "balanced"
    return settings


# ============================================================================
# Tests for GET /api/settings
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestGetSettings:
    """Test get settings endpoint."""
    
    async def test_get_settings_success(self, mock_db, mock_user, mock_user_service, mock_settings):
        """✅ Returns all user settings."""
        mock_user_service.get_user_settings = AsyncMock(return_value=mock_settings)
        
        from app.api.routes.settings import get_settings
        
        response = await get_settings(current_user=mock_user, db=mock_db)
        
        assert response["ff_threshold"] == 0.1
        assert response["vol_point"] == "ATM"
        assert len(response["dte_pairs"]) == 1


# ============================================================================
# Tests for PUT /api/settings
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestUpdateSettings:
    """Test update settings endpoint."""
    
    async def test_update_settings_success(self, mock_db, mock_user, mock_user_service, mock_settings):
        """✅ Partial updates (only provided fields)."""
        mock_user_service.get_user_settings = AsyncMock(return_value=mock_settings)
        
        from app.api.routes.settings import update_settings, UpdateSettingsRequest
        
        request = UpdateSettingsRequest(ff_threshold=0.2)
        
        response = await update_settings(request, mock_user, mock_db)
        
        assert response["ff_threshold"] == 0.2
        assert mock_settings.ff_threshold == 0.2
        
        # Verify commit/refresh
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    async def test_invalid_dte_pairs_order(self, mock_db, mock_user, mock_user_service, mock_settings):
        """✅ DTE pair validation: front < back."""
        mock_user_service.get_user_settings = AsyncMock(return_value=mock_settings)
        
        from app.api.routes.settings import update_settings, UpdateSettingsRequest
        
        # Front >= Back
        request = UpdateSettingsRequest(
            dte_pairs=[{"front": 60, "back": 30, "front_tol": 5, "back_tol": 10}]
        )
        
        with pytest.raises(HTTPException) as exc:
            await update_settings(request, mock_user, mock_db)
        
        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Front DTE must be less than back DTE" in exc.value.detail
    
    async def test_invalid_dte_pairs_negative(self, mock_db, mock_user, mock_user_service, mock_settings):
        """✅ DTE pair validation: non-negative values."""
        mock_user_service.get_user_settings = AsyncMock(return_value=mock_settings)
        
        from app.api.routes.settings import update_settings, UpdateSettingsRequest
        
        # Negative values
        request = UpdateSettingsRequest(
            dte_pairs=[{"front": -10, "back": 30, "front_tol": 5, "back_tol": 10}]
        )
        
        with pytest.raises(HTTPException) as exc:
            await update_settings(request, mock_user, mock_db)
        
        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "DTE values must be positive" in exc.value.detail
