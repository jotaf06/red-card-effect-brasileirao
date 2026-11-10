"""Aba 1: Simulador Tático em Tempo Real (In-game Simulator)."""
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from src.dashboard.data_loader import (
    calcular_pontos_esperados,
    obter_att_pareamento,
    obter_dados_posicao,
    obter_dinamica_gols,
    predizer_probabilidades_multinomial,
)


def render_tab_simulator(
    minuto: float,
    saldo_time: int,
    lado_time: str,
    elo_diff: float,
    posicao_advertida: str,
):
    """Renderiza a interface do simulador in-game de cartão vermelho."""
    st.markdown("### Simulador de Impacto Tático em Tempo Real")
    st.markdown(
        "Estime o custo imediato de uma expulsão para a sua equipe com base no "
        "minuto do jogo, placar atual, força relativa dos times e posição sob risco."
    )

    if lado_time == "mandante":
        saldo_mandante = float(saldo_time)
        elo_mandante = elo_diff
        verm_m_antes, verm_v_antes = 0, 0
        verm_m_depois, verm_v_depois = 1, 0
    else:
        saldo_mandante = -float(saldo_time)
        elo_mandante = -elo_diff
        verm_m_antes, verm_v_antes = 0, 0
        verm_m_depois, verm_v_depois = 0, 1

    prob_antes = predizer_probabilidades_multinomial(
        minuto=minuto,
        saldo_mandante=saldo_mandante,
        elo_diff=elo_mandante,
        verm_mandante=verm_m_antes,
        verm_visitante=verm_v_antes,
    )
    prob_depois = predizer_probabilidades_multinomial(
        minuto=minuto,
        saldo_mandante=saldo_mandante,
        elo_diff=elo_mandante,
        verm_mandante=verm_m_depois,
        verm_visitante=verm_v_depois,
    )

    pe_antes = calcular_pontos_esperados(prob_antes, lado_time)
    pe_depois = calcular_pontos_esperados(prob_depois, lado_time)
    delta_pe = pe_depois - pe_antes

    att_info = obter_att_pareamento(minuto, lado=lado_time, saldo=saldo_time)
    gols_info = obter_dinamica_gols(lado=lado_time)
    dados_pos = obter_dados_posicao(posicao_advertida)

    if lado_time == "mandante":
        pv_antes, pe_emp_antes, pd_antes = prob_antes["P(V)"], prob_antes["P(E)"], prob_antes["P(D)"]
        pv_depois, pe_emp_depois, pd_depois = prob_depois["P(V)"], prob_depois["P(E)"], prob_depois["P(D)"]
    else:
        pv_antes, pe_emp_antes, pd_antes = prob_antes["P(D)"], prob_antes["P(E)"], prob_antes["P(V)"]
        pv_depois, pe_emp_depois, pd_depois = prob_depois["P(D)"], prob_depois["P(E)"], prob_depois["P(V)"]

    col1, col2, col3, col4 = st.columns(4)

    faixa_limpa = att_info["faixa"].replace("faixa ", "")

    with col1:
        st.markdown(
            f"""
            <div class="metric-card-danger">
                <div class="metric-value-danger">{delta_pe:+.2f} pts</div>
                <div class="metric-label">Custo Estimado (Delta PE)</div>
                <div class="metric-subtext">Modelo no minuto {int(minuto)}'<br>(Saldo {saldo_time:+d})</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value">{att_info['att']:+.2f} pts</div>
                <div class="metric-label">Efeito Causal (ATT Faixa)</div>
                <div class="metric-subtext">Faixa {faixa_limpa} min<br>(Mando: {att_info['att_lado']:+.2f} pts)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        irr_contra = gols_info["especifico"]["gols_contra_irr"]
        pct_sofrer = int((irr_contra - 1.0) * 100)
        st.markdown(
            f"""
            <div class="metric-card-danger">
                <div class="metric-value-danger">+{pct_sofrer}%</div>
                <div class="metric-label">Risco de Sofrer Gols</div>
                <div class="metric-subtext">IRR = {irr_contra:.2f}<br>({lado_time.capitalize()})</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        taxa_pos = dados_pos["taxa_conversao"]
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value">{taxa_pos:.1f}%</div>
                <div class="metric-label">Risco {posicao_advertida}</div>
                <div class="metric-subtext">Taxa de Conversão<br>Amarelo para Vermelho</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    col_graf, col_det = st.columns([1.3, 1.0])

    with col_graf:
        st.markdown("#### Distribuição de Probabilidades Finais")

        categorias = ["Vitória", "Empate", "Derrota"]
        valores_antes = [pv_antes * 100, pe_emp_antes * 100, pd_antes * 100]
        valores_depois = [pv_depois * 100, pe_emp_depois * 100, pd_depois * 100]

        x = np.arange(len(categorias))
        largura = 0.35

        fig, ax = plt.subplots(figsize=(6.5, 4.2), dpi=120)
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#fcfcfc")

        bar1 = ax.bar(x - largura / 2, valores_antes, largura, label="Com 11 jogadores", color="#4dabf7", alpha=0.9)
        bar2 = ax.bar(x + largura / 2, valores_depois, largura, label="Após Expulsão (10 jogadores)", color="#e03131", alpha=0.9)

        ax.set_ylabel("Probabilidade (%)", fontsize=11, fontweight="bold", color="#495057")
        ax.set_xticks(x)
        ax.set_xticklabels(categorias, fontsize=11, fontweight="bold", color="#343a40")
        ax.set_ylim(0, max(max(valores_antes), max(valores_depois)) * 1.25)
        ax.legend(frameon=True, facecolor="#ffffff", edgecolor="#dee2e6")
        ax.grid(axis="y", linestyle="--", alpha=0.4)

        for bar in bar1:
            h = bar.get_height()
            ax.annotate(f"{h:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, h), xytext=(0, 3),
                        textcoords="offset points", ha="center", va="bottom", fontsize=9, fontweight="bold", color="#1c7ed6")

        for bar in bar2:
            h = bar.get_height()
            ax.annotate(f"{h:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, h), xytext=(0, 3),
                        textcoords="offset points", ha="center", va="bottom", fontsize=9, fontweight="bold", color="#c92a2a")

        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

    with col_det:
        st.markdown("#### Impacto Quantitativo")
        dif_v = (pv_depois - pv_antes) * 100
        dif_e = (pe_emp_depois - pe_emp_antes) * 100
        dif_d = (pd_depois - pd_antes) * 100

        dados_tabela = {
            "Desfecho": ["Vitória", "Empate", "Derrota"],
            "11 em campo": [f"{pv_antes*100:.1f}%", f"{pe_emp_antes*100:.1f}%", f"{pd_antes*100:.1f}%"],
            "10 em campo": [f"{pv_depois*100:.1f}%", f"{pe_emp_depois*100:.1f}%", f"{pd_depois*100:.1f}%"],
            "Variação": [f"{dif_v:+.1f} p.p.", f"{dif_e:+.1f} p.p.", f"{dif_d:+.1f} p.p."],
        }
        st.dataframe(dados_tabela, use_container_width=True, hide_index=True)

        st.info(
            f"Leitura Técnica: No minuto {int(minuto)}' com saldo {saldo_time:+d}, o time na condição de "
            f"{lado_time} perde {abs(delta_pe):.2f} pontos esperados ao ter um {posicao_advertida.lower()} expulso. "
            f"A probabilidade de derrota varia {dif_d:+.1f} pontos percentuais. A prioridade tática é recomposição imediata."
        )

    st.markdown("#### Diretrizes Táticas Operacionais para a Comissão Técnica")

    if saldo_time >= 1:
        st.markdown(
            f"""
            <div class="tactical-box">
                <b>Cenário: Vencendo o Jogo (Vantagem no Placar)</b><br>
                1. <b>Linha de 5 Defensores Imediata:</b> Recuar linha de zaga e compactar setor com atenção ao {posicao_advertida}.<br>
                2. <b>Neutralização de Corredores:</b> Como a chance de sofrer gols sobe {pct_sofrer}%, fechar espaços laterais.<br>
                3. <b>Transição Segura:</b> Priorizar saídas diretas para atacante de velocidade, sem perder a posse em zona intermediária.
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif saldo_time == 0:
        st.markdown(
            f"""
            <div class="tactical-box">
                <b>Cenário: Jogo Empatado (Ponto Valioso)</b><br>
                1. <b>Bloco Médio-Baixo (4-4-1):</b> Manter linhas de quatro muito compactas, protegendo a entrelinha central.<br>
                2. <b>Substituição de Reequilíbrio:</b> Proteger o {posicao_advertida} amarelado com volante de cobertura.<br>
                3. <b>Controle de Ritmo:</b> Reduzir aceleração do jogo para conservar desgaste físico com 1 homem a menos.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="alert-box-critical">
                <b>Cenário: Perdendo a Partida (Zona de Risco Máximo)</b><br>
                1. <b>Vulnerabilidade Crítica:</b> Desvantagem de 1 gol tem risco de expulsão 48% maior (IRR = 1,48).<br>
                2. <b>Atleta Alvo:</b> O {posicao_advertida} amarelado tem probabilidade de expulsão de {taxa_pos:.1f}%. Substituir preventivamente antes dos 60'.<br>
                3. <b>Paciência Estratégica:</b> Não arriscar pressão alta descoordenada; concentrar investidas ofensivas em lances de bola parada.
            </div>
            """,
            unsafe_allow_html=True,
        )
