# Schriften

Diese Schriften sind gebündelt, damit `build.py` reproduzierbare PDFs erzeugt
(via `typst compile --font-path assets/fonts`). Alle stehen unter der
**SIL Open Font License 1.1** (Lizenztexte: `OFL-*.txt`). Keine der Familien
deklariert einen „Reserved Font Name", Modifikation und Weitergabe sind daher
zulässig.

| Familie | Dateien | Quelle |
|---|---|---|
| **Spectral** | `Spectral-*.ttf` (statische Schnitte) | google/fonts, `ofl/spectral` |
| **Libre Franklin** | `LibreFranklin.ttf`, `LibreFranklin-Italic.ttf` (variabel, wght) | google/fonts, `ofl/librefranklin` |
| **Newsreader** | `Newsreader.ttf`, `Newsreader-Italic.ttf` (variabel, wght) | google/fonts, `ofl/newsreader` |

## Änderung an Newsreader

Die Original-Variable-Fonts von Newsreader haben eine `opsz`-Achse (optische
Größe) und melden sich dadurch bei Typst als „Newsreader 16pt" o. ä., wodurch
`font: "Newsreader"` nicht auflöst. Deshalb wurde:

1. die `opsz`-Achse auf 18 fixiert (`fontTools.varLib.instancer`), die
   `wght`-Achse (Gewicht) blieb erhalten;
2. der Familienname im `name`-Table auf „Newsreader" normalisiert.

Ergebnis: Typst erkennt `Newsreader` sauber und wählt Gewichte (Regular/Medium/
Bold) sowie Kursive korrekt aus. Diese modifizierten Dateien werden gemäß OFL
ebenfalls unter der OFL weitergegeben.

Dieselben Dateien wurden zusätzlich benutzerweit in Windows installiert, sodass
Typst sie auch ohne `--font-path` findet.
