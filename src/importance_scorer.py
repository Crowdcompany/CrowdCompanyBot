"""
Importance Scorer für Memory 2.0

Bewertet die Wichtigkeit von Konversationen mithilfe von LLM-basierter Analyse.
Score-System: 0-10 Punkte basierend auf Häufigkeit, Recency, expliziter Wichtigkeit und persönlicher Relevanz.
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ImportanceScorer:
    """
    Bewertet Konversationen nach Wichtigkeit für das Langzeitgedächtnis.

    Score-Faktoren:
    - Häufigkeit (0-3 Punkte): Wie oft wurde das Thema erwähnt
    - Recency (0-2 Punkte): Wie aktuell ist die Information
    - Explizite Wichtigkeit (0-2 Punkte): Hat User es als wichtig markiert
    - Persönliche Relevanz (0-3 Punkte): Präferenzen, Abneigungen, Ziele
    """

    # Keywords für explizite Wichtigkeit
    IMPORTANCE_KEYWORDS = [
        "merke dir", "wichtig", "entscheidend", "nie vergessen",
        "projektentscheidung", "strategie", "plan", "ziel",
        "erinnere mich", "denk dran", "notiere"
    ]

    # Keywords für temporäre Fakten (Score = 0-1)
    TEMPORARY_KEYWORDS = [
        "tv-programm", "fernsehprogramm", "tv heute", "läuft heute",
        "wetter", "wettervorhersage", "temperatur heute",
        "nachrichten heute", "aktuell", "gerade", "jetzt"
    ]

    # Prompt-Template für LLM
    SCORING_PROMPT_TEMPLATE = """Analysiere die folgende Konversation und bewerte ihre Wichtigkeit für das Langzeitgedächtnis.

Konversation:
{conversation_snippet}

Kontext:
- Bisherige Erwähnungen dieses Themas: {frequency_count}
- Zeitpunkt: {timestamp}
- Tage seit erster Erwähnung: {days_since_first_mention}

Bewerte anhand dieser Kriterien:

1. Häufigkeit (0-3 Punkte):
   - Wie oft wurde dieses Thema bereits erwähnt?
   - Ist es ein wiederkehrendes Interesse?
   - 3 Punkte: Täglich oder wöchentlich erwähnt
   - 2 Punkte: Mehrfach im Monat
   - 1 Punkt: 2-3 Mal erwähnt
   - 0 Punkte: Nur einmal erwähnt

2. Recency (0-2 Punkte):
   - Wie aktuell ist die Information?
   - Wird sie bald veraltet sein?
   - 2 Punkte: In den letzten 7 Tagen erwähnt
   - 1 Punkt: In den letzten 30 Tagen
   - 0 Punkte: Älter als 30 Tage

3. Explizite Wichtigkeit (0-2 Punkte):
   - Hat der Nutzer die Wichtigkeit betont?
   - Wurde mehrfach nachgefragt?
   - 2 Punkte: Explizit als wichtig markiert
   - 1 Punkt: Mehrfach nachgefragt
   - 0 Punkte: Keine Marker

4. Persönliche Relevanz (0-3 Punkte):
   - Betrifft es persönliche Präferenzen oder Eigenschaften?
   - Ist es eine strategische Entscheidung?
   - Hat es langfristige Bedeutung?
   - 3 Punkte: Präferenzen, Abneigungen, Ziele
   - 2 Punkte: Projektentscheidungen, Strategien
   - 1 Punkt: Persönliche Ereignisse
   - 0 Punkte: Allgemeine Fakten-Anfragen

Antworte NUR mit einem JSON-Objekt in folgendem Format (keine zusätzlichen Erklärungen):
{{
  "score": 7,
  "frequency_points": 2,
  "recency_points": 2,
  "explicit_points": 1,
  "relevance_points": 2,
  "reasoning": "Kurze Begründung der Bewertung",
  "retention_recommendation": "Behalten in Wochen-/Monatszusammenfassungen"
}}"""

    def __init__(self, llm_client):
        """
        Initialisiert den Importance Scorer.

        Args:
            llm_client: LLM Client für Bewertungen (GLM-4.7)
        """
        self.llm_client = llm_client

    def score_conversation(self, snippet: str, context: Dict = None) -> Dict:
        """
        Bewertet einen Konversationsabschnitt.

        Args:
            snippet: Der zu bewertende Gesprächsabschnitt
            context: Zusätzlicher Kontext (frequency_count, timestamp, etc.)

        Returns:
            Dictionary mit Score-Details:
            {
                "score": 7,
                "frequency_points": 2,
                "recency_points": 2,
                "explicit_points": 1,
                "relevance_points": 2,
                "reasoning": "...",
                "retention_recommendation": "..."
            }
        """
        if context is None:
            context = {}

        # Hole Kontext-Werte oder setze Defaults
        frequency_count = context.get("frequency_count", 0)
        timestamp = context.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        days_since_first = context.get("days_since_first_mention", 0)

        # Schnelle Heuristik-Prüfung für temporäre Fakten
        if self._is_temporary_fact(snippet):
            logger.debug("Temporäre Fakten erkannt, Score = 0")
            return {
                "score": 0,
                "frequency_points": 0,
                "recency_points": 0,
                "explicit_points": 0,
                "relevance_points": 0,
                "reasoning": "Temporäre Fakten-Anfrage (TV, Wetter, etc.)",
                "retention_recommendation": "Nach 24h entfernen"
            }

        # LLM-basierte Bewertung
        try:
            llm_score = self._score_with_llm(snippet, frequency_count, timestamp, days_since_first)

            # Validiere Score
            if not self._validate_score(llm_score):
                logger.warning("Ungültiger LLM-Score, verwende Fallback")
                return self._fallback_score(snippet, context)

            return llm_score

        except Exception as e:
            logger.error(f"Fehler bei LLM-Bewertung: {e}")
            return self._fallback_score(snippet, context)

    def calculate_frequency_score(self, topic: str, history: List[str]) -> int:
        """
        Berechnet Häufigkeits-Score (0-3 Punkte).

        Args:
            topic: Thema/Keyword
            history: Liste von vorherigen Gesprächen

        Returns:
            0-3 Punkte
        """
        if not history:
            return 0

        # Zähle Erwähnungen
        count = sum(1 for msg in history if topic.lower() in msg.lower())

        # Score basierend auf Häufigkeit
        if count >= 10:  # Täglich/wöchentlich
            return 3
        elif count >= 4:  # Mehrfach im Monat
            return 2
        elif count >= 2:  # 2-3 Mal
            return 1
        else:  # Nur einmal
            return 0

    def detect_explicit_markers(self, text: str) -> int:
        """
        Erkennt Keywords wie "wichtig", "merke dir" (0-2 Punkte).

        Args:
            text: Zu analysierender Text

        Returns:
            0-2 Punkte
        """
        text_lower = text.lower()

        # Zähle gefundene Keywords
        found_keywords = [kw for kw in self.IMPORTANCE_KEYWORDS if kw in text_lower]

        if len(found_keywords) >= 2:  # Mehrere Marker
            return 2
        elif len(found_keywords) == 1:  # Ein Marker
            return 1
        else:
            return 0

    def get_retention_strategy(self, score: int) -> str:
        """
        Gibt Empfehlung für Retention basierend auf Score.

        Args:
            score: Wichtigkeits-Score (0-10)

        Returns:
            Retention-Empfehlung als String
        """
        if score >= 8:
            return "Persistent in memory.md + important/preferences.md"
        elif score >= 5:
            return "Behalten in Wochen-/Monatszusammenfassungen"
        elif score >= 2:
            return "Nach 7 Tagen archivieren"
        else:
            return "Nach 24h entfernen"

    # Private Hilfsmethoden

    def _score_with_llm(self, snippet: str, frequency: int,
                       timestamp: str, days_since: int) -> Dict:
        """Verwendet LLM für Bewertung."""

        # Erstelle Prompt
        prompt = self.SCORING_PROMPT_TEMPLATE.format(
            conversation_snippet=snippet,
            frequency_count=frequency,
            timestamp=timestamp,
            days_since_first_mention=days_since
        )

        # LLM-Aufruf
        response = self.llm_client.send_message(
            prompt,
            max_tokens=500,
            temperature=0.3  # Niedrig für konsistente Bewertungen
        )

        # Parse JSON-Antwort
        try:
            # Extrahiere JSON aus Antwort (könnte Markdown-Code-Blöcke enthalten)
            response_text = response.strip()

            # Entferne Markdown Code-Blöcke falls vorhanden
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            score_data = json.loads(response_text.strip())

            logger.debug(f"LLM-Score: {score_data['score']} - {score_data['reasoning']}")
            return score_data

        except json.JSONDecodeError as e:
            logger.error(f"Fehler beim Parsen der LLM-Antwort: {e}\nAntwort: {response}")
            raise

    def _fallback_score(self, snippet: str, context: Dict) -> Dict:
        """
        Regelbasierter Fallback wenn LLM nicht verfügbar.

        Verwendet einfache Heuristiken statt LLM-Analyse.
        """
        # Häufigkeit
        frequency_points = 0
        if context.get("frequency_count", 0) >= 10:
            frequency_points = 3
        elif context.get("frequency_count", 0) >= 4:
            frequency_points = 2
        elif context.get("frequency_count", 0) >= 2:
            frequency_points = 1

        # Recency
        recency_points = 0
        days_since = context.get("days_since_first_mention", 999)
        if days_since <= 7:
            recency_points = 2
        elif days_since <= 30:
            recency_points = 1

        # Explizite Marker
        explicit_points = self.detect_explicit_markers(snippet)

        # Persönliche Relevanz (einfache Heuristik)
        relevance_points = 0
        snippet_lower = snippet.lower()

        # Präferenzen
        if any(kw in snippet_lower for kw in ["mag nicht", "interessiere mich nicht",
                                                "liebe", "hasse", "bevorzuge"]):
            relevance_points = 3
        # Projekte/Ziele
        elif any(kw in snippet_lower for kw in ["projekt", "ziel", "plan",
                                                  "vorhabe", "möchte"]):
            relevance_points = 2
        # Persönliches
        elif any(kw in snippet_lower for kw in ["ich", "mein", "meine"]):
            relevance_points = 1

        total_score = frequency_points + recency_points + explicit_points + relevance_points

        return {
            "score": total_score,
            "frequency_points": frequency_points,
            "recency_points": recency_points,
            "explicit_points": explicit_points,
            "relevance_points": relevance_points,
            "reasoning": "Regelbasierter Fallback (LLM nicht verfügbar)",
            "retention_recommendation": self.get_retention_strategy(total_score)
        }

    def _is_temporary_fact(self, text: str) -> bool:
        """Prüft ob es sich um temporäre Fakten handelt."""
        text_lower = text.lower()

        return any(kw in text_lower for kw in self.TEMPORARY_KEYWORDS)

    def _validate_score(self, score_data: Dict) -> bool:
        """Validiert LLM-Score-Ausgabe."""
        required_fields = ["score", "frequency_points", "recency_points",
                          "explicit_points", "relevance_points",
                          "reasoning", "retention_recommendation"]

        # Prüfe ob alle Felder vorhanden
        if not all(field in score_data for field in required_fields):
            return False

        # Prüfe Wertebereiche
        if not (0 <= score_data["score"] <= 10):
            return False
        if not (0 <= score_data["frequency_points"] <= 3):
            return False
        if not (0 <= score_data["recency_points"] <= 2):
            return False
        if not (0 <= score_data["explicit_points"] <= 2):
            return False
        if not (0 <= score_data["relevance_points"] <= 3):
            return False

        return True


class TopicTracker:
    """
    Verfolgt Themen über Zeit für Häufigkeits-Analyse.

    Speichert wann und wie oft Themen erwähnt wurden.
    """

    def __init__(self, file_structure_manager):
        """
        Args:
            file_structure_manager: FileStructureManager Instanz
        """
        self.file_structure = file_structure_manager

    def track_topic(self, user_id: int, topic: str, timestamp: datetime = None):
        """
        Registriert eine Themen-Erwähnung.

        Args:
            user_id: Telegram Benutzer-ID
            topic: Thema/Keyword
            timestamp: Zeitpunkt (default: jetzt)
        """
        # TODO: Implementierung für Topic-Tracking
        # Könnte in separate topics.json Datei schreiben
        pass

    def get_topic_frequency(self, user_id: int, topic: str,
                           since: datetime = None) -> int:
        """
        Gibt Anzahl der Erwähnungen eines Themas zurück.

        Args:
            user_id: Telegram Benutzer-ID
            topic: Thema/Keyword
            since: Nur Erwähnungen seit diesem Datum zählen

        Returns:
            Anzahl der Erwähnungen
        """
        # TODO: Implementierung
        # Durchsuche Tagesdateien und zähle Erwähnungen
        return 0

    def get_first_mention_date(self, user_id: int, topic: str) -> Optional[datetime]:
        """
        Gibt Datum der ersten Erwähnung zurück.

        Args:
            user_id: Telegram Benutzer-ID
            topic: Thema/Keyword

        Returns:
            Datetime der ersten Erwähnung oder None
        """
        # TODO: Implementierung
        return None
