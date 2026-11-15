"""Estatística descritiva e testes brutos do resultado com e sem expulsão (seção 6.1 do plano).

São comparações *sem ajuste*: mostram a associação crua entre levar vermelho e o
resultado, que os modelos de src/models.py depois controlam por placar, minuto,
mando e Elo. A unidade é o time em cada partida (2014–2024).

1. Qui-quadrado: resultado (V/E/D) × o time levou vermelho na partida, com V de Cramér.
2. Mann-Whitney: pontos e saldo de gols de quem levou e de quem não levou vermelho,
   com correlação bisserial de postos como tamanho de efeito.
3. Diferença de médias com IC 95% por bootstrap *por partida*, porque os dois times
   do mesmo jogo não são independentes (o que um ganha, o outro perde).
4. Resultado final do time punido conforme o placar no momento do 1º vermelho.

Os p-valores da família são corrigidos por Holm.

Uso: python -m src.descritiva
"""
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

from src.features import PROCESSED_DIR, TABELAS_DIR
from src.models import tratados

N_BOOTSTRAP = 2000
SEMENTE = 42
RESULTADOS = ["V", "E", "D"]


def grupos_vermelho(tp: pd.DataFrame) -> pd.DataFrame:
    tp = tp.copy()
    tp["saldo"] = tp["gols_pro"] - tp["gols_contra"]
    tp["levou_vermelho"] = tp["vermelhos_proprios"] > 0
    return tp


def resumo_grupos(tp: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for levou, d in tp.groupby("levou_vermelho"):
        freq = d["resultado"].value_counts(normalize=True)
        linhas.append({"grupo": "com vermelho" if levou else "sem vermelho", "times_partida": len(d),
                       "pct_vitoria": freq.get("V", 0), "pct_empate": freq.get("E", 0),
                       "pct_derrota": freq.get("D", 0), "pontos_media": d["pontos"].mean(),
                       "saldo_media": d["saldo"].mean()})
    return pd.DataFrame(linhas)


def bootstrap_diferenca(tp: pd.DataFrame, coluna: str, rng: np.random.Generator) -> tuple[float, float, float]:
    """Diferença de médias (com − sem vermelho), reamostrando partidas inteiras."""
    ids = tp["partida_id"].unique()
    soma = tp.groupby(["partida_id", "levou_vermelho"])[coluna].agg(["sum", "size"]).unstack(fill_value=0)
    s_com, n_com = soma[("sum", True)].to_numpy(float), soma[("size", True)].to_numpy(float)
    s_sem, n_sem = soma[("sum", False)].to_numpy(float), soma[("size", False)].to_numpy(float)
    valor = s_com.sum() / n_com.sum() - s_sem.sum() / n_sem.sum()
    boot = np.empty(N_BOOTSTRAP)
    for b in range(N_BOOTSTRAP):
        i = rng.integers(0, len(ids), len(ids))
        boot[b] = s_com[i].sum() / n_com[i].sum() - s_sem[i].sum() / n_sem[i].sum()
    return valor, np.percentile(boot, 2.5), np.percentile(boot, 97.5)


def testes(tp: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEMENTE)
    linhas = []

    tabela = pd.crosstab(tp["levou_vermelho"], tp["resultado"])[RESULTADOS].to_numpy()
    chi2, p, gl, _ = stats.chi2_contingency(tabela)
    v = np.sqrt(chi2 / (tabela.sum() * (min(tabela.shape) - 1)))
    linhas.append({"teste": "Qui-quadrado: resultado × levou vermelho", "estatistica": chi2, "gl": gl,
                   "p_valor": p, "efeito": "V de Cramér", "valor_efeito": v, "n": int(tabela.sum())})

    com, sem = tp[tp["levou_vermelho"]], tp[~tp["levou_vermelho"]]
    for coluna, nome in (("pontos", "pontos"), ("saldo", "saldo de gols")):
        u, p = stats.mannwhitneyu(com[coluna], sem[coluna], alternative="two-sided")
        r = 1 - 2 * u / (len(com) * len(sem))  # bisserial de postos: positivo = sem vermelho maior
        dif, inf, sup = bootstrap_diferenca(tp, coluna, rng)
        linhas.append({"teste": f"Mann-Whitney: {nome}, com × sem vermelho", "estatistica": u, "gl": np.nan,
                       "p_valor": p, "efeito": "bisserial de postos", "valor_efeito": r, "n": len(tp),
                       "dif_media": dif, "ic95_inf": inf, "ic95_sup": sup})
    t = pd.DataFrame(linhas)
    t["p_holm"] = multipletests(t["p_valor"], method="holm")[1]
    return t


def resultado_por_estado(eventos: pd.DataFrame, partidas: pd.DataFrame) -> pd.DataFrame:
    """Resultado final do punido pelo placar no momento do 1º vermelho (até o minuto 90)."""
    t = tratados(eventos, partidas)
    estado = np.select([t["saldo_lado_antes"] < 0, t["saldo_lado_antes"] == 0], ["perdendo", "empatando"], "vencendo")
    resultado = np.select([t["pontos"] == 3, t["pontos"] == 1], ["vitória", "empate"], "derrota")
    tab = pd.crosstab(pd.Series(estado, name="estado"), pd.Series(resultado, name="resultado"))
    tab = tab.reindex(index=["empatando", "vencendo", "perdendo"], columns=["derrota", "empate", "vitória"], fill_value=0)
    tab["total"] = tab.sum(axis=1)
    return tab.reset_index()


def main() -> None:
    tp = grupos_vermelho(pd.read_parquet(PROCESSED_DIR / "time_partida.parquet"))
    eventos = pd.read_parquet(PROCESSED_DIR / "eventos.parquet")
    partidas = pd.read_parquet(PROCESSED_DIR / "partidas.parquet")

    resumo = resumo_grupos(tp)
    tst = testes(tp)
    estado = resultado_por_estado(eventos, partidas)

    resumo.to_csv(TABELAS_DIR / "descritiva_grupos.csv", index=False)
    tst.to_csv(TABELAS_DIR / "descritiva_testes.csv", index=False)
    estado.to_csv(TABELAS_DIR / "descritiva_resultado_por_estado.csv", index=False)
    with pd.option_context("display.width", 200, "display.float_format", "{:.4g}".format):
        print(resumo.to_string(index=False))
        print(tst.to_string(index=False))
        print(estado.to_string(index=False))


if __name__ == "__main__":
    main()
