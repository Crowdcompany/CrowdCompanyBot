# Deployment auf Coolify

## KRITISCH: Persistenter Storage Setup

Der Bot speichert User-Daten (Memory 2.0) im `/app/data` Verzeichnis. Damit diese Daten nach Redeployments erhalten bleiben, MUSS ein Persistent Volume in Coolify konfiguriert werden.

## Schritt-für-Schritt Anleitung

### 1. Persistent Volume in Coolify erstellen

**WICHTIG: Dies muss VOR dem ersten Deployment gemacht werden!**

1. Öffne dein Coolify Dashboard
2. Gehe zu "Storages" oder "Persistent Volumes"
3. Klicke auf "Add New Storage" oder "Create Persistent Volume"
4. Konfiguration:
   - **Name**: `crowdbot-data`
   - **Type**: Persistent Volume
   - **Driver**: local (Standard)
   - **Mount Path** (optional): `/var/lib/docker/volumes/crowdbot-data/_data`

5. Klicke auf "Create" oder "Save"

### 2. Volume dem Service zuweisen

1. Gehe zu deinem Crowdbot Service in Coolify
2. Öffne den Tab "Storages" oder "Volumes"
3. Klicke auf "Add Storage"
4. Konfiguration:
   - **Source**: `crowdbot-data` (das eben erstellte Volume)
   - **Destination**: `/app/data`
   - **Mount Type**: Volume

5. Speichern

**Alternativ**: Die docker-compose.yml definiert bereits das Volume. Coolify sollte es automatisch erkennen und in der UI anzeigen. Du musst dann nur noch bestätigen, dass es als "external" bzw. "persistent" markiert ist.

### 3. Umgebungsvariablen setzen

In Coolify unter "Environment Variables":

- `TELEGRAM_BOT_TOKEN`: Dein Bot-Token vom @BotFather
- `ALLOWED_USER_IDS`: Komma-separierte User-IDs (z.B. `7043093505`)
- `RATE_LIMIT_PER_MINUTE`: Optional (Standard: 10)

### 4. Deployment starten

1. Klicke auf "Deploy" in Coolify
2. Warte bis Build abgeschlossen ist (1-2 Minuten)
3. Bot sollte jetzt laufen

### 5. Bot initialisieren

In Telegram:
1. Sende `/start` an deinen Bot
2. Dies erstellt die Memory-Struktur im persistenten Volume
3. Importiere Infos: `/import crowdcompany.info`

### 6. Persistence verifizieren (WICHTIG!)

**Test 1: Volume-Inhalt prüfen**

Im Coolify Terminal oder SSH:

```bash
# Prüfe ob Volume existiert
docker volume ls | grep crowdbot-data

# Prüfe Inhalt
docker volume inspect crowdbot-data

# Zeige Dateien im Volume
docker exec crowdbot ls -la /app/data/users/

# Sollte anzeigen:
# drwxr-xr-x 2 botuser botuser 4096 Jan 30 20:15 7043093505
```

**Test 2: Redeployment-Test**

1. Löse ein weiteres Redeployment in Coolify aus
2. Warte bis Deployment fertig ist
3. Sende OHNE `/start` eine Nachricht an den Bot
4. Bot sollte NICHT "Bitte starte den Bot erst mit /start!" sagen
5. Frage: "Welche Informationen hast du über mich?"
6. Bot sollte die vorher importierten Infos kennen

## Technische Details

### Volume-Konfiguration

Die `docker-compose.yml` definiert:

```yaml
volumes:
  crowdbot-data:
    name: crowdbot-data
    external: true
```

**`external: true`** bedeutet: Das Volume existiert bereits außerhalb des Compose-Stacks und wird nicht gelöscht, wenn der Stack neu erstellt wird.

### Warum relativer Pfad (`./data`) NICHT funktioniert

Bei Git-basierten Deployments:
1. Coolify klont das Repo in ein temporäres Verzeichnis
2. Jedes Redeployment = neuer Checkout
3. `./data` ist relativ zum Checkout → wird jedes Mal neu erstellt
4. Alte Daten gehen verloren

**Lösung**: External Named Volume, das außerhalb des Projekt-Checkouts existiert.

## Troubleshooting

### Problem: Daten gehen nach Redeployment verloren

**Ursache 1**: Volume wurde nicht als `external` erstellt

**Lösung**:
```bash
# SSH auf Coolify-Server
docker volume ls | grep crowdbot

# Wenn Volume fehlt, manuell erstellen:
docker volume create crowdbot-data

# Danach Redeploy
```

**Ursache 2**: Volume ist nicht im Service gemountet

**Lösung**:
1. Prüfe in Coolify UI unter "Storages"
2. Volume muss auf `/app/data` gemountet sein
3. Mount Type muss "Volume" sein (nicht "Bind")

### Problem: Permission Denied beim Schreiben

**Fehler**: Bot kann nicht in `/app/data` schreiben

**Lösung**:
```bash
# SSH auf Coolify-Server
docker exec crowdbot whoami
# Sollte: botuser

# Prüfe Permissions im Volume
docker exec crowdbot ls -la /app/data
# Sollte: drwxr-xr-x botuser botuser

# Falls falsche Permissions:
docker exec -u root crowdbot chown -R botuser:botuser /app/data
docker exec -u root crowdbot chmod 755 /app/data
```

### Problem: Volume existiert aber ist leer nach Redeployment

**Ursache**: Falsches Volume wird gemountet

**Lösung**:
```bash
# Prüfe welches Volume tatsächlich gemountet ist
docker inspect crowdbot | grep -A 10 Mounts

# Sollte zeigen:
# "Source": "/var/lib/docker/volumes/crowdbot-data/_data"
# "Destination": "/app/data"
```

## Backup-Strategie

### Automatisches Backup

```bash
#!/bin/bash
# backup-crowdbot.sh

BACKUP_DIR="/var/backups/crowdbot"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Volume-Daten sichern
docker run --rm \
  -v crowdbot-data:/data \
  -v "$BACKUP_DIR":/backup \
  alpine tar czf /backup/crowdbot-data-$DATE.tar.gz -C /data .

# Alte Backups löschen (älter als 30 Tage)
find "$BACKUP_DIR" -name "crowdbot-data-*.tar.gz" -mtime +30 -delete

echo "Backup erstellt: crowdbot-data-$DATE.tar.gz"
```

### Backup wiederherstellen

```bash
#!/bin/bash
# restore-crowdbot.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup-file.tar.gz>"
  exit 1
fi

# Bot stoppen
docker stop crowdbot

# Backup wiederherstellen
docker run --rm \
  -v crowdbot-data:/data \
  -v $(dirname "$BACKUP_FILE"):/backup \
  alpine sh -c "cd /data && tar xzf /backup/$(basename "$BACKUP_FILE")"

# Bot starten
docker start crowdbot

echo "Backup wiederhergestellt: $BACKUP_FILE"
```

## Checkliste für neues Deployment

- [ ] Persistent Volume `crowdbot-data` in Coolify erstellt
- [ ] Volume als "external" markiert
- [ ] Volume dem Service zugewiesen: Source=`crowdbot-data`, Destination=`/app/data`
- [ ] Umgebungsvariablen gesetzt: `TELEGRAM_BOT_TOKEN`, `ALLOWED_USER_IDS`
- [ ] Erstes Deployment durchgeführt
- [ ] Bot mit `/start` initialisiert
- [ ] Test-Daten importiert (z.B. `/import crowdcompany.info`)
- [ ] Zweites Redeployment zum Testen der Persistence
- [ ] Daten sind nach Redeployment noch vorhanden
- [ ] Backup-Strategie konfiguriert
