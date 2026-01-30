Projekt: MoltBot V1 (Unbenannt) - Spezifikation & Implementierungsplan
Ziel: Nachbau der beliebten Clawdbot/Moltbot-Funktionalitäten mit einem sicheren, selbst gehosteten Tech-Stack.Kern-Merkmale: Langzeit-Gedächtnis (Markdown), Telegram-Interface, Jina-Suche (Deep Internet Access).Tech-Stack: Python, GLM-4 (Z.ai), Jina AI, Telegram Bot API, Coolify.

1. Architektur-Übersicht
Das System besteht aus drei Hauptkomponenten, die eng verknüpft sind, um das "Benutzererlebnis" eines intelligenten Assistenten zu schaffen:

Frontend (Telegram): Der primäre Interaktionspunkt.
Backend (Python Core):
Orchestrator: Verwaltet den Gesprächsfluss.
Memory Manager: Verwaltet das Langzeitgedächtnis in Form von Markdown-Dateien.
Search Module: Nutzt Jina AI für tiefe Internetrecherche.
Intelligenz (LLM): GLM-4 (via Z.ai API).
2. Technische Anforderungen & Voraussetzungen
2.1 Externe Dienste & API Keys
LLM: Zhipu AI (GLM-4) API Key.
Bot: Telegram Bot Token (vom @BotFather).
Suche: Jina AI (Reader API / Summarizer) - Anmerkung: Jina bietet oft Endpunkte, die URLs in sauberes Markdown konvertieren, ideal für unsere Memory-Struktur.
2.2 Python-Bibliotheken (Requirements)
Folgende Pakete sind für die lokale Entwicklung und spätere Dockerisierung notwendig:

python-dotenv: Umgebungsvariablen verwalten.
python-telegram-bot: Wrapper für die Telegram API.
openai (oder Zhipu SDK): Da GLM-4 oft kompatibel ist, nutzen wir den OpenAI-Client oder das spezifische Zhipu-SDK für die Anbindung.
aiohttp: Für asynchrone HTTP-Requests (wichtig für Telegram und Jina).
requests (Fallback/Sync): Falls simpler Zugriff nötig.
3. Implementierungsplan (Phasen)
Dieser Plan ist strukturiert, um schrittweise mit "Claude Code" oder einem ähnlichen KI-Assistenten umgesetzt zu werden.

Phase 1: Projekt-Setup & Umgebung (Lokal)
Ziel: Eine saubere Codebasis erstellen, die sich später leicht deployen lässt.

Schritt 1.1: Repository initialisieren.
Erstellen der Ordnerstruktur: /src, /data, /tests.
Erstellen von .gitignore (Ausschluss von .env, __pycache__, /data).
Schritt 1.2: Konfiguration einrichten.
Datei .env erstellen mit Platzhaltern für GLM_API_KEY, TELEGRAM_TOKEN, JINA_API_KEY (falls nötig, sonst öffentliche Endpunkte nutzen).
Schritt 1.3: Dependencies definieren.
Erstellen von requirements.txt mit den oben genannten Paketen.
Phase 2: Das Langzeit-Gedächtnis (Markdown Memory System)
Ziel: Die Kernfunktionalität von Clawdbot reproduzieren. Alles wird gespeichert und ist als lesbarer Text verfügbar.

Schritt 2.1: Datenstruktur definieren.
Für jeden Telegram-User wird ein Ordner /data/users/{user_id}/ erstellt.
Innerhalb des Ordners wird eine memory.md Datei geführt.
Schritt 2.2: Speicher-Logik implementieren (memory_manager.py).
Funktion append_message(user_id, role, content): Hängt neue Nachrichten (User/Bot) an das Ende der memory.md Datei an. Format: Markdown Headers (## User:, ## Bot:).
Funktion get_context(user_id): Liest die letzten X Zeichen oder Zeilen der Datei, um sie in den Prompt des LLMs zu injizieren.
Schritt 2.3: Retrieval-Logik (Optional für V1, aber wichtig für Skalierbarkeit).
Wenn der Kontext zu groß wird, muss eine intelligente Zusammenfassung (Summary) der alten Daten erstellt werden, die oben in der Datei gespeichert wird.
Phase 3: Die Intelligenz anbinden (GLM-4)
Ziel: Den Bot zum Denken bringen.

Schritt 3.1: API-Client Setup.
Verbindung zur Z.ai API herstellen. Test-Call ("Hallo Bot") implementieren.
Schritt 3.2: System Prompt definieren.
Der Prompt muss GLM-4 anweisen:
Präzise und hilfreich zu sein.
Markdown zu nutzen für Ausgaben.
Wenn eine Information fehlt, signalisieren zu können, dass eine Suche nötig ist.
Phase 4: Internet-Suche mit Jina (Der "Proxy"-Aspekt)
Ziel: Dem Bot ermöglichen, das aktuelle Internet zu lesen, nicht nur Trainingsdaten.

Schritt 4.1: Jina Integration (search_service.py).
Nutzung des Jina Readers Endpunkts (z.B. https://r.jina.ai/http://URL). Dieser extrahiert den gesamten Text einer Webseite und gibt ihn als Markdown zurück.
Schritt 4.2: Search Workflow.
User fragt etwas Aktuelles.
Bot entscheidet (intern via LLM Tool Call oder Keyword-Erkennung), dass gesucht werden muss.
Bot sendet Suchbegriff an eine Suchmaschine (z.B. DuckDuckGo oder Bing API), um URLs zu bekommen.
Bot nutzt Jina, um den Inhalt der Top-3 URLs zu extrahieren.
Der extrahierte Markdown-Inhalt wird an GLM-4 gefüttert zur Beantwortung.
Phase 5: Telegram Integration (Das Interface)
Ziel: Alles verbinden.

Schritt 5.1: Bot Setup.
Initialisierung des Application Builders aus python-telegram-bot.
Schritt 5.2: Message Handler.
Handler für /start (Initialisierung des Memory).
Handler für /reset (Löschen der memory.md).
Handler für Textnachrichten.
Schritt 5.3: Asynchroner Ablauf.
User sendet Text -> "Typing..." Aktion senden -> Memory laden -> GLM-4 fragen (ggf. Jina-Suche im Hintergrund) -> Antwort speichern -> Antwort senden.
Phase 6: Deployment Vorbereitung (Coolify & GitHub)
Ziel: Vom lokalen Test zum Live-Server.

Schritt 6.1: Dockerisierung.
Erstellen einer Dockerfile: Python Base Image, Requirements installieren, Code kopieren, Startkommando definieren.
Schritt 6.2: GitHub Integration.
Code hochladen. README.md mit Anleitung zur Installation und API-Key Handhabung schreiben.
Schritt 6.3: Coolify Konfiguration.
Repository in Coolify anbinden.
Umgebungsvariablen in Coolify setzen (niemals Keys ins Git committen!).
Persistenter Speicher (Volume) für den /data Ordner einrichten, damit das Gedächtnis bei einem Neustart des Containers nicht verloren geht.
4. Sicherheitscheckliste (Wichtig!)
Bei der Umsetzung mit Claude Code müssen diese Punkte beachtet werden:

Input Sanitization: Telegram Nachrichten können Markdown-Code enthalten, der das System kaputt macht ("Markdown Injections"). Alle Inputs müssen "escaped" werden, bevor sie in das Memory geschrieben oder an den Prompt angehängt werden.
Rate Limiting: Der Bot muss nicht wild Suchmaschinen bombardieren (Jina Limits beachten).
Privacy: Die memory.md Dateien enthalten private Gespräche. Zugriff auf das Dateisystem des Servers muss strikt kontrolliert sein.
Token Sicherheit: Der .env File muss im .gitignore stehen. Das Docker Image darf keine Keys enthalten.
5. Nächste Aktion
Sobald dieser Plan genehmigt ist, beginnen wir mit Phase 1 und lassen Claude Code das Initial-Setup und die Ordnerstruktur erstellen.

Zusammenfassung für Sie:
Ich habe die MOLTBOT_V1_PLAN.md erstellt. Sie deckt alle Ihre Anforderungen ab:

Markdown-Gedächtnis: Als zentrales Feature in Phase 2 definiert.
Telegram & Proxy/Jina: In Phase 4 und 5 integriert.
Tech-Stack: Python, GLM-4 (Z.ai), Lokal -> Coolify Workflow enthalten.
Vorbereitung für Claude Code: Die Phasen sind so granular, dass man sie direkt als Prompts ("Implementiere Phase 1") nutzen kann.
