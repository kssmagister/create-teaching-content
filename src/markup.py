"""Minimaler Markdown -> Typst-Konverter.

Deckt die haeufigen Faelle aus Web-Clippings ab: Ueberschriften, Absaetze,
Listen, Zitate, fett/kursiv/Code, Links. Kein voller Markdown-Parser -- bewusst
klein gehalten, damit der Build ohne schwere Abhaengigkeiten laeuft.
"""
import re

# Typst-Sonderzeichen, die in Fliesstext escaped werden muessen.
_SPECIAL = str.maketrans({c: "\\" + c for c in "\\#$*_`<>@~[]"})


def esc(s: str) -> str:
    """Escaped Typst-Sonderzeichen in einem reinen Textabschnitt."""
    return s.translate(_SPECIAL)


def tstr(s: str) -> str:
    """Serialisiert einen String als Typst-String-Literal."""
    s = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return '"' + s + '"'


_INLINE = re.compile(
    r"(?P<link>\[[^\]]+\]\([^)]+\))"
    r"|(?P<code>`[^`]+`)"
    r"|(?P<bold>\*\*[^*]+\*\*|__[^_]+__)"
    r"|(?P<italic>\*[^*]+\*|_[^_]+_)"
)


def inline(text: str) -> str:
    """Wandelt Inline-Markdown in Typst-Markup um (Rest wird escaped)."""
    out, pos = [], 0
    for m in _INLINE.finditer(text):
        out.append(esc(text[pos:m.start()]))
        if m.group("link"):
            lm = re.match(r"\[([^\]]+)\]\(([^)]+)\)", m.group("link"))
            url = lm.group(2).replace('"', "")
            out.append('#link("' + url + '")[' + esc(lm.group(1)) + "]")
        elif m.group("code"):
            out.append("`" + m.group("code")[1:-1].replace("`", "'") + "`")
        elif m.group("bold"):
            out.append("*" + esc(m.group("bold")[2:-2]) + "*")
        else:
            out.append("_" + esc(m.group("italic")[1:-1]) + "_")
        pos = m.end()
    out.append(esc(text[pos:]))
    return "".join(out)


def split_haupttext_md(md: str) -> list[str]:
    """Teilt ein fertiges Markdown-Dokument an Top-Level-Ueberschriften (`# `) in
    Abschnitte, die je zu einem `haupttext`-Textblock werden. Tiefere Ueberschriften
    (`##` etc.) bleiben als Zwischentitel innerhalb eines Blocks erhalten."""
    lines = md.replace("\r\n", "\n").split("\n")
    sections, current = [], []
    for line in lines:
        if re.match(r"^#\s+\S", line) and current:
            sections.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    return [s for s in sections if s]


def md_to_typst(md: str) -> str:
    """Wandelt einen Markdown-Block in Typst-Markup um."""
    lines = md.replace("\r\n", "\n").split("\n")
    out, para, quote = [], [], []

    def flush_quote():
        if quote:
            out.append("#quote(block: true)[" + inline(" ".join(quote).strip()) + "]")
            out.append("")
            quote.clear()

    def flush():
        flush_quote()
        if para:
            txt = inline(" ".join(para).strip())
            if txt:
                # Block-bedeutsame Startzeichen entschaerfen.
                if txt[:1] in "-+=/#":
                    txt = "\\" + txt
                out.append(txt)
            para.clear()

    def ensure_gap_before_list():
        if out and out[-1] != "" and not out[-1].startswith(("- ", "+ ")):
            out.append("")

    for raw in lines:
        stripped = raw.strip()
        if stripped == "":
            flush()
            out.append("")
            continue
        # Freiraum-/Schreiblinie
        if re.fullmatch(r"_{3,}", stripped):
            flush()
            out.append("#writing-lines(n: 1)")
            out.append("")
            continue
        # Ueberschrift
        h = re.match(r"(#{1,6})\s+(.*)", stripped)
        if h:
            flush()
            lvl = min(len(h.group(1)) + 2, 4)
            out.append("=" * lvl + " " + inline(h.group(2)))
            out.append("")
            continue
        # Ungeordnete Liste
        m = re.match(r"[-*]\s+(.*)", stripped)
        if m:
            flush()
            ensure_gap_before_list()
            out.append("- " + inline(m.group(1)))
            continue
        # Geordnete Liste
        m = re.match(r"\d+\.\s+(.*)", stripped)
        if m:
            flush()
            ensure_gap_before_list()
            out.append("+ " + inline(m.group(1)))
            continue
        # Zitat (aufeinanderfolgende Zeilen -> ein Block)
        m = re.match(r">\s?(.*)", stripped)
        if m:
            if para:
                flush()
            quote.append(m.group(1))
            continue
        flush_quote()
        para.append(stripped)

    flush()
    result = re.sub(r"\n{3,}", "\n\n", "\n".join(out))
    return result.strip()
