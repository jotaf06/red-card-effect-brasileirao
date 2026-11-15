// Componentes gráficos dos slides, desenhados direto no Typst a partir das tabelas do pipeline.
#import "tema.typ": *
#import "dados.typ": fmt

#let grade = 0.5pt + cor.cal.transparentize(82%)
#let eixo-texto(corpo) = text(..rotulo-fonte, size: 13pt, fill: cor.suave, corpo)

// ------------------------------------------------------------------ placar de TV
#let placar-tv(mand, gm, gv, vis, minuto) = box(
  fill: cor.painel, stroke: 0.6pt + cor.borda, radius: 3pt, inset: 0pt, clip: true,
  grid(columns: 5, align: horizon,
    box(inset: (x: 16pt, y: 10pt), text(..titulo-fonte, size: 34pt, upper(mand))),
    box(fill: cor.texto, inset: (x: 14pt, y: 10pt), text(..titulo-fonte, size: 34pt, fill: cor.sombra, [#gm – #gv])),
    box(inset: (x: 16pt, y: 10pt), text(..titulo-fonte, size: 34pt, upper(vis))),
    box(fill: cor.sombra, inset: (x: 14pt, y: 10pt), text(..titulo-fonte, size: 34pt, fill: cor.amarelo, minuto)),
    box(inset: (x: 14pt, y: 8pt), cartao(cor.vermelho, h: 30pt)),
  ),
)

// ------------------------------------------------------------------ linha do tempo de uma partida
// eventos: (t, tipo, rotulo, alto); trechos: (inicio, fim, placar, cor); marcas: (t, rotulo)
#let linha-do-tempo(largura, fim, eventos, trechos, marcas) = {
  let x(t) = largura * t / fim
  box(width: largura, height: 4.4cm, {
    for (t, tipo, rotulo, alto) in eventos {
      let marca = if tipo == "vermelho" { cartao(cor.vermelho, h: 20pt) } else if tipo == "amarelo" {
        cartao(cor.amarelo, h: 15pt) } else { circle(radius: 7pt, fill: cor.texto) }
      place(top + left, dx: x(t) - 6pt, dy: 1.15cm, marca)
      if rotulo != "" {
        place(top + left, dx: x(t) - 0.2cm, dy: if alto { 0cm } else { 0.5cm },
          text(..rotulo-fonte, size: 12pt, fill: cor.texto, rotulo))
      }
    }
    for (i, (a, b, placar, c)) in trechos.enumerate() {
      place(top + left, dx: x(a) + 1pt, dy: 2.1cm,
        rect(width: x(b) - x(a) - 2pt, height: 1cm, fill: cor.sombra.transparentize(20%), stroke: 1.6pt + c,
          align(center + horizon, text(..rotulo-fonte, size: 13pt, if x(b) - x(a) > 1.4cm { placar }))))
      place(top + left, dx: x(a) + 3pt, dy: 3.2cm, eixo-texto[T#i])
    }
    for (t, r) in marcas {
      place(top + left, dx: x(t), dy: 3.7cm, eixo-texto(r))
    }
  })
}

// ------------------------------------------------------------------ campo com zonas
// zonas: (fx, fy, rotulo, razao, ic_inf, ic_sup)
#let campo(largura, altura, zonas) = box(width: largura, height: altura, {
  for i in range(10) {
    place(top + left, dx: largura * i / 10, rect(width: largura / 10 + 0.3pt, height: altura,
      fill: if calc.even(i) { rgb("#12321e") } else { rgb("#153822") }))
  }
  let s = 1.2pt + cor.cal.transparentize(35%)
  place(rect(width: largura, height: altura, stroke: s))
  place(dx: largura / 2, line(length: altura, angle: 90deg, stroke: s))
  place(center + horizon, circle(radius: altura * 0.15, stroke: s))
  place(left + horizon, rect(width: largura * 0.14, height: altura * 0.55, stroke: s))
  place(left + horizon, rect(width: largura * 0.05, height: altura * 0.26, stroke: s))
  place(right + horizon, rect(width: largura * 0.14, height: altura * 0.55, stroke: s))
  place(right + horizon, rect(width: largura * 0.05, height: altura * 0.26, stroke: s))
  for (fx, fy, rotulo, r, inf, sup) in zonas {
    let c = if inf > 1 { cor.vermelho } else if sup < 1 { cor.destaque } else { cor.texto }
    place(top + left, dx: largura * fx - 1.6cm, dy: altura * fy - 1.1cm, box(width: 3.2cm,
      align(center, box(fill: cor.sombra.transparentize(10%), stroke: 1.2pt + c, radius: 3pt, inset: 8pt, width: 100%)[
        #text(..titulo-fonte, size: 40pt, fill: c, fmt(r) + "×") \
        #v(-14pt)
        #text(..rotulo-fonte, size: 11pt, fill: cor.texto, tracking: 1pt, upper(rotulo))
      ])))
  }
})

// ------------------------------------------------------------------ barras verticais com IC
// itens: array de dicionários (rotulo, valor, inf, sup, cor); ymin pode ser negativo.
#let barras(itens, largura: 16cm, altura: 7cm, ymin: 0, ymax: 1, ticks: (), fmt-y: v => fmt(v, d: 2),
  fmt-valor: v => fmt(v, d: 2)) = {
  let esq = 1.5cm
  let base = altura - 1.1cm
  let w = (largura - esq) / itens.len()
  let y(v) = base * (1 - (v - ymin) / (ymax - ymin))
  let zero = y(calc.max(ymin, 0))
  box(width: largura, height: altura, {
    for t in ticks {
      place(top + left, dx: esq, dy: y(t), line(length: largura - esq, stroke: grade))
      place(top + left, dy: y(t) - 0.3cm, box(width: esq - 0.25cm, align(right, eixo-texto(fmt-y(t)))))
    }
    place(top + left, dx: esq, dy: zero, line(length: largura - esq, stroke: 0.8pt + cor.cal.transparentize(40%)))
    for (i, it) in itens.enumerate() {
      let bw = w * 0.6
      let x0 = esq + w * i + (w - bw) / 2
      let yv = y(it.valor)
      let (topo, h) = if yv < zero { (yv, zero - yv) } else { (zero, yv - zero) }
      place(top + left, dx: x0, dy: topo, rect(width: bw, height: h, fill: it.cor))
      if "inf" in it {
        let (a, b) = (y(it.sup), y(it.inf))
        place(top + left, dx: x0 + bw / 2, dy: a, line(length: b - a, angle: 90deg, stroke: 1.3pt + cor.texto))
        place(top + left, dx: x0 + bw / 2 - 5pt, dy: a, line(length: 10pt, stroke: 1.3pt + cor.texto))
        place(top + left, dx: x0 + bw / 2 - 5pt, dy: b, line(length: 10pt, stroke: 1.3pt + cor.texto))
      }
      let dy-rot = if it.valor >= 0 { calc.min(yv, if "sup" in it { y(it.sup) } else { yv }) - 0.65cm }
        else { calc.max(yv, if "inf" in it { y(it.inf) } else { yv }) + 0.15cm }
      place(top + left, dx: x0 + bw + 2pt, dy: dy-rot + (if it.valor >= 0 { 0.35cm } else { -0.45cm }),
        text(..titulo-fonte, size: 20pt, fill: it.cor, fmt-valor(it.valor)))
      place(top + left, dx: esq + w * i, dy: base + 0.25cm, box(width: w, align(center, eixo-texto(it.rotulo))))
    }
  })
}

// ------------------------------------------------------------------ intervalos (escala log), para razões de taxa
// linhas: (rotulo, valor, inf, sup, cor)
#let intervalos(linhas, largura: 18cm, rotulo-larg: 7cm, xmin: 0.5, xmax: 4, ticks: (0.5, 1, 2, 4), passo: 1.05cm) = {
  let area = largura - rotulo-larg - 1.6cm
  let x(v) = rotulo-larg + area * (calc.ln(v) - calc.ln(xmin)) / (calc.ln(xmax) - calc.ln(xmin))
  let altura = passo * linhas.len() + 0.9cm
  box(width: largura, height: altura, {
    for t in ticks {
      place(top + left, dx: x(t), line(length: altura - 0.8cm, angle: 90deg,
        stroke: if t == 1 { (paint: cor.cal.transparentize(30%), thickness: 1pt, dash: "dashed") } else { grade }))
      place(top + left, dx: x(t) - 0.4cm, dy: altura - 0.6cm, box(width: 0.8cm, align(center, eixo-texto(fmt(t, d: if t < 1 { 1 } else { 0 }) + "×"))))
    }
    for (i, (rotulo, v, inf, sup, c)) in linhas.enumerate() {
      let yy = passo * i + passo / 2
      place(top + left, dy: yy - 0.32cm, box(width: rotulo-larg - 0.3cm, align(right, text(size: 16pt, rotulo))))
      place(top + left, dx: x(inf), dy: yy, line(length: x(sup) - x(inf), stroke: 2.4pt + c))
      place(top + left, dx: x(v) - 6pt, dy: yy - 6pt, circle(radius: 6pt, fill: c, stroke: 1.2pt + cor.sombra))
      place(top + left, dx: x(sup) + 6pt, dy: yy - 0.38cm, text(..titulo-fonte, size: 20pt, fill: c, fmt(v) + "×"))
    }
  })
}

// ------------------------------------------------------------------ curvas com faixa de IC
// series: (nome, cor, pontos: ((x, y, inf, sup), ...))
#let curvas(series, largura: 18cm, altura: 8cm, xmin: 0, xmax: 90, ymin: -1, ymax: 0.2,
  xticks: (), yticks: (), fmt-x: v => str(v) + "'", fmt-y: v => fmt(v, d: 1)) = {
  let esq = 1.5cm
  let base = altura - 0.9cm
  let x(v) = esq + (largura - esq - 0.3cm) * (v - xmin) / (xmax - xmin)
  let y(v) = base * (1 - (v - ymin) / (ymax - ymin))
  box(width: largura, height: altura, {
    for t in yticks {
      place(top + left, dx: esq, dy: y(t), line(length: largura - esq, stroke: if t == 0 { 0.9pt + cor.cal.transparentize(40%) } else { grade }))
      place(top + left, dy: y(t) - 0.3cm, box(width: esq - 0.25cm, align(right, eixo-texto(fmt-y(t)))))
    }
    for t in xticks {
      place(top + left, dx: x(t) - 0.5cm, dy: base + 0.2cm, box(width: 1cm, align(center, eixo-texto(fmt-x(t)))))
    }
    for (nome, c, pts) in series {
      let banda = pts.map(p => (x(p.at(0)), y(p.at(3)))) + pts.rev().map(p => (x(p.at(0)), y(p.at(2))))
      place(top + left, polygon(fill: c.transparentize(78%), stroke: none, ..banda))
      for i in range(pts.len() - 1) {
        let (a, b) = (pts.at(i), pts.at(i + 1))
        place(top + left, line(start: (x(a.at(0)), y(a.at(1))), end: (x(b.at(0)), y(b.at(1))), stroke: 2.6pt + c))
      }
    }
  })
}

// Legenda simples: (cor, rótulo)
#let legenda(..itens) = itens.pos().map(((c, r)) => box(inset: (right: 14pt))[#box(baseline: 1pt, rect(width: 14pt, height: 5pt, fill: c)) #h(4pt) #eixo-texto(r)]).join()
