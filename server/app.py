"""FastAPI-Schicht: Units/Dateien verwalten, Build ausloesen, PDF liefern.

Bewusst duenn und Single-User (hinter Tailscale, keine Auth). Der Build
delegiert an build.py (Subprozess), damit die gesamte Render-Logik wiederverwendet wird.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
UNITS = ROOT / "units"
SCHEMA = ROOT / "schema" / "editorial.schema.json"
STATIC = Path(__file__).resolve().parent / "static"

sys.path.insert(0, str(ROOT))
from src.validate import validate  # noqa: E402

app = FastAPI(title="create-teaching-content")

SLUG = re.compile(r"^[A-Za-z0-9._-]+$")
EDITORIAL_SKELETON = {
    "schema_version": "2.0",
    "meta": {"titel": "Neue Einheit", "fach": "", "stufe": ""},
    "lernziele": {"kognitiv": ["..."]},
    "haupttext": [{"typ": "text", "text": "..."}],
}


def _unit_dir(unit: str, create: bool = False) -> Path:
    if not SLUG.match(unit):
        raise HTTPException(400, "Ungültiger Unit-Name (nur A-Z, a-z, 0-9, . _ -).")
    d = UNITS / unit
    if create:
        d.mkdir(parents=True, exist_ok=True)
        return d
    if not d.is_dir():
        raise HTTPException(404, f"Unit '{unit}' nicht gefunden.")
    return d


def _safe_name(name: str) -> str:
    name = Path(name).name  # kein Pfad
    name = re.sub(r"[^A-Za-z0-9._ \-]", "_", name).strip()
    if not name:
        raise HTTPException(400, "Ungültiger Dateiname.")
    return name


def _list(dirpath: Path):
    return sorted(p.name for p in dirpath.glob("*") if p.is_file()) if dirpath.is_dir() else []


# ---- Seite -------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC / "index.html").read_text(encoding="utf-8")


# ---- Health ------------------------------------------------------------
@app.get("/api/health")
def health():
    ok, ver = False, None
    try:
        r = subprocess.run(["typst", "--version"], capture_output=True, text=True)
        ok, ver = r.returncode == 0, r.stdout.strip()
    except FileNotFoundError:
        pass
    return {"typst": ok, "typst_version": ver}


# ---- Units -------------------------------------------------------------
@app.get("/api/units")
def list_units():
    out = []
    if UNITS.is_dir():
        for d in sorted(UNITS.iterdir()):
            if d.is_dir():
                out.append({"name": d.name, "has_editorial": (d / "editorial.json").exists()})
    return out


@app.post("/api/units")
def create_unit(payload: dict = Body(...)):
    name = payload.get("name", "").strip()
    if not SLUG.match(name):
        raise HTTPException(400, "Ungültiger Unit-Name.")
    d = UNITS / name
    if d.exists():
        raise HTTPException(409, "Unit existiert bereits.")
    d.mkdir(parents=True)
    (d / "sources").mkdir()
    (d / "images").mkdir()
    (d / "editorial.json").write_text(
        json.dumps(EDITORIAL_SKELETON, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "name": name}


@app.get("/api/units/{unit}")
def unit_detail(unit: str):
    d = _unit_dir(unit)
    return {
        "name": unit,
        "sources": _list(d / "sources"),
        "images": _list(d / "images"),
        "pdfs": [p.name for p in sorted((d / "out").glob("*.pdf"))] if (d / "out").is_dir() else [],
        "has_editorial": (d / "editorial.json").exists(),
    }


# ---- editorial.json ----------------------------------------------------
@app.get("/api/units/{unit}/editorial", response_class=HTMLResponse)
def get_editorial(unit: str):
    d = _unit_dir(unit)
    f = d / "editorial.json"
    return HTMLResponse(f.read_text(encoding="utf-8") if f.exists() else "{}",
                        media_type="application/json")


@app.put("/api/units/{unit}/editorial")
def put_editorial(unit: str, payload: dict = Body(...)):
    d = _unit_dir(unit)
    try:
        data = payload if isinstance(payload, dict) else json.loads(payload)
    except (ValueError, TypeError):
        raise HTTPException(400, "Kein gültiges JSON.")
    errors, warnings = validate(data, SCHEMA)
    if errors:
        return {"ok": False, "errors": errors, "warnings": warnings}
    (d / "editorial.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "warnings": warnings}


# ---- Datei-Upload ------------------------------------------------------
@app.post("/api/units/{unit}/upload")
async def upload(unit: str, kind: str, files: list[UploadFile]):
    if kind not in ("sources", "images"):
        raise HTTPException(400, "kind muss 'sources' oder 'images' sein.")
    d = _unit_dir(unit)
    target = d / kind
    target.mkdir(exist_ok=True)
    saved = []
    for f in files:
        name = _safe_name(f.filename or "datei")
        (target / name).write_bytes(await f.read())
        saved.append(name)
    return {"ok": True, "saved": saved}


@app.delete("/api/units/{unit}/file")
def delete_file(unit: str, kind: str, name: str):
    if kind not in ("sources", "images"):
        raise HTTPException(400, "kind muss 'sources' oder 'images' sein.")
    d = _unit_dir(unit)
    p = d / kind / _safe_name(name)
    if p.exists():
        p.unlink()
    return {"ok": True}


# ---- LLM-Generierung (Schritt 3: agent.py) ------------------------------
@app.post("/api/units/{unit}/generate")
def generate(unit: str):
    d = _unit_dir(unit)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(400, "ANTHROPIC_API_KEY ist nicht gesetzt (.env pruefen).")
    if not _list(d / "sources"):
        raise HTTPException(400, "Keine Dateien in sources/ - zuerst Rohmaterial hochladen.")
    cmd = [sys.executable, str(ROOT / "agent.py"), f"units/{unit}"]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    log = (res.stdout + res.stderr).strip()
    ok = res.returncode == 0 and (d / "editorial.json").exists()
    editorial = (d / "editorial.json").read_text(encoding="utf-8") if ok else None
    return {"ok": ok, "log": log, "editorial": editorial}


# ---- Build -------------------------------------------------------------
@app.post("/api/units/{unit}/build")
def build(unit: str, payload: dict = Body(default={})):
    d = _unit_dir(unit)
    variant = payload.get("variant", "teacher")
    solutions = bool(payload.get("solutions", False))
    if variant not in ("teacher", "student"):
        raise HTTPException(400, "variant muss 'teacher' oder 'student' sein.")
    cmd = [sys.executable, str(ROOT / "build.py"), f"units/{unit}", "--variant", variant]
    if solutions:
        cmd.append("--solutions")
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    suffix = variant + ("-loesung" if solutions else "")
    pdf = f"{unit}-{suffix}.pdf"
    ok = res.returncode == 0 and (d / "out" / pdf).exists()
    return {
        "ok": ok,
        "pdf": pdf if ok else None,
        "log": (res.stdout + res.stderr).strip(),
    }


@app.get("/api/units/{unit}/pdf/{name}")
def get_pdf(unit: str, name: str):
    d = _unit_dir(unit)
    p = d / "out" / _safe_name(name)
    if not p.exists() or p.suffix != ".pdf":
        raise HTTPException(404, "PDF nicht gefunden.")
    return FileResponse(p, media_type="application/pdf", filename=name)


# Statische Assets (optional, falls spaeter benoetigt)
if STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC), name="static")
