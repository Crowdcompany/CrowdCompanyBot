# Crowdbot

Ein selbst gehosteter KI-Assistent als sichere Alternative zu Moltbot.

## Merkmale

- **Datensouveränität**: Sensible Daten bleiben lokal
- **Sicherheit**: User-Authentifizierung, Isolation, Rate Limiting
- **Kosteneffizienz**: GLM-4.7 via Proxy statt teurer Cloud-APIs
- **Transparenz**: Markdown-basiertes Gedächtnis
- **Internet-Suche**: Jina Deep Research Integration
- **TTS-Optimiert**: Text-to-Speech kompatible Ausgaben

## Status

**Phase 7 - Sicherheits-Härtung** (in Arbeit)

- ✓ Telegram-Authentifizierung implementiert
- ✓ GLM-4.7 Sprachmodell integriert
- ✓ Markdown-Gedächtnis funktionsfähig
- ✓ Internet-Suche mit Jina Deep Research
- ✓ Alle 32 Tests bestanden (24 + 8 Auth-Tests)

Siehe [CHANGELOG.md](CHANGELOG.md) für Details.

## Installation

### Voraussetzungen

- Python 3.11 oder höher
- Telegram Bot Token (vom @BotFather)
- Deine Telegram Chat-ID (von @userinfobot)

### Setup

1. Virtuelle Umgebung erstellen:

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
```

2. Abhängigkeiten installieren:

```bash
pip install -r requirements.txt
```

3. `.env` Datei konfigurieren:

```bash
cp .env.example .env
```

Bearbeite `.env` und setze:

```bash
# Telegram Bot Token vom @BotFather
TELEGRAM_BOT_TOKEN=dein_token_hier

# Deine Chat-ID (von @userinfobot erhalten)
ALLOWED_USER_IDS=YOUR_CHAT_ID

# Optional: Rate Limiting anpassen
RATE_LIMIT_PER_MINUTE=10

# Optional: Data-Verzeichnis anpassen
DATA_DIR=./data
```

### Chat-ID herausfinden

1. Öffne Telegram
2. Suche nach `@get_id_bot` oder `@userinfobot`
3. Starte Chat mit dem Bot
4. Der Bot zeigt dir sofort deine Chat-ID

Empfohlen: `@get_id_bot` (vom Owner verwendet)

## Ausführen

```bash
python3 -m src.bot
```

Der Bot läuft dann und wartet auf Nachrichten in Telegram.

## Befehle

- `/start` - Bot starten und begrüßen
- `/reset` - Gedächtnis zurücksetzen
- `/help` - Hilfe anzeigen
- `/search <Anfrage>` - Internet-Suche mit TTS-Output
- `/searchmd <Anfrage>` - Internet-Suche mit Markdown-Datei
- Textnachrichten werden an das LLM gesendet mit automatischer Tool-Nutzung

## Funktionen

### Markdown-Gedächtnis

Jede Konversation wird lokal in `data/users/{user_id}/memory.md` gespeichert:

```markdown
# Crowdbot Gedächtnis für Username

### Benutzer - 2026-01-30 16:00:00
Hallo, wie geht es dir?

### Crowdbot - 2026-01-30 16:00:05
Mir geht es gut, danke der Nachfrage!
```

### Internet-Suche

Der Bot kann automatisch im Internet suchen wenn benötigt:

- Erkennt automatisch Suchanfragen
- Nutzt Jina Deep Research für umfassende Recherche
- TTS-optimierte Ausgabe für Sprachsynthese
- Optional: Vollständiges Markdown als Download

### Tool-System

Das LLM kann automatisch Tools aufrufen:

- `web_search` - Wird automatisch bei Bedarf genutzt
- Erweiterbar für weitere Tools

## Projektstruktur

```
Crowdbot/
├── src/
│   ├── __init__.py
│   ├── bot.py             # Telegram Bot mit Authentifizierung
│   ├── memory_manager.py  # Markdown-Gedächtnis
│   ├── llm_client.py      # GLM-4.7 Client mit Tools
│   └── search_module.py   # Jina Deep Research
├── data/
│   └── users/
│       └── {user_id}/
│           └── memory.md  # Konversationsverlauf
├── tests/
│   ├── test_memory.py     # Memory Manager Tests (6)
│   ├── test_llm_client.py # LLM Client Tests (5)
│   ├── test_search.py     # Search Module Tests (9)
│   ├── test_integration.py # Integration Tests (4)
│   └── test_auth.py       # Authentifizierung Tests (8)
├── Context/               # Projektdokumentation
│   ├── SecurityImplementation.md
│   └── ...
├── .env                   # API Keys (NICHT im Git!)
├── .env.example           # Beispiel-Konfiguration
├── .gitignore
├── .plan                  # Implementierungsplan
├── CLAUDE.md              # Claude Code Anweisungen
├── CHANGELOG.md           # Änderungshistorie
├── README.md              # Diese Datei
└── requirements.txt       # Python-Abhängigkeiten
```

## Tests

Alle Tests ausführen:

```bash
pytest tests/ -v
```

Einzelne Test-Suite:

```bash
pytest tests/test_auth.py -v
```

**Aktueller Stand:** 32 Tests, alle bestanden ✓

## Sicherheit

### Implementiert (Phase 7.1)

✓ **Telegram-Authentifizierung**
- User-Allowlist mit Chat-IDs
- Nur autorisierte User haben Zugriff
- Freundliche Ablehnung nicht-autorisierter User
- Logging von Zugriffsversuchen

### Geplant

- **Relative Pfade**: Keine hardcodierten Pfade
- **Input-Validierung**: Strikte Prüfung aller Eingaben
- **Rate Limiting**: Schutz vor API-Missbrauch
- **Dependencies Update**: Aktuelle Versionen

### Best Practices

1. `.env` Datei NIEMALS committen
2. Bot in VM oder Docker-Container betreiben
3. Regelmäßige Updates der Dependencies
4. Logs auf sensible Daten prüfen

## Weitere User hinzufügen

Um weitere User zu autorisieren, einfach deren Chat-ID in `.env` hinzufügen:

```bash
ALLOWED_USER_IDS=YOUR_CHAT_ID,1234567890,9876543210
```

Komma-separiert, ohne Leerzeichen.

## Entwicklung

Siehe [CLAUDE.md](CLAUDE.md) für Entwickler-Anweisungen und [.plan](.plan) für den Implementierungsplan.

## Lizenz

MIT License

## Support

Bei Problemen oder Fragen siehe:
- [CHANGELOG.md](CHANGELOG.md) - Was wurde geändert?
- [Context/SecurityImplementation.md](Context/SecurityImplementation.md) - Sicherheitsdetails
- [.plan](.plan) - Implementierungsstatus
