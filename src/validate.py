"""Validiert editorial.json gegen das JSON-Schema.

jsonschema ist optional: fehlt es, wird eine Warnung zurueckgegeben und der
Build laeuft trotzdem (nur ohne Validierung).
"""
import json
from pathlib import Path


def validate(data: dict, schema_path: Path):
    """Gibt (errors, warnings) zurueck. errors leer => gueltig."""
    try:
        import jsonschema
    except ImportError:
        return [], [
            "jsonschema nicht installiert -- Validierung uebersprungen "
            "(pip install -r requirements.txt)"
        ]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "(root)"
        errors.append(f"{loc}: {err.message}")
    return errors, []
