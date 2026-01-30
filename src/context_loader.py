"""
Context Loader für Memory 2.0

Intelligentes Laden von Memory-Kontext basierend auf User-Anfragen:
- Standard-Kontext: memory.md + letzte 3 Tage + preferences.md
- LLM-basierte Auswahl: Identifiziert relevante historische Dateien
- Token-Limit-Management: Lädt Dateien bis Max-Limit erreicht
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from .file_structure import FileStructureManager

logger = logging.getLogger(__name__)


class ContextLoader:
    """
    Lädt intelligenten Kontext für User-Anfragen.

    Kombiniert Standard-Dateien mit LLM-basierter historischer Auswahl.
    """

    # Maximale Token für Memory (50% des Context Windows)
    MAX_MEMORY_TOKENS_GLM4 = 64000  # GLM-4.7 hat 128k Context
    TOKEN_ESTIMATION_RATIO = 4  # 4 Zeichen ≈ 1 Token

    # LLM-Prompt für relevante Datei-Auswahl
    FILE_SELECTION_PROMPT = """Analysiere die User-Anfrage und bestimme welche historischen Memory-Dateien relevant sind.

User-Anfrage:
"{user_query}"

Verfügbare Dateien:
{available_files}

Kriterien:
1. Bezieht sich die Anfrage auf ein spezifisches Datum oder Ereignis?
2. Erwähnt die Anfrage ein Thema das in der Vergangenheit besprochen wurde?
3. Ist historischer Kontext notwendig um die Anfrage zu beantworten?
4. Gibt es Verweise auf frühere Gespräche?

Antworte NUR mit einem JSON-Array von Dateinamen (keine Erklärungen):
["daily/20260115.md", "weekly/2026-W04.md"]

Wenn KEIN historischer Kontext benötigt wird, antworte mit:
[]"""

    def __init__(self, llm_client, file_structure_manager: FileStructureManager):
        """
        Initialisiert den Context Loader.

        Args:
            llm_client: LLM Client für intelligente Auswahl
            file_structure_manager: FileStructureManager Instanz
        """
        self.llm_client = llm_client
        self.file_structure = file_structure_manager

    def load_context(self, user_id: int, user_query: str) -> Dict:
        """
        Lädt relevanten Kontext für eine User-Anfrage.

        Args:
            user_id: Telegram Benutzer-ID
            user_query: Die Anfrage des Users

        Returns:
            Dictionary mit:
            {
                "memory_index": "...",  # memory.md Inhalt
                "preferences": "...",   # preferences.md Inhalt
                "recent_days": [...],   # Liste von Tagesdatei-Inhalten
                "additional_context": [...],  # Historische Dateien
                "total_tokens": 12500,
                "files_loaded": ["memory.md", "daily/20260130.md", ...]
            }
        """
        logger.info(f"Lade Kontext für User {user_id}")

        context = {
            "memory_index": "",
            "preferences": "",
            "recent_days": [],
            "additional_context": [],
            "total_tokens": 0,
            "files_loaded": []
        }

        # 1. Standard-Kontext laden
        context = self._load_standard_context(user_id, context)

        # 2. Prüfe Token-Budget
        remaining_tokens = self.MAX_MEMORY_TOKENS_GLM4 - context["total_tokens"]

        if remaining_tokens < 1000:
            logger.warning("Token-Limit fast erreicht, überspringe historischen Kontext")
            return context

        # 3. LLM-basierte Auswahl historischer Dateien
        if user_query and len(user_query) > 10:  # Nur bei nicht-trivialen Anfragen
            historical_files = self._select_relevant_files(user_id, user_query)

            # 4. Lade historische Dateien bis Token-Limit
            context = self._load_historical_files(
                user_id,
                historical_files,
                context,
                remaining_tokens
            )

        logger.info(f"Kontext geladen: {len(context['files_loaded'])} Dateien, "
                   f"{context['total_tokens']} Tokens")

        return context

    def _load_standard_context(self, user_id: int, context: Dict) -> Dict:
        """
        Lädt Standard-Kontext (immer geladen).

        Standard:
        - memory.md (Master Index)
        - preferences.md
        - Letzte 3 Tagesdateien
        """
        files_loaded = []
        total_chars = 0

        # 1. memory.md
        memory_path = self.file_structure.get_memory_index_path(user_id)
        if memory_path.exists():
            content = memory_path.read_text(encoding="utf-8")
            context["memory_index"] = content
            total_chars += len(content)
            files_loaded.append("memory.md")
            logger.debug(f"Geladen: memory.md ({len(content)} Zeichen)")

        # 2. preferences.md
        prefs_path = self.file_structure.get_preferences_path(user_id)
        if prefs_path.exists():
            content = prefs_path.read_text(encoding="utf-8")
            context["preferences"] = content
            total_chars += len(content)
            files_loaded.append("important/preferences.md")
            logger.debug(f"Geladen: preferences.md ({len(content)} Zeichen)")

        # 3. Letzte 3 Tagesdateien
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)

        daily_files = self.file_structure.list_daily_files(
            user_id,
            start_date=start_date,
            end_date=end_date
        )

        for daily_file in daily_files[:3]:  # Max 3 neueste
            try:
                content = daily_file.read_text(encoding="utf-8")
                context["recent_days"].append({
                    "file": daily_file.name,
                    "content": content
                })
                total_chars += len(content)
                files_loaded.append(f"daily/{daily_file.name}")
                logger.debug(f"Geladen: {daily_file.name} ({len(content)} Zeichen)")

            except Exception as e:
                logger.error(f"Fehler beim Laden von {daily_file.name}: {e}")
                continue

        # Token-Schätzung
        context["total_tokens"] = total_chars // self.TOKEN_ESTIMATION_RATIO
        context["files_loaded"] = files_loaded

        return context

    def _select_relevant_files(self, user_id: int, user_query: str) -> List[str]:
        """
        Nutzt LLM um relevante historische Dateien zu identifizieren.

        Args:
            user_id: Telegram Benutzer-ID
            user_query: User-Anfrage

        Returns:
            Liste von relativen Dateipfaden (z.B. ["daily/20260115.md"])
        """
        # Sammle verfügbare Dateien
        user_dir = self.file_structure.get_user_dir(user_id)
        available_files = []

        # Daily files
        daily_dir = user_dir / "daily"
        if daily_dir.exists():
            for f in sorted(daily_dir.glob("*.md"), reverse=True)[:30]:  # Max 30 neueste
                date_str = datetime.strptime(f.stem, "%Y%m%d").strftime("%d.%m.%Y")
                available_files.append(f"daily/{f.name} ({date_str})")

        # Weekly files
        weekly_dir = user_dir / "weekly"
        if weekly_dir.exists():
            for f in sorted(weekly_dir.glob("*.md"), reverse=True)[:12]:  # Max 12 neueste
                available_files.append(f"weekly/{f.name}")

        # Monthly files
        monthly_dir = user_dir / "monthly"
        if monthly_dir.exists():
            for f in sorted(monthly_dir.glob("*.md"), reverse=True)[:6]:  # Max 6 neueste
                available_files.append(f"monthly/{f.name}")

        if not available_files:
            logger.debug("Keine historischen Dateien verfügbar")
            return []

        # Erstelle Prompt
        files_text = "\n".join([f"- {f}" for f in available_files])
        prompt = self.FILE_SELECTION_PROMPT.format(
            user_query=user_query,
            available_files=files_text
        )

        try:
            # LLM-Aufruf
            response = self.llm_client.send_message(
                prompt,
                max_tokens=500,
                temperature=0.2
            )

            # Parse JSON-Antwort
            response_text = response.strip()

            # Bereinige Markdown Code-Blöcke
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            selected_files = json.loads(response_text.strip())

            if not isinstance(selected_files, list):
                logger.warning(f"Ungültige LLM-Antwort: {response_text}")
                return []

            # Entferne Datum-Annotationen wenn vorhanden
            cleaned_files = []
            for f in selected_files:
                # Entferne " (DD.MM.YYYY)" falls vorhanden
                if " (" in f:
                    f = f.split(" (")[0]
                cleaned_files.append(f)

            logger.info(f"LLM wählte {len(cleaned_files)} relevante Dateien aus")
            return cleaned_files

        except json.JSONDecodeError as e:
            logger.error(f"Fehler beim Parsen der LLM-Antwort: {e}")
            return []
        except Exception as e:
            logger.error(f"Fehler bei LLM-Dateiauswahl: {e}")
            return []

    def _load_historical_files(self, user_id: int, file_list: List[str],
                               context: Dict, max_tokens: int) -> Dict:
        """
        Lädt historische Dateien bis Token-Limit erreicht.

        Args:
            user_id: Telegram Benutzer-ID
            file_list: Liste von relativen Dateipfaden
            context: Bisheriger Kontext
            max_tokens: Maximale zusätzliche Tokens

        Returns:
            Aktualisierter Kontext
        """
        user_dir = self.file_structure.get_user_dir(user_id)
        loaded_tokens = 0

        for rel_path in file_list:
            file_path = user_dir / rel_path

            if not file_path.exists():
                logger.warning(f"Datei nicht gefunden: {rel_path}")
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                estimated_tokens = len(content) // self.TOKEN_ESTIMATION_RATIO

                # Prüfe Token-Budget
                if loaded_tokens + estimated_tokens > max_tokens:
                    logger.info(f"Token-Limit erreicht, überspringe {rel_path}")
                    break

                # Füge zu Kontext hinzu
                context["additional_context"].append({
                    "file": rel_path,
                    "content": content
                })

                loaded_tokens += estimated_tokens
                context["files_loaded"].append(rel_path)
                context["total_tokens"] += estimated_tokens

                logger.debug(f"Geladen: {rel_path} ({len(content)} Zeichen)")

            except Exception as e:
                logger.error(f"Fehler beim Laden von {rel_path}: {e}")
                continue

        return context

    def format_context_for_llm(self, context: Dict) -> str:
        """
        Formatiert geladenen Kontext für LLM-Eingabe.

        Args:
            context: Kontext-Dictionary

        Returns:
            Formatierter String für LLM System-Prompt
        """
        parts = []

        # Memory Index
        if context["memory_index"]:
            parts.append("=== GEDÄCHTNIS-INDEX ===\n")
            parts.append(context["memory_index"])
            parts.append("\n")

        # Preferences
        if context["preferences"]:
            parts.append("=== PERSÖNLICHE PRÄFERENZEN ===\n")
            parts.append(context["preferences"])
            parts.append("\n")

        # Recent Days
        if context["recent_days"]:
            parts.append("=== LETZTE GESPRÄCHE ===\n")
            for day in context["recent_days"]:
                parts.append(f"--- {day['file']} ---\n")
                parts.append(day["content"])
                parts.append("\n")

        # Additional Historical Context
        if context["additional_context"]:
            parts.append("=== HISTORISCHER KONTEXT ===\n")
            for hist in context["additional_context"]:
                parts.append(f"--- {hist['file']} ---\n")
                parts.append(hist["content"])
                parts.append("\n")

        formatted = "\n".join(parts)

        logger.debug(f"Kontext formatiert: {len(formatted)} Zeichen, "
                    f"{len(parts)} Abschnitte")

        return formatted

    def get_context_stats(self, context: Dict) -> str:
        """
        Erstellt Human-readable Statistik über geladenen Kontext.

        Args:
            context: Kontext-Dictionary

        Returns:
            Statistik-String
        """
        return (
            f"Kontext-Statistik:\n"
            f"- Dateien geladen: {len(context['files_loaded'])}\n"
            f"- Tokens geschätzt: {context['total_tokens']:,}\n"
            f"- Recent Days: {len(context['recent_days'])}\n"
            f"- Historischer Kontext: {len(context['additional_context'])}\n"
            f"- Memory Index: {'Ja' if context['memory_index'] else 'Nein'}\n"
            f"- Preferences: {'Ja' if context['preferences'] else 'Nein'}"
        )
