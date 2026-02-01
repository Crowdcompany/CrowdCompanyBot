# Changelog - CrowdBot

Alle wichtigen Änderungen am Projekt werden hier dokumentiert.

## [Version 1.01 - Multi-Agenten Task-System] - 2026-02-01

### Status: PRODUKTIV MIT VERBESSERTER TASK-AUSFÜHRUNG

**Multi-Agenten System:**
- ✓ Developer-Critic Loop für bessere Code-Qualität
- ✓ Selbstüberprüfung nach Task-Ausführung
- ✓ 3 Developer-Critic Iterationen für Script-Optimierung
- ✓ Validierung der Ergebnisse mit LLM

**Behobene Probleme:**
- ✓ urllib 403 Forbidden → User-Agent Pflicht im Prompt
- ✓ Schlechte Code-Qualität → Best Practices im Prompt
- ✓ Keine Ergebnisprüfung → Validierung implementiert

**Neue Features:**
- `_validate_execution_output()` - Prüft Ergebnisse nach Ausführung
- `_build_developer_prompt()` - Developer-Agent Prompt
- `_build_improvement_prompt()` - Verbesserungs-Prompt basierend auf Feedback
- `_critic_script()` - Critic-Agent für Code-Review
- `_clean_script_code()` - Markdown-Bereinigung

**Tests:**
- 22 Task Manager Tests (5 neue für Validierung)
- Alle Tests bestehen ✓

**Phase 10 Status:**
- ✅ Prompt-Verbesserung mit Best Practices
- ✅ Selbstüberprüfung nach Ausführung
- ⏳ Auto-Fix bei Fehlschlag (noch offen)

---

## [Version 1.1 - Coolify Deployment & Security Audit] - 2026-01-30

### Status: PRODUKTIV AUF COOLIFY

**Deployment-Fixes:**
- ✓ Docker Healthcheck repariert (ps-basiert statt pgrep)
- ✓ Bot läuft erfolgreich auf Coolify
- ✓ Non-root User (botuser) im Container
- ✓ Volume für persistente Daten

**Sicherheits-Audit durchgeführt:**
- ✓ Authentifizierung: Sicher (User-Allowlist funktioniert)
- ✓ Docker-Security: Best Practices befolgt
- ✓ Secrets Management: Keine Secrets im Git
- ✓ Input-Validierung: Gut geschützt
- ⚠️ Dependencies: Veraltete Versionen mit CVEs (Update in Phase 9 geplant)
- ✓ Daten-Privacy: Lokal gespeichert, keine Cloud-Uploads
- ✓ Logging: Sicher, keine sensiblen Daten

**Neue Phasen geplant:**
- Phase 9: Dependencies aktualisieren (KRITISCH)
- Phase 10: .env Permissions korrigieren (KRITISCH)
- Phase 11: Prompt Injection Defense (Empfohlen)
- Phase 12: Rate Limiting (Empfohlen)
- Phase 13: Monitoring verbessern

**Bewertung:** System ist sicher für Produktivbetrieb, mit kleinen Verbesserungen in Phasen 9-10

---

## [Version 1.0 - Produktiv-Release] - 2026-01-30

### Status: PRODUKTIV EINSETZBAR

Crowdbot ist vollständig funktionsfähig mit allen Kernfeatures und kann produktiv eingesetzt werden.

**Implementierte Features:**
- ✓ GLM-4.7 Sprachmodell (via glmproxy.ccpn.cc)
- ✓ Telegram Bot mit Authentifizierung
- ✓ Perplexity Sonar für schnelle Faktensuche
- ✓ Jina Deep Research für ausführliche Analysen
- ✓ Markdown-basiertes Gedächtnis V1
- ✓ TTS-kompatible Ausgaben
- ✓ Tool-System mit automatischer Nutzung
- ✓ Alle 32 Tests bestanden

**Befehle:**
- /start - Bot starten
- /reset - Gedächtnis zurücksetzen
- /help - Hilfe anzeigen
- /search - Schnelle Faktensuche (Perplexity)
- /searchmd - Suche mit Markdown-Download
- /deepresearch - Ausführliche Analyse (Jina)

**In Planung:** Memory 2.0 - Hierarchisches Gedächtnis-System (Kern-Implementierung abgeschlossen, noch nicht aktiviert)

---

## [Phase 8 - Memory 2.0] - 2026-01-30

### ✓ VOLLSTÄNDIG AKTIVIERT

Memory 2.0 ist vollständig implementiert und im Bot aktiviert!

**Implementierte Komponenten:**
- file_structure.py (340 Zeilen) - Hierarchische Ordnerstruktur
- memory_manager_v2.py (550 Zeilen) - Rückwärtskompatible V2 API
- importance_scorer.py (420 Zeilen) - LLM-basierte Bewertung
- summarizer.py (380 Zeilen) - Progressive Verdichtung
- cleanup_service.py (450 Zeilen) - Automatische Bereinigung
- context_loader.py (320 Zeilen) - Intelligentes Laden
- Tests (12 Tests in test_memory_v2.py)
- migrate_v1_to_v2.py - Migrations-Skript

**Aktivierungsschritte (30.01.2026 19:35 Uhr):**
✓ bot.py auf MemoryManagerV2 umgestellt
✓ Migration von V1 zu V2 durchgeführt (User 7043093505)
✓ memory.md Index erstellt
✓ Hierarchische Ordnerstruktur angelegt (daily/, weekly/, monthly/, archive/, important/)
✓ preferences.md erstellt
✓ 38 Konversationen migriert

**Noch optional:**
- Cronjob-Setup für automatischen Cleanup (manuell via cleanup_service.py möglich)

**Neue Dateistruktur:**
```
/data/users/{user_id}/
├── memory.md                    # Master Index
├── daily/20260130.md           # Heutige Konversationen
├── weekly/                     # Wochenzusammenfassungen (noch leer)
├── monthly/                    # Monatszusammenfassungen (noch leer)
├── archive/                    # Alte archivierte Dateien
└── important/preferences.md    # Persistente Präferenzen
```

Details: [Context/MemoryStrategy.md](Context/MemoryStrategy.md)

---

## [Phase 7 - Sicherheits-Härtung] - 2026-01-30

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

**Hinweis:** Phase 7 wurde abgeschlossen. Input-Validierung und TTS-Kompatibilität sind implementiert. Relative Pfade und Rate Limiting sind optional für zukünftige Erweiterungen vorgesehen.

---

## Nächste Schritte (Optional)

- [ ] Memory 2.0 in bot.py aktivieren
- [ ] Cronjob für Memory Cleanup einrichten
- [ ] Relative Pfade implementieren (DATA_DIR aus .env)
- [ ] Rate Limiting implementieren
- [ ] Dependencies aktualisieren (requests >= 2.32.0, aiohttp >= 3.10.0)
