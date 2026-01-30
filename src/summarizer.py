"""
Summarizer für Memory 2.0

Erstellt intelligente Zusammenfassungen von Konversationen:
- Soft Trim (T+1): Kürzt unwichtige Details
- Weekly Summary (T+7): Wochenzusammenfassung aus Tagesdateien
- Monthly Summary (T+30): Monatszusammenfassung aus Wochen
- Yearly Summary (T+365): Jahreszusammenfassung
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class Summarizer:
    """
    Erstellt Zusammenfassungen von Konversationen mit LLM.

    Progressive Verdichtung: Soft Trim → Weekly → Monthly → Yearly
    """

    # Prompt für Soft Trim (T+1)
    SOFT_TRIM_PROMPT = """Analysiere die folgende Tagesdatei und kürze unwichtige Details.

Tagesdatei:
{daily_content}

Wichtigkeits-Scores:
{importance_scores}

Regeln:
1. Behalte ALLE User-Fragen vollständig
2. Kürze Bot-Antworten bei Score 0-1 auf 1-2 Sätze Zusammenfassung
3. Entferne vollständige Search-Resultate, behalte nur "Fragte nach X"
4. Kürze Tool-Outputs > 500 Zeichen auf Head (200) + Tail (200)
5. Behalte wichtige Erkenntnisse (Score >= 5) vollständig

Antworte NUR mit der gekürzten Version der Tagesdatei im gleichen Markdown-Format."""

    # Prompt für Weekly Summary
    WEEKLY_SUMMARY_PROMPT = """Erstelle eine strukturierte Wochenzusammenfassung aus den folgenden Tagesdateien.

Zeitraum: {start_date} bis {end_date} (KW {week_number})

Tagesdateien:
{daily_files_content}

Erstelle eine Zusammenfassung mit folgender Struktur:

## Kalenderwoche {week_number} ({start_date} bis {end_date})

### Hauptthemen
- [Liste der 3-5 wichtigsten Themen]

### Wichtige Erkenntnisse & Entscheidungen
- [Projektentscheidungen, neue Erkenntnisse, strategische Überlegungen]

### Persönliche Ereignisse
- [Relevante persönliche Erlebnisse]

### Wiederkehrende Aktivitäten
- [Was wurde mehrfach gemacht/besprochen?]

### Kontext für spätere Referenz
- [Informationen die für zukünftige Gespräche relevant sein könnten]

Fokussiere auf Informationen mit hoher Wichtigkeit (Score >= 5).
Ignoriere einmalige Fakten-Anfragen (TV-Programm, Wetter, etc.).
Nutze Fließtext, KEIN Markdown (für TTS-Kompatibilität)."""

    # Prompt für Monthly Summary
    MONTHLY_SUMMARY_PROMPT = """Erstelle eine Monatszusammenfassung aus den folgenden Wochenzusammenfassungen.

Monat: {month_name} {year}

Wochenzusammenfassungen:
{weekly_summaries}

Erstelle eine Zusammenfassung mit folgender Struktur:

## {month_name} {year}

### Überblick
- [1-2 Sätze über den Monat]

### Schlüsselthemen
- [Top 3-5 Themen des Monats]

### Wichtige Meilensteine
- [Abgeschlossene Projekte, Entscheidungen, Erfolge]

### Entwicklungen & Trends
- [Was hat sich verändert? Neue Interessen? Fortschritte?]

### Essentials für Langzeitgedächtnis
- [Nur Score >= 7: Präferenzen, wichtige Erkenntnisse]

Nur das Wichtigste behalten. Keine temporären Fakten.
Nutze Fließtext, KEIN Markdown."""

    def __init__(self, llm_client, importance_scorer):
        """
        Initialisiert den Summarizer.

        Args:
            llm_client: LLM Client für Zusammenfassungen
            importance_scorer: ImportanceScorer für Wichtigkeitsbewertung
        """
        self.llm_client = llm_client
        self.scorer = importance_scorer

    def soft_trim_daily_file(self, file_path: Path,
                            importance_scores: Dict = None) -> bool:
        """
        Wendet Soft Trim auf eine Tagesdatei an (T+1).

        Kürzt unwichtige Details, behält Essentials.

        Args:
            file_path: Pfad zur Tagesdatei
            importance_scores: Dictionary mit Scores für Abschnitte

        Returns:
            True wenn erfolgreich
        """
        if not file_path.exists():
            logger.error(f"Datei nicht gefunden: {file_path}")
            return False

        if importance_scores is None:
            importance_scores = {}

        # Lese Original
        content = file_path.read_text(encoding="utf-8")

        logger.info(f"Soft Trim für {file_path.name} (Original: {len(content)} Zeichen)")

        try:
            # Erstelle Prompt
            scores_text = "\n".join([f"- {k}: Score {v['score']}"
                                    for k, v in importance_scores.items()])

            prompt = self.SOFT_TRIM_PROMPT.format(
                daily_content=content,
                importance_scores=scores_text or "Keine Scores verfügbar"
            )

            # LLM-Aufruf
            trimmed_content = self.llm_client.send_message(
                prompt,
                max_tokens=3000,
                temperature=0.3
            )

            # Entferne Markdown-Code-Blöcke falls vorhanden
            if "```markdown" in trimmed_content:
                trimmed_content = trimmed_content.split("```markdown")[1].split("```")[0]
            elif "```" in trimmed_content:
                trimmed_content = trimmed_content.split("```")[1].split("```")[0]

            trimmed_content = trimmed_content.strip()

            # Schreibe zurück
            file_path.write_text(trimmed_content, encoding="utf-8")

            saved_chars = len(content) - len(trimmed_content)
            logger.info(f"Soft Trim abgeschlossen: {saved_chars} Zeichen gespart "
                       f"({len(trimmed_content)} Zeichen verbleibend)")

            return True

        except Exception as e:
            logger.error(f"Fehler beim Soft Trim: {e}")
            return False

    def create_weekly_summary(self, daily_files: List[Path],
                             output_path: Path,
                             week_number: int,
                             year: int) -> bool:
        """
        Erstellt Wochenzusammenfassung aus Tagesdateien (T+7).

        Args:
            daily_files: Liste von Pfaden zu Tagesdateien
            output_path: Pfad für die Wochenzusammenfassung
            week_number: Kalenderwoche
            year: Jahr

        Returns:
            True wenn erfolgreich
        """
        if not daily_files:
            logger.warning("Keine Tagesdateien für Weekly Summary")
            return False

        logger.info(f"Erstelle Weekly Summary KW {week_number}/{year} "
                   f"aus {len(daily_files)} Tagesdateien")

        # Lese alle Tagesdateien
        daily_contents = []
        for daily_file in sorted(daily_files):
            try:
                content = daily_file.read_text(encoding="utf-8")
                date_str = datetime.strptime(daily_file.stem, "%Y%m%d").strftime("%d.%m.%Y")
                daily_contents.append(f"## {date_str}\n\n{content}\n\n---\n")
            except Exception as e:
                logger.error(f"Fehler beim Lesen von {daily_file.name}: {e}")
                continue

        if not daily_contents:
            logger.error("Keine lesbaren Tagesdateien")
            return False

        # Bestimme Zeitraum
        first_date = datetime.strptime(daily_files[0].stem, "%Y%m%d")
        last_date = datetime.strptime(daily_files[-1].stem, "%Y%m%d")
        start_date = first_date.strftime("%d.%m.%Y")
        end_date = last_date.strftime("%d.%m.%Y")

        try:
            # Erstelle Prompt
            prompt = self.WEEKLY_SUMMARY_PROMPT.format(
                start_date=start_date,
                end_date=end_date,
                week_number=week_number,
                daily_files_content="\n".join(daily_contents)
            )

            # LLM-Aufruf
            summary = self.llm_client.send_message(
                prompt,
                max_tokens=2000,
                temperature=0.4
            )

            # Bereinige Markdown
            summary = self._clean_markdown(summary)

            # Erstelle finale Zusammenfassung
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            final_content = f"""# Wochenzusammenfassung KW {week_number}/{year}

Erstellt: {timestamp}
Zeitraum: {start_date} bis {end_date}
Quellen: {len(daily_files)} Tagesdateien

---

{summary}

---

**Hinweis:** Dies ist eine automatisch generierte Zusammenfassung.
Vollständige Details sind in den archivierten Tagesdateien verfügbar.
"""

            # Schreibe Datei
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(final_content, encoding="utf-8")

            logger.info(f"Weekly Summary erstellt: {output_path.name}")
            return True

        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Weekly Summary: {e}")
            return False

    def create_monthly_summary(self, weekly_files: List[Path],
                              output_path: Path,
                              month: int,
                              year: int) -> bool:
        """
        Erstellt Monatszusammenfassung aus Wochenzusammenfassungen (T+30).

        Args:
            weekly_files: Liste von Pfaden zu Wochenzusammenfassungen
            output_path: Pfad für die Monatszusammenfassung
            month: Monat (1-12)
            year: Jahr

        Returns:
            True wenn erfolgreich
        """
        if not weekly_files:
            logger.warning("Keine Wochenzusammenfassungen für Monthly Summary")
            return False

        month_names = ["", "Januar", "Februar", "März", "April", "Mai", "Juni",
                      "Juli", "August", "September", "Oktober", "November", "Dezember"]
        month_name = month_names[month]

        logger.info(f"Erstelle Monthly Summary {month_name} {year} "
                   f"aus {len(weekly_files)} Wochenzusammenfassungen")

        # Lese alle Wochenzusammenfassungen
        weekly_contents = []
        for weekly_file in sorted(weekly_files):
            try:
                content = weekly_file.read_text(encoding="utf-8")
                weekly_contents.append(content)
            except Exception as e:
                logger.error(f"Fehler beim Lesen von {weekly_file.name}: {e}")
                continue

        if not weekly_contents:
            logger.error("Keine lesbaren Wochenzusammenfassungen")
            return False

        try:
            # Erstelle Prompt
            prompt = self.MONTHLY_SUMMARY_PROMPT.format(
                month_name=month_name,
                year=year,
                weekly_summaries="\n\n---\n\n".join(weekly_contents)
            )

            # LLM-Aufruf
            summary = self.llm_client.send_message(
                prompt,
                max_tokens=1500,
                temperature=0.4
            )

            # Bereinige Markdown
            summary = self._clean_markdown(summary)

            # Erstelle finale Zusammenfassung
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            final_content = f"""# Monatszusammenfassung {month_name} {year}

Erstellt: {timestamp}
Quellen: {len(weekly_files)} Wochenzusammenfassungen

---

{summary}

---

**Hinweis:** Dies ist eine stark verdichtete Zusammenfassung.
Details sind in den archivierten Wochenzusammenfassungen verfügbar.
"""

            # Schreibe Datei
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(final_content, encoding="utf-8")

            logger.info(f"Monthly Summary erstellt: {output_path.name}")
            return True

        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Monthly Summary: {e}")
            return False

    def create_yearly_summary(self, monthly_files: List[Path],
                             output_path: Path,
                             year: int) -> bool:
        """
        Erstellt Jahreszusammenfassung aus Monatszusammenfassungen (T+365).

        Args:
            monthly_files: Liste von Pfaden zu Monatszusammenfassungen
            output_path: Pfad für die Jahreszusammenfassung
            year: Jahr

        Returns:
            True wenn erfolgreich
        """
        # Vereinfachte Implementierung - kombiniert Monate
        if not monthly_files:
            logger.warning("Keine Monatszusammenfassungen für Yearly Summary")
            return False

        logger.info(f"Erstelle Yearly Summary {year} "
                   f"aus {len(monthly_files)} Monatszusammenfassungen")

        # Lese alle Monatszusammenfassungen
        monthly_contents = []
        for monthly_file in sorted(monthly_files):
            try:
                content = monthly_file.read_text(encoding="utf-8")
                monthly_contents.append(content)
            except Exception as e:
                logger.error(f"Fehler beim Lesen von {monthly_file.name}: {e}")
                continue

        if not monthly_contents:
            return False

        # Einfache Konkatenation für Yearly (kann später mit LLM verbessert werden)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        final_content = f"""# Jahreszusammenfassung {year}

Erstellt: {timestamp}
Quellen: {len(monthly_files)} Monatszusammenfassungen

---

## Monatsübersicht

{chr(10).join(monthly_contents)}

---

**Hinweis:** Vollständige Jahreszusammenfassung.
Dies repräsentiert die wichtigsten Ereignisse und Erkenntnisse des Jahres {year}.
"""

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(final_content, encoding="utf-8")

        logger.info(f"Yearly Summary erstellt: {output_path.name}")
        return True

    # Private Hilfsmethoden

    def _clean_markdown(self, text: str) -> str:
        """
        Entfernt Markdown-Formatierung für TTS-Kompatibilität.

        Args:
            text: Text mit Markdown

        Returns:
            Text ohne Markdown
        """
        import re

        # Entferne Code-Blöcke
        if "```" in text:
            text = re.sub(r"```[\s\S]*?```", "", text)

        # Entferne Markdown-Formatierung
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # Bold
        text = re.sub(r"\*(.+?)\*", r"\1", text)      # Italic
        text = re.sub(r"__(.+?)__", r"\1", text)      # Bold
        text = re.sub(r"_(.+?)_", r"\1", text)        # Italic
        text = re.sub(r"`(.+?)`", r"\1", text)        # Code
        text = re.sub(r"#+\s", "", text)              # Headers

        return text.strip()
