# create-teaching-content

Ein kleines, lokales System, das aus gesammelten Quellen (Web-Clippings, Texten)
**druckfertige Unterrichtseinheiten** als PDF erzeugt – inspiriert von der Idee
hinter „The Periodical", aber zugeschnitten auf Unterrichtsmaterial.

**Prinzip:** Ein LLM erzeugt nur die *Struktur* (`editorial.json`), der
deterministische Code rendert daraus mit **Typst** *ein* durchpaginiertes
Dokument. Diese Trennung („File Contract") macht Ergebnisse reproduzierbar und
per Git versionierbar.

```
Clippings (.md)  ──►  [LLM: editorial.json]  ──►  build.py  ──►  Typst  ──►  PDF
                       (Struktur/Didaktik)        (deterministisch)
```

---

## Ehrlicher Workflow (halb-manuell)

Es gibt **keinen** vollautomatischen Knopfdruck – über ein Web-Abo lässt sich
ein LLM nicht programmatisch aufrufen. Der Ablauf ist bewusst schlank:

1. **Quellen sammeln** → Markdown-Dateien nach `units/<unit>/clippings/` legen
   (mit Front-Matter, siehe unten).
2. **Editorial-Schritt** → Prompt aus [`prompts/editorial.md`](prompts/editorial.md)
   + Clippings in ein LLM geben, Ausgabe als `units/<unit>/editorial.json` speichern.
3. **Bauen** → `python build.py units/<unit>`.
4. **Prüfen** → PDF gegenlesen (Fakten! Urheberrecht!), ggf. `editorial.json` anpassen, neu bauen.
5. **Versionieren** → `git add` + `git commit` (Snapshot der Einheit).

---

## Installation

**Typst** (Rendering, Pflicht):

```powershell
winget install --id Typst.Typst
# Alternativen: scoop install typst  |  cargo install typst-cli
```

**Python-Abhängigkeit** (nur Schema-Validierung, optional aber empfohlen):

```powershell
pip install -r requirements.txt
```

**Schriften:** Newsreader, Spectral und Libre Franklin (SIL OFL) sind bereits in
[`assets/fonts/`](assets/fonts/) gebündelt – `build.py` gibt Typst diesen Ordner
via `--font-path` mit, es ist also **nichts weiter zu installieren**. Details &
Lizenz: [`assets/fonts/README.md`](assets/fonts/README.md). (Ohne diese Fonts
würde Typst auf Georgia / New Computer Modern zurückfallen.)

---

## Nutzung

```powershell
# Lehrerversion (Standard: mit Lehrerhinweisen, Evidenz-Box, Differenzierung)
python build.py units/001-schweiz-2wk

# Schülerversion (ohne Lehrerteil/Lösungen)
python build.py units/001-schweiz-2wk --variant student

# PDF danach öffnen
python build.py units/001-schweiz-2wk --open

# Nur die .typ-Datei erzeugen (kein Typst nötig) – zum Inspizieren/Debuggen
python build.py units/001-schweiz-2wk --no-compile
```

Ausgaben landen in `units/<unit>/out/` (per `.gitignore` ausgeschlossen).

---

## Aufbau einer Unit

```
units/001-schweiz-2wk/
├── editorial.json        ← vom LLM erzeugt, gegen schema/editorial.schema.json validiert
├── cover.svg             ← optionales Cover-Bild (Feld "cover_image"), ersetzbar
├── clippings/            ← Quelltexte als Markdown mit Front-Matter
│   ├── 01-schweiz-1939.md
│   └── ...
└── out/                  ← generiert (main-*.typ, *.pdf)
```

**Aufbau des erzeugten Hefts:** Cover (optional mit Bild) → Überblick
(Lernziele + automatisches **Inhaltsverzeichnis** mit Seitenzahlen, in beiden
Versionen) → [Lehrerhinweise, nur Lehrerversion] → nummerierte Rubriken →
Arbeitsblätter → Quellen. Enthält eine Rubrik nur *einen* Text, dient der
Rubriktitel zugleich als Titel (kein doppelter Kopf).

**Cover-Bild:** Feld `cover_image` in `editorial.json` = Dateiname relativ zum
Unit-Ordner (PNG/JPG/**SVG**). Fehlt es, nutzt das Cover ein rein
typografisches Layout. Das mitgelieferte `cover.svg` ist ein abstrakter
Platzhalter – für den Druck durch ein eigenes/generiertes Motiv ersetzen (siehe
[`prompts/cover.md`](prompts/cover.md)).

**Clipping-Front-Matter** (die `id` verknüpft mit `editorial.json`):

```markdown
---
id: schweiz-1939
title: "Die Schweiz 1939 – Zwischen den Fronten"
source: "Quelle/Autor"
url: "https://..."
license: "Lizenz/Status – vor Verteilung klären"
---
Markdown-Text …
```

Unterstütztes Markdown: Überschriften, Absätze, Listen, Zitate, `**fett**`,
`*kursiv*`, `` `Code` ``, `[Links](url)`. Eine Zeile aus nur `___` erzeugt eine
Schreiblinie (praktisch in Arbeitsblättern).

---

## Grenzen – bitte lesen

Dieses Werkzeug erzeugt *Layout und Struktur*. Es ersetzt **keine**
fachliche/didaktische Prüfung:

- **Kein Fakten-Check.** LLM-Texte können sachlich falsch sein. Bei
  Sachfächern (Geschichte, Bio, …) **immer gegenlesen**.
- **Evidenzbasis ist Vorsicht geboten.** LLMs erfinden Effektstärken und
  Studien. Im Schema gibt es `verified`-Flags; nur als ✓ verifiziert markierte
  Angaben werden ohne Warnhinweis gedruckt, unmarkierte erscheinen mit ⚠.
  Hattie-Effektstärken sind zudem methodisch umstritten – nicht als Gütesiegel
  missbrauchen.
- **Urheberrecht.** Fremde Web-Artikel als Klassensatz zu vervielfältigen ist
  rechtlich heikel (auch der schulische Eigengebrauch hat Grenzen). Für eigene
  Verteilung entweder eigene Texte, lizenzfreie/geklärte Quellen oder korrekt
  belegte, zulässige Zitate verwenden. Die `sources`/`license`-Felder helfen
  bei der Dokumentation.

---

## Andere Ausgabeformate (Pandoc)

Neben PDF (Typst) ist der einfachste Weg zu weiteren Formaten **Pandoc** –
nicht der im Ausgangsdokument beschriebene „eine-Bibliothek-pro-Format"-Weg
(`python-docx` liest z. B. kein HTML). Pandoc kann aus Markdown/HTML u. a.
DOCX, EPUB, ODT, LaTeX erzeugen. Ein Markdown-Export der Unit lässt sich damit
weiterverarbeiten. (Noch nicht als Skript enthalten – bewusst als nächster
Ausbauschritt, siehe [PRD.md](PRD.md).)

---

## Warum Typst statt WeasyPrint?

Das Ausgangsdokument empfahl WeasyPrint (HTML+CSS→PDF). Auf Windows ist dessen
GTK/Pango/Cairo-Stack mühsam. Typst ist ein einzelnes Binary, plattform-
unabhängig, mit exzellenter Druck-Typografie und erzeugt von sich aus *ein*
durchgehend paginiertes Dokument.
