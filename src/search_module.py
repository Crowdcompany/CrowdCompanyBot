"""
Search Module für Crowdbot

Verwendet Jina AI für Web-Suche und Deep Research:
- Jina Reader für einzelne URLs
- Jina Deep Research für komplexe Fragen
"""

import requests
from typing import Optional, List
import re


class SearchModule:
    """Modul für Internet-Suche und Web-Scraping."""

    def __init__(
        self,
        jina_reader_url: str = "https://r.jina.ai",
        jina_proxy_url: str = "https://jinaproxy.ccpn.cc"
    ):
        """
        Initialisiert das Search Module.

        Args:
            jina_reader_url: URL für Jina Reader
            jina_proxy_url: URL für Jina Deep Search Proxy
        """
        self.jina_reader_url = jina_reader_url
        self.jina_proxy_url = jina_proxy_url

    def is_url(self, text: str) -> bool:
        """
        Prüft, ob ein Text eine URL ist.

        Args:
            text: Zu prüfender Text

        Returns:
            True wenn es eine URL ist
        """
        url_pattern = re.compile(
            r'^https?://'  # http:// oder https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # Domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # Port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )
        return url_pattern.match(text) is not None

    def fetch_url(self, url: str, timeout: int = 10) -> Optional[str]:
        """
        Liest eine URL mit Jina Reader und gibt den Markdown-Inhalt zurück.

        Args:
            url: Die zu lesende URL
            timeout: Timeout in Sekunden

        Returns:
            Markdown-Inhalt der URL oder None bei Fehler
        """
        # Stelle sicher, dass die URL ein Schema hat
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        try:
            # Jina Reader URL
            reader_url = f"{self.jina_reader_url}/{url}"

            response = requests.get(reader_url, timeout=timeout)

            if response.status_code == 200:
                return response.text
            else:
                return f"Fehler: HTTP {response.status_code}"

        except Exception as e:
            return f"Fehler: {e}"

    def deep_search(
        self,
        query: str,
        max_results: int = 10,
        max_tokens: int = 4000
    ) -> Optional[str]:
        """
        Führt eine Deep Research mit dem Jina-Proxy durch.

        Args:
            query: Die Suchanfrage
            max_results: Maximale Anzahl der Quellen
            max_tokens: Maximale Token in der Antwort

        Returns:
            Die Suchergebnisse als Text oder None bei Fehler
        """
        try:
            url = f"{self.jina_proxy_url}/v1/chat/completions"

            payload = {
                "model": "jina-deepsearch-v1",
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"Führe eine gründliche Recherche zu folgender Frage durch: {query}\n\n"
                            f"Erstelle eine detaillierte Analyse mit:\n"
                            f"- Hintergrundkontext\n"
                            f"- Relevante Fakten und Informationen\n"
                            f"- Konkrete Beispiele\n"
                            f"- Quellenangaben\n\n"
                            f"Nutze alle verfügbaren Quellen und sei so detailliert wie möglich."
                        )
                    }
                ],
                "max_tokens": max_tokens,
                "budget_tokens": 8000,
                "max_returned_urls": max_results,
                "reasoning_effort": "high",
                "stream": False
            }

            response = requests.post(url, json=payload, timeout=120)

            if response.status_code == 200:
                data = response.json()

                if data.get("choices") and len(data["choices"]) > 0:
                    content = data["choices"][0].get("message", {}).get("content")
                    return content
                else:
                    return "Keine Ergebnisse erhalten"

            else:
                return f"Fehler: HTTP {response.status_code}"

        except Exception as e:
            return f"Fehler: {e}"

    def _make_tts_compatible(self, text: str) -> str:
        """
        Wandelt Markdown-Text in TTS-kompatiblen Fließtext um.

        Entfernt oder ersetzt Sonderzeichen, die von Text-to-Speech
        Systemen falsch vorgelesen werden.

        Args:
            text: Der ursprüngliche Markdown-Text

        Returns:
            TTS-kompatibler Text in ganzen Sätzen
        """
        if not text:
            return ""

        import re

        # Zeilenweise verarbeiten
        lines = text.split('\n')
        result_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Überschriften in normalen Text umwandeln
            while line.startswith('#'):
                line = line[1:].strip()

            # Markdown-Sonderzeichen entfernen (alle Varianten)
            line = line.replace('**', '').replace('__', '')
            line = line.replace('*', '').replace('_', '')
            line = line.replace('`', '').replace('```', '')

            # Code-Blöcke entfernen
            line = re.sub(r'```.*?```', '', line, flags=re.DOTALL)

            # TTS-problematische Sonderzeichen entfernen oder ersetzen
            line = line.replace('=', ', ')  # Gleichheitszeichen zu Komma
            line = line.replace('+', ' und ')  # Plus zu "und"
            line = line.replace('|', ', ')  # Pipe zu Komma
            line = line.replace('>', ', ')  # Größer als zu Komma
            line = line.replace('<', ', ')  # Kleiner als zu Komma

            # Listenpunkte in ganzzählige Form umwandeln
            if line.startswith('- '):
                line = line[2:]
            elif line.startswith('* '):
                line = line[2:]
            elif line.startswith('1. ') or line.startswith('2. ') or line.startswith('3. '):
                # Nummerierte Listen
                parts = line.split('. ', 1)
                if len(parts) == 2:
                    line = parts[1]

            # Links umwandeln: [Text](URL) -> Text
            line = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', line)

            # URLs entfernen (stehen oft noch im Text)
            line = re.sub(r'https?://[^\s]+', '', line)

            # Mehrere Leerzeichen reduzieren
            line = ' '.join(line.split())

            if line:
                result_lines.append(line)

        # Zu einem Fließtext zusammenfügen
        result = ' '.join(result_lines)

        # Satzzeichen optimieren für TTS
        result = result.replace(' . ', '. ')
        result = result.replace(' , ', ', ')
        result = result.replace(' : ', ', ')  # Doppelpunkte zu Komma
        result = result.replace(' ; ', '; ')

        # Remaining Doppelpunkte zu Komma für bessere Pausen bei TTS
        result = result.replace(':', ',')

        return result.strip()

    def search(
        self,
        query: str,
        use_deep_search: bool = True,
        format: str = "tts"
    ) -> Optional[str]:
        """
        Sucht im Internet basierend auf der Anfrage.

        Args:
            query: Die Suchanfrage oder URL
            use_deep_search: True für Deep Research, False für einzelnen URL-Fetch
            format: "tts" fuer TTS-kompatiblen Text, "markdown" fuer rohes Markdown

        Returns:
            Die Suchergebnisse oder None bei Fehler
        """
        # Prüfe, ob es eine URL ist
        if self.is_url(query):
            raw_result = self.fetch_url(query)
        else:
            # Deep Research
            if use_deep_search:
                raw_result = self.deep_search(query)
            else:
                return "Deep Research ist deaktiviert"

        # Formatierung anwenden
        if raw_result and format == "tts":
            return self._make_tts_compatible(raw_result)

        return raw_result

    def test_connection(self) -> bool:
        """
        Testet die Verbindung zu den Such-Services.

        Returns:
            True wenn mindestens ein Service funktioniert
        """
        # Teste Jina Reader mit einer einfachen URL
        result = self.fetch_url("https://example.com")

        if result and "Example Domain" in result:
            print("Jina Reader Verbindungstest erfolgreich.")
            return True
        else:
            print(f"Jina Reader Verbindungstest fehlgeschlagen: {result}")
            return False


# Test-Funktion
if __name__ == "__main__":
    search = SearchModule()

    print("Teste URL-Fetch...")
    result = search.fetch_url("https://example.com")
    print(result[:200] if result else "Fehler")

    print("\nTeste Deep Research...")
    result = search.deep_search("Was ist Python?", max_tokens=500)
    print(result[:500] if result else "Fehler")
