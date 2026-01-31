# Task Manager System API-Dokumentation

**Erstellt:** 31. Januar 2026
**Status:** Produktiv
**Dateien:** `src/task_manager.py`, `src/skill_manager.py`

## Übersicht

Das Task Manager System ermöglicht es dem Bot, Python-Skripte zu erstellen, zu verwalten und auszuführen.

## TaskManager API

### `create_task(user_id, name, description, script="", requirements=None, auto_execute=False)`

Erstellt eine neue Task.

**Parameter:**
- `user_id` (int): Telegram Benutzer-ID
- `name` (str): **PFLICHT** - Kurzer Task-Name (wird für task_id verwendet)
- `description` (str): **PFLICHT** - Beschreibung was die Task tun soll
- `script` (str): Optional - Python-Script (kann später generiert werden)
- `requirements` (List[str]): Optional - Liste von pip-Paketen
- `auto_execute` (bool): Optional - Automatisch nach Erstellung ausführen

**Rückgabe:** `task_id` (str) - Die generierte Task-ID

**Beispiel:**
```python
task_id = task_manager.create_task(
    user_id=123456,
    name="fibonacci_rechner",
    description="Berechne die Fibonacci-Folge bis 10"
)
```

### `get_task(user_id, task_id)`

Lädt eine Task.

**Rückgabe:** Dict mit Task-Daten oder None

### `list_tasks(user_id, status=None)`

Listet alle Tasks eines Benutzers.

**Parameter:**
- `status` (str): Optional - Filter nach Status ("pending", "running", "completed", "failed")

**Rückgabe:** List[Dict] - Liste von Task-Metadaten

### `run_task(user_id, task_id, llm_client)`

Führt eine Task aus. Wenn kein Script vorhanden, wird das LLM zur Generierung verwendet.

**Parameter:**
- `llm_client`: LLMClient-Instanz für Script-Generierung

**Rückgabe:** `(success: bool, result: str)`

### `update_task(user_id, task_id, status=None, script=None, execution_result=None)`

Aktualisiert eine Task.

### `delete_task(user_id, task_id)`

Löscht (archiviert) eine Task.

**Rückgabe:** `bool` - True wenn erfolgreich

## SkillManager API

### `save_skill(user_id, task_id, skill_name, task_manager)`

Speichert einen erfolgreichen Task als wiederverwendbaren Skill.

**Parameter:**
- `task_id` (str): Die Task-ID des zu speichernden Tasks
- `skill_name` (str): Name für den Skill
- `task_manager`: TaskManager-Instanz zum Laden der Task

**Rückgabe:** `bool` - True wenn erfolgreich

**Wichtig:** Task muss Status "completed" haben!

### `get_skill(user_id, skill_name)`

Lädt einen Skill.

**Rückgabe:** Dict mit Skill-Daten oder None

### `list_skills(user_id)`

Listet alle Skills eines Benutzers.

**Rückgabe:** List[Dict] - Liste von Skill-Metadaten

### `run_skill(user_id, skill_name, args=None)`

Führt einen Skill aus.

**Parameter:**
- `args` (List[str]): Optional - Argumente für das Script

**Rückgabe:** `(success: bool, result: str)`

### `delete_skill(user_id, skill_name)`

Löscht einen Skill.

**Rückgabe:** `bool` - True wenn erfolgreich

## Dateistruktur

```
data/users/{user_id}/important/
├── tasks/
│   ├── active/
│   │   └── {task_id}.json
│   ├── completed/
│   │   └── {task_id}.json
│   ├── archived/
│   │   └── {task_id}.json
│   └── workspace/
│       └── (temporäre Script-Dateien)
└── skills/
    └── {skill_name}.json
```

## Task JSON Format

```json
{
  "task_id": "fibonacci_rechner_abc123",
  "name": "fibonacci_rechner",
  "description": "Berechne die Fibonacci-Folge bis 10",
  "status": "pending|running|completed|failed",
  "created_at": "2026-01-31T11:00:00",
  "updated_at": "2026-01-31T11:05:00",
  "script": "print('Hello World')",
  "requirements": ["numpy", "pandas"],
  "executions": [
    {
      "version": 1,
      "timestamp": "2026-01-31T11:05:00",
      "script": "print('Hello')",
      "output": "Hello\n",
      "error": null,
      "execution_time": 0.02
    }
  ]
}
```

## Skill JSON Format

```json
{
  "name": "fibonacci_rechner",
  "description": "Berechne die Fibonacci-Folge bis 10",
  "created_at": "2026-01-31T11:10:00",
  "source_task_id": "fibonacci_rechner_abc123",
  "current_version": 1,
  "script": "def fib(n):\n    ...",
  "last_execution": {
    "timestamp": "2026-01-31T11:05:00",
    "output": "0 1 1 2 3 5 8\n"
  }
}
```

## Bot-Integration

### `/task` Commands

```
/task create <Beschreibung>  - Erstellt Task (Name wird auto-generiert)
/task list                   - Zeigt alle Tasks
/task show <task_id>         - Zeigt Details
/task run <task_id>          - Führt Task aus
/task delete <task_id>       - Löscht Task
```

**Wichtig:** Im Bot wird der `name` Parameter automatisch aus der Beschreibung generiert:
```python
description = " ".join(context.args[1:])
words = description.split()[:5]
name = "_".join(words).lower()
name = "".join(c for c in name if c.isalnum() or c == "_")
task_id = self.task_manager.create_task(user_id, name, description)
```

### `/skill` Commands

```
/skill save <task_id> <skill_name>  - Speichert Task als Skill
/skill list                         - Zeigt alle Skills
/skill show <skill_name>            - Zeigt Details
/skill run <skill_name> [args]      - Führt Skill aus
/skill delete <skill_name>          - Löscht Skill
```

## LLM Script-Generierung

Wenn `/task run` ausgeführt wird und kein Script vorhanden ist, wird das LLM verwendet:

```python
success, result = self.task_manager.run_task(user_id, task_id, self.llm_client)
```

Der TaskManager sendet dann einen Prompt an das LLM:
```
Generiere ein Python-Script für folgende Aufgabe:
{description}

Das Script soll:
- Vollständig und lauffähig sein
- Keine interaktive Eingabe benötigen
- Ergebnisse per print() ausgeben
- Sicher sein (keine System-Calls, kein Netzwerk)
```

## Sicherheit

- Scripts laufen in isoliertem Workspace-Verzeichnis
- 30 Sekunden Timeout pro Ausführung
- Keine pip-Installation während Laufzeit
- Subprocess mit capture_output=True

## Tests

Implementiert in `tests/test_task_manager.py`:
- 14 Tests für TaskManager
- Alle Tests bestehen
- Coverage: Task-Erstellung, -Update, -Löschung, -Ausführung, Skill-Management

## Fehlerbehebungen

### 31. Januar 2026 - Bot-Integration Fehler

**Problem:** `TypeError: TaskManager.create_task() missing 1 required positional argument: 'description'`

**Ursache:** Bot-Code rief `create_task(user_id, description)` auf, aber API erwartet `create_task(user_id, name, description)`

**Lösung:** Auto-Generierung des `name` Parameters im Bot aus den ersten Wörtern der Beschreibung

**Commit:** siehe git log für Details
