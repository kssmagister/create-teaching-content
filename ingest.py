#!/usr/bin/env python3
"""ingest.py -- Rohquellen in units/<unit>/sources/ zu Markdown wandeln (Docling).

agent.py liest sources/ zwar bereits selbst ein (txt/md direkt, docx/pdf ueber
einfache Parser ohne OCR), aber ohne Layout-/Tabellenverstaendnis und ohne
gescannte PDFs. ingest.py nutzt stattdessen Docling (bessere Extraktion, OCR
fuer Bild-PDFs/Fotos, mehr Formate: PPTX, XLSX, HTML) und schreibt das
Ergebnis als *.md-Datei zurueck in sources/ -- vor dem agent.py-Lauf ansicht-
und editierbar (zusaetzliches Fakten-Gate).

Docling ist absichtlich NICHT im Haupt-Container (GB-schweres ML-Image durch
Torch/OCR). ingest.py laeuft im separaten "ingest"-Compose-Service:

  docker compose --profile ingest run --rm ingest python ingest.py units/<unit>

Ablauf je Datei in sources/ (Top-Level, ohne sources/_originals/):
  1. Ist sources/<stem>.md schon vorhanden und kein --force -> ueberspringen.
  2. Sonst: mit Docling konvertieren, als sources/<stem>.md speichern.
  3. Original nach sources/_originals/<name> verschieben. agent.py's Quellen-
     Scan ist nicht rekursiv und liest danach automatisch nur noch die
     bessere Markdown-Version -- kein Doppel-Lesen, keine Aenderung an
     agent.py noetig.

Nutzung:
  python ingest.py units/002-kreuzzuege-2g
  python ingest.py units/002-kreuzzuege-2g --force   # bereits konvertierte neu wandeln
"""
import argparse
import sys
from pathlib import Path

from docling.document_converter import DocumentConverter

ROOT = Path(__file__).resolve().parent
MIN_TEXT_CHARS = 200  # gleiche Schwelle wie agent.py._safe_read_pdf

CONVERTIBLE_SUFFIXES = {
    ".pdf", ".docx", ".pptx", ".xlsx", ".html", ".htm",
    ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp",
}
PASSTHROUGH_SUFFIXES = {".txt", ".md"}


def ingest(unit: Path, force: bool) -> None:
    src_dir = unit / "sources"
    if not src_dir.is_dir():
        raise SystemExit(f"Kein sources/-Ordner in {unit}")

    converted, skipped, unsupported = [], [], []
    converter = None  # lazy: nur instanziieren, wenn wirklich etwas zu konvertieren ist

    for f in sorted(src_dir.glob("*")):
        if not f.is_file() or f.suffix.lower() in PASSTHROUGH_SUFFIXES:
            continue
        if f.suffix.lower() not in CONVERTIBLE_SUFFIXES:
            unsupported.append(f.name)
            continue

        target = f.with_suffix(".md")
        if target.exists() and not force:
            skipped.append(f.name)
            _archive(f, src_dir)
            continue

        if converter is None:
            converter = DocumentConverter()
        print(f"  konvertiere '{f.name}' ...")
        result = converter.convert(str(f))
        markdown = result.document.export_to_markdown()
        if len(markdown.strip()) < MIN_TEXT_CHARS:
            print(f"  [Warnung] '{f.name}': kaum Text extrahiert ({len(markdown.strip())} "
                  f"Zeichen) -- Quelle pruefen (schlechter Scan/OCR-Fehlschlag?).")
        target.write_text(markdown, encoding="utf-8")
        converted.append(f.name)
        _archive(f, src_dir)

    print(f"\nKonvertiert: {len(converted)}  Uebersprungen: {len(skipped)}  "
          f"Nicht unterstuetzt: {len(unsupported)}")
    if unsupported:
        print("  Nicht unterstuetzt (Docling kann z. B. kein ODT/RTF -- siehe README, "
              "Abschnitt 'Andere Ausgabeformate (Pandoc)'):")
        for name in unsupported:
            print(f"    - {name}")


def _archive(f: Path, src_dir: Path) -> None:
    """Verschiebt das Original nach sources/_originals/, damit agent.py's
    flacher Scan nur noch die konvertierte .md-Datei sieht."""
    archive_dir = src_dir / "_originals"
    archive_dir.mkdir(exist_ok=True)
    f.rename(archive_dir / f.name)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Wandelt units/<unit>/sources/* mit Docling zu Markdown.")
    ap.add_argument("unit", type=Path, help="z. B. units/002-kreuzzuege-2g")
    ap.add_argument("--force", action="store_true", help="bereits vorhandene .md-Dateien neu konvertieren")
    args = ap.parse_args()

    unit_path = args.unit if args.unit.is_absolute() else ROOT / args.unit
    if not unit_path.is_dir():
        sys.exit(f"Unit-Ordner nicht gefunden: {unit_path}")

    ingest(unit_path, args.force)
