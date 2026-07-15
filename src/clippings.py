"""Laedt Clipping-Dateien (Markdown mit einfachem YAML-aehnlichem Front-Matter).

Front-Matter-Beispiel:

    ---
    id: schweiz-1939
    title: "Die Schweiz 1939 - Zwischen den Fronten"
    source: "Beispielquelle"
    url: "https://..."
    license: "unklar - vor Verteilung klaeren"
    ---
    Markdown-Text ...

Bewusst nur simple `key: value`-Zeilen -- kein voller YAML-Parser noetig.
"""
from pathlib import Path


def load_clipping(path: Path):
    text = path.read_text(encoding="utf-8")
    meta, body = {}, text
    lead = text.lstrip()
    if lead.startswith("---"):
        parts = lead.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"').strip("'")
            body = parts[2].lstrip("\n")
    meta.setdefault("id", path.stem)
    meta.setdefault("title", meta["id"])
    meta["_body"] = body
    meta["_path"] = str(path)
    return meta


def load_all(clippings_dir: Path):
    """Alle *.md aus dem Ordner, indexiert nach id."""
    result = {}
    if not clippings_dir.is_dir():
        return result
    for path in sorted(clippings_dir.glob("*.md")):
        meta = load_clipping(path)
        result[meta["id"]] = meta
    return result
