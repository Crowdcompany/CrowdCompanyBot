#!/bin/bash
#
# secure-moltbot-wrapper.sh
# Verschlüsselt Credentials at-rest, startet Gateway, verschlüsselt beim Beenden
#
# Installation:
#   chmod +x /usr/local/bin/secure-moltbot-wrapper.sh
#   sudo chown moltbot:moltbot /usr/local/bin/secure-moltbot-wrapper.sh

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

MOLTBOT_USER="${USER}"
MOLTBOT_HOME="${HOME}"
CRED_DIR="${MOLTBOT_HOME}/.moltbot/credentials"
ENCRYPTED_DIR="${MOLTBOT_HOME}/.moltbot-encrypted"
LOG_FILE="${MOLTBOT_HOME}/.moltbot/logs/wrapper.log"

# Aus .env laden
if [[ -f "${MOLTBOT_HOME}/.moltbot/.env" ]]; then
    # shellcheck disable=SC1091
    source "${MOLTBOT_HOME}/.moltbot/.env"
fi

# Prüfe Master Key
if [[ -z "${MOLTBOT_MASTER_KEY:-}" ]]; then
    echo "ERROR: MOLTBOT_MASTER_KEY nicht gesetzt in .env" >&2
    exit 1
fi

# ============================================================================
# LOGGING
# ============================================================================

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

# ============================================================================
# ENCRYPTION FUNCTIONS
# ============================================================================

decrypt_credentials() {
    log "Entschlüssle Credentials..."
    
    mkdir -p "${CRED_DIR}/whatsapp"
    mkdir -p "${CRED_DIR}/telegram"
    
    # WhatsApp Credentials
    if [[ -f "${ENCRYPTED_DIR}/whatsapp.enc" ]]; then
        openssl enc -d -aes-256-cbc \
            -in "${ENCRYPTED_DIR}/whatsapp.enc" \
            -out "${CRED_DIR}/whatsapp/creds.json" \
            -pass env:MOLTBOT_MASTER_KEY \
            2>>"${LOG_FILE}" || {
                log "WARNING: WhatsApp Credentials konnten nicht entschlüsselt werden"
            }
    else
        log "INFO: Keine verschlüsselten WhatsApp Credentials gefunden"
    fi
    
    # Telegram Token
    if [[ -f "${ENCRYPTED_DIR}/telegram.enc" ]]; then
        openssl enc -d -aes-256-cbc \
            -in "${ENCRYPTED_DIR}/telegram.enc" \
            -out "${CRED_DIR}/telegram.token" \
            -pass env:MOLTBOT_MASTER_KEY \
            2>>"${LOG_FILE}" || {
                log "WARNING: Telegram Token konnte nicht entschlüsselt werden"
            }
    else
        log "INFO: Keine verschlüsselten Telegram Credentials gefunden"
    fi
    
    # Permissions sichern
    chmod 600 "${CRED_DIR}/whatsapp/creds.json" 2>/dev/null || true
    chmod 600 "${CRED_DIR}/telegram.token" 2>/dev/null || true
    
    log "Credentials entschlüsselt"
}

encrypt_credentials() {
    log "Verschlüssle Credentials..."
    
    mkdir -p "${ENCRYPTED_DIR}"
    
    # WhatsApp
    if [[ -f "${CRED_DIR}/whatsapp/creds.json" ]]; then
        openssl enc -aes-256-cbc \
            -in "${CRED_DIR}/whatsapp/creds.json" \
            -out "${ENCRYPTED_DIR}/whatsapp.enc" \
            -pass env:MOLTBOT_MASTER_KEY \
            2>>"${LOG_FILE}"
        
        # Original sicher löschen
        shred -u "${CRED_DIR}/whatsapp/creds.json" 2>/dev/null || \
            rm -f "${CRED_DIR}/whatsapp/creds.json"
    fi
    
    # Telegram
    if [[ -f "${CRED_DIR}/telegram.token" ]]; then
        openssl enc -aes-256-cbc \
            -in "${CRED_DIR}/telegram.token" \
            -out "${ENCRYPTED_DIR}/telegram.enc" \
            -pass env:MOLTBOT_MASTER_KEY \
            2>>"${LOG_FILE}"
        
        # Original sicher löschen
        shred -u "${CRED_DIR}/telegram.token" 2>/dev/null || \
            rm -f "${CRED_DIR}/telegram.token"
    fi
    
    chmod 600 "${ENCRYPTED_DIR}"/*.enc 2>/dev/null || true
    
    log "Credentials verschlüsselt und Originale gelöscht"
}

cleanup() {
    local exit_code=$?
    log "Cleanup gestartet (Exit Code: ${exit_code})"
    
    # Gateway beenden falls noch läuft
    if [[ -n "${GATEWAY_PID:-}" ]]; then
        log "Beende Gateway (PID: ${GATEWAY_PID})"
        kill "${GATEWAY_PID}" 2>/dev/null || true
        wait "${GATEWAY_PID}" 2>/dev/null || true
    fi
    
    # Credentials verschlüsseln
    encrypt_credentials
    
    log "Cleanup abgeschlossen"
    exit "${exit_code}"
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    log "=== Secure Moltbot Wrapper Start ==="
    
    # Trap für sauberes Cleanup
    trap cleanup EXIT INT TERM
    
    # Credentials entschlüsseln
    decrypt_credentials
    
    # Gateway starten
    log "Starte Moltbot Gateway..."
    
    # .env laden für Gateway
    set -a
    # shellcheck disable=SC1091
    source "${MOLTBOT_HOME}/.moltbot/.env"
    set +a
    
    # Gateway im Hintergrund starten
    moltbot gateway &
    GATEWAY_PID=$!
    
    log "Gateway gestartet (PID: ${GATEWAY_PID})"
    
    # Warten auf Gateway-Process
    wait "${GATEWAY_PID}"
    
    log "Gateway beendet"
}

# ============================================================================
# SCRIPT EXECUTION
# ============================================================================

main "$@"
