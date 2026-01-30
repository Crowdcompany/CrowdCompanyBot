# Crowdbot Deployment Guide

## Deployment mit Coolify

Crowdbot kann einfach mit Coolify auf deinem eigenen Server gehostet werden.

### Voraussetzungen

- Coolify installiert auf deinem Server
- Telegram Bot Token (von @BotFather)
- Deine Telegram Chat-ID (von @userinfobot)

### Schritt 1: Repository in Coolify hinzufügen

1. Öffne Coolify Dashboard
2. Neues Projekt erstellen oder bestehendes auswählen
3. "New Resource" → "Public Repository"
4. Repository URL: `https://github.com/Crowdcompany/CrowdCompanyBot`
5. Branch: `main`
6. Build Pack: `Dockerfile` (wird automatisch erkannt)

### Schritt 2: Umgebungsvariablen konfigurieren

In Coolify unter "Environment Variables" folgende Variablen setzen:

```bash
TELEGRAM_BOT_TOKEN=dein_bot_token_von_botfather
ALLOWED_USER_IDS=deine_chat_id
RATE_LIMIT_PER_MINUTE=10
DATA_DIR=/app/data
```

**Wichtig:** `TELEGRAM_BOT_TOKEN` und `ALLOWED_USER_IDS` müssen gesetzt werden!

#### Telegram Bot Token erhalten

1. Öffne Telegram und suche nach `@BotFather`
2. Sende `/newbot` und folge den Anweisungen
3. Kopiere den erhaltenen Token

#### Deine Chat-ID herausfinden

1. Öffne Telegram und suche nach `@userinfobot`
2. Sende `/start`
3. Kopiere die angezeigte User-ID

### Schritt 3: Volumes konfigurieren (Optional aber empfohlen)

Für persistentes Memory (Konversationshistorie):

- **Source:** `/var/lib/crowdbot/data` (oder ein anderer Pfad auf deinem Server)
- **Destination:** `/app/data`

Dies stellt sicher, dass die Memory-Dateien bei Container-Neustarts erhalten bleiben.

### Schritt 4: Deployment starten

1. Klicke auf "Deploy"
2. Coolify baut das Docker-Image und startet den Container
3. Nach ~30-60 Sekunden ist der Bot online

### Schritt 5: Bot testen

1. Öffne Telegram
2. Suche deinen Bot (Name den du bei @BotFather angegeben hast)
3. Sende `/start`
4. Der Bot sollte antworten!

## Manuelles Deployment mit Docker

Falls du Docker direkt nutzen möchtest:

```bash
# Repository klonen
git clone https://github.com/Crowdcompany/CrowdCompanyBot.git
cd CrowdCompanyBot

# .env Datei erstellen
cp .env.example .env
# Bearbeite .env und setze TELEGRAM_BOT_TOKEN und ALLOWED_USER_IDS

# Docker Compose starten
docker-compose up -d

# Logs anschauen
docker-compose logs -f crowdbot
```

## Troubleshooting

### Bot antwortet nicht

1. Prüfe Logs in Coolify: "Logs" Tab
2. Stelle sicher, dass `TELEGRAM_BOT_TOKEN` korrekt ist
3. Prüfe ob deine Chat-ID in `ALLOWED_USER_IDS` steht

### Container startet nicht

1. Prüfe Coolify Build-Logs
2. Stelle sicher, dass alle required Environment Variables gesetzt sind
3. Prüfe ob Port-Konflikte bestehen (Telegram Bots brauchen keine Ports)

### Memory-Dateien gehen verloren

1. Prüfe ob Volume korrekt gemountet ist
2. Pfad auf Server: `/var/lib/crowdbot/data`
3. Pfad im Container: `/app/data`

## Updates

Coolify deployed automatisch bei neuen Commits auf `main`:

1. Neue Version wird auf GitHub gepusht
2. Coolify erkennt Änderung (Webhook oder Polling)
3. Neues Image wird gebaut
4. Container wird neu gestartet
5. Memory-Dateien bleiben durch Volume erhalten

## Ressourcen

- **CPU:** 0.5-1.0 Core empfohlen
- **RAM:** 256-512 MB empfohlen
- **Disk:** ~500 MB für Image + Memory-Daten

## Sicherheit

- Bot läuft als non-root User (botuser, UID 1000)
- Nur autorisierte User (via ALLOWED_USER_IDS) haben Zugriff
- Keine Ports nach außen exponiert (Telegram long-polling)
- Alle Daten bleiben auf deinem Server

## Support

Bei Problemen öffne ein Issue auf GitHub:
https://github.com/Crowdcompany/CrowdCompanyBot/issues
