"""Aba 2: Monitor da Zona de Risco Disciplinar e Alertas de Substituição."""
import matplotlib.pyplot as plt
import streamlit as st

from src.dashboard.config import CORES
from src.dashboard.data_loader import (
    carregar_tabela,
    formatar_decimal,
    formatar_p_valor,
    obter_att_pareamento,
    obter_dados_insights,
    obter_dados_posicao,
    obter_faixa_minuto,
    obter_irr_saldo,
    obter_taxas_faixa,
)


def calcular_nivel_risco(minuto: float, saldo_time: int, posicao: str) -> tuple[str, str, str, str]:
    """Calcula a classificação de risco e a recomendação de substituição com dados reais."""
    att_info = obter_att_pareamento(minuto, saldo=saldo_time)
    irr_info = obter_irr_saldo(saldo_time)
    dados_pos = obter_dados_posicao(posicao)
    taxas_h5 = obter_taxas_faixa()
    ins = obter_dados_insights()

    df_h5 = taxas_h5["tabela"]
    rotulo_h5 = obter_faixa_minuto(minuto, incluir_acrescimo_final=True)
    taxa_faixa = float(df_h5[df_h5["faixa_rotulo"] == rotulo_h5].iloc[0]["taxa_90"])

    att_faixa = abs(float(att_info["att"]))
    att_estado = abs(float(att_info["att_estado"]))
    att_ate75 = abs(float(att_info["ate_75"]["att"]))
    att_dep75 = abs(float(att_info["depois_75"]["att"]))
    pct_terco_final = float(taxas_h5["pct_terco_final"])

    irr_saldo = float(irr_info["irr"])
    irr_perd_geral = float(irr_info["irr_perdendo_geral"])
    var_pct = round((irr_saldo - 1.0) * 100)
    conv_pos = float(dados_pos["taxa_conversao"])

    conv_zag_1t = float(ins["conversao"].loc["zagueiro · 1º tempo", "taxa"]) * 100
    conv_demais_1t = float(ins["conversao"].loc["demais · 1º tempo", "taxa"]) * 100
    teste_z1t = ins["testes"].loc["I2 conversão: zagueiro 1º tempo × demais 1º tempo"]

    if saldo_time < 0 and minuto <= 75 and posicao in ["Zagueiro", "Meio-campo"]:
        detalhe_h3 = (
            f"risco {var_pct:+d}% maior (IRR = {irr_saldo:.2f}, p {formatar_p_valor(irr_info['p_valor'])})"
            if irr_info["significativo"]
            else f"em desvantagem a taxa geral sobe (IRR = {irr_perd_geral:.2f}; saldo específico IRR = {irr_saldo:.2f})"
        )
        return (
            "CRÍTICO",
            CORES["vermelho_alerta"],
            f"Equipe em desvantagem dentro da janela cara (≤ 75', ATT médio de {att_ate75:.2f} pt; faixa {rotulo_h5}: {att_faixa:.2f} pt) "
            f"com {posicao.lower()} amarelado — {detalhe_h3}.",
            f"SUBSTITUIÇÃO PREVENTIVA PRIORITÁRIA: Avaliar troca imediata antes dos 75' para preservar pontos esperados.",
        )

    if minuto <= 45 and posicao == "Zagueiro":
        return (
            "ALTO",
            "#ff922b",
            f"Zagueiro advertido no 1º tempo tem conversão de {conv_zag_1t:.2f}% para 2º amarelo "
            f"(vs {conv_demais_1t:.2f}% nas demais posições; razão {float(teste_z1t['valor_efeito']):.2f}x, p de Holm {formatar_p_valor(float(teste_z1t['p_holm']))}). "
            f"Uma expulsão até os 75' custa {att_ate75:.2f} pt ({att_faixa:.2f} pt na faixa {rotulo_h5}).",
            "ALERTA DO INTERVALO (Insight 2): Avaliar substituição ou ajuste de cobertura no intervalo; evitar expor o zagueiro ao 2º tempo inteiro.",
        )

    if saldo_time < 0:
        acao = (
            "PREPARAÇÃO DE TROCA: Orientar aquecimento do reserva e instruir contenção até os 75'."
            if minuto <= 75
            else f"CONTENÇÃO TÁTICA: Após os 75' o custo marginal cai para {att_dep75:.2f} pt; evitar faltas de segundo amarelo sem expor o time."
        )
        return (
            "ALTO",
            "#ff922b",
            f"Desvantagem no placar eleva a taxa de expulsões (IRR geral perdendo = {irr_perd_geral:.2f}; na faixa {rotulo_h5}, "
            f"taxa base de {taxa_faixa:.3f} vermelhos/90 min e ATT de {att_faixa:.2f} pt).",
            acao,
        )

    if saldo_time == 0 and minuto <= 75 and posicao == "Zagueiro":
        return (
            "ALTO",
            "#ff922b",
            f"Placar empatado na janela crítica (≤ 75'), onde expulsão custa {att_estado:.2f} pt em empate "
            f"({att_faixa:.2f} pt na faixa {rotulo_h5}; taxa global de conversão do zagueiro: {conv_pos:.2f}%).",
            "SUBSTITUIÇÃO TÁTICA PREVENTIVA: Monitorar duelos de 1×1 e considerar troca antes dos 75'.",
        )

    if minuto >= 61:
        if minuto <= 75:
            return (
                "MODERADO",
                CORES["amarelo_aviso"],
                f"Entrada na reta final da janela crítica ({rotulo_h5}: {taxa_faixa:.3f} vermelhos/90 min e ATT = {att_faixa:.2f} pt; "
                f"{pct_terco_final:.1f}% das expulsões ocorrem a partir dos 61').",
                "ORIENTAÇÃO DE CONTENÇÃO: Evitar faltas táticas de transição com atleta advertido até superar os 75'.",
            )
        return (
            "MODERADO",
            CORES["amarelo_aviso"],
            f"Terço final de altíssima densidade ({rotulo_h5}: {taxa_faixa:.3f} vermelhos/90 min; {pct_terco_final:.1f}% dos vermelhos a partir dos 61'), "
            f"mas com menor custo marginal (ATT pós-75' = {att_dep75:.2f} pt).",
            "CONTROLE DISCIPLINAR: Manter organização tática e orientar para evitar segundo amarelo desnecessário.",
        )

    return (
        "BAIXO",
        CORES["verde_sucesso"],
        f"Incidência histórica menor na faixa {rotulo_h5} (taxa observada de {taxa_faixa:.3f} vermelhos/90 min), "
        f"porém com alto custo causal caso ocorra expulsão ({att_faixa:.2f} pt na faixa).",
        "MONITORAMENTO NORMAL: Manter atleta em campo com orientação preventiva em transições defensivas.",
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
        st.markdown("#### Custo por Faixa de Minuto: Corte dos 75'")
        st.caption(f"Custo médio da expulsão por faixa de minuto (Destaque para o minuto {int(minuto)}')")

        df_att = carregar_tabela("h1_pareamento_att")
        faixas_att = df_att[df_att["grupo"].str.startswith("faixa")].copy()
        faixas_att["rotulo"] = faixas_att["grupo"].str.replace("faixa ", "")

        faixa_ativa = obter_faixa_minuto(minuto, incluir_acrescimo_final=False)

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

        ax.axvline(x=4.5, color="#e03131", linestyle=":", linewidth=2, label="Corte de 75' (Insight 1)")
        ax.legend(frameon=True, facecolor="#ffffff", fontsize=9)

        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

        att_map = df_att.set_index("grupo")["att"]
        att_16_30 = abs(float(att_map["faixa 16–30"]))
        att_61_75 = abs(float(att_map["faixa 61–75"]))
        att_ate75 = abs(float(att_map["até 75'"]))
        att_dep75 = abs(float(att_map["depois de 75'"]))
        razao_custo = att_ate75 / att_dep75

        st.caption(
            f"Evidência (ATT): Uma expulsão entre 16–30' custa {att_16_30:.2f} pt e entre 61–75' ainda custa {att_61_75:.2f} pt "
            f"(média até 75': {att_ate75:.2f} pt — {razao_custo:.1f}x o custo após os 75', {att_dep75:.2f} pt)."
        )

    with col_g2:
        st.markdown("#### Taxa Real de Expulsões por Faixa (H5 × H3)")
        irr_info = obter_irr_saldo(saldo_time)
        fator_h3 = float(irr_info["irr"])

        taxas_h5 = obter_taxas_faixa()["tabela"]
        rotulos_h5 = taxas_h5["faixa_rotulo"].tolist()
        taxas_obs = taxas_h5["taxa_90"].to_numpy(float)
        ic_inf = taxas_h5["ic95_inf"].to_numpy(float)
        ic_sup = taxas_h5["ic95_sup"].to_numpy(float)
        taxas_h3 = taxas_obs * fator_h3

        rotulo_ativo = obter_faixa_minuto(minuto, incluir_acrescimo_final=True)
        idx_ativo = rotulos_h5.index(rotulo_ativo)
        taxa_base_ativa = float(taxas_obs[idx_ativo])
        taxa_ajustada_ativa = float(taxas_h3[idx_ativo])

        x_idx = list(range(len(rotulos_h5)))
        fig2, ax2 = plt.subplots(figsize=(5.5, 3.8), dpi=120)
        fig2.patch.set_facecolor("#ffffff")
        ax2.set_facecolor("#fcfcfc")

        ax2.fill_between(x_idx, ic_inf, ic_sup, color="#adb5bd", alpha=0.25, label="IC 95% (Série A)")
        ax2.plot(
            x_idx, taxas_obs, marker="o", linestyle="--", color="#868e96",
            linewidth=1.8, markersize=5, label="Taxa Observada (Série A)",
        )

        cor_cenario = "#e03131" if saldo_time < 0 else ("#2f9e44" if saldo_time > 0 else "#1971c2")
        if saldo_time != 0:
            ax2.plot(
                x_idx, taxas_h3, marker="s", color=cor_cenario,
                linewidth=2.3, markersize=5.5, label=f"Ajustada IRR H3 ({fator_h3:.2f}x, Saldo {saldo_time:+d})",
            )

        ax2.scatter([idx_ativo], [taxa_ajustada_ativa], color=cor_cenario, s=85, zorder=5)
        ax2.annotate(
            f"{rotulo_ativo}: {taxa_ajustada_ativa:.3f}",
            xy=(idx_ativo, taxa_ajustada_ativa),
            xytext=(-15 if idx_ativo >= 4 else 8, 8),
            textcoords="offset points",
            fontsize=8.5,
            fontweight="bold",
            color=cor_cenario,
        )

        ax2.set_xticks(x_idx)
        ax2.set_xticklabels(rotulos_h5, fontsize=9)
        ax2.set_ylabel("Taxa de Cartões Vermelhos / 90 min", fontsize=9.5, fontweight="bold", color="#495057")
        ax2.set_xlabel("Faixa de Minuto (H5)", fontsize=9.5, fontweight="bold", color="#495057")
        ax2.set_ylim(0, max(float(ic_sup.max()), float(taxas_h3.max())) * 1.18)
        ax2.grid(True, linestyle="--", alpha=0.4)
        ax2.legend(frameon=True, facecolor="#ffffff", fontsize=8.2, loc="upper left")

        plt.tight_layout()
        st.pyplot(fig2)
        plt.close(fig2)

        var_pct = round((fator_h3 - 1.0) * 100)
        if saldo_time == 0:
            texto_h3 = (
                f"Taxa real na faixa {rotulo_ativo}: {formatar_decimal(taxa_base_ativa, 3)} vermelhos/90 min "
                "(placar empatado é a referência H3, IRR = 1,00)."
            )
        else:
            irr_txt = formatar_decimal(fator_h3)
            taxa_txt = formatar_decimal(taxa_ajustada_ativa, 3)
            nota_sig = (
                f"p {formatar_p_valor(irr_info['p_valor'])}"
                if irr_info["significativo"]
                else f"não significativo isoladamente, p = {formatar_decimal(irr_info['p_valor'], 3)}; em desvantagem geral IRR = {formatar_decimal(irr_info['irr_perdendo_geral'])}"
                if saldo_time < 0
                else f"não significativo isoladamente, p = {formatar_decimal(irr_info['p_valor'], 3)}; em vantagem geral IRR = {formatar_decimal(irr_info['irr_vencendo_geral'])}"
            )
            if var_pct > 0:
                texto_h3 = (
                    f"Em {irr_info['descricao']}, a taxa esperada sobe +{var_pct}% (IRR = {irr_txt}, {nota_sig}), "
                    f"chegando a {taxa_txt} vermelhos/90 min na faixa {rotulo_ativo}."
                )
            else:
                texto_h3 = (
                    f"Em {irr_info['descricao']}, a taxa esperada cai {abs(var_pct)}% (IRR = {irr_txt}, {nota_sig}), "
                    f"reduzindo para {taxa_txt} vermelhos/90 min na faixa {rotulo_ativo}."
                )
        st.caption(texto_h3)

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
        p_txt = formatar_p_valor(dados_sel["p_holm"])
        if posicao_advertida == "Zagueiro":
            ins = obter_dados_insights()
            conv_1t = float(ins["conversao"].loc["zagueiro · 1º tempo", "taxa"]) * 100
            acao_pos = (
                f"Prioridade máxima quando advertido no 1º tempo "
                f"(conversão de {conv_1t:.2f}% para 2º amarelo; avaliar troca no intervalo)."
            )
        elif dados_sel["razao_obs_esp"] < 1.0:
            acao_pos = "Incidência abaixo do esperado pela formação; manter acompanhamento preventivo padrão."
        else:
            acao_pos = "Acompanhamento preventivo dentro da janela de alto custo (≤ 75')."

        st.markdown(
            f"""
            <div class="info-card">
                <b style="font-size: 1.05rem;">Relatório do Atleta Selecionado: {posicao_advertida}</b><br><br>
                - <b>Taxa de Conversão (geral):</b> {dados_sel['taxa_conversao']:.2f}% dos atletas com cartão são expulsos.<br>
                - <b>Razão Observado / Esperado:</b> {dados_sel['razao_obs_esp']:.2f}x em relação à formação.<br>
                - <b>Significância Estatística:</b> p-valor corrigido (Holm) {p_txt}.<br>
                - <b>Ação Tático-Disciplinar:</b> {acao_pos}
            </div>
            """,
            unsafe_allow_html=True,
        )
