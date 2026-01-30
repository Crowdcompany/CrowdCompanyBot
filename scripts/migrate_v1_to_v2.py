#!/usr/bin/env python3
"""
Migration Script: Memory V1 → Memory V2

Migriert bestehende memory.md Dateien zur neuen hierarchischen Struktur.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import re
import shutil

# Projekt-Root zum Path hinzufügen
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.file_structure import FileStructureManager


def parse_v1_memory(memory_path: Path) -> list:
    """
    Parsed eine V1 memory.md Datei und extrahiert Konversationen mit Timestamps.

    Returns:
        Liste von (timestamp, role, content) Tupeln
    """
    if not memory_path.exists():
        return []

    content = memory_path.read_text(encoding="utf-8")
    conversations = []

    # Regex für V1 Format: ### Benutzer - 2026-01-30 12:30:49
    pattern = r"### (Benutzer|Crowdbot) - (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\n\n(.*?)(?=\n---|\Z)"

    matches = re.finditer(pattern, content, re.DOTALL)

    for match in matches:
        role = match.group(1)
        timestamp_str = match.group(2)
        message = match.group(3).strip()

        try:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            conversations.append((timestamp, role, message))
        except ValueError:
            print(f"Warnung: Konnte Timestamp nicht parsen: {timestamp_str}")
            continue

    return conversations


def migrate_user(user_id: int, data_dir: Path):
    """
    Migriert einen einzelnen User von V1 zu V2.

    Args:
        user_id: Telegram User-ID
        data_dir: Basis-Datenverzeichnis
    """
    user_dir = data_dir / "users" / str(user_id)
    old_memory = user_dir / "memory.md"

    if not old_memory.exists():
        print(f"Keine V1 Memory-Datei für User {user_id} gefunden.")
        return

    print(f"\n=== Migration für User {user_id} ===")

    # 1. Backup erstellen
    backup_path = user_dir / f"memory_v1_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    shutil.copy2(old_memory, backup_path)
    print(f"✓ Backup erstellt: {backup_path.name}")

    # 2. V1 Memory parsen
    conversations = parse_v1_memory(old_memory)
    print(f"✓ {len(conversations)} Konversationen gefunden")

    if not conversations:
        print("Keine Konversationen zum Migrieren.")
        return

    # 3. V2 Struktur erstellen
    file_manager = FileStructureManager(str(data_dir))
    file_manager.ensure_v2_structure(user_id)
    print("✓ V2 Ordnerstruktur erstellt")

    # 4. Konversationen nach Datum gruppieren
    daily_conversations = {}
    for timestamp, role, message in conversations:
        date_key = timestamp.strftime("%Y%m%d")
        if date_key not in daily_conversations:
            daily_conversations[date_key] = []
        daily_conversations[date_key].append((timestamp, role, message))

    # 5. Tagesdateien schreiben
    for date_key, day_convs in sorted(daily_conversations.items()):
        date_obj = datetime.strptime(date_key, "%Y%m%d")
        daily_file = user_dir / "daily" / f"{date_key}.md"

        # Tagesdatei-Header
        header = f"# Konversation vom {date_obj.strftime('%d.%m.%Y')}\n\n"
        header += f"Erstellt durch Migration am {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        header += "---\n\n"

        # Konversationen hinzufügen
        content = header
        for timestamp, role, message in day_convs:
            content += f"### {role} - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            content += f"{message}\n\n"
            content += "---\n\n"

        daily_file.write_text(content, encoding="utf-8")

    print(f"✓ {len(daily_conversations)} Tagesdateien erstellt")

    # 6. Memory.md Index erstellen
    memory_index = user_dir / "memory.md"

    # Extrahiere Username aus erster Zeile der V1 Memory
    first_line = old_memory.read_text(encoding="utf-8").split('\n')[0]
    username_match = re.search(r"für (.+)", first_line)
    username = username_match.group(1) if username_match else "User"

    # Erstelle neuen Index
    index_content = f"# Crowdbot Langzeitgedächtnis für {username}\n\n"
    index_content += f"Erstellt: {min(conversations, key=lambda x: x[0])[0].strftime('%Y-%m-%d')}\n"
    index_content += f"Letzte Aktualisierung: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    index_content += f"Migration von V1: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    index_content += "---\n\n"
    index_content += "## Wichtige Persönliche Informationen\n\n"
    index_content += "*(Wird durch Memory 2.0 System automatisch gefüllt)*\n\n"
    index_content += "---\n\n"
    index_content += "## Konversationshistorie (Chronologisch, neueste zuerst)\n\n"

    # Füge Tagesdateien als Links hinzu
    for date_key in sorted(daily_conversations.keys(), reverse=True):
        date_obj = datetime.strptime(date_key, "%Y%m%d")
        date_str = date_obj.strftime("%d.%m.%Y")
        day_convs = daily_conversations[date_key]

        # Erste User-Nachricht als Thema
        first_user_msg = next((msg for _, role, msg in day_convs if role == "Benutzer"), "")
        topic = first_user_msg[:60] + "..." if len(first_user_msg) > 60 else first_user_msg

        index_content += f"### {date_str} - [Details](daily/{date_key}.md)\n\n"
        index_content += f"**Thema:** {topic}\n"
        index_content += f"**Nachrichten:** {len(day_convs)}\n\n"

    index_content += "---\n\n"
    index_content += "## Meta-Statistiken\n\n"
    index_content += f"- **Gesamtgespräche:** {len(conversations)}\n"
    index_content += f"- **Tagesdateien:** {len(daily_conversations)}\n"
    index_content += f"- **Migration:** V1 → V2 erfolgreich\n"

    memory_index.write_text(index_content, encoding="utf-8")
    print("✓ memory.md Index erstellt")

    # 7. Alte memory.md umbenennen (nicht löschen)
    old_memory.rename(user_dir / "memory_v1_original.md")
    print("✓ Alte memory.md → memory_v1_original.md")

    print(f"\n✓ Migration für User {user_id} abgeschlossen!")
    print(f"  - Backup: {backup_path.name}")
    print(f"  - Tagesdateien: {len(daily_conversations)}")
    print(f"  - Konversationen: {len(conversations)}")


def main():
    """Hauptfunktion."""
    import argparse

    parser = argparse.ArgumentParser(description="Migriert Memory V1 zu V2")
    parser.add_argument("--user-id", type=int, help="Spezifische User-ID migrieren")
    parser.add_argument("--all", action="store_true", help="Alle User migrieren")
    parser.add_argument("--data-dir", type=str, default="./data", help="Datenverzeichnis")

    args = parser.parse_args()

    data_dir = Path(args.data_dir)

    if not data_dir.exists():
        print(f"Fehler: Datenverzeichnis {data_dir} existiert nicht!")
        sys.exit(1)

    users_dir = data_dir / "users"

    if not users_dir.exists():
        print(f"Fehler: Users-Verzeichnis {users_dir} existiert nicht!")
        sys.exit(1)

    if args.user_id:
        # Einzelner User
        migrate_user(args.user_id, data_dir)
    elif args.all:
        # Alle User
        user_dirs = [d for d in users_dir.iterdir() if d.is_dir()]
        print(f"Gefundene User: {len(user_dirs)}")

        for user_dir in user_dirs:
            try:
                user_id = int(user_dir.name)
                migrate_user(user_id, data_dir)
            except ValueError:
                print(f"Überspringe ungültiges Verzeichnis: {user_dir.name}")
            except Exception as e:
                print(f"Fehler bei User {user_dir.name}: {e}")
    else:
        print("Bitte --user-id oder --all angeben.")
        parser.print_help()
        sys.exit(1)

    print("\n=== Migration abgeschlossen ===")


if __name__ == "__main__":
    main()
