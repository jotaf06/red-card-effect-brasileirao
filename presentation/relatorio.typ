#import "dados.typ": *

#set document(title: "Quanto custa uma expulsão? Relatório de andamento", author: "José Felix")
#set page(paper: "a4", margin: 2.5cm, numbering: "1")
#set text(lang: "pt", size: 11pt)
#set par(justify: true)
#set heading(numbering: "1.")
#show link: underline
#show figure.caption: set text(size: 9.5pt)
#set figure(placement: auto)

#align(center)[
  #text(size: 18pt, weight: "bold")[Quanto custa uma expulsão?]
  #v(0.3em)
  #text(size: 13pt)[Efeito do cartão vermelho, por minuto e contexto de jogo, no resultado das partidas do Campeonato Brasileiro Série A (2014–2024)]
  #v(0.5em)
  Relatório de andamento \
  José Felix · Ciência de Dados · UFAL/IC · 2026.1
]

#outline(title: "Sumário", indent: auto)

= Aplicação

*Problema.* Qual o impacto de um cartão vermelho sobre o resultado de uma partida (pontos esperados, probabilidades de vitória, empate e derrota, e taxa de gols), e como esse impacto varia com o minuto da expulsão, o placar no momento, o mando de campo e a força relativa dos times.

*Justificativa.* A literatura sobre o Brasileirão se concentra em vantagem de mando e em previsão de resultados. O efeito do vermelho foi estudado com dados de Copas do Mundo @caliendo2006, em que o efeito depende do minuto. Antes de afirmar que há lacuna para o Brasileirão, falta uma busca sistemática por "red card" e "Brazilian" com tempo ou minuto da expulsão.

*Cliente e decisões apoiadas.* A comissão técnica e o departamento de análise de desempenho de um clube da Série A. A análise deve apoiar:
- o protocolo disciplinar por posição e por fase do jogo;
- a conduta tática após uma expulsão, própria ou do adversário, conforme minuto e placar;
- a priorização de treinamento e de orientação aos atletas de maior risco disciplinar.

*Hipóteses.*
- *H1:* o vermelho reduz os pontos esperados do time punido, controlando placar no momento, mando e força relativa.
- *H2:* o efeito depende do minuto, com expulsões mais cedo custando mais.
- *H3:* existe causalidade reversa, pois times que estão perdendo recebem mais vermelhos. Sem controlar o placar no momento, o efeito fica superestimado.
- *H4:* o efeito difere entre mandante e visitante.
- *H5:* os vermelhos se concentram em posições específicas e nos minutos finais.
- *H6 (contexto):* a vantagem de mando diminuiu entre 2003 e 2024, ou em 2020, nos jogos sem público.

= Base de Dados

== Origem e estrutura

Os dados vêm do conjunto "Campeonato Brasileiro de Futebol", de Adão Duque, disponível em #link("https://github.com/adaoduque/Brasileirao_Dataset") e no Kaggle. São quatro arquivos CSV ligados por `ID` (partida) ou `partida_id`.

#figure(
  table(
    columns: (auto, auto, auto, 1fr),
    align: (left, right, right, left),
    table.header[*Arquivo*][*Linhas*][*Colunas*][*Granularidade*],
    [`full`], [#n("partidas_total")], [#n("colunas_partidas")], [partida],
    [`estatisticas-full`], [#n("estatisticas_linhas")], [#n("colunas_estatisticas")], [time por partida],
    [`gols`], [#n("gols_linhas")], [#n("colunas_gols")], [gol],
    [`cartoes`], [#n("cartoes_linhas")], [#n("colunas_cartoes")], [cartão],
  ),
  caption: [Arquivos da base bruta. Fonte: `reports/tabelas/resumo_base.csv`.],
)

O arquivo de partidas cobre #n("temporadas_total") temporadas, de 2003 a 2024. O minuto de gols e cartões existe de 2014 a 2024, que correspondem a #n("partidas_2014_2024") partidas, o período da análise. Nesse período há #n("amarelos") cartões amarelos e #n("vermelhos") vermelhos, em #n("partidas_com_vermelho") partidas (#n("pct_partidas_com_vermelho")% delas). Em todo o histórico, o mandante vence #n("pct_vitoria_mandante")% das partidas e empata #n("pct_empate")%.

Dos #n("vermelhos") vermelhos, #n("vermelhos_1o_tempo_regulamentar") ocorreram até o minuto 45 do 1º tempo e #n("vermelhos_acrescimo_1o_tempo") no acréscimo do 1º tempo. Poucas expulsões precoces limitam a precisão das estimativas para esse grupo.

== Pré-processamento

O script `src/clean.py` lê `data/raw/`, que nunca é alterado, e grava tabelas limpas em `data/interim/` no formato parquet. O download e a conferência de linhas e colunas ficam em `src/download.py`. O pipeline completo, do download às figuras e a este documento, roda com `python -m src.run_all`.

*Minutos com acréscimo.* Valores como `45+2` são separados em `tempo`, `minuto_base`, `acrescimo`, `minuto_jogado` (base mais acréscimo) e `ordem` (base mais acréscimo dividido por 100). A chave `ordem` garante que `45+3` venha antes de `46`.

*Temporada.* A coluna `temporada` usa o ano da data, com uma exceção: os jogos de 2021 anteriores a 1º de março de 2021 pertencem à temporada 2020, que terminou em 25/02/2021. A regra funciona porque as temporadas de 2020 e 2021 não se sobrepõem, e cada uma fica com 380 jogos.

*Validação do número de jogos.* De 2006 a 2024 cada temporada deve ter 380 jogos. A temporada 2016 tem 379, pois a rodada 38 tem 9 jogos, e isso gera um aviso em vez de erro. As temporadas de 2003 a 2005 têm formato diferente (24 times) e ficam fora dessa regra.

*Resultado da partida.* `resultado_mandante` (V, E ou D) é derivado do placar. A coluna `vencedor` diverge do placar em uma partida de 2005 (`partida_id` 1114), registrada como empate com placar de 0 a 1, e essa divergência é avisada na execução. Foi escolhido o placar por ser validado contra os gols.

*Estatísticas ausentes.* Linhas com chutes, passes e faltas todos iguais a zero são ausências disfarçadas, e viram valores nulos em todas as colunas de estatística, preservando os cartões. Foram #n("estatisticas_anuladas_total") linhas, das quais #n("estatisticas_anuladas_2015_2023") dentro de 2015–2023, o período em que as estatísticas deveriam ser válidas. Posse de bola e precisão de passes, que vinham como texto (`"55%"`), foram convertidas para número.

*Posição nos cartões.* A variante `Zagueira` (22 linhas, todas do mesmo atleta) foi unificada em `Zagueiro`. Havia #n("posicao_nula_original") cartões sem posição, todos de 2014 a 2018. O preenchimento segue duas etapas, registradas na coluna `posicao_origem`:
+ *Imputação automática:* usa a posição do mesmo atleta em outros cartões, se ele tiver uma só posição, ou se a mais frequente cobrir pelo menos 80% dos seus registros. Foram imputadas #n("posicao_imputada") linhas. A posição na base parece ser a da partida e não fixa por atleta, e por isso o limiar de 80%.
+ *Levantamento manual:* os 28 vermelhos sem posição segura foram consultados na escalação de cada jogo e registrados em `data/manual/posicao_vermelhos.csv`. Laterais foram registrados como `Zagueiro`, seguindo a convenção da base. Posições manuais prevalecem sobre as imputadas. Foram preenchidas #n("posicao_manual") linhas, número maior que 28 porque a junção por partida e atleta também alcança o amarelo anterior do mesmo jogador. Nas linhas que já tinham posição imputada, a anotação manual coincidiu com a imputação.

Restam #n("posicao_nula_final") cartões sem posição, todos amarelos: os #n("vermelhos") vermelhos têm posição (#n("vermelhos_posicao_nula_final") nulos).

*Nome do estádio.* A coluna `arena` tinha #n("arenas_grafias_total") grafias para #n("arenas_estadios_total") estádios (#n("arenas_grafias_2014_2024") e #n("arenas_estadios_2014_2024") em 2014–2024). Havia espaços não separáveis no início do nome, a anotação `*(PF)` dos jogos de portões fechados de 2005–2006, abreviações e acentos inconsistentes (`R de Oliveira`, `Heriberto Hulse`) e o mesmo estádio com nome popular, oficial ou comercial (`Arena da Baixada`, `Kyocera Arena`, `Joaquim Américo Guimarães`, `Ligga Arena`). O texto é normalizado, a anotação é removida e o resultado é mapeado pelo dicionário manual `data/manual/arenas.csv` para um nome canônico, com a cidade e a UF. Conta como o mesmo estádio o mesmo local físico, mesmo após reforma ou reconstrução, e o nome canônico é o popular, sem patrocínio, quando ele existe. O valor da fonte fica em `arena_original`, e um nome sem entrada no dicionário interrompe a execução. Jogos em estádio de outro estado não são erro: mando vendido ou estádio indisponível são comuns no futebol brasileiro.

== Atributos derivados

O script `src/features.py` grava as tabelas analíticas em `data/processed/`. Os números desta subseção vêm de `reports/tabelas/features_resumo.csv` e `elo_parametros.csv`.

*Linha do tempo de eventos.* Gols e cartões formam uma linha do tempo única (#nf("eventos_linhas") eventos), ordenada por minuto e, no mesmo minuto, com o gol antes do cartão e o amarelo antes do vermelho. Cada evento guarda o placar e o número de jogadores de cada lado antes e depois dele. Há #nf("partidas_2_mais_vermelhos") partidas com dois ou mais vermelhos.

*Tipo de vermelho.* A base não distingue vermelho direto de segundo amarelo. Um vermelho é classificado como 2º amarelo quando o mesmo atleta, do mesmo clube, tem um amarelo anterior na mesma partida. São #nf("vermelhos_direto") diretos, #nf("vermelhos_2o_amarelo") por 2º amarelo e #nf("vermelhos_indeterminado") indeterminado, sem atleta registrado.

*Duração e tempo restante.* A base não registra o acréscimo dado pelo árbitro. O acréscimo de cada tempo é estimado como o maior entre o acréscimo observado nos eventos da partida e a mediana desse valor na temporada. A duração mediana estimada passa de #nf("duracao_mediana_2014") minutos em 2014 para #nf("duracao_mediana_2024") em 2024. Mesmo assim, #nf("vermelhos_t_restante_zero") vermelhos ficam com tempo restante zero, porque ocorreram depois da mediana de acréscimo e sem eventos posteriores. A estimativa é um limite inferior da duração real.

*Estados de jogo e exposição.* A partida é dividida em #nf("trechos") trechos com placar e número de jogadores constantes, dos quais #nf("trechos_duracao_zero") têm duração zero (eventos simultâneos ou no último minuto registrado). Cruzando os trechos com faixas de 15 minutos, obtém-se, para cada time, quantos minutos ele passou em cada estado e quantos vermelhos e gols ocorreram ali. Essa exposição é a base dos testes da @inferencia.

*Força relativa (Elo).* Um rating Elo é calculado desde 2003 usando apenas jogos anteriores a cada partida. Os parâmetros foram escolhidos por log-loss em 2004–2013, fora da janela de análise, e o resultado foi K = #fmt(elo_escolhido.k, d: 1), vantagem de mando de #fmt(elo_escolhido.mando, d: 1) pontos e regressão de #pct(elo_escolhido.regressao, d: 0)% à média entre temporadas, com multiplicador por saldo de gols. A log-loss na calibração foi #fmt(elo_escolhido.log_loss_2004_2013, d: 4), contra #fmt(elo_baseline.log_loss_2004_2013, d: 4) do baseline de frequências históricas. Em 2014–2024 foi #fmt(elo_escolhido.log_loss_2014_2024, d: 4). Um teste automático confirma que alterar o resultado de uma partida não muda o Elo pré-jogo dela nem o das anteriores.

== Validações

- Os gols por lado, em `gols`, batem com o placar final em todas as partidas de 2014 a 2024. O placar reconstruído evento a evento também bate com o placar final.
- Todo evento de gol ou cartão tem `partida_id` presente em `partidas`, e `estatisticas` tem exatamente duas linhas por partida.
- O número de jogadores em campo fica entre 7 e 11, e nenhum atleta tem dois vermelhos na mesma partida.
- A exposição de cada time soma a duração estimada da partida, e as contagens de vermelhos e gols na tabela de exposição batem com os eventos.

Pendências de qualidade: o técnico continua sem uso. A formação passou a ser usada no H5 (disponível de 2015 a 2024).

= Estatística Descritiva e Inferência <inferencia>

Os testes estão em `src/stats_tests.py`, e as tabelas em `reports/tabelas/h3_*.csv` e `h5_*.csv`.

*Método comum.* Comparar contagens brutas de vermelhos engana, porque os times passam tempos diferentes em cada situação. Por isso, a medida é a *taxa por 90 minutos de exposição*. Os efeitos ajustados vêm de uma regressão de Poisson com offset igual ao logaritmo da exposição, que estima a *razão de taxas* (IRR) entre situações. Os intervalos de confiança de 95% vêm de um bootstrap por partida com 2.000 réplicas. O p-valor usa o erro-padrão desse bootstrap, que leva em conta a dependência entre trechos do mesmo jogo. Dentro de cada família de testes (H3 e H5), os p-valores são corrigidos por Holm, e os valores citados abaixo já estão corrigidos.

== H3: placar no momento do vermelho

#let h3_ad = h3_teste("H3 aderência")
#let p_aj = irr("ajustado", "estado[perdendo]")
#let v_aj = irr("ajustado", "estado[vencendo]")
#let p_sa = irr("sem ajuste", "estado[perdendo]")
#let v_sa = irr("sem ajuste", "estado[vencendo]")
#let hp(modelo, termo) = h3_teste("H3 IRR " + termo + " vs empatando (" + modelo + ")").p_holm

*Sem ajuste.* O time que está perdendo recebe #fmt(taxa_estado("perdendo").taxa_90, d: 3) vermelho por 90 minutos, contra #fmt(taxa_estado("empatando").taxa_90, d: 3) empatando e #fmt(taxa_estado("vencendo").taxa_90, d: 3) vencendo. A distribuição dos vermelhos difere da distribuição da exposição (qui-quadrado, p #pfmt(h3_ad.p_holm)#[;] V de Cramér = #fmt(h3_ad.valor_efeito)).

*Ajustado.* Parte dessa diferença vem do minuto, porque o tempo em que um time está perdendo se concentra no fim do jogo, que é quando os vermelhos se concentram. Controlando faixa de minuto, mando, quintil de diferença de Elo e vantagem numérica, a IRR de perdendo contra empatando cai de #fmt(p_sa.irr) para #com_ic(p_aj) (p #pfmt(hp("ajustado", "estado[perdendo]"))). A de vencendo inverte o sinal: de #fmt(v_sa.irr) sem ajuste para #com_ic(v_aj) (p #pfmt(hp("ajustado", "estado[vencendo]"))). Ou seja, o aparente risco maior de quem vence era efeito do minuto.

*Por tipo de vermelho.* O efeito de estar perdendo aparece tanto no vermelho direto, IRR #com_ic(irr("ajustado — direto", "estado[perdendo]")), quanto no 2º amarelo, IRR #com_ic(irr("ajustado — 2º amarelo", "estado[perdendo]")).

*Robustez.* O resultado se mantém sem os vermelhos de 90+, com IRR #com_ic(irr("robustez — sem 90+", "estado[perdendo]")), e só em 2015–2024, com IRR #com_ic(irr("robustez — 2015–2024", "estado[perdendo]")). Com o saldo em cinco níveis, o risco se concentra em *perder por um gol*, com IRR #com_ic(irr("robustez — saldo em 5 níveis", "saldo5[-1]")). Perder por dois ou mais dá #com_ic(irr("robustez — saldo em 5 níveis", "saldo5[-2]")), com intervalo que inclui 1.

#figure(
  image("/reports/figures/h3_irr.png", width: 88%),
  caption: [Razão de taxas de vermelho (IRR) de perdendo e de vencendo contra empatando, nos modelos principal e de robustez. Fonte: `reports/tabelas/h3_irr.csv`.],
)

*Conclusão.* A H3 é sustentada: times perdendo recebem mais vermelhos, mesmo comparando o mesmo minuto, mando e força. Para estimar o efeito do vermelho no resultado (H1 e H2), portanto, o placar no momento precisa entrar como controle. Caso contrário, o efeito fica superestimado.

== H5: minuto e posição

#let h5_ad = h5_teste("H5 aderência: vermelhos por faixa × exposição (todos)")
*Minuto.* A taxa de vermelhos cresce ao longo do jogo, de #fmt(taxa_faixa("0–15").taxa_90, d: 3) por 90 minutos na faixa 0–15 para #fmt(taxa_faixa("76–90+").taxa_90, d: 3) na faixa 76–90+ (qui-quadrado contra a exposição, p #pfmt(h5_ad.p_holm)#[;] V de Cramér = #fmt(h5_ad.valor_efeito)). O padrão vale para vermelhos diretos e para 2º amarelo. O 2º amarelo é praticamente ausente nos primeiros 15 minutos, como esperado. A taxa nos acréscimos do 2º tempo, #fmt(taxa_fina("90+").taxa_90, d: 2) por 90 minutos, está inflada pela subestimação da duração e não deve ser lida isoladamente. Um modelo de tendência linear por faixa se ajusta mal (dispersão de #fmt(h5_tendencia.at(0).dispersao_pearson, d: 1)), porque o crescimento acelera no fim. Por isso, a evidência principal são as taxas por faixa.

#figure(
  image("/reports/figures/h5_taxa_faixa.png", width: 85%),
  caption: [Vermelhos por time a cada 90 minutos, por faixa de minuto e tipo de vermelho, com IC 95% bootstrap. Fonte: `reports/tabelas/h5_taxas_faixa.csv`.],
)

#let z = formacao("Zagueiro")
#let g = formacao("Goleiro")
#let pos_ad = h5_teste("H5 aderência: posição dos vermelhos × formação (principal)")
*Posição em relação à formação.* Sem escalação, a referência é a formação de cada jogo (de 2015 a 2024): numa 4-2-3-1, por exemplo, espera-se que 4 dos 11 jogadores sejam defensores. Os zagueiros (que na base incluem laterais) recebem #fmt(z.razao_obs_esp) vez o esperado (IC 95%: #fmt(z.ic95_inf)–#fmt(z.ic95_sup)), e os goleiros, #fmt(g.razao_obs_esp) (IC 95%: #fmt(g.ic95_inf)–#fmt(g.ic95_sup)). A distribuição difere da esperada (p #pfmt(pos_ad.p_holm)#[;] V de Cramér = #fmt(pos_ad.valor_efeito)). O resultado de meio-campo e atacante, por outro lado, *depende de como os pontas são classificados*: o atacante fica acima do esperado na referência principal (#fmt(formacao("Atacante").razao_obs_esp)) e bem abaixo quando os pontas contam como ataque (#fmt(formacao("Atacante", variante: "sensibilidade — pontas no ataque").razao_obs_esp)). Para essas duas posições, não há conclusão.

#let zm = par_posicoes("Zagueiro", "Meio-campo")
#let ind = h5_teste("H5 independência: posição × expulsão")
*Gravidade entre os punidos.* Entre os atletas que receberam algum cartão na partida, o zagueiro foi expulso em #pct(cartao("Zagueiro").proporcao)% dos casos (IC 95% de Wilson: #pct(cartao("Zagueiro").ic95_inf)–#pct(cartao("Zagueiro").ic95_sup)%) e o meio-campo em #pct(cartao("Meio-campo").proporcao)% (#pct(cartao("Meio-campo").ic95_inf)–#pct(cartao("Meio-campo").ic95_sup)%). A diferença é significativa (p de Holm #pfmt(zm.p_holm)), mas o efeito é pequeno (V de Cramér = #fmt(ind.valor_efeito)).

#let pf = h5_teste("H5 independência: posição × faixa")
*Posição × minuto.* Não há associação entre posição e faixa de minuto do vermelho (p #pfmt(pf.p_holm)#[;] V de Cramér = #fmt(pf.valor_efeito)). Todas as posições se concentram no fim do jogo da mesma forma. A tabela tem #pf.obs, o que pede cautela com o goleiro.

*Conclusão.* A H5 é sustentada para o minuto e, em parte, para a posição: zagueiros acima e goleiros abaixo do esperado. Como posição e minuto não interagem, um protocolo disciplinar pode tratar os dois critérios separadamente. A base não distingue volantes dentro de meio-campo.

= Efeito do Vermelho no Resultado <efeito>

Os modelos estão em `src/models.py` e `src/evaluate.py`, e as tabelas em `reports/tabelas/h1_*.csv` e `modelos_*.csv`. A população do efeito são as partidas cujo primeiro vermelho ocorreu até o minuto 90 regulamentar. O corte usa o minuto do vermelho, que é conhecido no momento, e nunca o que aconteceu depois dele, o que criaria viés de seleção.

== Métodos avaliados

*Modelo de estado do jogo.* Cada partida é fotografada em minutos fixos (0, 5, …, 85), os _landmarks_. Em cada um, o modelo estima a probabilidade de vitória, empate e derrota do mandante a partir do estado naquele momento: saldo (também escalado pela raiz do tempo restante), tempo restante, diferença de Elo e sua interação com o tempo restante, e o número de vermelhos de cada lado com e sem interação com o tempo restante. Partidas sem vermelho no mesmo estado servem de comparação, e o placar no momento fica controlado, como exige a H3. O *custo da expulsão* é a variação de pontos esperados do time punido, ΔPE = PE(com o vermelho) − PE(sem), em que PE = 3·P(vitória) + P(empate). Os intervalos vêm de 2.000 simulações dos parâmetros com covariância robusta agrupada por partida.

*Multinomial × ordinal.* O plano previa a logística ordinal como principal. A suposição de chances proporcionais, porém, não se sustentou: o AIC da ordinal ficou #fmt(estado_ajuste("ordinal").delta_aic, d: 0) pontos acima do da multinomial, e no teste temporal a log-loss da ordinal foi maior em #val_ic(dif_ll("logística ordinal"), "dif_log_loss_vs_multinomial", d: 4). Por isso a *multinomial é o modelo principal*, e a ordinal fica como comparação.

*Pareamento.* Cada time expulso é comparado a #h1_equilibrio.controles_por_tratado_min.replace(".0", "")–5 times de outras partidas que, no mesmo minuto, tinham o mesmo mando e o mesmo saldo (−2 a +2), ainda não tinham levado vermelho e tinham o Elo mais próximo. O controle pode levar vermelho depois, porque excluir esses casos seria usar o futuro. A medida é o ATT, a diferença média de pontos finais entre expulsos e controles, com IC bootstrap. O equilíbrio ficou bom: diferença padronizada de Elo de #fmt(h1_equilibrio.diferenca_padronizada_elo, d: 3).

*Gols.* Uma regressão de Poisson sobre a tabela de exposição estima a taxa de gols marcados com um jogador a menos ou a mais, controlando faixa de minuto, saldo, mando e Elo. Como robustez, há um modelo com efeito fixo de partida, que compara o antes e o depois dentro do mesmo jogo.

== H1: o custo da expulsão

#let h1m = h1_teste("H1 ΔPE de um vermelho no minuto 45, empatando (média dos lados) [multinomial]")
#let att_todos = att("todos")
O vermelho reduz os pontos do time punido nos três métodos. No modelo de estado, um vermelho no intervalo (minuto 45), com o jogo empatado, custa #val_ic(h1m, "valor_efeito") ponto esperado (p de Holm #pfmt(h1m.p_holm)). No pareamento, com #att_todos.n_tratados expulsões, o ATT é de #val_ic(att_todos, "att") ponto por partida (p de Holm #pfmt(h1_teste("H1 pareamento").p_holm)). Os expulsos fizeram em média #fmt(att_todos.pontos_tratados) ponto, e seus controles, #fmt(att_todos.pontos_controles).

#figure(
  image("/reports/figures/h1_custo_minuto.png", width: 95%),
  caption: [Custo da expulsão em pontos esperados do time punido, por minuto, placar no momento e lado punido (multinomial, IC 95%). As pontas iniciais das curvas de perdendo e vencendo são extrapolação, pois esses placares não ocorrem no início. Fonte: `reports/tabelas/h1_custo_minuto.csv`.],
)

== H2: o custo depende do minuto?

#let h2m = h1_teste("H2 ΔPE(min 15) − ΔPE(min 75), empatando (média dos lados) [multinomial]")
#let h2w = h1_teste("H2 Wald: custo não depende do tempo restante [multinomial]")
#let h2o = h1_teste("H2 ΔPE(min 15) − ΔPE(min 75), empatando (média dos lados) [ordinal]")
A resposta depende do método. No pareamento, o custo cai ao longo do jogo: de #val_ic(att("faixa 16–30"), "att") ponto para expulsões entre os minutos 16 e 30, para #val_ic(att("faixa 76–90"), "att") entre 76 e 90. No modelo multinomial, as interações com o tempo restante são significativas (Wald, p de Holm #pfmt(h2w.p_holm)). Com o jogo empatado, porém, a diferença de custo entre os minutos 15 e 75 é de #val_ic(h2m, "valor_efeito"), sem significância (p de Holm #pfmt(h2m.p_holm)). Na ordinal, a mesma diferença é #fmt(h2o.valor_efeito) (p #pfmt(h2o.p_valor), sem correção). Os primeiros 15 minutos têm só #att("faixa 0–15").n_tratados expulsões, com IC de #fmt(att("faixa 0–15").ic95_inf) a #fmt(att("faixa 0–15").ic95_sup), e não permitem conclusão. A H2 é sustentada em parte: o custo existe em todo o jogo, mas a forma da queda ainda é incerta.

#figure(
  image("/reports/figures/h1_pareamento.png", width: 80%),
  caption: [ATT do pareamento por faixa de minuto da expulsão, com IC 95% bootstrap. Fonte: `reports/tabelas/h1_pareamento_att.csv`.],
)

== H4: mandante × visitante

#let h4d = h1_teste("H4 pareamento: ATT mandante − ATT visitante")
#let h4m = h1_teste("H4 ΔPE mandante punido − ΔPE visitante punido (min 45, empatando) [multinomial]")
No pareamento, o mandante expulso perde #val_ic(att("lado mandante"), "att") ponto, e o visitante, #val_ic(att("lado visitante"), "att"). A diferença, #fmt(h4d.valor_efeito), é significativa no limite (p de Holm #pfmt(h4d.p_holm)). Parte dela é efeito teto: os controles do mandante fizeram #fmt(att("lado mandante").pontos_controles) ponto, e os do visitante, #fmt(att("lado visitante").pontos_controles), então o mandante tem mais a perder. No modelo de estado, a diferença não é significativa (#fmt(h4m.valor_efeito)#[;] p de Holm #pfmt(h4m.p_holm)). A H4 não tem conclusão firme.

== Gols após a expulsão

#let gi = gols_irr("todos", "vantagem[inferior]")
#let gs = gols_irr("todos", "vantagem[superior]")
#let fei = gols_irr("efeito fixo de partida (partidas com vermelho)", "vantagem[inferior]")
#let fes = gols_irr("efeito fixo de partida (partidas com vermelho)", "vantagem[superior]")
Com um jogador a menos, o time marca gols a uma taxa #fmt(gi.irr) vez a da igualdade numérica (IC 95%: #fmt(gi.ic95_inf)–#fmt(gi.ic95_sup)). Com um a mais, a taxa é #fmt(gs.irr) vez (IC 95%: #fmt(gs.ic95_inf)–#fmt(gs.ic95_sup)). No modelo com efeito fixo de partida, os valores são #fmt(fei.irr) e #fmt(fes.irr). Ou seja, a expulsão pesa mais pelos gols sofridos a mais do que pelos gols marcados a menos.

== Comparação de modelos e avaliação

Todos os modelos preveem o resultado final a partir do estado em cada landmark. A validação é temporal: treino em 2014–2021 e teste em 2022–2024, simulando o uso real (treina-se com o passado e aplica-se ao futuro). Os hiperparâmetros da random forest e do LightGBM foram escolhidos por log-loss em validação cruzada de 5 grupos *por partida* dentro do treino, para que landmarks do mesmo jogo nunca fiquem nos dois lados. Os baselines obrigatórios são "sempre mandante" e as frequências históricas. A acurácia sozinha é inadequada por causa dos empates, e por isso as métricas principais são log-loss e RPS (_ranked probability score_), próprio para resultados ordenados.

#let linha_m(nome) = {
  let m = metrica(nome)
  (nome, fmt_ou(m.log_loss), fmt_ou(m.brier), fmt_ou(m.rps), fmt_ou(m.auc_ovr), fmt_ou(m.acuracia), fmt_ou(m.f1_macro))
}
#figure(
  table(
    columns: (1fr, auto, auto, auto, auto, auto, auto),
    align: (left, right, right, right, right, right, right),
    table.header[*Modelo*][*Log-loss*][*Brier*][*RPS*][*AUC*][*Acurácia*][*F1 macro*],
    ..("sempre mandante", "frequências históricas", "Elo pré-jogo", "logística ordinal",
       "logística multinomial", "random forest", "LightGBM").map(linha_m).flatten(),
  ),
  caption: [Métricas no teste (2022–2024, todos os landmarks). "Sempre mandante" não produz probabilidades. Fonte: `reports/tabelas/modelos_metricas.csv`.],
)

#let rf = dif_ll("random forest")
A multinomial tem a menor log-loss no teste. A random forest fica próxima, com diferença de #val_ic(rf, "dif_log_loss_vs_multinomial", d: 4), intervalo que inclui zero. O LightGBM fica atrás, com diferença de #val_ic(dif_ll("LightGBM"), "dif_log_loss_vs_multinomial", d: 4). Como a multinomial é tão boa quanto o melhor modelo flexível e é interpretável, ela é o modelo de decisão. Entre os landmarks com vermelho, as árvores ficam levemente à frente (log-loss #fmt(metrica("LightGBM", sub: "landmarks com vermelho").log_loss, d: 4) do LightGBM contra #fmt(metrica("logística multinomial", sub: "landmarks com vermelho").log_loss, d: 4) da multinomial).

#figure(
  image("/reports/figures/modelos_calibracao.png", width: 90%),
  caption: [Curva de calibração no teste para vitória do mandante e empate. Fonte: `src/evaluate.py`.],
)

*Estabilidade da curva de custo.* Ajustada só no treino, a multinomial estima #fmt(curva(0, 0, "visitante").at("logística multinomial")) ponto para o visitante expulso no início com o jogo empatado. Com todos os dados, estima #fmt(custo(0, 0, "visitante").delta_pe). Há poucos vermelhos para identificar bem esses coeficientes. Por isso, para a recomendação, a evidência mais robusta é o ATT do pareamento, e a curva do modelo serve para mostrar o formato do custo ao longo do jogo.

= Estado atual e próximos passos

Concluído: download, limpeza, anotação manual das posições, atributos derivados (eventos, estados, exposição, landmarks, Elo), testes de H3 e H5, modelos do efeito (H1, H2, H4) e comparação de modelos com validação temporal. Pendente: insights no formato exigido, com métricas de acompanhamento e critérios de sucesso; documento final no template SBC; dashboard com o custo da expulsão por minuto.

#bibliography("referencias.bib", style: "association-for-computing-machinery")
