"""
Web Import Tool für Crowdbot

Lädt Webseiten-Inhalte, extrahiert den Text und speichert ihn dauerhaft im Memory.
"""

import requests
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
import re

logger = logging.getLogger(__name__)


class WebImporter:
    """Importiert Webseiten-Inhalte ins dauerhafte Memory."""

    def __init__(self, data_dir: str = "/media/xray/NEU/Code/Crowdbot/data"):
        """
        Initialisiert den Web Importer.

        Args:
            data_dir: Basisverzeichnis für Benutzerdaten
        """
        self.data_dir = Path(data_dir)
        self.jina_reader_url = "https://r.jina.ai/"

    def _sanitize_filename(self, text: str, max_length: int = 50) -> str:
        """
        Erstellt einen sicheren Dateinamen aus Text.

        Args:
            text: Ursprungstext
            max_length: Maximale Länge

        Returns:
            Bereinigter Dateiname
        """
        # Nur alphanumerische Zeichen, Bindestriche und Unterstriche
        safe = re.sub(r'[^\w\s-]', '', text)
        # Leerzeichen durch Unterstriche
        safe = safe.replace(' ', '_')
        # Mehrfache Unterstriche reduzieren
        safe = re.sub(r'_+', '_', safe)
        # Länge begrenzen
        safe = safe[:max_length]
        # Sicherstellen dass es ein gültiger Dateiname ist
        safe = safe.strip('_-')
        return safe if safe else "imported_content"

    def _extract_title_from_content(self, content: str) -> str:
        """
        Versucht einen Titel aus dem Inhalt zu extrahieren.

        Args:
            content: Markdown-Content

        Returns:
            Extrahierter Titel oder "Imported Content"
        """
        lines = content.split('\n')
        for line in lines[:10]:  # Erste 10 Zeilen prüfen
            line = line.strip()
            # Suche nach Markdown-Header
            if line.startswith('#'):
                title = line.lstrip('#').strip()
                if title:
                    return title
            # Suche nach fett gedrucktem Text am Anfang
            if line.startswith('**') and line.endswith('**'):
                title = line.strip('*').strip()
                if title:
                    return title
            # Erste nicht-leere Zeile als Fallback
            if line and len(line) > 5:
                return line[:100]

        return "Imported Content"

    def fetch_url_content(self, url: str) -> Tuple[bool, str, Optional[str]]:
        """
        Lädt Inhalt einer URL über Jina Reader.

        Args:
            url: Die zu ladende URL

        Returns:
            Tuple von (success, content/error_message, title)
        """
        try:
            # Füge https:// hinzu wenn kein Schema vorhanden
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            # Nutze Jina Reader für sauberen Markdown-Content
            jina_url = f"{self.jina_reader_url}{url}"

            logger.info(f"Fetching URL via Jina Reader: {url}")

            response = requests.get(
                jina_url,
                timeout=30,
                headers={
                    'User-Agent': 'Crowdbot Web Importer/1.0'
                }
            )

            if response.status_code != 200:
                return False, f"HTTP Fehler {response.status_code}: {response.reason}", None

            content = response.text

            # Entferne mögliche HTML-Reste (falls Jina doch welche zurückgibt)
            # Jina sollte bereits Markdown liefern, aber zur Sicherheit
            content = self._clean_content(content)

            if not content or len(content) < 50:
                return False, "Inhalt zu kurz oder leer", None

            # Extrahiere Titel
            title = self._extract_title_from_content(content)

            logger.info(f"Successfully fetched content from {url} ({len(content)} chars)")

            return True, content, title

        except requests.exceptions.Timeout:
            return False, "Timeout beim Laden der URL (30 Sekunden überschritten)", None
        except requests.exceptions.ConnectionError:
            return False, "Verbindungsfehler - URL nicht erreichbar", None
        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}")
            return False, f"Fehler beim Laden: {str(e)}", None

    def _clean_content(self, content: str) -> str:
        """
        Bereinigt Content von HTML-Resten und unerwünschten Zeichen.

        Args:
            content: Roher Content

        Returns:
            Bereinigter Content
        """
        # Entferne HTML-Tags falls vorhanden
        content = re.sub(r'<[^>]+>', '', content)

        # Entferne übermäßige Leerzeilen (mehr als 2 aufeinander)
        content = re.sub(r'\n{3,}', '\n\n', content)

        # Entferne führende/trailing Whitespace
        content = content.strip()

        return content

    def save_to_memory(
        self,
        user_id: int,
        content: str,
        source_url: str,
        title: Optional[str] = None,
        custom_filename: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Speichert Webseiten-Content dauerhaft im important/ Verzeichnis.

        Args:
            user_id: Telegram User-ID
            content: Der zu speichernde Inhalt
            source_url: Ursprungs-URL
            title: Optionaler Titel
            custom_filename: Optionaler benutzerdefinierter Dateiname

        Returns:
            Tuple von (success, filepath/error_message)
        """
        try:
            user_dir = self.data_dir / "users" / str(user_id)
            important_dir = user_dir / "important"

            # Stelle sicher dass Verzeichnis existiert
            important_dir.mkdir(parents=True, exist_ok=True)

            # Erstelle Dateiname
            if custom_filename:
                filename = self._sanitize_filename(custom_filename)
            elif title:
                filename = self._sanitize_filename(title)
            else:
                # Nutze Domain aus URL als Fallback
                domain = re.search(r'https?://([^/]+)', source_url)
                if domain:
                    filename = self._sanitize_filename(domain.group(1))
                else:
                    filename = "imported_content"

            # Füge Timestamp hinzu um Überschreibungen zu vermeiden
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename}_{timestamp}.md"

            filepath = important_dir / filename

            # Erstelle formattierten Inhalt mit Metadaten
            formatted_content = f"# {title or 'Imported Content'}\n\n"
            formatted_content += f"**Quelle:** {source_url}\n"
            formatted_content += f"**Importiert:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            formatted_content += f"**Gespeichert in:** important/{filename}\n\n"
            formatted_content += "---\n\n"
            formatted_content += content
            formatted_content += "\n\n---\n\n"
            formatted_content += "**Hinweis:** Diese Datei ist dauerhaft gespeichert und wird nie automatisch gelöscht.\n"

            # Speichere Datei
            filepath.write_text(formatted_content, encoding='utf-8')

            logger.info(f"Saved web content to {filepath}")

            return True, str(filepath.relative_to(user_dir))

        except Exception as e:
            logger.error(f"Error saving content to memory: {e}")
            return False, f"Fehler beim Speichern: {str(e)}"

    def import_url(
        self,
        user_id: int,
        url: str,
        custom_filename: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Kompletter Import-Workflow: Laden + Speichern.

        Args:
            user_id: Telegram User-ID
            url: Die zu importierende URL
            custom_filename: Optionaler Dateiname

        Returns:
            Tuple von (success, message)
        """
        # 1. Content laden
        success, content_or_error, title = self.fetch_url_content(url)

        if not success:
            return False, f"Fehler beim Laden der URL: {content_or_error}"

        content = content_or_error

        # 2. In Memory speichern
        success, filepath_or_error = self.save_to_memory(
            user_id=user_id,
            content=content,
            source_url=url,
            title=title,
            custom_filename=custom_filename
        )

        if not success:
            return False, filepath_or_error

        # 3. Erfolgs-Nachricht
        message = f"Webseite erfolgreich importiert!\n\n"
        message += f"Titel: {title}\n"
        message += f"Gespeichert als: {filepath_or_error}\n"
        message += f"Größe: {len(content)} Zeichen\n\n"
        message += "Der Inhalt ist jetzt dauerhaft in deinem Memory gespeichert "
        message += "und wird bei zukünftigen Anfragen automatisch berücksichtigt."

        return True, message


# Hilfsfunktion für Bot-Integration
def import_web_page(user_id: int, url: str, custom_filename: Optional[str] = None) -> str:
    """
    Bot-freundliche Funktion zum Importieren einer Webseite.

    Args:
        user_id: Telegram User-ID
        url: Die zu importierende URL
        custom_filename: Optionaler Dateiname

    Returns:
        Erfolgs- oder Fehlermeldung
    """
    importer = WebImporter()
    success, message = importer.import_url(user_id, url, custom_filename)

    return message
