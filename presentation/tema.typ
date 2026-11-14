// Tema visual dos slides: gramado listrado, linhas de cal, cores dos cartões.
// Fontes em presentation/fonts (compilar com --font-path presentation/fonts).

#let cor = (
  faixa1: rgb("#1a4226"), // listras do gramado
  faixa2: rgb("#1e482a"),
  painel: rgb("#0d2c19").transparentize(15%),
  borda: rgb("#ffffff").transparentize(78%),
  texto: rgb("#f4f7f2"),
  suave: rgb("#c4d8c8"),
  cal: rgb("#ffffff"), // linhas do campo
  destaque: rgb("#c8f560"), // verde-limão: o que é bom / concluído
  amarelo: rgb("#ffd23f"),
  vermelho: rgb("#ff5a4e"),
  sombra: rgb("#0c2615"),
)

#let titulo-fonte = (font: "Bebas Neue", weight: 400)
#let rotulo-fonte = (font: "Fira Sans", stretch: 75%, weight: 600)

// Gramado: listras verticais de corte, com a linha lateral de cal.
#let gramado(listras: 12) = {
  let w = 1200pt / listras
  for i in range(listras) {
    place(top + left, dx: w * i, rect(width: w + 0.5pt, height: 675pt,
      fill: if calc.even(i) { cor.faixa1 } else { cor.faixa2 }))
  }
  place(top + left, dx: 22pt, dy: 22pt,
    rect(width: 1200pt - 44pt, height: 675pt - 44pt, stroke: 1.4pt + cor.cal.transparentize(55%)))
}

#let tema(doc) = {
  set page(width: 1200pt, height: 675pt, margin: (x: 2.4cm, top: 1.7cm, bottom: 1.9cm),
    background: gramado())
  set text(lang: "pt", font: "Fira Sans", size: 21pt, fill: cor.texto)
  set par(justify: false, leading: 0.6em)
  set list(spacing: 0.85em, marker: text(fill: cor.amarelo, size: 13pt, baseline: -1pt)[●])
  set strong(delta: 300)
  show raw: set text(font: "Fira Mono", size: 0.85em)
  doc
}

// Cartão de árbitro.
#let cartao(c, h: 1em) = box(baseline: 15%, rect(width: h * 0.7, height: h, radius: 0.08 * h, fill: c,
  stroke: 0.6pt + cor.sombra.transparentize(40%)))

// Etiqueta de etapa, no estilo de faixa de transmissão.
#let etiqueta(etapa, codigo, sub, c: cor.destaque) = {
  box(fill: c, inset: (x: 9pt, y: 4pt),
    text(..rotulo-fonte, size: 13pt, fill: cor.sombra, tracking: 1.2pt, upper(etapa)))
  box(fill: cor.sombra.transparentize(30%), inset: (x: 9pt, y: 4pt),
    text(..rotulo-fonte, size: 13pt, fill: cor.texto, tracking: 1.2pt, upper(codigo + " · " + sub)))
}

#let slide(etapa: none, codigo: "", sub: "", c: cor.destaque, titulo: none, tempo: none, corpo) = {
  pagebreak(weak: true)
  if etapa != none { etiqueta(etapa, codigo, sub, c: c); v(2pt) }
  if titulo != none {
    text(..titulo-fonte, size: 46pt, titulo)
    v(6pt)
  }
  corpo
  if tempo != none {
    place(bottom + left, dy: 0.6cm, text(..rotulo-fonte, size: 11.5pt, fill: cor.suave, tracking: 1.5pt, upper(tempo)))
  }
  place(bottom + right, dy: 0.6cm, context box(fill: cor.sombra.transparentize(30%), inset: (x: 7pt, y: 3pt),
    text(..titulo-fonte, size: 17pt, fill: cor.amarelo, str(counter(page).get().first()) + "'")))
}

// Painel translúcido sobre o gramado.
#let painel(titulo: none, c: cor.amarelo, destaque: false, corpo) = block(
  fill: cor.painel, stroke: if destaque { 1.2pt + c } else { 0.6pt + cor.borda },
  inset: 13pt, radius: 4pt, width: 100%,
  {
    if titulo != none {
      text(..rotulo-fonte, size: 13pt, fill: c, tracking: 1.4pt, upper(titulo))
      v(1pt)
    }
    corpo
  },
)

// Número grande com legenda, como no placar.
#let numero(valor, legenda, c: cor.texto, tamanho: 44pt, destaque: false) = block(
  fill: cor.painel, stroke: if destaque { 1.2pt + cor.amarelo } else { 0.6pt + cor.borda },
  inset: (x: 14pt, top: 10pt, bottom: 12pt), radius: 4pt, width: 100%,
  {
    text(..titulo-fonte, size: tamanho, fill: c, valor)
    v(-10pt)
    text(..rotulo-fonte, size: 12pt, fill: cor.suave, tracking: 1pt, upper(legenda))
  },
)

#let ama(corpo) = text(fill: cor.amarelo, corpo)
#let verm(corpo) = text(fill: cor.vermelho, corpo)
#let verde(corpo) = text(fill: cor.destaque, corpo)

#let codigo(corpo) = block(fill: cor.sombra.transparentize(15%), stroke: (left: 2pt + cor.destaque), inset: 12pt,
  width: 100%, text(font: "Fira Mono", size: 12.5pt, fill: cor.suave, corpo))
