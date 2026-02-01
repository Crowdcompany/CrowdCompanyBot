"""
Tests für den Task Manager
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.task_manager import TaskManager
from src.file_structure import FileStructureManager


@pytest.fixture
def temp_data_dir():
    """Erstellt ein temporäres Datenverzeichnis für Tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def task_manager(temp_data_dir):
    """Erstellt einen TaskManager mit temporärem Datenverzeichnis."""
    return TaskManager(data_dir=temp_data_dir)


def test_task_manager_initialization(task_manager, temp_data_dir):
    """Test: TaskManager wird korrekt initialisiert."""
    assert task_manager.data_dir == temp_data_dir
    assert isinstance(task_manager.file_manager, FileStructureManager)


def test_create_task(task_manager):
    """Test: Task wird erstellt."""
    user_id = 12345

    task_id = task_manager.create_task(
        user_id=user_id,
        name="Test Task",
        description="Eine Test-Task",
        script="print('Hello World')",
        requirements=["requests"],
        auto_execute=False
    )

    # Prüfe dass Task-ID generiert wurde (Snake-Case Format)
    assert task_id == "test_task"
    assert "_" in task_id or task_id.islower()

    # Prüfe dass Task-Datei existiert
    task_file = task_manager.file_manager.get_task_active_dir(user_id) / f"{task_id}.md"
    assert task_file.exists()


def test_get_task(task_manager):
    """Test: Task wird geladen."""
    user_id = 12345

    # Erstelle Task
    task_id = task_manager.create_task(
        user_id=user_id,
        name="Get Task Test",
        description="Test zum Laden",
        script="x = 1 + 1",
        requirements=["numpy"]
    )

    # Lade Task
    task = task_manager.get_task(user_id, task_id)

    assert task is not None
    assert task["id"] == task_id
    assert task["name"] == "Get Task Test"
    assert task["description"] == "Test zum Laden"
    assert "x = 1 + 1" in task["script"]
    assert task["status"] == "active"
    assert task["version"] == 1


def test_update_task_script(task_manager):
    """Test: Task-Script wird aktualisiert."""
    user_id = 12345

    # Erstelle Task
    task_id = task_manager.create_task(
        user_id=user_id,
        name="Update Test",
        description="Test zum Aktualisieren",
        script="print('v1')"
    )

    # Update Script
    success = task_manager.update_task(
        user_id=user_id,
        task_id=task_id,
        script="print('v2')"
    )

    assert success is True

    # Lade aktualisierte Task
    task = task_manager.get_task(user_id, task_id)
    assert "print('v2')" in task["script"]
    assert task["version"] == 2


def test_update_task_status(task_manager):
    """Test: Task-Status wird aktualisiert."""
    user_id = 12345

    # Erstelle Task
    task_id = task_manager.create_task(
        user_id=user_id,
        name="Status Test",
        description="Test für Status-Änderung"
    )

    # Update Status zu completed
    success = task_manager.update_task(
        user_id=user_id,
        task_id=task_id,
        status="completed"
    )

    assert success is True

    # Prüfe dass Datei verschoben wurde
    active_file = task_manager.file_manager.get_task_active_dir(user_id) / f"{task_id}.md"
    completed_file = task_manager.file_manager.get_task_completed_dir(user_id) / f"{task_id}.md"

    assert not active_file.exists()
    assert completed_file.exists()


def test_add_execution_history(task_manager):
    """Test: Execution History wird in Markdown geschrieben."""
    user_id = 12345

    # Erstelle Task
    task_id = task_manager.create_task(
        user_id=user_id,
        name="Execution Test",
        description="Test für Execution History"
    )

    # Füge Execution hinzu
    success = task_manager.update_task(
        user_id=user_id,
        task_id=task_id,
        output="Success!",
        error=None,
        execution_time=1.23
    )

    assert success is True

    # Prüfe dass die Datei erfolgreich aktualisiert wurde
    task_file = task_manager.file_manager.get_task_active_dir(user_id) / f"{task_id}.md"
    assert task_file.exists()

    # Prüfe dass Execution-Info im Markdown steht
    with open(task_file, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Success!" in content
    assert "1.23s" in content


def test_list_tasks(task_manager):
    """Test: Tasks werden gelistet."""
    user_id = 12345

    # Erstelle mehrere Tasks
    task_id1 = task_manager.create_task(user_id, "Task 1", "Erste Task")
    task_id2 = task_manager.create_task(user_id, "Task 2", "Zweite Task")
    task_id3 = task_manager.create_task(user_id, "Task 3", "Dritte Task")

    # Markiere eine als completed
    task_manager.update_task(user_id, task_id2, status="completed")

    # Liste aktive Tasks
    active_tasks = task_manager.list_tasks(user_id, status="active")
    assert len(active_tasks) == 2

    # Liste completed Tasks
    completed_tasks = task_manager.list_tasks(user_id, status="completed")
    assert len(completed_tasks) == 1

    # Liste alle Tasks
    all_tasks = task_manager.list_tasks(user_id, status="all")
    assert len(all_tasks) == 3


def test_delete_task(task_manager):
    """Test: Task wird archiviert."""
    user_id = 12345

    # Erstelle Task
    task_id = task_manager.create_task(
        user_id=user_id,
        name="Delete Test",
        description="Test zum Löschen"
    )

    # Archiviere Task
    success = task_manager.delete_task(user_id, task_id)
    assert success is True

    # Prüfe dass Datei verschoben wurde
    archived_file = task_manager.file_manager.get_task_archived_dir(user_id) / f"{task_id}.md"
    assert archived_file.exists()


def test_save_as_skill(task_manager):
    """Test: Task wird als Skill gespeichert."""
    user_id = 12345

    # Erstelle Task mit Script
    task_id = task_manager.create_task(
        user_id=user_id,
        name="Skill Test",
        description="Test zum Skill-Speichern",
        script="def hello():\n    print('Hello')",
        requirements=["requests"]
    )

    # Speichere als Skill
    skill_path = task_manager.save_as_skill(
        user_id=user_id,
        task_id=task_id,
        skill_name="hello_skill"
    )

    assert skill_path is not None
    assert Path(skill_path).exists()
    assert "hello_skill.py" in skill_path


def test_get_skill(task_manager):
    """Test: Skill wird geladen."""
    user_id = 12345

    # Erstelle Task und speichere als Skill
    task_id = task_manager.create_task(
        user_id=user_id,
        name="Get Skill Test",
        description="Test",
        script="def test():\n    return 42"
    )

    task_manager.save_as_skill(user_id, task_id, "test_skill")

    # Lade Skill
    skill_script = task_manager.get_skill(user_id, "test_skill")

    assert skill_script is not None
    assert "def test():" in skill_script
    assert "return 42" in skill_script


def test_list_skills(task_manager):
    """Test: Skills werden gelistet."""
    user_id = 12345

    # Erstelle mehrere Skills
    for i in range(3):
        task_id = task_manager.create_task(
            user_id=user_id,
            name=f"Skill {i}",
            description=f"Test Skill {i}",
            script=f"def func{i}(): pass"
        )
        task_manager.save_as_skill(user_id, task_id, f"skill_{i}")

    # Liste Skills
    skills = task_manager.list_skills(user_id)

    assert len(skills) == 3
    assert all("skill_" in skill["name"] for skill in skills)


def test_task_not_found(task_manager):
    """Test: Nicht existierende Task gibt None zurück."""
    user_id = 12345

    task = task_manager.get_task(user_id, "nonexistent_task_id")
    assert task is None


def test_skill_not_found(task_manager):
    """Test: Nicht existierender Skill gibt None zurück."""
    user_id = 12345

    skill = task_manager.get_skill(user_id, "nonexistent_skill")
    assert skill is None


def test_save_task_without_script_fails(task_manager):
    """Test: Task ohne Script kann nicht als Skill gespeichert werden."""
    user_id = 12345

    # Erstelle Task ohne Script
    task_id = task_manager.create_task(
        user_id=user_id,
        name="No Script",
        description="Task ohne Script"
    )

    # Versuche als Skill zu speichern
    skill_path = task_manager.save_as_skill(user_id, task_id)
    assert skill_path is None


def test_create_task_with_metadata(task_manager):
    """Test: Task mit Metadaten wird korrekt erstellt."""
    user_id = 12345

    metadata = {
        "tags": ["mathematik", "addition", "berechnung"],
        "category": "datenverarbeitung",
        "input_schema": {"numbers": "List[int]"},
        "output_schema": {"sum": "int"},
        "use_cases": [
            "Addiere beliebig viele Zahlen",
            "Berechne Gesamtsummen aus Listen"
        ]
    }

    task_id = task_manager.create_task(
        user_id=user_id,
        name="Addiere drei Zahlen",
        description="Addiert drei gegebene Zahlen",
        metadata=metadata
    )

    # Lade Task
    task = task_manager.get_task(user_id, task_id)

    assert task is not None
    assert task["id"] == "addiere_drei_zahlen"
    assert task["metadata"]["category"] == "datenverarbeitung"
    assert "mathematik" in task["metadata"]["tags"]
    assert "addition" in task["metadata"]["tags"]
    assert task["metadata"]["input_schema"]["numbers"] == "List[int]"
    assert task["metadata"]["output_schema"]["sum"] == "int"
    assert len(task["metadata"]["use_cases"]) == 2


def test_snake_case_conversion(task_manager):
    """Test: Task-Namen werden korrekt zu Snake-Case konvertiert."""
    user_id = 12345

    # Test mit Umlauten
    task_id1 = task_manager.create_task(
        user_id=user_id,
        name="Zähle Äpfel und Birnen",
        description="Test"
    )
    assert task_id1 == "zaehle_aepfel_und_birnen"

    # Test mit Sonderzeichen
    task_id2 = task_manager.create_task(
        user_id=user_id,
        name="Berechne x+y=z",
        description="Test"
    )
    assert task_id2 == "berechne_x_y_z"

    # Test mit mehrfachen Leerzeichen
    task_id3 = task_manager.create_task(
        user_id=user_id,
        name="Test   mit    Leerzeichen",
        description="Test"
    )
    assert task_id3 == "test_mit_leerzeichen"


def test_duplicate_task_names(task_manager):
    """Test: Doppelte Task-Namen erhalten Versions-Suffix."""
    user_id = 12345

    # Erstelle erste Task
    task_id1 = task_manager.create_task(
        user_id=user_id,
        name="Duplikat Test",
        description="Erste Task"
    )
    assert task_id1 == "duplikat_test"

    # Erstelle zweite Task mit gleichem Namen
    task_id2 = task_manager.create_task(
        user_id=user_id,
        name="Duplikat Test",
        description="Zweite Task"
    )
    assert task_id2 == "duplikat_test_v2"

    # Erstelle dritte Task mit gleichem Namen
    task_id3 = task_manager.create_task(
        user_id=user_id,
        name="Duplikat Test",
        description="Dritte Task"
    )
    assert task_id3 == "duplikat_test_v3"


def test_validate_execution_output_valid(task_manager):
    """Test: Validierung erkennt korrekte Ausgabe."""
    from unittest.mock import MagicMock

    # Mock LLM Client
    mock_llm = MagicMock()
    mock_llm.chat.return_value = "VALID: Ausgabe zeigt korrekt den Titel der Webseite"

    result = task_manager._validate_execution_output(
        llm_client=mock_llm,
        task_description="Webseite laden und Titel anzeigen",
        script_output="Crowdcompany UG | Multi-Cloud AI Solutions",
        task_id="test_task"
    )

    assert result["is_valid"] is True
    assert "korrekt" in result["reason"].lower()


def test_validate_execution_output_invalid(task_manager):
    """Test: Validierung erkennt fehlerhafte Ausgabe."""
    from unittest.mock import MagicMock

    # Mock LLM Client
    mock_llm = MagicMock()
    mock_llm.chat.return_value = "INVALID: Ausgabe ist leer oder enthält nur Fehlermeldung"

    result = task_manager._validate_execution_output(
        llm_client=mock_llm,
        task_description="Berechne Fibonacci von 10",
        script_output="Fehler beim Laden der URL: Forbidden",
        task_id="test_task"
    )

    assert result["is_valid"] is False
    assert "Fehler" in result["reason"] or "ungültig" in result["reason"].lower()


def test_validate_execution_output_llm_error(task_manager):
    """Test: Bei LLM-Fehler wird Success angenommen."""
    from unittest.mock import MagicMock

    # Mock LLM Client wirft Exception
    mock_llm = MagicMock()
    mock_llm.chat.side_effect = Exception("LLM Connection failed")

    result = task_manager._validate_execution_output(
        llm_client=mock_llm,
        task_description="Test Task",
        script_output="Irgendeine Ausgabe",
        task_id="test_task"
    )

    # Bei Fehler soll Success angenommen werden (defensiv)
    assert result["is_valid"] is True
    assert "assume success" in result["reason"].lower()


def test_run_task_with_validation(task_manager):
    """Test: Task-Ausführung mit Selbstüberprüfung."""
    from unittest.mock import MagicMock

    user_id = 12345

    # Erstelle Task mit funktionierendem Script
    task_id = task_manager.create_task(
        user_id=user_id,
        name="Validation Test",
        description="Berechne 5 + 3",
        script="import sys; print(8)"
    )

    # Mock LLM Client für Validierung
    mock_llm = MagicMock()
    mock_llm.chat.return_value = "VALID: Ergebnis ist korrekt"

    # Führe Task aus
    success, output = task_manager.run_task(
        user_id=user_id,
        task_id=task_id,
        llm_client=mock_llm
    )

    assert success is True
    assert output == "8"

    # Prüfe ob Validierung aufgerufen wurde
    mock_llm.chat.assert_called()
    # Der zweite Aufruf sollte die Validierung sein
    assert mock_llm.chat.call_count >= 1


def test_improved_script_generation_with_user_agent(task_manager):
    """Test: Verbesserter Prompt generiert Scripts mit User-Agent."""
    from unittest.mock import MagicMock

    user_id = 12345

    # Erstelle Task ohne Script (während Ausführung generiert)
    task_id = task_manager.create_task(
        user_id=user_id,
        name="Web Scraping Test",
        description="Lade den Inhalt von https://example.com"
    )

    # Mock LLM Client - gibt verbessertes Script zurück
    mock_llm = MagicMock()

    # Erste Antwort: Script-Generierung
    improved_script = """import sys
import urllib.request
import urllib.error

if len(sys.argv) < 2:
    print("Fehler: Keine URL")
    sys.exit(1)

url = sys.argv[1]

try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as response:
        content = response.read().decode('utf-8')
    print(content[:200])
except urllib.error.URLError as e:
    print(f"Fehler: {e.reason}")
    sys.exit(1)"""

    # Developer-Antworten (Script-Generierung)
    improved_script = """import sys
import urllib.request
import urllib.error

if len(sys.argv) < 2:
    print("Fehler: Keine URL")
    sys.exit(1)

url = sys.argv[1]

try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as response:
        content = response.read().decode('utf-8')
    print(content[:200])
except urllib.error.URLError as e:
    print(f"Fehler: {e.reason}")
    sys.exit(1)"""

    # Critic-Antwort: APPROVED (erster Versuch)
    critic_response = "APPROVED: Script ist bereit für Produktion"

    # Validierungs-Antwort
    validation_response = "VALID: Webseite erfolgreich geladen"

    # Simuliere drei Aufrufe: Developer + Critic + Validierung
    mock_llm.chat.side_effect = [improved_script, critic_response, validation_response]

    # Führe Task aus mit Parameter
    success, output = task_manager.run_task(
        user_id=user_id,
        task_id=task_id,
        llm_client=mock_llm,
        user_input="https://example.com"
    )

    # Prüfe ob LLM dreimal aufgerufen wurde (Developer + Critic + Validierung)
    assert mock_llm.chat.call_count == 3

    # Prüfe den ERSTEN Aufruf (Developer - Script-Generierung)
    first_call_args = mock_llm.chat.call_args_list[0]
    prompt = first_call_args[1]['user_message']  # keyword argument

    # Prüfe ob Prompt Developer-Rolle enthält
    assert "Senior Python Developer" in prompt

    # Prüfe den ZWEITEN Aufruf (Critic - Prüfung)
    second_call_args = mock_llm.chat.call_args_list[1]
    critic_prompt = second_call_args[1]['user_message']

    # Prüfe ob Prompt Critic-Rolle enthält
    assert "Code Reviewer" in critic_prompt or "Prüfe das Python-Script" in critic_prompt

