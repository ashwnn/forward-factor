"""Unit tests for Bot Handlers.

This module tests the Telegram bot command handlers and callbacks.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Mock imports
from app.bot.handlers.start import start_command
from app.bot.handlers.watchlist import add_ticker_command, remove_ticker_command, list_watchlist_command
from app.bot.handlers.settings import settings_command
from app.bot.handlers.history import history_command
from app.bot.handlers.callbacks import handle_decision


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_update():
    """Mock Telegram Update."""
    update = MagicMock()
    update.effective_chat.id = 12345
    update.effective_user.username = "testuser"
    update.message.reply_text = AsyncMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_reply_markup = AsyncMock()
    update.callback_query.data = "decision:place:sig-123"
    return update


@pytest.fixture
def mock_context():
    """Mock Telegram Context."""
    context = MagicMock()
    context.args = []
    return context


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    
    with patch("app.core.database.AsyncSessionLocal", return_value=session):
        yield session


@pytest.fixture
def mock_services():
    """Mock services."""
    with patch("app.services.UserService") as user_svc, \
         patch("app.services.SubscriptionService") as sub_svc, \
         patch("app.services.SignalService") as sig_svc:
        yield {
            "user": user_svc,
            "sub": sub_svc,
            "signal": sig_svc
        }


@pytest.fixture
def mock_settings():
    """Mock app settings."""
    with patch("app.core.config.settings") as mock:
        mock.invite_code = "secret"
        yield mock


# ============================================================================
# Tests for Start Handler
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestStartHandler:
    """Test /start command."""
    
    async def test_start_existing_user(self, mock_update, mock_context, mock_db_session, mock_services):
        """✅ User registration/retrieval."""
        mock_services["user"].get_user_by_chat_id.return_value = MagicMock()
        
        await start_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        assert "Welcome" in mock_update.message.reply_text.call_args[0][0]
    
    async def test_start_new_user_no_code(self, mock_update, mock_context, mock_db_session, mock_services, mock_settings):
        """✅ Missing invite code."""
        mock_services["user"].get_user_by_chat_id.return_value = None
        mock_context.args = []
        
        await start_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        assert "Access Restricted" in mock_update.message.reply_text.call_args[0][0]
    
    async def test_start_new_user_valid_code(self, mock_update, mock_context, mock_db_session, mock_services, mock_settings):
        """✅ Valid invite code."""
        mock_services["user"].get_user_by_chat_id.return_value = None
        mock_context.args = ["secret"]
        
        await start_command(mock_update, mock_context)
        
        mock_services["user"].get_or_create_user.assert_called_once()
        mock_update.message.reply_text.assert_called_once()


# ============================================================================
# Tests for Watchlist Handler
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestWatchlistHandler:
    """Test watchlist commands."""
    
    async def test_add_ticker(self, mock_update, mock_context, mock_db_session, mock_services):
        """✅ Add ticker via bot."""
        mock_context.args = ["SPY"]
        mock_services["user"].get_user_by_chat_id.return_value = MagicMock(id="user-1")
        
        await add_ticker_command(mock_update, mock_context)
        
        mock_services["sub"].add_subscription.assert_called_once()
        mock_update.message.reply_text.assert_called_once()
        assert "Added SPY" in mock_update.message.reply_text.call_args[0][0]
    
    async def test_remove_ticker(self, mock_update, mock_context, mock_db_session, mock_services):
        """✅ Remove ticker via bot."""
        mock_context.args = ["SPY"]
        mock_services["user"].get_user_by_chat_id.return_value = MagicMock(id="user-1")
        mock_services["sub"].remove_subscription.return_value = True
        
        await remove_ticker_command(mock_update, mock_context)
        
        mock_services["sub"].remove_subscription.assert_called_once()
        mock_update.message.reply_text.assert_called_once()
        assert "Removed SPY" in mock_update.message.reply_text.call_args[0][0]
    
    async def test_list_watchlist(self, mock_update, mock_context, mock_db_session, mock_services):
        """✅ View watchlist."""
        mock_services["user"].get_user_by_chat_id.return_value = MagicMock(id="user-1")
        mock_sub = MagicMock()
        mock_sub.ticker = "SPY"
        mock_services["sub"].get_user_subscriptions.return_value = [mock_sub]
        
        await list_watchlist_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        assert "SPY" in mock_update.message.reply_text.call_args[0][0]


# ============================================================================
# Tests for Callbacks Handler
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestCallbacksHandler:
    """Test callback handlers."""
    
    async def test_decision_callback(self, mock_update, mock_context, mock_db_session, mock_services):
        """✅ Signal decision callbacks."""
        mock_update.callback_query.data = "decision:placed:sig-123"
        mock_services["user"].get_user_by_chat_id.return_value = MagicMock(id="user-1")
        
        await handle_decision(mock_update, mock_context)
        
        mock_services["signal"].record_decision.assert_called_once()
        mock_update.callback_query.answer.assert_called_once()
        mock_update.callback_query.edit_message_reply_markup.assert_called_once()
