// Modelo de artigo da SBC (sbc-template.sty, versão 2017) em Typst.
//
// Medidas tiradas do sbc-template.sty e conferidas contra o PDF do exemplo oficial
// compilado com pdflatex:
//   A4; margens 3,5 cm (sup.), 2,5 cm (inf.), 3 cm (laterais); sem número de página;
//   Times 12/14,4 pt; \parskip 6 pt; \parindent 1,27 cm (não no 1º parágrafo da seção);
//   seção 13/17 pt negrito, "1." + 1ex; subseção 12 pt negrito, "1.1.";
//   título 16/20 pt negrito; autores 12 pt negrito; endereços 12 pt; e-mails Courier 10 pt;
//   Abstract/Resumo em itálico, recuo de 0,8 cm dos dois lados, rótulo em negrito itálico;
//   legendas Helvetica 10/12 pt negrito, "Figura 1." centralizada se cabe numa linha,
//   senão justificada com margem de 0,8 cm e recuo pendente; legenda de tabela acima;
//   referências [Autor Ano], lista com recuo pendente e 6 pt entre itens (sbc.csl).
//
// Fontes: TeX Gyre Termes, Heros e Cursor (clones livres de Times, Helvetica e Courier,
// com as mesmas métricas), em presentation/fonts. Compilar com --font-path presentation/fonts.

#let serifa = ("TeX Gyre Termes", "Nimbus Roman")
#let sem-serifa = ("TeX Gyre Heros", "Nimbus Sans")
#let mono = ("TeX Gyre Cursor", "Nimbus Mono PS")

// Altura de linha no estilo LaTeX: a caixa de cada linha mede 1 em, e o espaço entre
// linhas completa o \baselineskip.
#let entrelinha(tamanho, baseline) = baseline - tamanho

// Bloco de Abstract/Resumo: lista com margem de 0,8 cm dos dois lados.
#let bloco-resumo(rotulo, corpo) = pad(x: 0.8cm, {
  set par(first-line-indent: 0pt)
  set text(style: "italic")
  [#text(weight: "bold")[#rotulo.] #corpo]
})

#let sbc(
  titulo: none,
  autores: (),          // ((nome: "Fulano", inst: 1), ...)
  instituicoes: (),     // (conteúdo da 1ª instituição, da 2ª, ...)
  emails: none,
  abstract: none,
  resumo: none,
  idioma: "pt",
  doc,
) = {
  set document(title: titulo, author: autores.map(a => a.nome))
  // O LaTeX põe a 1ª linha de base 12 pt (\topskip) abaixo da margem e deixa os descendentes
  // da última linha invadirem a margem inferior; o Typst mede a caixa da linha. As margens
  // compensam essa diferença, mantendo as mesmas 46 linhas por página.
  set page(paper: "a4", margin: (top: 3.5cm + 3.7pt, bottom: 2.5cm - 2.4pt, x: 3cm), numbering: none)
  set text(font: serifa, size: 12pt, lang: idioma, top-edge: 0.8em, bottom-edge: -0.2em)
  set par(justify: true, leading: entrelinha(12pt, 14.4pt), spacing: entrelinha(12pt, 14.4pt) + 6pt,
    first-line-indent: 1.27cm)

  // Seções: "1. Título", 12 pt extras antes (6 pt do \@startsection + 6 pt do \parskip).
  set heading(numbering: "1.1.")
  show heading: it => {
    let (tam, base) = if it.level == 1 { (13pt, 17pt) } else { (12pt, 14.4pt) }
    set text(size: tam, weight: "bold")
    set par(leading: entrelinha(tam, base), justify: false, first-line-indent: 0pt)
    block(above: 15pt + entrelinha(tam, base) - 2.4pt, below: 6pt + entrelinha(12pt, 14.4pt), sticky: true, {
      if it.numbering != none { counter(heading).display(it.numbering); h(0.45em) }
      it.body
    })
  }

  // Listas: rótulo alinhado à direita numa faixa de 1,27 cm, sem espaço extra entre itens.
  let faixa = 1.27cm - 6pt
  set list(indent: 0pt, body-indent: 6pt, spacing: entrelinha(12pt, 14.4pt),
    marker: box(width: faixa, align(right, [•])))
  set enum(indent: 0pt, body-indent: 6pt, spacing: entrelinha(12pt, 14.4pt),
    numbering: (..n) => box(width: faixa, align(right, numbering("1.", ..n))))

  // Legendas.
  set figure(gap: 10pt)
  show figure.where(kind: table): set figure.caption(position: top)
  show figure: set block(above: 12pt, below: 12pt)
  show figure.caption: it => {
    set text(font: sem-serifa, size: 10pt, weight: "bold", top-edge: 0.8em, bottom-edge: -0.2em)
    set par(leading: entrelinha(10pt, 12pt), first-line-indent: 0pt, justify: true)
    let rotulo = [#it.supplement #context it.counter.display(it.numbering)#it.separator]
    // Âncora dentro do flutuante: a legenda acompanha a figura, a posição original não.
    context [#metadata((tipo: it.kind, n: it.counter.get())) <sbc-legenda>]
    layout(area => {
      let inteira = rotulo + it.body
      if measure(inteira).width <= area.width - 1.6cm {
        align(center, inteira)
      } else {
        // Opção indent do caption: linhas seguintes recuadas em \leftmargini (2,5 em ≈ 29,3 pt).
        align(left, pad(x: 0.8cm, par(hanging-indent: 29.3pt, inteira)))
      }
    })
  }
  set figure.caption(separator: ". ")

  // Referência a figura flutuante: o Typst aponta o link para onde a figura foi declarada,
  // não para onde ela foi parar. O link passa a ir para o topo da página da legenda.
  show ref: it => {
    let el = it.element
    if el == none or el.func() != figure or el.placement == none { return it }
    context {
      let n = el.counter.at(el.location())
      let alvo = query(<sbc-legenda>).find(m => m.value.tipo == el.kind and m.value.n == n)
      if alvo == none { return it }
      let sup = if it.supplement == auto { el.supplement } else { it.supplement }
      link((page: alvo.location().page(), x: 0pt, y: 0pt), [#sup~#numbering(el.numbering, ..n)])
    }
  }

  // Referências: estilo sbc.csl, título de seção sem número.
  set bibliography(style: "sbc.csl", title: if idioma == "pt" { "Referências" } else { "References" })
  show bibliography: it => {
    // Recuo pendente: o sbc-template.sty usa ≈ 13,8 pt (0,5 cm); o Typst fixa o recuo do CSL
    // em 1,5 em (18 pt), e não há como mudar. É a única diferença visível para o LaTeX.
    set par(first-line-indent: 0pt, spacing: entrelinha(12pt, 14.4pt) + 6pt, justify: true)
    show heading: set heading(numbering: none)
    it
  }

  set footnote.entry(separator: line(length: 30%, stroke: 0.4pt))
  show raw: set text(font: mono, size: 1.25em)
  show link: it => it

  // Primeira página.
  {
    set par(justify: false, first-line-indent: 0pt)
    set align(center)
    v(-0.7cm + 26.8pt - 3.7pt) // \vspace*{-.7cm} + o espaço que o \maketitle do LaTeX põe antes
    block(below: 12.2pt, {
      set text(size: 16pt, weight: "bold")
      set par(leading: entrelinha(16pt, 20pt))
      titulo
    })
    block(below: 15.8pt, text(weight: "bold",
      autores.map(a => [#a.nome#super(typographic: false, str(a.inst))]).join(", ")))
    for (i, inst) in instituicoes.enumerate() {
      block(above: 0pt, below: if i < instituicoes.len() - 1 { 10.7pt } else { 0pt },
        [#super(typographic: false, str(i + 1))#inst])
    }
    if emails != none {
      block(above: 11.7pt, text(font: mono, size: 10pt, emails))
    }
    v(6pt)
  }
  if abstract != none { block(above: 12.2pt, below: 0pt, bloco-resumo("Abstract", abstract)) }
  if resumo != none { block(above: 17.6pt, below: 0pt, bloco-resumo("Resumo", resumo)) }
  v(2.7pt)

  doc
}
