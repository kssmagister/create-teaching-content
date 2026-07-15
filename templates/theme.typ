// theme.typ -- Layout & Stil fuer Unterrichtseinheiten.
// Ein Modul: liefert Seiten-Setup + wiederverwendbare Bausteine.
// Ergibt EIN durchpaginiertes Dokument:
//   Cover -> Ueberblick (Lernziele + Inhalt) -> [Lehrerteil] -> Rubriken -> Arbeitsblaetter -> Kolophon

// ---- Schriften ---------------------------------------------------------
// Wunsch-Fonts (Newsreader/Spectral/Libre Franklin) muessen installiert sein,
// sonst greifen die Fallbacks (Georgia/Arial). Details im README.
#let display-font = ("Newsreader", "Georgia", "New Computer Modern")
#let body-font = ("Spectral", "Georgia", "New Computer Modern")
#let sans-font = ("Libre Franklin", "Arial", "DejaVu Sans")

// ---- Farbpalette (ruhig, blau/grau) -----------------------------------
#let ink = rgb("#1f2933")
#let muted = rgb("#5b6b7a")
#let accent = rgb("#2c5282")
#let accent-soft = rgb("#eef3f8")
#let teach = rgb("#2c7a7b")
#let teach-soft = rgb("#e6fffa")
#let warn = rgb("#9a3412")
#let warn-soft = rgb("#fff4ed")
#let line-grey = rgb("#d5dbe1")

// ---- Dokument-Setup ----------------------------------------------------
#let conf(unit-title: "", variant: "teacher", doc) = {
  set document(title: unit-title)
  set page(
    paper: "a4",
    margin: (top: 2.4cm, bottom: 2.4cm, x: 2.2cm),
    header: context {
      if counter(page).get().first() > 1 {
        set text(font: sans-font, size: 8.5pt, fill: muted)
        grid(
          columns: (1fr, auto),
          align(left)[#unit-title],
          align(right)[#if variant == "student" [Schülerversion] else [Lehrerversion]],
        )
        line(length: 100%, stroke: 0.4pt + line-grey)
      }
    },
    footer: context {
      if counter(page).get().first() > 1 {
        set text(font: sans-font, size: 8.5pt, fill: muted)
        align(center)[#counter(page).display()]
      }
    },
  )
  set text(font: body-font, size: 11pt, fill: ink, lang: "de", hyphenate: true)
  set par(justify: true, leading: 0.72em, spacing: 1.1em)

  // Rubriken (Level 1) werden nummeriert; Unterebenen nicht.
  set heading(numbering: (..n) => if n.pos().len() == 1 { numbering("01", n.pos().first()) })

  // Level-2/3-Ueberschriften: schlicht, in der Display-Schrift.
  show heading: set text(font: display-font, fill: ink)
  show heading.where(level: 2): set text(size: 13pt)
  show heading.where(level: 3): set text(size: 11.5pt)
  show heading.where(level: 2): it => block(above: 1.3em, below: 0.6em, it.body)
  show heading.where(level: 3): it => block(above: 1.1em, below: 0.5em, it.body)

  // Rubrik-Trenner (Level 1): eigene Seite, Nummer + Titel + Linie.
  show heading.where(level: 1): it => context {
    let nr = counter(heading).display()
    pagebreak(weak: true)
    block(above: 0em, below: 1.1em, breakable: false, {
      line(length: 100%, stroke: 0.9pt + accent)
      v(0.55em)
      grid(
        columns: (auto, 1fr),
        column-gutter: 0.8em,
        align: horizon,
        text(font: sans-font, size: 20pt, weight: "bold", fill: accent)[#nr],
        text(font: display-font, size: 17pt, fill: ink)[#it.body],
      )
    })
  }

  set list(indent: 0.6em, spacing: 0.7em)
  set enum(indent: 0.6em, spacing: 0.7em)
  show quote.where(block: true): it => block(
    inset: (left: 1em, y: 0.2em),
    stroke: (left: 2pt + line-grey),
    text(style: "italic", fill: muted, it.body),
  )
  doc
}

// ---- Callout-Boxen -----------------------------------------------------
#let callout(title: none, fill: accent-soft, bar: accent, body) = {
  block(
    width: 100%,
    fill: fill,
    inset: (x: 1em, y: 0.9em),
    radius: 2pt,
    stroke: (left: 3pt + bar),
    breakable: true,
    {
      if title != none {
        text(font: sans-font, weight: "bold", size: 9.5pt, fill: bar, tracking: 0.4pt)[#upper(title)]
        v(0.4em, weak: true)
      }
      body
    },
  )
}

#let objectives-box(title: "Lernziele", body) = callout(title: title, fill: teach-soft, bar: teach, body)
#let teacher-box(title: "Für die Lehrkraft", body) = callout(title: title, fill: accent-soft, bar: accent, body)
#let warn-box(title: "Prüfen vor Gebrauch", body) = callout(title: title, fill: warn-soft, bar: warn, body)

// ---- Cover -------------------------------------------------------------
#let cover(unit-title: "", subject: "", grade: "", duration: "", lines: (), variant: "teacher", image-path: none) = {
  set page(header: none, footer: none)
  v(2.3cm)
  align(center)[
    #text(font: sans-font, size: 10pt, fill: accent, tracking: 2pt)[UNTERRICHTSEINHEIT]
    #v(0.7cm)
    #text(font: display-font, size: 30pt, weight: "medium", fill: ink)[#unit-title]
    #v(0.5cm)
    #text(font: sans-font, size: 11pt, fill: muted)[
      #subject
      #if grade != "" [ · #grade ]
      #if duration != "" [ · #duration ]
    ]
  ]
  if image-path != none {
    v(1.1cm)
    align(center, box(width: 52%, image(image-path, width: 100%)))
    v(1.0cm)
  } else {
    v(1.3cm)
    align(center, line(length: 28%, stroke: 0.6pt + line-grey))
    v(1.3cm)
  }
  if lines.len() > 0 {
    align(center)[
      #for l in lines {
        text(font: display-font, size: 13pt, style: "italic", fill: accent)[#l]
        v(0.5cm, weak: true)
      }
    ]
  }
  align(center + bottom)[
    #v(1fr)
    #text(font: sans-font, size: 9pt, fill: muted)[
      #if variant == "student" [Schülerversion] else [Lehrerversion]
      · erstellt mit create-teaching-content
    ]
  ]
  pagebreak()
}

// ---- Ueberblick: Lernziele + Inhaltsverzeichnis ------------------------
#let overview(objectives-body, variant: "teacher") = {
  objectives-box(objectives-body)
  v(1em)
  heading(level: 2, outlined: false, numbering: none)[Inhalt]
  show outline.entry: set text(font: sans-font, size: 10.5pt)
  outline(title: none, target: heading.where(level: 1), depth: 1)
}

// ---- Rubrik-Trenner (nutzt die Level-1-Ueberschrift) -------------------
#let section-divider(title, purpose: none) = {
  heading(level: 1, title)
  if purpose != none {
    text(font: sans-font, size: 9.5pt, fill: muted, style: "italic")[#purpose]
    v(0.6em)
  }
}

// ---- Artikel (zweispaltig; Titel optional) -----------------------------
#let article(title: none, source: none, body) = {
  block(breakable: true, {
    if title != none { heading(level: 2, outlined: false, numbering: none, title) }
    if source != none {
      text(font: sans-font, size: 8.5pt, fill: muted)[Quelle: #source]
      v(0.4em, weak: true)
    }
    columns(2, gutter: 1.2em, body)
  })
}

// ---- Schreiblinien -----------------------------------------------------
#let writing-lines(n: 3) = {
  v(0.4em)
  for _ in range(n) {
    line(length: 100%, stroke: 0.5pt + line-grey)
    v(0.9em)
  }
}

// ---- Arbeitsblatt ------------------------------------------------------
#let worksheet(title: "", task: "", body: none, support: none, extension: none, variant: "teacher") = {
  pagebreak(weak: true)
  block(breakable: true, {
    text(font: sans-font, size: 9pt, fill: accent, tracking: 1.5pt)[ARBEITSBLATT]
    v(0.2em, weak: true)
    heading(level: 2, outlined: false, numbering: none, title)
    callout(title: "Auftrag", fill: accent-soft, bar: accent)[#task]
    if body != none { body }
    if variant == "teacher" and (support != none or extension != none) {
      callout(title: "Differenzierung", fill: teach-soft, bar: teach)[
        #if support != none [*Unterstützung:* #support \ ]
        #if extension != none [*Erweiterung:* #extension]
      ]
    }
    v(1.5em)
    text(font: sans-font, size: 9pt, fill: muted)[Name: #box(width: 6cm, line(length: 100%, stroke: 0.5pt + line-grey))   Datum: #box(width: 3cm, line(length: 100%, stroke: 0.5pt + line-grey))]
  })
}

// ---- Kolophon / Quellen ------------------------------------------------
#let colophon(sources: (), keywords: ()) = {
  pagebreak(weak: true)
  heading(level: 2, outlined: false, numbering: none)[Quellen & Angaben]
  if sources.len() > 0 {
    for s in sources [ - #s ]
  } else [
    #text(fill: muted)[Keine Quellen angegeben.]
  ]
  if keywords.len() > 0 {
    v(1em)
    text(font: sans-font, size: 9pt, fill: muted)[Schlagwörter: #keywords.join(" · ")]
  }
}
