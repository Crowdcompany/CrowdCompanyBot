# Konzept: Gehärtete Moltbot-Installation

## Security-First Architektur

### 1. Netzwerk-Isolation
```json
{
  "gateway": {
    "bind": "127.0.0.1",              // NIE public IP
    "port": 18789,
    "token": "${GATEWAY_TOKEN}",      // Aus .env
    "controlUi": {
      "enabled": true,
      "requireDevicePairing": true,   // Gerätebindung erzwingen
      "allowInsecureAuth": false      // Kein Fallback
    }
  }
}
```

### 2. GLM 4.7 via Z.AI Integration

**Warum GLM 4.7:**
- Kosteneffizient für Tool-Calling
- Gute Performance bei lokalen Tasks
- Z.AI Provider bereits in Moltbot eingebaut

**Konfiguration (.env):**
```bash
# GLM 4.7 via Z.AI
ZAI_API_KEY=your_zai_key_here

# Gateway Security
GATEWAY_TOKEN=random_secure_token_256bit
CLAWDBOT_DISABLE_BONJOUR=1  # kein mDNS Broadcasting
```

**moltbot.json:**
```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "zai/glm-4.7"
      },
      "models": {
        "zai/glm-4.7": {
          "alias": "GLM",
          "params": {
            "thinking": {
              "type": "enabled",
              "budgetTokens": 16384
            }
          }
        }
      },
      "sandbox": {
        "mode": "non-main",  // Gruppen/Channels in Docker
        "image": "moltbot-sandbox:latest"
      }
    }
  }
}
```

**Bekanntes Problem:**
GLM 4.7 hat Context-Contamination-Issues (siehe GitHub Issue #1712).
→ Für kritische Cron-Jobs andere Models nutzen (Haiku 4.5)

### 3. Jina Reader Proxy für Web-Fetching

**Warum Jina Reader:**
- Verwandelt Websites in sauberes LLM-Markdown
- Bypassed Bot-Protection mit Puppeteer
- Proxy-Header für zusätzliche Anonymität
- Kostenlos mit Rate-Limits (oder API-Key für mehr)

**Integration via Custom Skill:**

`~/clawd/skills/jina-web/SKILL.md`:
```markdown
# Jina Web Reader Skill

Use Jina Reader API for web fetching instead of direct scraping.

## Tool: jina_fetch
**Purpose:** Fetch and convert any URL to clean markdown

**Usage:**
```bash
curl "https://r.jina.ai/${URL}" \
  -H "X-With-Generated-Alt: true" \
  -H "X-Proxy-Url: ${PROXY_URL}"
```

**Parameters:**
- URL: The webpage to fetch
- PROXY_URL (optional): Custom proxy for additional privacy

**Returns:** Clean markdown text suitable for LLM context

## When to use:
- User asks to read a website
- Need to extract article content
- Parse documentation pages
- Any web research task

## Example:
User: "Read the latest news from example.com"
Assistant: [calls jina_fetch with "https://example.com/news"]
```

**Tool Implementation:**
```javascript
// tools/jina-web.js
export async function jina_fetch({ url, use_proxy = false }) {
  const JINA_API_KEY = process.env.JINA_API_KEY; // optional
  const headers = {
    'X-With-Generated-Alt': 'true',
    'X-Return-Format': 'markdown'
  };
  
  if (JINA_API_KEY) {
    headers['Authorization'] = `Bearer ${JINA_API_KEY}`;
  }
  
  if (use_proxy) {
    headers['X-Proxy-Url'] = process.env.JINA_PROXY_URL;
  }
  
  const response = await fetch(`https://r.jina.ai/${url}`, { headers });
  return await response.text();
}
```

### 4. Credential-Verschlüsselung

**Problem:** Moltbot speichert alles in Plaintext

**Lösung:** Wrapper-Script mit Encryption

```bash
#!/bin/bash
# encrypt-credentials.sh

CRED_DIR="$HOME/.moltbot/credentials"
ENCRYPTED_DIR="$HOME/.moltbot-encrypted"

# Vor Gateway-Start: Entschlüsseln
decrypt_credentials() {
  openssl enc -d -aes-256-cbc \
    -in "$ENCRYPTED_DIR/whatsapp.enc" \
    -out "$CRED_DIR/whatsapp/creds.json" \
    -pass env:MOLTBOT_MASTER_KEY
}

# Nach Gateway-Stop: Verschlüsseln
encrypt_credentials() {
  openssl enc -aes-256-cbc \
    -in "$CRED_DIR/whatsapp/creds.json" \
    -out "$ENCRYPTED_DIR/whatsapp.enc" \
    -pass env:MOLTBOT_MASTER_KEY
  
  # Original löschen
  shred -u "$CRED_DIR/whatsapp/creds.json"
}

# Trap für sauberes Cleanup
trap encrypt_credentials EXIT

decrypt_credentials
moltbot gateway
```

### 5. Systemd Service mit Security

```ini
[Unit]
Description=Secure Moltbot Gateway
After=network.target
Requires=docker.service

[Service]
Type=simple
User=moltbot
Group=moltbot

# Umgebungsvariablen aus verschlüsselter Datei
EnvironmentFile=/etc/moltbot/secure.env

# Security Hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/moltbot/.moltbot /home/moltbot/clawd

# Network Isolation
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
IPAddressAllow=127.0.0.1/8

# Sandbox
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

# Restart Policy
Restart=on-failure
RestartSec=10

ExecStart=/usr/local/bin/secure-moltbot-wrapper.sh

[Install]
WantedBy=multi-user.target
```

### 6. Firewall-Regeln

```bash
# ufw setup
ufw default deny incoming
ufw default allow outgoing

# Nur SSH (mit Key-Auth)
ufw allow 22/tcp

# Gateway nur loopback
ufw deny 18789/tcp

# Wenn Tailscale genutzt wird:
ufw allow in on tailscale0

ufw enable
```

### 7. Monitoring & Alerts

**Webhook für Security-Events:**
```json
{
  "automation": {
    "webhook": {
      "enabled": true,
      "endpoints": [
        {
          "url": "https://your-monitoring.com/webhook",
          "events": [
            "gateway.unauthorized_access",
            "pairing.request",
            "tool.elevated_exec"
          ],
          "secret": "${WEBHOOK_SECRET}"
        }
      ]
    }
  }
}
```

## Installation Steps

### 1. System vorbereiten
```bash
# User erstellen (non-root)
sudo useradd -m -s /bin/bash moltbot
sudo usermod -aG docker moltbot

# Node.js 24 (neueste Version)
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo bash -
sudo apt install -y nodejs

# pnpm
npm install -g pnpm
```

### 2. Moltbot installieren
```bash
su - moltbot
pnpm add -g moltbot@latest

# Onboarding überspringen, manuell konfigurieren
mkdir -p ~/.moltbot ~/.moltbot-encrypted ~/clawd
```

### 3. Sichere Konfiguration
```bash
# .env Datei erstellen
cat > ~/.moltbot/.env << 'EOF'
# Z.AI für GLM 4.7
ZAI_API_KEY=your_api_key

# Jina (optional, für höhere Limits)
JINA_API_KEY=your_jina_key

# Gateway Security
GATEWAY_TOKEN=$(openssl rand -hex 32)
CLAWDBOT_DISABLE_BONJOUR=1

# Encryption
MOLTBOT_MASTER_KEY=$(openssl rand -hex 32)
EOF

chmod 600 ~/.moltbot/.env
```

### 4. Nur WhatsApp & Telegram konfigurieren
```bash
# Telegram (sicherer als WhatsApp)
moltbot configure --section channels
# → Telegram wählen, Bot-Token eingeben

# WhatsApp (optional)
moltbot channels login
# → QR-Code scannen
```

### 5. Pairing strikt aktivieren
```bash
# In moltbot.json:
{
  "channels": {
    "telegram": {
      "requirePairing": true,
      "allowFrom": ["+49..."]  // Deine Nummer
    }
  }
}
```

### 6. Docker-Sandbox testen
```bash
# Sandbox-Image bauen
docker build -t moltbot-sandbox:latest \
  -f ~/clawd/Dockerfile.sandbox .

# Test
moltbot agent send --text "ls -la /tmp" --session test
```

### 7. Service starten
```bash
sudo systemctl enable --now secure-moltbot.service
sudo systemctl status secure-moltbot
```

## Best Practices

### DO:
✅ **Immer** Tailscale/SSH-Tunnel für Remote-Zugriff
✅ Credentials verschlüsselt at-rest
✅ Docker-Sandbox für alle non-DM Sessions
✅ Regelmäßige `moltbot security audit --deep`
✅ Backup der verschlüsselten Credentials
✅ Separate User für Moltbot (nicht root)
✅ Firewall auf Host-Level
✅ Rate-Limiting für Gateway-Port

### DON'T:
❌ Gateway an public IP binden
❌ Authentication deaktivieren
❌ root-User nutzen
❌ Credentials in Git committen
❌ mDNS Broadcasting aktiv lassen
❌ Sandbox-Mode für DMs deaktivieren (wenn public Channels genutzt)
❌ Alte Node.js Versionen (<22.12.0)

## Unterschiede zu Standard-Moltbot

| Feature | Standard Moltbot | Deine Version |
|---------|------------------|---------------|
| Gateway Bind | LAN-fähig | Loopback-only |
| Credentials | Plaintext | Verschlüsselt at-rest |
| Channel Auth | Optional | Pairing required |
| Sandbox | Optional | Default für non-DM |
| Web Fetch | Direkt | Via Jina Proxy |
| Model | Anthropic API | GLM 4.7 (Z.AI) |
| mDNS | Enabled | Disabled |
| Systemd | Basic | Hardened |

## Kosten-Rechnung

**Z.AI GLM 4.7:**
- Input: ~$0.03 / 1M tokens
- Output: ~$0.06 / 1M tokens
- **~95% günstiger als Claude Sonnet**

**Jina Reader:**
- Kostenlos: 20 requests/min
- Mit API Key: $10/mo für 10K requests

**Total: ~$10-20/Monat** (vs. $200+ mit Claude)

## Multi-Bot Setup für Adam/Berta/Charlie

```bash
# Jeder Bot eigener User + Port
sudo useradd -m adam
sudo useradd -m berta  
sudo useradd -m charlie

# Separate Instanzen
CLAWDBOT_CONFIG_PATH=~/.moltbot/adam.json \
CLAWDBOT_STATE_DIR=~/.moltbot-adam \
moltbot gateway --port 19001 &

CLAWDBOT_CONFIG_PATH=~/.moltbot/berta.json \
CLAWDBOT_STATE_DIR=~/.moltbot-berta \
moltbot gateway --port 19002 &

CLAWDBOT_CONFIG_PATH=~/.moltbot/charlie.json \
CLAWDBOT_STATE_DIR=~/.moltbot-charlie \
moltbot gateway --port 19003 &

# Slack für Inter-Bot-Communication
# Jeder Bot eigener Slack-Channel
```

## Nächste Schritte

1. ✅ Fresh Debian 13 VM aufsetzen
2. ✅ User & Docker Setup
3. ✅ Moltbot mit obiger Config installieren
4. ✅ Telegram + WhatsApp pairen
5. ✅ Jina Skill hinzufügen
6. ✅ Systemd Service härten
7. ✅ Security Audit durchführen
8. ✅ Backup-Strategie definieren
9. ✅ Multi-Bot-Setup für Adam/Berta/Charlie
10. ✅ Coolify Integration für Management

## Quellen & Links

- Moltbot Docs: https://docs.molt.bot
- Z.AI Provider: https://docs.molt.bot/providers/zai
- GLM Config: https://docs.molt.bot/gateway/configuration
- Jina Reader: https://jina.ai/reader/
- Security Guide: https://docs.molt.bot/gateway/security
- GitHub Issue #1712: GLM Context-Bug
