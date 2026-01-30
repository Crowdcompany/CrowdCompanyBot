# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projektüberblick

Crowdbot ist ein geplanter KI-Assistent als sicherere Alternative zu Moltbot. Das Projekt soll ein persönlicher Assistent sein, der lokal betrieben wird und sensible Daten nicht an externe Cloud-Dienste sendet. Das Projekt befindet sich derzeit in der Planungsphase.

## Architektur

Das System besteht aus drei Hauptkomponenten:

1. **Frontend (Telegram)**: Primärer Interaktionspunkt mit Benutzern
2. **Backend (Python Core)**: Orchestrator, Memory Manager, Search Module
3. **Intelligenz (LLM)**: GLM-4 via Z.ai API

### Tech-Stack
- **Sprache**: Python (immer mit virtueller Umgebung)
- **KI-Modell**: GLM-4 via Z.ai API (MiniMax-M2.1)
- **Bot-Framework**: Telegram Bot API (python-telegram-bot)
- **Suche**: Jina AI für Internetrecherche
- **Gedächtnis**: Markdown-basiertes Langzeitgedächtnis

## Projektaufbau

Das Projekt folgt einem strukturierten Implementierungsplan (siehe `Context/CrowdBotDescription.md`):

### Phase 1: Projekt-Setup
- Ordnerstruktur: `/src`, `/data`, `/tests`
- `.gitignore` für `.env`, `__pycache__`, `/data`
- Virtuelle Python-Umgebung

### Phase 2: Markdown-Gedächtnis
- Pro User: `/data/users/{user_id}/memory.md`
- Memory Manager mit `append_message()` und `get_context()`
- Format: Markdown-Header für User/Bot-Nachrichten

### Phase 3: GLM-4 Anbindung
- API-Client für Z.ai
- System-Prompt für präzise, hilfreiche Antworten

### Phase 4: Internet-Suche
- Jina Reader für Web-Scraping (https://r.jina.ai/http://URL)
- Suchmaschinen-Integration für URLs
- Proxy für Deep Research: https://jinaproxy.ccpn.cc/

### Phase 5: Telegram Integration
- /start, /reset, Text-Handler
- Asynchroner Ablauf mit Typing-Indikator

## API-Konfiguration

### Z.ai GLM-4
- API-Key in `.env`-Datei (NICHT ins Git committen!)
- API-Key ist bereits im Projekt hinterlegt
- Alternativ: MiniMax-M2.1 via Proxy (kein Key nötig)

### Telegram
- Bot-Token vom @BotFather
- In `.env` speichern

### Jina AI
- Öffentliche Endpunkte verfügbar
- Optionaler API-Key für erweiterte Funktionen

## Entwicklung

### Virtuelle Umgebung
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
```

### Installation (geplant)
```bash
pip install -r requirements.txt
```

### Ausführen (geplant)
```bash
python3 -m src.bot
```

### Tests (geplant)
```bash
pytest tests/
```

## Sicherheit

Kritische Sicherheitsanforderungen basierend auf Sicherheitsaudit:

### Sofort zu implementieren (Priorität 1):

1. **Telegram-Authentifizierung**: ✓ IMPLEMENTIERT (2026-01-30)
   - User-Allowlist mit autorisierten Chat-IDs
   - Owner Chat-ID: YOUR_CHAT_ID in `.env` konfiguriert
   - Weitere autorisierte User können hinzugefügt werden
   - Alle anderen User werden abgelehnt mit freundlicher Nachricht
   - 8 Tests implementiert und bestanden
   - Siehe: [CHANGELOG.md](CHANGELOG.md) für Details
   - Chat-ID herausfinden: Jeder User kann @userinfobot auf Telegram nutzen

2. **Relative Pfade**: Keine hardcodierten absoluten Pfade
   - Alle Pfade relativ zum Projektverzeichnis
   - Konfigurierbar über Umgebungsvariablen

3. **Input-Validierung**: Strikte Prüfung aller User-Inputs
   - Längen-Limits für alle Eingaben
   - Sanitization gegen Markdown-Injection
   - Path-Traversal Prevention bei Dateinamen

4. **Rate Limiting**: Schutz vor API-Missbrauch
   - Standard: 10 Anfragen pro Minute pro User
   - Konfigurierbar über Umgebungsvariable: RATE_LIMIT_PER_MINUTE
   - Cooldown für teure Operationen wie Deep Search

### Für Produktion (Priorität 2):

5. **Token-Sicherheit**: `.env` niemals committen
   - GitHub revoked automatisch exponierte Tokens
   - Regelmäßige Key-Rotation empfohlen

6. **Kein Standard-Port**: Port muss während Einrichtung gewählt werden

7. **Isolation**: VM oder Docker-Container empfohlen

### Geplant für später:

8. **Logging-Sicherheit**: Sensible Daten in Logs maskieren

9. **Security-Tests**: Automated Input-Validierung Tests

10. **Error Handling**: Detaillierte Fehler nur für authentifizierte User

### .gitignore
Die `.gitignore`-Datei muss enthalten:
- `.env`
- `__pycache__/`
- `venv/`
- `/data/`
- `*.pyc`

## Verweise

- Projektspezifikation: `Context/CrowdBotDescription.md`
- Sicherheitsanalyse: `Context/MoltBotSecurity.md`
- Moltbot-Referenz: `Context/Moltbot-Repo.md`
- Deep Research Proxy: `Context/DeepResearchProxy.md`
- AI-Konfiguration: `Context/AI.md`
- Projektziel: `Context/ProjektZiel.md`
