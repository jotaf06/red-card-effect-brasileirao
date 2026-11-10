"""Aba 3: Evidências Científicas, Modelos e Avaliação."""
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from src.dashboard.config import FIGURES_DIR
from src.dashboard.data_loader import carregar_tabela, obter_comparacao_modelos_cenario


def render_tab_models(minuto: float = 45.0, saldo_time: int = 0, lado_time: str = "mandante"):
    """Renderiza a aba de evidências científicas, métricas out-of-time e modelos comparados."""
    st.markdown("### Evidências Científicas e Avaliação dos Modelos")
    st.markdown(
        "Apresentação rigorosa da performance dos modelos estatísticos e de aprendizado de máquina "
        "no conjunto de teste out-of-time (temporadas 2022 a 2024), demonstrando conformidade com as seções 4, 5 e 6 do edital."
    )

    st.markdown("#### 1. Comparação de Desempenho no Teste Temporal (2022–2024)")
    st.caption(
        "Avaliação rigorosa em 3 anos futuros completos (2022–2024), sem vazamento de dados. "
        "Log-loss e RPS são as métricas principais para probabilidades ordenadas (D < E < V)."
    )

    df_metr = carregar_tabela("modelos_metricas")
    col_sub = "subconjunto" if "subconjunto" in df_metr.columns else "subpopulacao"

    opcoes_sub = {
        "Todos os momentos do jogo (Todos os landmarks)": "todos os landmarks",
        "Apenas momentos com cartão vermelho em campo": "landmarks com vermelho",
    }
    sub_escolhido = st.radio(
        "Filtro da avaliação no teste:",
        options=list(opcoes_sub.keys()),
        horizontal=True,
    )
    filtro_valor = opcoes_sub[sub_escolhido]

    teste_geral = df_metr[df_metr[col_sub] == filtro_valor].copy()

    n_amostras = int(teste_geral["n_linhas"].iloc[0]) if "n_linhas" in teste_geral.columns else len(teste_geral)
    linhas_validas = teste_geral[teste_geral["log_loss"].notna()]
    melhor_ll_row = linhas_validas.loc[linhas_validas["log_loss"].idxmin()]
    melhor_acc_row = teste_geral.loc[teste_geral["acuracia"].idxmax()]
    melhor_rps_row = linhas_validas.loc[linhas_validas["rps"].idxmin()]

    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.metric(
            label="Amostras no Teste (N)",
            value=f"{n_amostras:,}".replace(",", "."),
            delta="Temporadas 2022–2024",
            delta_color="off",
        )
    with m_col2:
        st.metric(
            label="Melhor Log-Loss",
            value=f"{melhor_ll_row['log_loss']:.4f}",
            delta=melhor_ll_row["modelo"],
            delta_color="off",
        )
    with m_col3:
        st.metric(
            label="Melhor Acurácia",
            value=f"{melhor_acc_row['acuracia']*100:.1f}%",
            delta=melhor_acc_row["modelo"],
            delta_color="off",
        )
    with m_col4:
        st.metric(
            label="Melhor Ranked Score (RPS)",
            value=f"{melhor_rps_row['rps']:.4f}",
            delta=melhor_rps_row["modelo"],
            delta_color="off",
        )

    if filtro_valor == "todos os landmarks":
        st.info(
            "Cenário Geral: Avaliação em todos os 20.520 marcos do teste (2022–2024). "
            "A Logística Multinomial alcança o melhor compromisso de calibração e Log-Loss (0,8282), superando com folga o benchmark de frequências históricas (1,0661)."
        )
    else:
        st.success(
            "Cenário sob Inferioridade Numérica: Avaliação focada nos 1.189 marcos com expulsão ativa. "
            "A separabilidade do desfecho se acentua, reduzindo o Log-Loss para 0,6666 e elevando a acurácia global para 72,5%."
        )

    tabela_exib = []
    for _, row in teste_geral.iterrows():
        tabela_exib.append({
            "Abordagem / Modelo": row["modelo"],
            "Log-Loss": f"{row['log_loss']:.4f}" if pd.notna(row["log_loss"]) else "—",
            "RPS (Ranked Score)": f"{row['rps']:.4f}" if pd.notna(row["rps"]) else "—",
            "Brier Score": f"{row['brier']:.4f}" if pd.notna(row["brier"]) else "—",
            "AUC (OvR)": f"{row['auc_ovr']:.3f}" if pd.notna(row["auc_ovr"]) else "—",
            "Acurácia": f"{row['acuracia']*100:.1f}%" if pd.notna(row["acuracia"]) else "—",
            "F1 Macro": f"{row['f1_macro']:.3f}" if pd.notna(row["f1_macro"]) else "—",
        })

    st.dataframe(
        pd.DataFrame(tabela_exib),
        use_container_width=True,
        hide_index=True,
        key=f"tabela_desempenho_{filtro_valor.replace(' ', '_')}",
    )

    st.markdown("---")

    st.markdown("#### 2. Estimativa de Custo nos 4 Modelos para o Cenário Selecionado")
    st.caption(f"Comparativo no minuto {int(minuto)}', saldo {saldo_time:+d}, condição {lado_time.capitalize()}")

    comp = obter_comparacao_modelos_cenario(minuto, saldo_time, lado_time)
    if comp:
        modelos_nomes = ["Logística Multinomial", "Logística Ordinal", "Random Forest", "LightGBM"]
        valores_comp = [comp.get(m, 0.0) for m in modelos_nomes]

        fig_comp, ax_comp = plt.subplots(figsize=(6.5, 3.4), dpi=120)
        fig_comp.patch.set_facecolor("#ffffff")
        ax_comp.set_facecolor("#fcfcfc")

        cores_m = ["#1971c2", "#74c0fc", "#2f9e44", "#f59f00"]
        barras_m = ax_comp.bar(modelos_nomes, [abs(v) for v in valores_comp], color=cores_m, alpha=0.9, edgecolor="#495057")

        ax_comp.set_ylabel("Custo Estimado (Pontos Perdidos)", fontsize=9, fontweight="bold", color="#495057")
        ax_comp.grid(axis="y", linestyle="--", alpha=0.4)

        for bm, val in zip(barras_m, valores_comp):
            h = bm.get_height()
            ax_comp.annotate(f"{val:+.2f} pts", xy=(bm.get_x() + bm.get_width() / 2, h), xytext=(0, 4),
                             textcoords="offset points", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#212529")

        plt.tight_layout()
        st.pyplot(fig_comp)
        plt.close(fig_comp)

        st.caption(
            "Convergência de Modelos: A Logística Multinomial e a Random Forest produzem estimativas coerentes "
            "e estáveis, confirmando o efeito negativo consistente do cartão vermelho sob diferentes famílias algorítmicas."
        )

    st.markdown("---")

    st.markdown("#### 3. Galeria de Diagnósticos Gráficos e Causalidade")

    opcoes_figuras = {
        "Curva de Calibração das Probabilidades (Vitória e Empate)": "modelos_calibracao.png",
        "Custo da Expulsão por Minuto e Placar (Curvas Multinomiais)": "h1_custo_minuto.png",
        "Efeito Causal por Faixa de Minuto (Estimador ATT Pareamento)": "h1_pareamento.png",
        "Razão de Taxas de Gols sob Inferioridade / Superioridade": "h1_gols.png",
        "Causalidade Reversa (H3): Risco por Placar no Momento": "h3_irr.png",
        "Aceleração da Taxa de Vermelhos por Minuto (H5)": "h5_taxa_faixa.png",
        "Dependência e Importância das Variáveis (SHAP)": "modelos_shap_dependencia.png",
    }

    escolha = st.selectbox(
        "Selecione a evidência gráfica para inspecionar:",
        options=list(opcoes_figuras.keys()),
        filter_mode=None,
    )
    arquivo_fig = opcoes_figuras[escolha]
    caminho_fig = FIGURES_DIR / arquivo_fig

    if caminho_fig.exists():
        st.image(str(caminho_fig), use_container_width=True, caption=f"Fonte: reports/figures/{arquivo_fig}")
    else:
        st.warning(f"Figura {arquivo_fig} não encontrada em reports/figures/.")

    st.markdown("---")

    st.markdown("#### 4. Rigor Metodológico e Blindagem contra Vieses")
    
    col_m1, col_m2, col_m3 = st.columns(3)

    with col_m1:
        st.markdown(
            """
            **1. Sem Vazamento Temporal (Data Leakage):**
            - O rating Elo dos times foi calibrado com jogos de 2004 a 2013 (fora da janela analítica).
            - As features em cada minuto utilizam estritamente o histórico anterior ao apito inicial ou ao evento corrente.
            """
        )

    with col_m2:
        st.markdown(
            """
            **2. Validação Temporal e Agrupamento:**
            - Separação estrita: Treino (2014–2021) e Teste (2022–2024).
            - O ajuste de hiperparâmetros de árvores utilizou GroupKFold(5) agrupado por partida_id, impedindo que marcos do mesmo jogo coexistissem em treino e teste.
            """
        )

    with col_m3:
        st.markdown(
            """
            **3. Mitigação de Causalidade Reversa (H3):**
            - Times que estão perdendo recebem 39% mais cartões vermelhos.
            - O modelo controla explicitamente o placar no momento exato da expulsão, e o pareamento compara times com mesmo saldo, minuto e Elo.
            """
        )
