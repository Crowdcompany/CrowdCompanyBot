"""
Tests für Memory 2.0 System

Testet die Kernfunktionalität des hierarchischen Memory-Systems:
- FileStructureManager
- MemoryManagerV2
- ImportanceScorer
- Summarizer
- CleanupService
- ContextLoader
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from src.file_structure import FileStructureManager
from src.memory_manager_v2 import MemoryManagerV2
from src.importance_scorer import ImportanceScorer
from src.summarizer import Summarizer


# Mock LLM Client für Tests
class MockLLMClient:
    """Mock LLM Client der vordefinierte Antworten zurückgibt."""

    def send_message(self, prompt, max_tokens=1000, temperature=0.7):
        """Simuliert LLM-Antwort basierend auf Prompt."""

        # Importance Scoring Mock
        if "Analysiere die folgende Konversation und bewerte" in prompt:
            return '''```json
{
  "score": 5,
  "frequency_points": 1,
  "recency_points": 2,
  "explicit_points": 0,
  "relevance_points": 2,
  "reasoning": "Mock-Bewertung für Tests",
  "retention_recommendation": "Behalten in Wochen-/Monatszusammenfassungen"
}
```'''

        # Soft Trim Mock
        if "kürze unwichtige Details" in prompt.lower():
            return "### Benutzer - 2026-01-30\\n\\nGekürzte Testfrage\\n\\n### Crowdbot - 2026-01-30\\n\\nGekürzte Testantwort"

        # Weekly Summary Mock
        if "Wochenzusammenfassung" in prompt:
            return "Hauptthemen: Testing. Wichtige Erkenntnisse: Memory V2 funktioniert."

        # Monthly Summary Mock
        if "Monatszusammenfassung" in prompt:
            return "Überblick: Ein erfolgreicher Testmonat. Schlüsselthemen: Testing."

        # File Selection Mock
        if "bestimme welche historischen Memory-Dateien relevant" in prompt:
            return "[]"

        return "Mock LLM Antwort"


@pytest.fixture
def temp_data_dir():
    """Erstellt temporäres Datenverzeichnis für Tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def file_structure(temp_data_dir):
    """FileStructureManager Fixture."""
    return FileStructureManager(temp_data_dir)


@pytest.fixture
def memory_manager(temp_data_dir):
    """MemoryManagerV2 Fixture."""
    return MemoryManagerV2(temp_data_dir)


@pytest.fixture
def mock_llm():
    """Mock LLM Client Fixture."""
    return MockLLMClient()


@pytest.fixture
def importance_scorer(mock_llm):
    """ImportanceScorer Fixture mit Mock LLM."""
    return ImportanceScorer(mock_llm)


@pytest.fixture
def summarizer(mock_llm, importance_scorer):
    """Summarizer Fixture mit Mock LLM."""
    return Summarizer(mock_llm, importance_scorer)


# Tests für FileStructureManager

def test_file_structure_creation(file_structure):
    """Test: V2 Ordnerstruktur wird korrekt erstellt."""
    user_id = 12345

    result = file_structure.ensure_v2_structure(user_id)

    assert result is True
    assert file_structure.is_v2_structure(user_id) is True

    # Prüfe ob alle Ordner existieren
    user_dir = file_structure.get_user_dir(user_id)
    assert (user_dir / "daily").exists()
    assert (user_dir / "weekly").exists()
    assert (user_dir / "monthly").exists()
    assert (user_dir / "archive" / "daily").exists()
    assert (user_dir / "important").exists()


def test_daily_file_paths(file_structure):
    """Test: Tagesdatei-Pfade werden korrekt generiert."""
    user_id = 12345
    date = datetime(2026, 1, 30)

    path = file_structure.get_daily_file_path(user_id, date)

    assert path.name == "20260130.md"
    assert "daily" in str(path)


def test_archive_and_compress(file_structure, temp_data_dir):
    """Test: Dateien können archiviert und komprimiert werden."""
    user_id = 12345
    file_structure.ensure_v2_structure(user_id)

    # Erstelle Test-Datei
    daily_path = file_structure.get_daily_file_path(user_id)
    daily_path.write_text("Test content", encoding="utf-8")

    # Archiviere
    archived = file_structure.archive_file(daily_path, user_id, "daily")
    assert archived is not None
    assert archived.exists()
    assert not daily_path.exists()  # Original sollte verschoben sein

    # Komprimiere
    compressed = file_structure.compress_file(archived)
    assert compressed is not None
    assert str(compressed).endswith(".gz")
    assert not archived.exists()  # Original sollte nach Kompression gelöscht sein


# Tests für MemoryManagerV2

def test_create_user_v2(memory_manager):
    """Test: User wird mit V2 Struktur erstellt."""
    user_id = 12345

    result = memory_manager.create_user(user_id, "TestUser")

    assert result is True
    assert memory_manager.user_exists(user_id) is True

    # Prüfe ob memory.md existiert
    memory_path = memory_manager.file_structure.get_memory_index_path(user_id)
    assert memory_path.exists()

    content = memory_path.read_text(encoding="utf-8")
    assert "TestUser" in content
    assert "Langzeitgedächtnis" in content


def test_append_message_v2(memory_manager):
    """Test: Nachrichten werden in Tagesdateien gespeichert."""
    user_id = 12345
    memory_manager.create_user(user_id)

    result = memory_manager.append_message(user_id, "user", "Testnachricht")

    assert result is True

    # Prüfe ob Nachricht in heutiger Tagesdatei ist
    daily_path = memory_manager.file_structure.get_daily_file_path(user_id)
    assert daily_path.exists()

    content = daily_path.read_text(encoding="utf-8")
    assert "Testnachricht" in content
    assert "Benutzer" in content


def test_get_context_v2(memory_manager):
    """Test: Kontext wird aus Tagesdateien geladen."""
    user_id = 12345
    memory_manager.create_user(user_id)

    # Füge mehrere Nachrichten hinzu
    memory_manager.append_message(user_id, "user", "Frage 1")
    memory_manager.append_message(user_id, "assistant", "Antwort 1")
    memory_manager.append_message(user_id, "user", "Frage 2")

    messages = memory_manager.get_context(user_id, max_messages=10)

    assert len(messages) == 3
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Frage 1"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"


def test_migration_v1_to_v2(memory_manager, temp_data_dir):
    """Test: V1 Memory wird korrekt zu V2 migriert."""
    from src.memory_manager import MemoryManager

    user_id = 12345

    # Erstelle V1 Memory
    v1_manager = MemoryManager(temp_data_dir)
    v1_manager.create_user(user_id, "MigrationTest")
    v1_manager.append_message(user_id, "user", "V1 Nachricht")
    v1_manager.append_message(user_id, "assistant", "V1 Antwort")

    # Migriere zu V2
    result = memory_manager.migrate_from_v1(user_id)

    assert result is True
    assert memory_manager.file_structure.is_v2_structure(user_id)

    # Prüfe ob Backup existiert
    user_dir = memory_manager.file_structure.get_user_dir(user_id)
    backup_path = user_dir / "memory_v1_backup.md"
    assert backup_path.exists()


# Tests für ImportanceScorer

def test_importance_scoring(importance_scorer):
    """Test: LLM-basierte Wichtigkeitsbewertung."""
    snippet = "Ich möchte dieses Jahr AWS Zertifizierungen machen."
    context = {
        "frequency_count": 3,
        "timestamp": "2026-01-30 15:00:00",
        "days_since_first_mention": 5
    }

    score_data = importance_scorer.score_conversation(snippet, context)

    assert "score" in score_data
    assert 0 <= score_data["score"] <= 10
    assert "reasoning" in score_data
    assert "retention_recommendation" in score_data


def test_temporary_fact_detection(importance_scorer):
    """Test: Temporäre Fakten werden erkannt."""
    snippet = "Was läuft heute im TV-Programm um 20:15?"

    score_data = importance_scorer.score_conversation(snippet)

    assert score_data["score"] == 0
    assert "temporär" in score_data["reasoning"].lower()


def test_explicit_markers(importance_scorer):
    """Test: Explizite Wichtigkeits-Marker werden erkannt."""
    text = "Merke dir das: Ich mag keinen Fußball. Das ist wichtig!"

    points = importance_scorer.detect_explicit_markers(text)

    assert points >= 1  # Mindestens ein Marker gefunden


# Tests für Summarizer

def test_soft_trim(summarizer, file_structure, temp_data_dir):
    """Test: Soft Trim kürzt unwichtige Details."""
    user_id = 12345
    file_structure.ensure_v2_structure(user_id)

    # Erstelle Tagesdatei mit langem Inhalt
    daily_path = file_structure.get_daily_file_path(user_id)
    long_content = """# Tagesdatei

### Benutzer - 2026-01-30 15:00:00

Was läuft heute im TV?

---

### Crowdbot - 2026-01-30 15:00:05

""" + ("Sehr lange TV-Programm-Details " * 100)  # Langer Text

    daily_path.write_text(long_content, encoding="utf-8")
    original_size = len(long_content)

    # Soft Trim anwenden
    result = summarizer.soft_trim_daily_file(daily_path)

    assert result is True

    # Prüfe ob Datei kleiner wurde
    trimmed_content = daily_path.read_text(encoding="utf-8")
    assert len(trimmed_content) < original_size


def test_weekly_summary_creation(summarizer, file_structure, temp_data_dir):
    """Test: Wochenzusammenfassung wird erstellt."""
    user_id = 12345
    file_structure.ensure_v2_structure(user_id)

    # Erstelle Test-Tagesdateien
    daily_files = []
    for i in range(7):
        date = datetime.now() - timedelta(days=i)
        daily_path = file_structure.get_daily_file_path(user_id, date)
        daily_path.write_text(f"# Tagesdatei {date.date()}\n\nTest Inhalt Tag {i}", encoding="utf-8")
        daily_files.append(daily_path)

    # Erstelle Summary
    output_path = file_structure.get_weekly_file_path(user_id, 2026, 5)
    result = summarizer.create_weekly_summary(daily_files, output_path, 5, 2026)

    assert result is True
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")
    assert "Wochenzusammenfassung" in content
    assert "KW 5" in content


# Tests für Integration

def test_complete_memory_lifecycle(memory_manager, summarizer, file_structure):
    """Test: Vollständiger Memory-Lifecycle von Erstellung bis Archivierung."""
    user_id = 99999

    # 1. User erstellen
    memory_manager.create_user(user_id, "LifecycleTest")

    # 2. Nachrichten hinzufügen
    for i in range(10):
        memory_manager.append_message(user_id, "user", f"Frage {i}")
        memory_manager.append_message(user_id, "assistant", f"Antwort {i}")

    # 3. Kontext laden
    messages = memory_manager.get_context(user_id, max_messages=20)
    assert len(messages) == 20

    # 4. Statistiken abrufen
    stats = memory_manager.get_memory_stats(user_id)
    assert stats["exists"] is True
    assert stats["daily_files"] >= 1
    assert stats["total_messages"] == 20

    # 5. Soft Trim auf Tagesdatei anwenden
    daily_path = file_structure.get_daily_file_path(user_id)
    summarizer.soft_trim_daily_file(daily_path)

    # Prüfe ob Datei noch existiert und lesbar ist
    assert daily_path.exists()
    content = daily_path.read_text(encoding="utf-8")
    assert len(content) > 0


def test_memory_stats(memory_manager):
    """Test: Memory-Statistiken werden korrekt berechnet."""
    user_id = 54321

    # User ohne Memory
    stats = memory_manager.get_memory_stats(user_id)
    assert stats["exists"] is False

    # User mit Memory
    memory_manager.create_user(user_id)
    memory_manager.append_message(user_id, "user", "Test")

    stats = memory_manager.get_memory_stats(user_id)
    assert stats["exists"] is True
    assert stats["daily_files"] >= 1
    assert stats["total_messages"] >= 1
    assert "total_size_mb" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
