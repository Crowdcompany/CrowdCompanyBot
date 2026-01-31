"""
Task Manager für Crowdbot

Verwaltet Tasks (automatisierte Python-Skripte) für Benutzer:
- Task-Erstellung, -Aktualisierung, -Ausführung
- Script-Versionierung
- Execution History
- Skill-Verwaltung (wiederverwendbare Tasks)
"""

import os
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

from src.file_structure import FileStructureManager

logger = logging.getLogger(__name__)


class TaskManager:
    """Verwaltet Tasks und Skills für Benutzer."""

    def __init__(self, data_dir: str = "/media/xray/NEU/Code/Crowdbot/data"):
        """
        Initialisiert den Task Manager.

        Args:
            data_dir: Basisverzeichnis für Benutzerdaten
        """
        self.data_dir = data_dir
        self.file_manager = FileStructureManager(data_dir)

    def _generate_task_id(self, name: str) -> str:
        """
        Generiert eine eindeutige Task-ID.

        Args:
            name: Task-Name

        Returns:
            Eindeutige ID im Format: task_YYYYMMDD_HHMMSS_HASH
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Hash aus Name + Timestamp für Eindeutigkeit
        hash_input = f"{name}_{timestamp}".encode("utf-8")
        hash_short = hashlib.md5(hash_input).hexdigest()[:6]
        return f"task_{timestamp}_{hash_short}"

    def create_task(
        self,
        user_id: int,
        name: str,
        description: str,
        script: str = "",
        requirements: List[str] = None,
        auto_execute: bool = False
    ) -> str:
        """
        Erstellt eine neue Task.

        Args:
            user_id: Telegram Benutzer-ID
            name: Task-Name
            description: Beschreibung was die Task tun soll
            script: Python-Script (optional, kann später generiert werden)
            requirements: Liste von pip-Paketen (optional)
            auto_execute: Automatisch nach Erstellung ausführen

        Returns:
            Task-ID der erstellten Task
        """
        # Stelle Struktur sicher
        self.file_manager.ensure_v2_structure(user_id)

        # Generiere Task-ID
        task_id = self._generate_task_id(name)

        # Task-Daten
        task_data = {
            "id": task_id,
            "name": name,
            "description": description,
            "script": script,
            "requirements": requirements or [],
            "status": "active",
            "auto_execute": auto_execute,
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
            "version": 1,
            "execution_history": []
        }

        # Speichere Task als Markdown
        task_file = self.file_manager.get_task_active_dir(user_id) / f"{task_id}.md"
        self._write_task_markdown(task_file, task_data)

        logger.info(f"Task erstellt: {task_id} für User {user_id}")
        return task_id

    def get_task(self, user_id: int, task_id: str) -> Optional[Dict]:
        """
        Lädt eine Task.

        Args:
            user_id: Telegram Benutzer-ID
            task_id: Task-ID

        Returns:
            Task-Daten als Dictionary oder None wenn nicht gefunden
        """
        # Suche in allen Status-Ordnern
        for status_dir in ["active", "completed", "archived"]:
            task_file = self.file_manager.get_tasks_dir(user_id) / status_dir / f"{task_id}.md"
            if task_file.exists():
                return self._read_task_markdown(task_file)

        logger.warning(f"Task {task_id} nicht gefunden für User {user_id}")
        return None

    def update_task(
        self,
        user_id: int,
        task_id: str,
        status: Optional[str] = None,
        script: Optional[str] = None,
        output: Optional[str] = None,
        error: Optional[str] = None,
        execution_time: Optional[float] = None
    ) -> bool:
        """
        Aktualisiert eine Task.

        Args:
            user_id: Telegram Benutzer-ID
            task_id: Task-ID
            status: Neuer Status (active, running, completed, failed)
            script: Neues Script (erstellt neue Version)
            output: Execution-Output
            error: Execution-Error
            execution_time: Ausführungsdauer in Sekunden

        Returns:
            True wenn erfolgreich
        """
        task = self.get_task(user_id, task_id)
        if not task:
            logger.error(f"Task {task_id} nicht gefunden für Update")
            return False

        # Update Timestamp
        task["updated"] = datetime.now().isoformat()

        # Update Status
        if status:
            old_status = task["status"]
            task["status"] = status

            # Verschiebe Datei bei Status-Änderung
            if old_status != status and status in ["completed", "archived"]:
                self._move_task_file(user_id, task_id, old_status, status)

        # Update Script (neue Version)
        if script and script != task.get("script", ""):
            task["script"] = script
            task["version"] = task.get("version", 1) + 1

        # Füge Execution History hinzu
        if output is not None or error is not None:
            execution = {
                "timestamp": datetime.now().isoformat(),
                "status": status or task["status"],
                "output": output,
                "error": error,
                "execution_time": execution_time
            }
            task["execution_history"].append(execution)

        # Speichere aktualisierte Task
        task_file = self._get_task_file_path(user_id, task_id, task["status"])
        if task_file:
            self._write_task_markdown(task_file, task)
            logger.info(f"Task {task_id} aktualisiert")
            return True

        return False

    def list_tasks(self, user_id: int, status: str = "active") -> List[Dict]:
        """
        Listet Tasks nach Status auf.

        Args:
            user_id: Telegram Benutzer-ID
            status: Status-Filter (active, completed, archived, all)

        Returns:
            Liste von Task-Daten
        """
        tasks = []

        # Bestimme welche Ordner durchsucht werden
        if status == "all":
            dirs = ["active", "completed", "archived"]
        else:
            dirs = [status]

        for dir_name in dirs:
            task_dir = self.file_manager.get_tasks_dir(user_id) / dir_name
            if not task_dir.exists():
                continue

            for task_file in task_dir.glob("*.md"):
                task_data = self._read_task_markdown(task_file)
                if task_data:
                    tasks.append(task_data)

        # Sortiere nach Erstellungsdatum (neueste zuerst)
        tasks.sort(key=lambda t: t.get("created", ""), reverse=True)
        return tasks

    def delete_task(self, user_id: int, task_id: str) -> bool:
        """
        Archiviert eine Task (verschiebt nach archived/).

        Args:
            user_id: Telegram Benutzer-ID
            task_id: Task-ID

        Returns:
            True wenn erfolgreich
        """
        task = self.get_task(user_id, task_id)
        if not task:
            return False

        current_status = task["status"]
        return self._move_task_file(user_id, task_id, current_status, "archived")

    def save_as_skill(
        self,
        user_id: int,
        task_id: str,
        skill_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Speichert eine Task als wiederverwendbaren Skill.

        Args:
            user_id: Telegram Benutzer-ID
            task_id: Task-ID
            skill_name: Name für den Skill (optional, nutzt Task-Name)

        Returns:
            Pfad zum Skill-File oder None bei Fehler
        """
        task = self.get_task(user_id, task_id)
        if not task:
            logger.error(f"Task {task_id} nicht gefunden")
            return None

        if not task.get("script"):
            logger.error(f"Task {task_id} hat kein Script")
            return None

        # Skill-Name
        if not skill_name:
            skill_name = task["name"]

        # Sanitize Skill-Name
        skill_name = "".join(c if c.isalnum() or c in "_ " else "" for c in skill_name)
        skill_name = skill_name.replace(" ", "_").lower()

        # Skill-Datei
        skills_dir = self.file_manager.get_skills_dir(user_id)
        skill_file = skills_dir / f"{skill_name}.py"

        # Schreibe Skill
        try:
            with open(skill_file, "w", encoding="utf-8") as f:
                # Header
                f.write(f'"""\n')
                f.write(f'Skill: {task["name"]}\n')
                f.write(f'Description: {task["description"]}\n')
                f.write(f'Created from Task: {task_id}\n')
                f.write(f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
                if task["requirements"]:
                    f.write(f'Requirements: {", ".join(task["requirements"])}\n')
                f.write(f'"""\n\n')

                # Script
                f.write(task["script"])

            logger.info(f"Skill gespeichert: {skill_name} für User {user_id}")
            return str(skill_file)

        except Exception as e:
            logger.error(f"Fehler beim Speichern des Skills: {e}")
            return None

    def get_skill(self, user_id: int, skill_name: str) -> Optional[str]:
        """
        Lädt ein Skill-Script.

        Args:
            user_id: Telegram Benutzer-ID
            skill_name: Name des Skills

        Returns:
            Skill-Script oder None
        """
        skills_dir = self.file_manager.get_skills_dir(user_id)
        skill_file = skills_dir / f"{skill_name}.py"

        if not skill_file.exists():
            logger.warning(f"Skill {skill_name} nicht gefunden")
            return None

        try:
            with open(skill_file, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Fehler beim Laden des Skills {skill_name}: {e}")
            return None

    def list_skills(self, user_id: int) -> List[Dict]:
        """
        Listet alle Skills auf.

        Args:
            user_id: Telegram Benutzer-ID

        Returns:
            Liste von Skill-Informationen
        """
        skills = []
        skill_files = self.file_manager.list_skills(user_id)

        for skill_file in skill_files:
            # Nur Python-Dateien
            if not skill_file.name.endswith(".py"):
                continue

            skill_name = skill_file.stem

            try:
                with open(skill_file, "r", encoding="utf-8") as f:
                    content = f.read()

                    # Extrahiere Docstring
                    description = "Keine Beschreibung"
                    if '"""' in content:
                        parts = content.split('"""')
                        if len(parts) >= 3:
                            description = parts[1].strip()

                    skills.append({
                        "name": skill_name,
                        "file": str(skill_file),
                        "description": description
                    })

            except Exception as e:
                logger.error(f"Fehler beim Lesen von Skill {skill_name}: {e}")
                continue

        return skills

    # Hilfsfunktionen

    def _write_task_markdown(self, file_path: Path, task_data: Dict):
        """Schreibt Task-Daten als Markdown."""
        with open(file_path, "w", encoding="utf-8") as f:
            # Header
            f.write(f"# Task: {task_data['name']}\n\n")

            # Metadata
            f.write("## Metadata\n\n")
            f.write(f"- ID: {task_data['id']}\n")
            f.write(f"- Created: {task_data['created']}\n")
            f.write(f"- Updated: {task_data['updated']}\n")
            f.write(f"- Status: {task_data['status']}\n")
            f.write(f"- Version: {task_data.get('version', 1)}\n")
            f.write(f"- Auto-Execute: {'yes' if task_data.get('auto_execute') else 'no'}\n\n")

            # Description
            f.write("## Description\n\n")
            f.write(f"{task_data['description']}\n\n")

            # Requirements
            if task_data.get("requirements"):
                f.write("## Requirements\n\n")
                f.write(", ".join(task_data["requirements"]) + "\n\n")

            # Script
            f.write("## Generated Script\n\n")
            f.write("```python\n")
            f.write(task_data.get("script", "# Kein Script vorhanden\n"))
            f.write("\n```\n\n")

            # Execution History
            f.write("## Execution History\n\n")
            if not task_data.get("execution_history"):
                f.write("*Noch keine Ausführungen*\n\n")
            else:
                for i, execution in enumerate(task_data["execution_history"], 1):
                    f.write(f"### Execution {i} ({execution['timestamp']})\n\n")
                    f.write(f"- Status: {execution['status']}\n")
                    if execution.get("execution_time"):
                        f.write(f"- Duration: {execution['execution_time']:.2f}s\n")

                    if execution.get("output"):
                        f.write("\n**Output:**\n```\n")
                        f.write(execution["output"])
                        f.write("\n```\n\n")

                    if execution.get("error"):
                        f.write("\n**Error:**\n```\n")
                        f.write(execution["error"])
                        f.write("\n```\n\n")

    def _read_task_markdown(self, file_path: Path) -> Optional[Dict]:
        """Liest Task-Daten aus Markdown."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse Markdown (einfaches Parsing)
            lines = content.split("\n")

            task_data = {
                "id": "",
                "name": "",
                "description": "",
                "script": "",
                "requirements": [],
                "status": "active",
                "created": "",
                "updated": "",
                "version": 1,
                "auto_execute": False,
                "execution_history": []
            }

            # Parse Header (# Task: Name)
            for line in lines:
                if line.startswith("# Task:"):
                    task_data["name"] = line.replace("# Task:", "").strip()
                    break

            # Parse Metadata
            in_metadata = False
            for line in lines:
                if line.startswith("## Metadata"):
                    in_metadata = True
                    continue
                elif line.startswith("##"):
                    in_metadata = False

                if in_metadata and line.strip().startswith("-"):
                    key_val = line.strip().lstrip("- ").split(":", 1)
                    if len(key_val) == 2:
                        key, val = key_val
                        key = key.strip().lower()
                        val = val.strip()

                        if key == "id":
                            task_data["id"] = val
                        elif key == "created":
                            task_data["created"] = val
                        elif key == "updated":
                            task_data["updated"] = val
                        elif key == "status":
                            task_data["status"] = val
                        elif key == "version":
                            task_data["version"] = int(val)
                        elif key == "auto-execute":
                            task_data["auto_execute"] = val.lower() == "yes"

            # Parse Description
            desc_lines = []
            in_desc = False
            for line in lines:
                if line.startswith("## Description"):
                    in_desc = True
                    continue
                elif line.startswith("##"):
                    in_desc = False

                if in_desc and line.strip():
                    desc_lines.append(line)

            task_data["description"] = "\n".join(desc_lines).strip()

            # Parse Script
            script_lines = []
            in_script = False
            for line in lines:
                if line.startswith("## Generated Script"):
                    in_script = True
                    continue
                elif line.startswith("##"):
                    in_script = False

                if in_script:
                    if line.strip() == "```python":
                        continue
                    elif line.strip() == "```":
                        break
                    else:
                        script_lines.append(line)

            task_data["script"] = "\n".join(script_lines).strip()

            # Parse Requirements
            req_lines = []
            in_req = False
            for line in lines:
                if line.startswith("## Requirements"):
                    in_req = True
                    continue
                elif line.startswith("##"):
                    in_req = False

                if in_req and line.strip():
                    req_lines.append(line.strip())

            if req_lines:
                # Comma-separated
                task_data["requirements"] = [r.strip() for r in req_lines[0].split(",")]

            return task_data

        except Exception as e:
            logger.error(f"Fehler beim Lesen von Task {file_path}: {e}")
            return None

    def _get_task_file_path(self, user_id: int, task_id: str, status: str) -> Optional[Path]:
        """Gibt den Pfad zur Task-Datei zurück basierend auf Status."""
        if status not in ["active", "completed", "archived"]:
            status = "active"

        task_file = self.file_manager.get_tasks_dir(user_id) / status / f"{task_id}.md"
        return task_file if task_file.exists() else None

    def _move_task_file(
        self,
        user_id: int,
        task_id: str,
        from_status: str,
        to_status: str
    ) -> bool:
        """Verschiebt eine Task-Datei zwischen Status-Ordnern."""
        source = self.file_manager.get_tasks_dir(user_id) / from_status / f"{task_id}.md"
        dest = self.file_manager.get_tasks_dir(user_id) / to_status / f"{task_id}.md"

        if not source.exists():
            logger.error(f"Quelldatei {source} existiert nicht")
            return False

        try:
            # Verschiebe Datei
            import shutil
            shutil.move(str(source), str(dest))
            logger.info(f"Task {task_id} verschoben: {from_status} → {to_status}")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Verschieben von Task {task_id}: {e}")
            return False
