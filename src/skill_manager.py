"""
Skill Manager für Crowdbot

Verwaltet wiederverwendbare Python-Scripts ("Skills") die aus erfolgreichen Tasks erstellt werden.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import subprocess
import sys

logger = logging.getLogger(__name__)


class SkillManager:
    """
    Verwaltet wiederverwendbare Python-Skills.

    Ein Skill ist ein Python-Skript das aus einem erfolgreichen Task erstellt wurde
    und mit Argumenten aufgerufen werden kann.
    """

    def __init__(self, data_dir: str = "./data"):
        """
        Initialisiert den Skill Manager.

        Args:
            data_dir: Basis-Verzeichnis für Benutzerdaten
        """
        self.data_dir = Path(data_dir)

    def _get_skill_dir(self, user_id: int) -> Path:
        """
        Gibt das Skills-Verzeichnis für einen Benutzer zurück.

        Args:
            user_id: Benutzer-ID

        Returns:
            Pfad zum Skills-Verzeichnis
        """
        skill_dir = self.data_dir / "users" / str(user_id) / "important" / "skills"
        skill_dir.mkdir(parents=True, exist_ok=True)
        return skill_dir

    def _get_skill_path(self, user_id: int, skill_name: str) -> Path:
        """
        Gibt den Pfad zur Skill-Datei zurück.

        Args:
            user_id: Benutzer-ID
            skill_name: Name des Skills

        Returns:
            Pfad zur Skill-Datei
        """
        skill_dir = self._get_skill_dir(user_id)
        return skill_dir / f"{skill_name}.json"

    def save_skill(
        self,
        user_id: int,
        task_id: str,
        skill_name: str,
        task_manager
    ) -> bool:
        """
        Speichert einen erfolgreichen Task als wiederverwendbaren Skill.

        Args:
            user_id: Benutzer-ID
            task_id: Task-ID des zu speichernden Tasks
            skill_name: Name für den Skill
            task_manager: TaskManager-Instanz

        Returns:
            True wenn erfolgreich, False sonst
        """
        # Task laden
        task = task_manager.get_task(user_id, task_id)

        if not task:
            logger.error(f"Task {task_id} nicht gefunden")
            return False

        if task["status"] != "completed":
            logger.error(f"Task {task_id} ist nicht completed")
            return False

        # Letztes erfolgreiches Execution holen
        if not task.get("executions"):
            logger.error(f"Task {task_id} hat keine Executions")
            return False

        latest_execution = task["executions"][-1]

        if latest_execution.get("error"):
            logger.error(f"Task {task_id} hat Fehler in letzter Execution")
            return False

        # Skill-Daten erstellen
        skill_data = {
            "name": skill_name,
            "description": task["description"],
            "created_at": datetime.now().isoformat(),
            "source_task_id": task_id,
            "current_version": latest_execution["version"],
            "script": latest_execution["script"],
            "last_execution": {
                "timestamp": latest_execution["timestamp"],
                "output": latest_execution.get("output", "")
            }
        }

        # Skill speichern
        skill_path = self._get_skill_path(user_id, skill_name)

        try:
            with open(skill_path, 'w', encoding='utf-8') as f:
                json.dump(skill_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Skill {skill_name} für User {user_id} gespeichert")
            return True

        except Exception as e:
            logger.error(f"Fehler beim Speichern von Skill {skill_name}: {e}")
            return False

    def get_skill(self, user_id: int, skill_name: str) -> Optional[Dict[str, Any]]:
        """
        Lädt einen Skill.

        Args:
            user_id: Benutzer-ID
            skill_name: Name des Skills

        Returns:
            Skill-Daten oder None
        """
        skill_path = self._get_skill_path(user_id, skill_name)

        if not skill_path.exists():
            return None

        try:
            with open(skill_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Fehler beim Laden von Skill {skill_name}: {e}")
            return None

    def list_skills(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Listet alle Skills eines Benutzers auf.

        Args:
            user_id: Benutzer-ID

        Returns:
            Liste von Skill-Metadaten
        """
        skill_dir = self._get_skill_dir(user_id)
        skills = []

        for skill_file in skill_dir.glob("*.json"):
            try:
                with open(skill_file, 'r', encoding='utf-8') as f:
                    skill_data = json.load(f)
                    skills.append({
                        "name": skill_data["name"],
                        "description": skill_data["description"],
                        "created_at": skill_data["created_at"],
                        "version": skill_data["current_version"]
                    })
            except Exception as e:
                logger.error(f"Fehler beim Laden von {skill_file}: {e}")
                continue

        return sorted(skills, key=lambda x: x["created_at"], reverse=True)

    def run_skill(
        self,
        user_id: int,
        skill_name: str,
        args: Optional[List[str]] = None
    ) -> tuple[bool, str]:
        """
        Führt einen Skill aus.

        Args:
            user_id: Benutzer-ID
            skill_name: Name des Skills
            args: Optionale Argumente für den Skill

        Returns:
            (success, output/error)
        """
        skill = self.get_skill(user_id, skill_name)

        if not skill:
            return False, f"Skill {skill_name} nicht gefunden"

        script = skill["script"]

        # Workspace-Verzeichnis erstellen
        workspace = self.data_dir / "users" / str(user_id) / "important" / "tasks" / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)

        # Script-Datei erstellen
        script_file = workspace / f"{skill_name}_temp.py"

        try:
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(script)

            # Script ausführen mit Argumenten
            cmd = [sys.executable, str(script_file)]
            if args:
                cmd.extend(args)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(workspace)
            )

            # Cleanup
            script_file.unlink()

            if result.returncode == 0:
                output = result.stdout or "Script erfolgreich ausgeführt (keine Ausgabe)"
                logger.info(f"Skill {skill_name} für User {user_id} erfolgreich ausgeführt")
                return True, output
            else:
                error = result.stderr or f"Script fehlgeschlagen mit Exit-Code {result.returncode}"
                logger.error(f"Skill {skill_name} fehlgeschlagen: {error}")
                return False, error

        except subprocess.TimeoutExpired:
            logger.error(f"Skill {skill_name} Timeout")
            return False, "Timeout: Script dauerte länger als 30 Sekunden"
        except Exception as e:
            logger.error(f"Fehler beim Ausführen von Skill {skill_name}: {e}")
            return False, f"Fehler: {str(e)}"
        finally:
            # Cleanup falls noch vorhanden
            if script_file.exists():
                script_file.unlink()

    def delete_skill(self, user_id: int, skill_name: str) -> bool:
        """
        Löscht einen Skill.

        Args:
            user_id: Benutzer-ID
            skill_name: Name des Skills

        Returns:
            True wenn erfolgreich, False sonst
        """
        skill_path = self._get_skill_path(user_id, skill_name)

        if not skill_path.exists():
            return False

        try:
            skill_path.unlink()
            logger.info(f"Skill {skill_name} für User {user_id} gelöscht")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Löschen von Skill {skill_name}: {e}")
            return False

    def update_skill(
        self,
        user_id: int,
        skill_name: str,
        new_script: str
    ) -> bool:
        """
        Aktualisiert das Script eines Skills.

        Args:
            user_id: Benutzer-ID
            skill_name: Name des Skills
            new_script: Neues Python-Script

        Returns:
            True wenn erfolgreich, False sonst
        """
        skill = self.get_skill(user_id, skill_name)

        if not skill:
            return False

        skill["script"] = new_script
        skill["current_version"] += 1
        skill["updated_at"] = datetime.now().isoformat()

        skill_path = self._get_skill_path(user_id, skill_name)

        try:
            with open(skill_path, 'w', encoding='utf-8') as f:
                json.dump(skill, f, indent=2, ensure_ascii=False)

            logger.info(f"Skill {skill_name} für User {user_id} aktualisiert")
            return True

        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren von Skill {skill_name}: {e}")
            return False
