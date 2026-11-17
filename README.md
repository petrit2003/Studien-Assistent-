# 🎓 Mein Studien-Assistent — Chatbot-Prototyp

Ein interaktionsfähiger Prototyp eines persönlichen KI-Studienassistenten, entwickelt mit [Streamlit](https://streamlit.io) und der [Mistral API](https://console.mistral.ai).

## Die drei Anwendungsbereiche

1. **📚 Studienorganisation & Studienverlaufsberatung** — beantworte Fragen zu Modulhandbuch, Prüfungsordnung und Anerkennungsordnung **mit Quellenangabe** (RAG aus der Wissensbasis) und berücksichtigt dein Profil und deine Deadlines.
2. **🧠 Lernstrategien & Prüfungsvorbereitung** — individuelle Lernpläne, Methodenempfehlungen und Zeitmanagement.
3. **💡 Fachliche Lernunterstützung** — verständliche Erklärungen, Praxisbeispiele und interaktive Übungsaufgaben (der Bot löst die Aufgabe nicht selbst, sondern bewertet deine Antwort).

Zusätzlich: **Deadline-Tracker** in der Seitenleiste — anstehende Fristen fließen automatisch in jede Antwort ein (z. B. „Bis wann muss ich mich anmelden?“ → der Bot kennt deine Frist).

## Schnellstart

Voraussetzung: [Python](https://www.python.org/downloads/) 3.10 oder neuer.

```bash
cd studien-assistent
pip install -r requirements.txt
streamlit run app.py
```

Die App öffnet sich automatisch im Browser (standardmäßig http://localhost:8501).

## Mistral API-Key einrichten (kostenlos)

1. Kostenlos registrieren: https://console.mistral.ai („Experiment“-Plan, kostenfrei)
2. Unter **API Keys** einen neuen Schlüssel erstellen
3. Den Key in der App in der Seitenleiste eintragen **oder** beim Start als Umgebungsvariable setzen:

```bash
MISTRAL_API_KEY=dein-key streamlit run app.py
```

Ohne Key startet die App im **Demo-Modus** (Beispielantworten) — praktisch zum Testen der Oberfläche.

## Eigene Wissensbasis einpflegen

Die Dateien in `wissensbasis/` sind aktuell **Beispieldaten**. Ersetze sie durch eure echten Dokumente:

- `modulhandbuch.md` — Modulhandbuch
- `pruefungsordnung.md` — Prüfungsordnung (PO)
- weitere Dateien möglich: `anerkennungsordnung.md`, `stundenplan.md`, … (`.md` oder `.txt`)

Am einfachsten: PDF-Text per Copy-Paste in eine `.md`-Datei übertragen, Überschriften mit `##` markieren. Die Software zerlegt die Dokumente automatisch in Abschnitte und findet beim Chatten die relevanten Passagen (retrieval-augmented generation, RAG).

## Projektstruktur

```
studien-assistent/
├── app.py                  # Die komplette Streamlit-Anwendung
├── requirements.txt        # Abhängigkeiten (nur streamlit)
├── deadlines.json          # Wird automatisch angelegt, speichert eure Deadlines
└── wissensbasis/           # Wissensbasis (RAG) — hier eure echten Dokumente ablegen
    ├── modulhandbuch.md
    └── pruefungsordnung.md
```

## Hinweise für Präsentation & Evaluation

- **Live-Demo:** Reale Szenarien vorbereiten, z. B. (1) „Bis wann muss ich mich zur Statistik-Klausur anmelden?“ (2) „Erstelle mir einen Lernplan für die Klausur in 2 Wochen“ (3) „Erkläre mir Normalverteilung und gib mir eine Übungsaufgabe“.
- **Antwortqualität bewerten:** Testfragen mit bekannter richtiger Antwort aus der PO stellen und prüfen, ob Quellen korrekt zitiert werden.
- **Grenzen & Risiken reflektieren:** Halluzinationen bei Fragen außerhalb der Wissensbasis, keine Rechtsverbindlichkeit (PO maßgeblich), Datenschutz (Chatverläufe gehen an den API-Anbieter), Abhängigkeit vom Modell.

## requirements.txt

```
streamlit>=1.40
```
