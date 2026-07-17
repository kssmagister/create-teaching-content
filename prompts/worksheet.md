# Prompt: Aufgaben-Generator (erzeugt das `aufgaben`-Array)

> Kann separat aufgerufen werden, wenn du die Aufgaben getrennt vom Haupttext
> generieren willst. Ergebnis in `editorial.json` unter `aufgaben` einsortieren.

---

Du erstellst **Aufgaben** zu dem bereitgestellten `haupttext` (unten angehängt).
Gib **nur** ein JSON-Array `aufgaben` zurück:

```json
[
  { "afb": 1, "text": "Reproduktion: nennen, wiedergeben …", "loesung": "…" },
  { "afb": 2, "text": "Reorganisation/Analyse: erklären, analysieren …", "loesung": "…" },
  { "afb": 3, "text": "Werten/Beurteilen: beurteilen, Stellung nehmen …", "loesung": "…" }
]
```

Regeln:

- **AFB = Anforderungsbereich** (I–III, hier `1`/`2`/`3`): I reproduzieren, II
  reorganisieren/analysieren, III werten/beurteilen. Decke idealerweise alle drei ab.
- Aufgaben beziehen sich **ausschliesslich** auf den angehängten `haupttext`
  (inkl. Quellen/Tabellen) – kein Allgemeinwissen, keine erfundenen Fakten.
- Nutze klare Operatoren (nennen, analysieren, beurteilen …).
- `loesung` ist ein Erwartungshorizont; sie erscheint im PDF nur mit `--solutions`.

---

**Angehängter Haupttext:**

<!-- Hier den generierten haupttext einfügen. -->
