"""Figuras do projeto (PNG 300 dpi + PDF em reports/figures/), com rótulos em português."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402
from matplotlib.ticker import FuncFormatter, NullFormatter  # noqa: E402

from src.clean import RAIZ  # noqa: E402

FIGURAS_DIR = RAIZ / "reports" / "figures"

# Paleta de referência (validada): slots categóricos em ordem fixa, tinta neutra.
SERIE = ["#2a78d6", "#eb6834", "#1baf7a"]
SUPERFICIE = "#fcfcfb"
TEXTO = "#0b0b0b"
TEXTO_SEC = "#52514e"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"
COR_MODELO = {"logística multinomial": SERIE[0], "logística ordinal": SERIE[1], "LightGBM": SERIE[2]}
DIVERGENTE = LinearSegmentedColormap.from_list("azul_vermelho", ["#2a78d6", "#f0efec", "#e34948"])

plt.rcParams.update({
    "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE, "savefig.facecolor": SUPERFICIE,
    "axes.edgecolor": EIXO, "axes.labelcolor": TEXTO_SEC, "xtick.color": TEXTO_SEC,
    "ytick.color": TEXTO_SEC, "text.color": TEXTO, "axes.titlecolor": TEXTO,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRADE,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "font.size": 9, "axes.titlesize": 10,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "legend.frameon": False,
})


VIRGULA = FuncFormatter(lambda v, _: f"{v:g}".replace(".", ","))


def titulo_e_legenda(ax, titulo: str, ncol: int = 2) -> None:
    """Título à esquerda e legenda logo abaixo dele, fora da área dos dados."""
    ax.set_title(titulo, pad=24)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=ncol, borderaxespad=0.2,
              handletextpad=0.5, columnspacing=1.5)


def salvar(fig: plt.Figure, nome: str) -> None:
    FIGURAS_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIGURAS_DIR / f"{nome}.png", dpi=300)
    fig.savefig(FIGURAS_DIR / f"{nome}.pdf")
    plt.close(fig)


def barras_agrupadas(ax, categorias: list, series: dict) -> None:
    """Barras agrupadas com IC 95% (series: rótulo -> DataFrame com taxa_90 e IC)."""
    n = len(series)
    largura = 0.8 / n
    x = np.arange(len(categorias))
    for i, (rotulo, df) in enumerate(series.items()):
        pos = x + (i - (n - 1) / 2) * largura
        erro = [df["taxa_90"] - df["ic95_inf"], df["ic95_sup"] - df["taxa_90"]]
        ax.bar(pos, df["taxa_90"], width=largura, color=SERIE[i], edgecolor=SUPERFICIE,
               linewidth=1, label=rotulo)
        ax.errorbar(pos, df["taxa_90"], yerr=erro, fmt="none", ecolor=TEXTO_SEC, elinewidth=0.8, capsize=2)
    ax.set_xticks(x, categorias)
    ax.grid(axis="x", visible=False)
    ax.yaxis.set_major_formatter(VIRGULA)


def h3_taxa_estado(taxas: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(5.5, 3.2))
    ordem = ["perdendo", "empatando", "vencendo"]
    series = {r: taxas[taxas["tipo"] == t].set_index("estado").loc[ordem].reset_index()
              for r, t in (("Vermelho direto", "direto"), ("2º amarelo", "2º amarelo"))}
    barras_agrupadas(ax, ["Perdendo", "Empatando", "Vencendo"], series)
    titulo_e_legenda(ax, "Vermelhos por 90 minutos, conforme o placar no momento")
    ax.set_ylabel("Vermelhos por time a cada 90 min")
    ax.set_xlabel("Situação do time punido (sem ajuste; barras = IC 95% bootstrap)")
    salvar(fig, "h3_taxa_estado")


def h3_irr(irr: pd.DataFrame) -> None:
    dados = irr[irr["termo"].isin(["estado[perdendo]", "estado[vencendo]"])]
    modelos = list(dict.fromkeys(dados["modelo"]))
    fig, ax = plt.subplots(figsize=(6.2, 0.42 * len(modelos) + 1.6))
    y = np.arange(len(modelos))[::-1]
    for i, (termo, rotulo) in enumerate((("estado[perdendo]", "Perdendo × empatando"),
                                         ("estado[vencendo]", "Vencendo × empatando"))):
        d = dados[dados["termo"] == termo].set_index("modelo").loc[modelos]
        pos = y + (0.14 if i == 0 else -0.14)
        ax.errorbar(d["irr"], pos, xerr=[d["irr"] - d["ic95_inf"], d["ic95_sup"] - d["irr"]],
                    fmt="o", color=SERIE[i], ms=5, elinewidth=1.2, capsize=0, label=rotulo)
    ax.axvline(1, color=TEXTO_SEC, linewidth=0.8, linestyle="--")
    ax.set_xscale("log")
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks([0.5, 0.75, 1, 1.5, 2, 3], ["0,5", "0,75", "1", "1,5", "2", "3"])
    ax.set_yticks(y, modelos)
    ax.grid(axis="y", visible=False)
    titulo_e_legenda(ax, "IRR de vermelho pelo placar no momento")
    ax.set_xlabel("IRR (escala log; 1 = sem diferença; barras = IC 95% bootstrap)")
    salvar(fig, "h3_irr")


def h5_taxa_faixa(taxas: pd.DataFrame) -> None:
    from src.features import FAIXAS
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    series = {r: taxas[taxas["tipo"] == t].set_index("faixa_rotulo").loc[FAIXAS].reset_index()
              for r, t in (("Vermelho direto", "direto"), ("2º amarelo", "2º amarelo"))}
    barras_agrupadas(ax, FAIXAS, series)
    titulo_e_legenda(ax, "Vermelhos por 90 minutos, por faixa de minuto")
    ax.set_ylabel("Vermelhos por time a cada 90 min")
    ax.set_xlabel("Faixa de minuto (acréscimos incluídos na última faixa de cada tempo)")
    salvar(fig, "h5_taxa_faixa")


def h5_posicao(formacao: pd.DataFrame) -> None:
    from src.stats_tests import POSICOES
    fig, ax = plt.subplots(figsize=(5.5, 3.3))
    x = np.arange(len(POSICOES))
    for i, (variante, rotulo) in enumerate((("principal", "Referência: formação"),
                                            ("sensibilidade — pontas no ataque", "Sensibilidade: pontas no ataque"))):
        d = formacao[formacao["variante"] == variante].set_index("posicao").loc[POSICOES]
        pos = x + (-0.12 if i == 0 else 0.12)
        ax.errorbar(pos, d["razao_obs_esp"], yerr=[d["razao_obs_esp"] - d["ic95_inf"],
                                                   d["ic95_sup"] - d["razao_obs_esp"]],
                    fmt="o", color=SERIE[i], ms=5, elinewidth=1.2, capsize=0, label=rotulo)
    ax.axhline(1, color=TEXTO_SEC, linewidth=0.8, linestyle="--")
    ax.set_xticks(x, POSICOES)
    ax.grid(axis="x", visible=False)
    ax.yaxis.set_major_formatter(VIRGULA)
    titulo_e_legenda(ax, "Vermelhos observados ÷ esperados pela formação")
    ax.set_ylabel("Observado ÷ esperado (1 = proporcional)")
    ax.set_xlabel("Posição (barras = IC 95% bootstrap por partida)")
    salvar(fig, "h5_posicao")


def h5_posicao_faixa(celulas: pd.DataFrame) -> None:
    from src.features import FAIXAS
    from src.stats_tests import POSICOES
    res = celulas.pivot(index="posicao", columns="faixa", values="residuo_ajustado").loc[POSICOES, FAIXAS]
    obs = celulas.pivot(index="posicao", columns="faixa", values="observados").loc[POSICOES, FAIXAS]
    limite = max(3.0, float(np.abs(res.to_numpy()).max()))
    fig, ax = plt.subplots(figsize=(6.2, 2.8))
    im = ax.imshow(res.to_numpy(), cmap=DIVERGENTE, norm=TwoSlopeNorm(0, -limite, limite), aspect="auto")
    for (i, j), n in np.ndenumerate(obs.to_numpy()):
        ax.text(j, i, str(n), ha="center", va="center", fontsize=8, color=TEXTO)
    ax.set_xticks(range(len(FAIXAS)), FAIXAS)
    ax.set_yticks(range(len(POSICOES)), POSICOES)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    barra = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    barra.set_label("Resíduo ajustado", color=TEXTO_SEC)
    barra.outline.set_visible(False)
    ax.set_title("Vermelhos por posição × faixa de minuto (número = contagem)")
    ax.set_xlabel("Faixa de minuto (cor: acima/abaixo do esperado sob independência)")
    salvar(fig, "h5_posicao_faixa")


def h1_custo_minuto(custo: pd.DataFrame) -> None:
    """ΔPE do time punido por minuto da expulsão, por placar no momento e lado punido."""
    fig, eixos = plt.subplots(1, 2, figsize=(7.2, 3.4), sharey=True)
    rotulos = {-1: "Perdendo por 1", 0: "Empatando", 1: "Vencendo por 1"}
    for ax, (lado, titulo) in zip(eixos, (("mandante", "Mandante expulso"), ("visitante", "Visitante expulso"))):
        for i, (saldo, rotulo) in enumerate(rotulos.items()):
            d = custo[(custo["lado_punido"] == lado) & (custo["saldo_punido"] == saldo)].sort_values("landmark")
            ax.fill_between(d["landmark"], d["ic95_inf"], d["ic95_sup"], color=SERIE[i], alpha=0.15, linewidth=0)
            ax.plot(d["landmark"], d["delta_pe"], color=SERIE[i], linewidth=2, label=rotulo)
        ax.axhline(0, color=TEXTO_SEC, linewidth=0.8, linestyle="--")
        ax.set_title(titulo, fontsize=9.5)
        ax.set_xticks(range(0, 90, 15))
        ax.set_xlabel("Minuto da expulsão")
        ax.yaxis.set_major_formatter(VIRGULA)
    eixos[0].set_ylabel("Variação de pontos esperados (ΔPE)")
    eixos[0].legend(loc="lower right", fontsize=8)
    fig.suptitle("Custo da expulsão em pontos esperados do time punido (IC 95%)", x=0.02, ha="left",
                 fontsize=10, fontweight="bold")
    salvar(fig, "h1_custo_minuto")


def h1_pareamento(att: pd.DataFrame) -> None:
    grupos = ["todos"] + [g for g in att["grupo"] if g.startswith("faixa ")]
    d = att.set_index("grupo").loc[grupos]
    rotulos = ["Todos"] + [g.replace("faixa ", "") for g in grupos[1:]]
    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    x = np.arange(len(grupos))
    ax.errorbar(x, d["att"], yerr=[d["att"] - d["ic95_inf"], d["ic95_sup"] - d["att"]], fmt="o",
                color=SERIE[0], ms=6, elinewidth=1.2, capsize=0)
    for xi, n in zip(x, d["n_tratados"]):
        ax.text(xi, ax.get_ylim()[0], f"n={n}", ha="center", va="bottom", fontsize=7.5, color=TEXTO_SEC)
    ax.axhline(0, color=TEXTO_SEC, linewidth=0.8, linestyle="--")
    ax.set_xticks(x, rotulos)
    ax.grid(axis="x", visible=False)
    ax.yaxis.set_major_formatter(VIRGULA)
    ax.set_title("Pareamento: expulso − controles semelhantes")
    ax.set_ylabel("ATT (pontos por partida)")
    ax.set_xlabel("Faixa de minuto da expulsão (barras = IC 95% bootstrap)")
    salvar(fig, "h1_pareamento")


def h1_gols(gols: pd.DataFrame) -> None:
    modelos = list(dict.fromkeys(gols["modelo"]))
    fig, ax = plt.subplots(figsize=(6.4, 0.5 * len(modelos) + 1.6))
    y = np.arange(len(modelos))[::-1]
    for i, (termo, rotulo) in enumerate((("vantagem[inferior]", "Com um a menos"),
                                         ("vantagem[superior]", "Com um a mais"))):
        d = gols[gols["termo"] == termo].set_index("modelo").loc[modelos]
        pos = y + (0.12 if i == 0 else -0.12)
        ax.errorbar(d["irr"], pos, xerr=[d["irr"] - d["ic95_inf"], d["ic95_sup"] - d["irr"]], fmt="o",
                    color=SERIE[i], ms=5, elinewidth=1.2, capsize=0, label=rotulo)
    ax.axvline(1, color=TEXTO_SEC, linewidth=0.8, linestyle="--")
    ax.set_xscale("log")
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks([0.5, 0.75, 1, 1.5, 2], ["0,5", "0,75", "1", "1,5", "2"])
    ax.set_yticks(y, [m.replace("efeito fixo de partida (partidas com vermelho)", "efeito fixo de partida")
                      for m in modelos])
    ax.grid(axis="y", visible=False)
    titulo_e_legenda(ax, "Gols marcados vs. igualdade numérica")
    ax.set_xlabel("IRR (escala log; 1 = sem diferença; barras = IC 95%)")
    salvar(fig, "h1_gols")


def modelos_calibracao(y: np.ndarray, probs: dict, n_bins: int = 10) -> None:
    """Curva de confiabilidade de P(V) e P(E) do mandante no teste (bins por quantil)."""
    fig, eixos = plt.subplots(1, 2, figsize=(7.2, 3.4))
    for ax, (classe, titulo) in zip(eixos, ((2, "Vitória do mandante"), (1, "Empate"))):
        for nome, p in probs.items():
            q = pd.qcut(p[:, classe], n_bins, labels=False, duplicates="drop")
            d = pd.DataFrame({"p": p[:, classe], "y": (y == classe).astype(float), "q": q}).groupby("q").mean()
            ax.plot(d["p"], d["y"], marker="o", ms=4, linewidth=1.5, color=COR_MODELO[nome], label=nome)
        lim = [0, max(ax.get_xlim()[1], ax.get_ylim()[1])]
        ax.plot(lim, lim, color=TEXTO_SEC, linewidth=0.8, linestyle="--")
        ax.set_title(titulo, fontsize=9.5)
        ax.set_xlabel("Probabilidade prevista")
        ax.xaxis.set_major_formatter(VIRGULA)
        ax.yaxis.set_major_formatter(VIRGULA)
    eixos[0].set_ylabel("Frequência observada")
    eixos[0].legend(loc="upper left", fontsize=8)
    fig.suptitle("Calibração no teste (2022–2024)", x=0.02, ha="left", fontsize=10, fontweight="bold")
    salvar(fig, "modelos_calibracao")


def modelos_custo_comparacao(curvas: pd.DataFrame) -> None:
    """ΔPE com o time empatando, por modelo: o efeito estimado depende do modelo?"""
    modelos = ["logística multinomial", "logística ordinal", "LightGBM"]
    fig, eixos = plt.subplots(1, 2, figsize=(7.2, 3.4), sharey=True)
    for ax, (lado, titulo) in zip(eixos, (("mandante", "Mandante expulso"), ("visitante", "Visitante expulso"))):
        d = curvas[(curvas["lado_punido"] == lado) & (curvas["saldo_punido"] == 0)].sort_values("landmark")
        for nome in modelos:
            ax.plot(d["landmark"], d[nome], color=COR_MODELO[nome], linewidth=2, label=nome)
        ax.axhline(0, color=TEXTO_SEC, linewidth=0.8, linestyle="--")
        ax.set_title(titulo, fontsize=9.5)
        ax.set_xticks(range(0, 90, 15))
        ax.set_xlabel("Minuto da expulsão")
        ax.yaxis.set_major_formatter(VIRGULA)
    eixos[0].set_ylabel("ΔPE do time punido (empatando)")
    eixos[0].legend(loc="lower right", fontsize=8)
    fig.suptitle("Custo da expulsão estimado por modelo (treino 2014–2021)", x=0.02, ha="left",
                 fontsize=10, fontweight="bold")
    salvar(fig, "modelos_custo_comparacao")


def modelos_shap_dependencia(dep: pd.DataFrame) -> None:
    """SHAP do vermelho do mandante (classe V) conforme o minuto, nos landmarks com vermelho."""
    d = dep[dep["vermelhos_mandante"] > 0]
    fig, ax = plt.subplots(figsize=(5.5, 3.2))
    ax.scatter(d["landmark"], d["shap_verm_mandante_V"], s=14, color=SERIE[0], alpha=0.7, linewidths=0)
    ax.axhline(0, color=TEXTO_SEC, linewidth=0.8, linestyle="--")
    ax.set_xticks(range(0, 90, 15))
    ax.yaxis.set_major_formatter(VIRGULA)
    ax.set_title("SHAP do vermelho do mandante em P(vitória), LightGBM")
    ax.set_xlabel("Minuto (landmark) — só landmarks com mandante já expulso")
    ax.set_ylabel("Contribuição (log-odds de V)")
    salvar(fig, "modelos_shap_dependencia")
