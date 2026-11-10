"""Aplicação Principal do Dashboard Interativo (Streamlit).

Execução:
    streamlit run src/dashboard/app.py
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st

from src.dashboard.config import (
    CUSTOM_CSS,
    LAYOUT,
    OPCOES_ELO,
    OPCOES_SALDO,
    PAGE_ICON,
    PAGE_TITLE,
    POSICOES,
)
from src.dashboard.tabs.tab_advisor import render_tab_advisor
from src.dashboard.tabs.tab_models import render_tab_models
from src.dashboard.tabs.tab_risk_monitor import render_tab_risk_monitor
from src.dashboard.tabs.tab_simulator import render_tab_simulator


def main():
    """Executa a interface gráfica principal do Dashboard Tático Streamlit."""
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout=LAYOUT,
        initial_sidebar_state="expanded",
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    st.markdown('<div class="main-header">Quanto Custa uma Expulsão?</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">'
        '<b>Painel de Decisão Tática e Efeito Causal no Brasileirão Série A (2014–2024)</b><br>'
        '<span style="font-size: 0.95rem; color: #868e96;">UFAL / Instituto de Computação · '
        'Projeto de Ciência de Dados · Cliente: Comissão Técnica e Análise de Desempenho</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### Cenário da Partida (In-Game)")
        st.caption("Ajuste as condições para atualizar instantaneamente as simulações e diretrizes.")

        minuto = st.slider(
            "Minuto do Jogo:",
            min_value=0,
            max_value=90,
            value=45,
            step=5,
        )

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

        lado_time = st.radio(
            "Mando de Campo da sua Equipe:",
            options=["mandante", "visitante"],
            format_func=lambda x: "Mandante (Casa)" if x == "mandante" else "Visitante (Fora)",
            index=0,
        )

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

        saldo_opcoes = list(OPCOES_SALDO.keys())
        saldo_chave = st.selectbox(
            "Placar no Momento (Saldo do seu time):",
            options=saldo_opcoes,
            index=saldo_opcoes.index("Empatando (0)"),
            filter_mode=None,
        )
        saldo_time = OPCOES_SALDO[saldo_chave]

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

        elo_opcoes = list(OPCOES_ELO.keys())
        elo_chave = st.selectbox(
            "Força Relativa (Diferença de Elo):",
            options=elo_opcoes,
            index=elo_opcoes.index("Equilibrado (Elo 0)"),
            filter_mode=None,
        )
        elo_diff = OPCOES_ELO[elo_chave]

        st.markdown("---")
        st.markdown("### Atleta sob Risco")
        posicao_advertida = st.selectbox(
            "Posição do Atleta Amarelado:",
            options=POSICOES,
            index=0,
            filter_mode=None,
        )

        st.markdown("---")
        st.markdown(
            """
            <div style="font-size: 0.8rem; color: #868e96; line-height: 1.4;">
                <b>Dataset Analisado:</b><br>
                - 4.179 partidas (2014–2024)<br>
                - 1.086 cartões vermelhos em 876 jogos<br>
                - Minuto exato em 100% dos eventos<br>
                - Rating Elo calibrado em 2004–2013
            </div>
            """,
            unsafe_allow_html=True,
        )

    tab1, tab2, tab3, tab4 = st.tabs([
        "Simulador Tático (In-game)",
        "Radar da Zona de Risco",
        "Evidências e Modelos",
        "Parecer Executivo e Insights",
    ])

    with tab1:
        render_tab_simulator(
            minuto=float(minuto),
            saldo_time=saldo_time,
            lado_time=lado_time,
            elo_diff=elo_diff,
            posicao_advertida=posicao_advertida,
        )

    with tab2:
        render_tab_risk_monitor(
            minuto=float(minuto),
            saldo_time=saldo_time,
            posicao_advertida=posicao_advertida,
        )

    with tab3:
        render_tab_models(
            minuto=float(minuto),
            saldo_time=saldo_time,
            lado_time=lado_time,
        )

    with tab4:
        render_tab_advisor(
            minuto=float(minuto),
            saldo_time=saldo_time,
            lado_time=lado_time,
            elo_diff=elo_diff,
            posicao_advertida=posicao_advertida,
        )

    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; font-size: 0.85rem; color: #868e96;">
            Projeto Final de Ciência de Dados — UFAL / Instituto de Computação (2026.2) <br>
            <i>Modelos ajustados com validação temporal estrita e inferência causal com pareamento exato.</i>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
