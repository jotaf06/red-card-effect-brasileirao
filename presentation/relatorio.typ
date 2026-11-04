#set document(title: "Quanto custa uma expulsão? Relatório de andamento", author: "José Felix")
#set page(paper: "a4", margin: 2.5cm, numbering: "1")
#set text(lang: "pt", size: 11pt)
#set par(justify: true)
#set heading(numbering: "1.")
#show link: underline

#let resumo = csv("/reports/tabelas/resumo_base.csv", row-type: dictionary)
#let valor(chave) = resumo.find(linha => linha.chave == chave).valor
#let n(chave) = {
  let s = valor(chave)
  if s.contains(".") { s.replace(".", ",") }
  else if s.len() > 3 { s.slice(0, s.len() - 3) + "." + s.slice(-3) }
  else { s }
}

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

O script `src/clean.py` lê `data/raw/`, que nunca é alterado, e grava tabelas limpas em `data/interim/` no formato parquet. O download e a conferência de linhas e colunas ficam em `src/download.py`.

*Minutos com acréscimo.* Valores como `45+2` são separados em `tempo`, `minuto_base`, `acrescimo`, `minuto_jogado` (base mais acréscimo) e `ordem` (base mais acréscimo dividido por 100). A chave `ordem` garante que `45+3` venha antes de `46`.

*Temporada.* A coluna `temporada` usa o ano da data, com uma exceção: os jogos de 2021 anteriores a 1º de março de 2021 pertencem à temporada 2020, que terminou em 25/02/2021. A regra funciona porque as temporadas de 2020 e 2021 não se sobrepõem, e cada uma fica com 380 jogos.

*Validação do número de jogos.* De 2006 a 2024 cada temporada deve ter 380 jogos. A temporada 2016 tem 379, pois a rodada 38 tem 9 jogos, e isso gera um aviso em vez de erro. As temporadas de 2003 a 2005 têm formato diferente (24 times) e ficam fora dessa regra.

*Resultado da partida.* `resultado_mandante` (V, E ou D) é derivado do placar. A coluna `vencedor` diverge do placar em uma partida de 2005 (`partida_id` 1114), registrada como empate com placar de 0 a 1, e essa divergência é avisada na execução. Foi escolhido o placar por ser validado contra os gols.

*Estatísticas ausentes.* Linhas com chutes, passes e faltas todos iguais a zero são ausências disfarçadas, e viram valores nulos em todas as colunas de estatística, preservando os cartões. Foram #n("estatisticas_anuladas_total") linhas, das quais #n("estatisticas_anuladas_2015_2023") dentro de 2015–2023, o período em que as estatísticas deveriam ser válidas. Posse de bola e precisão de passes, que vinham como texto (`"55%"`), foram convertidas para número.

*Posição nos cartões.* A variante `Zagueira` (22 linhas, todas do mesmo atleta) foi unificada em `Zagueiro`. Havia #n("posicao_nula_original") cartões sem posição, todos de 2014 a 2018. O preenchimento segue duas etapas, registradas na coluna `posicao_origem`:
+ *Imputação automática:* usa a posição do mesmo atleta em outros cartões, se ele tiver uma só posição, ou se a mais frequente cobrir pelo menos 80% dos seus registros. Foram imputadas #n("posicao_imputada") linhas. A posição na base parece ser a da partida e não fixa por atleta, e por isso o limiar de 80%.
+ *Levantamento manual:* 28 vermelhos sem posição segura foram listados em `data/manual/posicao_vermelhos.csv` para consulta à escalação do jogo. Posições manuais prevalecem sobre as imputadas. Até aqui, #n("posicao_manual") foram preenchidas.

Restam #n("posicao_nula_final") cartões sem posição, dos quais #n("vermelhos_posicao_nula_final") vermelhos. A análise por posição (H5) deve reportar essa categoria à parte e testar a sensibilidade com e sem as posições imputadas.

== Validações

- Os gols por lado, em `gols`, batem com o placar final em todas as partidas de 2014 a 2024.
- Todo evento de gol ou cartão tem `partida_id` presente em `partidas`.
- `estatisticas` tem exatamente duas linhas por partida.

Pendências de qualidade: padronização de nomes de arenas (168 valores distintos, ainda não verificados) e escolha de uso para técnico e formação, que têm cerca de 53–57% de nulos.

= Estado atual e próximos passos

Concluído: `download.py`, `clean.py` e `resumo_base.py` (que gera os números deste relatório). Pendente: preenchimento manual de posições, `features.py` (eventos, placar no momento, Elo), estatística descritiva e testes de hipótese, modelos do efeito, avaliação e insights. As seções de métodos, métricas, resultados e conclusão do documento final serão escritas quando houver resultados.

#bibliography("referencias.bib", style: "association-for-computing-machinery")
