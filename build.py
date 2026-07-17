#!/usr/bin/env python3
"""build.py -- baut aus einer Unit (editorial.json v2) ein PDF (Reader-Modell).

Ablauf:
  1. editorial.json laden + gegen schema/editorial.schema.json validieren
  2. Bilder (Cover + Figuren) nach out/ kopieren
  3. Typst-Quelle erzeugen (ein durchpaginiertes Dokument)
  4. mit 'typst' zu PDF kompilieren

Nutzung:
  python build.py units/001-schweiz-2wk
  python build.py units/001-schweiz-2wk --variant student
  python build.py units/001-schweiz-2wk --solutions          # Loesungs-Anhang
  python build.py units/001-schweiz-2wk --variant teacher --solutions --open
  python build.py units/001-schweiz-2wk --no-compile          # nur .typ
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.markup import md_to_typst, tstr, inline

try:
    from src.validate import validate
except Exception:  # validate optional
    validate = None

SCHEMA = ROOT / "schema" / "editorial.schema.json"
THEME = ROOT / "templates" / "theme.typ"


def tstr_num(v):
    return tstr(str(v))


def tarr(strings):
    return "(" + "".join(tstr(s) + ", " for s in strings) + ")"


def tdict(d, keys):
    parts = []
    for k in keys:
        if k in d and d[k] not in (None, ""):
            parts.append(f"{k}: {tstr(str(d[k]))}")
    return "(" + ", ".join(parts) + ")"


def objectives_body(lo):
    out = ["*Kognitive Lernziele* \\"]
    for o in lo["kognitiv"]:
        out.append("- " + inline(o))
    if lo.get("fertigkeiten"):
        out += ["", "*Fähigkeiten* \\"] + ["- " + inline(o) for o in lo["fertigkeiten"]]
    if lo.get("metakognitiv"):
        out += ["", "*Metakognition / Reflexion* \\"] + ["- " + inline(o) for o in lo["metakognitiv"]]
    return out


def build_typst(data, variant, solutions, figures):
    """figures: dict {bildname -> relativer Pfad in out/ oder None wenn fehlt}."""
    teacher = variant == "teacher"
    meta = data["meta"]
    L = ['#import "theme.typ": *', ""]
    L.append(f'#show: doc => conf(titel: {tstr(meta["titel"])}, variant: {tstr(variant)}, doc)')
    L.append("")

    # --- Cover ---
    cimg = figures.get("__cover__")
    img_arg = f", bild: {tstr(cimg)}" if cimg else ""
    L.append(
        f'#cover(titel: {tstr(meta["titel"])}, fach: {tstr(meta.get("fach", ""))}, '
        f'stufe: {tstr(meta.get("stufe", ""))}, dauer: {tstr(meta.get("dauer", ""))}, '
        f'zeilen: {tarr(meta.get("cover_zeilen", []))}, variant: {tstr(variant)}{img_arg})'
    )
    L.append("")

    # --- Ueberblick: Lernziele + Inhalt ---
    L.append("#overview[")
    L += objectives_body(data["lernziele"])
    L += ["]", ""]

    # --- Lehrerteil (nur teacher) ---
    if teacher and (data.get("lehrerhinweis") or data.get("evidenzbasis")):
        L.append("#pagebreak()")
        L.append('#heading(level: 2, outlined: false, numbering: none)[Lehrerhinweise]')
        L.append("")
        lh = data.get("lehrerhinweis")
        if lh:
            L.append("#teacher-box[")
            L.append(md_to_typst(lh["text"]))
            if lh.get("kernpunkte"):
                L += ["", "*Kernpunkte* \\"] + ["- " + inline(k) for k in lh["kernpunkte"]]
            L += ["]", ""]
        eb = data.get("evidenzbasis")
        if eb and eb.get("studien"):
            L.append('#warn-box(title: "Evidenzbasis - vor Gebrauch prüfen")[')
            L.append("Effektstärken und Studien können vom LLM stammen. Nur ✓-markierte Angaben sind geprüft. \\")
            for r in eb["studien"]:
                mark = "✓ " if r.get("geprueft") else "⚠ "
                es = r.get("effektstaerke")
                es_txt = f" (d = {es})" if es not in (None, "", "-") else ""
                L.append("- " + mark + "*" + inline(r["prinzip"]) + "*" + inline(es_txt) + " — " + inline(r["studie"]))
                if r.get("anwendung"):
                    L.append("  " + inline(r["anwendung"]))
            L += ["]", ""]

    # --- Vorwissen ---
    if data.get("vorwissen"):
        L.append("#rubrik[Vorwissen]")
        L.append("#prior-box[")
        L.append(md_to_typst(data["vorwissen"]["text"]))
        L += ["]", ""]

    # --- Einleitung ---
    if data.get("einleitung"):
        L.append("#rubrik[Einleitung]")
        L.append(md_to_typst(data["einleitung"]["text"]))
        L.append("")

    # --- Haupttext (Bloecke) ---
    L.append("#rubrik[Haupttext]")
    L.append("")
    for blk in data["haupttext"]:
        typ = blk["typ"]
        if typ == "text":
            L.append(md_to_typst(blk["text"]))
            L.append("")
        elif typ == "quelle":
            args = []
            if blk.get("autor"):
                args.append(f'autor: {tstr(blk["autor"])}')
            if blk.get("titel"):
                args.append(f'titel: {tstr(blk["titel"])}')
            head = "#quelle(" + ", ".join(args) + (", " if args else "") + ")["
            L.append(head if args else "#quelle[")
            L.append(md_to_typst(blk["text"]))
            L += ["]", ""]
        elif typ == "figur":
            rel = figures.get(blk["bild"])
            if rel is None:
                L += [f"#warn-box[Fehlendes Bild: `{blk['bild']}` (nicht in images/).]", ""]
                continue
            q = f', quelle: {tstr(blk["quelle"])}' if blk.get("quelle") else ""
            b = f', breite: {blk["breite"]}' if blk.get("breite") else ""
            L.append(f'#abbildung({tstr(rel)}, beschriftung: {tstr(blk.get("beschriftung",""))}{q}{b})')
            L.append("")
        elif typ == "tabelle":
            kopf = tarr(blk["kopf"])
            zeilen = "(" + "".join("(" + "".join(tstr(c) + ", " for c in row) + "), " for row in blk["zeilen"]) + ")"
            bsc = f', beschriftung: {tstr(blk["beschriftung"])}' if blk.get("beschriftung") else ""
            L.append(f"#tabelle(kopf: {kopf}, zeilen: {zeilen}{bsc})")
            L.append("")

    # --- Verstaendnisfragen ---
    if data.get("verstaendnisfragen"):
        L.append("#rubrik[Verständnisfragen]")
        L.append("#callout(title: \"Verständnisfragen\", fill: teach-soft, bar: teach)[")
        L.append("#set enum(numbering: \"1.\")")
        for f in data["verstaendnisfragen"]:
            L.append("+ " + inline(f))
        L += ["]", ""]

    # --- Aufgaben ---
    aufgaben = data.get("aufgaben", [])
    if aufgaben:
        L.append("#rubrik[Aufgaben]")
        L.append("")
        for i, a in enumerate(aufgaben, 1):
            L.append(f'#aufgabe({i}, {a["afb"]})[')
            L.append(md_to_typst(a["text"]))
            L += ["]", ""]

    # --- Glossar ---
    if data.get("glossar"):
        arr = "(" + "".join(tdict(e, ["begriff", "definition"]) + ", " for e in data["glossar"]) + ")"
        L.append("#rubrik[Glossar]")
        L.append(f"#glossar({arr})")
        L.append("")

    # --- Loesungen (nur mit --solutions) ---
    if solutions:
        loes = [(i, a) for i, a in enumerate(aufgaben, 1) if a.get("loesung")]
        if loes:
            L.append("#rubrik[Lösungen]")
            L.append("#set enum(numbering: \"1.\")")
            for i, a in loes:
                L.append(f"{i}. " + inline(a["loesung"]))
            L.append("")

    # --- Apparat: Bibliografie + Verzeichnisse ---
    if data.get("bibliografie"):
        arr = "(" + "".join(tdict(e, ["autor", "titel", "jahr", "ort", "verlag", "url"]) + ", " for e in data["bibliografie"]) + ")"
        L.append("#pagebreak(weak: true)")
        L.append('#apparat-heading[Bibliografie]')
        L.append(f"#bibliografie({arr})")
        L.append("")
    L.append("#bildverzeichnis()")
    L.append("#tabellenverzeichnis()")
    L.append("")
    return "\n".join(L)


def copy_images(unit, data, out_dir):
    """Kopiert Cover- und Figur-Bilder nach out/. Gibt {name -> rel. Pfad|None}."""
    figures = {}
    img_dir = out_dir / "img"
    # Cover
    cb = data["meta"].get("cover_bild")
    if cb:
        src = unit / cb
        if src.exists():
            dst = "cover" + src.suffix
            shutil.copyfile(src, out_dir / dst)
            figures["__cover__"] = dst
        else:
            print(f"  [Warnung] cover_bild '{cb}' nicht gefunden.")
    # Figuren
    fig_names = [b["bild"] for b in data.get("haupttext", []) if b.get("typ") == "figur"]
    if fig_names:
        img_dir.mkdir(exist_ok=True)
    for name in fig_names:
        src = unit / "images" / name
        if src.exists():
            shutil.copyfile(src, img_dir / name)
            figures[name] = f"img/{name}"
        else:
            figures[name] = None
            print(f"  [Warnung] Bild '{name}' nicht in images/ gefunden.")
    return figures


def main():
    ap = argparse.ArgumentParser(description="Baut eine Unterrichtseinheit zu PDF.")
    ap.add_argument("unit")
    ap.add_argument("--variant", choices=["teacher", "student"], default="teacher")
    ap.add_argument("--solutions", action="store_true", help="Loesungs-Anhang einfuegen")
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--no-compile", action="store_true")
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

    out_dir = unit / "out"
    out_dir.mkdir(exist_ok=True)
    shutil.copyfile(THEME, out_dir / "theme.typ")
    figures = copy_images(unit, data, out_dir)

    typ = build_typst(data, args.variant, args.solutions, figures)
    suffix = args.variant + ("-loesung" if args.solutions else "")
    main_typ = out_dir / f"main-{suffix}.typ"
    main_typ.write_text(typ, encoding="utf-8")
    print(f"  Typst geschrieben: {main_typ}")

    if args.no_compile:
        print("  --no-compile gesetzt: kein PDF erzeugt.")
        return

    if shutil.which("typst") is None:
        print("\nFEHLER: 'typst' nicht gefunden. Installieren: winget install --id Typst.Typst")
        sys.exit(2)

    pdf = out_dir / f"{unit.name}-{suffix}.pdf"
    cmd = ["typst", "compile", "--font-path", str(ROOT / "assets" / "fonts"), str(main_typ), str(pdf)]
    res = subprocess.run(cmd)
    if res.returncode != 0:
        sys.exit(res.returncode)
    print(f"\nFertig: {pdf}")

    if args.open:
        try:
            import os
            os.startfile(pdf)
        except AttributeError:
            subprocess.run(["xdg-open", str(pdf)])


if __name__ == "__main__":
    main()
