"""Aba 2: Monitor da Zona de Risco Disciplinar e Alertas de Substituição."""
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from src.dashboard.config import CORES
from src.dashboard.data_loader import carregar_tabela, obter_dados_posicao


def calcular_nivel_risco(minuto: float, saldo_time: int, posicao: str) -> tuple[str, str, str, str]:
    """Calcula a classificação de risco e a recomendação de substituição baseada no cenário."""
    if saldo_time == -1 and minuto >= 45 and posicao in ["Zagueiro", "Meio-campo"]:
        return (
            "CRÍTICO",
            CORES["vermelho_alerta"],
            "Desvantagem mínima no placar, segundo tempo e defensor amarelado. "
            "Risco estatístico de expulsão 48% superior ao normal (IRR = 1,48, p < 0,001).",
            "SUBSTITUIÇÃO PREVENTIVA IMEDIATA: Efetuar a troca do atleta advertido até os 60 minutos.",
        )
    elif saldo_time < 0 and minuto >= 40:
        return (
            "ALTO",
            "#ff922b",
            "Equipe em desvantagem no placar entrando na fase de alta densidade de faltas e cartões (IRR = 1,39).",
            "PREPARAÇÃO DE TROCA: Orientar aquecimento do reserva imediato e alertar o atleta sobre risco de 2º amarelo.",
        )
    elif saldo_time == 0 and minuto >= 60 and posicao == "Zagueiro":
        return (
            "ALTO",
            "#ff922b",
            "Partida empatada nos últimos 30 minutos com zagueiro advertido (taxa de conversão para vermelho de 6,19%).",
            "SUBSTITUIÇÃO TÁTICA: Trocar o zagueiro amarelado para evitar que uma falta tática custe 0,44 ponto esperado.",
        )
    elif minuto >= 60:
        return (
            "MODERADO",
            CORES["amarelo_aviso"],
            "Entrada no terço final do jogo, onde ocorrem mais de 70% de todas as expulsões do campeonato.",
            "ORIENTAÇÃO DE CONTENÇÃO: Proibir atletas advertidos de efetuarem faltas táticas de transição.",
        )
    else:
        return (
            "BAIXO",
            CORES["verde_sucesso"],
            "Fase inicial de jogo com baixa taxa histórica de expulsões (apenas 0,018 vermelho/90 min).",
            "MONITORAMENTO NORMAL: Manter atleta em campo com orientação preventiva.",
        )


def render_tab_risk_monitor(minuto: float, saldo_time: int, posicao_advertida: str):
    """Renderiza a aba de monitoramento da zona de risco disciplinar e substituições preventivas."""
    st.markdown("### Monitor da Zona de Risco Disciplinar e Protocolo de Substituição")
    st.markdown(
        "Identifique antecipadamente quando um atleta com cartão amarelo está entrando "
        "na zona crítica de expulsão, embasado nos testes estatísticos de causalidade reversa (H3) e distribuição temporal (H5)."
    )

    nivel, cor, desc, acao = calcular_nivel_risco(minuto, saldo_time, posicao_advertida)

    cor_fundo = (
        "rgba(255, 107, 107, 0.16)"
        if nivel == "CRÍTICO"
        else (
            "rgba(255, 146, 43, 0.16)"
            if nivel == "ALTO"
            else (
                "rgba(252, 196, 25, 0.16)"
                if nivel == "MODERADO"
                else "rgba(81, 207, 102, 0.16)"
            )
        )
    )

    st.markdown(
        f"""
        <div style="background-color: {cor_fundo}; border-left: 6px solid {cor}; padding: 18px 22px; border-radius: 6px; margin-bottom: 20px; color: inherit;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <span style="font-size: 1.4rem; font-weight: 800; color: {cor};">STATUS DE RISCO: {nivel}</span>
                <span style="font-size: 0.95rem; font-weight: 600; color: inherit; opacity: 0.85;">Posição: {posicao_advertida} | Minuto: {int(minuto)}' | Placar: Saldo {saldo_time:+d}</span>
            </div>
            <p style="font-size: 1.05rem; color: inherit; margin-top: 10px; margin-bottom: 12px;"><b>Diagnóstico:</b> {desc}</p>
            <div style="background-color: rgba(134, 142, 150, 0.14); padding: 10px 14px; border-radius: 4px; border: 1px solid rgba(134, 142, 150, 0.3); color: inherit;">
                <span style="font-weight: 700; color: {cor};">RECOMENDAÇÃO OPERACIONAL:</span>
                <span style="font-weight: 600; color: inherit;"> {acao}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("#### Por que substituir antes dos 60 minutos?")
        st.caption(f"Custo médio da expulsão por faixa de minuto (Destaque para o minuto {int(minuto)}')")

        df_att = carregar_tabela("h1_pareamento_att")
        faixas_att = df_att[df_att["grupo"].str.startswith("faixa")].copy()
        faixas_att["rotulo"] = faixas_att["grupo"].str.replace("faixa ", "")

        if minuto <= 15:
            faixa_ativa = "0–15"
        elif minuto <= 30:
            faixa_ativa = "16–30"
        elif minuto <= 45:
            faixa_ativa = "31–45+"
        elif minuto <= 60:
            faixa_ativa = "46–60"
        elif minuto <= 75:
            faixa_ativa = "61–75"
        else:
            faixa_ativa = "76–90"

        cores_barras = []
        for rot in faixas_att["rotulo"]:
            if rot == faixa_ativa:
                cores_barras.append("#c92a2a" if saldo_time < 0 else "#1971c2")
            else:
                cores_barras.append("#ced4da")

        fig, ax = plt.subplots(figsize=(5.5, 3.8), dpi=120)
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#fcfcfc")

        barras = ax.bar(
            faixas_att["rotulo"],
            faixas_att["att"].abs(),
            color=cores_barras,
            alpha=0.95,
            edgecolor="#495057",
            linewidth=0.8,
        )

        ax.set_ylabel("Pontos Perdidos por Expulsão", fontsize=10, fontweight="bold", color="#495057")
        ax.set_xlabel("Momento da Expulsão (Minutos)", fontsize=10, fontweight="bold", color="#495057")
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.set_ylim(0, 1.25)

        for b, rot in zip(barras, faixas_att["rotulo"]):
            h = b.get_height()
            if rot == faixa_ativa:
                ax.annotate(f"Atual: -{h:.2f} pts", xy=(b.get_x() + b.get_width() / 2, h), xytext=(0, 5),
                            textcoords="offset points", ha="center", va="bottom", fontsize=9, fontweight="bold",
                            color="#c92a2a" if saldo_time < 0 else "#1971c2")
            else:
                ax.annotate(f"-{h:.2f}", xy=(b.get_x() + b.get_width() / 2, h), xytext=(0, 3),
                            textcoords="offset points", ha="center", va="bottom", fontsize=8, color="#868e96")

        ax.axvline(x=3.5, color="#e03131", linestyle=":", linewidth=2, label="Barreira dos 60'")
        ax.legend(frameon=True, facecolor="#ffffff", fontsize=9)

        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

        st.caption(
            "Evidência: Uma expulsão entre os minutos 16–30 custa 0,85 ponto e, entre 46–60, custa 0,35 ponto. "
            "A partir dos 75', o prejuízo marginal cai para 0,12 ponto. Substituir preventivamente antes dos 60' evita a zona de maior perda."
        )

    with col_g2:
        st.markdown("#### Curva de Aceleração das Expulsões")
        fator_h3 = 1.48 if saldo_time == -1 else (1.39 if saldo_time < 0 else (0.77 if saldo_time > 0 else 1.0))

        minutos_grade = np.linspace(5, 90, 80)
        taxa_base = 0.015 * np.exp(0.038 * minutos_grade)
        taxa_ajustada = taxa_base * fator_h3

        fig2, ax2 = plt.subplots(figsize=(5.5, 3.8), dpi=120)
        fig2.patch.set_facecolor("#ffffff")
        ax2.set_facecolor("#fcfcfc")

        ax2.plot(minutos_grade, taxa_base, label="Taxa Média Histórica (Série A)", color="#868e96", linestyle="--", linewidth=1.8)
        ax2.plot(minutos_grade, taxa_ajustada, label=f"Taxa com Saldo {saldo_time:+d} (H3)", color="#e03131" if saldo_time < 0 else "#1971c2", linewidth=2.4)

        taxa_no_minuto = float(0.015 * np.exp(0.038 * minuto) * fator_h3)
        ax2.scatter([minuto], [taxa_no_minuto], color="#e03131" if saldo_time < 0 else "#1971c2", s=70, zorder=5)
        ax2.annotate(f"Minuto {int(minuto)}': {taxa_no_minuto:.3f} verm/90min", xy=(minuto, taxa_no_minuto), xytext=(10, 5),
                     textcoords="offset points", fontsize=8.5, fontweight="bold",
                     color="#e03131" if saldo_time < 0 else "#1971c2")

        ax2.set_ylabel("Taxa de Cartões Vermelhos / 90 min", fontsize=9.5, fontweight="bold", color="#495057")
        ax2.set_xlabel("Minutos de Jogo", fontsize=9.5, fontweight="bold", color="#495057")
        ax2.grid(True, linestyle="--", alpha=0.4)
        ax2.legend(frameon=True, facecolor="#ffffff", fontsize=8.5)

        plt.tight_layout()
        st.pyplot(fig2)
        plt.close(fig2)

        st.caption(
            f"Curva Dinâmica: A taxa esperada sobe para {taxa_no_minuto:.3f} vermelhos/90 min no minuto {int(minuto)}'. "
            f"Equipes em desvantagem sofrem um incremento de {int((fator_h3 - 1)*100)}% na probabilidade de expulsão."
        )

    st.markdown("---")

    st.markdown("#### Comparativo de Vulnerabilidade por Posição")
    st.caption(f"Destaque para a posição selecionada: {posicao_advertida}")

    df_pos = carregar_tabela("h5_posicao_cartao")
    posicoes_nomes = df_pos["posicao"].tolist()
    taxas_conv = (df_pos["proporcao"] * 100).tolist()

    cores_pos = []
    for p in posicoes_nomes:
        if p == posicao_advertida:
            cores_pos.append("#c92a2a" if p in ["Zagueiro", "Meio-campo"] else "#1971c2")
        else:
            cores_pos.append("#adb5bd")

    col_gp, col_infop = st.columns([1.2, 1.0])

    with col_gp:
        fig3, ax3 = plt.subplots(figsize=(5.5, 3.2), dpi=120)
        fig3.patch.set_facecolor("#ffffff")
        ax3.set_facecolor("#fcfcfc")

        barras_p = ax3.bar(posicoes_nomes, taxas_conv, color=cores_pos, alpha=0.95, edgecolor="#495057")
        ax3.set_ylabel("Conversão Amarelo para Vermelho (%)", fontsize=9, fontweight="bold", color="#495057")
        ax3.grid(axis="y", linestyle="--", alpha=0.4)
        ax3.set_ylim(0, 8.0)

        for bp, p_nome in zip(barras_p, posicoes_nomes):
            h = bp.get_height()
            is_sel = p_nome == posicao_advertida
            rot_texto = f"SELECIONADO: {h:.1f}%" if is_sel else f"{h:.1f}%"
            cor_t = "#c92a2a" if is_sel else "#495057"
            ax3.annotate(rot_texto, xy=(bp.get_x() + bp.get_width() / 2, h), xytext=(0, 4),
                         textcoords="offset points", ha="center", va="bottom", fontsize=8.5,
                         fontweight="bold" if is_sel else "normal", color=cor_t)

        plt.tight_layout()
        st.pyplot(fig3)
        plt.close(fig3)

    with col_infop:
        dados_sel = obter_dados_posicao(posicao_advertida)
        st.markdown(
            f"""
            <div class="info-card">
                <b style="font-size: 1.05rem;">Relatório do Atleta Selecionado: {posicao_advertida}</b><br><br>
                - <b>Taxa de Conversão:</b> {dados_sel['taxa_conversao']:.2f}% dos atletas com cartão são expulsos.<br>
                - <b>Razão Observado / Esperado:</b> {dados_sel['razao_obs_esp']:.2f}x em relação à formação.<br>
                - <b>Significância Estatística:</b> p-valor corrigido = {dados_sel['p_holm']:.5f}.<br>
                - <b>Ação Tático-Disciplinar:</b> {'Prioridade máxima de substituição.' if posicao_advertida == 'Zagueiro' else 'Acompanhamento preventivo.'}
            </div>
            """,
            unsafe_allow_html=True,
        )
