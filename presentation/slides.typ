// Apresentação: pitch (5 min) + parte técnica (15 min)
// Compilar a partir da raiz: typst compile --root . presentation/slides.typ
#import "dados.typ": *

#set document(title: "Quanto custa uma expulsão?", author: "José Felix")
#set page(width: 33.87cm, height: 19.05cm, margin: (x: 1.8cm, y: 1.5cm), numbering: "1",
  number-align: right)
#set text(lang: "pt", size: 22pt)
#set par(justify: false)
#set list(spacing: 0.75em)
#show heading.where(level: 1): it => { pagebreak(weak: true); text(size: 32pt, it); v(0.4em) }

#let destaque(corpo) = block(fill: rgb("#eef4fc"), inset: 14pt, radius: 6pt, width: 100%, corpo)
#let pendente(corpo) = block(stroke: (paint: rgb("#c3c2b7"), dash: "dashed"), inset: 14pt,
  radius: 6pt, width: 100%, text(fill: rgb("#52514e"))[*Pendente:* #corpo])
#let numero(valor, legenda, tamanho: 44pt) = align(center)[
  #text(size: tamanho, weight: "bold", fill: rgb("#2a78d6"))[#valor] \
  #text(size: 17pt, fill: rgb("#52514e"))[#legenda]
]
#let fonte(arquivo) = place(bottom + left, dy: 0.6cm, text(size: 13pt, fill: rgb("#52514e"))[Fonte: #raw(arquivo)])

#let p_aj = irr("ajustado", "estado[perdendo]")
#let p_sa = irr("sem ajuste", "estado[perdendo]")
#let z = formacao("Zagueiro")
#let razao_fim = float(taxa_faixa("76–90+").taxa_90) / float(taxa_faixa("0–15").taxa_90)
#let att_todos = att("todos")
#let gs = gols_irr("todos", "vantagem[superior]")
#let gi = gols_irr("todos", "vantagem[inferior]")
// Vermelhos por time por temporada: 11 temporadas (2014–2024) × 20 times.
#let verm_temporada = float(chave(resumo, "vermelhos")) / (11 * 20)

#align(center + horizon)[
  #text(size: 38pt, weight: "bold")[Quanto custa uma expulsão?]
  #v(0.5em)
  Efeito do cartão vermelho no Brasileirão Série A (2014–2024)
  #v(1em)
  José Felix · Ciência de Dados · UFAL/IC · 2026.1
]

// ---------------------------------------------------------------- Pitch (5 min)

= Pitch: problema

#grid(columns: (1fr, 1fr, 1fr), gutter: 1cm,
  numero(n("vermelhos"), [vermelhos em 2014–2024]),
  numero(n("pct_partidas_com_vermelho") + "%", [das partidas têm expulsão]),
  numero(fmt(verm_temporada, d: 1), [vermelhos por time, por temporada]),
)
#v(1cm)
- Uma expulsão muda o jogo, mas a comissão técnica não sabe *quanto custa*, *quando acontece* nem *como reagir*.
- Hoje, a conduta disciplinar e tática após um vermelho é decidida no improviso.

= Pitch: oportunidade

- Os vermelhos *não são aleatórios*: seguem padrões de minuto, placar e posição.
- Padrões previsíveis permitem *prevenir*: orientar atletas e fazer substituições antes da zona de risco.
- O custo em pontos permite *reagir*: um plano tático pronto para jogar com 10 ou contra 10.

#v(0.6cm)
#destaque[Cliente: comissão técnica e análise de desempenho de um clube da Série A.]

= Pitch: evidências

#grid(columns: (1fr, 1fr, 1fr, 1fr), gutter: 0.8cm,
  numero(fmt(att_todos.att), [ponto por expulsão, contra times na mesma situação], tamanho: 40pt),
  numero(pct_var(gs.irr), [gols do adversário quando se joga com um a menos], tamanho: 40pt),
  numero(pct_var(p_aj.irr), [risco de vermelho quando o time está *perdendo*], tamanho: 40pt),
  numero(fmt(razao_fim, d: 0) + "×", [taxa de vermelhos nos minutos 76–90+ contra 0–15], tamanho: 40pt),
)
#v(0.8cm)
Todos com IC 95% bootstrap e p-valor corrigido por Holm (detalhes na parte técnica).

= Pitch: decisão e impacto

- *Prevenir — zona de risco disciplinar:* time perdendo por 1 gol, no 2º tempo, com atenção a zagueiros já advertidos. Ação: orientação e substituição preventiva do atleta advertido.
- *Reagir — plano para jogar com 10:* a expulsão pesa mais pelos gols sofridos (#pct_var(gs.irr)) do que pelos marcados (#pct_var(gi.irr)). A prioridade é fechar a defesa.
- *Impacto:* cada expulsão evitada vale cerca de #fmt(calc.abs(float(att_todos.att))) ponto. Um time leva em média #fmt(verm_temporada, d: 1) vermelhos por temporada, o que soma cerca de #fmt(calc.abs(float(att_todos.att)) * verm_temporada, d: 1) pontos perdidos por ano.

#v(0.3cm)
#destaque[*KPIs:* vermelhos por 38 jogos (principal) e pontos obtidos em jogos com expulsão (auxiliar).]

// ---------------------------------------------------------------- Técnica (15 min)

= Técnica: base de dados

#grid(columns: (1.1fr, 1fr), gutter: 1.2cm,
  table(
    columns: (auto, auto, auto),
    align: (left, right, left),
    inset: 8pt,
    table.header[*Arquivo*][*Linhas*][*Grão*],
    [`full`], [#n("partidas_total")], [partida],
    [`estatisticas`], [#n("estatisticas_linhas")], [time × partida],
    [`gols`], [#n("gols_linhas")], [gol],
    [`cartoes`], [#n("cartoes_linhas")], [cartão],
  ),
  [
    - Adão Duque, Brasileirao_Dataset (GitHub/Kaggle).
    - Minuto de gols e cartões: *2014–2024*, #n("partidas_2014_2024") partidas.
    - #n("amarelos") amarelos e #n("vermelhos") vermelhos.
    - Gols por lado batem com o placar em 100% das partidas.
  ],
)
#fonte("reports/tabelas/resumo_base.csv")

= Técnica: preparação

- *Acréscimos* (`45+3`): tempo, minuto e acréscimo separados, com ordenação correta.
- *Temporada ≠ ano*: a temporada 2020 terminou em 2021, e cada temporada fica com 380 jogos.
- *Zeros = ausentes* nas estatísticas: #n("estatisticas_anuladas_total") linhas viraram nulas.
- *Posição*: #n("posicao_imputada") imputadas pelo atleta, e os 28 vermelhos restantes anotados à mão pela escalação.
- *Tipo de vermelho* inferido: #nf("vermelhos_direto") diretos e #nf("vermelhos_2o_amarelo") por 2º amarelo.
- *Linha do tempo*: placar e jogadores a cada evento, #nf("trechos") trechos de estado constante e landmarks de 5 em 5 minutos.

= Técnica: métodos

- *Exposição:* minutos em cada placar e faixa de 15 min. Poisson com offset → razão de taxas (IRR) de vermelhos (H3, H5) e de gols.
- *Modelo de estado do jogo:* logística *multinomial* do resultado final em landmarks de 5 min. Custo = ΔPE do time punido. A ordinal foi rejeitada (ΔAIC = #fmt(estado_ajuste("ordinal").delta_aic, d: 0)).
- *Pareamento:* expulso × 5 controles no mesmo minuto, mando e saldo, sem vermelho até ali e com Elo próximo → ATT em pontos.
- *Força relativa:* Elo sem vazamento, calibrado em 2004–2013.
- *Comparação:* frequências, Elo, ordinal, multinomial, random forest e LightGBM (+ SHAP).
- *Incerteza:* bootstrap ou covariância robusta por partida, com correção de Holm.

= Técnica: métricas e avaliação

#let lm(nome) = { let m = metrica(nome); (nome, fmt_ou(m.log_loss), fmt_ou(m.rps), fmt_ou(m.auc_ovr), fmt_ou(m.acuracia)) }
#grid(columns: (1.25fr, 1fr), gutter: 1cm,
  text(size: 18pt, table(
    columns: (auto, auto, auto, auto, auto),
    align: (left, right, right, right, right),
    inset: 7pt,
    table.header[*Modelo (teste 2022–24)*][*Log-loss*][*RPS*][*AUC*][*Acur.*],
    ..("sempre mandante", "frequências históricas", "Elo pré-jogo", "logística ordinal",
       "logística multinomial", "random forest", "LightGBM").map(lm).flatten(),
  )),
  [
    - *Validação temporal:* treino 2014–2021, teste 2022–2024.
    - Hiperparâmetros por k-fold *agrupado por partida*.
    - Log-loss e RPS como métricas principais (acurácia engana com empates).
    - A multinomial empata com a random forest e é interpretável → modelo de decisão.
  ],
)
#fonte("reports/tabelas/modelos_metricas.csv")

= Técnica: resultados (H3)

#grid(columns: (1.35fr, 1fr), gutter: 1cm,
  image("/reports/figures/h3_irr.png", width: 100%),
  [
    - Sem ajuste: perdendo × empatando = #fmt(p_sa.irr).
    - *Ajustado:* #com_ic(p_aj).
    - O minuto confundia: o excesso de risco cai de #pct_var(p_sa.irr) para #pct_var(p_aj.irr) com o ajuste.
    - O risco se concentra em *perder por 1 gol*.
  ],
)
#fonte("reports/tabelas/h3_irr.csv")

= Técnica: resultados (H5)

#grid(columns: (1fr, 1fr), gutter: 0.8cm,
  image("/reports/figures/h5_taxa_faixa.png", width: 100%),
  image("/reports/figures/h5_posicao.png", width: 100%),
)
#text(size: 18pt)[
  - A taxa cresce a cada faixa de minuto. Zagueiros ficam acima e goleiros abaixo do esperado.
  - Zagueiro punido é expulso em #pct(cartao("Zagueiro").proporcao)%, contra #pct(cartao("Meio-campo").proporcao)% no meio-campo. Posição e minuto não interagem (p #pfmt(h5_teste("H5 independência: posição × faixa").p_holm)).
]
#fonte("reports/tabelas/h5_taxas_faixa.csv, h5_posicao_formacao.csv, h5_posicao_cartao.csv")

= Técnica: resultados (H1, H2)

#let h1m = h1_teste("H1 ΔPE de um vermelho no minuto 45, empatando (média dos lados) [multinomial]")
#grid(columns: (1fr, 1fr), gutter: 0.8cm,
  image("/reports/figures/h1_custo_minuto.png", width: 100%),
  image("/reports/figures/h1_pareamento.png", width: 100%),
)
#text(size: 18pt)[
  - *H1:* pareamento, ATT = #val_ic(att_todos, "att") ponto. Modelo de estado, minuto 45 empatando = #val_ic(h1m, "valor_efeito").
  - *H2 em parte:* no pareamento, o custo cai de #fmt(att("faixa 16–30").att) (16–30) para #fmt(att("faixa 76–90").att) (76–90). No modelo, a diferença 15 × 75 empatando não é significativa.
]
#fonte("reports/tabelas/h1_pareamento_att.csv, h1_custo_minuto.csv, h1_testes.csv")

= Técnica: resultados (H4 e gols)

#let h4d = h1_teste("H4 pareamento: ATT mandante − ATT visitante")
#grid(columns: (1.1fr, 1fr), gutter: 1cm,
  image("/reports/figures/h1_gols.png", width: 100%),
  [
    - *Com um a menos:* marca #pct_var(gi.irr) e sofre #pct_var(gs.irr) gols por minuto.
    - *H4 sem conclusão firme:* o mandante perde #fmt(att("lado mandante").att) e o visitante #fmt(att("lado visitante").att) (p de Holm #pfmt(h4d.p_holm)), mas parte disso é efeito teto, e o modelo de estado não confirma a diferença.
  ],
)
#fonte("reports/tabelas/h1_gols_irr.csv, h1_testes.csv")

= Técnica: limitações

- *Dados observacionais:* o efeito estimado é associativo. Pareamento e controle do estado de jogo mitigam o problema, mas não garantem causalidade.
- *Curva de custo instável:* poucos vermelhos para identificar os coeficientes. A recomendação se apoia no ATT do pareamento.
- *Acréscimo não registrado:* a duração estimada é um limite inferior, e #nf("vermelhos_t_restante_zero") vermelhos ficam com tempo restante zero.
- *Sem escalação:* a posição vem da formação, e meio-campo × atacante depende da classificação dos pontas. Volante não é distinguido.
- Poucos vermelhos no 1º tempo (#n("vermelhos_1o_tempo_regulamentar") + #n("vermelhos_acrescimo_1o_tempo") no acréscimo) e só #att("faixa 0–15").n_tratados nos primeiros 15 minutos.

= Técnica: justificativa da decisão

#text(size: 20pt)[
  *Percebemos que* um vermelho custa #fmt(calc.abs(float(att_todos.att))) ponto ao time punido e que o risco de expulsão é #fmt((float(p_aj.irr) - 1) * 100, d: 0)% maior quando o time está perdendo. *Isso sugere que* expulsões são, em parte, previsíveis e evitáveis. *Por isso, recomendamos* um protocolo de zona de risco (perdendo por 1, 2º tempo, atleta advertido) e um plano defensivo para jogar com 10. *A decisão foi sustentada por* ATT = #val_ic(att_todos, "att") e IRR = #com_ic(p_aj). *Após* uma temporada, o sucesso pode ser avaliado por *vermelhos por 38 jogos* e acompanhado por *pontos em jogos com expulsão*.
]
#v(0.3cm)
#pendente[critério objetivo de sucesso (por exemplo, a meta de redução de vermelhos por 38 jogos), a definir com a comissão a partir do histórico do clube.]
