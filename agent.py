#!/usr/bin/env python3
"""agent.py -- LLM-Automatisierung: sources/ -> editorial.json (Schema v2).

Modulare Prompts statt eines Monolithen: Lernziele -> Vorwissen/Einleitung ->
Haupttext -> Aufgaben -> Glossar/Bibliografie. Jede Stufe baut auf dem bereits
generierten Zustand auf (kontext.json), damit sich z.B. Aufgaben auf den
tatsaechlich erzeugten Haupttext beziehen (Grounding gegen Halluzination).

Ablauf:
  1. Rohmaterial aus units/<unit>/sources/ einlesen (txt/md direkt, docx via
     eingebautem Parser; andere Formate werden uebersprungen und gemeldet).
  2. Fuenf gestufte Claude-Aufrufe, jeweils mit Structured Outputs
     (output_config.format) fuer garantiert valides JSON je Stufe.
  3. Ergebnis wird laufend nach kontext.json geschrieben und am Ende als
     editorial.json gespeichert (vorherige Version -> editorial.json.bak).
  4. Menschliches Fakten-Gate bleibt: Ergebnis wird im UI zur Pruefung
     angezeigt, bevor gebaut wird.

Nutzung:
  python agent.py units/002-kreuzzuege-2g
"""
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parent
MODEL = "claude-opus-4-8"
MAX_SOURCE_CHARS = 150_000  # Kostenschutz; 1M-Kontextfenster erlaubt mehr, ist aber selten noetig.

REGELN = """\
Feste Regeln (Grounding - gegen Halluzination):
1. Gib ausschliesslich gueltiges JSON zurueck, das exakt dem vorgegebenen Schema entspricht.
2. Beziehe dich ausschliesslich auf die angehaengten Quellen. Erfinde keine Fakten, Daten,
   Namen oder Zahlen. Was nicht in den Quellen steht, kommt nicht hinein.
3. Sprache auf gymnasialem Niveau; keine Floskeln ("In einer Welt von...",
   "Zusammenfassend laesst sich sagen...").
4. Markdown in Textfeldern ist erlaubt (**fett**, *kursiv*, Listen, ## Zwischentitel).
5. Echte Umlaute (ae->ä, oe->ö, ue->ü, ss->ß) in allen sichtbaren Texten verwenden.
"""


def _safe_read_docx(path: Path) -> str:
    """Extrahiert Fliesstext aus .docx via ZIP/XML (keine Zusatzabhaengigkeit)."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab/>", "\t", xml)
    xml = re.sub(r"<w:br/>", "\n", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    import html
    text = html.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def read_sources(unit: Path) -> str:
    """Liest alles aus sources/ als Klartext ein; meldet nicht unterstuetzte Formate."""
    src_dir = unit / "sources"
    if not src_dir.is_dir():
        return ""
    parts = []
    for f in sorted(src_dir.glob("*")):
        if not f.is_file():
            continue
        if f.suffix.lower() in (".txt", ".md"):
            parts.append(f"--- Quelle: {f.name} ---\n{f.read_text(encoding='utf-8', errors='replace')}")
        elif f.suffix.lower() == ".docx":
            parts.append(f"--- Quelle: {f.name} ---\n{_safe_read_docx(f)}")
        else:
            print(f"  [Hinweis] '{f.name}': Format wird von agent.py noch nicht gelesen (spaeter ingest.py). Uebersprungen.")
    text = "\n\n".join(parts)
    if len(text) > MAX_SOURCE_CHARS:
        print(f"  [Hinweis] Quellen gekuerzt: {len(text)} -> {MAX_SOURCE_CHARS} Zeichen (Kostenschutz).")
        text = text[:MAX_SOURCE_CHARS]
    return text


def _call(client, system, user, schema, max_tokens=8000):
    with client.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": schema}},
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        response = stream.get_final_message()
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude hat die Anfrage abgelehnt (stop_reason=refusal).")
    if response.stop_reason == "max_tokens":
        raise RuntimeError(f"Antwort bei max_tokens={max_tokens} abgeschnitten - agent.py mit hoeherem max_tokens fuer diese Stufe erneut versuchen.")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


# ---- Stufe A: Meta + Lernziele ------------------------------------------
SCHEMA_A = {
    "type": "object",
    "properties": {
        "meta": {
            "type": "object",
            "properties": {
                "titel": {"type": "string"},
                "fach": {"type": "string"},
                "stufe": {"type": "string", "description": "z.B. 'Gymnasium (Sek II)'"},
                "dauer": {"type": "string", "description": "z.B. '4-5 Lektionen'"},
                "cover_zeilen": {"type": "array", "items": {"type": "string"}, "description": "max. 3 kurze Zeilen fuers Cover"},
            },
            "required": ["titel", "fach", "stufe", "dauer", "cover_zeilen"],
            "additionalProperties": False,
        },
        "lernziele": {
            "type": "object",
            "properties": {
                "kognitiv": {"type": "array", "items": {"type": "string"}},
                "fertigkeiten": {"type": "array", "items": {"type": "string"}},
                "metakognitiv": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["kognitiv", "fertigkeiten", "metakognitiv"],
            "additionalProperties": False,
        },
    },
    "required": ["meta", "lernziele"],
    "additionalProperties": False,
}


def stufe_meta_lernziele(client, quellen):
    system = (
        "Du bist Fachdidaktikerin/Fachdidaktiker fuer eine Unterrichtsmaterial-Reihe "
        "am Gymnasium (Sek II).\n" + REGELN
    )
    user = (
        "Erzeuge `meta` (titel, fach, stufe, dauer, cover_zeilen) und `lernziele` "
        "(kognitiv/fertigkeiten/metakognitiv) fuer eine Unterrichtseinheit auf Basis "
        "der folgenden Quellen.\n\n" + quellen
    )
    return _call(client, system, user, SCHEMA_A, max_tokens=6000)


# ---- Stufe B: Lehrerhinweis + Vorwissen + Einleitung ---------------------
SCHEMA_B = {
    "type": "object",
    "properties": {
        "lehrerhinweis": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Markdown; didaktische Begruendung fuer die Lehrkraft"},
                "kernpunkte": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["text", "kernpunkte"],
            "additionalProperties": False,
        },
        "vorwissen": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "Markdown; Advance Organizer"}},
            "required": ["text"],
            "additionalProperties": False,
        },
        "einleitung": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "Markdown"}},
            "required": ["text"],
            "additionalProperties": False,
        },
    },
    "required": ["lehrerhinweis", "vorwissen", "einleitung"],
    "additionalProperties": False,
}


def stufe_einleitung(client, quellen, kontext):
    system = (
        "Du bist Fachdidaktikerin/Fachdidaktiker fuer eine Unterrichtsmaterial-Reihe "
        "am Gymnasium (Sek II).\n" + REGELN
    )
    user = (
        f"Titel/Lernziele dieser Einheit (bereits festgelegt):\n{json.dumps({'meta': kontext['meta'], 'lernziele': kontext['lernziele']}, ensure_ascii=False, indent=2)}\n\n"
        "Erzeuge dazu: `lehrerhinweis` (didaktische Begruendung + Kernpunkte, NUR fuer "
        "die Lehrkraft), `vorwissen` (Advance Organizer, aktiviert Vorwissen der "
        "Lernenden) und `einleitung` (Hinfuehrung zum Thema).\n\nQuellen:\n\n" + quellen
    )
    return _call(client, system, user, SCHEMA_B, max_tokens=8000)


# ---- Stufe C: Haupttext ---------------------------------------------------
_BLOCK_TEXT = {"type": "object", "properties": {"typ": {"const": "text"}, "text": {"type": "string"}},
               "required": ["typ", "text"], "additionalProperties": False}
_BLOCK_QUELLE = {"type": "object", "properties": {
    "typ": {"const": "quelle"}, "autor": {"type": "string"}, "titel": {"type": "string"}, "text": {"type": "string"}},
    "required": ["typ", "text"], "additionalProperties": False}
_BLOCK_FIGUR = {"type": "object", "properties": {
    "typ": {"const": "figur"}, "bild": {"type": "string", "description": "Dateiname aus der Liste verfuegbarer Bilder"},
    "beschriftung": {"type": "string"}, "quelle": {"type": "string"}, "breite": {"type": "string"}},
    "required": ["typ", "bild", "beschriftung"], "additionalProperties": False}
_BLOCK_TABELLE = {"type": "object", "properties": {
    "typ": {"const": "tabelle"}, "beschriftung": {"type": "string"},
    "kopf": {"type": "array", "items": {"type": "string"}},
    "zeilen": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}}},
    "required": ["typ", "kopf", "zeilen"], "additionalProperties": False}

SCHEMA_C = {
    "type": "object",
    "properties": {
        "haupttext": {
            "type": "array",
            "items": {"anyOf": [_BLOCK_TEXT, _BLOCK_QUELLE, _BLOCK_FIGUR, _BLOCK_TABELLE]},
        },
    },
    "required": ["haupttext"],
    "additionalProperties": False,
}


def stufe_haupttext(client, quellen, kontext, bilder):
    system = (
        "Du bist Fachdidaktikerin/Fachdidaktiker fuer eine Unterrichtsmaterial-Reihe "
        "am Gymnasium (Sek II).\n" + REGELN + """
Blocktypen fuer `haupttext`:
- {typ: "text", text}                                    Fliesstext, ## fuer Zwischentitel
- {typ: "quelle", autor?, titel?, text}                   woertliches Zitat/Primaerquelle
- {typ: "figur", bild, beschriftung, quelle?, breite?}    bild = Dateiname aus verfuegbaren Bildern
- {typ: "tabelle", beschriftung?, kopf[], zeilen[][]}      Uebersichtstabelle

Baue eine sinnvolle Dramaturgie mit mehreren Textbloecken (## Zwischentitel je
Abschnitt). Nutze `figur` nur mit einem Dateinamen aus der Liste der
verfuegbaren Bilder. Nutze `tabelle` fuer Uebersichten, wenn die Quellen das
hergeben (z.B. Chronologien, Vergleiche)."""
    )
    bilder_hinweis = (
        "Verfuegbare Bilder (nur diese Dateinamen fuer `bild` verwenden): "
        + (", ".join(bilder) if bilder else "keine hochgeladen - keine figur-Bloecke erzeugen.")
    )
    user = (
        f"Titel/Lernziele/Einleitung dieser Einheit:\n"
        f"{json.dumps({'meta': kontext['meta'], 'lernziele': kontext['lernziele'], 'einleitung': kontext['einleitung']}, ensure_ascii=False, indent=2)}\n\n"
        f"{bilder_hinweis}\n\nErzeuge den `haupttext` (geordnete Bloecke) auf Basis "
        "der folgenden Quellen:\n\n" + quellen
    )
    return _call(client, system, user, SCHEMA_C, max_tokens=20000)


# ---- Stufe D: Verstaendnisfragen + Aufgaben -------------------------------
SCHEMA_D = {
    "type": "object",
    "properties": {
        "verstaendnisfragen": {"type": "array", "items": {"type": "string"}},
        "aufgaben": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "afb": {"type": "integer", "enum": [1, 2, 3]},
                    "text": {"type": "string"},
                    "loesung": {"type": "string", "description": "Erwartungshorizont"},
                },
                "required": ["afb", "text", "loesung"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["verstaendnisfragen", "aufgaben"],
    "additionalProperties": False,
}


def stufe_aufgaben(client, kontext):
    system = (
        "Du bist Fachdidaktikerin/Fachdidaktiker fuer eine Unterrichtsmaterial-Reihe "
        "am Gymnasium (Sek II).\n" + REGELN + """
AFB = Anforderungsbereich (I-III, hier 1/2/3): I reproduzieren, II
reorganisieren/analysieren, III werten/beurteilen. Erzeuge mindestens je eine
Aufgabe pro AFB. Verstaendnisfragen sind niederschwellig (ohne AFB, ohne Loesung).
Beziehe dich AUSSCHLIESSLICH auf den unten angehaengten Haupttext - kein
Allgemeinwissen, keine erfundenen Fakten."""
    )
    user = (
        "Erzeuge `verstaendnisfragen` und `aufgaben` zu diesem Haupttext:\n\n"
        + json.dumps(kontext["haupttext"], ensure_ascii=False, indent=2)
    )
    return _call(client, system, user, SCHEMA_D, max_tokens=10000)


# ---- Stufe E: Glossar + Bibliografie + Schlagwoerter ----------------------
SCHEMA_E = {
    "type": "object",
    "properties": {
        "glossar": {"type": "array", "items": {
            "type": "object", "properties": {"begriff": {"type": "string"}, "definition": {"type": "string"}},
            "required": ["begriff", "definition"], "additionalProperties": False}},
        "bibliografie": {"type": "array", "items": {
            "type": "object", "properties": {
                "autor": {"type": "string"}, "titel": {"type": "string"}, "jahr": {"type": "string"},
                "ort": {"type": "string"}, "verlag": {"type": "string"}, "url": {"type": "string"}},
            "required": ["titel"], "additionalProperties": False}},
        "schlagwoerter": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["glossar", "bibliografie", "schlagwoerter"],
    "additionalProperties": False,
}


def stufe_glossar(client, quellen, kontext):
    system = (
        "Du bist Fachdidaktikerin/Fachdidaktiker fuer eine Unterrichtsmaterial-Reihe "
        "am Gymnasium (Sek II).\n" + REGELN + """
`bibliografie` NUR aus tatsaechlich in den Quellen genannten oder eindeutig
identifizierbaren Werken - erfinde keine Publikationen. Falls unklar, nenne
das Rohmaterial selbst als Eintrag."""
    )
    user = (
        f"Haupttext dieser Einheit:\n{json.dumps(kontext['haupttext'], ensure_ascii=False, indent=2)}\n\n"
        "Erzeuge dazu `glossar` (zentrale Fachbegriffe), `bibliografie` und "
        "`schlagwoerter`. Quellen (fuer Bibliografie-Hinweise):\n\n" + quellen
    )
    return _call(client, system, user, SCHEMA_E, max_tokens=8000)


def generate_editorial(unit: Path, log=print) -> dict:
    client = anthropic.Anthropic()
    quellen = read_sources(unit)
    if not quellen.strip():
        raise RuntimeError(f"Keine lesbaren Quellen in {unit / 'sources'} gefunden.")
    bilder = sorted(p.name for p in (unit / "images").glob("*") if p.is_file()) if (unit / "images").is_dir() else []

    kontext_path = unit / "kontext.json"
    kontext = {"schema_version": "2.0"}

    def speichere():
        kontext_path.write_text(json.dumps(kontext, ensure_ascii=False, indent=2), encoding="utf-8")

    log("  [1/5] Meta + Lernziele ...")
    kontext.update(stufe_meta_lernziele(client, quellen))
    speichere()

    log("  [2/5] Lehrerhinweis + Vorwissen + Einleitung ...")
    kontext.update(stufe_einleitung(client, quellen, kontext))
    speichere()

    log("  [3/5] Haupttext ...")
    kontext.update(stufe_haupttext(client, quellen, kontext, bilder))
    speichere()

    log("  [4/5] Verstaendnisfragen + Aufgaben ...")
    kontext.update(stufe_aufgaben(client, kontext))
    speichere()

    log("  [5/5] Glossar + Bibliografie + Schlagwoerter ...")
    kontext.update(stufe_glossar(client, quellen, kontext))
    speichere()

    return kontext


def main():
    ap = argparse.ArgumentParser(description="Generiert editorial.json aus units/<unit>/sources/ via Claude-API.")
    ap.add_argument("unit")
    args = ap.parse_args()

    unit = Path(args.unit).resolve()
    if not unit.is_dir():
        sys.exit(f"FEHLER: {unit} nicht gefunden.")

    data = generate_editorial(unit)

    ed_path = unit / "editorial.json"
    if ed_path.exists() and ed_path.read_text(encoding="utf-8").strip() not in ("", "{}"):
        (unit / "editorial.json.bak").write_text(ed_path.read_text(encoding="utf-8"), encoding="utf-8")
        print("  Bisherige editorial.json gesichert nach editorial.json.bak")

    ed_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nFertig: {ed_path}")
    print("Bitte im UI pruefen (Fakten-Check!), bevor gebaut wird.")


if __name__ == "__main__":
    main()
