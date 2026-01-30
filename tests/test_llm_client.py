"""
Unit-Tests für LLM Client (GLM-4.7 via Proxy)
"""

import os
import pytest
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.llm_client import LLMClient


@pytest.fixture
def llm_client():
    """Erstellt einen LLM Client."""
    return LLMClient()


def test_build_messages_without_history(llm_client):
    """Testet das Bauen von Nachrichten ohne Historie."""
    messages = llm_client._build_messages("Hallo")

    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hallo"


def test_build_messages_with_history(llm_client):
    """Testet das Bauen von Nachrichten mit Historie."""
    history = [
        {"role": "user", "content": "Wie geht es dir?"},
        {"role": "assistant", "content": "Mir geht es gut!"}
    ]

    messages = llm_client._build_messages("Und dir?", history)

    assert len(messages) == 3
    assert messages[0]["content"] == "Wie geht es dir?"
    assert messages[1]["content"] == "Mir geht es gut!"
    assert messages[2]["content"] == "Und dir?"


@patch("src.llm_client.requests.post")
def test_chat_success(mock_post, llm_client):
    """Testet erfolgreichen Chat."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "content": [
            {"type": "text", "text": "Hallo! Wie kann ich helfen?"}
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    result = llm_client.chat("Hallo")

    assert result == "Hallo! Wie kann ich helfen?"
    mock_post.assert_called_once()


@patch("src.llm_client.requests.post")
def test_chat_error(mock_post, llm_client):
    """Testet Fehlerbehandlung."""
    mock_post.side_effect = Exception("Connection error")

    result = llm_client.chat("Hallo")

    assert result is None


def test_system_prompt_content(llm_client):
    """Testet, dass der System-Prompt korrekte Inhalte hat."""
    prompt = llm_client.system_prompt

    assert "Crowdbot" in prompt
    assert "hilfreich" in prompt
    assert "freundlich" in prompt
    assert "Deutsch" in prompt


def test_default_values(llm_client):
    """Testet Default-Werte."""
    assert llm_client.proxy_url == "https://glmproxy.ccpn.cc/v1/messages"
    assert llm_client.model_name == "glm-4.7"
