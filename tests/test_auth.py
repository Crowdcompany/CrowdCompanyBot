"""
Tests für die Telegram-Authentifizierung
"""

import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from telegram import Update, User, Message, Chat

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.bot import is_authorized, Crowdbot


class TestAuthentication:
    """Tests für die Authentifizierungsfunktionen."""

    def test_is_authorized_with_valid_user(self):
        """Test: Autorisierter User wird akzeptiert."""
        with patch.dict(os.environ, {"ALLOWED_USER_IDS": "7043093505"}):
            assert is_authorized(7043093505) is True

    def test_is_authorized_with_invalid_user(self):
        """Test: Nicht-autorisierter User wird abgelehnt."""
        with patch.dict(os.environ, {"ALLOWED_USER_IDS": "7043093505"}):
            assert is_authorized(12345) is False

    def test_is_authorized_with_multiple_users(self):
        """Test: Mehrere autorisierte User funktionieren."""
        with patch.dict(os.environ, {"ALLOWED_USER_IDS": "7043093505,12345,67890"}):
            assert is_authorized(7043093505) is True
            assert is_authorized(12345) is True
            assert is_authorized(67890) is True
            assert is_authorized(99999) is False

    def test_is_authorized_with_empty_list(self):
        """Test: Leere Liste lehnt alle ab."""
        with patch.dict(os.environ, {"ALLOWED_USER_IDS": ""}):
            assert is_authorized(7043093505) is False

    def test_is_authorized_with_whitespace(self):
        """Test: Whitespace in der Liste wird ignoriert."""
        with patch.dict(os.environ, {"ALLOWED_USER_IDS": "7043093505 , 12345 , 67890"}):
            assert is_authorized(7043093505) is True
            assert is_authorized(12345) is True
            assert is_authorized(67890) is True

    def test_is_authorized_with_invalid_format(self):
        """Test: Ungültiges Format lehnt alle ab."""
        with patch.dict(os.environ, {"ALLOWED_USER_IDS": "abc,def"}):
            assert is_authorized(7043093505) is False

    @pytest.mark.asyncio
    async def test_check_authorization_allows_authorized_user(self):
        """Test: check_authorization lässt autorisierten User durch."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test_token",
            "ALLOWED_USER_IDS": "7043093505"
        }):
            bot = Crowdbot()

            # Mock Update und User
            user = User(id=7043093505, first_name="Test", is_bot=False)
            message = MagicMock(spec=Message)
            message.reply_text = AsyncMock()
            chat = Chat(id=7043093505, type="private")

            update = MagicMock(spec=Update)
            update.effective_user = user
            update.message = message

            result = await bot.check_authorization(update)

            assert result is True
            message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_authorization_blocks_unauthorized_user(self):
        """Test: check_authorization blockiert nicht-autorisierten User."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test_token",
            "ALLOWED_USER_IDS": "7043093505"
        }):
            bot = Crowdbot()

            # Mock Update und User
            user = User(id=99999, first_name="Hacker", is_bot=False)
            message = MagicMock(spec=Message)
            message.reply_text = AsyncMock()

            update = MagicMock(spec=Update)
            update.effective_user = user
            update.message = message

            result = await bot.check_authorization(update)

            assert result is False
            message.reply_text.assert_called_once()

            # Prüfe ob Fehlermeldung korrekt ist
            call_args = message.reply_text.call_args[0][0]
            assert "nicht autorisiert" in call_args.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
