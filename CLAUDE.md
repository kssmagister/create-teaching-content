# CLAUDE.md – Projektkontext create-teaching-content

## Was ist dieses Projekt?

Ein lokales/serverseitiges System, das aus gesammelten Quellen **druckfertige
Unterrichtseinheiten** als PDF erzeugt. Prinzip („File Contract"): Ein LLM
erzeugt nur die *Struktur* (`editorial.json`), deterministischer Code rendert
daraus mit **Typst** ein durchpaginiertes PDF.

```
sources/ (Rohmaterial)  →  [LLM: editorial.json]  →  build.py  →  Typst  →  PDF
                            (Struktur/Didaktik)       (deterministisch)
```

**GitHub:** `git@github.com:kssmagister/create-teaching-content` (privat).
Entwicklung läuft auf dem **Ubuntu-Server** (Docker nativ). Server = Quelle der
Wahrheit; andere Kopien nur via `git pull` nachziehen.

---

## Tech-Stack

- **Python 3.12** (Steuerung, Markdown→Typst-Konverter, Schema-Validierung)
- **Typst** (Satz/Rendering, ein Binary; Fonts in `assets/fonts/` gebündelt)
- **FastAPI + uvicorn** (Web-Schicht: Units/Dateien verwalten, Build, PDF)
- **Docker** (`Dockerfile` + `docker-compose.yml`), Single-User hinter Tailscale
- Keine JS-Build-Kette; die UI ist eine statische Seite mit Vanilla-JS.

---

## Verzeichnisstruktur

```
create-teaching-content/
├── build.py                 ← CLI: editorial.json → PDF (validieren, Bilder, Typst)
├── agent.py                 ← CLI: sources/ → editorial.json (Claude-API, gestuft)
├── ingest.py                ← CLI: sources/* → Markdown (Docling, OCR); eigenes Image
├── export.py                ← CLI: editorial.json → DOCX/EPUB/ODT (Pandoc, im Haupt-Container)
├── schema/editorial.schema.json  ← Schema v2 (Reader-Modell), versioniert
├── src/
│   ├── markup.py            ← Markdown→Typst (Escaping via Konvertierung, KEIN Sanitizer)
│   └── validate.py          ← jsonschema-Validierung (optional)
├── templates/theme.typ      ← Layout: Cover, Rubriken, Callouts, Abbildung/Tabelle,
│                               Quellenkasten, AFB-Aufgabenbox, Glossar, Bibliografie
├── prompts/                 ← editorial.md (Editorial-Agent), worksheet.md, cover.md
├── assets/fonts/            ← Newsreader/Spectral/Libre Franklin (SIL OFL) + Lizenzen
├── server/
│   ├── app.py               ← FastAPI: /api/units, upload, editorial, build, pdf
│   └── static/index.html    ← Tablet-taugliche Oberfläche
├── units/<unit>/
│   ├── editorial.json       ← generierter Content (Schema v2)
│   ├── sources/             ← Rohmaterial (LLM-Input, wird NICHT gerendert)
│   ├── sources/_originals/  ← von ingest.py archivierte Rohdateien (PDF/DOCX/…)
│   ├── images/              ← Abbildungen (im JSON per Dateiname referenziert)
│   └── out/                 ← generiert (main-*.typ, *.pdf); gitignored
├── Dockerfile · docker-compose.yml · .env.example  ← Haupt-Container (schlank)
├── Dockerfile.ingest · requirements-ingest.txt      ← separates Docling-Image
└── README.md · PRD.md
```

---

## Schema v2 (Reader-Modell)

`editorial.json` mit `schema_version` `"2.0"`, deutsche ASCII-Keys. Felder:

- `meta` (titel, fach, stufe, dauer?, cover_bild?, cover_zeilen?)
- `lernziele` (kognitiv[], fertigkeiten[]?, metakognitiv[]?)
- `lehrerhinweis?` (text, kernpunkte[]?) – nur in der Lehrerversion
- `evidenzbasis?` (prinzipien[]?, studien[]{studie, prinzip, effektstaerke?, anwendung?, **geprueft**})
- `vorwissen?` (text) · `einleitung?` (text)
- `haupttext[]` – geordnete Blöcke, `typ`: `text` | `quelle` | `figur` | `tabelle`
- `verstaendnisfragen[]?` (ohne AFB/Lösung)
- `aufgaben[]?` ({afb: 1|2|3, text, loesung?})
- `glossar[]?` ({begriff, definition}) · `bibliografie[]?` · `schlagwoerter[]?`

**Dramaturgie im PDF:** Cover → Überblick (Lernziele + Inhaltsverzeichnis) →
[Lehrerhinweise] → Vorwissen → Einleitung → Haupttext → Verständnisfragen →
Aufgaben → Glossar → [Lösungen] → Bibliografie + Bild-/Tabellenverzeichnis.

---

## Bauen & Betreiben

```bash
# CLI
python build.py units/<unit> [--variant teacher|student] [--solutions] [--open] [--no-compile]

# Web-Schicht lokal
uvicorn server.app:app --reload            # http://127.0.0.1:8000

# Container (Server)
docker compose up -d --build               # http://<server-im-tailnet>:8000

# Ingestion (separates, schweres Docling-Image; nicht Teil von "up")
docker compose --profile ingest run --rm ingest python ingest.py units/<unit> [--force]

# Export (Pandoc, im Haupt-Container)
python export.py units/<unit> [--format docx|epub|odt] [--variant teacher|student] [--solutions] [--open]
```

`--variant` (Lehrer/Schüler) und `--solutions` (Lösungs-Anhang) sind frei
kombinierbar; der Dateiname kodiert die Variante (z. B. `…-teacher-loesung.pdf`).

---

## Konventionen

- **Sichtbare Texte** (UI, PDF, Fehlermeldungen): echte Umlaute (ä, ö, ü, ß).
- **Code-Interna** (Variablen, Keys, Kommentare): ASCII (ae, oe, ue).
- **Commit-Messages auf Deutsch**, mit echten Umlauten.
- Typst-Fonts immer via `--font-path assets/fonts` (macht build.py automatisch).

---

## Wichtige Fakten / Fallstricke

- **Kein Escaping-Problem via `json()`:** Per Typst `json()` eingelesene Strings
  sind Textinhalt → Sonderzeichen (`_ * # < >`) erscheinen literal, kein Crash.
  Für Markdown-*Formatierung* konvertiert `markup.py` sauber nach Typst
  (konvertieren statt maskieren). Ein „Regex-Sanitizer" ist unnötig.
- **Kein Fakten-Check.** LLM-Texte immer gegenlesen (Geschichte/Latein). Der
  Editorial-Prompt erzwingt Grounding auf `sources/`, garantiert aber nichts.
- **Evidenzbasis:** `geprueft: true` wird ohne Warnhinweis gedruckt, sonst ⚠.
- **Urheberrecht:** Nutzer ist kantonale Lehrperson → Gesamtverträge decken den
  Unterrichtsgebrauch. `bibliografie`/Bildquellen dienen der Attribution.
- **Secrets:** `.env` (gitignored) für `ANTHROPIC_API_KEY`; `.env.example` als Vorlage.

---

## Status & nächster Schritt

**Fertig & verifiziert:** Schema v2 + Reader-Layout, Fonts gebündelt, CLI-Build,
Docker-Container, FastAPI-Web-Schicht (Upload/Build/Download, Schema-Validierung).

**Schritt 3 (`agent.py`, LLM-Automatisierung) ist fertig:** modulare Prompts
(Lernziele → Vorwissen/Einleitung → Haupttext → Aufgaben → Glossar/Bibliografie),
`kontext.json` als geteilter Zustand (Grounding gegen Halluzination), Claude-API
Backend, Endpoint `POST /api/units/{unit}/generate` + Button in der UI.

**`ingest.py` (sources/ → Markdown via Docling) ist ebenfalls fertig:** eigenes,
schweres Docker-Image (`Dockerfile.ingest`, Compose-Profil `ingest`, bewusst
getrennt vom schlanken Haupt-Container), OCR für Scans/Fotos, mehr Formate
(PDF/DOCX/PPTX/XLSX/HTML). Aufruf: `docker compose --profile ingest run --rm
ingest python ingest.py units/<unit>`.

**`export.py` (editorial.json → DOCX/EPUB/ODT via Pandoc) ist ebenfalls
fertig:** läuft im Haupt-Container (Pandoc ist ein schlankes Binary, anders
als Docling); baut die gleiche Dramaturgie wie `build.py` als Markdown und
kompiliert damit.

**Roadmap danach:** Slides via Typst `touying`, Latein-Vokabelabgleich.
