"""Aba 4: Parecer Técnico Executivo e Insights Acionáveis do Edital."""
import streamlit as st

from src.dashboard.data_loader import (
    calcular_pontos_esperados,
    obter_att_pareamento,
    obter_dinamica_gols,
    predizer_probabilidades_multinomial,
)


def render_tab_advisor(
    minuto: float,
    saldo_time: int,
    lado_time: str,
    elo_diff: float,
    posicao_advertida: str,
):
    """Renderiza a aba de parecer executivo, insights padronizados e relatório operacional."""
    st.markdown("### Parecer Técnico Executivo e Insights Acionáveis")
    st.markdown(
        "Apresentação dos insights acionáveis segundo o modelo estrito exigido pela UFAL, "
        "além de um assistente de parecer técnico automatizado baseado no cenário atual do jogo."
    )

    st.markdown("#### 1. Três Insights Acionáveis (Modelo Obrigatório da Disciplina)")

    with st.expander("Insight 1: Zona de Risco Disciplinar e Prevenção Focalizada", expanded=True):
        st.markdown(
            """
            > **Percebemos que** equipes em desvantagem no placar apresentam taxa de expulsão **39% maior** que em empate 
            (IRR = 1,39, IC 95%: 1,19–1,64, p < 0,001), concentrada especificamente quando estão perdendo por 1 gol 
            (IRR = 1,48, IC 95%: 1,26–1,75, p < 0,001), e que zagueiros/laterais recebem **16% mais cartões vermelhos** 
            do que o esperado pela formação tática (razão obs/esp = 1,16, IC 95%: 1,08–1,25, p < 0,001). 
            **Isso sugere que** a urgência do resultado gera desorganização emocional e tática, expondo os defensores 
            a faltas de contenção de alto risco de segundo cartão amarelo no segundo tempo. 
            **Por isso, recomendamos** a implementação do *Protocolo de Zona de Risco Disciplinar*, estabelecendo orientação 
            obrigatória no vestiário aos defensores amarelados e sua substituição preventiva prioritária caso a equipe 
            esteja perdendo por 1 gol até os 60 minutos de partida. 
            **A decisão foi sustentada por** razão de taxas ajustada de Poisson (IRR = 1,48 para saldo -1) e teste de 
            aderência binomial para defensores (p corrigido por Holm = 0,00045). 
            **Após** uma temporada completa (38 rodadas), o sucesso da ação pode ser avaliado por **número total de expulsões 
            sofridas na temporada** e acompanhado por **cartões amarelos recebidos por zagueiros no 2º tempo**. 
            **A ação será considerada bem-sucedida se** a equipe limitar suas expulsões a no máximo **3 cartões vermelhos no campeonato**, 
            representando uma redução de pelo menos 38% em relação à média histórica da Série A (4,9 vermelhos por time/ano).
            """
        )

    with st.expander("Insight 2: Reação Tática com 10 em Campo — Prioridade Defensiva", expanded=True):
        st.markdown(
            """
            > **Percebemos que** atuar com um jogador a menos reduz a taxa de gols marcados em **37%** (IRR = 0,63, IC 95%: 0,54–0,72, p < 10⁻⁹), 
            mas eleva a taxa de gols sofridos em **53%** no modelo geral (IRR = 1,53, IC 95%: 1,39–1,67, p < 10⁻¹⁹) e em **99%** no modelo 
            com efeito fixo intra-partida (IRR = 1,99, IC 95%: 1,73–2,30). 
            **Isso sugere que** a punição esportiva da inferioridade numérica não decorre precipuamente da esterilidade ofensiva, 
            mas da vulnerabilidade crítica gerada nos espaços defensivos e sobrecarga da linha de zaga. 
            **Por isso, recomendamos** a adoção imediata do *Plano de Recomposição Defensiva*, estruturando a equipe em bloco 
            baixo (formação 4-4-1 ou 5-3-1), fechando o corredor central e abrindo mão da pressão alta até os minutos finais da partida. 
            **A decisão foi sustentada por** modelos de Poisson com offset de minutos de exposição e efeito fixo de partida 
            (IRR de gols contra = 1,53 a 1,99). 
            **Após** uma temporada (38 rodadas), o sucesso da ação pode ser avaliado por **média de pontos conquistados em partidas 
            com expulsão própria** e acompanhado por **saldo de gols pós-expulsão por 90 minutos de inferioridade**. 
            **A ação será considerada bem-sucedida se** a média de pontos obtidos em jogos com expulsão atingir pelo menos **1,00 ponto por jogo**, 
            recuperando metade da perda média histórica decorrente do cartão vermelho (média observada de 0,85 pt contra 1,15 pt de controles pareados).
            """
        )

    with st.expander("Insight 3: Custo por Minuto e Janela de Substituição Preventiva", expanded=True):
        st.markdown(
            """
            > **Percebemos que** o custo de uma expulsão decresce acentuadamente ao longo dos minutos de partida: expulsões ocorridas entre 
            16–30 minutos custam em média **0,85 ponto esperado** (ATT = -0,85, IC 95%: -1,14 a -0,52, p < 10⁻⁶), caindo para **-0,46 ponto** 
            (31–45+ min), **-0,35 ponto** (46–60 min) e apenas **-0,12 ponto** no último quarto de hora (76–90 min, IC 95%: -0,20 a -0,03). 
            **Isso sugere que** o impacto negativo de atuar em desvantagem numérica é cumulativo no tempo restante, tornando expulsões precoces 
            desproporcionalmente devastadoras para o desfecho da partida. 
            **Por isso, recomendamos** instituir a diretriz técnica de substituição preventiva obrigatória para atletas advertidos com cartão amarelo 
            até os 60 minutos de jogo, mesmo tratando-se de titulares fundamentais, priorizando volantes e laterais. 
            **A decisão foi sustentada por** estimador de Pareamento Causal exato por minuto, saldo de gols e diferença de rating Elo (ATT = -0,85 no 1º tempo vs -0,12 no fim). 
            **Após** uma temporada (38 rodadas), o sucesso da ação pode ser avaliado por **frequência de expulsões sofridas antes dos 60 minutos** 
            e acompanhado por **minutos totais jogados por atletas sob advertência de cartão amarelo**. 
            **A ação será considerada bem-sucedida se** a equipe zerar (**0 expulsões**) o número de cartões vermelhos ocorridos antes dos 60 minutos de jogo ao longo de todo o campeonato nacional.
            """
        )

    st.markdown("---")

    st.markdown("#### 2. Gerador Automatizado de Parecer Tático em Tempo Real")
    st.caption("Síntese executiva formatada a partir das condições configuradas na barra lateral.")

    if lado_time == "mandante":
        saldo_m = float(saldo_time)
        elo_m = elo_diff
    else:
        saldo_m = -float(saldo_time)
        elo_m = -elo_diff

    p_antes = predizer_probabilidades_multinomial(minuto, saldo_m, elo_m, 0, 0)
    p_depois = predizer_probabilidades_multinomial(minuto, saldo_m, elo_m, 1 if lado_time == "mandante" else 0, 1 if lado_time == "visitante" else 0)

    pe_ant = calcular_pontos_esperados(p_antes, lado_time)
    pe_dep = calcular_pontos_esperados(p_depois, lado_time)
    d_pe = pe_dep - pe_ant

    att = obter_att_pareamento(minuto, lado=lado_time, saldo=saldo_time)
    gols = obter_dinamica_gols(lado=lado_time)
    irr_contra = gols["especifico"]["gols_contra_irr"]

    alerta_txt = (
        f"ALERTA DE SUBSTITUIÇÃO: O atleta na posição {posicao_advertida} deve ser substituído prioritariamente. "
        f"O custo de um segundo amarelo neste momento ({d_pe:.2f} pts) compromete gravemente o resultado da partida."
        if (minuto >= 45 and saldo_time <= 0 and posicao_advertida in ["Zagueiro", "Meio-campo"])
        else "CONDUTA PREVENTIVA: Manter o atleta em campo com orientação expressa para evitar faltas de transição em contra-ataques adversários."
    )

    faixa_num = att['faixa'].replace('faixa ', '')

    texto_parecer = f"""PARECER TÁTICO OPERACIONAL — COMISSÃO TÉCNICA
Data/Hora da Simulação: Em tempo real
Contexto de Jogo: Minuto {int(minuto)}' | Condição: {lado_time.capitalize()} | Placar: Saldo {saldo_time:+d} | Elo Diff: {elo_diff:+.0f}
Atleta Monitorado: Posição {posicao_advertida}

------------------------------------------------------------------------

1. Diagnóstico de Risco Imediato
- Custo Esperado de Expulsão (Delta PE): {d_pe:+.2f} pontos por partida (Modelo Multinomial ajustado).
- Referência Histórica Pareada (ATT): {att['att']:+.2f} pontos (Faixa {faixa_num} min, IC 95%: [{att['ic95_inf']:.2f}, {att['ic95_sup']:.2f}]).
- Impacto Defensivo: O adversário terá aumento de +{int((irr_contra - 1)*100)}% na taxa de gols marcados (IRR = {irr_contra:.2f}).

2. Probabilidade de Resultados
- Com 11 atletas: Vitória: {p_antes['P(V)']*100 if lado_time == 'mandante' else p_antes['P(D)']*100:.1f}% | Empate: {p_antes['P(E)']*100:.1f}% | Derrota: {p_antes['P(D)']*100 if lado_time == 'mandante' else p_antes['P(V)']*100:.1f}%
- Após eventual vermelho: Vitória: {p_depois['P(V)']*100 if lado_time == 'mandante' else p_depois['P(D)']*100:.1f}% | Empate: {p_depois['P(E)']*100:.1f}% | Derrota: {p_depois['P(D)']*100 if lado_time == 'mandante' else p_depois['P(V)']*100:.1f}%

3. Recomendação Operacional da Análise de Desempenho
{alerta_txt}
"""

    st.text_area("Pré-visualização do Parecer:", texto_parecer, height=260)

    st.download_button(
        label="Baixar Parecer Técnico (.md)",
        data=texto_parecer,
        file_name=f"parecer_tatico_minuto_{int(minuto)}_saldo_{saldo_time}.md",
        mime="text/markdown",
    )
