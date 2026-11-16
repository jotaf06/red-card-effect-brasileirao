// Artigo final no modelo SBC (máximo de 12 páginas). Compilar a partir da raiz:
//   typst compile --root . --font-path presentation/fonts presentation/artigo.typ
// Nenhum número é digitado: todos vêm de reports/tabelas/ via dados.typ.
#import "dados.typ": *
#import "sbc.typ": sbc, mono, sem-serifa

// Marca visível para o que ainda falta (some quando não houver mais nenhuma).
#let pendente(corpo) = box(fill: rgb("#fff3c4"), inset: (x: 3pt, y: 1pt), text(size: 10pt)[*Pendente:* #corpo])

// ------------------------------------------------------------------ números usados no texto
#let att_todos = att("todos")
#let a75 = att("até 75'")
#let d75 = att("depois de 75'")
#let p_aj = irr("ajustado", "estado[perdendo]")
#let p_sa = irr("sem ajuste", "estado[perdendo]")
#let v_aj = irr("ajustado", "estado[vencendo]")
#let v_sa = irr("sem ajuste", "estado[vencendo]")
#let z = formacao("Zagueiro")
#let g = formacao("Goleiro")
#let gi = gols_irr("todos", "vantagem[inferior]")
#let gs = gols_irr("todos", "vantagem[superior]")
#let h1m = h1_teste("H1 ΔPE de um vermelho no minuto 45, empatando (média dos lados) [multinomial]")
#let cz = conversao("zagueiro · 1º tempo")
#let cd = conversao("demais · 1º tempo")
#let tz = ins_teste("I2 conversão: zagueiro 1º tempo × demais 1º tempo")
#let tz2 = ins_teste("I2 conversão: zagueiro 2º tempo × demais 2º tempo")
#let m1 = ins_meta("I1")
#let m2 = ins_meta("I2")
#let m3 = ins_meta("I3")
#let perda_media = float(liga("pontos_perdidos_estimados").media)
#let corte_perto = ins_corte.filter(l => float(l.diferenca) <= calc.ceil(perda_media)).len()
#let razao_fim = float(taxa_faixa("76–90+").taxa_90) / float(taxa_faixa("0–15").taxa_90)
#let pct_var_abs(x) = fmt(calc.abs(float(x) - 1) * 100, d: 0) + "%"
#let tem(k) = resumo.find(l => l.chave == k) != none

#show: sbc.with(
  titulo: [Quanto custa uma expulsão? Efeito do cartão vermelho, por minuto e contexto de jogo, no Campeonato Brasileiro Série A (2014–2024)],
  autores: ((nome: "José Felix de Oliveira Neto", inst: 1), (nome: "Rafael Anacleto Alves de Souza", inst: 1)),
  instituicoes: ([Instituto de Computação -- Universidade Federal de Alagoas (UFAL)\ Maceió -- AL -- Brasil],),
  emails: "{jfon,raas}@ic.ufal.br",
  abstract: [We estimate the cost of a red card in the Brazilian Série A from #n("partidas_2014_2024") matches (2014–2024), controlling for the score at the moment of the dismissal, home advantage and an Elo rating. Teams that are losing receive #pct_var_abs(p_aj.irr) more red cards per minute of exposure, so the score must be controlled. Matching each dismissed team to teams in the same minute, venue and score, a red card costs #fmt(-float(att_todos.att)) points (95% CI #fmt(-float(att_todos.ic95_sup))–#fmt(-float(att_todos.ic95_inf))), #fmt(-float(a75.att)) up to minute 75. We derive three actionable recommendations with league-based targets.],
  resumo: [Estimamos o custo de um cartão vermelho na Série A a partir de #n("partidas_2014_2024") partidas (2014–2024), controlando o placar no momento da expulsão, o mando e um rating Elo. Times que estão perdendo recebem #pct_var_abs(p_aj.irr) mais vermelhos por minuto de exposição, e por isso o placar precisa ser controlado. Pareando cada time expulso com times no mesmo minuto, mando e placar, um vermelho custa #fmt(-float(att_todos.att)) ponto (IC 95%: #fmt(-float(att_todos.ic95_sup))–#fmt(-float(att_todos.ic95_inf))), e #fmt(-float(a75.att)) até os 75 minutos. Derivamos três recomendações acionáveis, com metas baseadas na liga.],
)

#set figure(placement: auto)

= Aplicação

Um cartão vermelho deixa o time com dez jogadores pelo resto da partida. A comissão técnica decide, à beira do campo, se substitui um atleta já advertido e como reorganizar o time depois de uma expulsão, mas raramente sabe quanto uma expulsão custa em pontos, nem quando ela é mais provável. Este trabalho responde a essas perguntas para o Campeonato Brasileiro Série A: *qual é o impacto do vermelho sobre o resultado, e como ele varia com o minuto, o placar no momento, o mando e a força relativa dos times?*

O cliente é a comissão técnica e o departamento de análise de desempenho de um clube da Série A. A análise apoia três decisões: o protocolo disciplinar por posição e fase do jogo; a conduta tática depois de uma expulsão; e a priorização de orientação aos atletas de maior risco.

O efeito do vermelho já foi medido em outras competições. Em ligas holandesas, a chance de vitória do adversário cresce quanto mais cedo ocorre a expulsão @ridder1994. Em Copas do Mundo, o mito de que "dez jogam melhor" não se confirma @caliendo2006. Na Inglaterra, o vermelho altera as taxas de gols, e o amarelo não @titman2015. Nas copas europeias, o efeito para o visitante depende do minuto @demeyere2018. Para o Brasileirão, a literatura concentra-se na vantagem de mando @leite2024 e na previsão de resultados, e uma busca em novembro de 2026 não encontrou estudo do efeito do vermelho no resultado da Série A que considere o minuto e o placar da expulsão. Este trabalho ocupa essa lacuna com dados de onze temporadas.

As cinco hipóteses da análise estão na @tab:hipoteses, com o método usado para testar cada uma e a resposta encontrada. A vantagem de mando ao longo do tempo, tema já coberto por @leite2024, ficou fora do escopo.

#figure(
  text(size: 10pt, {set par(justify: false); table(columns: (auto, 1.7fr, 1fr, 1fr), align: (left + top, left + top, left + top, left + top),
    stroke: none, inset: (x: 4pt, y: 3pt),
    table.hline(), table.header[][*Hipótese*][*Método*][*Resposta*], table.hline(stroke: 0.5pt),
    [*H1*], [O vermelho reduz os pontos do time punido, com placar, mando e força controlados], [pareamento e modelo de estado], [sustentada (@res-custo)],
    [*H2*], [Expulsões mais cedo custam mais], [pareamento e modelo de estado], [em parte (@res-custo)],
    [*H3*], [Quem está perdendo leva mais vermelhos (causalidade reversa)], [Poisson por exposição], [sustentada (@inferencia)],
    [*H4*], [O efeito difere entre mandante e visitante], [pareamento e modelo de estado], [sem conclusão (@res-mando)],
    [*H5*], [Os vermelhos se concentram em posições específicas e no fim do jogo], [Poisson por exposição e aderência à formação], [sustentada para o minuto; em parte para a posição (@inferencia)],
    table.hline(),
  )}),
  caption: [Hipóteses, métodos e respostas],
) <tab:hipoteses>

= Base de Dados

== Origem e estrutura

A base é o conjunto _Brasileirao_Dataset_ @duque_dataset, com quatro arquivos CSV ligados pelo identificador da partida (@tab:arquivos). O arquivo de partidas cobre #n("temporadas_total") temporadas (2003–2024), mas o minuto de gols e cartões só existe de 2014 a 2024: são #n("partidas_2014_2024") partidas, o período da análise, com #n("amarelos") amarelos e #n("vermelhos") vermelhos, presentes em #n("pct_partidas_com_vermelho")% das partidas. A variável-alvo é o resultado final (vitória, empate ou derrota) e os pontos de cada time.

#figure(
  table(columns: (auto, auto, auto, 1fr), align: (left, right, right, left), stroke: none,
    table.hline(), table.header[*Arquivo*][*Linhas*][*Colunas*][*Uma linha é*], table.hline(stroke: 0.5pt),
    [`full`], [#n("partidas_total")], [#n("colunas_partidas")], [partida],
    [`estatisticas-full`], [#n("estatisticas_linhas")], [#n("colunas_estatisticas")], [time em uma partida],
    [`gols`], [#n("gols_linhas")], [#n("colunas_gols")], [gol, com minuto],
    [`cartoes`], [#n("cartoes_linhas")], [#n("colunas_cartoes")], [cartão, com minuto e posição],
    table.hline(),
  ),
  caption: [Arquivos da base bruta],
) <tab:arquivos>

== Pré-processamento

O pré-processamento está em `src/clean.py` e `src/features.py`. Os arquivos brutos nunca são alterados, e um único comando (`python -m src.run_all`) refaz todas as etapas, do download às tabelas analíticas. A @tab:preproc resume as técnicas, os parágrafos seguintes detalham cada uma, e a @fig:antes-depois mostra uma partida real antes e depois do processo.

#let pp(etapa, tecnica, afetados) = (text(weight: "bold", etapa), tecnica, afetados)
#figure(
  text(size: 10pt, {set par(justify: false); table(columns: (auto, 1fr, auto), align: (left + top, left + top, right + top), stroke: none, inset: (x: 4pt, y: 3pt),
    table.hline(), table.header[*Etapa*][*Técnica*][*Afetados*], table.hline(stroke: 0.5pt),
    ..pp([Limpeza], [minuto `45+2` separado em tempo, minuto e acréscimo; texto `"55%"` convertido em número; nomes normalizados], [todos os eventos]),
    ..pp([Ausentes], [zeros que eram ausência viram nulos], [#n("estatisticas_anuladas_total") linhas]),
    ..pp([], [posição imputada pelo histórico do atleta e, nos vermelhos, anotada pela escalação], [#n("posicao_nula_original") cartões]),
    ..pp([], [acréscimo não registrado, estimado por partida e temporada], [todas as partidas]),
    ..pp([Inconsistências], [temporada pelo calendário do campeonato; resultado pelo placar; estádios por dicionário], [#n("arenas_grafias_total") → #n("arenas_estadios_total") estádios]),
    ..pp([Integração], [quatro arquivos unidos pela partida; gols e cartões numa linha do tempo única], [#nf("eventos_linhas") eventos]),
    ..pp([Transformação], [tipo de vermelho, trechos e exposição, _landmarks_, Elo pré-jogo], [#nf("landmarks_linhas") _landmarks_]),
    ..pp([Seleção], [janela 2014–2024; estatísticas de jogo, técnico e estádio fora dos modelos], [#n("partidas_2014_2024") partidas]),
    table.hline(),
  )}),
  caption: [Técnicas de pré-processamento aplicadas],
) <tab:preproc>

*Limpeza dos dados.* O minuto dos eventos vinha como texto com acréscimo (`45+2`, `90+5`). Ele foi separado em tempo de jogo, minuto-base e acréscimo, com uma chave de ordenação em que `45+3` vem antes de `46`. Posse de bola e precisão de passes, também em texto (`"55%"`), viraram números. Os nomes de estádio passaram por normalização Unicode (NFKC), que remove espaços não separáveis, e perderam a anotação `*(PF)` de jogos de portões fechados. A variante `Zagueira` foi unificada em `Zagueiro`.

*Tratamento de valores ausentes.* Três tipos de ausência foram tratados de formas diferentes.
(i) *Ausência disfarçada:* nas estatísticas, linhas com chutes, passes e faltas todos iguais a zero não descrevem um jogo real. Essas #n("estatisticas_anuladas_total") linhas viraram nulas (#n("estatisticas_anuladas_2015_2023") delas em 2015–2023), sem perder os cartões.
(ii) *Posição do atleta:* #n("posicao_nula_original") cartões de 2014 a 2018 vinham sem posição. Descartá-los enviesaria a H5 para os anos completos. Primeiro, #n("posicao_imputada") herdaram a posição do mesmo atleta em outros cartões, quando ela cobria ao menos 80% dos seus registros. Depois, os vermelhos que sobraram foram anotados à mão pela escalação de cada jogo (`data/manual/posicao_vermelhos.csv`). Restam #n("posicao_nula_final") cartões sem posição, todos amarelos: nenhum vermelho ficou sem posição.
(iii) *Acréscimo:* a base não registra o acréscimo dado pelo árbitro. Ele foi estimado como o maior entre o acréscimo observado nos eventos da partida e a mediana da temporada, e a duração mediana passa de #nf("duracao_mediana_2014") minutos em 2014 para #nf("duracao_mediana_2024") em 2024. A estimativa é um limite inferior: #nf("vermelhos_t_restante_zero") vermelhos ficam com tempo restante zero.

*Dados inconsistentes.* A *temporada* não coincide com o ano da data: a de 2020 terminou em fevereiro de 2021, e por isso ela foi definida pelo calendário do campeonato e validada com 380 jogos por edição. A coluna *vencedor* diverge do placar numa partida de 2005; o resultado (V, E, D) foi derivado do placar, que bate com a contagem de gols em todas as partidas. Os *estádios* apareciam com nomes popular, oficial e comercial e com grafias variadas (`Arena da Baixada`, `Kyocera Arena`, `Ligga Arena`). Um dicionário manual (`data/manual/arenas.csv`) leva as #n("arenas_grafias_total") grafias a #n("arenas_estadios_total") estádios, com cidade e UF, contando como o mesmo estádio o mesmo local físico. A execução é interrompida se aparecer um nome sem mapeamento, um campo vazio ou um estádio com duas cidades.

*Integração.* Os quatro arquivos são unidos pelo identificador da partida, e os nomes de clubes coincidem entre eles. Gols e cartões formam uma linha do tempo única de #nf("eventos_linhas") eventos. No mesmo minuto, o gol vem antes do cartão e o amarelo antes do vermelho. Cada evento guarda o placar e o número de jogadores de cada lado antes e depois dele.

*Transformação de variáveis.* A base não distingue vermelho direto de 2º amarelo. Um vermelho é de *2º amarelo* quando o atleta tem um amarelo anterior na mesma partida (#nf("vermelhos_2o_amarelo") casos), e *direto* nos demais (#nf("vermelhos_direto")). Cada partida é dividida em #nf("trechos") *trechos* com placar e jogadores constantes, que dão a *exposição*: quantos minutos cada time passou perdendo, empatando ou vencendo, com 11 ou com 10, em cada faixa de 15 minutos. Os *landmarks* fotografam o estado da partida a cada 5 minutos (#nf("landmarks_linhas") linhas), com saldo, saldo dividido pela raiz do tempo restante, tempo restante, Elo e vermelhos de cada lado. A força relativa vem de um *rating Elo* @hvattum2010 calculado desde 2003 só com jogos anteriores a cada partida. Os parâmetros foram escolhidos por log-loss em 2004–2013, fora da janela de análise (K = #fmt(elo_escolhido.k, d: 1), mando de #fmt(elo_escolhido.mando, d: 0) pontos). A variável-alvo é o resultado final e os pontos (3, 1 ou 0).

*Seleção e redução de atributos.* Entram as #n("partidas_2014_2024") partidas de 2014 a 2024, as únicas com minuto de gols e cartões; as de 2003 a 2013 servem apenas para calibrar o Elo. As estatísticas de jogo (chutes, posse) ficam de fora: estão vazias antes de 2015 e em 2024 e, por serem do jogo inteiro, incluem o que aconteceu depois da expulsão, o que seria vazamento. Técnico e estádio não entram nos modelos, e a formação é usada só como referência de posições na H5. Para o efeito do vermelho, a população é o 1º vermelho de cada partida até o minuto 90 (#att_todos.n_tratados casos), um corte que usa só o minuto do vermelho, nunca o que aconteceu depois dele.

*Validação.* Testes automáticos interrompem o pipeline se os gols por lado não baterem com o placar, se o placar reconstruído evento a evento divergir do final, se o número de jogadores sair do intervalo de 7 a 11, se a exposição de um time não somar a duração da partida ou se o Elo de uma partida mudar quando se altera o resultado dela.

// Uma partida antes e depois do pré-processamento (tabelas exemplo_partida_* de src/features.py).
#let exb = tabela("exemplo_partida_bruto_eventos")
#let exr = tabela("exemplo_partida_bruto_partida").at(0)
#let exd = tabela("exemplo_partida_eventos")
#let exd0 = exd.at(0)
#let cru(x) = text(font: mono, size: 8pt, if x == "" { "\"\"" } else { x })
#let ou(x) = if x == "" { "—" } else { x }
#let lado-nome = (mandante: "mand.", visitante: "visit.")
#let cab(..c) = c.pos().map(x => text(weight: "bold", x))
#let rotulo-ad(t) = align(left, text(font: sem-serifa, size: 8.5pt, weight: "bold", t))
#figure(
  {
    set text(size: 8.5pt)
    set par(justify: false, first-line-indent: 0pt)
    set smartquote(enabled: false)
    set align(left)
    rotulo-ad[(a) Antes: linhas dos CSVs brutos, na ordem dos arquivos]
    v(2pt)
    align(left, [`full`: #cru(exr.ID) · #cru(exr.data) · #cru(exr.mandante) #cru(exr.mandante_Placar)×#cru(exr.visitante_Placar) #cru(exr.visitante) · vencedor #cru(exr.vencedor) · arena #cru(exr.arena)])
    v(2pt)
    table(columns: (auto, auto, auto, auto, auto), align: left, stroke: none, inset: (x: 5pt, y: 1.6pt),
      table.hline(), table.header(..cab[Arquivo][Clube][Registro][Posição][Minuto]), table.hline(stroke: 0.4pt),
      ..exb.map(l => (raw(l.arquivo), cru(l.clube), cru(l.registro), cru(l.posicao), cru(l.minuto))).flatten(),
      table.hline(),
    )
    v(6pt)
    rotulo-ad[(b) Depois: tabela de eventos, ordenada e com o estado do jogo]
    v(2pt)
    align(left, [temporada #exd0.temporada · #exd0.mandante #exd0.placar_mandante×#exd0.placar_visitante #exd0.visitante · resultado do mandante #exd0.resultado_mandante · arena #exd0.arena · diferença de Elo #fmt(exd0.elo_diff, d: 1) · duração estimada #fmt(exd0.duracao, d: 0) min])
    v(2pt)
    table(columns: 11, align: (x, y) => if x in (0, 1, 2, 3, 9, 10) { right } else { left }, stroke: none, inset: (x: 4pt, y: 1.6pt),
      table.hline(), table.header(..cab[Tempo][Min.][Acr.][$t$][Evento][Lado][Posição][Vermelho][Placar antes][Jogadores][$t$ rest.]), table.hline(stroke: 0.4pt),
      ..exd.map(l => (l.tempo, l.minuto_base, l.acrescimo, fmt(l.t, d: 0), l.tipo, lado-nome.at(l.lado), ou(l.posicao),
        ou(l.vermelho_tipo), [#l.gols_mandante_antes–#l.gols_visitante_antes], [#l.jogadores_mandante_depois×#l.jogadores_visitante_depois],
        fmt(l.t_restante, d: 0))).flatten(),
      table.hline(),
    )
  },
  kind: image,
  caption: [Uma partida antes e depois do pré-processamento. Em (a), os eventos vêm em dois arquivos, fora de ordem, com o minuto em texto (`90+9`) e o estádio com o nome oficial. Em (b), formam uma linha do tempo única, com o minuto separado em tempo e acréscimo, o tempo corrido $t$, o tipo do vermelho, o placar antes do evento, os jogadores em campo depois dele e o tempo restante estimado],
) <fig:antes-depois>

= Estatística Descritiva e Inferência <inferencia>

Contagens brutas de vermelhos enganam, porque os times passam tempos diferentes em cada situação. A medida é a *taxa por 90 minutos de exposição*, e os efeitos ajustados vêm de uma regressão de Poisson com o logaritmo da exposição como _offset_, que estima a razão de taxas (IRR). Os intervalos de 95% vêm de um bootstrap por partida (2.000 réplicas), que respeita a dependência entre trechos do mesmo jogo, e os p-valores de cada família são corrigidos por Holm @holm1979.

#let gc = desc_grupo("com vermelho")
#let gsv = desc_grupo("sem vermelho")
#let tq = desc_teste("Qui-quadrado")
#let tmw = desc_teste("Mann-Whitney: pontos")
#let rem = resultado_estado("empatando")
#let rve = resultado_estado("vencendo")
*Resultado com e sem expulsão.* Sem nenhum ajuste, o time que leva vermelho vence #pct(gc.pct_vitoria, d: 0)% e perde #pct(gc.pct_derrota, d: 0)% das partidas, contra #pct(gsv.pct_vitoria, d: 0)% e #pct(gsv.pct_derrota, d: 0)% de quem não leva (qui-quadrado, p #pfmt(tq.p_holm)#[;] V de Cramér #fmt(tq.valor_efeito)). Ele faz #fmt(gc.pontos_media) ponto por jogo, contra #fmt(gsv.pontos_media) (Mann-Whitney, p #pfmt(tmw.p_holm)#[;] correlação bisserial de postos #fmt(tmw.valor_efeito)), uma diferença de #val_ic(tmw, "dif_media") ponto, com IC por bootstrap de partidas, porque os dois times do mesmo jogo não são independentes. Dos #(int(rem.total) + int(rve.total)) punidos que ainda não perdiam no momento do 1º vermelho, #(int(rem.derrota) + int(rve.derrota)) terminaram derrotados. Essa diferença bruta, porém, mistura o efeito do vermelho com a situação em que ele acontece, como mostra a H3 a seguir.

*H3: placar no momento.* Sem ajuste, quem está perdendo recebe #fmt(taxa_estado("perdendo").taxa_90, d: 3) vermelho por 90 minutos, contra #fmt(taxa_estado("empatando").taxa_90, d: 3) empatando (IRR #fmt(p_sa.irr)). Parte disso é efeito do minuto, porque o tempo perdendo se concentra no fim do jogo. Controlando faixa de minuto, mando, quintil de Elo e vantagem numérica, a IRR cai para #com_ic(p_aj) (p de Holm #pfmt(h3_teste("H3 IRR estado[perdendo] vs empatando (ajustado)").p_holm)). Já o aparente risco de quem vence (#fmt(v_sa.irr) sem ajuste) inverte para #com_ic(v_aj). O resultado se mantém por tipo de vermelho e sem os acréscimos. *A H3 é sustentada*: o placar no momento precisa entrar como controle no efeito do vermelho.

#figure(image("/reports/figures/h5_taxa_faixa.png", width: 82%),
  caption: [Vermelhos por time a cada 90 minutos de exposição, por faixa de minuto e tipo, com IC 95% bootstrap]) <fig:faixa>

#let h5_ad = h5_teste("H5 aderência: vermelhos por faixa × exposição (todos)")
#let pos_ad = h5_teste("H5 aderência: posição dos vermelhos × formação (principal)")
#let pf = h5_teste("H5 independência: posição × faixa")
*H5: minuto e posição.* A taxa cresce #fmt(razao_fim, d: 0) vezes da faixa 0–15 para a 76–90+ (@fig:faixa; qui-quadrado contra a exposição, p #pfmt(h5_ad.p_holm)#[;] V de Cramér #fmt(h5_ad.valor_efeito)). Sem escalação, a referência de posição é a formação de cada jogo (2015–2024): os zagueiros, que na base incluem laterais, recebem #com_ic(z, valor: "razao_obs_esp") vez o esperado, e os goleiros #com_ic(g, valor: "razao_obs_esp") (p #pfmt(pos_ad.p_holm)). Meio-campo e ataque dependem de onde se contam os pontas e ficam sem conclusão. Posição e minuto não se associam (p #pfmt(pf.p_holm)). Por fim, o zagueiro advertido no 1º tempo termina expulso por 2º amarelo em #pct(cz.taxa)% dos casos (IC de Wilson: #pct(cz.ic95_inf)–#pct(cz.ic95_sup)%), contra #pct(cd.taxa)% nas demais posições (teste z, razão #fmt(tz.valor_efeito), p de Holm #pfmt(tz.p_holm)). No 2º tempo, não há diferença (p #pfmt(tz2.p_holm)). *A H5 é sustentada* para o minuto e, em parte, para a posição.

= Métodos Avaliados

A população do efeito são as partidas cujo 1º vermelho ocorreu até o minuto 90 regulamentar. O corte usa só o minuto do vermelho, nunca o que aconteceu depois dele, para não criar viés de seleção. Três métodos estimam o mesmo efeito, porque cada um falha de um jeito.

*Modelo de estado do jogo.* Uma regressão logística multinomial prevê vitória, empate ou derrota do mandante em cada landmark, a partir do saldo (também dividido pela raiz do tempo restante), do tempo restante, da diferença de Elo e sua interação com o tempo, e dos vermelhos de cada lado, com e sem interação com o tempo. O custo da expulsão é a variação de pontos esperados do punido, $Delta"PE" = "PE"_"com" - "PE"_"sem"$, com $"PE" = 3 P(V) + P(E)$.

*Pareamento.* Cada time expulso é comparado a até 5 times de outras partidas que, no mesmo minuto, tinham o mesmo mando e saldo (−2 a +2), ainda não tinham levado vermelho e tinham o Elo mais próximo @stuart2010. A medida é o efeito médio do tratamento sobre os tratados (ATT) em pontos finais. O equilíbrio ficou bom: diferença padronizada de Elo de #fmt(h1_equilibrio.diferenca_padronizada_elo, d: 3). É o método mais transparente e o usado na recomendação.

*Poisson de gols.* Sobre a exposição, estima a taxa de gols marcados e sofridos com um jogador a menos, controlando minuto, saldo, mando e Elo.

*Modelos de comparação.* Random forest e LightGBM @ke2017 preveem o mesmo resultado com as mesmas entradas, ao lado dos baselines obrigatórios "sempre mandante" e frequências históricas, além do Elo pré-jogo. Servem para verificar se a multinomial, mais simples e interpretável, perde precisão.

= Métricas de Avaliação

Para a previsão do resultado, as métricas principais avaliam *probabilidades*: log-loss, Brier e RPS (_ranked probability score_), adequado a resultados ordenados @constantinou2012. AUC um-contra-todos e acurácia também são reportadas, mas a acurácia sozinha é enganosa, porque quase nenhum modelo prevê empates. Para o efeito, as medidas são o ATT e o $Delta"PE"$ em pontos, e a IRR para taxas, sempre com IC de 95%.

= Métodos de Avaliação

*Validação temporal:* treino em 2014–2021 e teste em 2022–2024, como no uso real, em que se treina no passado e se aplica ao futuro. *Validação cruzada agrupada por partida* (5 grupos) dentro do treino escolhe os hiperparâmetros, para que landmarks do mesmo jogo nunca fiquem dos dois lados. *Bootstrap por partida* dá os intervalos das métricas no teste e dos efeitos. A *correção de Holm* controla as comparações múltiplas em cada família de testes.

= Resultados e Discussão

== Custo da expulsão (H1 e H2) <res-custo>

O vermelho reduz os pontos do punido em todos os métodos. No pareamento, com #att_todos.n_tratados expulsões, o ATT é #val_ic(att_todos, "att") ponto por partida (p de Holm #pfmt(h1_teste("H1 pareamento").p_holm)): os expulsos fizeram #fmt(att_todos.pontos_tratados) ponto em média, e seus pares, #fmt(att_todos.pontos_controles). No modelo de estado, um vermelho no intervalo com o jogo empatado custa #val_ic(h1m, "valor_efeito"). O efeito pareado é menor que a diferença bruta da @inferencia (#fmt(desc_teste("Mann-Whitney: pontos").dif_media)), porque parte dela vem do placar e da força de quem é expulso. *A H1 é sustentada.*

#figure(image("/reports/figures/h1_pareamento.png", width: 72%),
  caption: [Efeito do vermelho em pontos (ATT do pareamento) por faixa de minuto da expulsão, com IC 95% bootstrap]) <fig:att>

O custo cai ao longo do jogo (@fig:att): #val_ic(att("faixa 16–30"), "att") entre os minutos 16 e 30 e #val_ic(att("faixa 76–90"), "att") entre 76 e 90. Até os 75 minutos, o custo é #val_ic(a75, "att"), cerca de #fmt(float(a75.att) / float(d75.att), d: 0) vezes o de depois (#val_ic(d75, "att")). No modelo multinomial, porém, a diferença entre os minutos 15 e 75 não é significativa, e os primeiros 15 minutos têm só #att("faixa 0–15").n_tratados expulsões. *A H2 é sustentada em parte.*

#let est_linha(rotulo, e) = {
  let l = resultado_estado(e)
  ([#rotulo (#l.total)], l.derrota, l.empate, l.vitória)
}
#let rp = resultado_estado("perdendo")
O resultado final também depende do placar no momento da expulsão (@tab:estado). Entre os punidos que estavam empatando, #rem.derrota de #rem.total terminaram derrotados; entre os que já perdiam, só #(int(rp.empate) + int(rp.vitória)) de #rp.total evitaram a derrota. Quem é expulso perdendo raramente se recupera, e por isso o custo pareado nesse grupo é pequeno: há pouco a perder.

#figure(
  text(size: 10pt, table(columns: (auto, auto, auto, auto), align: (left, right, right, right), stroke: none,
    inset: (x: 8pt, y: 3pt),
    table.hline(), table.header[*Placar no 1º vermelho*][*Derrota*][*Empate*][*Vitória*], table.hline(stroke: 0.5pt),
    ..est_linha("empatando", "empatando"), ..est_linha("vencendo", "vencendo"), ..est_linha("perdendo", "perdendo"),
    table.hline(),
  )),
  caption: [Resultado final do time punido, pelo placar no momento do 1º vermelho (até o minuto 90). Entre parênteses, o número de expulsões],
) <tab:estado>

== Mando e gols (H4) <res-mando>

#let h4d = h1_teste("H4 pareamento: ATT mandante − ATT visitante")
O mandante expulso perde #fmt(att("lado mandante").att) ponto e o visitante #fmt(att("lado visitante").att) (diferença #fmt(h4d.valor_efeito), p de Holm #pfmt(h4d.p_holm)). Parte disso é efeito teto, pois o mandante tem mais pontos a perder, e o modelo de estado não confirma a diferença: *a H4 fica sem conclusão*. Com um a menos, o time sofre gols a #com_ic(gs) vez a taxa da igualdade numérica e marca a #com_ic(gi). A expulsão pesa mais pelo que se sofre. A @fig:gols mostra o padrão para mandante e visitante e no modelo com efeito fixo de partida, que compara o antes e o depois dentro do mesmo jogo.

#figure(image("/reports/figures/h1_gols.png", width: 80%),
  caption: [Razão de taxas de gols marcados com um jogador a menos (azul) e a mais (laranja), em relação à igualdade numérica, com IC 95%. A série "com um a mais" equivale aos gols que o time com dez sofre]) <fig:gols>

== Comparação de modelos

#let linha_m(nome) = {
  let m = metrica(nome)
  (nome, fmt_ou(m.log_loss), fmt_ou(m.brier), fmt_ou(m.rps), fmt_ou(m.auc_ovr), fmt_ou(m.acuracia))
}
#figure(
  table(columns: (1fr, auto, auto, auto, auto, auto), align: (left, right, right, right, right, right), stroke: none,
    table.hline(), table.header[*Modelo*][*Log-loss*][*Brier*][*RPS*][*AUC*][*Acurácia*], table.hline(stroke: 0.5pt),
    ..("sempre mandante", "frequências históricas", "Elo pré-jogo",
       "logística multinomial", "random forest", "LightGBM").map(linha_m).flatten(),
    table.hline(),
  ),
  caption: [Métricas no teste (2022–2024, #milhar(metrica("logística multinomial").n_linhas) landmarks). "Sempre mandante" não produz probabilidades],
) <tab:modelos>

A multinomial tem a menor log-loss no teste (@tab:modelos). A random forest fica a #val_ic(dif_ll("random forest"), "dif_log_loss_vs_multinomial", d: 4), intervalo que inclui zero, e o LightGBM fica atrás. Como a multinomial é tão boa quanto o melhor modelo flexível e é interpretável, ela é o modelo de estado adotado. Ajustada só no treino, porém, sua curva de custo no início do jogo muda bastante, porque há poucos vermelhos precoces. Por isso a recomendação usa o ATT do pareamento.

== Decisão recomendada

Uma expulsão custa em média #fmt(perda_media, d: 1) ponto por time e por temporada (soma do ATT de cada 1º vermelho, pela faixa de minuto), e em #corte_perto das #ins_corte.len() temporadas o 16º e o 17º colocados ficaram separados por até #calc.ceil(perda_media) ponto. Como a base não identifica o clube cliente, as metas usam a distribuição da liga por time e temporada. Os três insights seguem o formato exigido.

*Insight 1 (o relógio).* Percebemos que uma expulsão até os 75 minutos custa #fmt(-float(a75.att)) ponto, contra #fmt(-float(d75.att)) depois, e que #pct(float(att("tipo 2o_amarelo").n_tratados) / float(att_todos.n_tratados), d: 0)% dos vermelhos vêm do 2º amarelo. Isso sugere que o atleta já advertido é o risco evitável, e que o minuto diz quanto ele vale. Por isso, recomendamos uma zona de risco até os 75 minutos, em que o advertido envolvido em lances de risco é o primeiro candidato à substituição. A decisão foi sustentada pelo ATT do pareamento (ICs sem sobreposição). Após uma temporada, o sucesso pode ser avaliado pelos vermelhos por 2º amarelo até os 75 minutos (média da liga: #fmt(m1.liga_media, d: 1)) e acompanhado pelos pontos perdidos estimados. A ação será bem-sucedida se #if float(m1.meta) == 0 [não houver nenhuma expulsão desse tipo] else [houver no máximo #fmt(m1.meta, d: 0)], o quartil inferior da liga.

*Insight 2 (a posição).* Percebemos que o zagueiro advertido no 1º tempo é expulso em #pct(cz.taxa)% dos casos, o dobro das demais posições, e que zagueiros recebem #fmt(z.razao_obs_esp)× os vermelhos esperados pela formação. Isso sugere que o risco é o zagueiro com amarelo e o 2º tempo inteiro pela frente. Por isso, recomendamos avaliar no intervalo a substituição ou a mudança de função do zagueiro advertido, além de treino de bote e cobertura com a linha defensiva. A decisão foi sustentada pelo teste de proporções (p de Holm #pfmt(tz.p_holm)) e pela razão observado/esperado da H5. Após uma temporada, o sucesso pode ser avaliado pelos vermelhos de zagueiros (mediana da liga: #fmt(m2.liga_mediana, d: 0)) e acompanhado pela taxa de expulsão dos zagueiros advertidos no 1º tempo. A ação será bem-sucedida se houver no máximo #fmt(m2.meta, d: 0) vermelho de zagueiro, o quartil inferior da liga.

*Insight 3 (com um a menos).* Percebemos que, com um a menos, o time sofre #pct_var(gs.irr) gols e marca #pct_var(gi.irr). Isso sugere que os pontos se perdem atrás. Por isso, recomendamos um plano pré-treinado para jogar com dez, que preserve a linha defensiva e abra mão de um atacante. A decisão foi sustentada pela Poisson de gols por minuto exposto. Após duas temporadas, porque um time passa só cerca de #fmt(liga("minutos_com_menos").mediana, d: 0) minutos por ano com um a menos, o sucesso pode ser avaliado pelos gols sofridos por 90 minutos com dez (liga: #fmt(m3.liga_media) com dez e #fmt(m3.taxa_com_11) com onze) e acompanhado pelos gols marcados nessa situação. A ação será bem-sucedida se o time sofrer no máximo #fmt(m3.meta) gol por 90 minutos com dez.

As metas são exigentes, mas um time médio as cumpriria por acaso em #pct(m1.chance_acaso, d: 0)%, #pct(m2.chance_acaso, d: 0)% e #pct(m3.chance_acaso, d: 0)% dos períodos, respectivamente. Por isso, um único período mostra a direção, não prova o efeito.

== Limitações

Os dados são observacionais: o pareamento e o controle do estado reduzem o viés, mas não garantem causalidade, e a base não tem posse de bola nem finalizações para descrever o domínio do jogo antes da expulsão. O acréscimo é estimado, e #nf("vermelhos_t_restante_zero") vermelhos ficam com tempo restante zero. A posição vem do cartão, não da escalação, e não separa volantes. Há poucas expulsões nos primeiros 15 minutos.

= Conclusão

Em #n("partidas_2014_2024") partidas da Série A, um vermelho custa #fmt(-float(att_todos.att)) ponto ao time punido, mais quando ocorre até os 75 minutos, e pesa sobretudo nos gols sofridos. Como quem está perdendo leva mais vermelhos, esse custo só aparece corretamente com o placar no momento controlado. A comissão técnica pode agir em três frentes: proteger o advertido até os 75 minutos, decidir no intervalo sobre o zagueiro advertido e ter um plano treinado para jogar com dez. Todos os números deste artigo são gerados por um único pipeline reproduzível (`python -m src.run_all`).

// Referências numa página própria (a última).
#pagebreak()
#bibliography("referencias.bib")
