# Task Metadata System

Version 1.0 - Stand: 31. Januar 2026

## Übersicht

Das Task Metadata System ermöglicht es der KI, aus hunderten von Tasks automatisch die relevanten Skills für eine bestimmte Aufgabe zu identifizieren.

## Sprechende Task-IDs

### Snake-Case Format

Tasks erhalten automatisch sprechende IDs im Snake-Case-Format basierend auf dem Task-Namen:

```python
name = "Addiere drei Zahlen"
task_id = "addiere_drei_zahlen"

name = "Zähle Äpfel und Birnen"
task_id = "zaehle_aepfel_und_birnen"

name = "Berechne x+y=z"
task_id = "berechne_x_y_z"
```

### Automatische Konvertierung

- Umlaute werden ersetzt: ä→ae, ö→oe, ü→ue, ß→ss
- Nur alphanumerische Zeichen und Unterstriche
- Mehrfache Unterstriche werden reduziert
- Führende/nachfolgende Unterstriche entfernt

### Konfliktbehandlung

Bei doppelten Task-Namen wird automatisch ein Versions-Suffix angehängt:

```
duplikat_test
duplikat_test_v2
duplikat_test_v3
```

## Metadaten-Felder

### Tags (Liste)

Keywords die den Task beschreiben für semantische Suche:

```python
"tags": ["mathematik", "addition", "berechnung", "zahlen"]
```

### Category (String)

Grobe Kategorisierung des Tasks:

```python
"category": "datenverarbeitung"
```

Beispiel-Kategorien:
- datenverarbeitung
- web-scraping
- analyse
- visualisierung
- automatisierung
- kommunikation

### Input Schema (Dictionary)

Beschreibt welche Eingabedaten der Task erwartet:

```python
"input_schema": {
    "numbers": "List[int]",
    "operation": "str"
}
```

### Output Schema (Dictionary)

Beschreibt welche Ausgabedaten der Task liefert:

```python
"output_schema": {
    "result": "int",
    "execution_time": "float"
}
```

### Use Cases (Liste)

Beispiele wann dieser Skill nützlich ist:

```python
"use_cases": [
    "Addiere beliebig viele Zahlen",
    "Berechne Gesamtsummen aus Listen",
    "Summiere Preise in einer Einkaufsliste"
]
```

## Verwendung

### Task erstellen mit Metadaten

```python
from src.task_manager import TaskManager

tm = TaskManager()

task_id = tm.create_task(
    user_id=12345,
    name="Addiere drei Zahlen",
    description="Addiert drei gegebene Zahlen und gibt die Summe zurück",
    metadata={
        "tags": ["mathematik", "addition", "berechnung"],
        "category": "datenverarbeitung",
        "input_schema": {"numbers": "List[int]"},
        "output_schema": {"sum": "int"},
        "use_cases": [
            "Addiere beliebig viele Zahlen",
            "Berechne Gesamtsummen aus Listen"
        ]
    }
)

print(task_id)  # addiere_drei_zahlen
```

### Task laden und Metadaten lesen

```python
task = tm.get_task(user_id=12345, task_id="addiere_drei_zahlen")

print(task["id"])  # addiere_drei_zahlen
print(task["metadata"]["category"])  # datenverarbeitung
print(task["metadata"]["tags"])  # ["mathematik", "addition", "berechnung"]
```

### Telegram Bot Integration

```
/task create Addiere drei Zahlen
→ Task erstellt!
→ Task-ID: addiere_drei_zahlen
→ Status: active
→ Führe den Task mit /task run addiere_drei_zahlen aus
```

## KI-Discovery (Geplant)

In Zukunft kann die KI die Metadaten nutzen um automatisch passende Skills zu finden:

### Beispiel-Query

```
User: "Ich brauche ein Script das Zahlen addiert"

KI-Analyse:
- Keywords: "zahlen", "addiert"
- Kategorie: "datenverarbeitung"
- Operation: "addition"

Gefundene Skills:
1. addiere_drei_zahlen (Tags: mathematik, addition, berechnung)
   → Match: 95% (Tags + Use-Cases)
2. summiere_liste (Tags: mathematik, summe, liste)
   → Match: 80% (Tags)
```

### Semantische Suche

```python
def find_relevant_skills(user_query, all_tasks):
    """
    Findet relevante Skills basierend auf Metadaten.

    1. Extrahiere Keywords aus User-Query
    2. Vergleiche mit Tags in Tasks
    3. Vergleiche mit Use-Cases
    4. Prüfe Input/Output-Schema
    5. Ranking nach Relevanz
    """
    pass
```

## Markdown-Speicherung

Die Metadaten werden im Task-Markdown gespeichert:

```markdown
# Task: Addiere drei Zahlen

## Metadata

- ID: addiere_drei_zahlen
- Created: 2026-01-31T11:13:48
- Updated: 2026-01-31T11:13:48
- Status: active
- Version: 1

## KI Discovery Metadata

- Category: datenverarbeitung
- Tags: mathematik, addition, berechnung
- Input Schema: ```json
{
  "numbers": "List[int]"
}
```
- Output Schema: ```json
{
  "sum": "int"
}
```

**Use Cases:**
- Addiere beliebig viele Zahlen
- Berechne Gesamtsummen aus Listen

## Description

Addiert drei gegebene Zahlen und gibt die Summe zurück

## Generated Script

```python
# Script wird vom LLM generiert
```
```

## Best Practices

### Tags wählen

- Nutze präzise Keywords, keine ganzen Sätze
- 3-5 Tags pro Task sind ideal
- Denke an Synonyme (z.B. "addition", "summe", "addieren")
- Nutze Fachbegriffe wenn passend

### Category wählen

- Wähle die hauptsächliche Funktion
- Eine Category pro Task
- Halte dich an etablierte Kategorien für Konsistenz

### Input/Output-Schema

- Nutze Python-Type-Hints als Format
- Beschreibe alle wichtigen Parameter
- Sei präzise aber nicht zu detailliert

### Use Cases

- Konkrete Beispiele statt abstrakte Beschreibungen
- 2-4 Use Cases sind ideal
- Denke an verschiedene Anwendungsszenarien

## Zukunft

Geplante Erweiterungen:

1. **Vector Embeddings**: Semantische Suche via Embeddings
2. **Automatische Tag-Generierung**: LLM schlägt Tags basierend auf Description vor
3. **Skill-Recommendations**: "Ähnliche Skills die dir gefallen könnten"
4. **Usage-Tracking**: Welche Skills werden häufig zusammen genutzt?
5. **Skill-Composition**: Mehrere Skills zu Workflows kombinieren
