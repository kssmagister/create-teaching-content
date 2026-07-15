# Prompt: Arbeitsblatt-Generator (optional)

> Ergänzt die `worksheets[]` in `editorial.json`. Kann separat aufgerufen und
> das Ergebnis in die bestehende `editorial.json` einsortiert werden.

---

Du erstellst **Arbeitsaufträge** zu der bereitgestellten Unterrichtseinheit.
Gib ein JSON-Array `worksheets` zurück, dessen Elemente diesem Schema folgen:

```json
{
  "id": "ab-kurzname",
  "title": "Titel des Arbeitsblatts",
  "task": "Klarer, handlungsorientierter Arbeitsauftrag (1–3 Sätze).",
  "body": "Markdown. Nutze Zeilen aus nur '___' als Schreiblinien.",
  "differentiation": {
    "support": "Scaffolding / vereinfachte Variante",
    "extension": "Vertiefung für Schnellere"
  }
}
```

Regeln:

- Aufgaben sollen **kognitiv aktivieren** (nicht nur reproduzieren): vergleichen,
  beurteilen, begründen, Quellen auswerten.
- Baue mindestens eine **Differenzierung** (support/extension) ein.
- Erfinde keine Fakten; beziehe dich auf die Inhalte der Einheit.
- Halte die Sprache dem `grade_level` angemessen.
