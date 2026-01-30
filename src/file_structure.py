"""
File Structure Manager für Memory 2.0

Verwaltet die hierarchische Ordnerstruktur für das erweiterte Gedächtnissystem:
- daily/: Tagesdateien (YYYYMMDD.md)
- weekly/: Wochenzusammenfassungen (YYYY-WXX.md)
- monthly/: Monatszusammenfassungen (YYYY-MM.md)
- archive/: Alte Dateien (komprimiert nach 90 Tagen)
- important/: Persistente Präferenzen
"""

import os
import gzip
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class FileStructureManager:
    """Verwaltet die Memory 2.0 Ordnerstruktur."""

    def __init__(self, data_dir: str = "/media/xray/NEU/Code/Crowdbot/data"):
        """
        Initialisiert den File Structure Manager.

        Args:
            data_dir: Basisverzeichnis für Benutzerdaten
        """
        self.data_dir = Path(data_dir)
        self.users_dir = self.data_dir / "users"
        self.users_dir.mkdir(parents=True, exist_ok=True)

    def get_user_dir(self, user_id: int) -> Path:
        """Gibt das Hauptverzeichnis eines Benutzers zurück."""
        return self.users_dir / str(user_id)

    def ensure_v2_structure(self, user_id: int) -> bool:
        """
        Stellt sicher, dass die Memory 2.0 Ordnerstruktur existiert.

        Args:
            user_id: Telegram Benutzer-ID

        Returns:
            True wenn erfolgreich erstellt/geprüft
        """
        user_dir = self.get_user_dir(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        # Erstelle alle Unterordner
        folders = [
            "daily",
            "weekly",
            "monthly",
            "archive/daily",
            "archive/weekly",
            "archive/monthly",
            "important"
        ]

        for folder in folders:
            (user_dir / folder).mkdir(parents=True, exist_ok=True)

        logger.info(f"Memory 2.0 Struktur für User {user_id} erstellt/geprüft")
        return True

    def get_daily_file_path(self, user_id: int, date: datetime = None) -> Path:
        """
        Gibt den Pfad zur Tagesdatei für ein bestimmtes Datum zurück.

        Args:
            user_id: Telegram Benutzer-ID
            date: Datum (default: heute)

        Returns:
            Pfad zur daily/YYYYMMDD.md Datei
        """
        if date is None:
            date = datetime.now()

        user_dir = self.get_user_dir(user_id)
        filename = date.strftime("%Y%m%d.md")
        return user_dir / "daily" / filename

    def get_weekly_file_path(self, user_id: int, year: int, week: int) -> Path:
        """
        Gibt den Pfad zur Wochenzusammenfassung zurück.

        Args:
            user_id: Telegram Benutzer-ID
            year: Jahr (z.B. 2026)
            week: Kalenderwoche (1-53)

        Returns:
            Pfad zur weekly/YYYY-WXX.md Datei
        """
        user_dir = self.get_user_dir(user_id)
        filename = f"{year}-W{week:02d}.md"
        return user_dir / "weekly" / filename

    def get_monthly_file_path(self, user_id: int, year: int, month: int) -> Path:
        """
        Gibt den Pfad zur Monatszusammenfassung zurück.

        Args:
            user_id: Telegram Benutzer-ID
            year: Jahr (z.B. 2026)
            month: Monat (1-12)

        Returns:
            Pfad zur monthly/YYYY-MM.md Datei
        """
        user_dir = self.get_user_dir(user_id)
        filename = f"{year}-{month:02d}.md"
        return user_dir / "monthly" / filename

    def get_memory_index_path(self, user_id: int) -> Path:
        """
        Gibt den Pfad zur memory.md (Master Index) zurück.

        Args:
            user_id: Telegram Benutzer-ID

        Returns:
            Pfad zur memory.md Datei
        """
        return self.get_user_dir(user_id) / "memory.md"

    def get_preferences_path(self, user_id: int) -> Path:
        """
        Gibt den Pfad zur preferences.md zurück.

        Args:
            user_id: Telegram Benutzer-ID

        Returns:
            Pfad zur important/preferences.md Datei
        """
        return self.get_user_dir(user_id) / "important" / "preferences.md"

    def list_daily_files(self, user_id: int, start_date: datetime = None,
                        end_date: datetime = None) -> List[Path]:
        """
        Listet alle Tagesdateien für einen Zeitraum auf.

        Args:
            user_id: Telegram Benutzer-ID
            start_date: Startdatum (optional)
            end_date: Enddatum (optional)

        Returns:
            Liste von Pfaden zu Tagesdateien, sortiert nach Datum (neueste zuerst)
        """
        daily_dir = self.get_user_dir(user_id) / "daily"

        if not daily_dir.exists():
            return []

        # Alle .md Dateien im daily Ordner
        files = list(daily_dir.glob("*.md"))

        # Filtern nach Datum wenn angegeben
        if start_date or end_date:
            filtered_files = []
            for file in files:
                try:
                    # Parse Datum aus Dateiname YYYYMMDD.md
                    file_date = datetime.strptime(file.stem, "%Y%m%d")

                    if start_date and file_date < start_date:
                        continue
                    if end_date and file_date > end_date:
                        continue

                    filtered_files.append(file)
                except ValueError:
                    logger.warning(f"Ungültiger Dateiname: {file.name}")
                    continue

            files = filtered_files

        # Sortiere nach Datum (neueste zuerst)
        files.sort(reverse=True)
        return files

    def archive_file(self, source_path: Path, user_id: int,
                    file_type: str = "daily") -> Optional[Path]:
        """
        Verschiebt eine Datei ins Archiv.

        Args:
            source_path: Quellpfad der zu archivierenden Datei
            user_id: Telegram Benutzer-ID
            file_type: "daily", "weekly" oder "monthly"

        Returns:
            Pfad zur archivierten Datei oder None bei Fehler
        """
        if not source_path.exists():
            logger.error(f"Quelldatei existiert nicht: {source_path}")
            return None

        user_dir = self.get_user_dir(user_id)
        archive_dir = user_dir / "archive" / file_type
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Ziel-Pfad im Archiv
        archive_path = archive_dir / source_path.name

        try:
            shutil.move(str(source_path), str(archive_path))
            logger.info(f"Datei archiviert: {source_path.name} → archive/{file_type}/")
            return archive_path
        except Exception as e:
            logger.error(f"Fehler beim Archivieren von {source_path}: {e}")
            return None

    def compress_file(self, file_path: Path) -> Optional[Path]:
        """
        Komprimiert eine Datei mit gzip.

        Args:
            file_path: Pfad zur zu komprimierenden Datei

        Returns:
            Pfad zur komprimierten .gz Datei oder None bei Fehler
        """
        if not file_path.exists():
            logger.error(f"Datei existiert nicht: {file_path}")
            return None

        compressed_path = Path(str(file_path) + ".gz")

        try:
            with open(file_path, "rb") as f_in:
                with gzip.open(compressed_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Original löschen nach erfolgreicher Kompression
            file_path.unlink()

            original_size = file_path.stat().st_size if file_path.exists() else 0
            compressed_size = compressed_path.stat().st_size

            logger.info(f"Datei komprimiert: {file_path.name} "
                       f"({original_size} → {compressed_size} Bytes)")

            return compressed_path
        except Exception as e:
            logger.error(f"Fehler beim Komprimieren von {file_path}: {e}")
            return None

    def decompress_file(self, compressed_path: Path) -> Optional[Path]:
        """
        Dekomprimiert eine .gz Datei.

        Args:
            compressed_path: Pfad zur .gz Datei

        Returns:
            Pfad zur dekomprimierten Datei oder None bei Fehler
        """
        if not compressed_path.exists() or not str(compressed_path).endswith(".gz"):
            logger.error(f"Ungültige komprimierte Datei: {compressed_path}")
            return None

        # Entferne .gz Extension
        decompressed_path = Path(str(compressed_path)[:-3])

        try:
            with gzip.open(compressed_path, "rb") as f_in:
                with open(decompressed_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            logger.info(f"Datei dekomprimiert: {compressed_path.name}")
            return decompressed_path
        except Exception as e:
            logger.error(f"Fehler beim Dekomprimieren von {compressed_path}: {e}")
            return None

    def find_old_archives(self, user_id: int, days: int = 90) -> List[Path]:
        """
        Findet alle Archive die älter als X Tage sind und nicht komprimiert.

        Args:
            user_id: Telegram Benutzer-ID
            days: Alter in Tagen

        Returns:
            Liste von Pfaden zu alten, unkomprimierten Archiven
        """
        user_dir = self.get_user_dir(user_id)
        archive_dir = user_dir / "archive"

        if not archive_dir.exists():
            return []

        cutoff_date = datetime.now() - timedelta(days=days)
        old_files = []

        # Durchsuche alle Archive-Unterordner
        for file_type in ["daily", "weekly", "monthly"]:
            type_dir = archive_dir / file_type
            if not type_dir.exists():
                continue

            # Nur .md Dateien (keine .gz)
            for file_path in type_dir.glob("*.md"):
                # Prüfe Änderungsdatum
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                if mtime < cutoff_date:
                    old_files.append(file_path)

        return old_files

    def get_structure_stats(self, user_id: int) -> Dict:
        """
        Gibt Statistiken über die Dateistruktur zurück.

        Args:
            user_id: Telegram Benutzer-ID

        Returns:
            Dictionary mit Statistiken
        """
        user_dir = self.get_user_dir(user_id)

        if not user_dir.exists():
            return {"exists": False}

        stats = {
            "exists": True,
            "user_id": user_id,
            "daily_files": len(list((user_dir / "daily").glob("*.md"))) if (user_dir / "daily").exists() else 0,
            "weekly_files": len(list((user_dir / "weekly").glob("*.md"))) if (user_dir / "weekly").exists() else 0,
            "monthly_files": len(list((user_dir / "monthly").glob("*.md"))) if (user_dir / "monthly").exists() else 0,
            "archived_files": 0,
            "compressed_files": 0,
            "total_size_bytes": 0
        }

        # Zähle archivierte Dateien
        archive_dir = user_dir / "archive"
        if archive_dir.exists():
            stats["archived_files"] = len(list(archive_dir.rglob("*.md")))
            stats["compressed_files"] = len(list(archive_dir.rglob("*.gz")))

        # Berechne Gesamtgröße
        for file_path in user_dir.rglob("*"):
            if file_path.is_file():
                stats["total_size_bytes"] += file_path.stat().st_size

        stats["total_size_mb"] = round(stats["total_size_bytes"] / (1024 * 1024), 2)

        return stats

    def is_v2_structure(self, user_id: int) -> bool:
        """
        Prüft ob ein User bereits die V2 Struktur hat.

        Args:
            user_id: Telegram Benutzer-ID

        Returns:
            True wenn V2 Struktur existiert
        """
        user_dir = self.get_user_dir(user_id)

        # Prüfe ob daily/ Ordner existiert (charakteristisch für V2)
        return (user_dir / "daily").exists()
