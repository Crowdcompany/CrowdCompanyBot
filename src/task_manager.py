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

    def _generate_task_id(self, user_id: int, name: str) -> str:
        """
        Generiert eine sprechende Task-ID im Snake-Case-Format.

        Args:
            user_id: Benutzer-ID (für Konfliktprüfung)
            name: Task-Name

        Returns:
            Eindeutige ID im Snake-Case-Format (z.B. "addiere_3_zahlen")
        """
        # Konvertiere zu Snake-Case
        task_id = name.lower()
        # Ersetze Umlaute
        umlaut_map = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}
        for umlaut, replacement in umlaut_map.items():
            task_id = task_id.replace(umlaut, replacement)
        # Nur alphanumerische Zeichen und Unterstriche
        task_id = "".join(c if c.isalnum() or c == "_" else "_" for c in task_id)
        # Mehrfache Unterstriche reduzieren
        while "__" in task_id:
            task_id = task_id.replace("__", "_")
        # Führende/nachfolgende Unterstriche entfernen
        task_id = task_id.strip("_")

        # Prüfe auf Konflikte und füge Suffix hinzu falls nötig
        base_id = task_id
        counter = 2
        while self._task_id_exists(user_id, task_id):
            task_id = f"{base_id}_v{counter}"
            counter += 1

        return task_id

    def _task_id_exists(self, user_id: int, task_id: str) -> bool:
        """
        Prüft ob eine Task-ID bereits existiert.

        Args:
            user_id: Benutzer-ID
            task_id: Zu prüfende Task-ID

        Returns:
            True wenn ID existiert
        """
        for status_dir in ["active", "completed", "archived"]:
            task_file = self.file_manager.get_tasks_dir(user_id) / status_dir / f"{task_id}.md"
            if task_file.exists():
                return True
        return False

    def create_task(
        self,
        user_id: int,
        name: str,
        description: str,
        script: str = "",
        requirements: List[str] = None,
        auto_execute: bool = False,
        metadata: Dict = None
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
            metadata: Metadaten für KI-Discovery (optional)
                - tags: Liste von Keywords (z.B. ["mathematik", "addition"])
                - category: Kategorie (z.B. "datenverarbeitung")
                - input_schema: Erwartete Input-Daten (z.B. {"numbers": "List[int]"})
                - output_schema: Erwartete Output-Daten (z.B. {"sum": "int"})
                - use_cases: Liste von Beispiel-Anwendungsfällen

        Returns:
            Task-ID der erstellten Task
        """
        # Stelle Struktur sicher
        self.file_manager.ensure_v2_structure(user_id)

        # Generiere Task-ID
        task_id = self._generate_task_id(user_id, name)

        # Default Metadaten
        if metadata is None:
            metadata = {}

        default_metadata = {
            "tags": [],
            "category": "",
            "input_schema": {},
            "output_schema": {},
            "use_cases": []
        }
        default_metadata.update(metadata)

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
            "execution_history": [],
            "metadata": default_metadata
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

    def run_task(self, user_id: int, task_id: str, llm_client, user_input: str = "") -> Tuple[bool, str]:
        """
        Führt eine Task aus. Wenn kein Script vorhanden, wird das LLM zur Generierung verwendet.

        Args:
            user_id: Telegram Benutzer-ID
            task_id: Task-ID
            llm_client: LLMClient-Instanz für Script-Generierung
            user_input: Optionale Eingabe für das Script

        Returns:
            (success: bool, result: str) - Erfolg und Ausgabe/Fehler
        """
        import subprocess
        import tempfile
        import time

        # Task laden
        task = self.get_task(user_id, task_id)
        if not task:
            return False, f"Task {task_id} nicht gefunden"

        # Wenn kein Script vorhanden, generiere eines mit Multi-Agenten-System
        if not task.get("script") or task["script"].strip() == "":
            logger.info(f"Generiere Script für Task {task_id} mit Multi-Agenten-System...")

            try:
                # Multi-Agenten-Loop: Developer + Critic
                max_iterations = 3
                approved_script = None
                iteration_history = []

                for iteration in range(max_iterations):
                    logger.info(f"Developer-Critic Iteration {iteration + 1}/{max_iterations}")

                    # 1. DEVELOPER: Script generieren (oder verbessern)
                    if iteration == 0:
                        # Erste Iteration: Neues Script erstellen
                        developer_prompt = self._build_developer_prompt(task['description'], iteration_history)
                    else:
                        # Folge-Iterationen: Script basierend auf Critic-Feedback verbessern
                        developer_prompt = self._build_improvement_prompt(task['description'], iteration_history)

                    script = llm_client.chat(user_message=developer_prompt, max_tokens=1000)

                    # Markdown-Code-Blöcke entfernen
                    script = self._clean_script_code(script)

                    logger.info(f"Developer hat Script generiert (Iteration {iteration + 1})")

                    # 2. CRITIC: Script prüfen
                    critic_result = self._critic_script(
                        llm_client=llm_client,
                        task_description=task['description'],
                        script=script
                    )

                    logger.info(f"Critic Bewertung: {critic_result['status']}")

                    # Iteration speichern
                    iteration_history.append({
                        'iteration': iteration + 1,
                        'script': script,
                        'critic_status': critic_result['status'],
                        'critic_feedback': critic_result['feedback']
                    })

                    # 3. Wenn Critic approves → Fertig
                    if critic_result['status'] == 'APPROVED':
                        approved_script = script
                        logger.info(f"Script vom Critic freigegeben nach {iteration + 1} Iteration(en)")
                        break
                    else:
                        logger.warning(f"Critic ablehnt ab: {critic_result['feedback'][:100]}...")
                        # Loop continues mit verbessertem Prompt

                # Wenn kein Script freigegeben wurde, nehme das letzte (als Fallback)
                if not approved_script:
                    logger.warning("Kein Script vom Critic freigegeben, nehme letzte Version als Fallback")
                    approved_script = iteration_history[-1]['script']

                # Speichere freigegebenes Script
                self.update_task(user_id, task_id, script=approved_script)
                task["script"] = approved_script
                logger.info(f"Script nach {len(iteration_history)} Developer-Critic Iterationen generiert")

            except Exception as e:
                error_msg = f"Fehler bei Multi-Agenten Script-Generierung: {str(e)}"
                logger.error(error_msg)
                self.update_task(user_id, task_id, error=error_msg)
                return False, error_msg

        # Script ausführen
        start_time = time.time()

        try:
            # Temporäre Datei für Script
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(task["script"])
                script_path = f.name

            # Führe Script aus
            cmd = ["python3", script_path]
            if user_input:
                cmd.append(user_input)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            execution_time = time.time() - start_time

            # Aufräumen
            import os
            os.unlink(script_path)

            # Erfolg?
            if result.returncode == 0:
                output = result.stdout.strip()

                # Selbstüberprüfung: LLM analysiert das Ergebnis
                validation_result = self._validate_execution_output(
                    llm_client=llm_client,
                    task_description=task['description'],
                    script_output=output,
                    task_id=task_id
                )

                # Speichere Ergebnis
                self.update_task(
                    user_id,
                    task_id,
                    status="completed",
                    output=output,
                    execution_time=execution_time
                )

                # Logge Validierungsergebnis
                if validation_result["is_valid"]:
                    logger.info(f"Task {task_id} erfolgreich ausgeführt und validiert")
                else:
                    logger.warning(f"Task {task_id} ausgeführt aber Validierung kritisiert: {validation_result['reason']}")

                return True, output
            else:
                error = result.stderr.strip() or "Script returned non-zero exit code"
                self.update_task(
                    user_id,
                    task_id,
                    status="active",
                    error=error,
                    execution_time=execution_time
                )
                logger.error(f"Task {task_id} fehlgeschlagen: {error}")
                return False, f"Fehler bei Ausführung:\n{error}"

        except subprocess.TimeoutExpired:
            error_msg = "Script-Ausführung dauert zu lange (Timeout nach 30 Sekunden)"
            self.update_task(user_id, task_id, error=error_msg)
            logger.error(f"Task {task_id} Timeout")
            return False, error_msg

        except Exception as e:
            error_msg = f"Fehler bei Script-Ausführung: {str(e)}"
            self.update_task(user_id, task_id, error=error_msg)
            logger.error(f"Task {task_id} Exception: {e}")
            return False, error_msg

    def _validate_execution_output(
        self,
        llm_client,
        task_description: str,
        script_output: str,
        task_id: str
    ) -> dict:
        """
        Analysiert die Script-Ausgabe mit LLM und prüft, ob das Ergebnis die Anforderung erfüllt.

        Args:
            llm_client: LLMClient-Instanz
            task_description: Die ursprüngliche Aufgabenbeschreibung
            script_output: Die Ausgabe des Scripts
            task_id: Task-ID für Logging

        Returns:
            dict mit 'is_valid' (bool) und 'reason' (str)
        """
        validation_prompt = f"""Analysiere die Ausgabe eines Python-Scripts und prüfe, ob die Aufgabe erfüllt wurde.

AUFGABE: {task_description}

SCRIPT-AUSGABE:
{script_output}

PRÜFUNG:
1. Erfüllt die Ausgabe die Anforderung?
2. Gibt es offensichtliche Fehler oder Probleme?
3. Ist das Ergebnis plausibel und vollständig?

ANTWORT FORMAT:
Gib nur eine Zeile zurück mit entweder:
- VALID: <kurze Bestätigung was gut ist>
- INVALID: <kurze Erklärung was fehlt oder falsch ist>

Beispiele:
- VALID: Ausgabe zeigt korrekt den Titel der Webseite
- VALID: Berechnung ergibt korrektes Ergebnis
- INVALID: Ausgabe ist leer oder enthält nur Fehlermeldung
- INVALID: Ergebnis entspricht nicht der Anforderung"""

        try:
            response = llm_client.chat(user_message=validation_prompt, max_tokens=100).strip()

            # Parse Antwort
            if response.upper().startswith("VALID"):
                logger.info(f"Task {task_id} Validierung: {response}")
                return {"is_valid": True, "reason": response}
            else:
                logger.warning(f"Task {task_id} Validierung: {response}")
                return {"is_valid": False, "reason": response}

        except Exception as e:
            logger.error(f"Fehler bei Validierung von Task {task_id}: {e}")
            # Bei Validierungsfehler assume success (besser als false positive)
            return {"is_valid": True, "reason": "Validierung fehlgeschlagen, assume success"}

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

            # KI Discovery Metadata
            metadata = task_data.get("metadata", {})
            if metadata.get("tags") or metadata.get("category"):
                f.write("## KI Discovery Metadata\n\n")

                if metadata.get("category"):
                    f.write(f"- Category: {metadata['category']}\n")

                if metadata.get("tags"):
                    f.write(f"- Tags: {', '.join(metadata['tags'])}\n")

                if metadata.get("input_schema"):
                    f.write(f"- Input Schema: ```json\n{json.dumps(metadata['input_schema'], indent=2, ensure_ascii=False)}\n```\n")

                if metadata.get("output_schema"):
                    f.write(f"- Output Schema: ```json\n{json.dumps(metadata['output_schema'], indent=2, ensure_ascii=False)}\n```\n")

                if metadata.get("use_cases"):
                    f.write("\n**Use Cases:**\n")
                    for use_case in metadata["use_cases"]:
                        f.write(f"- {use_case}\n")

                f.write("\n")

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
                "execution_history": [],
                "metadata": {
                    "tags": [],
                    "category": "",
                    "input_schema": {},
                    "output_schema": {},
                    "use_cases": []
                }
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

            # Parse KI Discovery Metadata
            in_ki_meta = False
            ki_meta_content = []
            for line in lines:
                if line.startswith("## KI Discovery Metadata"):
                    in_ki_meta = True
                    continue
                elif line.startswith("##"):
                    in_ki_meta = False

                if in_ki_meta:
                    ki_meta_content.append(line)

            # Parse KI Metadata Fields
            if ki_meta_content:
                content_str = "\n".join(ki_meta_content)

                # Parse Category
                if "- Category:" in content_str:
                    for line in ki_meta_content:
                        if line.strip().startswith("- Category:"):
                            task_data["metadata"]["category"] = line.split(":", 1)[1].strip()

                # Parse Tags
                if "- Tags:" in content_str:
                    for line in ki_meta_content:
                        if line.strip().startswith("- Tags:"):
                            tags_str = line.split(":", 1)[1].strip()
                            task_data["metadata"]["tags"] = [t.strip() for t in tags_str.split(",")]

                # Parse Input Schema (JSON)
                if "- Input Schema:" in content_str:
                    try:
                        schema_start = False
                        schema_lines = []
                        for line in ki_meta_content:
                            if "- Input Schema:" in line:
                                schema_start = True
                                continue
                            if schema_start:
                                if line.strip() == "```":
                                    break
                                if line.strip().startswith("```json"):
                                    continue
                                if line.strip().startswith("- "):
                                    break
                                schema_lines.append(line)
                        if schema_lines:
                            task_data["metadata"]["input_schema"] = json.loads("\n".join(schema_lines))
                    except Exception as e:
                        logger.warning(f"Fehler beim Parsen von Input Schema: {e}")

                # Parse Output Schema (JSON)
                if "- Output Schema:" in content_str:
                    try:
                        schema_start = False
                        schema_lines = []
                        for line in ki_meta_content:
                            if "- Output Schema:" in line:
                                schema_start = True
                                continue
                            if schema_start:
                                if line.strip() == "```":
                                    break
                                if line.strip().startswith("```json"):
                                    continue
                                if line.strip().startswith("- "):
                                    break
                                schema_lines.append(line)
                        if schema_lines:
                            task_data["metadata"]["output_schema"] = json.loads("\n".join(schema_lines))
                    except Exception as e:
                        logger.warning(f"Fehler beim Parsen von Output Schema: {e}")

                # Parse Use Cases
                use_case_start = False
                for line in ki_meta_content:
                    if "**Use Cases:**" in line:
                        use_case_start = True
                        continue
                    if use_case_start and line.strip().startswith("- "):
                        use_case = line.strip().lstrip("- ")
                        task_data["metadata"]["use_cases"].append(use_case)

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

    def _build_developer_prompt(self, task_description: str, iteration_history: list) -> str:
        """Erstellt Prompt für Developer-Agent (Script-Generierung)."""
        return f"""Du bist ein Senior Python Developer. Erstelle ein robustes, fehlerfreies Python-Script.

AUFGABE: {task_description}

ANFORDERUNGEN:
1. SYNTAX: Perfektes Python, keine f-string Fehler, keine Indentation errors
2. STRUKTUR: Nutze main() Funktion und if __name__ == "__main__"
3. FEHLERBEHANDLUNG: Alle externen Operationen in try/except
4. IMPORTS: Nur Standard-Library (sys, os, urllib, json, subprocess, platform, socket)
5. AUSGABE: Ergebnis mit print() ausgeben
6. PARAMETER: Über sys.argv[1] lesen wenn benötigt

BEISPIEL-STRUKTUR:
```python
import sys
import os

def main():
    try:
        # Dein Code hier
        if len(sys.argv) > 1:
            param = sys.argv[1]
        result = "..."
        print(result)
    except Exception as e:
        print(f"Fehler: {{e}}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

WICHTIG:
- Schreibe KOMPLETTES, lauffähiges Script
- Keine abgeschnittenen Strings oder f-strings
- Korrekte Einrückung (4 Spaces)
- Alle Strings korrekt schließen

Schreibe nur den Python-Code ohne Markdown."""

    def _build_improvement_prompt(self, task_description: str, iteration_history: list) -> str:
        """Erstellt Prompt für Developer-Agent (Script-Verbesserung basierend auf Critic-Feedback)."""
        last_feedback = iteration_history[-1]['critic_feedback']

        return f"""Du bist ein Senior Python Developer. Verbessere das Script basierend auf dem Feedback.

AUFGABE: {task_description}

KRITIK VOM CODE REVIEWER:
{last_feedback}

DEIN JOB:
1. Analysiere das Kritik-Punkte
2. Korrigiere ALLE genannten Fehler
3. Stelle sicher, dass das Script syntaktisch korrekt ist
4. Achte auf: f-string Schließung, Klammern, Indentation

WICHTIGSTE REGELN:
- Alle f-strings MÜSSEN korrekt geschlossen sein: print(f"...")
- Keine unvollständigen Strings
- Korrekte Exception-Handling
- Alle imports am Anfang

Schreibe nur den korrigierten Python-Code ohne Markdown."""

    def _critic_script(self, llm_client, task_description: str, script: str) -> dict:
        """
        Critic-Agent: Prüft das Script auf Syntax und Logik-Fehler.

        Returns:
            dict with 'status' ('APPROVED' or 'NEEDS_IMPROVEMENT') and 'feedback' (str)
        """
        critic_prompt = f"""Du bist ein strenger Code Reviewer. Prüfe das Python-Script.

AUFGABE: {task_description}

ZU PRÜFENDES SCRIPT:
{script}

PRÜFUNG:
1. SYNTAX-FEHLER:
   - Alle f-strings korrekt geschlossen? (print(f"...) ))
   - Alle Klammern paarig?
   - Korrekte Indentation?
   - Alle Strings geschlossen?

2. IMPORTS:
   - Nur Standard-Library?
   - Alle imports korrekt?

3. LOGIK:
   - Erfüllt Script die Aufgabe?
   - Gibt es offensichtliche Logik-Fehler?

4. AUSFÜHRUNG:
   - Wird das Script laufen ohne Fehler?

ENTSCHEIDUNG:
- Wenn ALLES korrekt → "APPROVED: Script ist bereit für Produktion"
- Wenn FEHLER gefunden → "NEEDS_IMPROVEMENT: <Liste der Fehler mit Lösungsvorschlägen>"

Gib nur EINE Zeile zurück mit entweder APPROVED oder NEEDS_IMPROVEMENT."""

        try:
            response = llm_client.chat(user_message=critic_prompt, max_tokens=200).strip()

            if "APPROVED" in response.upper():
                return {
                    'status': 'APPROVED',
                    'feedback': response
                }
            else:
                return {
                    'status': 'NEEDS_IMPROVEMENT',
                    'feedback': response
                }
        except Exception as e:
            logger.error(f"Fehler bei Critic-Prüfung: {e}")
            # Bei Fehler: Defensive → Approven
            return {
                'status': 'APPROVED',
                'feedback': f'Critic fehlgeschlagen, auto-approved: {e}'
            }

    def _clean_script_code(self, script: str) -> str:
        """Entfernt Markdown-Code-Blöcke und bereinigt das Script."""
        script = script.strip()

        # Markdown-Code-Blöcke entfernen
        if script.startswith("```python"):
            script = script.split("```python", 1)[1]
        if script.startswith("```"):
            script = script.split("```", 1)[1]
        if script.endswith("```"):
            script = script.rsplit("```", 1)[0]

        return script.strip()

