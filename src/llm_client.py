"""
LLM Client für Crowdbot

Verwendet GLM-4.7 via glmproxy.ccpn.cc (Anthropic API Format)
Unterstützt Intention-basierte Tool-Nutzung.
"""

import os
import json
import requests
from typing import List, Dict, Optional, Callable, Any
from dotenv import load_dotenv

# Lade Umgebungsvariablen
load_dotenv()


class LLMClient:
    """Client für die Kommunikation mit GLM-4.7 via Proxy."""

    def __init__(
        self,
        proxy_url: str = "https://glmproxy.ccpn.cc/v1/messages",
        model_name: str = "glm-4.7"
    ):
        """
        Initialisiert den LLM Client.

        Args:
            proxy_url: URL des GLM-Proxies (Anthropic Format)
            model_name: Name des Modells
        """
        self.proxy_url = proxy_url
        self.model_name = model_name

        # Tool-Registry (wird von außen registriert)
        self.tools: Dict[str, Callable] = {}

        # Tool-Beschreibungen für Intention-Erkennung
        self.tool_descriptions: List[Dict[str, str]] = []

        # System-Prompt für Crowdbot
        self.system_prompt = """Du bist Crowdbot, ein hilfreicher und freundlicher KI-Assistent mit dauerhaftem Gedächtnis.

Deine Eigenschaften:
- Du hast Zugriff auf die komplette Konversationshistorie mit diesem Benutzer
- Du erinnerst dich an alle bisherigen Gespräche und kannst darauf Bezug nehmen
- Sei präzise und hilfreich in deinen Antworten
- Bleibe freundlich und respektvoll
- Wenn du etwas nicht weißt, sag es ehrlich
- Antworte auf Deutsch, es sei denn, der Benutzer schreibt in einer anderen Sprache
- Vermeide Wiederholungen
- Strukturiere deine Antworten klar und verständlich

KRITISCH: Umgang mit Such-Ergebnissen:
- Wenn du Informationen aus Tool-Ergebnissen erhältst, gib diese EXAKT und WORTGETREU wieder
- Erfinde NIEMALS Informationen oder Details, die nicht in den Tool-Ergebnissen stehen
- Bei Fernsehprogrammen, Nachrichten oder faktischen Daten: Nenne GENAU das, was in den Suchergebnissen steht
- Verwechsle NIEMALS Sender, Namen, Zeiten oder andere Details
- Wenn die Suchergebnisse mehrere Sender oder Optionen enthalten, gib diese korrekt getrennt wieder
- Lieber weniger sagen als etwas Falsches erfinden

WICHTIG für deine Antworten:
- Schreibe immer in ganzen Sätzen und fließendem Text
- Nutze niemals Markdown-Formatierung (keine Sternchen *, keine Unterstriche _, keine Backticks `)
- Vermeide Sonderzeichen wie =, +, # die von Text-to-Speech Systemen falsch vorgelesen werden
- Schreibe Zahlen als Worte wenn möglich für bessere Aussprache
- Deine Antworten müssen für Text-to-Speech optimiert sein"""

    def _build_messages(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """
        Baut die Nachrichten-Liste für die API auf.

        Args:
            user_message: Die aktuelle Nachricht des Benutzers
            conversation_history: Optionaler Konversationsverlauf

        Returns:
            Liste der Nachrichten im Anthropic-Format
        """
        messages = []

        # Füge den Konversationsverlauf hinzu (ohne System-Prompt, der geht separat)
        if conversation_history:
            for msg in conversation_history:
                if msg["role"] in ["user", "assistant"]:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

        # Füge die aktuelle Nachricht hinzu
        messages.append({"role": "user", "content": user_message})

        return messages

    def register_tool(
        self,
        name: str,
        func: Callable,
        description: str,
        parameters: Dict[str, Any] = None
    ):
        """
        Registriert ein Tool, das vom LLM aufgerufen werden kann.

        Args:
            name: Name des Tools
            func: Funktion die bei Tool-Aufruf ausgeführt wird
            description: Beschreibung wofür das Tool genutzt wird
            parameters: Beschreibung der Parameter (optional)
        """
        self.tools[name] = func
        self.tool_descriptions.append({
            "name": name,
            "description": description,
            "parameters": parameters or {}
        })
        print(f"Tool '{name}' registriert: {description}")

    def _analyze_intention(self, user_message: str) -> List[Dict[str, Any]]:
        """
        Analysiert die Intention des Benutzers und entscheidet welche Tools genutzt werden.

        Args:
            user_message: Die Nachricht des Benutzers

        Returns:
            Liste der Tool-Aufrufe mit Parametern
        """
        if not self.tool_descriptions:
            return []

        # Baue Tool-Liste für den Prompt auf
        tools_list = "\n".join([
            f"- {tool['name']}: {tool['description']}"
            for tool in self.tool_descriptions
        ])

        intention_prompt = f"""Analysiere die folgende Benutzeranfrage und entscheide, welche Tools genutzt werden sollen.

Verfügbare Tools:
{tools_list}

Benutzeranfrage: {user_message}

Gib deine Antwort ausschließlich als gültiges JSON-Array zurück. Jedes Objekt im Array muss folgende Struktur haben:
{{"tool": "tool_name", "parameters": {{"param": "value"}}}}

Wenn kein Tool benötigt wird, gib ein leeres Array zurück: []

Beispiele:
- "Wie ist das Wetter?" -> [{{"tool": "web_search", "parameters": {{"query": "aktuelles Wetter"}}}}]
- "Erzähl mir einen Witz" -> []
- "Was gibt es Neues?" -> [{{"tool": "web_search", "parameters": {{"query": "aktuelle Nachrichten"}}}}]
- "Suche nach Informationen über Python" -> [{{"tool": "web_search", "parameters": {{"query": "Python Programmierung"}}}}]

Deine Antwort (nur JSON):"""

        try:
            payload = {
                "model": self.model_name,
                "max_tokens": 500,
                "messages": [
                    {"role": "user", "content": intention_prompt}
                ]
            }

            headers = {
                "Content-Type": "application/json",
                "x-api-key": "dummy-key"
            }

            response = requests.post(
                self.proxy_url,
                json=payload,
                headers=headers,
                timeout=30
            )

            response.raise_for_status()
            data = response.json()

            if data.get("content") and len(data["content"]) > 0:
                content = data["content"][0].get("text", "")

                # JSON aus dem Content extrahieren
                # Manchmal gibt der Bot Text vor dem JSON zurück
                json_start = content.find("[")
                json_end = content.rfind("]") + 1

                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    tool_calls = json.loads(json_str)
                    print(f"Intention erkannt: {tool_calls}")
                    return tool_calls

            return []

        except Exception as e:
            print(f"Fehler bei Intention-Analyse: {e}")
            return []

    def _execute_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """
        Führt einen Tool-Aufruf aus.

        Args:
            tool_name: Name des aufzurufenden Tools
            tool_input: Parameter für das Tool

        Returns:
            Das Ergebnis des Tool-Aufrufs als String
        """
        if tool_name not in self.tools:
            return f"Fehler: Tool '{tool_name}' nicht gefunden"

        try:
            func = self.tools[tool_name]
            result = func(**tool_input)

            # Ergebnis zu String konvertieren
            if result is None:
                return "Keine Ergebnisse"
            elif isinstance(result, str):
                return result
            else:
                return str(result)

        except Exception as e:
            return f"Fehler bei der Ausführung von {tool_name}: {e}"

    def chat_with_intention(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 2000
    ) -> Optional[str]:
        """
        Chat-Methode mit Intention-basierter Tool-Nutzung.

        Args:
            user_message: Die Nachricht des Benutzers
            conversation_history: Optionaler Konversationsverlauf
            max_tokens: Maximale Anzahl der Tokens in der Antwort

        Returns:
            Die Antwort des Modells oder None bei Fehler
        """
        # 1. Intention analysieren
        tool_calls = self._analyze_intention(user_message)

        # 2. Tools ausführen wenn benötigt
        tool_results = []
        if tool_calls:
            print(f"Führe {len(tool_calls)} Tool-Aufrufe aus...")

            for call in tool_calls:
                tool_name = call.get("tool")
                parameters = call.get("parameters", {})

                print(f"Tool: {tool_name}, Parameter: {parameters}")
                result = self._execute_tool_call(tool_name, parameters)
                tool_results.append(f"Tool '{tool_name}' Ergebnis:\n{result}")

        # 3. Nachricht für finale Antwort vorbereiten
        if tool_results:
            # Mit Tool-Ergebnissen
            enhanced_message = (
                f"Der Benutzer fragt: {user_message}\n\n"
                f"WICHTIG: Ich habe aktuelle Informationen durch eine Internetsuche erhalten. "
                f"Diese Informationen sind FAKTEN und müssen EXAKT wiedergegeben werden:\n\n"
                f"{chr(10).join(tool_results)}\n\n"
                f"ANWEISUNG: Beantworte die Frage des Benutzers ausschließlich mit den Informationen aus den Tool-Ergebnissen. "
                f"Gib die Fakten WORTGETREU wieder. ERFINDE NICHTS. "
                f"Wenn mehrere Sender oder Optionen genannt werden, gib sie ALLE korrekt wieder."
            )
        else:
            # Ohne Tool-Ergebnisse
            enhanced_message = user_message

        # 4. Normale Chat-Anfrage
        messages = self._build_messages(enhanced_message, conversation_history)

        try:
            payload = {
                "model": self.model_name,
                "max_tokens": max_tokens,
                "system": self.system_prompt,
                "messages": messages
            }

            headers = {
                "Content-Type": "application/json",
                "x-api-key": "dummy-key"
            }

            response = requests.post(
                self.proxy_url,
                json=payload,
                headers=headers,
                timeout=60
            )

            response.raise_for_status()
            data = response.json()

            # Anthropic API Format
            if data.get("content") and len(data["content"]) > 0:
                return data["content"][0].get("text")
            else:
                print("Fehler: Keine content in der Antwort")
                print(f"Response: {data}")
                return None

        except requests.RequestException as e:
            print(f"Fehler bei der API-Anfrage: {e}")
            return None
        except (KeyError, IndexError) as e:
            print(f"Fehler beim Parsen der Antwort: {e}")
            return None
        except Exception as e:
            print(f"Unerwarteter Fehler: {e}")
            return None

    def chat(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 1000
    ) -> Optional[str]:
        """
        Sendet eine Anfrage an das GLM-4.7 Modell via Proxy.

        Args:
            user_message: Die Nachricht des Benutzers
            conversation_history: Optionaler Konversationsverlauf
            max_tokens: Maximale Anzahl der Tokens in der Antwort

        Returns:
            Die Antwort des Modells oder None bei Fehler
        """
        messages = self._build_messages(user_message, conversation_history)

        try:
            payload = {
                "model": self.model_name,
                "max_tokens": max_tokens,
                "system": self.system_prompt,
                "messages": messages
            }

            headers = {
                "Content-Type": "application/json",
                "x-api-key": "dummy-key"
            }

            response = requests.post(
                self.proxy_url,
                json=payload,
                headers=headers,
                timeout=30
            )

            response.raise_for_status()
            data = response.json()

            # Anthropic API Format
            if data.get("content") and len(data["content"]) > 0:
                return data["content"][0].get("text")
            else:
                print("Fehler: Keine content in der Antwort")
                print(f"Response: {data}")
                return None

        except requests.RequestException as e:
            print(f"Fehler bei der API-Anfrage: {e}")
            return None
        except (KeyError, IndexError) as e:
            print(f"Fehler beim Parsen der Antwort: {e}")
            return None
        except Exception as e:
            print(f"Unerwarteter Fehler: {e}")
            return None

    def test_connection(self) -> bool:
        """
        Testet die Verbindung zum GLM-Proxy.

        Returns:
            True wenn Verbindung erfolgreich
        """
        response = self.chat("Hallo, kannst du mich hören?")

        if response:
            print(f"Verbindungstest erfolgreich. Antwort: {response}")
            return True
        else:
            print("Verbindungstest fehlgeschlagen.")
            return False
