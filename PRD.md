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
- [x] Cover-Bild-Slot (`cover_image`, auch SVG)
- [x] Überblicksseite: Lernziele + automatisches Inhaltsverzeichnis (beide Versionen)
- [x] Nummerierte Rubriken, keine Titel-Dopplung bei Ein-Text-Rubriken

## 6. Roadmap

**Phase 2**
- [ ] Pandoc-Export (Markdown/HTML → DOCX, EPUB) als `export.py`
- [ ] Lösungsteil separat (Schülerversion strikt ohne Lösungen)
- [ ] Arbeitsblätter im Inhaltsverzeichnis

**Phase 3**
- [ ] Vorlagen-Bibliothek (mehrere Themes/Fächer)
- [ ] QR-Codes zu Quellen/Videos
- [ ] Optionaler Fakten-Check-Assistent (LLM schlägt zu prüfende Aussagen vor)

## 7. Risiken

| Risiko | Umgang |
|---|---|
| Sachliche Fehler im LLM-Text | menschliche Prüfung Pflicht; README-Hinweis |
| Erfundene Effektstärken/Studien | `verified`-Flags + ⚠-Kennzeichnung im PDF |
| Urheberrecht der Quellen | `license`/`sources`-Felder; eigene/geklärte Texte |
| Typst-/Font-Installation | Fallback-Fonts; klare Fehlermeldungen in build.py |
