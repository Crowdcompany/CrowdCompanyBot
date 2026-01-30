"""
Integrationstests für Crowdbot

Diese Tests prüfen das Zusammenspiel aller Komponenten.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.memory_manager import MemoryManager
from src.llm_client import LLMClient


def test_full_conversation_flow():
    """Testet den kompletten Konversationsablauf."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        # Komponenten initialisieren
        memory_manager = MemoryManager(data_dir=tmpdir)
        llm_client = LLMClient()

        # Benutzer erstellen
        user_id = 12345
        username = "TestUser"

        assert memory_manager.create_user(user_id, username) is True
        assert memory_manager.user_exists(user_id) is True

        # Erste Nachricht speichern
        user_message = "Hallo, wie heißt du?"
        memory_manager.append_message(user_id, "user", user_message)

        # Kontext laden
        context = memory_manager.get_context(user_id)
        assert len(context) == 1
        assert context[0]["content"] == user_message

        # LLM-Antwort generieren (mit Mock)
        from unittest.mock import Mock, patch

        mock_response = Mock()
        mock_response.json.return_value = {
            "content": [
                {"type": "text", "text": "Ich bin Crowdbot, dein KI-Assistent!"}
            ]
        }
        mock_response.raise_for_status = Mock()

        with patch("src.llm_client.requests.post", return_value=mock_response):
            response = llm_client.chat(
                user_message=user_message,
                conversation_history=context
            )

            assert response is not None
            assert "Crowdbot" in response

        # Antwort speichern
        memory_manager.append_message(user_id, "assistant", response)

        # Kontext sollte nun beide Nachrichten enthalten
        context = memory_manager.get_context(user_id)
        assert len(context) == 2
        assert context[0]["role"] == "user"
        assert context[1]["role"] == "assistant"
        assert "Crowdbot" in context[1]["content"]

        print("Integrationstest erfolgreich!")


def test_reset_conversation():
    """Testet das Zurücksetzen einer Konversation."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        memory_manager = MemoryManager(data_dir=tmpdir)

        user_id = 12345

        # Benutzer mit Nachrichten erstellen
        memory_manager.create_user(user_id, "TestUser")
        memory_manager.append_message(user_id, "user", "Nachricht 1")
        memory_manager.append_message(user_id, "assistant", "Antwort 1")

        # Prüfen, dass Nachrichten existieren
        context = memory_manager.get_context(user_id)
        assert len(context) == 2

        # Zurücksetzen
        memory_manager.reset_user(user_id)

        # Prüfen, dass Kontext leer ist
        context = memory_manager.get_context(user_id)
        assert len(context) == 0

        print("Reset-Test erfolgreich!")


def test_memory_stats():
    """Testet die Gedächtnis-Statistiken."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        memory_manager = MemoryManager(data_dir=tmpdir)

        user_id = 12345

        # Statistiken für nicht existierenden Benutzer
        stats = memory_manager.get_memory_stats(user_id)
        assert stats["exists"] is False

        # Benutzer erstellen
        memory_manager.create_user(user_id, "TestUser")
        memory_manager.append_message(user_id, "user", "Nachricht 1")
        memory_manager.append_message(user_id, "assistant", "Antwort 1")
        memory_manager.append_message(user_id, "user", "Nachricht 2")

        # Statistiken prüfen
        stats = memory_manager.get_memory_stats(user_id)
        assert stats["exists"] is True
        assert stats["total_messages"] == 3
        assert stats["file_size_bytes"] > 0

        print("Statistik-Test erfolgreich!")


if __name__ == "__main__":
    test_full_conversation_flow()
    test_reset_conversation()
    test_memory_stats()
    print("\nAlle Integrationstests bestanden!")
