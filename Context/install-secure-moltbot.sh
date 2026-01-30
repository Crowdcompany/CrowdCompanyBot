#!/bin/bash
#
# install-secure-moltbot.sh
# Komplette Installation von gehärtetem Moltbot auf Debian 13
#
# Usage:
#   curl -fsSL https://your-server.com/install-secure-moltbot.sh | bash
#   oder
#   bash install-secure-moltbot.sh

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

MOLTBOT_USER="moltbot"
MOLTBOT_HOME="/home/${MOLTBOT_USER}"
NODE_VERSION="24"

# Colors für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Dieses Script muss als root ausgeführt werden"
        exit 1
    fi
}

generate_secure_token() {
    openssl rand -hex 32
}

# ============================================================================
# SYSTEM VORBEREITUNG
# ============================================================================

prepare_system() {
    log_info "Update System Packages..."
    apt update && apt upgrade -y
    
    log_info "Installiere benötigte Packages..."
    apt install -y \
        curl \
        wget \
        git \
        build-essential \
        python3 \
        python3-pip \
        docker.io \
        docker-compose \
        ufw \
        openssl \
        jq
    
    systemctl enable docker
    systemctl start docker
}

# ============================================================================
# NODE.JS INSTALLATION
# ============================================================================

install_nodejs() {
    log_info "Installiere Node.js ${NODE_VERSION}..."
    
    # NodeSource Repository
    curl -fsSL "https://deb.nodesource.com/setup_${NODE_VERSION}.x" | bash -
    apt install -y nodejs
    
    # Version check
    node_version=$(node --version)
    log_info "Node.js installiert: ${node_version}"
    
    # pnpm global
    log_info "Installiere pnpm..."
    npm install -g pnpm
}

# ============================================================================
# USER SETUP
# ============================================================================

setup_moltbot_user() {
    log_info "Erstelle Moltbot User..."
    
    if id "${MOLTBOT_USER}" &>/dev/null; then
        log_warn "User ${MOLTBOT_USER} existiert bereits"
    else
        useradd -m -s /bin/bash "${MOLTBOT_USER}"
        log_info "User ${MOLTBOT_USER} erstellt"
    fi
    
    # Docker Group
    usermod -aG docker "${MOLTBOT_USER}"
    
    # Directories
    sudo -u "${MOLTBOT_USER}" mkdir -p "${MOLTBOT_HOME}"/{.moltbot,.moltbot-encrypted,clawd}
    sudo -u "${MOLTBOT_USER}" mkdir -p "${MOLTBOT_HOME}/.moltbot/"{logs,credentials}
    sudo -u "${MOLTBOT_USER}" mkdir -p "${MOLTBOT_HOME}/clawd/skills/jina-reader"
}

# ============================================================================
# MOLTBOT INSTALLATION
# ============================================================================

install_moltbot() {
    log_info "Installiere Moltbot..."
    
    sudo -u "${MOLTBOT_USER}" pnpm add -g moltbot@latest
    
    # Version check
    moltbot_version=$(sudo -u "${MOLTBOT_USER}" moltbot --version 2>/dev/null || echo "unknown")
    log_info "Moltbot installiert: ${moltbot_version}"
}

# ============================================================================
# CONFIGURATION
# ============================================================================

create_env_file() {
    log_info "Erstelle .env Datei..."
    
    local gateway_token
    local master_key
    gateway_token=$(generate_secure_token)
    master_key=$(generate_secure_token)
    
    cat > "${MOLTBOT_HOME}/.moltbot/.env" <<EOF
# Moltbot Secure Configuration
# Generated: $(date)

# ============================================================================
# MODEL PROVIDER
# ============================================================================

# Z.AI für GLM 4.7
ZAI_API_KEY=REPLACE_WITH_YOUR_ZAI_KEY

# Optional: Jina Reader API Key
JINA_API_KEY=REPLACE_WITH_YOUR_JINA_KEY

# ============================================================================
# GATEWAY SECURITY
# ============================================================================

GATEWAY_TOKEN=${gateway_token}
CLAWDBOT_DISABLE_BONJOUR=1

# ============================================================================
# CREDENTIAL ENCRYPTION
# ============================================================================

MOLTBOT_MASTER_KEY=${master_key}

# ============================================================================
# PATHS
# ============================================================================

CLAWDBOT_CONFIG_PATH=${MOLTBOT_HOME}/.moltbot/moltbot.json
CLAWDBOT_STATE_DIR=${MOLTBOT_HOME}/.moltbot
CLAWDBOT_WORKSPACE=${MOLTBOT_HOME}/clawd
EOF
    
    chown "${MOLTBOT_USER}:${MOLTBOT_USER}" "${MOLTBOT_HOME}/.moltbot/.env"
    chmod 600 "${MOLTBOT_HOME}/.moltbot/.env"
    
    log_info "✓ Gateway Token: ${gateway_token}"
    log_info "✓ Master Key: ${master_key}"
    log_warn "WICHTIG: Notiere diese Tokens sicher!"
}

create_moltbot_config() {
    log_info "Erstelle moltbot.json..."
    
    cat > "${MOLTBOT_HOME}/.moltbot/moltbot.json" <<'EOF'
{
  "gateway": {
    "bind": "127.0.0.1",
    "port": 18789,
    "token": "${GATEWAY_TOKEN}",
    "controlUi": {
      "enabled": true,
      "requireDevicePairing": true,
      "allowInsecureAuth": false
    },
    "discovery": {
      "bonjour": {
        "enabled": false
      }
    }
  },
  
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
      "workspace": "~/clawd",
      "sandbox": {
        "mode": "non-main",
        "image": "moltbot-sandbox:latest"
      }
    }
  },
  
  "channels": {
    "telegram": {
      "enabled": false,
      "requirePairing": true
    },
    "whatsapp": {
      "enabled": false,
      "requirePairing": true
    }
  },
  
  "logging": {
    "level": "info",
    "file": "~/.moltbot/logs/gateway.log"
  }
}
EOF
    
    chown "${MOLTBOT_USER}:${MOLTBOT_USER}" "${MOLTBOT_HOME}/.moltbot/moltbot.json"
    chmod 600 "${MOLTBOT_HOME}/.moltbot/moltbot.json"
}

# ============================================================================
# WRAPPER SCRIPT
# ============================================================================

install_wrapper_script() {
    log_info "Installiere Wrapper Script..."
    
    cat > /usr/local/bin/secure-moltbot-wrapper.sh <<'WRAPPER_EOF'
#!/bin/bash
set -euo pipefail

MOLTBOT_HOME="${HOME}"
CRED_DIR="${MOLTBOT_HOME}/.moltbot/credentials"
ENCRYPTED_DIR="${MOLTBOT_HOME}/.moltbot-encrypted"
LOG_FILE="${MOLTBOT_HOME}/.moltbot/logs/wrapper.log"

# Load .env
if [[ -f "${MOLTBOT_HOME}/.moltbot/.env" ]]; then
    source "${MOLTBOT_HOME}/.moltbot/.env"
fi

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

decrypt_credentials() {
    log "Entschlüssle Credentials..."
    mkdir -p "${CRED_DIR}"/{whatsapp,telegram}
    
    if [[ -f "${ENCRYPTED_DIR}/whatsapp.enc" ]]; then
        openssl enc -d -aes-256-cbc \
            -in "${ENCRYPTED_DIR}/whatsapp.enc" \
            -out "${CRED_DIR}/whatsapp/creds.json" \
            -pass env:MOLTBOT_MASTER_KEY 2>>"${LOG_FILE}" || true
    fi
    
    if [[ -f "${ENCRYPTED_DIR}/telegram.enc" ]]; then
        openssl enc -d -aes-256-cbc \
            -in "${ENCRYPTED_DIR}/telegram.enc" \
            -out "${CRED_DIR}/telegram.token" \
            -pass env:MOLTBOT_MASTER_KEY 2>>"${LOG_FILE}" || true
    fi
    
    chmod 600 "${CRED_DIR}"/**/* 2>/dev/null || true
}

encrypt_credentials() {
    log "Verschlüssle Credentials..."
    mkdir -p "${ENCRYPTED_DIR}"
    
    if [[ -f "${CRED_DIR}/whatsapp/creds.json" ]]; then
        openssl enc -aes-256-cbc \
            -in "${CRED_DIR}/whatsapp/creds.json" \
            -out "${ENCRYPTED_DIR}/whatsapp.enc" \
            -pass env:MOLTBOT_MASTER_KEY 2>>"${LOG_FILE}"
        shred -u "${CRED_DIR}/whatsapp/creds.json" 2>/dev/null || rm -f "${CRED_DIR}/whatsapp/creds.json"
    fi
    
    if [[ -f "${CRED_DIR}/telegram.token" ]]; then
        openssl enc -aes-256-cbc \
            -in "${CRED_DIR}/telegram.token" \
            -out "${ENCRYPTED_DIR}/telegram.enc" \
            -pass env:MOLTBOT_MASTER_KEY 2>>"${LOG_FILE}"
        shred -u "${CRED_DIR}/telegram.token" 2>/dev/null || rm -f "${CRED_DIR}/telegram.token"
    fi
    
    chmod 600 "${ENCRYPTED_DIR}"/*.enc 2>/dev/null || true
}

cleanup() {
    local exit_code=$?
    log "Cleanup (Exit: ${exit_code})"
    
    if [[ -n "${GATEWAY_PID:-}" ]]; then
        kill "${GATEWAY_PID}" 2>/dev/null || true
        wait "${GATEWAY_PID}" 2>/dev/null || true
    fi
    
    encrypt_credentials
    exit "${exit_code}"
}

main() {
    log "=== Start Secure Moltbot ==="
    trap cleanup EXIT INT TERM
    
    decrypt_credentials
    
    log "Starte Gateway..."
    set -a
    source "${MOLTBOT_HOME}/.moltbot/.env"
    set +a
    
    moltbot gateway &
    GATEWAY_PID=$!
    
    log "Gateway PID: ${GATEWAY_PID}"
    wait "${GATEWAY_PID}"
}

main "$@"
WRAPPER_EOF
    
    chmod +x /usr/local/bin/secure-moltbot-wrapper.sh
    chown "${MOLTBOT_USER}:${MOLTBOT_USER}" /usr/local/bin/secure-moltbot-wrapper.sh
}

# ============================================================================
# SYSTEMD SERVICE
# ============================================================================

install_systemd_service() {
    log_info "Installiere Systemd Service..."
    
    cat > /etc/systemd/system/secure-moltbot.service <<EOF
[Unit]
Description=Secure Moltbot Gateway
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=simple
User=${MOLTBOT_USER}
Group=${MOLTBOT_USER}

EnvironmentFile=${MOLTBOT_HOME}/.moltbot/.env
WorkingDirectory=${MOLTBOT_HOME}

# Security Hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${MOLTBOT_HOME}/.moltbot
ReadWritePaths=${MOLTBOT_HOME}/.moltbot-encrypted
ReadWritePaths=${MOLTBOT_HOME}/clawd

ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
IPAddressAllow=127.0.0.1/8 ::1/128

SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

LimitNOFILE=65536
MemoryMax=2G

StandardOutput=journal
StandardError=journal
SyslogIdentifier=moltbot

ExecStart=/usr/local/bin/secure-moltbot-wrapper.sh

KillMode=mixed
TimeoutStopSec=30
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    log_info "✓ Systemd Service installiert"
}

# ============================================================================
# FIREWALL
# ============================================================================

setup_firewall() {
    log_info "Konfiguriere UFW Firewall..."
    
    # Reset UFW
    ufw --force reset
    
    # Defaults
    ufw default deny incoming
    ufw default allow outgoing
    
    # SSH
    ufw allow 22/tcp comment "SSH"
    
    # Gateway Port blockieren (nur loopback)
    ufw deny 18789/tcp comment "Moltbot Gateway (blocked - use SSH tunnel)"
    
    # Enable
    ufw --force enable
    
    log_info "✓ Firewall konfiguriert"
}

# ============================================================================
# JINA SKILL
# ============================================================================

install_jina_skill() {
    log_info "Installiere Jina Reader Skill..."
    
    cat > "${MOLTBOT_HOME}/clawd/skills/jina-reader/SKILL.md" <<'EOF'
# Jina Web Reader Skill

## Purpose
Secure web content fetching via Jina Reader API.

## Tool: jina_fetch

Use this to fetch and convert URLs to clean markdown:

```bash
curl "https://r.jina.ai/${URL}" \
  -H "Authorization: Bearer ${JINA_API_KEY}" \
  -H "X-With-Generated-Alt: true"
```

## When to Use
- User asks to read a website
- Extract article content
- Parse documentation
- Web research tasks

## Rate Limits
- Without key: 20 req/min
- With key: 10K req/month

Use whenever user mentions a URL or asks about web content.
EOF
    
    chown -R "${MOLTBOT_USER}:${MOLTBOT_USER}" "${MOLTBOT_HOME}/clawd/skills"
    log_info "✓ Jina Skill installiert"
}

# ============================================================================
# MAIN INSTALLATION
# ============================================================================

main() {
    log_info "=== Secure Moltbot Installation für Debian 13 ==="
    
    check_root
    
    log_info "Step 1/10: System vorbereiten..."
    prepare_system
    
    log_info "Step 2/10: Node.js installieren..."
    install_nodejs
    
    log_info "Step 3/10: Moltbot User erstellen..."
    setup_moltbot_user
    
    log_info "Step 4/10: Moltbot installieren..."
    install_moltbot
    
    log_info "Step 5/10: .env Datei erstellen..."
    create_env_file
    
    log_info "Step 6/10: moltbot.json erstellen..."
    create_moltbot_config
    
    log_info "Step 7/10: Wrapper Script installieren..."
    install_wrapper_script
    
    log_info "Step 8/10: Systemd Service installieren..."
    install_systemd_service
    
    log_info "Step 9/10: Firewall konfigurieren..."
    setup_firewall
    
    log_info "Step 10/10: Jina Skill installieren..."
    install_jina_skill
    
    log_info ""
    log_info "========================================="
    log_info "✓ Installation abgeschlossen!"
    log_info "========================================="
    log_info ""
    log_info "NÄCHSTE SCHRITTE:"
    log_info ""
    log_info "1. API Keys setzen:"
    log_info "   sudo -u moltbot nano /home/moltbot/.moltbot/.env"
    log_info "   → ZAI_API_KEY und JINA_API_KEY eintragen"
    log_info ""
    log_info "2. Telegram konfigurieren:"
    log_info "   sudo -u moltbot moltbot configure --section channels"
    log_info "   → Telegram wählen, Bot-Token eingeben"
    log_info ""
    log_info "3. Service starten:"
    log_info "   systemctl enable secure-moltbot"
    log_info "   systemctl start secure-moltbot"
    log_info ""
    log_info "4. Status prüfen:"
    log_info "   systemctl status secure-moltbot"
    log_info "   sudo -u moltbot moltbot status"
    log_info ""
    log_info "5. Zugriff via SSH-Tunnel:"
    log_info "   ssh -L 18789:localhost:18789 root@server"
    log_info "   Dann: http://localhost:18789"
    log_info ""
    log_info "Gateway Token: $(grep GATEWAY_TOKEN ${MOLTBOT_HOME}/.moltbot/.env | cut -d= -f2)"
    log_info ""
}

main "$@"
