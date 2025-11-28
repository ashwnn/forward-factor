"""Unit tests for Bot Handlers.

This module tests the Telegram bot command handlers and callbacks.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Mock imports
from app.bot.handlers.start import start_command
from app.bot.handlers.watchlist import add_command, remove_command, list_command
from app.bot.handlers.settings import settings_command
from app.bot.handlers.history import history_command
from app.bot.handlers.callbacks import button_callback


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_update():
    """Mock Telegram update."""
    update = MagicMock()
    update.effective_user.id = 123456789
    update.effective_user.username = "testuser"
    update.effective_chat.id = 123456789
    update.message.reply_text = AsyncMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.edit_message_reply_markup = AsyncMock()
    update.callback_query.data = "some_data"
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
    # We need to patch the services where they are imported in the handlers
    with patch("app.bot.handlers.start.UserService") as start_user_svc, \
         patch("app.bot.handlers.start.AuthService") as start_auth_svc, \
         patch("app.bot.handlers.watchlist.UserService") as wl_user_svc, \
         patch("app.bot.handlers.watchlist.SubscriptionService") as wl_sub_svc, \
         patch("app.bot.handlers.watchlist.TickerService") as wl_tick_svc, \
         patch("app.bot.handlers.settings.UserService") as set_user_svc, \
         patch("app.bot.handlers.history.UserService") as hist_user_svc, \
         patch("app.bot.handlers.history.SignalService") as hist_sig_svc, \
         patch("app.bot.handlers.callbacks.UserService") as cb_user_svc, \
         patch("app.bot.handlers.callbacks.SignalService") as cb_sig_svc:
        
        # Configure AsyncMocks
        # User Service
        for svc in [start_user_svc, wl_user_svc, set_user_svc, hist_user_svc, cb_user_svc]:
            svc.get_user_by_chat_id = AsyncMock()
            svc.get_or_create_user = AsyncMock()
            svc.update_user_settings = AsyncMock()
        
        # Auth Service
        start_auth_svc.verify_link_code = AsyncMock()
        
        # Subscription Service
        wl_sub_svc.add_subscription = AsyncMock()
        wl_sub_svc.remove_subscription = AsyncMock()
        wl_sub_svc.get_user_subscriptions = AsyncMock()
        
        # Ticker Service
        wl_tick_svc.update_ticker_registry = AsyncMock()
        
        # Signal Service
        hist_sig_svc.get_user_decisions = AsyncMock()
        cb_sig_svc.record_decision = AsyncMock()
        
        yield {
            "user": start_user_svc, # They should all be similar mocks, but we return one for setting return_values
            "auth": start_auth_svc,
            "sub": wl_sub_svc,
            "signal": cb_sig_svc,
            # We might need to set return values on ALL of them if they are distinct objects
            "all_user": [start_user_svc, wl_user_svc, set_user_svc, hist_user_svc, cb_user_svc],
            "all_sub": [wl_sub_svc],
            "all_signal": [hist_sig_svc, cb_sig_svc]
        }


@pytest.fixture
def mock_settings():
    """Mock app settings."""
    # Patch settings where it is used
    with patch("app.bot.handlers.start.settings") as mock:
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
        for svc in mock_services["all_user"]:
            svc.get_user_by_chat_id.return_value = MagicMock()
        
        await start_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        assert "Welcome" in mock_update.message.reply_text.call_args[0][0]
    
    async def test_start_new_user_no_code(self, mock_update, mock_context, mock_db_session, mock_services, mock_settings):
        """✅ Missing link code."""
        for svc in mock_services["all_user"]:
            svc.get_user_by_chat_id.return_value = None
        mock_context.args = []
        
        await start_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        assert "You must register on the web application" in mock_update.message.reply_text.call_args[0][0]
    
    async def test_start_new_user_valid_code(self, mock_update, mock_context, mock_db_session, mock_services, mock_settings):
        """✅ Valid link code."""
        for svc in mock_services["all_user"]:
            svc.get_user_by_chat_id.return_value = None
        mock_context.args = ["valid-code"]
        
        # Mock auth service returning a user
        mock_services["auth"].verify_link_code.return_value = MagicMock(id="user-1")
        
        await start_command(mock_update, mock_context)
        
        # Verify call on the specific mock used by start_command
        mock_services["auth"].verify_link_code.assert_called_once()
        # Should reply twice: once for success, once for welcome
        assert mock_update.message.reply_text.call_count == 2
        assert "Account successfully linked" in mock_update.message.reply_text.call_args_list[0][0][0]

    async def test_start_new_user_invalid_code(self, mock_update, mock_context, mock_db_session, mock_services, mock_settings):
        """✅ Invalid link code."""
        for svc in mock_services["all_user"]:
            svc.get_user_by_chat_id.return_value = None
        mock_context.args = ["invalid-code"]
        
        # Mock auth service returning None
        mock_services["auth"].verify_link_code.return_value = None
        
        await start_command(mock_update, mock_context)
        
        # Verify call on the specific mock used by start_command
        mock_services["auth"].verify_link_code.assert_called_once()
        mock_update.message.reply_text.assert_called_once()
        assert "Invalid link code" in mock_update.message.reply_text.call_args[0][0]


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
        for svc in mock_services["all_user"]:
            svc.get_user_by_chat_id.return_value = MagicMock(id="user-1")
        
        await add_command(mock_update, mock_context)
        
        # Verify call on the specific mock used by add_command (wl_sub_svc is mock_services['sub'])
        mock_services["sub"].add_subscription.assert_called_once()
        mock_update.message.reply_text.assert_called_once()
        assert "Added SPY" in mock_update.message.reply_text.call_args[0][0]
    
    async def test_remove_ticker(self, mock_update, mock_context, mock_db_session, mock_services):
        """✅ Remove ticker via bot."""
        mock_context.args = ["SPY"]
        for svc in mock_services["all_user"]:
            svc.get_user_by_chat_id.return_value = MagicMock(id="user-1")
        
        for svc in mock_services["all_sub"]:
            svc.remove_subscription.return_value = True
        
        await remove_command(mock_update, mock_context)
        
        mock_services["sub"].remove_subscription.assert_called_once()
        mock_update.message.reply_text.assert_called_once()
        assert "Removed SPY" in mock_update.message.reply_text.call_args[0][0]
    
    async def test_list_watchlist(self, mock_update, mock_context, mock_db_session, mock_services):
        """✅ View watchlist."""
        for svc in mock_services["all_user"]:
            svc.get_user_by_chat_id.return_value = MagicMock(id="user-1")
        
        mock_sub = MagicMock()
        mock_sub.ticker = "SPY"
        for svc in mock_services["all_sub"]:
            svc.get_user_subscriptions.return_value = [mock_sub]
        
        await list_command(mock_update, mock_context)
        
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
        # Use format: action:signal_id
        mock_update.callback_query.data = "place:sig-123"
        for svc in mock_services["all_user"]:
            svc.get_user_by_chat_id.return_value = MagicMock(id="user-1")
        
        await button_callback(mock_update, mock_context)
        
        # Verify call on the specific mock used by button_callback (cb_sig_svc is mock_services['signal'])
        mock_services["signal"].record_decision.assert_called_once()
        mock_update.callback_query.answer.assert_called_once()
        # It calls edit_message_text, not edit_message_reply_markup
        mock_update.callback_query.edit_message_text.assert_called_once()
