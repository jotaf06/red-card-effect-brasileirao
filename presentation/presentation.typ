// Apresentação: pitch (5 min) + parte técnica (15 min), no tema "gramado".
// Compilar a partir da raiz:
//   typst compile --root . --font-path presentation/fonts presentation/apresentacao.typ
#import "dados.typ": *
#import "tema.typ": *
#import "graficos.typ": *
#show: tema

#set document(title: "Quanto custa uma expulsão?", author: ("José Felix", "Rafael Anacleto"))

// Cores das etapas (pitch e KDD).
#let et = (
  pitch: cor.amarelo,
  selecao: rgb("#9fd8ff"),
  pre: cor.amarelo,
  trans: cor.destaque,
  mine: cor.vermelho,
  aval: rgb("#ffb35c"),
  interp: cor.cal,
)
#let PITCH = "1º tempo · pitch"
#let TEC = "2º tempo · apresentação técnica"
#let FIM = "pós-jogo"

// Números usados em mais de um slide.
#let p_aj = irr("ajustado", "estado[perdendo]")
#let p_sa = irr("sem ajuste", "estado[perdendo]")
#let v_aj = irr("ajustado", "estado[vencendo]")
#let v_sa = irr("sem ajuste", "estado[vencendo]")
#let z = formacao("Zagueiro")
#let g = formacao("Goleiro")
#let razao_fim = float(taxa_faixa("76–90+").taxa_90) / float(taxa_faixa("0–15").taxa_90)
#let att_todos = att("todos")
#let custo_ponto = calc.abs(float(att_todos.att))
#let gs = gols_irr("todos", "vantagem[superior]")
#let gi = gols_irr("todos", "vantagem[inferior]")
#let verm_temporada = float(chave(resumo, "vermelhos")) / (11 * 20) // 11 temporadas × 20 times
#let pct_acima(x) = fmt((float(x) - 1) * 100, d: 0) + "%"
#let pct_abaixo(x) = fmt((1 - float(x)) * 100, d: 0) + "%"
#let n_teste = int(metrica("logística multinomial").n_linhas)
#let n_landmarks = int(chave(resumo_features, "landmarks_linhas"))

// Métricas do P2 (arenas): só existem depois do merge de feat/tratamento-de-dados.
#let n_ou(k) = if resumo.find(l => l.chave == k) == none { "?" } else { n(k) }

// Partida de exemplo (exportada por src/features.py).
#let ex = tabela("exemplo_partida_eventos")
#let ex_trechos = tabela("exemplo_partida_trechos").filter(l => float(l.duracao) > 0)
#let nome_clube = ("Santos": "Santos", "Atletico-MG": "Atlético-MG")
#let sigla = ("Santos": "SAN", "Atletico-MG": "CAM")
#let ex0 = ex.at(0)
#let ex_mand = nome_clube.at(ex0.mandante)
#let ex_vis = nome_clube.at(ex0.visitante)
#let ex_verm = ex.find(l => l.tipo == "vermelho")
#let gols_antes(lado) = ex.filter(l => l.tipo == "gol" and l.lado == lado and float(l.t) < float(ex_verm.t)).len()
#let ex_posicao = lower(ex_verm.posicao)
#let ex_punido = nome_clube.at(ex_verm.clube)

// ===================================================================== CAPA
#place(center + horizon, circle(radius: 150pt, stroke: 1.4pt + cor.cal.transparentize(70%)))
#place(center + horizon, line(length: 675pt, angle: 90deg, stroke: 1.4pt + cor.cal.transparentize(70%)))
#place(center + horizon, circle(radius: 4pt, fill: cor.cal.transparentize(55%)))
#align(center + horizon)[
  #text(..rotulo-fonte, size: 13pt, fill: cor.destaque, tracking: 4pt)[ESTUDO DE CASO · CIÊNCIA DE DADOS NO BRASILEIRÃO]
  #v(14pt)
  #placar-tv(ex_mand, gols_antes("mandante"), gols_antes("visitante"), ex_vis, ex_verm.minuto + "'")
  #v(6pt)
  #text(..rotulo-fonte, size: 12pt, fill: cor.suave)[#ex0.data · #ex0.arena · #ex_posicao do #ex_punido expulso]
  #v(10pt)
  #text(..titulo-fonte, size: 96pt)[Quanto custa uma expulsão?]
  #v(-14pt)
  #block(width: 62%, fill: cor.sombra.transparentize(35%), inset: 12pt, radius: 4pt)[
    #text(size: 19pt)[Minuto, placar e posição do cartão vermelho em #n("partidas_2014_2024") partidas da Série A (2014–2024), e o que a comissão técnica pode fazer com isso.]
  ]
  #v(12pt)
  #text(size: 15pt)[José Felix · Rafael Anacleto]
  #v(-6pt)
  #text(size: 13pt, fill: cor.suave)[Ciência de Dados · UFAL/IC · 2026.1]
]

// ===================================================================== PITCH (5 min)

#slide(etapa: "Problema", codigo: "1/5", sub: "o que acontece hoje", c: et.pitch,
  titulo: [Um em cada cinco jogos do Brasileirão tem expulsão], tempo: PITCH)[
  #grid(columns: (1fr, 1fr, 1fr), gutter: 12pt,
    numero(n("vermelhos"), [cartões vermelhos em 2014–2024], c: cor.vermelho, tamanho: 60pt),
    numero(n("pct_partidas_com_vermelho") + "%", [das partidas têm pelo menos um], tamanho: 60pt),
    numero(fmt(verm_temporada, d: 1), [vermelhos por time, por temporada], c: cor.amarelo, tamanho: 60pt),
  )
  #v(14pt)
  #painel(titulo: "A pergunta da comissão técnica")[
    #text(size: 24pt, style: "italic")["Levamos vermelho de novo. Quanto isso nos custou, e dava para evitar?"]
  ]
  #v(4pt)
  Hoje, a resposta é decidida #ama[no improviso], à beira do campo.
]

#slide(etapa: "Oportunidade", codigo: "2/5", sub: "o vermelho tem padrão", c: et.pitch,
  titulo: [Vermelho não é azar: tem hora, placar e posição], tempo: PITCH)[
  #grid(columns: (1fr, 1fr, 1fr), gutter: 14pt,
    painel(titulo: "Hora", c: cor.amarelo)[
      #text(..titulo-fonte, size: 54pt, fill: cor.amarelo)[#fmt(razao_fim, d: 0)×] \
      #v(-12pt)
      mais vermelhos no fim do que no início
    ],
    painel(titulo: "Placar", c: cor.amarelo)[
      #text(..titulo-fonte, size: 54pt, fill: cor.amarelo)[+#pct_acima(p_aj.irr)] \
      #v(-12pt)
      de risco para quem está *perdendo*
    ],
    painel(titulo: "Posição", c: cor.amarelo)[
      #text(..titulo-fonte, size: 54pt, fill: cor.amarelo)[+#pct_acima(z.razao_obs_esp)] \
      #v(-12pt)
      de vermelhos para *zagueiros*
    ],
  )
  #v(14pt)
  #grid(columns: (1fr, 1fr), gutter: 14pt,
    painel(titulo: "Previsível → dá para prevenir", c: cor.destaque)[Trocar o atleta certo *antes*.],
    painel(titulo: "Custo medido → dá para reagir", c: cor.destaque)[Plano pronto para jogar com 10.],
  )
]

#slide(etapa: "Evidências", codigo: "3/5", sub: "o que os dados mostram", c: et.pitch,
  titulo: [Uma expulsão custa #fmt(custo_ponto) ponto, e a conta vem na defesa], tempo: PITCH)[
  #grid(columns: (1fr, 1fr, 1fr, 1fr), gutter: 12pt,
    numero("−" + fmt(custo_ponto), [ponto por expulsão], c: cor.vermelho, tamanho: 60pt),
    numero(pct_var(gs.irr), [gols sofridos, com um a menos], c: cor.vermelho, tamanho: 60pt),
    numero(pct_var(gi.irr), [gols marcados, com um a menos], c: cor.amarelo, tamanho: 60pt),
    numero(pct_var(p_aj.irr), [risco de vermelho perdendo], c: cor.amarelo, tamanho: 60pt),
  )
  #v(14pt)
#text(fill: cor.suave)[#att_todos.n_tratados expulsões comparadas a times no mesmo minuto, mando e placar · todos os números com IC 95%.]
]

#let perda_media = float(liga("pontos_perdidos_estimados").media)
#let corte_perto = ins_corte.filter(l => float(l.diferenca) <= calc.ceil(perda_media)).len()
#slide(etapa: "Decisão e impacto", codigo: "4/5", sub: "o que propomos", c: et.pitch,
  titulo: [Prevenir antes, reagir depois], tempo: PITCH)[
  #grid(columns: (1fr, 1fr, 1fr), gutter: 12pt,
    painel(titulo: "1 · Zona de risco até os 75'", c: cor.amarelo, destaque: true)[
      Advertido em lance de risco → *substituir*
    ],
    painel(titulo: "2 · Zagueiro advertido no 1º tempo", c: cor.amarelo, destaque: true)[
      #pct(conversao("zagueiro · 1º tempo").taxa)% são expulsos → *decidir no intervalo*
    ],
    painel(titulo: "3 · Plano para jogar com 10", c: cor.vermelho, destaque: true)[
      Sofridos #pct_var(gs.irr) → *fechar a defesa*
    ],
  )
  #v(14pt)
  #grid(columns: (1fr, 1.2fr), gutter: 14pt,
    numero([≈ #fmt(perda_media, d: 1) ponto], [perdido por time, por temporada, em expulsões], c: cor.destaque, tamanho: 56pt),
    painel(titulo: "Por que importa", c: cor.destaque)[
      Em *#corte_perto de #ins_corte.len()* temporadas, o 16º e o 17º ficaram separados por até #calc.ceil(perda_media) ponto.
    ],
  )
]

#slide(etapa: "Resumo", codigo: "5/5", sub: "em uma frase", c: et.pitch, tempo: PITCH)[
  #v(1fr)
  #align(center)[
    #cartao(cor.vermelho, h: 70pt)
    #v(10pt)
    #block(width: 80%, text(..titulo-fonte, size: 64pt)[Cada expulsão evitada vale #fmt(custo_ponto) ponto. E boa parte delas é previsível.])
  ]
  #v(1fr)
]

// ===================================================================== TÉCNICA (15 min)

#let etapa-caixa(c, nome, linhas) = block(fill: cor.painel, stroke: (top: 4pt + c, rest: 0.6pt + cor.borda), inset: 11pt, radius: 3pt, width: 100%, height: 8.6cm, {
  text(..rotulo-fonte, size: 15pt, fill: c, tracking: 1.4pt, upper(nome))
  v(4pt)
  set text(size: 16pt)
  linhas
})
#let seta-kdd = align(center + horizon, text(size: 26pt, fill: cor.suave)[→])

#slide(etapa: "Roteiro", codigo: "KDD", sub: "do arquivo à decisão", c: cor.cal,
  titulo: [Do CSV à recomendação: cinco etapas, cada uma com escolhas], tempo: TEC)[
  #grid(columns: (1fr, auto, 1fr, auto, 1fr, auto, 1fr, auto, 1fr), gutter: 6pt,
    etapa-caixa(et.selecao, "Seleção")[
      #text(..titulo-fonte, size: 34pt)[#n("partidas_total")] \ #v(-12pt) partidas no arquivo
      #v(2pt) → *#n("partidas_2014_2024")* em 2014–2024
    ], seta-kdd,
    etapa-caixa(et.pre, "Pré-processamento")[
      #text(..titulo-fonte, size: 34pt)[6] \ #v(-12pt) inconsistências tratadas
      #v(2pt) + *#n("posicao_nula_original")* posições ausentes
    ], seta-kdd,
    etapa-caixa(et.trans, "Transformação")[
      #text(..titulo-fonte, size: 34pt)[#nf("eventos_linhas")] \ #v(-12pt) eventos em linha do tempo
      #v(2pt) → *#nf("landmarks_linhas")* fotografias
    ], seta-kdd,
    etapa-caixa(et.mine, "Mineração")[
      #text(..titulo-fonte, size: 34pt)[3] \ #v(-12pt) métodos para o mesmo efeito
      #v(2pt) *#h1_equilibrio.tratados* expulsões pareadas
    ], seta-kdd,
    etapa-caixa(et.aval, "Avaliação")[
      #text(..titulo-fonte, size: 34pt)[2022–24] \ #v(-12pt) teste nunca visto no treino
      #v(2pt) 7 modelos comparados
    ],
  )
  #v(10pt)
  #text(fill: cor.suave)[Em cada etapa: o que encontramos, o que decidimos e quanto afetou.]
]

// Hipóteses: o veredito resume a conclusão de cada slide de interpretação.
#let veredito(c, t) = box(fill: c, inset: (x: 8pt, y: 4pt), radius: 2pt,
  text(..rotulo-fonte, size: 13pt, fill: cor.sombra, tracking: 1pt, upper(t)))
#let linha-h(h, hipotese, pergunta, metodo, resposta, onde) = (
  text(..titulo-fonte, size: 34pt, fill: cor.amarelo, h), text(weight: 600, hipotese),
  text(fill: cor.suave, pergunta), text(size: 15pt, metodo), resposta, text(..rotulo-fonte, size: 14pt, fill: cor.suave, onde))
#slide(etapa: "Hipóteses", codigo: "H1–H5", sub: "as perguntas da análise", c: cor.cal,
  titulo: [Cinco hipóteses, uma pergunta da comissão em cada], tempo: TEC)[
  #set text(size: 18pt)
  #table(columns: (auto, 1.35fr, 1.1fr, 0.75fr, auto, auto), inset: (x: 9pt, y: 7pt), align: left + horizon,
    stroke: (x, y) => (bottom: 0.5pt + cor.borda), fill: (x, y) => if y == 0 { cor.sombra.transparentize(30%) } else { cor.painel },
    table.header(..([], [Hipótese], [Para o clube], [Método], [Resposta], [Slide]).map(c => text(..rotulo-fonte, size: 13pt, fill: cor.cal, upper(c)))),
    ..linha-h("H1", [O vermelho reduz os pontos do punido, com placar, mando e força controlados],
      [Quanto custa uma expulsão?], [estado + pareamento], veredito(cor.destaque, "sustentada"), [H1·H2]),
    ..linha-h("H2", [Expulsão mais cedo custa mais], [Quando ela pesa mais?],
      [estado + pareamento], veredito(cor.amarelo, "em parte"), [H1·H2]),
    ..linha-h("H3", [Quem está perdendo leva mais vermelhos (causalidade reversa)], [O placar precisa entrar no controle?],
      [taxa por exposição], veredito(cor.destaque, "sustentada"), [H3]),
    ..linha-h("H4", [O efeito difere entre mandante e visitante], [Fora de casa é pior?],
      [estado + pareamento], veredito(cor.suave, "sem conclusão"), [H4·gols]),
    ..linha-h("H5", [Vermelhos se concentram em posições e nos minutos finais], [Quem e quando orientar?],
      [taxa por exposição], veredito(cor.destaque, "sustentada"), [H5·a · H5·b]),
  )
  #v(4pt)
  #text(size: 14pt, fill: cor.suave)[H5: sustentada para o minuto; para a posição, em parte (zagueiro acima, goleiro abaixo do esperado).]
]

#slide(etapa: "Seleção", codigo: "S·1", sub: "a matéria-prima", c: et.selecao,
  titulo: [Quatro arquivos públicos, ligados pela partida], tempo: TEC)[
  #grid(columns: (1.15fr, 1fr), gutter: 22pt,
    [
      #set text(size: 17pt)
      #table(columns: (auto, auto, auto, 1fr), align: (left, right, right, left), inset: 9pt,
        stroke: (x, y) => (bottom: 0.5pt + cor.borda), fill: (x, y) => if y == 0 { cor.sombra.transparentize(30%) },
        table.header(..([Arquivo], [Linhas], [Colunas], [Uma linha é…]).map(c => text(..rotulo-fonte, size: 13pt, fill: et.selecao, upper(c)))),
        [`full`], [#n("partidas_total")], [#n("colunas_partidas")], [partida],
        [`estatisticas`], [#n("estatisticas_linhas")], [#n("colunas_estatisticas")], [time × partida],
        [`gols`], [#n("gols_linhas")], [#n("colunas_gols")], [gol, com minuto],
        [`cartoes`], [#n("cartoes_linhas")], [#n("colunas_cartoes")], [cartão, com minuto e posição],
      )
      #v(4pt)
      #text(size: 13pt, fill: cor.suave)[Fonte: Adão Duque, _Brasileirao_Dataset_ (GitHub/Kaggle), Série A 2003–2024.]
    ],
    [
      #grid(columns: (1fr, 1fr), gutter: 10pt,
        numero(n("amarelos"), [amarelos], c: cor.amarelo),
        numero(n("vermelhos"), [vermelhos], c: cor.vermelho),
        numero(n("temporadas_total"), [temporadas no arquivo]),
        numero(n("pct_vitoria_mandante") + "%", [vitórias do mandante]),
      )
      #v(8pt)
      #painel(titulo: "O alvo da análise", c: et.selecao)[
        Resultado final e *pontos* de cada time.
      ]
    ],
  )
]

#let linha-sel(o-que, decisao, por-que) = (text(weight: 600, o-que), decisao, text(fill: cor.suave, por-que))
#slide(etapa: "Seleção", codigo: "S·2", sub: "o que entra e o que fica de fora", c: et.selecao,
  titulo: [Nem tudo o que está na base deve entrar na análise], tempo: TEC)[
  #set text(size: 20pt)
  #table(columns: (1fr, 0.9fr, 1.4fr), inset: 14pt, align: left + horizon,
    stroke: (x, y) => (bottom: 0.5pt + cor.borda), fill: (x, y) => if y == 0 { cor.sombra.transparentize(30%) } else { cor.painel },
    table.header(..([Dado], [Decisão], [Por quê]).map(c => text(..rotulo-fonte, size: 13pt, fill: et.selecao, upper(c)))),
    ..linha-sel([Partidas de 2014 a 2024], verde[*entram* (#n("partidas_2014_2024"))], [Só a partir de 2014 há o minuto dos eventos.]),
    ..linha-sel([Partidas de 2003 a 2013], ama[*só calibram o Elo*], [Calibrar fora da janela de análise.]),
    ..linha-sel([Estatísticas (chutes, posse…)], verm[*ficam de fora*], [Vazias antes de 2015 e em 2024, e são do jogo inteiro: #ama[vazamento].]),
    ..linha-sel([Formação tática], ama[*só no H5*], [Referência de jogadores por posição.]),
    ..linha-sel([Técnico e arena], verm[*sem uso*], [Nenhuma hipótese depende deles.]),
  )
]

#let linha-pre(problema, exemplo, decisao, quanto) = (text(weight: 600, problema), text(fill: cor.suave, exemplo), decisao, text(..titulo-fonte, size: 24pt, fill: cor.amarelo, quanto))
#slide(etapa: "Pré-processamento", codigo: "P·1", sub: "inconsistências", c: et.pre,
  titulo: [Seis problemas que a base não avisa], tempo: TEC)[
  #set text(size: 19.5pt)
  #table(columns: (0.95fr, 1.15fr, 1.25fr, auto), inset: (x: 10pt, y: 10pt), align: left + horizon,
    stroke: (x, y) => (bottom: 0.5pt + cor.borda), fill: (x, y) => if y == 0 { cor.sombra.transparentize(30%) } else { cor.painel },
    table.header(..([Problema], [Exemplo], [O que fizemos], [Afetados]).map(c => text(..rotulo-fonte, size: 13pt, fill: et.pre, upper(c)))),
    ..linha-pre([Zero que era ausência], [chutes = passes = faltas = 0], [vira nulo], n("estatisticas_anuladas_total")),
    ..linha-pre([Mesmo estádio, vários nomes], [Baixada · Kyocera · Ligga Arena], [dicionário manual], [#n_ou("arenas_grafias_total") → #n_ou("arenas_estadios_total")]),
    ..linha-pre([Vencedor contradiz o placar], [partida 1114: "empate" com 0 × 1], [vale o placar], [1 jogo]),
    ..linha-pre([Grafia de posição], [`Zagueira`], [unificada em `Zagueiro`], [22]),
    ..linha-pre([Temporada ≠ ano], [2020 acabou em fev/2021], [data de corte], [380 jogos]),
    ..linha-pre([Rodada incompleta], [2016 tem 379 jogos], [mantida, com aviso], [1 jogo]),
  )
  #v(6pt)
  #text(fill: cor.suave)[Cada correção é uma regra no código: os arquivos brutos nunca são editados.]
]

#slide(etapa: "Pré-processamento", codigo: "P·2", sub: "valores ausentes", c: et.pre,
  titulo: [#n("posicao_nula_original") cartões chegaram sem posição], tempo: TEC)[
  #let seta = align(center + horizon, text(size: 26pt, fill: cor.suave)[→])
  #grid(columns: (1fr, auto, 1fr, auto, 1fr, auto, 1fr), gutter: 8pt,
    numero(n("posicao_nula_original"), [cartões sem posição]), seta,
    numero("−" + n("posicao_imputada"), [herdam a posição do atleta], c: cor.destaque), seta,
    numero("−" + n("posicao_manual"), [anotados pela escalação], c: cor.destaque), seta,
    numero(n("posicao_nula_final"), [restantes · #n("vermelhos_posicao_nula_final") vermelhos], c: cor.amarelo, destaque: true),
  )
  #v(12pt)
  #grid(columns: (1fr, 1fr), gutter: 22pt,
    [
      - *Regra:* a posição do atleta em #ama[≥ 80%] dos seus cartões.
      - *À mão:* 28 vermelhos conferidos #ama[na escalação].
    ],
    painel(titulo: "Por que não descartar?")[Enviesaria o H5 para 2019–2024.],
  )
]

// Linha do tempo da partida de exemplo, a partir das tabelas exportadas.
#let ex_fim = float(ex0.duracao)
#let ex_rotulados = ex.filter(l => l.tipo != "amarelo")
#let ex_eventos = ex.map(l => {
  let i = ex_rotulados.position(r => r == l)
  let rot = if l.tipo == "vermelho" { l.minuto + "' " + lower(l.posicao) + " " + sigla.at(l.clube) }
    else if l.tipo == "gol" { l.minuto + "' " + sigla.at(l.clube) } else { "" }
  (float(l.t), l.tipo, rot, i == none or calc.even(i))
})
#let ex_seg = ex_trechos.map(l => (float(l.inicio), float(l.fim), l.gols_mandante + "×" + l.gols_visitante,
  if l.jogadores_mandante == "11" and l.jogadores_visitante == "11" { cor.cal } else { cor.vermelho }))
#let ex_2t = ex.find(l => not l.minuto.contains("+") and int(l.minuto) > 45)
#let ex_inicio_2t = float(ex_2t.t) - (int(ex_2t.minuto) - 45)
#let ex_t3 = ex_trechos.at(3)

#slide(etapa: "Transformação", codigo: "T·1", sub: "do registro à linha do tempo", c: et.trans,
  titulo: [Cada partida vira uma sequência de situações de jogo], tempo: TEC)[
  #text(fill: cor.suave)[#ex_mand #ex0.placar_mandante × #ex0.placar_visitante #ex_vis (#ex0.data), evento a evento.]
  #linha-do-tempo(37cm, ex_fim, ex_eventos, ex_seg,
    ((0, "0'"), (ex_inicio_2t - 4, "45'"), (ex_inicio_2t, "2º tempo"), (ex_fim - 3, "fim est.")))
  #text(size: 13pt, fill: cor.suave)[Branco: 11 × 11. #verm[Vermelho]: #ex_punido com 10.]
  #v(8pt)
  #grid(columns: (1fr, 1fr, 1fr), gutter: 12pt,
    painel(titulo: "Trecho", c: cor.destaque)[Placar e jogadores constantes: #nf("trechos") no total.],
    painel(titulo: "Exposição")[Minutos #ama[perdendo, empatando ou vencendo]: o denominador das taxas.],
    painel(titulo: "Acréscimo não registrado", c: cor.vermelho)[Duração *estimada*: o gol dos #ex.last().minuto' fecha a partida.],
  )
]

#slide(etapa: "Transformação", codigo: "T·2", sub: "variáveis criadas", c: et.trans,
  titulo: [Quatro informações que a base não tinha], tempo: TEC)[
  #grid(columns: (1fr, 1fr), gutter: 14pt,
    painel(titulo: "Tipo de vermelho", c: cor.destaque)[
      Amarelo antes, no mesmo jogo → 2º amarelo.
      #v(2pt)
      #text(..titulo-fonte, size: 30pt, fill: cor.vermelho)[#nf("vermelhos_direto") diretos] #h(10pt)
      #text(..titulo-fonte, size: 30pt, fill: cor.amarelo)[#nf("vermelhos_2o_amarelo") por 2º amarelo] #h(10pt)
      #text(size: 13pt, fill: cor.suave)[#nf("vermelhos_indeterminado") sem atleta]
    ],
    painel(titulo: "Minuto com acréscimo", c: cor.destaque)[
      `45+3` → tempo, minuto e acréscimo, ordenado antes de `46`.
    ],
    painel(titulo: "Fotografias do jogo (landmarks)", c: cor.destaque)[
      Placar e vermelhos a cada 5 minutos.
      #v(2pt)
      #text(..titulo-fonte, size: 30pt)[#nf("landmarks_linhas") linhas] #text(size: 13pt, fill: cor.suave)[· 18 por partida]
    ],
    painel(titulo: "Força dos times (Elo)", c: cor.destaque)[
      Só com jogos *anteriores*, calibrado em 2004–2013.
    ],
  )
]

#slide(etapa: "Pré-processamento", codigo: "P·3", sub: "validação", c: et.pre,
  titulo: [Oito checagens rodam a cada execução, e param tudo se falharem], tempo: TEC)[
  #grid(columns: (1.25fr, 1fr), gutter: 22pt,
    block(fill: cor.sombra.transparentize(15%), stroke: (left: 3pt + cor.destaque), inset: 16pt, width: 100%, {
      set text(font: "Fira Mono", size: 16.5pt)
      set par(leading: 0.9em)
      let ok(t) = [#t #h(1fr) #text(fill: cor.destaque)[✓] \ ]
      ok[gols por lado == placar final]
      ok[placar refeito evento a evento == placar final]
      ok[todo evento tem partida_id existente]
      ok[estatísticas: 2 linhas por partida]
      ok[jogadores em campo entre 7 e 11]
      ok[nenhum atleta com 2 vermelhos no jogo]
      ok[exposição de cada time == duração do jogo]
      ok[Elo: mudar um resultado não muda o passado]
    }),
    [
      #painel(titulo: "Por que importa", c: cor.amarelo)[
        Um gol no minuto errado muda o placar no momento do vermelho.
      ]
      #v(8pt)
      #painel(titulo: "Resultado", c: cor.destaque)[
        Gols = placar em #verde[*100%*] das partidas.
      ]
    ],
  )
]

#slide(etapa: "Mineração", codigo: "M·1", sub: "métodos", c: et.mine,
  titulo: [Três formas de medir o mesmo efeito], tempo: TEC)[
  #grid(columns: (1fr, 1fr, 1fr), gutter: 12pt,
    painel(titulo: "1 · Taxa por exposição", c: cor.amarelo)[
      Poisson por minuto exposto → *razão de taxas*.
      #v(2pt) #text(fill: cor.suave)[H3, H5, gols]
    ],
    painel(titulo: "2 · Modelo de estado", c: cor.amarelo)[
      *Multinomial* V/E/D em cada fotografia → *pontos esperados*.
      #v(2pt) #text(fill: cor.suave)[H1, H2, H4]
    ],
    painel(titulo: "3 · Pareamento", c: cor.amarelo)[
      *#h1_equilibrio.tratados* expulsos × até 5 pares no mesmo minuto, mando e saldo.
      #v(2pt) #text(fill: cor.suave)[H1, H2, H4]
    ],
  )
  #v(12pt)
  #painel(titulo: "Decisões no caminho", c: cor.vermelho)[
    - Ordinal → *multinomial* (AIC #fmt(estado_ajuste("ordinal").delta_aic, d: 0) pontos melhor).
    - Nenhum corte usa o futuro: só o *1º vermelho até os 90'*.
  ]
]

// Linha do tempo de treino e teste.
#let barra-temporal = {
  let anos = range(2014, 2025)
  grid(columns: anos.len(), gutter: 3pt,
    ..anos.map(a => box(width: 100%, fill: if a <= 2021 { cor.cal.transparentize(70%) } else { et.aval }, inset: (y: 8pt),
      align(center, text(..rotulo-fonte, size: 13pt, fill: if a <= 2021 { cor.texto } else { cor.sombra }, str(a))))))
}
#let lm(nome, destaque: false) = {
  let m = metrica(nome)
  let c = if destaque { cor.amarelo } else { cor.texto }
  (text(fill: c, weight: if destaque { 600 } else { 400 }, nome), ..(m.log_loss, m.rps, m.auc_ovr, m.acuracia).map(v => text(fill: c, fmt_ou(v))))
}
#slide(etapa: "Avaliação", codigo: "A·1", sub: "validação e métricas", c: et.aval,
  titulo: [Treinar no passado, testar no futuro], tempo: TEC)[
  #barra-temporal
  #v(-4pt)
  #text(size: 13pt, fill: cor.suave)[Treino #milhar(n_landmarks - n_teste) · teste #milhar(n_teste) fotografias]
  #v(8pt)
  #grid(columns: (1.2fr, 1fr), gutter: 22pt,
    [
      #set text(size: 17pt)
      #table(columns: (1fr, auto, auto, auto, auto), inset: (x: 9pt, y: 8pt), align: (left, right, right, right, right),
        stroke: (x, y) => (bottom: 0.5pt + cor.borda), fill: (x, y) => if y == 0 { cor.sombra.transparentize(30%) } else { cor.painel },
        table.header(..([Modelo (teste)], [Log-loss], [RPS], [AUC], [Acurácia]).map(c => text(..rotulo-fonte, size: 12.5pt, fill: et.aval, upper(c)))),
        ..lm("sempre mandante"), ..lm("frequências históricas"), ..lm("Elo pré-jogo"), ..lm("logística ordinal"),
        ..lm("logística multinomial", destaque: true), ..lm("random forest"), ..lm("LightGBM"),
      )
    ],
    [
      - *Log-loss e RPS*: avaliam a probabilidade.
      - CV *agrupada por partida*.
      #v(2pt)
      #painel(titulo: "Escolha", c: cor.amarelo)[*Multinomial*: empata com a random forest e é interpretável.]
    ],
  )
]

#let irr-linha(rotulo, l, c) = (rotulo, float(l.irr), float(l.ic95_inf), float(l.ic95_sup), c)
#slide(etapa: "Interpretação", codigo: "H3", sub: "placar no momento do vermelho", c: et.interp,
  titulo: [Quem está perdendo leva #pct_acima(p_aj.irr) mais vermelhos, no mesmo minuto], tempo: TEC)[
  #grid(columns: (1.35fr, 1fr), gutter: 22pt,
    [
      #intervalos((
        irr-linha([Perdendo · sem ajuste], p_sa, cor.suave),
        irr-linha([*Perdendo · ajustado*], p_aj, cor.vermelho),
        irr-linha([Perdendo · só vermelho direto], irr("ajustado — direto", "estado[perdendo]"), cor.vermelho),
        irr-linha([Perdendo · só 2º amarelo], irr("ajustado — 2º amarelo", "estado[perdendo]"), cor.vermelho),
        irr-linha([Perdendo · sem os 90+], irr("robustez — sem 90+", "estado[perdendo]"), cor.vermelho),
        irr-linha([Vencendo · sem ajuste], v_sa, cor.suave),
        irr-linha([*Vencendo · ajustado*], v_aj, cor.destaque),
      ), largura: 21cm, rotulo-larg: 9.5cm, xmin: 0.5, xmax: 4, ticks: (0.5, 1, 2, 4), passo: 1.25cm)
      #text(size: 13pt, fill: cor.suave)[Razão de taxas contra *empatando*, IC 95%.]
    ],
    [
      - Sem ajuste: ×#fmt(p_sa.irr). Boa parte era *o minuto*.
      - Ajustado: #ama[+#pct_acima(p_aj.irr)], em todas as versões.
      #painel(titulo: "Consequência")[O placar *precisa* entrar como controle no custo do vermelho.]
    ],
  )
]

#let faixas = ("0–15", "16–30", "31–45+", "46–60", "61–75", "76–90+")
#slide(etapa: "Interpretação", codigo: "H5·a", sub: "quando acontece", c: et.interp,
  titulo: [O risco de expulsão cresce a cada 15 minutos], tempo: TEC)[
  #grid(columns: (1.4fr, 1fr), gutter: 22pt,
    [
      #barras(faixas.map(f => {
        let l = taxa_faixa(f)
        (rotulo: f, valor: float(l.taxa_90), inf: float(l.ic95_inf), sup: float(l.ic95_sup),
          cor: if f == "76–90+" { cor.vermelho } else { cor.amarelo })
      }), largura: 21cm, altura: 9.5cm, ymin: 0, ymax: 0.4, ticks: (0, 0.1, 0.2, 0.3, 0.4), fmt-y: v => fmt(v, d: 1),
        fmt-valor: v => fmt(v, d: 2))
      #text(size: 13pt, fill: cor.suave)[Vermelhos por time a cada 90 minutos, IC 95%.]
    ],
    [
      #numero(fmt(razao_fim, d: 0) + "×", [76–90+ contra 0–15], c: cor.vermelho, tamanho: 64pt)
      #v(8pt)
      - Vale para direto, 2º amarelo e todas as posições.
    ],
  )
]

#slide(etapa: "Interpretação", codigo: "H5·b", sub: "quem é expulso", c: et.interp,
  titulo: [Zagueiro leva #pct_acima(z.razao_obs_esp) mais vermelhos do que o esperado], tempo: TEC)[
  #let zona(fx, fy, rotulo, pos) = {
    let l = formacao(pos)
    (fx, fy, rotulo, float(l.razao_obs_esp), float(l.ic95_inf), float(l.ic95_sup))
  }
  #grid(columns: (1.35fr, 1fr), gutter: 22pt,
    [
      #campo(21cm, 11.6cm, (
        zona(0.09, 0.5, "goleiro", "Goleiro"), zona(0.3, 0.25, "zagueiro", "Zagueiro"),
        zona(0.55, 0.72, "meio-campo", "Meio-campo"), zona(0.8, 0.3, "atacante", "Atacante"),
      ))
      #v(2pt)
      #text(size: 13pt, fill: cor.suave)[Observados ÷ esperados. #verm[Vermelho]: acima · #verde[verde]: abaixo · branco: inconclusivo (IC 95%).]
    ],
    [
      - *Esperado:* jogadores da posição na formação.
      - Zagueiros: #ama[#z.observados vermelhos contra #fmt(z.esperados, d: 0)].
      - O goleiro do #ex_punido é o caso raro.
      #painel(titulo: "Para a comissão técnica")[A orientação disciplinar começa pela *linha defensiva*.]
    ],
  )
]

#let att-faixas = ("faixa 0–15", "faixa 16–30", "faixa 31–45+", "faixa 46–60", "faixa 61–75", "faixa 76–90")
#slide(etapa: "Interpretação", codigo: "H1·H2", sub: "o custo da expulsão", c: et.interp,
  titulo: [Um vermelho custa #fmt(custo_ponto) ponto, e custa mais cedo], tempo: TEC)[
  #grid(columns: (1.4fr, 1fr), gutter: 22pt,
    [
      #barras(att-faixas.filter(f => att(f) != none).map(f => {
        let l = att(f)
        (rotulo: f.replace("faixa ", ""), valor: float(l.att), inf: float(l.ic95_inf), sup: float(l.ic95_sup),
          cor: if float(l.ic95_sup) < 0 { cor.vermelho } else { cor.suave })
      }), largura: 21cm, altura: 9.5cm, ymin: -1.25, ymax: 0.6, ticks: (-1, -0.5, 0, 0.5), fmt-y: v => fmt(v, d: 1))
      #text(size: 13pt, fill: cor.suave)[Pontos do expulso − pontos dos pares (ATT), pelo minuto do vermelho. Cinza: inclui zero.]
    ],
    [
      #numero("−" + fmt(custo_ponto), [ponto · IC #fmt(att_todos.ic95_inf) a #fmt(att_todos.ic95_sup)], c: cor.vermelho, tamanho: 64pt)
      #v(8pt)
      - *H1:* sustentada nos três métodos.
      - *H2:* em parte, a queda não é significativa no modelo de estado.
    ],
  )
]

#let serie-custo(lado) = range(0, 90, step: 5).map(m => {
  let l = custo(m, 0, lado)
  (m, float(l.delta_pe), float(l.ic95_inf), float(l.ic95_sup))
})
#let h1m = h1_teste("H1 ΔPE de um vermelho no minuto 45, empatando (média dos lados) [multinomial]")
#slide(etapa: "Interpretação", codigo: "H1·b", sub: "custo minuto a minuto", c: et.interp,
  titulo: [O modelo de estado confirma o tamanho do custo], tempo: TEC)[
  #grid(columns: (1.4fr, 1fr), gutter: 22pt,
    [
      #legenda((cor.amarelo, "mandante expulso"), (cor.vermelho, "visitante expulso"))
      #curvas((("mandante", cor.amarelo, serie-custo("mandante")), ("visitante", cor.vermelho, serie-custo("visitante"))),
        largura: 21cm, altura: 9cm, xmin: 0, xmax: 85, ymin: -1.6, ymax: 0.4,
        xticks: (0, 15, 30, 45, 60, 75, 85), yticks: (-1.5, -1, -0.5, 0))
      #text(size: 13pt, fill: cor.suave)[Pontos esperados perdidos, jogo empatado (IC 95%).]
    ],
    [
      #numero(fmt(float(h1m.valor_efeito)), [vermelho no intervalo, empatado], c: cor.vermelho, tamanho: 64pt)
      #v(8pt)
      - Curva *instável* no início: a decisão usa o *pareamento*.
    ],
  )
]

#let h4d = h1_teste("H4 pareamento: ATT mandante − ATT visitante")
#slide(etapa: "Interpretação", codigo: "H4·gols", sub: "com um a menos", c: et.interp,
  titulo: [Com um a menos, o problema é defender], tempo: TEC)[
  #grid(columns: (1fr, 1fr, 1.2fr), gutter: 14pt,
    numero(pct_var(gs.irr), [gols sofridos · IC #fmt(gs.ic95_inf) a #fmt(gs.ic95_sup)×], c: cor.vermelho, tamanho: 72pt),
    numero(pct_var(gi.irr), [gols marcados · IC #fmt(gi.ic95_inf) a #fmt(gi.ic95_sup)×], c: cor.amarelo, tamanho: 72pt),
    painel(titulo: "Leitura tática", c: cor.destaque)[#text(size: 26pt)[Perde-se mais pelo que se *sofre*: fechar a defesa.]],
  )
  #v(14pt)
  #painel(titulo: "H4 · mandante × visitante: sem conclusão firme", c: cor.cal)[
    Mandante #fmt(att("lado mandante").att) × visitante #fmt(att("lado visitante").att), mas parte é *efeito teto*, e o modelo de estado não confirma.
  ]
]

#slide(etapa: "Interpretação", codigo: "L·1", sub: "limitações", c: et.interp,
  titulo: [O que estes dados não permitem afirmar], tempo: TEC)[
  #set text(size: 23pt)
  #grid(columns: (1fr, 1fr), gutter: 14pt,
    painel(titulo: "Associação, não causa", c: cor.vermelho)[Dados observacionais: controles reduzem o viés, não o eliminam.],
    painel(titulo: "Acréscimo estimado", c: cor.vermelho)[Duração é limite inferior: #nf("vermelhos_t_restante_zero") vermelhos com tempo restante zero.],
    painel(titulo: "Posição sem escalação", c: cor.amarelo)[Sem volante; meio × ataque depende dos pontas.],
    painel(titulo: "Poucos vermelhos cedo", c: cor.amarelo)[Só #att("faixa 0–15").n_tratados nos 15 primeiros minutos.],
  )
]

// Insights no formato do enunciado: uma linha por parte da frase.
#let rot-ins(t) = text(..rotulo-fonte, size: 14pt, fill: cor.amarelo, tracking: 1.2pt, upper(t))
#let insight(codigo, sub, titulo, linhas, nota) = slide(etapa: "Decisão", codigo: codigo, sub: sub, c: cor.amarelo,
  titulo: titulo, tempo: TEC)[
  #set text(size: 18pt)
  #table(columns: (auto, 1fr), inset: (x: 12pt, y: 8pt), align: left + horizon,
    stroke: (x, y) => (bottom: 0.5pt + cor.borda), fill: cor.painel,
    ..linhas.map(((r, t)) => (rot-ins(r), t)).flatten(),
  )
  #v(2pt)
  #text(size: 13pt, fill: cor.suave, nota)
]
#let acaso(m) = [Um time médio da liga cumpre esta meta por acaso em #pct(m.chance_acaso, d: 0)% dos períodos: a meta é exigente, mas um único período não basta para provar efeito.]

#let a75 = att("até 75'")
#let d75 = att("depois de 75'")
#let m1 = ins_meta("I1")
#insight("D·1", "insight 1 · o relógio", [Prevenir até os 75', quando a expulsão custa caro], (
  ("Percebemos que", [uma expulsão até os 75' custa *#fmt(-float(a75.att)) ponto*, #fmt(float(a75.att) / float(d75.att), d: 1)× a de depois dos 75', e #pct(float(att("tipo 2o_amarelo").n_tratados) / float(att_todos.n_tratados), d: 0)% dos vermelhos vêm do *2º amarelo*]),
  ("Isso sugere que", [o atleta *já advertido* é o risco evitável, e o relógio diz quanto ele vale]),
  ("Recomendamos", [*zona de risco* até os 75': advertido em lance de risco é candidato prioritário à substituição]),
  ("Sustentado por", [ATT pareado: até 75' #val_ic(a75, "att") · depois #val_ic(d75, "att")]),
  ("Após 1 temporada", [avaliar por *vermelhos por 2º amarelo até os 75'* (liga: #fmt(m1.liga_media, d: 1)) · acompanhar por *pontos perdidos estimados* (liga: #fmt(liga("pontos_perdidos_estimados").media, d: 1))]),
  ("Sucesso se", if float(m1.meta) == 0 [*nenhuma* expulsão por 2º amarelo até os 75' (quartil inferior da liga)] else [no máximo *#fmt(m1.meta, d: 0)* (quartil inferior da liga)]),
), acaso(m1))

#let cz = conversao("zagueiro · 1º tempo")
#let cd = conversao("demais · 1º tempo")
#let tz = ins_teste("I2 conversão: zagueiro 1º tempo × demais 1º tempo")
#let tz2 = ins_teste("I2 conversão: zagueiro 2º tempo × demais 2º tempo")
#let m2 = ins_meta("I2")
#insight("D·2", "insight 2 · a posição", [O zagueiro advertido no 1º tempo é o caso de maior risco], (
  ("Percebemos que", [zagueiro advertido no 1º tempo é expulso em *#pct(cz.taxa)%* dos casos, contra #pct(cd.taxa)% nas demais posições; no 2º tempo não há diferença. Zagueiros levam #pct_acima(z.razao_obs_esp) mais vermelhos do que a formação explica]),
  ("Isso sugere que", [o risco é o zagueiro com amarelo *e o 2º tempo inteiro* pela frente]),
  ("Recomendamos", [no *intervalo*, avaliar substituição ou mudança de função do zagueiro advertido; treino de bote e cobertura com a linha defensiva]),
  ("Sustentado por", [teste z de proporções: razão #fmt(tz.valor_efeito) (p de Holm #pfmt(tz.p_holm)#[;] no 2º tempo, p #pfmt(tz2.p_holm)) · H5: #fmt(z.razao_obs_esp)× o esperado]),
  ("Após 1 temporada", [avaliar por *vermelhos de zagueiros* (liga: mediana #fmt(m2.liga_mediana, d: 0)) · acompanhar por *expulsões de zagueiros advertidos no 1º tempo* (liga: #pct(cz.taxa)% de ≈ #fmt(liga("zagueiros_advertidos_1t").media, d: 0) casos)]),
  ("Sucesso se", [no máximo *#fmt(m2.meta, d: 0)* vermelho de zagueiro na temporada (quartil inferior da liga)]),
), acaso(m2))

#let m3 = ins_meta("I3")
#insight("D·3", "insight 3 · com um a menos", [Com 10, o plano é não sofrer], (
  ("Percebemos que", [com um a menos, o time *sofre #pct_var(gs.irr)* gols e *marca #pct_var(gi.irr)*]),
  ("Isso sugere que", [os pontos se perdem atrás: com 10, a prioridade é *não sofrer*]),
  ("Recomendamos", [*plano pré-treinado* para jogar com 10: preservar a linha defensiva, abrir mão de um atacante, acionar logo após a expulsão]),
  ("Sustentado por", [Poisson por minuto exposto: sofridos #com_ic(gs) · marcados #com_ic(gi)]),
  ("Após 2 temporadas", [avaliar por *gols sofridos por 90' com um a menos* (liga: #fmt(m3.liga_media) com 10, #fmt(m3.taxa_com_11) com 11) · acompanhar por *gols marcados com um a menos*]),
  ("Sucesso se", [no máximo *#fmt(m3.meta)* gol sofrido por 90' com 10: metade do caminho até a taxa com 11]),
), [Duas temporadas porque um time passa só ≈ #fmt(liga("minutos_com_menos").mediana, d: 0) minutos por ano com um a menos. #acaso(m3)])

// ===================================================================== PÓS-JOGO

#slide(etapa: "Referências", codigo: "R", sub: "tudo é reproduzível", c: cor.cal,
  titulo: [Fontes e código], tempo: FIM)[
  #set text(size: 17pt)
  #table(columns: (auto, 1fr), inset: 10pt, align: left + horizon,
    stroke: (x, y) => (bottom: 0.5pt + cor.borda), fill: cor.painel,
    text(..rotulo-fonte, fill: cor.amarelo)[DADOS], [Duque, A. _Campeonato Brasileiro de Futebol_ (Brasileirao_Dataset). GitHub/Kaggle. `github.com/adaoduque/Brasileirao_Dataset`],
    text(..rotulo-fonte, fill: cor.amarelo)[LITERATURA], [Caliendo, M.; Radic, D. _Ten Do It Better, Do They? An Empirical Analysis of an Old Football Myth_. IZA DP 2158, 2006.],
    text(..rotulo-fonte, fill: cor.amarelo)[CÓDIGO], [`python -m src.run_all` · todos os números lidos de `reports/tabelas/`],
  )
  #v(1fr)
  #align(center)[
    #cartao(cor.amarelo, h: 34pt) #h(8pt) #cartao(cor.vermelho, h: 34pt)
    #v(4pt)
    #text(..titulo-fonte, size: 44pt)[Obrigado!] \
    #v(-8pt)
    #text(fill: cor.suave)[José Felix · Rafael Anacleto]
  ]
  #v(1fr)
]
