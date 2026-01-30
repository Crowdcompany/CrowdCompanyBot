# Multi-Bot Setup: Adam, Berta, Charlie

## Konzept

Jeder Bot läuft als eigener User mit eigener Config und eigenem Port:
- **Adam** (Port 19001): Team Leader, Koordination
- **Berta** (Port 19002): Social Media Expert
- **Charlie** (Port 19003): Content Writer & SEO

**Kommunikation:** Via Slack (jeder Bot eigener Channel)

## Installation

### 1. Basis-System vorbereiten

```bash
# Zuerst die Standard-Installation durchführen
bash install-secure-moltbot.sh

# Dann Multi-Bot-Setup
```

### 2. Bot-User erstellen

```bash
#!/bin/bash

for bot in adam berta charlie; do
    # User erstellen
    useradd -m -s /bin/bash "$bot"
    usermod -aG docker "$bot"
    
    # Directories
    sudo -u "$bot" mkdir -p "/home/$bot"/{.moltbot,.moltbot-encrypted,clawd}
    sudo -u "$bot" mkdir -p "/home/$bot/.moltbot/"{logs,credentials}
    
    # Moltbot installieren
    sudo -u "$bot" pnpm add -g moltbot@latest
done
```

### 3. Individuelle Configs

#### Adam (Team Leader)
```bash
# /home/adam/.moltbot/.env
ZAI_API_KEY=your_key
GATEWAY_TOKEN=$(openssl rand -hex 32)
MOLTBOT_MASTER_KEY=$(openssl rand -hex 32)
CLAWDBOT_DISABLE_BONJOUR=1
CLAWDBOT_CONFIG_PATH=/home/adam/.moltbot/adam.json
CLAWDBOT_STATE_DIR=/home/adam/.moltbot
```

```json
// /home/adam/.moltbot/adam.json
{
  "gateway": {
    "bind": "127.0.0.1",
    "port": 19001,
    "token": "${GATEWAY_TOKEN}"
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "zai/glm-4.7"
      },
      "systemPrompt": "Du bist Adam, Team Leader. Koordiniere Tasks zwischen Berta (Social Media) und Charlie (Content). Nutze Slack-Tools für Kommunikation."
    }
  },
  "channels": {
    "slack": {
      "enabled": true,
      "token": "${SLACK_ADAM_TOKEN}",
      "channels": ["#adam-commands", "#team-coordination"]
    }
  }
}
```

#### Berta (Social Media)
```json
// /home/berta/.moltbot/berta.json
{
  "gateway": {
    "port": 19002
  },
  "agents": {
    "defaults": {
      "systemPrompt": "Du bist Berta, Social Media Expert. Fokus: Instagram, LinkedIn, Twitter. Hole Briefings von Adam via Slack #team-coordination."
    }
  },
  "channels": {
    "slack": {
      "channels": ["#berta-social", "#team-coordination"]
    }
  }
}
```

#### Charlie (Content Writer)
```json
// /home/charlie/.moltbot/charlie.json
{
  "gateway": {
    "port": 19003
  },
  "agents": {
    "defaults": {
      "systemPrompt": "Du bist Charlie, Content Writer & SEO Specialist. Erstelle Blogposts, optimiere für SEO. Koordination mit Adam via Slack."
    }
  },
  "channels": {
    "slack": {
      "channels": ["#charlie-content", "#team-coordination"]
    }
  }
}
```

### 4. Systemd Services

Für jeden Bot:

```bash
# /etc/systemd/system/moltbot-adam.service
[Unit]
Description=Moltbot Adam (Team Leader)
After=network-online.target

[Service]
Type=simple
User=adam
EnvironmentFile=/home/adam/.moltbot/.env
ExecStart=/usr/local/bin/moltbot gateway --port 19001
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Analog für Berta (19002) und Charlie (19003).

```bash
# Services aktivieren
systemctl enable moltbot-{adam,berta,charlie}
systemctl start moltbot-{adam,berta,charlie}
```

### 5. Slack-Integration

#### Slack Workspace Setup
1. Erstelle Workspace "7m-immobilien-bots"
2. Channels:
   - `#adam-commands` - Direktbefehle an Adam
   - `#berta-social` - Social Media Tasks
   - `#charlie-content` - Content Requests
   - `#team-coordination` - Inter-Bot-Communication

#### Bot Apps erstellen
Für jeden Bot in Slack:
1. https://api.slack.com/apps → Create New App
2. Bot Token Scopes:
   - `chat:write`
   - `channels:read`
   - `channels:history`
   - `users:read`
3. Install to Workspace
4. Copy Bot Token → .env Datei

#### Konfiguration
```bash
# Adam
SLACK_ADAM_TOKEN=xoxb-adam-token-here

# Berta  
SLACK_BERTA_TOKEN=xoxb-berta-token-here

# Charlie
SLACK_CHARLIE_TOKEN=xoxb-charlie-token-here
```

### 6. Inter-Bot-Communication

#### Beispiel Workflow:

**User → Adam:**
```
@adam Erstelle einen LinkedIn-Post über unser neues Angebot
```

**Adam → Berta (via Slack):**
```python
# Adam nutzt sessions_send Tool
await sessions_send(
    target="berta",
    channel="slack:#team-coordination",
    message="@berta Bitte erstelle LinkedIn-Post über Angebot XY. Zielgruppe: Immobilieninvestoren. Tonalität: Professional, vertrauenswürdig."
)
```

**Berta → Adam:**
```
@adam LinkedIn-Post erstellt und in #berta-social gepostet. Möchtest du Review?
```

**Adam → User:**
```
✓ LinkedIn-Post wurde von Berta erstellt. Sieh hier: [Link]
Soll ich Charlie bitten, einen Blogpost dazu zu schreiben?
```

### 7. Monitoring

#### Alle Logs zentral:
```bash
# Alle Bot-Logs
tail -f /home/{adam,berta,charlie}/.moltbot/logs/gateway.log

# Services
journalctl -fu moltbot-adam
journalctl -fu moltbot-berta
journalctl -fu moltbot-charlie
```

#### Health-Check Script:
```bash
#!/bin/bash
# check-bots.sh

for bot in adam berta charlie; do
    status=$(systemctl is-active "moltbot-$bot")
    port=$((19000 + $(echo "$bot" | wc -c)))
    
    if [[ "$status" == "active" ]]; then
        echo "✓ $bot: Running on port $port"
    else
        echo "✗ $bot: DOWN"
        systemctl restart "moltbot-$bot"
    fi
done
```

### 8. Backup-Strategie

```bash
#!/bin/bash
# backup-bots.sh

BACKUP_DIR="/backup/moltbot-$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

for bot in adam berta charlie; do
    # Verschlüsselte Credentials
    tar -czf "$BACKUP_DIR/$bot-encrypted.tar.gz" \
        "/home/$bot/.moltbot-encrypted"
    
    # Configs
    cp "/home/$bot/.moltbot/"{.env,*.json} "$BACKUP_DIR/"
    
    # Workspace (ohne große Files)
    tar -czf "$BACKUP_DIR/$bot-workspace.tar.gz" \
        --exclude='node_modules' \
        --exclude='*.log' \
        "/home/$bot/clawd"
done

# Verschlüsseln
tar -czf - "$BACKUP_DIR" | \
    openssl enc -aes-256-cbc -pbkdf2 -out "$BACKUP_DIR.enc" \
    -pass file:/root/.backup-key
```

### 9. Coolify-Integration

#### Als Docker-Container deployen:

```yaml
# docker-compose.yml
version: '3.8'

services:
  adam:
    image: node:24
    container_name: moltbot-adam
    user: "1000:1000"
    volumes:
      - ./adam:/home/adam
    environment:
      - PORT=19001
    command: pnpm exec moltbot gateway --port 19001
    restart: unless-stopped
    networks:
      - moltbot-network

  berta:
    image: node:24
    container_name: moltbot-berta
    user: "1001:1001"
    volumes:
      - ./berta:/home/berta
    environment:
      - PORT=19002
    command: pnpm exec moltbot gateway --port 19002
    restart: unless-stopped
    networks:
      - moltbot-network

  charlie:
    image: node:24
    container_name: moltbot-charlie
    user: "1002:1002"
    volumes:
      - ./charlie:/home/charlie
    environment:
      - PORT=19003
    command: pnpm exec moltbot gateway --port 19003
    restart: unless-stopped
    networks:
      - moltbot-network

networks:
  moltbot-network:
    driver: bridge
```

#### In Coolify:
1. Git Repository mit configs erstellen
2. In Coolify: New Resource → Docker Compose
3. Repository verbinden
4. Secrets/Env-Vars über Coolify UI setzen
5. Deploy

### 10. Sicherheits-Checklist

- [ ] Jeder Bot eigener User
- [ ] Jeder Bot eigener Port (nicht öffentlich)
- [ ] Credentials verschlüsselt at-rest
- [ ] Nur Loopback-Binding
- [ ] SSH-Tunnel für Zugriff
- [ ] UFW aktiv und konfiguriert
- [ ] Regelmäßige Backups
- [ ] Log-Rotation aktiviert
- [ ] Systemd-Hardening für alle Services
- [ ] Slack-Tokens in .env, nie in Git

## Kosten-Kalkulation

**3 Bots mit GLM 4.7:**
- Input: ~$0.03 / 1M tokens
- Output: ~$0.06 / 1M tokens

**Annahme: 10M tokens/Monat pro Bot**
- Adam: $0.90/Monat
- Berta: $0.90/Monat
- Charlie: $0.90/Monat
- **Total: ~$3/Monat**

**Vs. Claude Sonnet (3 Bots):**
- ~$600/Monat

**Ersparnis: 99.5%**

## Erweiterte Features

### Matrix statt Slack (Privacy)
```json
{
  "channels": {
    "matrix": {
      "enabled": true,
      "homeserver": "https://matrix.org",
      "accessToken": "${MATRIX_TOKEN}",
      "rooms": ["!roomid:matrix.org"]
    }
  }
}
```

### Custom Skills pro Bot
```bash
# Adam: Leadership Skills
~/clawd/skills/task-delegation/
~/clawd/skills/priority-management/

# Berta: Social Media Skills
~/clawd/skills/instagram-post/
~/clawd/skills/linkedin-optimizer/

# Charlie: Content Skills
~/clawd/skills/seo-analyzer/
~/clawd/skills/blog-formatter/
```

## Troubleshooting

**Bot antwortet nicht:**
```bash
# Status prüfen
systemctl status moltbot-adam
journalctl -fu moltbot-adam

# Manuell starten
sudo -u adam moltbot gateway --port 19001
```

**Slack-Integration funktioniert nicht:**
```bash
# Token testen
curl -X POST https://slack.com/api/auth.test \
  -H "Authorization: Bearer $SLACK_ADAM_TOKEN"

# Channels prüfen
sudo -u adam moltbot channels status
```

**Ports kollidieren:**
```bash
# Ports prüfen
ss -tlnp | grep 1900

# Config anpassen in moltbot.json
```
