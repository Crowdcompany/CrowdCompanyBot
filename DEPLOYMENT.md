# Deployment auf Coolify

## Persistenter Storage

Der Bot speichert User-Daten (Memory 2.0) im `/app/data` Verzeichnis. Damit diese Daten nach Redeployments erhalten bleiben, wird ein Host-Path-Volume verwendet.

### Konfiguration

Die `docker-compose.yml` mountet `./data:/app/data`. Das bedeutet:

- **Im Container**: `/app/data` (dort speichert der Bot die Daten)
- **Auf dem Host**: `./data` relativ zum Projektverzeichnis

### Coolify Setup

1. **Deployment via Git**
   - Repository verbinden
   - Branch auswählen (z.B. `main`)
   - Coolify erkennt automatisch die `docker-compose.yml`

2. **Volume-Persistence**
   - Das `./data` Verzeichnis wird auf dem Coolify-Server im Projektverzeichnis erstellt
   - Bei Redeployments bleibt dieses Verzeichnis erhalten
   - Alle User-Memories überleben Container-Neustarts

3. **Umgebungsvariablen in Coolify setzen**
   - `TELEGRAM_BOT_TOKEN`: Token vom @BotFather
   - `ALLOWED_USER_IDS`: Komma-separierte Liste (z.B. `7043093505`)
   - `RATE_LIMIT_PER_MINUTE`: Optional (Standard: 10)

### Verifikation nach Deployment

```bash
# Im Coolify-Server Shell:
docker exec crowdbot ls -la /app/data

# Sollte User-Verzeichnisse anzeigen:
# drwxr-xr-x 2 botuser botuser 4096 Jan 30 19:35 7043093505
```

### Backup-Strategie

Das `/app/data` Verzeichnis auf dem Coolify-Server sollte regelmäßig gesichert werden:

```bash
# Auf dem Coolify-Server
tar -czf crowdbot-backup-$(date +%Y%m%d).tar.gz /pfad/zum/projekt/data
```

## Troubleshooting

### Daten gehen nach Redeployment verloren

**Problem**: User-Memories sind nach Redeployment weg

**Ursache**: Volume wurde nicht korrekt gemountet

**Lösung**:
1. Prüfe ob `./data` Verzeichnis im Projektverzeichnis existiert
2. Prüfe Permissions: `chown -R 1000:1000 ./data`
3. Prüfe Docker-Logs: `docker logs crowdbot`

### Bot kann nicht in /app/data schreiben

**Problem**: Permission denied Fehler

**Lösung**:
```bash
# Auf dem Coolify-Server
cd /pfad/zum/projekt
mkdir -p data
chown -R 1000:1000 data
chmod 755 data
```

Der Bot läuft als User `botuser` (UID 1000), daher muss das Verzeichnis diesem User gehören.
