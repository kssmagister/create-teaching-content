// theme.typ -- Layout & Stil fuer Unterrichtseinheiten (Reader-Modell v2).
// Dramaturgie: Cover -> Ueberblick (Lernziele + Inhalt) -> [Lehrerteil]
//   -> Vorwissen -> Einleitung -> Haupttext (Text/Quelle/Abbildung/Tabelle)
//   -> Verstaendnisfragen -> Aufgaben -> Glossar -> [Loesungen] -> Apparat.

// ---- Schriften ---------------------------------------------------------
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
#let conf(titel: "", variant: "teacher", doc) = {
  set document(title: titel)
  set page(
    paper: "a4",
    margin: (top: 2.4cm, bottom: 2.4cm, x: 2.5cm),
    header: context {
      if counter(page).get().first() > 1 {
        set text(font: sans-font, size: 8.5pt, fill: muted)
        grid(
          columns: (1fr, auto),
          align(left)[#titel],
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
  // Fliesstext mit Mediaevalziffern (onum) -- ruhiger Lesefluss.
  set text(font: body-font, size: 11pt, fill: ink, lang: "de",
           hyphenate: true, number-type: "old-style")
  set par(justify: true, leading: 0.75em, spacing: 1.15em)

  // Abbildungen und Tabellen: eigene Zaehler, deutsche Kuerzel.
  set figure(numbering: "1")
  show figure.where(kind: image): set figure(supplement: [Abb.])
  show figure.where(kind: table): set figure(supplement: [Tab.])
  show figure.caption: set text(size: 9pt, fill: muted, font: sans-font)
  set figure.caption(separator: [ — ])

  // Rubriken (Level 1) werden nummeriert; Unterebenen nicht.
  set heading(numbering: (..n) => if n.pos().len() == 1 { numbering("01", n.pos().first()) })
  show heading: set text(font: display-font, fill: ink)
  show heading.where(level: 2): set text(size: 13pt)
  show heading.where(level: 3): set text(size: 11.5pt)
  show heading.where(level: 2): it => block(above: 1.3em, below: 0.6em, it.body)
  show heading.where(level: 3): it => block(above: 1.1em, below: 0.5em, it.body)
  show heading.where(level: 1): it => context {
    let nr = counter(heading).display()
    pagebreak(weak: true)
    block(above: 0em, below: 1.1em, breakable: false, {
      line(length: 100%, stroke: 0.9pt + accent)
      v(0.55em)
      grid(
        columns: (auto, 1fr), column-gutter: 0.8em, align: horizon,
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
    width: 100%, fill: fill, inset: (x: 1em, y: 0.9em), radius: 2pt,
    stroke: (left: 3pt + bar), breakable: true,
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
#let prior-box(title: "Vorwissen aktivieren", body) = callout(title: title, fill: accent-soft, bar: accent, body)

// ---- Cover -------------------------------------------------------------
#let cover(titel: "", fach: "", stufe: "", dauer: "", zeilen: (), variant: "teacher", bild: none) = {
  set page(header: none, footer: none)
  v(2.3cm)
  align(center)[
    #text(font: sans-font, size: 10pt, fill: accent, tracking: 2pt)[UNTERRICHTSEINHEIT]
    #v(0.7cm)
    #text(font: display-font, size: 30pt, weight: "medium", fill: ink)[#titel]
    #v(0.5cm)
    #text(font: sans-font, size: 11pt, fill: muted)[
      #fach #if stufe != "" [ · #stufe ] #if dauer != "" [ · #dauer ]
    ]
  ]
  if bild != none {
    v(1.1cm); align(center, box(width: 52%, image(bild, width: 100%))); v(1.0cm)
  } else {
    v(1.3cm); align(center, line(length: 28%, stroke: 0.6pt + line-grey)); v(1.3cm)
  }
  if zeilen.len() > 0 {
    align(center)[
      #for l in zeilen {
        text(font: display-font, size: 13pt, style: "italic", fill: accent)[#l]
        v(0.5cm, weak: true)
      }
    ]
  }
  align(center + bottom)[
    #v(1fr)
    #text(font: sans-font, size: 9pt, fill: muted)[
      #if variant == "student" [Schülerversion] else [Lehrerversion] · erstellt mit create-teaching-content
    ]
  ]
  pagebreak()
}

// ---- Ueberblick: Lernziele + Inhaltsverzeichnis ------------------------
#let overview(objectives-body) = {
  objectives-box(objectives-body)
  v(1em)
  heading(level: 2, outlined: false, numbering: none)[Inhalt]
  show outline.entry: set text(font: sans-font, size: 10.5pt)
  outline(title: none, target: heading.where(level: 1), depth: 1)
}

// ---- Rubrik-Trenner ----------------------------------------------------
#let rubrik(titel) = { heading(level: 1, titel) }

// ---- Quellentext (eingerueckt, kursiv, kleiner) ------------------------
#let quelle(autor: none, titel: none, body) = block(
  width: 100%, inset: (left: 1em, y: 0.3em), stroke: (left: 2pt + accent), breakable: true,
  {
    set text(size: 9.5pt)
    set par(leading: 0.65em)
    emph(body)
    if autor != none or titel != none {
      v(0.4em, weak: true)
      set text(size: 8.5pt, fill: muted, font: sans-font)
      align(right)[— #if autor != none [#autor]#if titel != none [, #emph(titel)]]
    }
  },
)

// ---- Abbildung ---------------------------------------------------------
#let abbildung(pfad, beschriftung: "", quelle: none, breite: 85%) = figure(
  image(pfad, width: breite),
  caption: {
    beschriftung
    if quelle != none [ #text(size: 8pt)[(Quelle: #quelle)] ]
  },
)

// ---- Tabelle (Versalziffern fuer Spaltenbuendigkeit) -------------------
#let tabelle(kopf: (), zeilen: (), beschriftung: none) = {
  set text(number-type: "lining")
  let head = kopf.map(h => table.cell(fill: accent-soft,
    text(font: sans-font, weight: "bold", size: 9.5pt)[#h]))
  let body-rows = zeilen.map(r => r.map(c => [#c])).flatten()
  let t = table(
    columns: kopf.len(),
    stroke: (x, y) => (bottom: 0.5pt + line-grey),
    inset: (x: 0.7em, y: 0.5em),
    ..head, ..body-rows,
  )
  if beschriftung != none { figure(t, kind: table, caption: beschriftung) } else { t }
}

// ---- Aufgabe (serifenlos, AFB-Badge) -----------------------------------
#let afb-roman(n) = ("I", "II", "III").at(calc.clamp(n, 1, 3) - 1)
#let aufgabe(nummer, afb, body) = block(
  width: 100%, fill: accent-soft, inset: (x: 1em, y: 0.8em), radius: 2pt,
  stroke: (left: 3pt + accent), breakable: true,
  {
    set text(font: sans-font, size: 10.5pt)
    grid(
      columns: (auto, 1fr), column-gutter: 0.7em, align: (top, top),
      text(weight: "bold", fill: accent)[#nummer.],
      {
        box(fill: accent, inset: (x: 0.4em, y: 0.15em), radius: 2pt,
            text(size: 7.5pt, fill: white, weight: "bold", tracking: 0.3pt)[AFB #afb-roman(afb)])
        h(0.5em)
        body
      },
    )
  },
)

// ---- Glossar -----------------------------------------------------------
#let glossar(eintraege) = {
  for e in eintraege {
    block(above: 0.6em, below: 0.6em, breakable: false,
      grid(columns: (4.5cm, 1fr), column-gutter: 0.6em,
        text(font: sans-font, weight: "bold", size: 10pt, fill: accent)[#e.begriff],
        [#e.definition]))
  }
}

// ---- Bibliografie ------------------------------------------------------
#let bibliografie(eintraege) = {
  set par(hanging-indent: 1.2em, justify: false)
  set text(size: 10pt)
  for e in eintraege {
    block(below: 0.6em, {
      if "autor" in e [#e.autor: ]
      emph(e.titel)
      if "ort" in e or "verlag" in e or "jahr" in e [. ]
      if "ort" in e [#e.ort#if "verlag" in e [: ] else [, ]]
      if "verlag" in e [#e.verlag, ]
      if "jahr" in e [#str(e.jahr)]
      [.]
      if "url" in e [ #text(size: 8.5pt, fill: muted)[#link(e.url)]]
    })
  }
}

// ---- Apparat-Ueberschrift (unnummeriert) + Verzeichnisse ---------------
#let apparat-heading(titel) = heading(level: 2, outlined: false, numbering: none, titel)
#let bildverzeichnis() = context {
  if query(figure.where(kind: image)).len() > 0 {
    apparat-heading("Bildverzeichnis")
    outline(title: none, target: figure.where(kind: image))
  }
}
#let tabellenverzeichnis() = context {
  if query(figure.where(kind: table)).len() > 0 {
    apparat-heading("Tabellenverzeichnis")
    outline(title: none, target: figure.where(kind: table))
  }
}
