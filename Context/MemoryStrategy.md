# Crowdbot Memory 2.0 - Architektur und Implementierungsstrategie

**Version:** 2.0
**Stand:** 30. Januar 2026
**Status:** Geplant (Dokumentation abgeschlossen)

---

## Überblick

Memory 2.0 ist ein hierarchisches, intelligentes Gedächtnis-System für Crowdbot, das auf der Analyse von Moltbot basiert und dessen beste Praktiken mit einer neuen dateibasierten Architektur kombiniert.

### Kernprobleme von Memory V1

1. **Unbegrenztes Wachstum:** memory.md wird immer größer ohne Bereinigung
2. **Keine Priorisierung:** Alle Informationen werden gleich behandelt
3. **Schlechte Performance:** Bei langen Konversationen wird das Laden langsam
4. **Kontextverlust:** Alte wichtige Informationen werden nicht strukturiert bewahrt
5. **Fehlende Archivierung:** Keine Möglichkeit alte Details nachzuschlagen

### Ziele von Memory 2.0

- **Skalierbarkeit:** System funktioniert auch nach Jahren täglicher Nutzung
- **Intelligenz:** LLM-basierte Bewertung der Wichtigkeit von Informationen
- **Performance:** Schneller Zugriff auf relevante Kontexte
- **Transparenz:** Nutzer kann alle Stufen der Archivierung einsehen
- **Flexibilität:** Balance zwischen Detailgrad und Speichereffizienz

---

## Moltbot-Analyse: Übernommene Strategien

Nach ausführlicher Analyse von Moltbot wurden folgende Strategien identifiziert und für Crowdbot adaptiert:

### 1. Progressive Verdichtung (Compaction & Summarization)

**Moltbot-Ansatz:**
- Split Message-Historie in Chunks
- Chunk-basierte Zusammenfassung via LLM
- Fallback-Kaskade bei Fehlern
- Adaptive Chunk-Größe basierend auf Context Window

**Crowdbot-Adaption:**
- Tagesdateien werden nach 7 Tagen zu Wochenzusammenfassungen verdichtet
- Wochendateien werden nach 30 Tagen zu Monatszusammenfassungen verdichtet
- Originale werden archiviert, nicht gelöscht
- LLM erstellt semantische Zusammenfassungen statt mechanischem Kürzen

### 2. Dual-Trigger-System

**Moltbot-Ansatz:**
- Idle-basiert UND Age-basiert für Container-Pruning
- Kombiniert Zeit- und Aktivitäts-Metriken

**Crowdbot-Adaption:**
- Zeit-basiert: Nach X Tagen bereinigen (1/7/30/365 Tage)
- Größen-basiert: Bei > 5MB Dateigröße Bereinigung triggern
- Frequenz-basiert: Häufig erwähnte Themen länger behalten

### 3. Soft Trim vor Hard Delete

**Moltbot-Ansatz:**
- 30% Auslastung: Soft Trim (Head + Tail behalten)
- 50% Auslastung: Hard Clear (komplettes Löschen)
- Gradueller Abbau statt abrupter Löschung

**Crowdbot-Adaption:**
- T+1 Tag: Soft Trim (unwichtige Details entfernen, Kern behalten)
- T+7 Tage: Summarization (Tagesdateien → Wochenzusammenfassung)
- T+30 Tage: Weitere Verdichtung (Wochen → Monat)
- T+365 Tage: Nur Essentials (Monat → Jahr)

### 4. LRU-Prinzip (Least Recently Used)

**Moltbot-Ansatz:**
- Sortierung nach `lastSeenAt` Timestamp
- Behalte die jüngsten 1000 Conversations
- Älteste werden zuerst gelöscht

**Crowdbot-Adaption:**
- Kombination aus Recency (wie kürzlich) und Frequency (wie oft)
- Wichtigkeits-Score entscheidet über Retention
- Auch alte aber wichtige Informationen werden bewahrt

### 5. Schutzmaßnahmen

**Moltbot-Ansatz:**
- Behält immer die letzten 3 Assistant-Nachrichten
- Schneidet nichts vor der ersten User-Nachricht

**Crowdbot-Adaption:**
- Letzte 7 Tage nie automatisch bereinigen
- `important/preferences.md` nie bereinigen
- Benutzer-Fragen immer behalten (nur Antworten kürzen)
- Projektentscheidungen explizit markieren und schützen

---

## Dateistruktur

```
/data/users/{user_id}/
├── memory.md                    # Master Index (Inhaltsverzeichnis)
├── daily/
│   ├── 20260130.md             # Heute: Volle Details
│   ├── 20260129.md             # Gestern: Volle Details
│   ├── 20260128.md             # Vorgestern: Soft Trim angewendet
│   ├── 20260127.md             # T-3: Soft Trim
│   └── ...
├── weekly/
│   ├── 2026-W05.md             # KW 5: Zusammenfassung von 7 Tagesdateien
│   ├── 2026-W04.md             # KW 4: Zusammenfassung
│   └── ...
├── monthly/
│   ├── 2026-01.md              # Januar 2026: Zusammenfassung aller Wochen
│   ├── 2025-12.md              # Dezember 2025
│   └── ...
├── archive/
│   ├── daily/
│   │   ├── 20260101.md         # Volle Tagesdatei archiviert
│   │   ├── 20250901.md.gz      # > 90 Tage: komprimiert
│   │   └── ...
│   ├── weekly/
│   │   ├── 2025-W52.md         # Volle Wochenzusammenfassung
│   │   └── ...
│   └── monthly/
│       ├── 2025-06.md          # Alte Monatszusammenfassungen
│       └── ...
└── important/
    └── preferences.md           # Persistente Präferenzen (nie bereinigt)
```

---

## Memory.md Format (Master Index)

Das Inhaltsverzeichnis ist die zentrale Anlaufstelle für das LLM, um relevante Informationen zu finden.

```markdown
# Crowdbot Langzeitgedächtnis für Raimund

Erstellt: 2026-01-15
Letzte Aktualisierung: 2026-01-30 18:17:00
Letzte Bereinigung: 2026-01-30 04:00:00

---

## Wichtige Persönliche Informationen

### Interessen & Präferenzen
- **Nicht interessiert an:** Fußball (erwähnt 2025-12-10, konsistent)
- **Aktive Projekte:**
  - AWS Zertifizierungen (häufig seit 2025-12, Status: laufend)
  - Crowdbot Entwicklung (tägliche Arbeit seit 2026-01-15)
- **Lieblingsserie:** Game of Thrones (abgeschlossen, positiv bewertet)

### Wohnort & Kontext
- Wohnort: Marmagen, Nettersheim, Kreis Euskirchen, Nordrhein-Westfalen
- Fragt häufig nach lokalem Wetter und Veranstaltungen
- Interesse an regionalen Events

### Persönliche Details
- Name: Raimund
- Beruf: Software-Entwickler
- Sprache: Deutsch (bevorzugt)

**Vollständige Präferenzen:** [important/preferences.md](important/preferences.md)

---

## Konversationshistorie (Chronologisch, neueste zuerst)

### 2026-01-30 (Heute) - [Details](daily/20260130.md)

**Themen:** Memory-Optimierung, Moltbot-Analyse, TV-Programm-Anfragen
**Wichtigkeit:** Hoch (strategische Projektentscheidung)

**Wichtige Erkenntnisse:**
- Entwickelt neue Memory-Strategie mit hierarchischer Archivierung
- Analysiert Moltbots technische Implementierung für Best Practices
- Entscheidung: LLM-basierte Wichtigkeitsbewertung statt Regeln
- Entscheidung: 7 Tage Schutzfrist für neue Einträge
- Entscheidung: Archiv-Kompression nach 90 Tagen

**Temporäre Fakten (verfallen nach 24h):**
- TV heute 20:15 Uhr: ZDF Handball-EM, Sat1 "Die Rettung...", ProSieben "Tribute von Panem"
- Wetter Marmagen: Morgen 1-6°C wechselnd bewölkt, Übermorgen -1-4°C mit Regen

**Gesprächskontext:**
- Mehrere TV-Programm-Anfragen (ZDF, Sat1, ProSieben, sixx)
- Technische Recherchen zu Moltbot-Implementierung
- Diskussion über Memory-Management-Strategien

---

### 2026-01-29 (Gestern) - [Details](daily/20260129.md)

**Themen:** Melania Trump Film, Wetter Marmagen, Veranstaltungen
**Wichtigkeit:** Niedrig (einmalige Fakten-Anfragen)

**Zusammenfassung:**
- Recherche zu Melania-Dokumentation und Donald Trumps Reaktion
- Wettervorhersage für Marmagen abgerufen
- Frage nach Veranstaltungen in KW 6

---

### Kalenderwoche 5 (2026-01-27 bis 2026-02-02) - [Zusammenfassung](weekly/2026-W05.md)

**Hauptaktivitäten:** Crowdbot Memory-System Design, lokale Event-Recherchen
**Wichtigkeit:** Hoch (Projekt-Entwicklung)

**Schlüsselthemen:**
- Intensive Arbeit an Memory 2.0 Architektur
- Moltbot-Analyse für Best Practices
- Mehrere Recherchen zu lokalen Veranstaltungen

---

### Kalenderwoche 4 (2026-01-20 bis 2026-01-26) - [Zusammenfassung](weekly/2026-W04.md)

**Hauptaktivitäten:** Crowdbot Initial-Setup, erste Tests
**Wichtigkeit:** Hoch (Projekt-Start)

---

### Januar 2026 - [Zusammenfassung](monthly/2026-01.md)

**Projekt:** Crowdbot Version 1.0 Entwicklung und Produktiv-Release
**Wichtigkeit:** Sehr Hoch (Major Milestone)

**Highlights:**
- Komplette Neuentwicklung von Crowdbot als Moltbot-Alternative
- Integration von GLM-4.7, Perplexity, Jina Deep Research
- Sicherheits-Implementierung (Authentifizierung, TTS-Kompatibilität)
- 32 Tests geschrieben und bestanden
- Produktiv-Release am 30.01.2026

---

## Meta-Statistiken

- **Gesamtgespräche:** 147
- **Häufigstes Thema:** Software-Entwicklung (34%), AWS Zertifizierungen (18%)
- **Durchschnittliche Gesprächslänge:** 12 Nachrichten
- **Aktivste Tageszeit:** 15:00-18:00 Uhr
- **Memory-Größe:**
  - Aktive Tagesdateien: 2.3 MB (7 Tage)
  - Wochenzusammenfassungen: 890 KB (4 Wochen)
  - Monatszusammenfassungen: 450 KB (2 Monate)
  - Archiv komprimiert: 1.2 MB (120 Tage)
  - Gesamtgröße: 4.84 MB

---

## Bereinigungsstatus

- **Letzte Bereinigung:** 2026-01-30 04:00:00
- **Nächste Bereinigung:** 2026-01-31 04:00:00
- **Gelöschte Einträge (letzte 24h):** 23 temporäre Fakten
- **Archivierte Dateien:** 2 (20260123.md → archive/daily/)
- **Neue Zusammenfassungen:** 1 (2026-W04.md erstellt)
```

---

## Wichtigkeits-Scoring-System

Das Herzstück von Memory 2.0 ist die intelligente Bewertung der Wichtigkeit von Konversationen.

### Scoring-Faktoren

Jeder Gesprächsabschnitt erhält einen Score von 0-10 Punkten:

#### 1. Häufigkeit (0-3 Punkte)
- **3 Punkte:** Thema wird täglich oder wöchentlich erwähnt (z.B. "AWS Zertifizierung")
- **2 Punkte:** Thema wird mehrfach im Monat erwähnt
- **1 Punkt:** Thema wird 2-3 Mal erwähnt
- **0 Punkte:** Thema wird nur einmal erwähnt (z.B. "TV-Programm heute")

#### 2. Recency (0-2 Punkte)
- **2 Punkte:** In den letzten 7 Tagen erwähnt
- **1 Punkt:** In den letzten 30 Tagen erwähnt
- **0 Punkte:** Älter als 30 Tage

#### 3. Explizite Wichtigkeit (0-2 Punkte)
- **2 Punkte:** Nutzer sagt explizit "Merke dir das", "wichtig", "entscheidend"
- **1 Punkt:** Nutzer fragt mehrfach nach demselben Thema
- **0 Punkte:** Keine expliziten Marker

#### 4. Persönliche Relevanz (0-3 Punkte)
- **3 Punkte:** Präferenzen, Abneigungen, persönliche Eigenschaften
- **2 Punkte:** Projektentscheidungen, strategische Überlegungen
- **1 Punkt:** Persönliche Ereignisse, Erlebnisse
- **0 Punkte:** Allgemeine Fakten-Anfragen

### Retention-Regeln basierend auf Score

- **Score 8-10 (Sehr Wichtig):**
  - Persistent in memory.md
  - Zusätzlich in important/preferences.md
  - Nie automatisch entfernen

- **Score 5-7 (Wichtig):**
  - In memory.md für 30 Tage
  - In Wochen-/Monatszusammenfassungen behalten
  - Nach 1 Jahr archivieren

- **Score 2-4 (Mäßig wichtig):**
  - In memory.md für 7 Tage
  - Nach 7 Tagen: Nur in Tagesdatei (archiviert)
  - Wochenzusammenfassung: Nur wenn relevant für andere Themen

- **Score 0-1 (Unwichtig):**
  - Nach 24 Stunden aus memory.md entfernen
  - Verbleibt in Tagesdatei für 7 Tage
  - Wird in Zusammenfassungen nicht erwähnt
  - Beispiele: TV-Programm, Wetter, einmalige Fakten

### LLM-Prompt für Scoring

```python
IMPORTANCE_SCORING_PROMPT = """
Analysiere die folgende Konversation und bewerte ihre Wichtigkeit für das Langzeitgedächtnis.

Konversation:
{conversation_snippet}

Bisherige Erwähnungen dieses Themas: {frequency_count}
Zeitpunkt: {timestamp}
Tage seit erster Erwähnung: {days_since_first_mention}

Bewerte anhand dieser Kriterien:

1. Häufigkeit (0-3 Punkte):
   - Wie oft wurde dieses Thema bereits erwähnt?
   - Ist es ein wiederkehrendes Interesse?

2. Recency (0-2 Punkte):
   - Wie aktuell ist die Information?
   - Wird sie bald veraltet sein?

3. Explizite Wichtigkeit (0-2 Punkte):
   - Hat der Nutzer die Wichtigkeit betont?
   - Wurde mehrfach nachgefragt?

4. Persönliche Relevanz (0-3 Punkte):
   - Betrifft es persönliche Präferenzen oder Eigenschaften?
   - Ist es eine strategische Entscheidung?
   - Hat es langfristige Bedeutung?

Gib eine Antwort im folgenden JSON-Format:
{
  "score": 7,
  "frequency_points": 2,
  "recency_points": 2,
  "explicit_points": 1,
  "relevance_points": 2,
  "reasoning": "Das Thema AWS Zertifizierungen wurde häufig erwähnt (2 Punkte), ist sehr aktuell (2 Punkte), wird vom Nutzer aktiv vorangetrieben (1 Punkt) und hat langfristige Karriere-Relevanz (2 Punkte). Gesamtscore: 7 - Wichtig für Langzeitgedächtnis.",
  "retention_recommendation": "Behalten in Wochen- und Monatszusammenfassungen, persistent in memory.md für 30 Tage"
}
"""
```

---

## Progressive Verdichtung: Timeline

### T+0 (Heute)
- Konversation wird in `daily/YYYYMMDD.md` geschrieben
- Volle Details, keine Kürzung
- Wird auch in `memory.md` referenziert

### T+1 Tag (Soft Trim)
**Trigger:** Automatisch um 04:00 Uhr nachts via Cronjob

**Aktionen:**
1. LLM analysiert gestrige Tagesdatei
2. Wichtigkeits-Scores werden berechnet
3. Einträge mit Score 0-1 werden gekürzt:
   - **Vorher:** Vollständiger TV-Programm-Text (2000 Zeichen)
   - **Nachher:** "Fragte nach TV-Programm ZDF 20:15 Uhr (Handball-EM)"
4. Tool-Outputs > 500 Zeichen werden auf Head (200) + Tail (200) gekürzt
5. Search-Resultate werden auf Zusammenfassung reduziert

**Beispiel:**
```markdown
### Vor Soft Trim (T+0):
Benutzer: Was läuft heute auf ZDF um 20:15?
Bot: [2000 Zeichen detaillierter Text über Handball-EM Halbfinale...]

### Nach Soft Trim (T+1):
Benutzer: Was läuft heute auf ZDF um 20:15?
Bot: Handball-EM Halbfinale (30.01.2026)
```

### T+7 Tage (Weekly Summarization)
**Trigger:** Automatisch um 04:00 Uhr, wenn 7 Tagesdateien vorliegen

**Aktionen:**
1. LLM erstellt Wochenzusammenfassung aus 7 Tagesdateien
2. Fokus auf:
   - Wiederkehrende Themen
   - Wichtige Erkenntnisse (Score >= 5)
   - Projektfortschritte
   - Persönliche Ereignisse
3. Original-Tagesdateien → `archive/daily/`
4. Neue Datei: `weekly/YYYY-WXX.md`
5. `memory.md` wird aktualisiert mit Link zur Wochenzusammenfassung

**LLM-Prompt:**
```python
WEEKLY_SUMMARY_PROMPT = """
Erstelle eine strukturierte Wochenzusammenfassung aus den folgenden 7 Tagesdateien:

Zeitraum: {start_date} bis {end_date} (KW {week_number})

Tagesdateien:
{daily_files_content}

Erstelle eine Zusammenfassung mit folgender Struktur:

## Kalenderwoche {week_number} ({start_date} bis {end_date})

### Hauptthemen
- [Liste der 3-5 wichtigsten Themen]

### Wichtige Erkenntnisse & Entscheidungen
- [Projektentscheidungen, neue Erkenntnisse, strategische Überlegungen]

### Persönliche Ereignisse
- [Relevante persönliche Erlebnisse]

### Wiederkehrende Aktivitäten
- [Was wurde mehrfach gemacht/besprochen?]

### Kontext für spätere Referenz
- [Informationen die für zukünftige Gespräche relevant sein könnten]

Fokussiere dich auf Informationen mit hoher Wichtigkeit (Score >= 5).
Ignoriere einmalige Fakten-Anfragen (TV-Programm, Wetter, etc.).
"""
```

### T+30 Tage (Monthly Summarization)
**Trigger:** Automatisch um 04:00 Uhr am 1. des Monats

**Aktionen:**
1. LLM verdichtet 4-5 Wochenzusammenfassungen zu Monatszusammenfassung
2. Nur Essentials bleiben erhalten (Score >= 7)
3. Wochenzusammenfassungen → `archive/weekly/`
4. Neue Datei: `monthly/YYYY-MM.md`

### T+90 Tage (Archive Compression)
**Trigger:** Automatisch um 04:00 Uhr

**Aktionen:**
1. Alle archivierten Dateien älter als 90 Tage werden komprimiert
2. `archive/daily/YYYYMMDD.md` → `archive/daily/YYYYMMDD.md.gz`
3. Kompressionsrate: ca. 70-80% Speicherersparnis
4. Bei Bedarf: Dekompression on-the-fly

### T+365 Tage (Yearly Summarization)
**Trigger:** Automatisch um 04:00 Uhr am 1. Januar

**Aktionen:**
1. 12 Monatszusammenfassungen werden zu Jahreszusammenfassung verdichtet
2. Nur absolute Highlights und wichtige Präferenzen
3. Monatszusammenfassungen → `archive/monthly/`
4. Neue Datei: `yearly/YYYY.md`

---

## Dual-Trigger-System

Bereinigung wird durch ZWEI unabhängige Trigger ausgelöst:

### 1. Zeit-basierter Trigger (Standard)

```python
TIME_TRIGGERS = {
    "soft_trim": 1,      # Nach 1 Tag
    "weekly_summary": 7,  # Nach 7 Tagen
    "monthly_summary": 30,  # Nach 30 Tagen
    "archive_compression": 90,  # Nach 90 Tagen
    "yearly_summary": 365  # Nach 365 Tagen
}
```

### 2. Größen-basierter Trigger (Notfall)

```python
SIZE_TRIGGERS = {
    "single_file_max": 5 * 1024 * 1024,  # 5 MB pro Datei
    "total_memory_max": 100 * 1024 * 1024,  # 100 MB gesamt
    "daily_folder_max": 20 * 1024 * 1024  # 20 MB für /daily/
}

def check_size_trigger():
    if daily_folder_size > SIZE_TRIGGERS["daily_folder_max"]:
        trigger_emergency_cleanup()
        # Erzwinge Weekly Summary auch wenn < 7 Tage
```

**Beispiel-Szenario:**
- Nutzer hat 5 Tage lang jeweils 50 lange Recherchen durchgeführt
- `/daily/` Ordner ist bereits 18 MB groß
- Größen-Trigger erkennt Überschreitung
- Weekly Summary wird vorzeitig ausgelöst (nach 5 statt 7 Tagen)

---

## Kontextladen-Strategie

Beim Empfang einer User-Anfrage muss das System entscheiden, welche Memory-Dateien geladen werden.

### Standard-Kontext (Immer geladen)

```python
STANDARD_CONTEXT = [
    "memory.md",  # Master Index
    "important/preferences.md",  # Persistente Präferenzen
    "daily/{heute}.md",  # Heute
    "daily/{gestern}.md",  # Gestern
    "daily/{vorgestern}.md"  # Vorgestern
]
```

**Begründung:**
- memory.md: Schneller Überblick über alle Themen
- preferences.md: Wichtig für personalisierte Antworten
- Letzte 3 Tage: Konversationskontext für natürliche Fortsetzung

### LLM-basierte Erweiterung

Wenn Standard-Kontext nicht ausreicht, analysiert das LLM die Anfrage:

```python
CONTEXT_SELECTION_PROMPT = """
Analysiere die folgende User-Anfrage und bestimme, welche zusätzlichen Memory-Dateien relevant sind.

User-Anfrage: "{user_query}"

Verfügbare Dateien:
- Tagesdateien: {list_of_daily_files}
- Wochenzusammenfassungen: {list_of_weekly_files}
- Monatszusammenfassungen: {list_of_monthly_files}

Kriterien:
1. Bezieht sich die Anfrage auf ein spezifisches Datum oder Ereignis?
2. Erwähnt die Anfrage ein Thema, das in der Vergangenheit besprochen wurde?
3. Ist historischer Kontext notwendig um die Anfrage zu beantworten?

Antworte im JSON-Format:
{
  "additional_files": ["weekly/2026-W04.md", "daily/20260123.md"],
  "reasoning": "Die Anfrage bezieht sich auf AWS Zertifizierungen, die in KW 4 intensiv besprochen wurden."
}
"""
```

**Beispiele:**

```python
# Beispiel 1: Spezifisches Datum
User: "Was haben wir am 15. Januar besprochen?"
→ Lädt: daily/20260115.md

# Beispiel 2: Thematischer Bezug
User: "Wie war nochmal mein Plan für die AWS Zertifizierung?"
→ Lädt: weekly/2026-W03.md (dort wurde der Plan erstellt)

# Beispiel 3: Zeitraum
User: "Was waren die Highlights im Januar?"
→ Lädt: monthly/2026-01.md
```

### Token-Limit-Management

```python
MAX_MEMORY_TOKENS = 0.5 * CONTEXT_WINDOW  # 50% für Memory
MAX_MEMORY_TOKENS_GLM4 = 64000  # GLM-4.7 hat 128k Context

def load_context_with_limit(files_to_load):
    """
    Lädt Dateien bis Token-Limit erreicht ist.
    Priorität: Neuere Dateien zuerst.
    """
    loaded_files = []
    total_tokens = 0

    # Sortiere nach Datum (neueste zuerst)
    files_to_load.sort(key=lambda f: f.date, reverse=True)

    for file in files_to_load:
        estimated_tokens = len(file.content) // 4  # 4 chars ≈ 1 token

        if total_tokens + estimated_tokens > MAX_MEMORY_TOKENS:
            logger.warning(f"Token limit reached, skipping {file.name}")
            break

        loaded_files.append(file)
        total_tokens += estimated_tokens

    return loaded_files, total_tokens
```

---

## Schutzmaßnahmen

### 1. Geschützte Zeiträume

```python
PROTECTED_PERIODS = {
    "recent_days": 7,  # Letzte 7 Tage nie bereinigen
    "important_files": ["important/preferences.md"]
}
```

### 2. Geschützte Inhaltstypen

```python
ALWAYS_KEEP = [
    "user_questions",  # Alle Fragen des Nutzers
    "project_decisions",  # Projektentscheidungen (erkannt via Keywords)
    "personal_preferences",  # Präferenzen und Abneigungen
    "explicit_importance"  # Explizit als wichtig markiert
]

IMPORTANCE_KEYWORDS = [
    "merke dir", "wichtig", "entscheidend", "nie vergessen",
    "projektentscheidung", "strategie", "plan", "ziel"
]
```

### 3. User-Override

Nutzer kann Einträge explizit schützen:

```python
# Beispiel-Kommando (zukünftig):
/protect "AWS Zertifizierung Plan vom 15.01"
→ Markiert Eintrag als geschützt, wird nie bereinigt
```

### 4. Rollback-Mechanismus

```python
# Bei versehentlicher Löschung wichtiger Daten:
- Alle Original-Dateien bleiben in archive/
- memory.md wird täglich gebackupt: memory.md.backup.YYYYMMDD
- Rollback-Funktion kann alte Versionen wiederherstellen
```

---

## Implementierungs-Roadmap

### Schritt 1: Dateistruktur (Woche 1)

**Dateien zu erstellen:**
- `src/memory_manager_v2.py` (erweiterte Version)
- `src/file_structure.py` (Ordner-Management)

**Funktionen:**
```python
def create_user_structure(user_id: int):
    """Erstellt hierarchische Ordnerstruktur für neuen User."""

def migrate_from_v1(user_id: int):
    """Migriert alte memory.md zu neuer Struktur."""

def ensure_structure_exists(user_id: int):
    """Prüft und repariert Ordnerstruktur."""
```

### Schritt 2: Importance Scorer (Woche 2)

**Datei:** `src/importance_scorer.py`

```python
class ImportanceScorer:
    def __init__(self, llm_client):
        self.llm = llm_client

    def score_conversation(self, snippet, context) -> dict:
        """
        Returns:
        {
            "score": 7,
            "frequency_points": 2,
            "recency_points": 2,
            "explicit_points": 1,
            "relevance_points": 2,
            "reasoning": "...",
            "retention_recommendation": "..."
        }
        """

    def calculate_frequency(self, topic, history) -> int:
        """Berechnet Häufigkeits-Score (0-3)."""

    def detect_explicit_markers(self, text) -> int:
        """Erkennt Keywords wie 'wichtig', 'merke dir' (0-2)."""
```

### Schritt 3: Summarizer (Woche 3)

**Datei:** `src/summarizer.py`

```python
class Summarizer:
    def __init__(self, llm_client):
        self.llm = llm_client

    def create_weekly_summary(self, daily_files: list) -> str:
        """Erstellt Wochenzusammenfassung aus 7 Tagesdateien."""

    def create_monthly_summary(self, weekly_files: list) -> str:
        """Erstellt Monatszusammenfassung aus Wochen."""

    def create_yearly_summary(self, monthly_files: list) -> str:
        """Erstellt Jahreszusammenfassung."""

    def soft_trim_daily_file(self, file_path: str) -> None:
        """Wendet Soft Trim auf Tagesdatei an."""
```

### Schritt 4: Cleanup Service (Woche 4)

**Datei:** `src/cleanup_service.py`

```python
class CleanupService:
    def __init__(self, scorer, summarizer):
        self.scorer = scorer
        self.summarizer = summarizer

    def run_daily_cleanup(self):
        """Läuft täglich um 04:00 Uhr."""
        # T+1: Soft Trim
        # T+7: Weekly Summary
        # T+30: Monthly Summary
        # T+90: Compression
        # T+365: Yearly Summary

    def check_size_triggers(self) -> bool:
        """Prüft ob Größenlimits überschritten."""

    def emergency_cleanup(self):
        """Erzwingt Cleanup bei Größenüberschreitung."""

    def compress_archive(self, file_path: str):
        """Komprimiert alte Archive mit gzip."""
```

### Schritt 5: Context Loader (Woche 5)

**Datei:** `src/context_loader.py`

```python
class ContextLoader:
    def __init__(self, llm_client):
        self.llm = llm_client

    def load_context(self, user_id: int, user_query: str) -> dict:
        """
        Lädt relevanten Kontext für User-Anfrage.

        Returns:
        {
            "memory_index": "...",
            "preferences": "...",
            "recent_days": ["...", "..."],
            "additional_context": ["...", "..."],
            "total_tokens": 12500
        }
        """

    def select_relevant_files(self, query: str, available: list) -> list:
        """LLM-basierte Auswahl relevanter Dateien."""

    def respect_token_limit(self, files: list) -> list:
        """Lädt Dateien bis Token-Limit erreicht."""
```

### Schritt 6: Cronjob Setup (Woche 6)

**Datei:** `scripts/memory_cleanup_cron.py`

```python
#!/usr/bin/env python3
"""
Cronjob-Skript für automatische Memory-Bereinigung.
Läuft täglich um 04:00 Uhr.

Crontab-Eintrag:
0 4 * * * cd /path/to/Crowdbot && /path/to/venv/bin/python3 scripts/memory_cleanup_cron.py
"""

def main():
    cleanup_service = CleanupService(scorer, summarizer)
    cleanup_service.run_daily_cleanup()

if __name__ == "__main__":
    main()
```

### Schritt 7: Integration & Testing (Woche 7)

**Neue Tests:**
- `tests/test_importance_scorer.py` (10 Tests)
- `tests/test_summarizer.py` (8 Tests)
- `tests/test_cleanup_service.py` (12 Tests)
- `tests/test_context_loader.py` (10 Tests)
- `tests/test_integration_v2.py` (15 Tests)

**Gesamtsumme:** 55 neue Tests

### Schritt 8: Migration & Rollout (Woche 8)

**Migration-Skript:** `scripts/migrate_v1_to_v2.py`

```python
def migrate_user(user_id: int):
    """
    1. Alte memory.md lesen
    2. Neue Ordnerstruktur erstellen
    3. Inhalte nach daily/YYYYMMDD.md aufteilen (anhand Timestamps)
    4. memory.md als Index neu erstellen
    5. important/preferences.md extrahieren
    6. Backup der alten memory.md: memory_v1_backup.md
    """
```

---

## Beispiel-Szenarien

### Szenario 1: TV-Programm-Anfrage

**T+0 (30.01.2026 18:00 Uhr):**
```markdown
# daily/20260130.md

### Benutzer - 18:00:15
Was läuft heute auf ZDF um 20:15?

### Crowdbot - 18:00:20
Im ZDF läuft heute Abend um zwanzig Uhr fünfzehn das Halbfinale
der Handball-Europameisterschaft zweitausendsechsundzwanzig.
Dieses Spiel wird live ausgestrahlt.

[Importance Score: 1 - Temporäre Fakten-Anfrage]
```

**T+1 (31.01.2026 04:00 Uhr - Soft Trim):**
```markdown
# daily/20260130.md

### Benutzer - 18:00:15
Was läuft heute auf ZDF um 20:15?

### Crowdbot - 18:00:20
Handball-EM Halbfinale (30.01.2026)

[Soft Trim angewendet: Volltext entfernt, nur Zusammenfassung]
```

**T+7 (06.02.2026 04:00 Uhr - Weekly Summary):**
```markdown
# weekly/2026-W05.md

## Kalenderwoche 5 (27.01-02.02.2026)

### Hauptthemen
- Memory 2.0 Architektur-Planung
- Moltbot-Analyse für Best Practices
- Lokale Veranstaltungsrecherchen

[TV-Programm-Anfrage wird NICHT erwähnt - zu unwichtig]
```

### Szenario 2: AWS Zertifizierungs-Gespräch

**T+0 (15.01.2026):**
```markdown
# daily/20260115.md

### Benutzer - 14:30:00
Ich möchte dieses Jahr drei AWS Zertifizierungen machen:
Solutions Architect, Developer und SysOps Administrator.
Kannst du mir einen Lernplan erstellen?

### Crowdbot - 14:31:20
[Ausführlicher Lernplan mit Timeline, Ressourcen, etc.]

[Importance Score: 9 - Persönliches Ziel, langfristig relevant]
```

**Weitere Erwähnungen:**
- 18.01.2026: "Wie weit bin ich mit dem AWS Lernplan?"
- 22.01.2026: "Erkläre mir VPCs für die AWS Prüfung"
- 25.01.2026: "Ich habe die erste Mock-Prüfung gemacht"
- 28.01.2026: "Wann sollte ich die Solutions Architect Prüfung buchen?"

**T+7 (22.01.2026 - Weekly Summary):**
```markdown
# weekly/2026-W03.md

### Wichtige Erkenntnisse & Entscheidungen

**AWS Zertifizierungs-Plan 2026:**
Raimund hat sich entschieden, drei AWS Zertifizierungen anzugehen:
1. Solutions Architect Associate (Ziel: März 2026)
2. Developer Associate (Ziel: Mai 2026)
3. SysOps Administrator Associate (Ziel: Juli 2026)

Erstellter Lernplan beinhaltet:
- 2 Stunden täglich Lernzeit
- Kombination aus Online-Kursen, Hands-on Labs, Mock-Prüfungen
- Fokus auf praktische Erfahrung mit AWS Console

[Frequency: 4x erwähnt in KW 3]
[Importance Score: 9 - Persistent]
```

**Retention:**
- Bleibt dauerhaft in memory.md
- Wird in important/preferences.md aufgenommen
- Wird in allen Zusammenfassungen erwähnt
- Nie automatisch bereinigt

### Szenario 3: Kontextladen bei Frage

**User-Anfrage (10.02.2026):**
"Wie war nochmal mein AWS Lernplan?"

**System-Ablauf:**

1. **Standard-Kontext laden:**
   - memory.md
   - important/preferences.md
   - daily/20260210.md, 20260209.md, 20260208.md

2. **LLM-Analyse:**
   - Anfrage bezieht sich auf "AWS Lernplan"
   - Keyword-Match in memory.md: "AWS Zertifizierungs-Plan" in KW 3
   - Empfehlung: Lade `weekly/2026-W03.md`

3. **Zusätzliche Dateien laden:**
   - weekly/2026-W03.md
   - daily/20260115.md (Original-Plan)

4. **Token-Check:**
   - Gesamtgröße: 8500 Tokens
   - Limit: 64000 Tokens
   - Status: OK, alle Dateien geladen

5. **Antwort generieren:**
   Bot hat vollen Kontext und kann detailliert antworten

---

## Performance-Überlegungen

### Speicherplatz

**Beispielrechnung für 1 Jahr intensiver Nutzung:**

```
Annahmen:
- 10 Gespräche pro Tag
- Durchschnittlich 2000 Zeichen pro Gespräch
- 365 Tage

Ohne Memory 2.0:
- memory.md: 10 * 2000 * 365 = 7,3 MB (unkomprimiert)
- Problem: Wird mit der Zeit immer langsamer zu laden

Mit Memory 2.0:
- daily/ (7 Tage): 10 * 2000 * 7 = 140 KB
- weekly/ (4 Wochen): ~80 KB (verdichtet)
- monthly/ (12 Monate): ~450 KB (verdichtet)
- archive/ komprimiert: ~2 MB (80% Kompression)
- important/: ~50 KB
- Gesamt: ~2,7 MB

Ersparnis: 63% weniger Speicher
Geschwindigkeit: 96% schneller (nur 140 KB statt 7,3 MB laden)
```

### API-Kosten

**LLM-Aufrufe für Memory-Management:**

```
Täglich (Cleanup Cronjob):
- Importance Scoring: ~5 Aufrufe (je 500 Tokens input, 200 output)
- Soft Trim Entscheidungen: ~10 Aufrufe (je 300 Tokens)
- Gesamt pro Tag: ~8500 Tokens

Wöchentlich (Summarization):
- Weekly Summary: 1 Aufruf (3000 Tokens input, 800 output)

Monatlich:
- Monthly Summary: 1 Aufruf (5000 Tokens input, 1200 output)

Jährliche API-Kosten (geschätzt):
- Täglich: 8500 * 365 = 3,1M Tokens
- Wöchentlich: 3800 * 52 = 198K Tokens
- Monatlich: 6200 * 12 = 74K Tokens
- Gesamt: ~3,4M Tokens/Jahr

Bei GLM-4.7 Proxy (kostenlos): 0 Euro
Bei bezahltem Service (~$0.01/1K): ~34 Euro/Jahr
```

### Ladezeiten

**Messwerte (geschätzt):**

```
Memory V1 (nach 1 Jahr):
- Dateigröße: 7,3 MB
- Ladezeit: ~2-3 Sekunden
- Parsing: ~1 Sekunde
- LLM Context-Aufbau: ~2 Sekunden
- Gesamt: ~5-6 Sekunden

Memory V2:
- Standard-Kontext: 140 KB
- Ladezeit: ~0,2 Sekunden
- Parsing: ~0,1 Sekunden
- LLM Context-Aufbau: ~0,3 Sekunden
- Gesamt: ~0,6 Sekunden

Speedup: 8-10x schneller
```

---

## Monitoring & Logging

### Log-Events

```python
MEMORY_LOG_EVENTS = {
    "soft_trim_applied": "Soft Trim auf {file} angewendet, {bytes} gespart",
    "weekly_summary_created": "Wochenzusammenfassung {file} erstellt aus {count} Tagesdateien",
    "importance_score": "{snippet} erhielt Score {score} ({reasoning})",
    "size_trigger": "Größenlimit überschritten: {folder} hat {size}MB (Limit: {limit}MB)",
    "archive_compressed": "Archiv {file} komprimiert: {old_size} → {new_size}",
    "context_loaded": "Kontext geladen: {files} ({total_tokens} Tokens)"
}
```

### Metriken

```python
MEMORY_METRICS = {
    "total_size_mb": 2.7,
    "daily_files_count": 7,
    "weekly_files_count": 4,
    "monthly_files_count": 2,
    "archive_files_count": 120,
    "compressed_files_count": 80,
    "avg_importance_score": 3.8,
    "cleanup_runs": 365,
    "summaries_created": 64,  # 52 weekly + 12 monthly
    "tokens_saved_vs_v1": 89_000  # Geschätzt
}
```

---

## Zukünftige Erweiterungen

### Phase 2.1: User-Interface
- `/memory stats` - Zeigt Memory-Statistiken
- `/memory search <keyword>` - Sucht in allen Memory-Dateien
- `/memory timeline <datum>` - Zeigt Konversationen an bestimmtem Datum
- `/memory protect <text>` - Markiert Eintrag als geschützt

### Phase 2.2: Intelligente Querverweise
- Automatische Erkennung von Themenzusammenhängen
- Verlinkung zwischen verwandten Gesprächsabschnitten
- "Siehe auch" Hinweise in Zusammenfassungen

### Phase 2.3: Multi-Modal Memory
- Speicherung von Bildern in `archive/media/`
- Referenzen zu Dateien, die der User hochgeladen hat
- Voice-Memo-Transkripte im Memory

### Phase 2.4: Semantic Search
- Embedding-basierte Suche statt Keyword-Match
- "Ähnliche Gespräche wie..." Feature
- Themen-Clustering über Zeit

---

## Risiken & Mitigations

### Risiko 1: LLM-Fehler bei Importance Scoring

**Problem:** LLM könnte wichtige Informationen falsch bewerten

**Mitigation:**
- User kann Einträge manuell schützen via `/protect`
- Letzte 7 Tage sind immer geschützt
- Backup-System erlaubt Rollback
- Log-Einträge für alle Score-Entscheidungen

### Risiko 2: Summarization-Qualität

**Problem:** Zusammenfassungen könnten wichtige Details verlieren

**Mitigation:**
- Originale werden archiviert, nie gelöscht
- Bei Bedarf kann User auf volle Tagesdatei zugreifen
- Dual-Ansatz: memory.md (kurz) + Archiv (voll)

### Risiko 3: Cronjob-Ausfälle

**Problem:** Cleanup läuft nicht, Dateien stauen sich

**Mitigation:**
- Größen-basierter Trigger als Fallback
- Health-Check-System erkennt verpasste Cleanups
- Manuelle Trigger-Option: `/memory cleanup force`

### Risiko 4: Migration-Probleme

**Problem:** V1 → V2 Migration schlägt fehl

**Mitigation:**
- Automatisches Backup vor Migration
- Rollback-Mechanismus implementiert
- Schrittweise Migration pro User
- V1 und V2 können temporär parallel laufen

---

## Zusammenfassung

Memory 2.0 transformiert Crowdbot von einem Bot mit wachsenden Dateien zu einem intelligenten System mit strukturiertem Langzeitgedächtnis. Durch die Kombination von Moltbots bewährten Strategien mit einer transparenten dateibasierten Architektur entsteht ein System, das:

- **Skaliert:** Funktioniert auch nach Jahren intensiver Nutzung
- **Intelligent ist:** LLM-basierte Entscheidungen über Wichtigkeit
- **Performant ist:** 8-10x schneller als V1
- **Transparent ist:** User kann alle Stufen einsehen
- **Robust ist:** Mehrfache Sicherheitsmechanismen und Backups

Die Implementierung erfolgt schrittweise über 8 Wochen mit umfassenden Tests und kann als non-breaking Update ausgerollt werden.

---

**Dokumentation erstellt:** 30. Januar 2026
**Nächster Review:** Nach Phase-8-Implementierung
**Verantwortlich:** Crowdbot Development Team
