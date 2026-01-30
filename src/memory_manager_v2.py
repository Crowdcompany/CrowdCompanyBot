"""
Memory Manager V2 für Crowdbot

Erweiterte Version mit hierarchischem Gedächtnissystem:
- Tagesdateien (daily/) statt einer großen memory.md
- Master Index (memory.md) als Inhaltsverzeichnis
- Automatische Migration von V1 zu V2
- Rückwärtskompatibilität mit bestehendem Code
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import logging

from .file_structure import FileStructureManager

logger = logging.getLogger(__name__)


class MemoryManagerV2:
    """
    Memory Manager V2 mit hierarchischem Gedächtnissystem.

    Kompatibel mit V1 API, nutzt aber intern die neue Struktur.
    """

    def __init__(self, data_dir: str = "/media/xray/NEU/Code/Crowdbot/data"):
        """
        Initialisiert den Memory Manager V2.

        Args:
            data_dir: Basisverzeichnis für Benutzerdaten
        """
        self.data_dir = Path(data_dir)
        self.users_dir = self.data_dir / "users"
        self.file_structure = FileStructureManager(data_dir)

        # Stelle sicher, dass Basisverzeichnis existiert
        self.users_dir.mkdir(parents=True, exist_ok=True)

    def create_user(self, user_id: int, username: str = None) -> bool:
        """
        Erstellt einen neuen Benutzer mit Memory 2.0 Struktur.

        Args:
            user_id: Telegram Benutzer-ID
            username: Optionaler Benutzername

        Returns:
            True wenn erfolgreich, False wenn Benutzer bereits existiert
        """
        # Prüfe ob User bereits existiert
        if self.user_exists(user_id):
            logger.info(f"User {user_id} existiert bereits")
            return False

        # Erstelle V2 Ordnerstruktur
        self.file_structure.ensure_v2_structure(user_id)

        # Erstelle Master Index (memory.md)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        display_name = username or f"User {user_id}"

        memory_index = f"""# Crowdbot Langzeitgedächtnis für {display_name}

Erstellt: {timestamp}
Letzte Aktualisierung: {timestamp}

---

## Wichtige Persönliche Informationen

### Interessen & Präferenzen
(Noch keine Informationen vorhanden)

### Kontext
(Noch keine Informationen vorhanden)

---

## Konversationshistorie (Chronologisch, neueste zuerst)

### {datetime.now().strftime("%Y-%m-%d")} (Heute) - [Details](daily/{datetime.now().strftime("%Y%m%d")}.md)

**Themen:** Erste Konversation
**Wichtigkeit:** -

---

## Meta-Statistiken

- Gesamtgespräche: 0
- Häufigstes Thema: -
- Durchschnittliche Gesprächslänge: -
- Letzte Bereinigung: Noch nie
"""

        memory_path = self.file_structure.get_memory_index_path(user_id)
        memory_path.write_text(memory_index, encoding="utf-8")

        # Erstelle erste Tagesdatei
        today = datetime.now()
        daily_path = self.file_structure.get_daily_file_path(user_id, today)

        daily_content = f"""# Tagesdatei {today.strftime("%d.%m.%Y")}

Erstellt: {timestamp}

---

## Gespräche

"""

        daily_path.write_text(daily_content, encoding="utf-8")

        # Erstelle leere preferences.md
        prefs_path = self.file_structure.get_preferences_path(user_id)
        prefs_content = f"""# Persistente Präferenzen für {display_name}

Erstellt: {timestamp}

---

## Interessen & Hobbys

## Abneigungen

## Wichtige Projekte

## Persönliche Details

"""
        prefs_path.write_text(prefs_content, encoding="utf-8")

        logger.info(f"User {user_id} erfolgreich mit Memory V2 erstellt")
        return True

    def reset_user(self, user_id: int, username: str = None) -> bool:
        """
        Setzt das Gedächtnis eines Benutzers zurück (löscht alle Dateien).

        Args:
            user_id: Telegram Benutzer-ID
            username: Optionaler Benutzername

        Returns:
            True wenn erfolgreich
        """
        import shutil

        user_dir = self.file_structure.get_user_dir(user_id)

        if not user_dir.exists():
            logger.warning(f"User {user_id} existiert nicht, kann nicht zurückgesetzt werden")
            return False

        # Backup erstellen
        backup_dir = user_dir.parent / f"{user_id}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copytree(user_dir, backup_dir)
        logger.info(f"Backup erstellt: {backup_dir}")

        # User-Verzeichnis löschen
        shutil.rmtree(user_dir)

        # Neu erstellen
        return self.create_user(user_id, username)

    def append_message(self, user_id: int, role: str, content: str) -> bool:
        """
        Fügt eine neue Nachricht zum Gedächtnis hinzu.

        Speichert in der Tagesdatei (daily/YYYYMMDD.md).

        Args:
            user_id: Telegram Benutzer-ID
            role: "user" oder "assistant"
            content: Der Nachrichteninhalt

        Returns:
            True wenn erfolgreich
        """
        # Stelle sicher, dass User existiert
        if not self.user_exists(user_id):
            self.create_user(user_id)

        # Hole Pfad zur heutigen Tagesdatei
        today = datetime.now()
        daily_path = self.file_structure.get_daily_file_path(user_id, today)

        # Erstelle Tagesdatei wenn sie noch nicht existiert
        if not daily_path.exists():
            self._create_daily_file(user_id, today)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        role_name = "Benutzer" if role == "user" else "Crowdbot"

        # Markdown-Format für die Nachricht
        message_entry = f"""
### {role_name} - {timestamp}

{content}

---

"""

        # An Tagesdatei anhängen
        with open(daily_path, "a", encoding="utf-8") as f:
            f.write(message_entry)

        # Aktualisiere memory.md Timestamp
        self._update_memory_index_timestamp(user_id)

        logger.debug(f"Nachricht hinzugefügt für User {user_id} in {daily_path.name}")
        return True

    def get_context(self, user_id: int, max_messages: int = 10) -> List[Dict[str, str]]:
        """
        Lädt die letzten Nachrichten aus dem Gedächtnis.

        Liest aus den Tagesdateien der letzten Tage.

        Args:
            user_id: Telegram Benutzer-ID
            max_messages: Maximale Anzahl der letzten Nachrichten

        Returns:
            Liste von Dictionaries mit {"role": ..., "content": ...}
        """
        if not self.user_exists(user_id):
            return []

        messages = []

        # Lade Tagesdateien der letzten 7 Tage
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        daily_files = self.file_structure.list_daily_files(
            user_id,
            start_date=start_date,
            end_date=end_date
        )

        # Lese Dateien (neueste zuerst)
        for daily_file in daily_files:
            file_messages = self._parse_daily_file(daily_file)
            messages.extend(file_messages)

            # Stoppe wenn genug Nachrichten gesammelt
            if len(messages) >= max_messages:
                break

        # Umkehren (chronologisch) und auf max_messages begrenzen
        messages.reverse()
        return messages[-max_messages:]

    def user_exists(self, user_id: int) -> bool:
        """
        Prüft, ob ein Benutzer bereits existiert.

        Args:
            user_id: Telegram Benutzer-ID

        Returns:
            True wenn Benutzer existiert (V1 oder V2)
        """
        user_dir = self.file_structure.get_user_dir(user_id)

        if not user_dir.exists():
            return False

        # Prüfe auf V2 Struktur (memory.md existiert)
        memory_path = self.file_structure.get_memory_index_path(user_id)

        return memory_path.exists()

    def get_memory_stats(self, user_id: int) -> Dict[str, any]:
        """
        Gibt Statistiken über das Gedächtnis eines Benutzers zurück.

        Args:
            user_id: Telegram Benutzer-ID

        Returns:
            Dictionary mit Statistiken
        """
        if not self.user_exists(user_id):
            return {"exists": False}

        # Hole Struktur-Statistiken
        stats = self.file_structure.get_structure_stats(user_id)

        # Füge Nachrichten-Zählung hinzu
        messages = self.get_context(user_id, max_messages=1000)
        stats["total_messages"] = len(messages)

        # Füge Pfad hinzu
        stats["memory_index_path"] = str(self.file_structure.get_memory_index_path(user_id))

        return stats

    def migrate_from_v1(self, user_id: int) -> bool:
        """
        Migriert einen V1 User zur V2 Struktur.

        Liest die alte memory.md und splittet sie in Tagesdateien.

        Args:
            user_id: Telegram Benutzer-ID

        Returns:
            True wenn erfolgreich
        """
        from .memory_manager import MemoryManager

        # Prüfe ob bereits V2
        if self.file_structure.is_v2_structure(user_id):
            logger.info(f"User {user_id} hat bereits V2 Struktur")
            return True

        # Erstelle V1 Manager
        v1_manager = MemoryManager(str(self.data_dir))
        old_memory_path = v1_manager._get_memory_path(user_id)

        if not old_memory_path.exists():
            logger.error(f"V1 memory.md nicht gefunden für User {user_id}")
            return False

        logger.info(f"Starte Migration von V1 zu V2 für User {user_id}")

        # Backup erstellen
        import shutil
        backup_path = old_memory_path.parent / "memory_v1_backup.md"
        shutil.copy(old_memory_path, backup_path)
        logger.info(f"Backup erstellt: {backup_path}")

        # Erstelle V2 Struktur
        self.file_structure.ensure_v2_structure(user_id)

        # Lese alte memory.md
        content = old_memory_path.read_text(encoding="utf-8")

        # Parse Nachrichten mit Timestamps
        messages_by_date = self._parse_v1_memory(content)

        # Erstelle Tagesdateien
        for date_str, messages in messages_by_date.items():
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
                daily_path = self.file_structure.get_daily_file_path(user_id, date)

                # Erstelle Tagesdatei
                self._create_daily_file(user_id, date)

                # Füge Nachrichten hinzu
                with open(daily_path, "a", encoding="utf-8") as f:
                    for msg in messages:
                        f.write(msg + "\n\n---\n\n")

                logger.debug(f"Tagesdatei erstellt: {daily_path.name} mit {len(messages)} Nachrichten")

            except ValueError as e:
                logger.error(f"Fehler beim Parsen von Datum {date_str}: {e}")
                continue

        # Erstelle memory.md Index
        self._create_memory_index_from_migration(user_id)

        # Erstelle leere preferences.md
        prefs_path = self.file_structure.get_preferences_path(user_id)
        prefs_content = f"""# Persistente Präferenzen

Migriert von V1: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

"""
        prefs_path.write_text(prefs_content, encoding="utf-8")

        # Lösche alte memory.md (Backup existiert ja)
        old_memory_path.unlink()

        logger.info(f"Migration erfolgreich abgeschlossen für User {user_id}")
        return True

    # Private Hilfsmethoden

    def _create_daily_file(self, user_id: int, date: datetime):
        """Erstellt eine neue Tagesdatei."""
        daily_path = self.file_structure.get_daily_file_path(user_id, date)

        if daily_path.exists():
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        daily_content = f"""# Tagesdatei {date.strftime("%d.%m.%Y")}

Erstellt: {timestamp}

---

## Gespräche

"""

        daily_path.write_text(daily_content, encoding="utf-8")

    def _parse_daily_file(self, file_path: Path) -> List[Dict[str, str]]:
        """Parst eine Tagesdatei und extrahiert Nachrichten."""
        if not file_path.exists():
            return []

        content = file_path.read_text(encoding="utf-8")
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
            # Überspringe Trennlinien und Header
            elif line.strip() and not line.startswith("---") and not line.startswith("#"):
                current_content.append(line)

        # Letzte Nachricht hinzufügen
        if current_role and current_content:
            messages.append({
                "role": current_role,
                "content": "\n".join(current_content).strip()
            })

        return messages

    def _parse_v1_memory(self, content: str) -> Dict[str, List[str]]:
        """
        Parst V1 memory.md und gruppiert Nachrichten nach Datum.

        Returns:
            Dict mit Datum (YYYY-MM-DD) als Key und Liste von Nachrichten als Value
        """
        messages_by_date = {}
        current_date = None
        current_message = []

        for line in content.split("\n"):
            # Erkenne Timestamps in Headers
            if line.startswith("### ") and " - " in line:
                # Extrahiere Datum aus "### Benutzer - 2026-01-30 15:21:46"
                try:
                    timestamp_part = line.split(" - ", 1)[1]
                    date_str = timestamp_part.split()[0]  # "2026-01-30"

                    # Speichere vorherige Nachricht
                    if current_date and current_message:
                        if current_date not in messages_by_date:
                            messages_by_date[current_date] = []
                        messages_by_date[current_date].append("\n".join(current_message))

                    current_date = date_str
                    current_message = [line]

                except (IndexError, ValueError):
                    current_message.append(line)

            else:
                current_message.append(line)

        # Letzte Nachricht speichern
        if current_date and current_message:
            if current_date not in messages_by_date:
                messages_by_date[current_date] = []
            messages_by_date[current_date].append("\n".join(current_message))

        return messages_by_date

    def _create_memory_index_from_migration(self, user_id: int):
        """Erstellt memory.md Index nach Migration."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Liste alle Tagesdateien
        daily_files = self.file_structure.list_daily_files(user_id)

        # Erstelle chronologische Liste
        history_entries = []
        for daily_file in daily_files[:30]:  # Max 30 letzte Tage
            try:
                date = datetime.strptime(daily_file.stem, "%Y%m%d")
                date_str = date.strftime("%Y-%m-%d")

                entry = f"""### {date_str} - [Details](daily/{daily_file.name})

**Migriert von V1**
"""
                history_entries.append(entry)

            except ValueError:
                continue

        history_section = "\n\n".join(history_entries)

        memory_index = f"""# Crowdbot Langzeitgedächtnis

Migriert von V1: {timestamp}
Letzte Aktualisierung: {timestamp}

---

## Wichtige Persönliche Informationen

(Wird beim ersten Cleanup befüllt)

---

## Konversationshistorie (Chronologisch, neueste zuerst)

{history_section}

---

## Meta-Statistiken

- Migration abgeschlossen: {timestamp}
- Tagesdateien: {len(daily_files)}
"""

        memory_path = self.file_structure.get_memory_index_path(user_id)
        memory_path.write_text(memory_index, encoding="utf-8")

    def _update_memory_index_timestamp(self, user_id: int):
        """Aktualisiert den Timestamp in memory.md."""
        memory_path = self.file_structure.get_memory_index_path(user_id)

        if not memory_path.exists():
            return

        content = memory_path.read_text(encoding="utf-8")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Ersetze "Letzte Aktualisierung:" Zeile
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("Letzte Aktualisierung:"):
                lines[i] = f"Letzte Aktualisierung: {timestamp}"
                break

        memory_path.write_text("\n".join(lines), encoding="utf-8")
