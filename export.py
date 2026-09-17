#!/usr/bin/env python3
"""export.py -- baut aus einer Unit (editorial.json v2) DOCX/EPUB/ODT via Pandoc.

Ablauf:
  1. editorial.json laden + gegen schema/editorial.schema.json validieren
     (gleiche Validierung wie build.py)
  2. Markdown-Zwischendatei erzeugen (gleiche Dramaturgie/Reihenfolge wie
     build.py's Typst-Ausgabe: Cover -> Lernziele -> [Lehrerhinweise] ->
     Vorwissen -> Einleitung -> Haupttext -> Verstaendnisfragen -> Aufgaben ->
     Glossar -> [Loesungen] -> Bibliografie). Textfelder in editorial.json
     sind bereits Markdown, werden also nur zusammengesetzt.
  3. mit 'pandoc' zu DOCX/EPUB/ODT kompilieren.

Nutzung:
  python export.py units/001-schweiz-2wk
  python export.py units/001-schweiz-2wk --format epub
  python export.py units/001-schweiz-2wk --format odt --variant student
  python export.py units/001-schweiz-2wk --solutions --open
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

try:
    from src.validate import validate
except Exception:  # validate optional
    validate = None

SCHEMA = ROOT / "schema" / "editorial.schema.json"


def md_table(kopf, zeilen):
    L = ["| " + " | ".join(kopf) + " |", "| " + " | ".join(["---"] * len(kopf)) + " |"]
    for row in zeilen:
        L.append("| " + " | ".join(row) + " |")
    return "\n".join(L)


def bibliografie_line(e):
    parts = []
    if e.get("autor"):
        parts.append(e["autor"])
    jahr = e.get("jahr")
    if jahr not in (None, ""):
        parts.append(f"({jahr})")
    parts.append(f'*{e["titel"]}*')
    if e.get("verlag"):
        parts.append(e["verlag"])
    if e.get("ort"):
        parts.append(e["ort"])
    line = ", ".join(parts) if len(parts) <= 1 else parts[0] + " " + ", ".join(parts[1:])
    if e.get("url"):
        line += f' — <{e["url"]}>'
    return "- " + line


def build_markdown(data, variant, solutions, unit):
    """Erzeugt eine flache Markdown-Datei, Dramaturgie analog build.py's build_typst()."""
    teacher = variant == "teacher"
    meta = data["meta"]
    L = [f'# {meta["titel"]}', ""]

    metazeile = " · ".join(x for x in [meta.get("fach"), meta.get("stufe"), meta.get("dauer")] if x)
    if metazeile:
        L += [f"*{metazeile}*", ""]

    titelseite = meta.get("titelseite", {})
    cover = titelseite.get("bild")
    if cover:
        cover_path = unit / "images" / cover
        if cover_path.exists():
            L += [f"![]({cover_path})", ""]
        else:
            print(f"  [Warnung] Titelbild '{cover}' nicht gefunden (units/<unit>/images/).")

    # --- Lernziele ---
    L += ["## Lernziele", "", "**Kognitive Lernziele**", ""]
    L += ["- " + o for o in data["lernziele"]["kognitiv"]]
    if data["lernziele"].get("fertigkeiten"):
        L += ["", "**Fähigkeiten**", ""] + ["- " + o for o in data["lernziele"]["fertigkeiten"]]
    if data["lernziele"].get("metakognitiv"):
        L += ["", "**Metakognition / Reflexion**", ""] + ["- " + o for o in data["lernziele"]["metakognitiv"]]
    L.append("")

    # --- Lehrerteil (nur teacher) ---
    if teacher and (data.get("lehrerhinweis") or data.get("evidenzbasis")):
        L += ["## Lehrerhinweise", ""]
        lh = data.get("lehrerhinweis")
        if lh:
            L += [lh["text"], ""]
            if lh.get("kernpunkte"):
                L += ["**Kernpunkte**", ""] + ["- " + k for k in lh["kernpunkte"]] + [""]
        eb = data.get("evidenzbasis")
        if eb and eb.get("studien"):
            L += ["**Evidenzbasis – vor Gebrauch prüfen** (nur ✓-markierte Angaben sind geprüft)", ""]
            for r in eb["studien"]:
                mark = "✓ " if r.get("geprueft") else "⚠ "
                es = r.get("effektstaerke")
                es_txt = f" (d = {es})" if es not in (None, "", "-") else ""
                L.append(f'- {mark}**{r["prinzip"]}**{es_txt} — {r["studie"]}')
                if r.get("anwendung"):
                    L.append(f'  {r["anwendung"]}')
            L.append("")

    # --- Vorwissen / Einleitung ---
    if data.get("vorwissen"):
        L += ["## Vorwissen", "", data["vorwissen"]["text"], ""]
    if data.get("einleitung"):
        L += ["## Einleitung", "", data["einleitung"]["text"], ""]

    # --- Haupttext ---
    L += ["## Haupttext", ""]
    for blk in data["haupttext"]:
        typ = blk["typ"]
        if typ == "text":
            L += [blk["text"], ""]
        elif typ == "quelle":
            kopf = " — ".join(x for x in [blk.get("autor"), blk.get("titel")] if x)
            if kopf:
                L.append(f"> **{kopf}**")
                L.append(">")
            L += ["> " + line for line in blk["text"].splitlines()]
            L.append("")
        elif typ == "figur":
            img_path = unit / "images" / blk["bild"]
            if not img_path.exists():
                L += [f'*[Fehlendes Bild: {blk["bild"]} (nicht in images/)]*', ""]
                print(f"  [Warnung] Bild '{blk['bild']}' nicht in images/ gefunden.")
                continue
            L.append(f'![{blk.get("beschriftung", "")}]({img_path})')
            caption = blk.get("beschriftung", "")
            if blk.get("quelle"):
                caption += f' (Quelle: {blk["quelle"]})'
            if caption:
                L.append(f"*{caption}*")
            L.append("")
        elif typ == "tabelle":
            L.append(md_table(blk["kopf"], blk["zeilen"]))
            if blk.get("beschriftung"):
                L.append(f'*{blk["beschriftung"]}*')
            L.append("")

    # --- Verstaendnisfragen ---
    if data.get("verstaendnisfragen"):
        L += ["## Verständnisfragen", ""]
        L += [f"{i}. {f}" for i, f in enumerate(data["verstaendnisfragen"], 1)]
        L.append("")

    # --- Aufgaben ---
    aufgaben = data.get("aufgaben", [])
    if aufgaben:
        L += ["## Aufgaben", ""]
        for i, a in enumerate(aufgaben, 1):
            L += [f'### Aufgabe {i} (AFB {a["afb"]})', "", a["text"], ""]

    # --- Glossar ---
    if data.get("glossar"):
        L += ["## Glossar", ""]
        for e in data["glossar"]:
            L += [f'**{e["begriff"]}**', f': {e["definition"]}', ""]

    # --- Loesungen (nur mit --solutions) ---
    if solutions:
        loes = [(i, a) for i, a in enumerate(aufgaben, 1) if a.get("loesung")]
        if loes:
            L += ["## Lösungen", ""]
            L += [f'{i}. {a["loesung"]}' for i, a in loes]
            L.append("")

    # --- Bibliografie ---
    if data.get("bibliografie"):
        L += ["## Bibliografie", ""]
        L += [bibliografie_line(e) for e in data["bibliografie"]]
        L.append("")

    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Exportiert eine Unterrichtseinheit zu DOCX/EPUB/ODT via Pandoc.")
    ap.add_argument("unit")
    ap.add_argument("--format", choices=["docx", "epub", "odt"], default="docx")
    ap.add_argument("--variant", choices=["teacher", "student"], default="teacher")
    ap.add_argument("--solutions", action="store_true", help="Loesungs-Anhang einfuegen")
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args()

    unit = Path(args.unit).resolve()
    ed_path = unit / "editorial.json"
    if not ed_path.exists():
        sys.exit(f"FEHLER: {ed_path} nicht gefunden.")
    data = json.loads(ed_path.read_text(encoding="utf-8"))

    if validate is not None:
        errors, warnings = validate(data, SCHEMA)
        for w in warnings:
            print(f"  [Warnung] {w}")
        if errors:
            print("FEHLER: editorial.json entspricht nicht dem Schema:")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)

    if shutil.which("pandoc") is None:
        sys.exit("FEHLER: 'pandoc' nicht gefunden. Installieren: apt-get install pandoc (im Container bereits enthalten).")

    out_dir = unit / "out"
    out_dir.mkdir(exist_ok=True)

    suffix = args.variant + ("-loesung" if args.solutions else "")
    md_path = out_dir / f"main-{suffix}.md"
    md_path.write_text(build_markdown(data, args.variant, args.solutions, unit), encoding="utf-8")
    print(f"  Markdown geschrieben: {md_path}")

    out_path = out_dir / f"{unit.name}-{suffix}.{args.format}"
    cmd = ["pandoc", str(md_path), "-o", str(out_path),
           "--metadata", f'title={data["meta"]["titel"]}', "--metadata", "lang=de"]
    if args.format == "epub":
        cover = data["meta"].get("titelseite", {}).get("bild")
        if cover and (unit / "images" / cover).exists():
            cmd += [f"--epub-cover-image={unit / 'images' / cover}"]

    res = subprocess.run(cmd)
    if res.returncode != 0:
        sys.exit(res.returncode)
    print(f"\nFertig: {out_path}")

    if args.open:
        try:
            import os
            os.startfile(out_path)
        except AttributeError:
            subprocess.run(["xdg-open", str(out_path)])


if __name__ == "__main__":
    main()
