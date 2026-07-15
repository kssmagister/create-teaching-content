#!/usr/bin/env python3
"""build.py -- baut aus einer Unit (editorial.json + clippings/) ein PDF.

Ablauf:
  1. editorial.json laden und gegen das Schema validieren
  2. Clippings laden (Markdown + Front-Matter)
  3. Typst-Quelle erzeugen (EIN durchpaginiertes Dokument)
  4. mit dem 'typst'-CLI zu PDF kompilieren

Nutzung:
  python build.py units/001-schweiz-2wk
  python build.py units/001-schweiz-2wk --variant student
  python build.py units/001-schweiz-2wk --variant teacher --open
  python build.py units/001-schweiz-2wk --no-compile     (nur .typ erzeugen)
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.clippings import load_all
from src.markup import md_to_typst, tstr, inline
from src.validate import validate

SCHEMA = ROOT / "schema" / "editorial.schema.json"
THEME = ROOT / "templates" / "theme.typ"


def opt(value):
    """Typst-Argument: String-Literal oder 'none'."""
    return tstr(value) if value else "none"


def objectives_body(lo: dict) -> list:
    """Baut das Typst-Markup fuer die Lernziel-Box (in beiden Varianten genutzt)."""
    out = ["*Kognitive Lernziele* \\"]
    for o in lo["cognitive"]:
        out.append("- " + inline(o))
    if lo.get("skills"):
        out.append("")
        out.append("*Fähigkeiten* \\")
        for o in lo["skills"]:
            out.append("- " + inline(o))
    if lo.get("metacognitive"):
        out.append("")
        out.append("*Metakognition / Reflexion* \\")
        for o in lo["metacognitive"]:
            out.append("- " + inline(o))
    return out


def build_typst(data: dict, clips: dict, variant: str, cover_image=None) -> str:
    """Erzeugt die vollstaendige Typst-Quelle als String."""
    teacher = variant == "teacher"
    L = ['#import "theme.typ": *', ""]
    L.append(
        f'#show: doc => conf(unit-title: {tstr(data["unit_title"])}, '
        f"variant: {tstr(variant)}, doc)"
    )
    L.append("")

    # --- Cover (optional mit Bild) ---
    lines = data.get("cover_lines", [])
    arr = "(" + "".join(tstr(x) + ", " for x in lines) + ")"
    img_arg = f", image-path: {tstr(cover_image)}" if cover_image else ""
    L.append(
        f'#cover(unit-title: {tstr(data["unit_title"])}, '
        f'subject: {tstr(data.get("subject", ""))}, '
        f'grade: {tstr(data.get("grade_level", ""))}, '
        f'duration: {tstr(data.get("duration", ""))}, '
        f"lines: {arr}, variant: {tstr(variant)}{img_arg})"
    )
    L.append("")

    # --- Ueberblick: Lernziele + Inhaltsverzeichnis (beide Varianten) ---
    L.append(f"#overview(variant: {tstr(variant)})[")
    L.extend(objectives_body(data["learning_objectives"]))
    L.append("]")
    L.append("")

    # --- Lehrerteil (nur in der Lehrerversion) ---
    if teacher:
        L.append("#pagebreak()")
        L.append('#heading(level: 2, outlined: false, numbering: none)[Lehrerhinweise]')
        L.append("")

        # Didaktische Begruendung (editor_note)
        note = data["editor_note"]
        L.append("#teacher-box[")
        L.append(md_to_typst(note["content"]))
        if note.get("key_takeaways"):
            L.append("")
            L.append("*Kernpunkte* \\")
            for k in note["key_takeaways"]:
                L.append("- " + inline(k))
        L.append("]")
        L.append("")

        # Evidenzbasis -- bewusst mit Pruef-Warnung (siehe README)
        eb = data.get("evidence_base")
        if eb and eb.get("key_research"):
            unverified = [r for r in eb["key_research"] if not r.get("verified")]
            body = ["#warn-box(title: \"Evidenzbasis - vor Gebrauch prüfen\")["]
            body.append(
                "Effektstärken und Studien wurden ggf. vom LLM erzeugt. "
                "Nur als _verifiziert_ markierte Angaben sind gegengeprüft. \\"
            )
            for r in eb["key_research"]:
                mark = "✓ " if r.get("verified") else "⚠ "
                es = r.get("effect_size")
                es_txt = f" (d = {es})" if es not in (None, "", "-") else ""
                body.append(
                    "- " + mark + "*" + inline(r["principle"]) + "*"
                    + inline(es_txt) + " — " + inline(r["study"])
                )
                if r.get("application"):
                    body.append("  " + inline(r["application"]))
            body.append("]")
            L.extend(body)
            L.append("")
            _ = unverified  # nur zur Klarheit; Markierung erfolgt inline

        # Empfohlene Reihenfolge
        order = data.get("recommended_order")
        if order:
            L.append('#heading(level: 3, outlined: false, numbering: none)[Empfohlene Reihenfolge]')
            for cid in order:
                title = clips.get(cid, {}).get("title", cid)
                L.append(f"+ {inline(title)}")
            L.append("")

    # --- Rubriken mit Artikeln ---
    # Bei genau einem Text pro Rubrik entfaellt der doppelte Artikel-Titel:
    # die Rubrik-Ueberschrift dient dann zugleich als Titel.
    used = set()
    for sec in data["sections"]:
        purpose = opt(sec.get("purpose", "")) if teacher else "none"
        L.append(f"#section-divider({tstr(sec['section_title'])}, purpose: {purpose})")
        L.append("")
        clip_ids = sec.get("clippings", [])
        single = len(clip_ids) == 1
        for cid in clip_ids:
            used.add(cid)
            clip = clips.get(cid)
            if clip is None:
                L.append(
                    f"#warn-box[Fehlende Clipping-Datei: `{cid}` — "
                    "keine passende .md in clippings/ gefunden.]"
                )
                L.append("")
                continue
            source = clip.get("source") or clip.get("url") or ""
            title_arg = "none" if single else tstr(clip["title"])
            L.append(f"#article(title: {title_arg}, source: {opt(source)})[")
            L.append(md_to_typst(clip["_body"]))
            L.append("]")
            L.append("")

    # --- Arbeitsblaetter ---
    for ws in data.get("worksheets", []):
        diff = ws.get("differentiation", {})
        L.append("#worksheet(")
        L.append(f"  title: {tstr(ws['title'])},")
        L.append(f"  task: {tstr(ws['task'])},")
        L.append(f"  support: {opt(diff.get('support', ''))},")
        L.append(f"  extension: {opt(diff.get('extension', ''))},")
        L.append(f"  variant: {tstr(variant)},")
        if ws.get("body"):
            L.append("  body: [")
            L.append(md_to_typst(ws["body"]))
            L.append("  ],")
        L.append(")")
        L.append("")

    # --- Kolophon ---
    sources = data.get("sources", [])
    keywords = data.get("keywords", [])
    s_arr = "(" + "".join(tstr(x) + ", " for x in sources) + ")"
    k_arr = "(" + "".join(tstr(x) + ", " for x in keywords) + ")"
    L.append(f"#colophon(sources: {s_arr}, keywords: {k_arr})")
    L.append("")

    # Hinweis auf nicht referenzierte Clippings (nur Konsole, s.u.)
    build_typst.unused = [cid for cid in clips if cid not in used]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Baut eine Unterrichtseinheit zu PDF.")
    ap.add_argument("unit", help="Pfad zum Unit-Ordner (enthaelt editorial.json)")
    ap.add_argument("--variant", choices=["teacher", "student"], default="teacher")
    ap.add_argument("--open", action="store_true", help="PDF nach dem Build oeffnen")
    ap.add_argument("--no-compile", action="store_true", help="nur .typ erzeugen")
    args = ap.parse_args()

    unit = Path(args.unit).resolve()
    ed_path = unit / "editorial.json"
    if not ed_path.exists():
        sys.exit(f"FEHLER: {ed_path} nicht gefunden.")

    data = json.loads(ed_path.read_text(encoding="utf-8"))

    # 1. Validierung
    errors, warnings = validate(data, SCHEMA)
    for w in warnings:
        print(f"  [Warnung] {w}")
    if errors:
        print("FEHLER: editorial.json entspricht nicht dem Schema:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    # 2. Clippings
    clips = load_all(unit / "clippings")
    print(f"  {len(clips)} Clipping(s) geladen.")

    # 3. Typst erzeugen
    out_dir = unit / "out"
    out_dir.mkdir(exist_ok=True)
    shutil.copyfile(THEME, out_dir / "theme.typ")

    # Cover-Bild (optional): relativ zum Unit-Ordner, wird nach out/ kopiert.
    cover_image = None
    ci = data.get("cover_image")
    if ci:
        src = unit / ci
        if src.exists():
            cover_image = "cover" + src.suffix
            shutil.copyfile(src, out_dir / cover_image)
        else:
            print(f"  [Warnung] cover_image '{ci}' nicht gefunden – wird ignoriert.")

    typ = build_typst(data, clips, args.variant, cover_image=cover_image)
    main_typ = out_dir / f"main-{args.variant}.typ"
    main_typ.write_text(typ, encoding="utf-8")
    print(f"  Typst geschrieben: {main_typ}")

    for cid in getattr(build_typst, "unused", []):
        print(f"  [Hinweis] Clipping '{cid}' ist in keiner Sektion referenziert.")

    if args.no_compile:
        print("  --no-compile gesetzt: kein PDF erzeugt.")
        return

    # 4. Kompilieren
    if shutil.which("typst") is None:
        print(
            "\nFEHLER: 'typst' nicht gefunden.\n"
            "Installieren (Windows):  winget install --id Typst.Typst\n"
            "  oder:                  cargo install typst-cli\n"
            "Danach erneut ausfuehren, oder mit --no-compile nur die .typ erzeugen."
        )
        sys.exit(2)

    pdf = out_dir / f"{unit.name}-{args.variant}.pdf"
    cmd = ["typst", "compile", "--font-path", str(ROOT / "assets" / "fonts"),
           str(main_typ), str(pdf)]
    print("  " + " ".join(cmd))
    res = subprocess.run(cmd)
    if res.returncode != 0:
        sys.exit(res.returncode)
    print(f"\nFertig: {pdf}")

    if args.open:
        try:
            import os
            os.startfile(pdf)  # Windows
        except AttributeError:
            subprocess.run(["xdg-open", str(pdf)])


if __name__ == "__main__":
    main()
