# Deployment Guide

## Persistenter Storage

Der Bot speichert User-Daten (Memory 2.0) im `/app/data` Verzeichnis. Docker Compose erstellt automatisch ein persistentes Volume, das bei Redeployments erhalten bleibt.

## Allgemeine Docker-Lösung

Die `docker-compose.yml` definiert ein Named Volume:

```yaml
volumes:
  crowdbot-data:
```

Dieses Volume wird automatisch erstellt und bleibt bestehen, auch wenn der Container neu gebaut oder neu gestartet wird. Diese Lösung funktioniert auf:

- Coolify
- Render.com
- AWS ECS (mit entsprechendem Plugin)
- Eigenen Servern mit Docker/Docker Compose
- Allen Docker-kompatiblen Plattformen

## Deployment auf verschiedenen Plattformen

### Coolify

1. **Repository verbinden**
   - GitHub Repository URL eingeben
   - Branch auswählen (z.B. `main`)
   - Coolify erkennt automatisch die `docker-compose.yml`

2. **Umgebungsvariablen setzen**
   - `TELEGRAM_BOT_TOKEN`: Token vom @BotFather
   - `ALLOWED_USER_IDS`: Komma-separierte User-IDs (z.B. `7043093505`)
   - `RATE_LIMIT_PER_MINUTE`: Optional (Standard: 10)

3. **Deploy**
   - Klicke auf "Deploy"
   - Warte bis Build fertig ist (1-2 Minuten)

4. **Bot initialisieren** (in Telegram)
   - `/start` - Erstellt Memory-Struktur
   - `/import crowdcompany.info` - Importiert deine Daten

### Eigener Server (Docker Compose)

```bash
# Repository klonen
git clone https://github.com/Crowdcompany/CrowdCompanyBot.git
cd CrowdCompanyBot

# .env Datei erstellen
cp .env.example .env
# TELEGRAM_BOT_TOKEN und ALLOWED_USER_IDS setzen

# Starten
docker-compose up -d

# Logs ansehen
docker-compose logs -f crowdbot
```

### Render.com

1. Neuen Service erstellen (Docker)
2. Repository verbinden
3. Umgebungsvariablen setzen (siehe oben)
4. Persistent Disk hinzufügen:
   - Mount Path: `/app/data`
   - Size: 1GB (oder mehr)
5. Deploy

## Wie funktioniert die Persistence?

Docker Compose erstellt beim ersten Start ein Named Volume. Dieses Volume:

- Existiert unabhängig vom Container
- Überlebt Container-Neuerstellungen
- Wird beim `docker-compose down` NICHT gelöscht (außer mit `-v` Flag)
- Ist bei Redeployments automatisch verfügbar

**Volume-Name:** Coolify und andere Plattformen fügen automatisch Prefixe hinzu (z.B. Projekt-Name), was in Ordnung ist. Der Inhalt bleibt erhalten.

## Verifikation nach Deployment

### Test 1: Volume prüfen

```bash
# Zeige alle Volumes
docker volume ls

# Sollte ein Volume mit "crowdbot-data" im Namen zeigen
# z.B.: myproject_crowdbot-data oder uuid_crowdbot-data

# Zeige Dateien im Volume
docker exec crowdbot ls -la /app/data/users/

# Sollte User-Verzeichnisse anzeigen (nach /start):
# drwxr-xr-x 2 botuser botuser 4096 Jan 30 20:15 7043093505
```

### Test 2: Persistence testen

1. Bot initialisieren: `/start` in Telegram
2. Daten importieren: `/import crowdcompany.info`
3. Frage: "Welche Informationen hast du über mich?"
4. Bot sollte die importierten Infos kennen
5. **Redeployment auslösen**
6. Direkt nach Redeployment: Sende eine Nachricht (OHNE `/start`)
7. Bot sollte dich noch kennen und NICHT "Bitte starte den Bot erst mit /start!" sagen
8. Frage wieder: "Welche Informationen hast du über mich?"
9. Alle Daten sollten noch da sein

## Troubleshooting

### Problem: Daten gehen nach Redeployment verloren

**Ursache 1**: Volume wurde versehentlich gelöscht

```bash
# Prüfe ob Volume existiert
docker volume ls | grep crowdbot

# Volume sollte vorhanden sein
# Falls nicht, wurde es mit docker-compose down -v gelöscht
```

**Lösung**: Nie `docker-compose down -v` verwenden (das `-v` löscht Volumes!)

**Ursache 2**: Falsches Volume gemountet

```bash
# Prüfe welches Volume tatsächlich gemountet ist
docker inspect crowdbot | grep -A 10 Mounts

# Sollte zeigen:
# "Source": "/var/lib/docker/volumes/.../crowdbot-data/_data"
# "Destination": "/app/data"
```

### Problem: Permission Denied beim Schreiben

```bash
# Prüfe User im Container
docker exec crowdbot whoami
# Sollte: botuser

# Prüfe Permissions
docker exec crowdbot ls -la /app/data

# Falls Permissions falsch:
docker exec -u root crowdbot chown -R botuser:botuser /app/data
docker exec -u root crowdbot chmod 755 /app/data
```

### Problem: Volume ist leer nach Redeployment

Das sollte mit der aktuellen Konfiguration nicht passieren. Falls doch:

1. Prüfe ob das Volume existiert: `docker volume ls`
2. Prüfe ob es gemountet ist: `docker inspect crowdbot`
3. Prüfe Plattform-spezifische Volume-Verwaltung

Falls das Volume bei jedem Deployment neu erstellt wird (erkennbar an leerem Inhalt), kontaktiere den Plattform-Support oder prüfe Plattform-spezifische Dokumentation.

## Backup und Restore

### Backup erstellen

```bash
#!/bin/bash
# backup-crowdbot.sh

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
VOLUME_NAME=$(docker volume ls | grep crowdbot-data | awk '{print $2}')

mkdir -p "$BACKUP_DIR"

# Volume-Daten sichern
docker run --rm \
  -v "$VOLUME_NAME":/data \
  -v "$(pwd)/$BACKUP_DIR":/backup \
  alpine tar czf /backup/crowdbot-$DATE.tar.gz -C /data .

echo "Backup erstellt: $BACKUP_DIR/crowdbot-$DATE.tar.gz"
```

### Backup wiederherstellen

```bash
#!/bin/bash
# restore-crowdbot.sh

BACKUP_FILE=$1
VOLUME_NAME=$(docker volume ls | grep crowdbot-data | awk '{print $2}')

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup-file.tar.gz>"
  exit 1
fi

# Bot stoppen
docker stop crowdbot

# Backup wiederherstellen
docker run --rm \
  -v "$VOLUME_NAME":/data \
  -v "$(pwd)":/backup \
  alpine sh -c "cd /data && tar xzf /backup/$BACKUP_FILE"

# Bot starten
docker start crowdbot

echo "Backup wiederhergestellt: $BACKUP_FILE"
```

## Technische Details

### Volume-Lifecycle

1. **Erster Start**: Docker erstellt das Volume automatisch
2. **Container-Neustart**: Volume bleibt erhalten
3. **Redeployment**: Volume wird wiederverwendet
4. **docker-compose down**: Volume bleibt erhalten
5. **docker-compose down -v**: Volume wird gelöscht (VORSICHT!)

### Volume-Naming

Plattformen fügen oft Prefixe hinzu:

- Coolify: `<uuid>_crowdbot-data`
- Docker Compose: `<projektname>_crowdbot-data`
- Render: Eigenes Persistent Disk System

Das ist normal und funktioniert korrekt, solange das Volume bei Redeployments wiederverwendet wird.

## Best Practices

1. **Nie `-v` Flag verwenden** beim Stoppen: `docker-compose down` statt `docker-compose down -v`
2. **Regelmäßige Backups**: Automatisiere das Backup-Script
3. **Test nach Deployment**: Führe immer den Persistence-Test durch
4. **Monitoring**: Überwache Volume-Größe: `docker system df -v`

## Checkliste

- [ ] Umgebungsvariablen gesetzt (TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS)
- [ ] Erstes Deployment durchgeführt
- [ ] Bot mit `/start` initialisiert
- [ ] Test-Daten importiert (z.B. `/import crowdcompany.info`)
- [ ] Volume-Existenz geprüft (`docker volume ls`)
- [ ] Persistence-Test durchgeführt (Redeployment + Datenprüfung)
- [ ] Backup-Strategie eingerichtet
