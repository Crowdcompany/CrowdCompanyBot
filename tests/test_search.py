"""
Unit-Tests für Search Module
"""

import os
import pytest
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.search_module import SearchModule


@pytest.fixture
def search_module():
    """Erstellt ein Search Module."""
    return SearchModule()


def test_is_url(search_module):
    """Testet die URL-Erkennung."""
    assert search_module.is_url("https://example.com") is True
    assert search_module.is_url("http://test.de") is True
    assert search_module.is_url("www.example.com") is False
    assert search_module.is_url("Hallo Welt") is False
    assert search_module.is_url("") is False


def test_is_url_with_www(search_module):
    """Testet URLs mit und ohne www."""
    assert search_module.is_url("https://www.example.com") is True
    assert search_module.is_url("http://www.test.de/path") is True


@patch("src.search_module.requests.get")
def test_fetch_url_success(mock_get, search_module):
    """Testet erfolgreiches URL-Fetch."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "Example Domain\n===========\nTest content"
    mock_get.return_value = mock_response

    result = search_module.fetch_url("https://example.com")

    assert result == "Example Domain\n===========\nTest content"
    mock_get.assert_called_once()


@patch("src.search_module.requests.get")
def test_fetch_url_error(mock_get, search_module):
    """Testet Fehlerbehandlung beim URL-Fetch."""
    mock_get.side_effect = Exception("Connection error")

    result = search_module.fetch_url("https://example.com")

    assert "Fehler:" in result


@patch("src.search_module.requests.post")
def test_deep_search_success(mock_post, search_module):
    """Testet erfolgreiche Deep Research."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Hier ist das Suchergebnis..."
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    result = search_module.deep_search("Was ist Python?")

    assert result == "Hier ist das Suchergebnis..."
    mock_post.assert_called_once()


@patch("src.search_module.requests.post")
def test_deep_search_error(mock_post, search_module):
    """Testet Fehlerbehandlung bei Deep Research."""
    mock_post.side_effect = Exception("Connection error")

    result = search_module.deep_search("Test")

    assert "Fehler:" in result


def test_search_with_url(search_module):
    """Testet Suche mit URL (nutzt Fetch)."""
    with patch.object(search_module, 'fetch_url', return_value="URL Content"):
        result = search_module.search("https://example.com")
        assert result == "URL Content"


def test_search_with_query(search_module):
    """Testet Suche mit Query (nutzt Deep Research)."""
    with patch.object(search_module, 'deep_search', return_value="Search Result"):
        result = search_module.search("Was ist Python?")
        assert result == "Search Result"


def test_default_values(search_module):
    """Testet Default-Werte."""
    assert search_module.jina_reader_url == "https://r.jina.ai"
    assert search_module.jina_proxy_url == "https://jinaproxy.ccpn.cc"
