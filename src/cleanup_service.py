"""
Cleanup Service für Memory 2.0

Automatische Bereinigung und Archivierung von Memory-Dateien:
- T+1: Soft Trim unwichtiger Details
- T+7: Weekly Summary erstellen, Tagesdateien archivieren
- T+30: Monthly Summary erstellen, Wochen archivieren
- T+90: Archive komprimieren
- T+365: Yearly Summary erstellen
"""

import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from .file_structure import FileStructureManager
from .memory_manager_v2 import MemoryManagerV2
from .importance_scorer import ImportanceScorer
from .summarizer import Summarizer

logger = logging.getLogger(__name__)


class CleanupService:
    """
    Automatischer Cleanup-Service für Memory 2.0.

    Läuft täglich um 04:00 Uhr via Cronjob.
    """

    # Konfiguration
    SOFT_TRIM_AFTER_DAYS = 1
    WEEKLY_SUMMARY_AFTER_DAYS = 7
    MONTHLY_SUMMARY_AFTER_DAYS = 30
    ARCHIVE_COMPRESSION_AFTER_DAYS = 90
    YEARLY_SUMMARY_AFTER_DAYS = 365

    # Schutzmaßnahmen
    PROTECTED_RECENT_DAYS = 7  # Letzte 7 Tage nie bereinigen
    MAX_FILE_SIZE_MB = 5  # Größen-Trigger
    MAX_DAILY_FOLDER_SIZE_MB = 20

    def __init__(self, llm_client, data_dir: str = "/media/xray/NEU/Code/Crowdbot/data"):
        """
        Initialisiert den Cleanup Service.

        Args:
            llm_client: LLM Client für Zusammenfassungen
            data_dir: Basisverzeichnis für Benutzerdaten
        """
        self.file_structure = FileStructureManager(data_dir)
        self.memory_manager = MemoryManagerV2(data_dir)
        self.scorer = ImportanceScorer(llm_client)
        self.summarizer = Summarizer(llm_client, self.scorer)
        self.llm_client = llm_client

    def run_daily_cleanup(self, user_ids: List[int] = None) -> Dict:
        """
        Führt täglichen Cleanup für alle oder spezifische User durch.

        Args:
            user_ids: Liste von User-IDs (None = alle User)

        Returns:
            Dictionary mit Cleanup-Statistiken
        """
        logger.info("=== Starte täglichen Memory-Cleanup ===")

        stats = {
            "processed_users": 0,
            "soft_trimmed_files": 0,
            "weekly_summaries_created": 0,
            "monthly_summaries_created": 0,
            "yearly_summaries_created": 0,
            "files_archived": 0,
            "files_compressed": 0,
            "errors": 0
        }

        # Bestimme User-Liste
        if user_ids is None:
            users_dir = self.file_structure.users_dir
            if not users_dir.exists():
                logger.warning("Kein Users-Verzeichnis gefunden")
                return stats

            user_ids = [int(d.name) for d in users_dir.iterdir()
                       if d.is_dir() and d.name.isdigit()]

        logger.info(f"Verarbeite {len(user_ids)} User")

        # Verarbeite jeden User
        for user_id in user_ids:
            try:
                user_stats = self._cleanup_user(user_id)

                stats["processed_users"] += 1
                stats["soft_trimmed_files"] += user_stats.get("soft_trimmed", 0)
                stats["weekly_summaries_created"] += user_stats.get("weekly_summaries", 0)
                stats["monthly_summaries_created"] += user_stats.get("monthly_summaries", 0)
                stats["yearly_summaries_created"] += user_stats.get("yearly_summaries", 0)
                stats["files_archived"] += user_stats.get("archived", 0)
                stats["files_compressed"] += user_stats.get("compressed", 0)

            except Exception as e:
                logger.error(f"Fehler beim Cleanup für User {user_id}: {e}")
                stats["errors"] += 1

        logger.info(f"=== Cleanup abgeschlossen: {stats} ===")
        return stats

    def check_size_triggers(self, user_id: int) -> bool:
        """
        Prüft ob Größenlimits überschritten sind.

        Args:
            user_id: Telegram Benutzer-ID

        Returns:
            True wenn Cleanup getriggert werden sollte
        """
        stats = self.file_structure.get_structure_stats(user_id)

        if not stats["exists"]:
            return False

        total_size_mb = stats["total_size_mb"]
        user_dir = self.file_structure.get_user_dir(user_id)
        daily_dir = user_dir / "daily"

        if daily_dir.exists():
            daily_size = sum(f.stat().st_size for f in daily_dir.rglob("*") if f.is_file())
            daily_size_mb = daily_size / (1024 * 1024)
        else:
            daily_size_mb = 0

        # Prüfe Limits
        if total_size_mb > 100:  # 100 MB Gesamt-Limit
            logger.warning(f"User {user_id}: Gesamt-Limit überschritten ({total_size_mb:.2f} MB)")
            return True

        if daily_size_mb > self.MAX_DAILY_FOLDER_SIZE_MB:
            logger.warning(f"User {user_id}: Daily-Folder-Limit überschritten ({daily_size_mb:.2f} MB)")
            return True

        return False

    def emergency_cleanup(self, user_id: int) -> bool:
        """
        Führt Notfall-Cleanup bei Größenüberschreitung durch.

        Erzwingt Weekly Summary auch wenn < 7 Tage.

        Args:
            user_id: Telegram Benutzer-ID

        Returns:
            True wenn erfolgreich
        """
        logger.warning(f"Notfall-Cleanup für User {user_id}")

        # Hole alle Daily-Files
        daily_files = self.file_structure.list_daily_files(user_id)

        if len(daily_files) < 3:
            logger.info("Zu wenige Dateien für Emergency Cleanup")
            return False

        # Erstelle Weekly Summary aus den ältesten Dateien (auch wenn < 7 Tage)
        oldest_files = daily_files[-5:]  # Nimm die ältesten 5 Dateien

        # Bestimme Woche
        if oldest_files:
            first_date = datetime.strptime(oldest_files[0].stem, "%Y%m%d")
            week_number = first_date.isocalendar()[1]
            year = first_date.year

            output_path = self.file_structure.get_weekly_file_path(user_id, year, week_number)

            success = self.summarizer.create_weekly_summary(
                oldest_files,
                output_path,
                week_number,
                year
            )

            if success:
                # Archiviere Originale
                for file in oldest_files:
                    self.file_structure.archive_file(file, user_id, "daily")

                logger.info(f"Emergency Cleanup: {len(oldest_files)} Dateien archiviert")
                return True

        return False

    # Private Methoden

    def _cleanup_user(self, user_id: int) -> Dict:
        """Führt Cleanup für einen einzelnen User durch."""
        logger.debug(f"Cleanup für User {user_id}")

        stats = {
            "soft_trimmed": 0,
            "weekly_summaries": 0,
            "monthly_summaries": 0,
            "yearly_summaries": 0,
            "archived": 0,
            "compressed": 0
        }

        # Prüfe ob V2 Struktur existiert
        if not self.file_structure.is_v2_structure(user_id):
            logger.debug(f"User {user_id} hat keine V2 Struktur, überspringe")
            return stats

        # 1. Soft Trim (T+1)
        stats["soft_trimmed"] = self._run_soft_trim(user_id)

        # 2. Weekly Summaries (T+7)
        stats["weekly_summaries"], archived_daily = self._run_weekly_summaries(user_id)
        stats["archived"] += archived_daily

        # 3. Monthly Summaries (T+30)
        stats["monthly_summaries"], archived_weekly = self._run_monthly_summaries(user_id)
        stats["archived"] += archived_weekly

        # 4. Archive Compression (T+90)
        stats["compressed"] = self._run_archive_compression(user_id)

        # 5. Yearly Summaries (T+365)
        stats["yearly_summaries"] = self._run_yearly_summaries(user_id)

        # 6. Prüfe Größen-Trigger
        if self.check_size_triggers(user_id):
            self.emergency_cleanup(user_id)

        return stats

    def _run_soft_trim(self, user_id: int) -> int:
        """Führt Soft Trim auf alte Tagesdateien aus."""
        count = 0

        # Hole Tagesdateien die älter als SOFT_TRIM_AFTER_DAYS sind
        cutoff_date = datetime.now() - timedelta(days=self.SOFT_TRIM_AFTER_DAYS)
        protected_date = datetime.now() - timedelta(days=self.PROTECTED_RECENT_DAYS)

        daily_files = self.file_structure.list_daily_files(user_id)

        for daily_file in daily_files:
            try:
                file_date = datetime.strptime(daily_file.stem, "%Y%m%d")

                # Überspringe geschützte und zu neue Dateien
                if file_date > cutoff_date or file_date > protected_date:
                    continue

                # Prüfe ob bereits getrimmt (Datei < 2KB)
                if daily_file.stat().st_size < 2048:
                    continue

                # Soft Trim anwenden
                success = self.summarizer.soft_trim_daily_file(daily_file)
                if success:
                    count += 1

            except Exception as e:
                logger.error(f"Fehler bei Soft Trim für {daily_file.name}: {e}")
                continue

        if count > 0:
            logger.info(f"Soft Trim: {count} Dateien bearbeitet")

        return count

    def _run_weekly_summaries(self, user_id: int) -> tuple:
        """Erstellt Weekly Summaries für vollständige Wochen."""
        summaries_created = 0
        files_archived = 0

        # Hole alle Tagesdateien
        daily_files = self.file_structure.list_daily_files(user_id)

        if not daily_files:
            return 0, 0

        # Gruppiere nach Wochen
        weeks = {}
        for daily_file in daily_files:
            try:
                file_date = datetime.strptime(daily_file.stem, "%Y%m%d")
                week_key = (file_date.year, file_date.isocalendar()[1])

                if week_key not in weeks:
                    weeks[week_key] = []

                weeks[week_key].append((file_date, daily_file))

            except ValueError:
                continue

        # Verarbeite vollständige Wochen
        cutoff_date = datetime.now() - timedelta(days=self.WEEKLY_SUMMARY_AFTER_DAYS)
        protected_date = datetime.now() - timedelta(days=self.PROTECTED_RECENT_DAYS)

        for (year, week_num), week_files in weeks.items():
            # Prüfe ob Woche alt genug ist
            week_files.sort(key=lambda x: x[0])  # Sortiere nach Datum
            oldest_date = week_files[0][0]

            if oldest_date > cutoff_date or oldest_date > protected_date:
                continue

            # Prüfe ob mindestens 5 Tage vorhanden (meiste Wochen haben 7)
            if len(week_files) < 5:
                continue

            # Prüfe ob Weekly Summary bereits existiert
            output_path = self.file_structure.get_weekly_file_path(user_id, year, week_num)
            if output_path.exists():
                continue

            # Erstelle Summary
            file_paths = [f[1] for f in week_files]

            success = self.summarizer.create_weekly_summary(
                file_paths,
                output_path,
                week_num,
                year
            )

            if success:
                summaries_created += 1

                # Archiviere Original-Tagesdateien
                for _, daily_file in week_files:
                    archived = self.file_structure.archive_file(daily_file, user_id, "daily")
                    if archived:
                        files_archived += 1

        if summaries_created > 0:
            logger.info(f"Weekly Summaries: {summaries_created} erstellt, "
                       f"{files_archived} Dateien archiviert")

        return summaries_created, files_archived

    def _run_monthly_summaries(self, user_id: int) -> tuple:
        """Erstellt Monthly Summaries aus Weekly Summaries."""
        summaries_created = 0
        files_archived = 0

        user_dir = self.file_structure.get_user_dir(user_id)
        weekly_dir = user_dir / "weekly"

        if not weekly_dir.exists():
            return 0, 0

        # Gruppiere nach Monaten
        months = {}
        for weekly_file in weekly_dir.glob("*.md"):
            try:
                # Parse YYYY-WXX.md
                parts = weekly_file.stem.split("-W")
                year = int(parts[0])
                week_num = int(parts[1])

                # Bestimme Monat aus Wochennummer
                # (vereinfacht: Woche 1-4 = Monat 1, etc.)
                month = ((week_num - 1) // 4) + 1
                if month > 12:
                    month = 12

                month_key = (year, month)

                if month_key not in months:
                    months[month_key] = []

                months[month_key].append(weekly_file)

            except (ValueError, IndexError):
                continue

        # Verarbeite vollständige Monate
        cutoff_date = datetime.now() - timedelta(days=self.MONTHLY_SUMMARY_AFTER_DAYS)

        for (year, month), week_files in months.items():
            # Prüfe ob mindestens 4 Wochen vorhanden
            if len(week_files) < 4:
                continue

            # Prüfe ob alt genug
            first_day = datetime(year, month, 1)
            if first_day > cutoff_date:
                continue

            # Prüfe ob Monthly Summary bereits existiert
            output_path = self.file_structure.get_monthly_file_path(user_id, year, month)
            if output_path.exists():
                continue

            # Erstelle Summary
            success = self.summarizer.create_monthly_summary(
                week_files,
                output_path,
                month,
                year
            )

            if success:
                summaries_created += 1

                # Archiviere Weekly Files
                for weekly_file in week_files:
                    archived = self.file_structure.archive_file(weekly_file, user_id, "weekly")
                    if archived:
                        files_archived += 1

        if summaries_created > 0:
            logger.info(f"Monthly Summaries: {summaries_created} erstellt, "
                       f"{files_archived} Dateien archiviert")

        return summaries_created, files_archived

    def _run_archive_compression(self, user_id: int) -> int:
        """Komprimiert alte Archive."""
        count = 0

        # Finde alte Archive
        old_archives = self.file_structure.find_old_archives(
            user_id,
            days=self.ARCHIVE_COMPRESSION_AFTER_DAYS
        )

        for archive_file in old_archives:
            compressed = self.file_structure.compress_file(archive_file)
            if compressed:
                count += 1

        if count > 0:
            logger.info(f"Archive komprimiert: {count} Dateien")

        return count

    def _run_yearly_summaries(self, user_id: int) -> int:
        """Erstellt Yearly Summaries aus Monthly Summaries."""
        summaries_created = 0

        user_dir = self.file_structure.get_user_dir(user_id)
        monthly_dir = user_dir / "monthly"

        if not monthly_dir.exists():
            return 0

        # Gruppiere nach Jahren
        years = {}
        for monthly_file in monthly_dir.glob("*.md"):
            try:
                # Parse YYYY-MM.md
                year = int(monthly_file.stem.split("-")[0])

                if year not in years:
                    years[year] = []

                years[year].append(monthly_file)

            except (ValueError, IndexError):
                continue

        # Verarbeite vollständige Jahre
        current_year = datetime.now().year

        for year, month_files in years.items():
            # Nur abgeschlossene Jahre
            if year >= current_year:
                continue

            # Prüfe ob mindestens 10 Monate vorhanden
            if len(month_files) < 10:
                continue

            # Prüfe ob Yearly Summary bereits existiert
            yearly_dir = user_dir / "yearly"
            yearly_dir.mkdir(exist_ok=True)
            output_path = yearly_dir / f"{year}.md"

            if output_path.exists():
                continue

            # Erstelle Summary
            success = self.summarizer.create_yearly_summary(
                month_files,
                output_path,
                year
            )

            if success:
                summaries_created += 1

        if summaries_created > 0:
            logger.info(f"Yearly Summaries: {summaries_created} erstellt")

        return summaries_created
