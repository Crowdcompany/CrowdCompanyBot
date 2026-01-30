# Sicherheits-Implementierungsplan

Datum: 2026-01-30
Status: Phase 1 Abgeschlossen (Telegram-Authentifizierung)
Priorität: Phase 1 KRITISCH (✓ Abgeschlossen)

## Übersicht

Basierend auf dem Sicherheitsaudit vom 2026-01-30 müssen folgende kritische Sicherheitsprobleme vor dem Production-Betrieb behoben werden.

## 1. Telegram-Authentifizierung ✓ ABGESCHLOSSEN

### Problem
Aktuell kann JEDER Telegram-User den Bot nutzen. Es gibt keine Zugriffskontrolle.

### Lösung ✓ IMPLEMENTIERT
User-Allowlist mit autorisierten Chat-IDs implementieren.

### Status: Vollständig implementiert und getestet (30.01.2026)
- ✓ is_authorized() Funktion implementiert
- ✓ check_authorization() Methode implementiert
- ✓ Alle 6 Handler abgesichert
- ✓ .env.example aktualisiert
- ✓ 8 Tests geschrieben und bestanden

### Implementierung

#### Datei: src/bot.py

**Neue Hilfsfunktion hinzufügen:**
```python
def is_authorized(user_id: int) -> bool:
    """
    Prüft ob ein Benutzer autorisiert ist.

    Args:
        user_id: Telegram User-ID

    Returns:
        True wenn autorisiert
    """
    allowed_ids_str = os.getenv("ALLOWED_USER_IDS", "")
    if not allowed_ids_str:
        return False

    allowed_ids = [int(id.strip()) for id in allowed_ids_str.split(",") if id.strip()]
    return user_id in allowed_ids
```

**Authentifizierungs-Decorator für alle Handler:**
```python
async def check_authorization(self, update: Update) -> bool:
    """Prüft Autorisierung und sendet Fehlermeldung wenn nötig."""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text(
            "Entschuldigung, du bist nicht autorisiert, diesen Bot zu nutzen. "
            "Bitte kontaktiere den Bot-Administrator."
        )
        logger.warning(f"Nicht autorisierter Zugriffsversuch von User-ID: {user_id}")
        return False

    return True
```

**In allen Handler-Funktionen am Anfang prüfen:**
```python
async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await self.check_authorization(update):
        return

    # Rest der Funktion...
```

#### Datei: .env
```
ALLOWED_USER_IDS=YOUR_CHAT_ID
```

Für mehrere User:
```
ALLOWED_USER_IDS=YOUR_CHAT_ID,1234567890,9876543210
```

#### Datei: .env.example
```
# Komma-separierte Liste von autorisierten Telegram User-IDs
ALLOWED_USER_IDS=YOUR_CHAT_ID
```

### Betroffene Funktionen
- start_command()
- reset_command()
- help_command()
- search_command()
- search_md_command()
- handle_message()

### Tests
- Autorisierter User kann Bot nutzen
- Nicht-autorisierter User erhält Ablehnung
- Leere ALLOWED_USER_IDS lehnt alle ab
- Mehrere User-IDs funktionieren

---

## 2. Relative Pfade

### Problem
Hardcodierte absolute Pfade mit Benutzername:
- `/media/xray/NEU/Code/Crowdbot/data` in src/bot.py
- `/media/xray/NEU/Code/Crowdbot/data` in src/memory_manager.py

### Lösung
Relative Pfade mit Umgebungsvariablen-Unterstützung.

### Implementierung

#### Datei: src/bot.py

**Änderung im __init__:**
```python
def __init__(
    self,
    token: Optional[str] = None,
    data_dir: str = None  # Entferne Default-Wert
):
    """
    Initialisiert den Crowdbot.

    Args:
        token: Telegram Bot Token (aus .env wenn None)
        data_dir: Verzeichnis für Benutzerdaten (aus .env oder ./data)
    """
    self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")

    if not self.token:
        raise ValueError(
            "Kein Telegram Bot Token gefunden. "
            "Bitte setze TELEGRAM_BOT_TOKEN in der .env Datei."
        )

    # Data-Dir aus Umgebung oder Standard
    if data_dir is None:
        data_dir = os.getenv("DATA_DIR", "./data")

    # Komponenten initialisieren
    self.memory_manager = MemoryManager(data_dir=data_dir)
    # ...
```

#### Datei: src/memory_manager.py

**Änderung im __init__:**
```python
def __init__(self, data_dir: str = None):
    """
    Initialisiert den Memory Manager.

    Args:
        data_dir: Basisverzeichnis für Benutzerdaten (Standard: ./data)
    """
    if data_dir is None:
        data_dir = os.getenv("DATA_DIR", "./data")

    self.data_dir = Path(data_dir)
    self.users_dir = self.data_dir / "users"
    self.users_dir.mkdir(parents=True, exist_ok=True)
```

#### Datei: .env
```
DATA_DIR=./data
```

#### Datei: .env.example
```
# Verzeichnis für Benutzerdaten (relativ zum Projektverzeichnis)
DATA_DIR=./data
```

### Tests
- Standard-Pfad ./data funktioniert
- Umgebungsvariable überschreibt Standard
- Verzeichnis wird automatisch erstellt

---

## 3. Input-Validierung

### Problem
User-Input wird ohne ausreichende Validierung verarbeitet.

### Lösung
Strikte Input-Validierung mit Längen-Limits und Sanitization.

### Implementierung

#### Datei: src/bot.py

**Neue Validierungsfunktionen:**
```python
def validate_message_length(text: str, max_length: int = 4000) -> tuple[bool, str]:
    """
    Validiert die Länge einer Nachricht.

    Args:
        text: Zu prüfender Text
        max_length: Maximale Länge

    Returns:
        (is_valid, error_message)
    """
    if len(text) > max_length:
        return False, f"Nachricht zu lang (max {max_length} Zeichen)"
    return True, ""


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    Bereinigt einen Dateinamen von gefährlichen Zeichen.

    Args:
        filename: Ursprünglicher Dateiname
        max_length: Maximale Länge

    Returns:
        Bereinigter Dateiname
    """
    import re

    # Nur alphanumerische Zeichen, Leerzeichen, Bindestriche und Unterstriche
    safe = re.sub(r'[^\w\s-]', '', filename)

    # Leerzeichen durch Unterstriche ersetzen
    safe = safe.replace(' ', '_')

    # Mehrfache Unterstriche reduzieren
    safe = re.sub(r'_+', '_', safe)

    # Länge begrenzen
    safe = safe[:max_length]

    # Path-Traversal verhindern
    safe = os.path.basename(safe)

    return safe.strip('_')


def validate_search_query(query: str) -> tuple[bool, str]:
    """
    Validiert eine Suchanfrage.

    Args:
        query: Die Suchanfrage

    Returns:
        (is_valid, error_message)
    """
    if not query or not query.strip():
        return False, "Suchanfrage darf nicht leer sein"

    if len(query) > 500:
        return False, "Suchanfrage zu lang (max 500 Zeichen)"

    # Prüfe auf gefährliche Zeichen
    dangerous_chars = ['<', '>', '|', '&', ';', '$', '`']
    for char in dangerous_chars:
        if char in query:
            return False, f"Ungültiges Zeichen in Suchanfrage: {char}"

    return True, ""
```

**Anwendung in handle_message:**
```python
async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await self.check_authorization(update):
        return

    user_id = update.effective_user.id
    user_message = update.message.text

    # Input-Validierung
    is_valid, error_msg = validate_message_length(user_message)
    if not is_valid:
        await update.message.reply_text(error_msg)
        return

    # ... Rest der Funktion
```

**Anwendung in search_command:**
```python
async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await self.check_authorization(update):
        return

    # ... bestehender Code ...

    query = " ".join(context.args)

    # Validierung
    is_valid, error_msg = validate_search_query(query)
    if not is_valid:
        await update.message.reply_text(error_msg)
        return

    # ... Rest der Funktion
```

**Anwendung in search_md_command:**
```python
# In der Dateinamens-Erstellung (Zeile 289):
safe_query = sanitize_filename(query, max_length=50)
filename = f"search_{safe_query}.md"
```

### Tests
- Zu lange Nachrichten werden abgelehnt
- Gefährliche Zeichen in Suchanfragen werden erkannt
- Dateinamen werden korrekt bereinigt
- Path-Traversal wird verhindert

---

## 4. Rate Limiting

### Problem
Keine Limitierung von Anfragen, API-Missbrauch möglich.

### Lösung
Rate Limiter mit konfigurierbarem Limit.

### Implementierung

#### Neue Datei: src/rate_limiter.py

```python
"""
Rate Limiter für Crowdbot

Limitiert die Anzahl der Anfragen pro User in einem Zeitfenster.
"""

import time
from typing import Dict, List
from collections import defaultdict


class RateLimiter:
    """Einfacher Rate Limiter basierend auf Sliding Window."""

    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        Initialisiert den Rate Limiter.

        Args:
            max_requests: Maximale Anzahl Anfragen
            time_window: Zeitfenster in Sekunden
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[int, List[float]] = defaultdict(list)

    def is_allowed(self, user_id: int) -> bool:
        """
        Prüft ob ein User eine weitere Anfrage stellen darf.

        Args:
            user_id: Telegram User-ID

        Returns:
            True wenn erlaubt
        """
        now = time.time()

        # Entferne alte Einträge
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if now - req_time < self.time_window
        ]

        # Prüfe Limit
        if len(self.requests[user_id]) >= self.max_requests:
            return False

        # Füge neue Anfrage hinzu
        self.requests[user_id].append(now)
        return True

    def get_remaining_time(self, user_id: int) -> int:
        """
        Gibt die verbleibende Zeit bis zur nächsten erlaubten Anfrage zurück.

        Args:
            user_id: Telegram User-ID

        Returns:
            Sekunden bis zur nächsten Anfrage (0 wenn sofort erlaubt)
        """
        if not self.requests[user_id]:
            return 0

        now = time.time()
        oldest_request = min(self.requests[user_id])
        time_passed = now - oldest_request

        if time_passed >= self.time_window:
            return 0

        return int(self.time_window - time_passed)

    def reset_user(self, user_id: int):
        """
        Setzt das Rate Limit für einen User zurück.

        Args:
            user_id: Telegram User-ID
        """
        if user_id in self.requests:
            del self.requests[user_id]
```

#### Datei: src/bot.py

**Import hinzufügen:**
```python
from src.rate_limiter import RateLimiter
```

**Im __init__:**
```python
# Rate Limiter initialisieren
rate_limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
self.rate_limiter = RateLimiter(max_requests=rate_limit, time_window=60)

# Separater Rate Limiter für Deep Search (längere Cooldown)
self.search_rate_limiter = RateLimiter(max_requests=1, time_window=60)
```

**Neue Hilfsfunktion:**
```python
async def check_rate_limit(
    self,
    update: Update,
    limiter: RateLimiter = None
) -> bool:
    """
    Prüft Rate Limit und sendet Fehlermeldung wenn nötig.

    Args:
        update: Telegram Update
        limiter: Zu verwendender Rate Limiter (Standard: self.rate_limiter)

    Returns:
        True wenn erlaubt
    """
    if limiter is None:
        limiter = self.rate_limiter

    user_id = update.effective_user.id

    if not limiter.is_allowed(user_id):
        remaining = limiter.get_remaining_time(user_id)
        await update.message.reply_text(
            f"Zu viele Anfragen. Bitte warte {remaining} Sekunden."
        )
        logger.warning(f"Rate Limit erreicht für User {user_id}")
        return False

    return True
```

**In handle_message:**
```python
async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await self.check_authorization(update):
        return

    if not await self.check_rate_limit(update):
        return

    # ... Rest der Funktion
```

**In search_command:**
```python
async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await self.check_authorization(update):
        return

    # Spezielles Rate Limit für Search
    if not await self.check_rate_limit(update, self.search_rate_limiter):
        return

    # ... Rest der Funktion
```

#### Datei: .env
```
RATE_LIMIT_PER_MINUTE=10
```

#### Datei: .env.example
```
# Maximale Anfragen pro Minute pro User
RATE_LIMIT_PER_MINUTE=10
```

### Tests
- Normale Nachrichten: 10 pro Minute erlaubt
- Deep Search: 1 pro Minute erlaubt
- Überschreitung wird abgelehnt mit Wartezeit
- Reset nach Zeitfenster funktioniert

---

## 5. Dependencies Update

### Problem
Veraltete Dependencies mit bekannten Security-Issues.

### Lösung
requirements.txt aktualisieren.

### Implementierung

#### Datei: requirements.txt

```python
# Telegram Bot
python-telegram-bot==20.7

# HTTP Requests (Security Update)
requests>=2.32.0,<3.0

# Umgebungsvariablen
python-dotenv==1.0.0

# Asynchrone Unterstützung (Security Update)
aiohttp>=3.10.0,<4.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
```

#### Befehle ausführen:
```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
pip audit
```

---

## Implementierungsreihenfolge

1. **Dependencies Update** (5 Minuten)
   - requirements.txt aktualisieren
   - pip install --upgrade ausführen

2. **Relative Pfade** (10 Minuten)
   - src/bot.py ändern
   - src/memory_manager.py ändern
   - .env.example aktualisieren

3. **Telegram-Authentifizierung** (20 Minuten)
   - is_authorized() Funktion
   - check_authorization() Methode
   - Alle Handler anpassen
   - .env.example aktualisieren

4. **Rate Limiting** (30 Minuten)
   - src/rate_limiter.py erstellen
   - Integration in src/bot.py
   - Tests schreiben

5. **Input-Validierung** (30 Minuten)
   - Validierungsfunktionen
   - Integration in Handler
   - Tests schreiben

**Gesamtzeit: ca. 90 Minuten**

---

## Tests nach Implementierung

1. Starte Bot mit autorisierter User-ID
2. Teste /start, /search, /help als autorisierter User
3. Teste mit nicht-autorisierter User-ID (sollte ablehnen)
4. Sende 11 Nachrichten schnell (11. sollte abgelehnt werden)
5. Teste /search zweimal schnell (2. sollte abgelehnt werden)
6. Teste zu lange Nachricht (sollte abgelehnt werden)
7. Teste gefährliche Zeichen in /search (sollte abgelehnt werden)
8. Prüfe dass data Verzeichnis relativ angelegt wird

---

## Checkliste vor Production

- [ ] Alle 4 Sicherheitsfixes implementiert
- [ ] Dependencies aktualisiert
- [ ] Alle Tests durchgeführt und bestanden
- [ ] .env mit korrekten Werten
- [ ] Git Repository initialisiert
- [ ] .gitignore prüfen
- [ ] Erste Commits ohne .env Datei
- [ ] Bot in VM oder Container deployen
- [ ] Firewall-Regeln setzen
- [ ] Monitoring einrichten
