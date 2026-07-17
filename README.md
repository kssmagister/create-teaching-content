# create-teaching-content

Ein kleines, lokales System, das aus gesammelten Quellen (Web-Clippings, Texten)
**druckfertige Unterrichtseinheiten** als PDF erzeugt – inspiriert von der Idee
hinter „The Periodical", aber zugeschnitten auf Unterrichtsmaterial.

**Prinzip:** Ein LLM erzeugt nur die *Struktur* (`editorial.json`), der
deterministische Code rendert daraus mit **Typst** *ein* durchpaginiertes
Dokument. Diese Trennung („File Contract") macht Ergebnisse reproduzierbar und
per Git versionierbar.

```
sources/ (Rohmaterial)  ──►  [LLM: editorial.json]  ──►  build.py  ──►  Typst  ──►  PDF
                              (Struktur/Didaktik)         (deterministisch)
```

Das LLM verarbeitet das **Rohmaterial** in `sources/` und schreibt daraus die
strukturierte `editorial.json` (v2, Reader-Modell). `sources/` wird **nicht**
direkt gerendert – es ist der Input für den Editorial-Schritt.

---

## Ehrlicher Workflow (halb-manuell)

Es gibt **keinen** vollautomatischen Knopfdruck – über ein Web-Abo lässt sich
ein LLM nicht programmatisch aufrufen. Der Ablauf ist bewusst schlank:

1. **Material sammeln** → Quelltexte nach `units/<unit>/sources/` legen
   (Markdown/Text; PDFs/DOCX vorab z. B. mit Docling/Pandoc zu Markdown wandeln).
2. **Editorial-Schritt** → Prompt aus [`prompts/editorial.md`](prompts/editorial.md)
   + Material in ein LLM geben, Ausgabe als `units/<unit>/editorial.json` speichern.
3. **Bilder** → allfällige Abbildungen nach `units/<unit>/images/` legen (im JSON
   nur mit Dateinamen referenziert).
4. **Bauen** → `python build.py units/<unit>`.
5. **Prüfen** → PDF gegenlesen (Fakten!), ggf. `editorial.json` anpassen, neu bauen.
6. **Versionieren** → `git add` + `git commit` (Snapshot der Einheit).

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
# Lehrerversion (mit Lehrerhinweisen + Evidenz-Box)
python build.py units/001-schweiz-2wk

# Schülerversion (ohne Lehrerteil)
python build.py units/001-schweiz-2wk --variant student

# Lösungs-Anhang einfügen (unabhängig von teacher/student kombinierbar)
python build.py units/001-schweiz-2wk --solutions

# PDF danach öffnen  /  nur .typ erzeugen (kein Typst nötig)
python build.py units/001-schweiz-2wk --open
python build.py units/001-schweiz-2wk --no-compile
```

Ausgaben landen in `units/<unit>/out/` (per `.gitignore` ausgeschlossen).
Der Dateiname kodiert die Variante, z. B. `…-teacher-loesung.pdf`.

---

## Aufbau einer Unit

```
units/001-schweiz-2wk/
├── editorial.json        ← vom LLM erzeugt (Schema v2), gegen schema/ validiert
├── cover.svg             ← optionales Cover-Bild (meta.cover_bild), ersetzbar
├── sources/              ← Rohmaterial (LLM-Input, wird NICHT gerendert)
├── images/               ← Abbildungen (im JSON per Dateiname referenziert)
└── out/                  ← generiert (main-*.typ, *.pdf)
```

**Aufbau des erzeugten Hefts (Reader-Modell):** Cover → Überblick (Lernziele +
automatisches **Inhaltsverzeichnis**, in beiden Versionen) → [Lehrerhinweise,
nur Lehrerversion] → **Vorwissen → Einleitung → Haupttext** (Text, Quellen­kästen,
Abbildungen, Tabellen) → **Verständnisfragen → Aufgaben** (AFB I–III) →
**Glossar** → [Lösungen, nur mit `--solutions`] → **Bibliografie + Bild-/
Tabellenverzeichnis**. Rubriken sind nummeriert und beginnen auf neuer Seite.

**Inhaltsblöcke** definierst du in `editorial.json` (siehe
[`schema/editorial.schema.json`](schema/editorial.schema.json) und
[`prompts/editorial.md`](prompts/editorial.md)). `haupttext` ist eine geordnete
Liste von Blöcken der Typen `text`, `quelle`, `figur`, `tabelle`.

**Cover-Bild:** `meta.cover_bild` = Dateiname relativ zum Unit-Ordner
(PNG/JPG/**SVG**). Fehlt es, nutzt das Cover ein rein typografisches Layout.

**Markdown in Textfeldern:** Überschriften (`## …`), Absätze, Listen, Zitate,
`**fett**`, `*kursiv*`, `` `Code` ``, `[Links](url)` werden nach Typst
konvertiert (inkl. korrektem Escaping – kein Sanitizer nötig).

**Typografie:** Fließtext in Spectral mit **Mediävalziffern** (`onum`),
Tabellen mit Versalziffern, Aufgaben serifenlos (Libre Franklin) in farbiger
AFB-Box – gemäß gängigen Empfehlungen für Unterrichtsmaterial.

---

## Server-Betrieb (Docker + Web-Oberfläche)

Für ortsunabhängigen Zugriff (Tablet, Browser) läuft das Projekt als Container
auf dem Ubuntu-Server – bewusst **Single-User hinter Tailscale**, ohne eigene
Benutzerverwaltung.

```bash
# auf dem Server
docker compose up -d --build
# Oberfläche: http://<server-im-tailnet>:8000
```

Der Container enthält Typst + die gebündelten Fonts; `./units` ist ein
**Volume** und bleibt ein Git-Repo auf dem Host (Snapshots überleben Rebuilds).
Docling bleibt bewusst draußen (sonst GB-Image).

**Die Web-Oberfläche kann:** Einheiten anlegen/auswählen · `sources/` und
`images/` per Upload verwalten · `editorial.json` bearbeiten **mit
Live-Schema-Validierung** · PDF bauen (teacher/student/`--solutions`) · PDF
ansehen/herunterladen. Der Build läuft synchron (Typst < 1 s), daher ohne
Job-Queue.

**Lokal entwickeln (ohne Docker):**

```powershell
pip install -r requirements.txt
python -m uvicorn server.app:app --reload
# http://127.0.0.1:8000
```

**Sicherheit:** Der Port ist für den Zugriff über das private Tailnet gedacht –
nicht öffentlich exposen. Die LLM-Automatisierung (Claude-API, `agent.py`) ist
als nächster Schritt vorgesehen; `ANTHROPIC_API_KEY` ist in `docker-compose.yml`
bereits reserviert.

---

## Grenzen – bitte lesen

Dieses Werkzeug erzeugt *Layout und Struktur*. Es ersetzt **keine**
fachliche/didaktische Prüfung:

- **Kein Fakten-Check.** LLM-Texte können sachlich falsch sein. Bei
  Sachfächern (Geschichte, Latein, Bio, …) **immer gegenlesen**. Der
  Editorial-Prompt erzwingt zwar Grounding auf `sources/`, garantiert aber keine
  Korrektheit.
- **Evidenzbasis mit Vorsicht.** LLMs erfinden Effektstärken/Studien. Im Schema
  gibt es `geprueft`-Flags; nur als ✓ markierte Angaben werden ohne Warnhinweis
  gedruckt, unmarkierte erscheinen mit ⚠. Hattie-Effektstärken sind zudem
  methodisch umstritten – nicht als Gütesiegel missbrauchen.
- **Urheberrecht.** Als Lehrperson an einer kantonalen Schule bist du über die
  Gesamtverträge für den Unterrichtsgebrauch abgesichert. Die `bibliografie`
  und die Quellenangaben bei Abbildungen dienen der korrekten Attribution; sie
  decken *deinen Klasseneinsatz*, nicht zwingend eine Weitergabe darüber hinaus.

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
