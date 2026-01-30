"""
Unit-Tests für Memory Manager
"""

import os
import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.memory_manager import MemoryManager


@pytest.fixture
def temp_memory_manager():
    """Erstellt einen temporären Memory Manager für Tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MemoryManager(data_dir=tmpdir)
        yield manager


def test_create_user(temp_memory_manager):
    """Testet das Erstellen eines neuen Benutzers."""
    user_id = 12345
    username = "TestUser"

    result = temp_memory_manager.create_user(user_id, username)

    assert result is True
    assert temp_memory_manager.user_exists(user_id) is True

    # Erneutes Erstellen sollte fehlschlagen
    result = temp_memory_manager.create_user(user_id, username)
    assert result is False


def test_append_message(temp_memory_manager):
    """Testet das Hinzufügen von Nachrichten."""
    user_id = 12345

    temp_memory_manager.create_user(user_id)
    temp_memory_manager.append_message(user_id, "user", "Hallo Bot")
    temp_memory_manager.append_message(user_id, "assistant", "Hallo User!")

    context = temp_memory_manager.get_context(user_id)

    assert len(context) == 2
    assert context[0]["role"] == "user"
    assert context[0]["content"] == "Hallo Bot"
    assert context[1]["role"] == "assistant"
    assert context[1]["content"] == "Hallo User!"


def test_get_context_limit(temp_memory_manager):
    """Testet die Begrenzung des Kontexts."""
    user_id = 12345

    temp_memory_manager.create_user(user_id)

    # Füge 20 Nachrichten hinzu
    for i in range(20):
        role = "user" if i % 2 == 0 else "assistant"
        temp_memory_manager.append_message(user_id, role, f"Nachricht {i}")

    # Hole nur die letzten 10
    context = temp_memory_manager.get_context(user_id, max_messages=10)

    assert len(context) == 10
    assert context[0]["content"] == "Nachricht 10"


def test_reset_user(temp_memory_manager):
    """Testet das Zurücksetzen eines Benutzers."""
    user_id = 12345

    temp_memory_manager.create_user(user_id)
    temp_memory_manager.append_message(user_id, "user", "Alte Nachricht")

    # Reset durchführen
    temp_memory_manager.reset_user(user_id)

    # Kontext sollte leer sein
    context = temp_memory_manager.get_context(user_id)

    assert len(context) == 0


def test_memory_stats(temp_memory_manager):
    """Testet die Gedächtnis-Statistiken."""
    user_id = 12345

    stats = temp_memory_manager.get_memory_stats(user_id)
    assert stats["exists"] is False

    temp_memory_manager.create_user(user_id)
    temp_memory_manager.append_message(user_id, "user", "Test")
    temp_memory_manager.append_message(user_id, "assistant", "Antwort")

    stats = temp_memory_manager.get_memory_stats(user_id)
    assert stats["exists"] is True
    assert stats["total_messages"] == 2
    assert stats["file_size_bytes"] > 0


def test_user_without_username(temp_memory_manager):
    """Testet das Erstellen von Benutzern ohne Benutzernamen."""
    user_id = 99999

    result = temp_memory_manager.create_user(user_id)

    assert result is True
    assert temp_memory_manager.user_exists(user_id) is True
