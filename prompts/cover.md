# Prompt: Cover-Motiv (optional)

> Hinweis: Bildgenerierung läuft über ein **Bildmodell** (z. B. GPT-Image /
> DALL·E / Midjourney), **nicht** über Codex – Codex ist ein Code-Modell. Das
> war im Ausgangsdokument verwechselt.

Das aktuelle Layout (`templates/theme.typ`) nutzt ein **typografisches Cover**
ohne Bild und braucht daher kein generiertes Motiv. Wenn du dennoch eines
möchtest, kannst du das Theme um ein `image(...)` erweitern und folgendes
Prompt-Muster nutzen:

---

Erstelle eine **minimalistische, flache Illustration** für das Cover einer
Unterrichtseinheit zum Thema „<THEMA>".

- Stil: reduziert, ruhig, professionell (kein Clipart, keine Stockfoto-Ästhetik)
- Farbwelt: gedämpfte Blau-/Grautöne, passend zu einem sachlichen Schulmaterial
- Motiv: ein einzelnes, klares Symbol oder eine schlichte Collage von
  Fachsymbolen zum Thema
- **Kein Text im Bild** (Titel setzt das Layout)
- Format: quadratisch bzw. Hochformat mit ruhigem Rand

Vermeide: überladene Szenen, Karikaturen, plakative Klischees.
