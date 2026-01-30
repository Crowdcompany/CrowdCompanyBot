# Changelog - CrowdBot

Alle wichtigen Änderungen am Projekt werden hier dokumentiert.

## [Phase 7] - 2026-01-30

### Sicherheit - Telegram-Authentifizierung

**KRITISCH:** Diese Änderungen müssen vor dem Production-Betrieb aktiviert sein!

#### Implementiert

1. **User-Allowlist System**
   - Neue Funktion `is_authorized(user_id)` in [src/bot.py:35-51](src/bot.py#L35-L51)
   - Prüft Telegram User-ID gegen ALLOWED_USER_IDS Umgebungsvariable
   - Unterstützt komma-separierte Liste von User-IDs
   - Fehlerbehandlung bei ungültigen Formaten

2. **Authentifizierungs-Middleware**
   - Neue Methode `check_authorization(update)` in [src/bot.py:100-123](src/bot.py#L100-L123)
   - Automatische Ablehnung nicht-autorisierter User
   - Freundliche Fehlermeldung an User
   - Logging von Zugriffsversuchen

3. **Handler-Absicherung**
   - Alle 6 Handler-Funktionen abgesichert:
     - `start_command()` - Zeile 166
     - `reset_command()` - Zeile 197
     - `help_command()` - Zeile 220
     - `search_command()` - Zeile 250
     - `search_md_command()` - Zeile 307
     - `handle_message()` - Zeile 401

4. **Konfiguration**
   - [.env](.env) erweitert um ALLOWED_USER_IDS=YOUR_CHAT_ID
   - [.env.example](.env.example) mit Dokumentation und Beispiel

5. **Tests**
   - Neue Test-Suite [tests/test_auth.py](tests/test_auth.py)
   - 8 Tests für alle Szenarien:
     - Autorisierter User wird akzeptiert
     - Nicht-autorisierter User wird abgelehnt
     - Multiple User-IDs funktionieren
     - Leere Liste lehnt alle ab
     - Whitespace wird korrekt behandelt
     - Ungültige Formate werden abgefangen
     - check_authorization() Integration
   - Alle Tests bestanden ✓

#### Weitere User hinzufügen

Um weitere User zu autorisieren, in [.env](.env) einfach weitere IDs hinzufügen:

```bash
ALLOWED_USER_IDS=YOUR_CHAT_ID,1234567890,9876543210
```

#### Chat-ID herausfinden

Jeder User kann seine eigene Telegram Chat-ID ganz einfach herausfinden:

1. Öffne Telegram
2. Suche nach `@userinfobot` oder `@get_id_bot`
3. Starte eine Unterhaltung mit dem Bot
4. Der Bot antwortet sofort mit deiner Chat-ID

Empfohlene Bots (alle funktionieren):
- `@get_id_bot` (vom Owner getestet und verwendet)
- `@userinfobot`
- `@getidsbot`
- `@myidbot`

#### Sicherheitshinweise

- ALLOWED_USER_IDS darf NIEMALS leer sein (sonst werden alle User abgelehnt)
- User-IDs sind öffentlich und können nicht als Secret betrachtet werden
- Zusätzliche Sicherheit durch Bot-Token-Geheimhaltung
- Bei Verdacht auf Missbrauch: Bot-Token neu generieren

#### Verhalten

**Autorisierter User (YOUR_CHAT_ID):**
- Alle Befehle funktionieren normal
- Zugriff auf alle Bot-Funktionen
- Nachrichten werden verarbeitet

**Nicht-autorisierter User:**
- Erhält Nachricht: "Entschuldigung, du bist nicht autorisiert, diesen Bot zu nutzen. Bitte kontaktiere den Bot-Administrator."
- Zugriff wird geloggt mit User-ID und Username
- Keine weitere Verarbeitung

---

## Nächste Schritte (Phase 7)

- [ ] Relative Pfade implementieren
- [ ] Input-Validierung implementieren
- [ ] Rate Limiting implementieren
- [ ] Dependencies aktualisieren
