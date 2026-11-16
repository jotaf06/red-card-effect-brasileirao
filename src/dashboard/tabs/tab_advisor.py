"""Aba 4: Parecer Técnico Executivo e Insights Acionáveis do Edital."""
import streamlit as st

from src.dashboard.data_loader import (
    calcular_pontos_esperados,
    formatar_decimal as _fmt_pt,
    formatar_p_valor,
    obter_att_pareamento,
    obter_dados_insights,
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

    ins = obter_dados_insights()
    metas = ins["metas"]
    liga = ins["liga"]
    conv = ins["conversao"]
    testes = ins["testes"]
    att_df = ins["att"]
    gols_todos = ins["gols_todos"]
    gols_fixo = ins["gols_fixo"]
    zag_form = ins["formacao"].loc["Zagueiro"]
    irr_perd = ins["irr_perdendo"]
    irr_m1 = ins["irr_saldo_m1"]

    a75 = att_df.loc["até 75'"]
    d75 = att_df.loc["depois de 75'"]
    att_todos = att_df.loc["todos"]
    att_2o = att_df.loc["tipo 2o_amarelo"]
    razao_75 = abs(float(a75["att"])) / abs(float(d75["att"]))
    pct_2o_am = float(att_2o["n_tratados"]) / float(att_todos["n_tratados"]) * 100
    m1 = metas.loc["I1"]

    with st.expander("Insight 1: O Relógio — Prevenir o 2º Amarelo até os 75'", expanded=True):
        st.markdown(
            f"""
            > **Percebemos que** uma expulsão até os **75'** custa em média **{_fmt_pt(-float(a75['att']))} ponto esperado**
            (ATT = {_fmt_pt(float(a75['att']))}, IC 95%: {_fmt_pt(float(a75['ic95_inf']))} a {_fmt_pt(float(a75['ic95_sup']))}),
            **{_fmt_pt(razao_75, 1)}×** o custo de uma expulsão após os 75' (ATT = {_fmt_pt(float(d75['att']))}, IC 95%:
            {_fmt_pt(float(d75['ic95_inf']))} a {_fmt_pt(float(d75['ic95_sup']))}), e que **{round(pct_2o_am)}%** das expulsões
            pareadas decorrem de **2º cartão amarelo** (agravadas quando o time está perdendo: IRR = {_fmt_pt(float(irr_perd['irr']))} no geral e
            {_fmt_pt(float(irr_m1['irr']))} com saldo -1).
            **Isso sugere que** o atleta já advertido é o principal risco disciplinar evitável — e o minuto da partida define a gravidade do prejuízo.
            **Por isso, recomendamos** instituir o *Protocolo de Zona de Risco até os 75'*: atletas advertidos expostos a faltas táticas de transição
            passam a ser candidatos prioritários à substituição preventiva ou contenção direta até superar os 75 minutos.
            **A decisão foi sustentada por** pareamento causal exato por minuto, placar, mando e Elo (ATT até 75' = {_fmt_pt(float(a75['att']))} vs após 75' = {_fmt_pt(float(d75['att']))}).
            **Após** uma temporada completa ({int(m1['periodo_jogos'])} jogos), o sucesso da ação pode ser avaliado por **número de expulsões por 2º amarelo até os 75'**
            (média da liga: **{_fmt_pt(float(m1['liga_media']), 1)}**, mediana **{_fmt_pt(float(m1['liga_mediana']), 0)}**) e acompanhado por **pontos perdidos estimados por expulsões**
            (média da liga: {_fmt_pt(float(liga.loc['pontos_perdidos_estimados', 'media']))} pt/ano).
            **A ação será considerada bem-sucedida se** a equipe não sofrer **nenhuma ({int(m1['meta'])}) expulsão por 2º amarelo até os 75'**
            ({m1['regra']}; um time médio cumpre essa meta por acaso em {round(float(m1['chance_acaso']) * 100)}% das temporadas).
            """
        )

    cz_1t = float(conv.loc["zagueiro · 1º tempo", "taxa"]) * 100
    cd_1t = float(conv.loc["demais · 1º tempo", "taxa"]) * 100
    cz_2t = float(conv.loc["zagueiro · 2º tempo", "taxa"]) * 100
    cd_2t = float(conv.loc["demais · 2º tempo", "taxa"]) * 100
    tz1 = testes.loc["I2 conversão: zagueiro 1º tempo × demais 1º tempo"]
    tz12 = testes.loc["I2 conversão: zagueiro 1º tempo × zagueiro 2º tempo"]
    tz2 = testes.loc["I2 conversão: zagueiro 2º tempo × demais 2º tempo"]
    m2 = metas.loc["I2"]

    with st.expander("Insight 2: A Posição — Zagueiro Advertido no 1º Tempo", expanded=True):
        st.markdown(
            f"""
            > **Percebemos que** um zagueiro advertido no **1º tempo** é expulso por 2º amarelo em **{_fmt_pt(cz_1t)}%** dos casos,
            contra **{_fmt_pt(cd_1t)}%** nas demais posições (razão **{_fmt_pt(float(tz1['valor_efeito']))}×**, p de Holm {formatar_p_valor(float(tz1['p_holm']))});
            no 2º tempo não há diferença significativa ({_fmt_pt(cz_2t)}% vs {_fmt_pt(cd_2t)}%, p {formatar_p_valor(float(tz2['p_holm']))}).
            Além disso, zagueiros sofrem **{round((float(zag_form['razao_obs_esp']) - 1) * 100)}% mais cartões vermelhos** que o esperado pela formação tática
            (razão obs/esp = {_fmt_pt(float(zag_form['razao_obs_esp']))}, IC 95%: {_fmt_pt(float(zag_form['ic95_inf']))}–{_fmt_pt(float(zag_form['ic95_sup']))},
            p de Holm {formatar_p_valor(float(zag_form['p_holm']))}).
            **Isso sugere que** o maior gargalo disciplinar ocorre ao combinar um zagueiro já amarelado com todo o 2º tempo ainda por jogar.
            **Por isso, recomendamos** avaliar obrigatoriamente **no intervalo** a substituição ou ajuste de encaixe/cobertura do zagueiro advertido no 1º tempo,
            aliado a treinos específicos de tempo de bote e cobertura da última linha.
            **A decisão foi sustentada por** testes *z* de proporções com correção de Holm (1º tempo vs demais: {_fmt_pt(float(tz1['valor_efeito']))}×; 1º tempo vs 2º tempo do zagueiro: {_fmt_pt(float(tz12['valor_efeito']))}×, p {formatar_p_valor(float(tz12['p_holm']))}) e teste binomial de formação (H5).
            **Após** uma temporada completa ({int(m2['periodo_jogos'])} jogos), o sucesso da ação pode ser avaliado por **cartões vermelhos de zagueiros na temporada**
            (mediana da liga: **{_fmt_pt(float(m2['liga_mediana']), 0)}**, média **{_fmt_pt(float(m2['liga_media']))}**) e acompanhado por **expulsões de zagueiros advertidos no 1º tempo**
            (liga: {_fmt_pt(cz_1t)}% em ≈ {_fmt_pt(float(liga.loc['zagueiros_advertidos_1t', 'media']), 0)} ocorrências/ano).
            **A ação será considerada bem-sucedida se** a equipe registrar no máximo **{int(m2['meta'])} cartão vermelho de zagueiro** na temporada
            ({m2['regra']}; chance ao acaso de {round(float(m2['chance_acaso']) * 100)}%).
            """
        )

    gs = gols_todos.loc["vantagem[superior]"]
    gi = gols_todos.loc["vantagem[inferior]"]
    gs_ef = gols_fixo.loc["vantagem[superior]"]
    m3 = metas.loc["I3"]

    with st.expander("Insight 3: Com 10 em Campo — Prioridade Defensiva e Plano Pré-Treinado", expanded=True):
        st.markdown(
            f"""
            > **Percebemos que** atuar com um jogador a menos eleva a taxa de **gols sofridos em {round((float(gs['irr']) - 1) * 100)}%**
            (IRR = {_fmt_pt(float(gs['irr']))}, IC 95%: {_fmt_pt(float(gs['ic95_inf']))}–{_fmt_pt(float(gs['ic95_sup']))}; e IRR = {_fmt_pt(float(gs_ef['irr']))}
            no modelo intra-partida com efeito fixo, IC 95%: {_fmt_pt(float(gs_ef['ic95_inf']))}–{_fmt_pt(float(gs_ef['ic95_sup']))}), enquanto a taxa de
            **gols marcados cai {round((1 - float(gi['irr'])) * 100)}%** (IRR = {_fmt_pt(float(gi['irr']))}, IC 95%: {_fmt_pt(float(gi['ic95_inf']))}–{_fmt_pt(float(gi['ic95_sup']))}).
            **Isso sugere que** a perda de pontos com 10 atletas decorre sobretudo da vulnerabilidade defensiva após a expulsão — a prioridade prática deve ser não sofrer gols.
            **Por isso, recomendamos** adotar um *Plano Tático Pré-Treinado para Inferioridade Numérica*, preservando a linha defensiva em bloco compacto (4-4-1 ou 5-3-1),
            abdicando de um atacante e acionando a reorganização imediatamente após o vermelho.
            **A decisão foi sustentada por** regressões de Poisson com offset pelos minutos de exposição e modelo intra-partida com efeito fixo.
            **Após** **2 temporadas ({int(m3['periodo_jogos'])} jogos)** *(janela necessária porque cada equipe atua em mediana apenas {_fmt_pt(float(liga.loc['minutos_com_menos', 'mediana']), 1)} min/ano com um a menos)*,
            o sucesso da ação pode ser avaliado por **gols sofridos por 90 minutos em inferioridade numérica** (liga: **{_fmt_pt(float(m3['liga_media']))}** com 10 vs **{_fmt_pt(float(m3['taxa_com_11']))}** com 11)
            e acompanhado por **gols marcados com um a menos**.
            **A ação será considerada bem-sucedida se** a taxa de gols sofridos por 90' com 10 cair para no máximo **{_fmt_pt(float(m3['meta']))}**
            ({m3['regra']}; chance ao acaso em 2 temporadas de {round(float(m3['chance_acaso']) * 100)}%).
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

    if posicao_advertida == "Zagueiro" and minuto <= 45:
        alerta_txt = (
            f"ALERTA DO INTERVALO (Insight 2): Zagueiro advertido no 1º tempo tem quase o dobro de conversão para 2º amarelo "
            f"({_fmt_pt(cz_1t)}% vs {_fmt_pt(cd_1t)}%). Avaliar substituição ou ajuste de cobertura antes do início do 2º tempo "
            f"(custo estimado neste cenário: {d_pe:.2f} pt)."
        )
    elif minuto <= 75 and saldo_time <= 0 and posicao_advertida in ["Zagueiro", "Meio-campo"]:
        alerta_txt = (
            f"ALERTA DE SUBSTITUIÇÃO (Insight 1): O atleta na posição {posicao_advertida} está dentro da janela de alto custo (≤ 75'). "
            f"O custo estimado de um segundo amarelo neste momento ({d_pe:.2f} pt) recomenda troca preventiva prioritária."
        )
    elif minuto > 75:
        alerta_txt = (
            f"ORIENTAÇÃO DE RETA FINAL: Após os 75', o custo marginal médio cai para {_fmt_pt(abs(att['depois_75']['att']))} pt; "
            "manter organização defensiva e instruir o atleta a evitar faltas táticas de segundo amarelo."
        )
    else:
        alerta_txt = "CONDUTA PREVENTIVA: Manter o atleta em campo com orientação expressa para evitar faltas de transição em contra-ataques adversários."

    faixa_num = att["faixa"].replace("faixa ", "")

    texto_parecer = f"""PARECER TÁTICO OPERACIONAL — COMISSÃO TÉCNICA
Data/Hora da Simulação: Em tempo real
Contexto de Jogo: Minuto {int(minuto)}' | Condição: {lado_time.capitalize()} | Placar: Saldo {saldo_time:+d} | Elo Diff: {elo_diff:+.0f}
Atleta Monitorado: Posição {posicao_advertida}

------------------------------------------------------------------------

1. Diagnóstico de Risco Imediato
- Custo Esperado de Expulsão (Delta PE): {d_pe:+.2f} pontos por partida (Modelo Multinomial ajustado).
- Referência Histórica Pareada (ATT): {att['att']:+.2f} pontos (Faixa {faixa_num} min, IC 95%: [{att['ic95_inf']:.2f}, {att['ic95_sup']:.2f}]; média até 75': {att['ate_75']['att']:+.2f} pt).
- Impacto Defensivo: O adversário terá aumento de +{round((irr_contra - 1)*100)}% na taxa de gols marcados (IRR = {irr_contra:.2f}).

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
