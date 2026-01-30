# Quick-Start Checkliste

## Vorbereitung (vor Installation)

- [ ] Fresh Debian 13 Server bereit
- [ ] Root-Zugang via SSH
- [ ] Z.AI Account & API Key: https://z.ai
- [ ] (Optional) Jina AI Account: https://jina.ai
- [ ] Telegram Bot erstellt bei @BotFather
- [ ] (Optional) Slack Workspace vorbereitet

## Installation (Single Bot)

```bash
# 1. Auf Server einloggen
ssh root@your-server-ip

# 2. Script herunterladen
wget https://raw.githubusercontent.com/your-repo/install-secure-moltbot.sh

# 3. Ausführbar machen
chmod +x install-secure-moltbot.sh

# 4. Installation starten
bash install-secure-moltbot.sh

# Dauer: ~10 Minuten
```

## Post-Installation

### 1. API Keys setzen
```bash
sudo -u moltbot nano /home/moltbot/.moltbot/.env

# Ersetze:
# ZAI_API_KEY=your_key      → Dein Z.AI Key
# JINA_API_KEY=your_key     → Dein Jina Key (optional)
```

### 2. Telegram verbinden
```bash
sudo -u moltbot moltbot configure --section channels

# Telegram wählen
# Bot Token eingeben (von @BotFather)
```

### 3. Service starten
```bash
systemctl enable secure-moltbot
systemctl start secure-moltbot
systemctl status secure-moltbot
```

### 4. Gateway-Zugriff testen
```bash
# Auf lokalem Rechner:
ssh -L 18789:localhost:18789 root@your-server-ip

# Im Browser öffnen:
http://localhost:18789

# Gateway Token aus .env eingeben
```

### 5. Telegram-Pairing
```bash
# In Telegram Bot anschreiben
/start

# Pairing-Code erscheint im Terminal
sudo -u moltbot moltbot pairing list

# Pairing bestätigen
sudo -u moltbot moltbot pairing approve telegram DEIN_CODE
```

### 6. Test
```
In Telegram:
"Hallo, bist du online?"

Bot sollte antworten mit GLM 4.7
```

## Multi-Bot Installation (Adam/Berta/Charlie)

```bash
# Nach Single-Bot Installation:

# 1. Multi-Bot Script ausführen
bash install-multi-bots.sh

# 2. Für jeden Bot API Keys setzen:
nano /home/adam/.moltbot/.env
nano /home/berta/.moltbot/.env
nano /home/charlie/.moltbot/.env

# 3. Slack Tokens eintragen
# (siehe multi-bot-setup-guide.md)

# 4. Services starten
systemctl start moltbot-{adam,berta,charlie}
```

## Security-Checklist

- [ ] UFW Firewall aktiv: `ufw status`
- [ ] Gateway nur loopback: `ss -tlnp | grep 18789`
- [ ] Credentials verschlüsselt: `ls -la ~/.moltbot-encrypted/`
- [ ] .env Permissions: `stat -c %a ~/.moltbot/.env` = 600
- [ ] mDNS disabled: `grep BONJOUR ~/.moltbot/.env`
- [ ] Security Audit: `moltbot security audit`

## Monitoring

```bash
# Logs live
journalctl -fu secure-moltbot

# Gateway Status
sudo -u moltbot moltbot status

# Channel Status
sudo -u moltbot moltbot channels status

# Token Usage
cat /home/moltbot/.moltbot/usage.json | jq
```

## Backup

```bash
# Manuelles Backup
tar -czf moltbot-backup-$(date +%Y%m%d).tar.gz \
  /home/moltbot/.moltbot-encrypted \
  /home/moltbot/.moltbot/.env \
  /home/moltbot/.moltbot/moltbot.json

# Verschlüsselt speichern
openssl enc -aes-256-cbc -pbkdf2 \
  -in moltbot-backup-*.tar.gz \
  -out backup.enc
```

## Troubleshooting

### Gateway startet nicht
```bash
# Logs prüfen
journalctl -xeu secure-moltbot

# Config validieren
sudo -u moltbot moltbot doctor

# Manual Start zum Debuggen
sudo -u moltbot moltbot gateway
```

### Telegram verbindet nicht
```bash
# Channel Status
sudo -u moltbot moltbot channels status --probe

# Pairing neu starten
sudo -u moltbot moltbot channels login
```

### Credentials-Fehler
```bash
# Verschlüsselung prüfen
ls -la /home/moltbot/.moltbot-encrypted/

# Neu verschlüsseln
sudo -u moltbot bash
cd ~/.moltbot-encrypted
# Manuell openssl enc commands
```

### GLM 4.7 Probleme
```bash
# Fallback auf Haiku
nano /home/moltbot/.moltbot/moltbot.json

# Ändern:
"primary": "anthropic/claude-haiku-4-5"

# Oder Z.AI API Key prüfen
echo $ZAI_API_KEY
```

## Updates

```bash
# Moltbot Update
sudo -u moltbot pnpm update -g moltbot

# Service neu starten
systemctl restart secure-moltbot

# Config migrieren
sudo -u moltbot moltbot doctor --fix
```

## Deinstallation

```bash
# Service stoppen
systemctl stop secure-moltbot
systemctl disable secure-moltbot

# Credentials entschlüsseln (Backup!)
sudo -u moltbot bash /usr/local/bin/secure-moltbot-wrapper.sh

# User löschen
userdel -r moltbot

# Systemd Service
rm /etc/systemd/system/secure-moltbot.service
systemctl daemon-reload
```

## Nächste Schritte

1. **Skills hinzufügen:**
   - `~/clawd/skills/` - eigene Skills erstellen
   - ClawdHub durchsuchen: `clawdhub search "skill-name"`

2. **Cron Jobs einrichten:**
   ```json
   {
     "automation": {
       "cron": {
         "jobs": [
           {
             "schedule": "0 9 * * *",
             "agentId": "main",
             "prompt": "Guten Morgen! Tagesbericht?"
           }
         ]
       }
     }
   }
   ```

3. **Webhooks integrieren:**
   - Gmail Pub/Sub für Email-Automation
   - GitHub Webhooks für Code-Reviews
   - Custom Webhooks für eigene Services

4. **Multi-Agent Setup:**
   - Siehe `multi-bot-setup-guide.md`
   - Adam/Berta/Charlie koordiniert aufsetzen

5. **Coolify Integration:**
   - Docker-Compose für alle Bots
   - Centralized Management
   - Auto-Deploy via Git

## Support & Docs

- **Moltbot Docs:** https://docs.molt.bot
- **Z.AI Docs:** https://docs.z.ai
- **Jina Reader:** https://jina.ai/reader/
- **GitHub Issues:** https://github.com/moltbot/moltbot/issues
- **Security Guide:** https://docs.molt.bot/gateway/security

## Wichtige Hinweise

⚠️ **Nie Public exponieren:**
- Gateway IMMER loopback-only
- Zugriff nur via SSH-Tunnel oder Tailscale

⚠️ **Credentials sichern:**
- Master Key niemals in Git
- Backups verschlüsselt aufbewahren
- Regelmäßig rotieren

⚠️ **GLM 4.7 Limitations:**
- Context-Contamination-Bug bekannt (Issue #1712)
- Für kritische Cron-Jobs Haiku nutzen
- Monitoring der Outputs empfohlen

✅ **Best Practices:**
- Security Audit regelmäßig: `moltbot security audit --deep`
- Logs täglich prüfen
- Token-Usage monitoren
- Updates zeitnah einspielen
