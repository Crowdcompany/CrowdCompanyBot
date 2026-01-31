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
