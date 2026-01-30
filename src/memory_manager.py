"""
Memory Manager für Crowdbot

Verwaltet das Konversationsgedächtnis pro User in Markdown-Dateien.
Jede Unterhaltung wird in /data/users/{user_id}/memory.md gespeichert.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict


class MemoryManager:
    """Verwaltet das Gedächtnis für Crowdbot-Benutzer."""

    def __init__(self, data_dir: str = "/media/xray/NEU/Code/Crowdbot/data"):
        """
        Initialisiert den Memory Manager.

        Args:
            data_dir: Basisverzeichnis für Benutzerdaten
        """
        self.data_dir = Path(data_dir)
        self.users_dir = self.data_dir / "users"
        self.users_dir.mkdir(parents=True, exist_ok=True)

    def _get_memory_path(self, user_id: int) -> Path:
        """
        Gibt den Pfad zur Memory-Datei eines Benutzers zurück.

        Args:
            user_id: Telegram Benutzer-ID

        Returns:
            Pfad zur memory.md Datei
        """
        user_dir = self.users_dir / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir / "memory.md"

    def create_user(self, user_id: int, username: str = None) -> bool:
        """
        Erstellt einen neuen Benutzer mit Memory-Datei.

        Args:
            user_id: Telegram Benutzer-ID
            username: Optionaler Benutzername

        Returns:
            True wenn erfolgreich, False wenn Benutzer bereits existiert
        """
        memory_path = self._get_memory_path(user_id)

        if memory_path.exists():
            return False

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        display_name = username or f"User_{user_id}"

        initial_content = f"""# Crowdbot Gedächtnis für {display_name}

Erstellt: {timestamp}

---

## Beginn der Konversation

"""

        memory_path.write_text(initial_content, encoding="utf-8")
        return True

    def reset_user(self, user_id: int, username: str = None) -> bool:
        """
        Setzt das Gedächtnis eines Benutzers zurück.

        Args:
            user_id: Telegram Benutzer-ID
            username: Optionaler Benutzername

        Returns:
            True wenn erfolgreich
        """
        memory_path = self._get_memory_path(user_id)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        display_name = username or f"User_{user_id}"

        reset_content = f"""# Crowdbot Gedächtnis für {display_name}

Zurückgesetzt: {timestamp}

---

## Beginn der Konversation

"""

        memory_path.write_text(reset_content, encoding="utf-8")
        return True

    def append_message(self, user_id: int, role: str, content: str) -> bool:
        """
        Fügt eine neue Nachricht zum Gedächtnis hinzu.

        Args:
            user_id: Telegram Benutzer-ID
            role: "user" oder "assistant"
            content: Der Nachrichteninhalt

        Returns:
            True wenn erfolgreich
        """
        memory_path = self._get_memory_path(user_id)

        # Stelle sicher, dass die Datei existiert
        if not memory_path.exists():
            self.create_user(user_id)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Role-Name bestimmen
        role_name = "Benutzer" if role == "user" else "Crowdbot"

        # Markdown-Format für die Nachricht
        message_entry = f"""
### {role_name} - {timestamp}

{content}

---

"""

        # An Datei anhängen
        with open(memory_path, "a", encoding="utf-8") as f:
            f.write(message_entry)

        return True

    def get_context(self, user_id: int, max_messages: int = 10) -> List[Dict[str, str]]:
        """
        Lädt die letzten Nachrichten aus dem Gedächtnis.

        Args:
            user_id: Telegram Benutzer-ID
            max_messages: Maximale Anzahl der letzten Nachrichten

        Returns:
            Liste von Dictionaries mit {"role": ..., "content": ...}
        """
        memory_path = self._get_memory_path(user_id)

        if not memory_path.exists():
            return []

        content = memory_path.read_text(encoding="utf-8")

        # Extrahiere Nachrichten aus dem Markdown-Format
        messages = []
        current_role = None
        current_content = []

        for line in content.split("\n"):
            # Erkenne Role-Header
            if line.startswith("### Benutzer - "):
                if current_role and current_content:
                    messages.append({
                        "role": current_role,
                        "content": "\n".join(current_content).strip()
                    })
                current_role = "user"
                current_content = []
            elif line.startswith("### Crowdbot - "):
                if current_role and current_content:
                    messages.append({
                        "role": current_role,
                        "content": "\n".join(current_content).strip()
                    })
                current_role = "assistant"
                current_content = []
            # Überspringe Trennlinien und leere Zeilen
            elif line.strip() and not line.startswith("---") and not line.startswith("#"):
                current_content.append(line)

        # Letzte Nachricht hinzufügen
        if current_role and current_content:
            messages.append({
                "role": current_role,
                "content": "\n".join(current_content).strip()
            })

        # Gib nur die letzten max_messages zurück
        return messages[-max_messages:]

    def user_exists(self, user_id: int) -> bool:
        """
        Prüft, ob ein Benutzer bereits existiert.

        Args:
            user_id: Telegram Benutzer-ID

        Returns:
            True wenn Benutzer existiert
        """
        return self._get_memory_path(user_id).exists()

    def get_memory_stats(self, user_id: int) -> Dict[str, any]:
        """
        Gibt Statistiken über das Gedächtnis eines Benutzers zurück.

        Args:
            user_id: Telegram Benutzer-ID

        Returns:
            Dictionary mit Statistiken
        """
        memory_path = self._get_memory_path(user_id)

        if not memory_path.exists():
            return {"exists": False}

        content = memory_path.read_text(encoding="utf-8")
        messages = self.get_context(user_id, max_messages=1000)

        return {
            "exists": True,
            "total_messages": len(messages),
            "file_size_bytes": len(content.encode("utf-8")),
            "path": str(memory_path)
        }
