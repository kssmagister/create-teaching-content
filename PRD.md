# PRD – create-teaching-content

**Version:** 1.0 · **Stand:** 2026-07-15

## 1. Vision

Ein lokales, versionierbares Werkzeug, das aus gesammelten Quellen strukturierte,
druckfertige **Unterrichtseinheiten** erzeugt. Fokus: didaktische Struktur +
sauberes Print-Layout, bei voller Kontrolle und Reproduzierbarkeit.

## 2. Ziele

- Zeitersparnis bei der Aufbereitung von Material zu ansprechenden Heften
- Reproduzierbarkeit: jede Einheit ist ein Git-Snapshot
- Trennung von KI-Kreativität (Struktur) und deterministischem Rendering
- Ehrlichkeit über Grenzen (kein Fakten-Check, Urheberrecht, Evidenz-Vorsicht)

## 3. Nicht-Ziele (v1)

- Kein vollautomatischer LLM-Aufruf (bewusst halb-manuell, Web-Abo)
- Kein Web-Interface
- Kein automatischer Fakten-Check (menschliche Prüfung bleibt Pflicht)

## 4. Architektur

```
editorial.json (Vertrag, schema-validiert)
        │
   build.py  ──►  Typst-Quelle (templates/theme.typ)  ──►  PDF
        ▲
   clippings/*.md (Front-Matter + Markdown)
```

- **Schema:** `schema/editorial.schema.json` (versioniert, `schema_version`)
- **Rendering:** Typst-CLI, ein durchpaginiertes Dokument
- **Varianten:** `--variant teacher|student` (Lehrer- vs. Schülerversion)

## 5. Umgesetzt (MVP)

- [x] Festes, validiertes `editorial.json`-Schema (behebt Schema-Drift)
- [x] Markdown→Typst-Konverter (Überschriften, Listen, Zitate, Inline, Links)
- [x] Typst-Theme: Cover, Lehrerhinweise, Lernziel-/Evidenz-/Differenzierungs-Boxen,
      zweispaltige Artikel, Arbeitsblätter mit Schreiblinien, Kolophon
- [x] Lehrer-/Schülerversion aus einer Quelle
- [x] Evidenz-Warnhinweis + `verified`-Flags
- [x] Beispiel-Unit „Schweiz im 2. Weltkrieg"
- [x] Cover-Bild-Slot (`meta.cover_bild`, auch SVG)
- [x] Überblicksseite: Lernziele + automatisches Inhaltsverzeichnis (beide Versionen)
- [x] Nummerierte Rubriken auf eigener Seite
- [x] **Schema v2 (Reader-Modell):** Vorwissen, Einleitung, Haupttext-Blöcke
      (text/quelle/figur/tabelle), Verständnisfragen, Aufgaben mit AFB I–III,
      Glossar, Bibliografie
- [x] Abbildungen/Tabellen mit eigener Zählung + Bild-/Tabellenverzeichnis
- [x] Lösungs-Anhang via `--solutions` (frei mit teacher/student kombinierbar)
- [x] Gebündelte Fonts (Newsreader/Spectral/Libre Franklin, OFL)
- [x] Typografie: Mediävalziffern im Fließtext, Versalziffern in Tabellen,
      serifenlose AFB-Aufgabenboxen

## 6. Roadmap

**Phase 2**
- [x] Docker-Container (Typst + Fonts + Web-Schicht), `docker-compose`
- [x] Dünne FastAPI-Oberfläche: Units/Dateien verwalten, Build auslösen, PDF liefern
      (Single-User hinter Tailscale)
- [x] LLM-Automatisierung `agent.py` (Claude-API) + `kontext.json` (Steuerungsinstanz)
- [x] Ingestion `ingest.py`: `sources/` (PDF/DOCX/PPTX/XLSX/HTML/Scans) →
      Markdown via Docling, separates Image (`Dockerfile.ingest`, Compose-
      Profil `ingest`)
- [ ] Pandoc-Export (Markdown/HTML → DOCX, EPUB) als `export.py`

**Phase 3**
- [ ] Slides aus derselben `editorial.json` (Typst `touying`)
- [ ] Latein-Vokabelabgleich (Anbindung an Projekt „verte")
- [ ] Optionaler Fakten-Check-Assistent (LLM markiert zu prüfende Aussagen)

## 7. Risiken

| Risiko | Umgang |
|---|---|
| Sachliche Fehler im LLM-Text | Grounding auf `sources/`; menschliche Prüfung Pflicht |
| Erfundene Effektstärken/Studien | `geprueft`-Flags + ⚠-Kennzeichnung im PDF |
| Layout-Sprengung durch lange Texte | einspaltiger Reader, breakable-Blöcke, Prüf-Loop |
| Typst-/Font-Installation | Fonts gebündelt (`--font-path`), klare Fehlermeldungen |
