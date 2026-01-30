# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projektüberblick

Crowdbot ist ein funktionsfähiger KI-Assistent als sicherere Alternative zu Moltbot. Ein persönlicher Telegram-Bot der lokal betrieben wird und sensible Daten nicht an externe Cloud-Dienste sendet.

**Status:** Produktiv einsetzbar (Version 1.0, Stand: 30. Januar 2026)

Der Bot ist voll funktionsfähig mit Telegram-Integration, Perplexity-Suche für Fakten, Jina Deep Research für Analysen und GLM-4.7 als Sprachmodell.

## Architektur

Das System besteht aus drei Hauptkomponenten:

1. **Frontend (Telegram)**: Primärer Interaktionspunkt mit Benutzern
2. **Backend (Python Core)**: Orchestrator, Memory Manager, Search Module
3. **Intelligenz (LLM)**: GLM-4 via Z.ai API

### Tech-Stack
- **Sprache**: Python 3.11+ (mit virtueller Umgebung)
- **KI-Modell**: GLM-4.7 via glmproxy.ccpn.cc (Anthropic API Format)
- **Bot-Framework**: Telegram Bot API (python-telegram-bot 21.11)
- **Suche**:
  - Perplexity Sonar via ppproxy.ccpn.cc (schnelle Fakten)
  - Jina Deep Research via jinaproxy.ccpn.cc (ausführliche Analysen)
- **Gedächtnis**: Markdown-basiertes Langzeitgedächtnis (lokal)

## Implementierungsstatus

✓ **Phase 1: Projekt-Setup** - ABGESCHLOSSEN
- Ordnerstruktur: `/src`, `/data`, `/tests`, `/Context`
- `.gitignore` für `.env`, `__pycache__`, `/data`
- Virtuelle Python-Umgebung aktiv

✓ **Phase 2: Markdown-Gedächtnis** - ABGESCHLOSSEN
- Pro User: `/data/users/{user_id}/memory.md`
- Memory Manager mit `append_message()`, `get_context()`, `reset_user()`
- Format: Markdown-Header mit Zeitstempeln

✓ **Phase 3: LLM-Anbindung** - ABGESCHLOSSEN
- GLM-4.7 via glmproxy.ccpn.cc (Anthropic API Format)
- Tool-Unterstützung implementiert
- Intention-basierte Tool-Nutzung

✓ **Phase 4: Internet-Suche** - ABGESCHLOSSEN
- Perplexity Sonar für schnelle Fakten (TV-Programm, Nachrichten, etc.)
- Jina Deep Research für ausführliche Analysen
- Intelligente Auswahl basierend auf Query-Keywords
- TTS-kompatible Formatierung

✓ **Phase 5: Telegram Integration** - ABGESCHLOSSEN
- Commands: /start, /reset, /help, /search, /searchmd, /deepresearch
- Text-Handler mit LLM und automatischer Tool-Nutzung
- Asynchroner Ablauf mit Typing-Indikator
- Markdown-Datei-Download für lange Recherchen

✓ **Phase 6: Testing** - ABGESCHLOSSEN
- 32 Tests implementiert, alle bestanden
- Test-Suites: Memory, LLM, Search, Integration, Auth

✓ **Phase 7: Sicherheit** - ABGESCHLOSSEN
- Telegram User-Authentifizierung (Allowlist)
- Input-Validierung
- TTS-Kompatibilität für alle Ausgaben

## API-Konfiguration

### GLM-4.7 (Sprachmodell)
- **Proxy**: https://glmproxy.ccpn.cc/v1/messages
- **Format**: Anthropic API kompatibel
- **Kein API-Key erforderlich** (in Proxy hinterlegt)
- **Model**: glm-4.7

### Telegram Bot
- **Bot-Token**: Vom @BotFather erhalten
- **Speichern**: In `.env` unter `TELEGRAM_BOT_TOKEN`
- **User-IDs**: In `.env` unter `ALLOWED_USER_IDS` (komma-separiert)
- **Chat-ID erhalten**: @userinfobot oder @get_id_bot

### Perplexity (Schnelle Faktensuche)
- **Proxy**: https://ppproxy.ccpn.cc/chat/completions
- **Kein API-Key erforderlich** (in Proxy hinterlegt)
- **Model**: sonar
- **Verwendung**: Automatisch bei Fakten-Anfragen

### Jina AI (Deep Research)
- **Reader**: https://r.jina.ai/ (öffentlich)
- **Deep Search Proxy**: https://jinaproxy.ccpn.cc/v1/chat/completions
- **Kein API-Key erforderlich** (in Proxy hinterlegt)
- **Model**: jina-deepsearch-v1
- **Verwendung**: Automatisch bei Analyse-Anfragen oder via /deepresearch

## Entwicklung

### Virtuelle Umgebung
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
```

### Installation
```bash
# Virtuelle Umgebung aktivieren
source venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt

# .env Datei erstellen und konfigurieren
cp .env.example .env
# Dann TELEGRAM_BOT_TOKEN und ALLOWED_USER_IDS setzen
```

### Ausführen
```bash
# Bot starten
python3 -m src.bot

# Bot läuft dann und wartet auf Telegram-Nachrichten
```

### Tests
```bash
# Alle Tests ausführen
pytest tests/ -v

# Spezifische Test-Suite
pytest tests/test_auth.py -v

# Aktueller Stand: 32/32 Tests bestanden ✓
```

## KRITISCH: TTS-Kompatibilität und Markdown

**WICHTIG:** Alle Bot-Antworten MÜSSEN TTS-kompatibel sein und dürfen KEIN Markdown enthalten!

### Problem
LLMs nutzen standardmäßig Markdown-Formatierung (**, *, _, `, ###, etc.), was zu Problemen bei Text-to-Speech führt.

### Lösung (IMPLEMENTIERT)
1. **System-Prompt**: LLM wird instruiert, kein Markdown zu verwenden
2. **Post-Processing**: Funktion `_remove_markdown()` in [src/bot.py](src/bot.py) entfernt alle Markdown-Zeichen
3. **Anwendung**: Wird auf ALLE LLM-Antworten vor dem Senden angewendet

### Regel für Entwicklung
- NIEMALS Markdown-formatierte Antworten direkt an User senden
- IMMER `_remove_markdown()` auf LLM-Antworten anwenden
- Bei neuen Handler-Funktionen: Post-Processing nicht vergessen!

## Sicherheit

### Implementierte Maßnahmen (Stand: 30.01.2026)

✓ **Telegram-Authentifizierung**
- User-Allowlist mit Chat-IDs in `.env`
- Nur autorisierte User haben Zugriff
- Freundliche Ablehnung nicht-autorisierter Anfragen
- Logging von Zugriffsversuchen
- 8 Tests implementiert und bestanden

✓ **Input-Validierung**
- Längen-Limits für Telegram-Nachrichten (4096 Zeichen)
- Sichere Dateinamen-Generierung für Downloads
- URL-Validierung für Web-Scraping

✓ **Token-Sicherheit**
- `.env` in `.gitignore` (NIEMALS committen!)
- Alle API-Keys nur in `.env`-Datei
- Kein Hardcoding von Secrets im Code

✓ **TTS-Kompatibilität**
- Markdown-Entfernung für alle Bot-Ausgaben
- Sonderzeichen-Filterung (=, +, |, etc.)
- Fließtext-Formatierung für Sprachausgabe

### Empfehlungen für Produktion

- **Isolation**: Bot in VM oder Docker-Container betreiben
- **Updates**: Regelmäßige Dependency-Updates
- **Logging**: Sensible Daten in Logs maskieren
- **Backups**: `/data` Verzeichnis regelmäßig sichern
- **Rate Limiting**: Optional RATE_LIMIT_PER_MINUTE in `.env` setzen

### .gitignore
Die `.gitignore`-Datei muss enthalten:
- `.env`
- `__pycache__/`
- `venv/`
- `/data/`
- `*.pyc`

## Verwendung

### Bot-Befehle auf Telegram

- **/start** - Bot starten und begrüßen (erstellt Memory-Datei)
- **/reset** - Gedächtnis zurücksetzen (löscht Konversationshistorie)
- **/help** - Hilfe anzeigen
- **/search <Anfrage>** - Schnelle Faktensuche (Perplexity, TTS-optimiert)
- **/searchmd <Anfrage>** - Suche mit Markdown-Datei als Download
- **/deepresearch <Anfrage>** - Ausführliche Analyse (Jina Deep Research)
- **Textnachrichten** - Normale Chat-Nachrichten (LLM mit automatischer Tool-Nutzung)

### Beispiele

```
User: Was läuft heute Abend im TV?
Bot: [Nutzt automatisch Perplexity für aktuelle TV-Programme]

User: /deepresearch Erkläre ausführlich wie Quantencomputer funktionieren
Bot: [Nutzt Jina Deep Research für umfassende Analyse]

User: /searchmd Python Programmierung Best Practices
Bot: [Sendet vollständige Recherche als Markdown-Datei]
```

### Intelligente Such-Auswahl

Der Bot wählt automatisch die passende Suchstrategie:

- **Perplexity (schnell)**: Nachrichten, TV-Programme, Fakten, "Was ist X?"
- **Deep Research (ausführlich)**: Analysen, technische Erklärungen, Wikipedia-ähnlich

Keywords für Deep Research: "erkläre ausführlich", "analysiere", "wie funktioniert", "vergleiche detailliert"

## Verweise

- **README.md**: Benutzer-Dokumentation und Installation
- **CHANGELOG.md**: Versionshistorie und Änderungen
- **Context/CrowdBotDescription.md**: Projektspezifikation
- **Context/SecurityImplementation.md**: Sicherheitsdetails
- **Context/MoltBotSecurity.md**: Ursprüngliche Sicherheitsanalyse
- **.plan**: Aktueller Implementierungsstatus
