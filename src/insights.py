"""Insights acionáveis (P1): evidência extra, linha de base da liga e metas.

Os três insights seguem o formato do enunciado. Este módulo gera os números que
eles citam e que não saem dos módulos de hipóteses:

1. Conversão do 1º amarelo em expulsão por 2º amarelo, por posição e tempo de
   jogo (proporções com IC de Wilson e testes z, corrigidos por Holm).
2. Indicadores por time e temporada (2014–2024): a distribuição da liga é a
   linha de base das metas, porque a base não identifica "o nosso clube".
3. Metas: cada métrica principal tem meta igual a um recorte da liga (quartil
   inferior ou ponto médio), e a tabela registra a chance de um time médio
   cumprir a meta por acaso, para mostrar o quanto a meta é exigente.
4. Diferença de pontos entre o 16º e o 17º colocados, para dar escala ao custo.

Lê data/processed/ (incluindo pareamento_tratados.parquet, de src.models) e
reports/tabelas/h1_pareamento_att.csv. Grava reports/tabelas/insights_*.csv.

Uso: python -m src.insights
"""
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint, proportions_ztest

from src.features import FAIXAS, PROCESSED_DIR, TABELAS_DIR

FAIXA_75 = FAIXAS.index("61–75")  # faixas até aqui = vermelho até os 75'
TEMPORADAS_I3 = 2  # minutos com um a menos numa temporada são poucos para medir gols


# ---------------------------------------------------------------------------
# 1. Do 1º amarelo à expulsão
# ---------------------------------------------------------------------------

def primeiros_amarelos(eventos: pd.DataFrame) -> pd.DataFrame:
    """1º amarelo de cada atleta na partida, marcado se ele terminou expulso por 2º amarelo."""
    am = (eventos[eventos["tipo"] == "amarelo"].sort_values(["partida_id", "ordem"])
          .drop_duplicates(["partida_id", "clube", "atleta"]))
    exp = eventos[(eventos["tipo"] == "vermelho") & (eventos["vermelho_tipo"] == "2o_amarelo")]
    exp = exp[["partida_id", "clube", "atleta"]].drop_duplicates().assign(expulso=1)
    am = am.merge(exp, on=["partida_id", "clube", "atleta"], how="left")
    am["expulso"] = am["expulso"].fillna(0).astype(int)
    am["grupo_posicao"] = np.where(am["posicao"] == "Zagueiro", "zagueiro",
                                   np.where(am["posicao"].isna(), None, "demais"))
    return am


def proporcao(nome: str, d: pd.DataFrame) -> dict:
    k, n = int(d["expulso"].sum()), len(d)
    inf, sup = proportion_confint(k, n, method="wilson")
    return {"grupo": nome, "amarelos": n, "expulsos": k, "taxa": k / n, "ic95_inf": inf, "ic95_sup": sup}


def conversao_amarelo(am: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    linhas = [proporcao("todos", am)]
    for t in (1, 2):
        linhas.append(proporcao(f"{t}º tempo", am[am["tempo"] == t]))
        for g in ("zagueiro", "demais"):
            linhas.append(proporcao(f"{g} · {t}º tempo", am[(am["tempo"] == t) & (am["grupo_posicao"] == g)]))
        for pos in ("Goleiro", "Zagueiro", "Meio-campo", "Atacante"):
            linhas.append(proporcao(f"{pos} · {t}º tempo", am[(am["tempo"] == t) & (am["posicao"] == pos)]))
    conv = pd.DataFrame(linhas)

    def teste(nome: str, a: str, b: str) -> dict:
        la, lb = conv.set_index("grupo").loc[a], conv.set_index("grupo").loc[b]
        _, p = proportions_ztest([la.expulsos, lb.expulsos], [la.amarelos, lb.amarelos])
        return {"teste": nome, "efeito": "razão de proporções", "valor_efeito": la.taxa / lb.taxa,
                "taxa_a": la.taxa, "taxa_b": lb.taxa, "p_valor": p}

    testes = pd.DataFrame([
        teste("I2 conversão: zagueiro 1º tempo × demais 1º tempo", "zagueiro · 1º tempo", "demais · 1º tempo"),
        teste("I2 conversão: zagueiro 1º tempo × zagueiro 2º tempo", "zagueiro · 1º tempo", "zagueiro · 2º tempo"),
        teste("I2 conversão: zagueiro 2º tempo × demais 2º tempo", "zagueiro · 2º tempo", "demais · 2º tempo"),
    ])
    testes["p_holm"] = multipletests(testes["p_valor"], method="holm")[1]
    return conv, testes


# ---------------------------------------------------------------------------
# 2. Indicadores por time e temporada
# ---------------------------------------------------------------------------

def times_temporada(partidas: pd.DataFrame) -> pd.DataFrame:
    lados = []
    for lado, outro in (("mandante", "visitante"), ("visitante", "mandante")):
        d = partidas[["partida_id", "temporada", lado, f"pontos_{lado}"]].copy()
        d.columns = ["partida_id", "temporada", "clube", "pontos"]
        d["lado"] = lado
        lados.append(d)
    return pd.concat(lados, ignore_index=True)


def indicadores(eventos: pd.DataFrame, partidas: pd.DataFrame, exposicao: pd.DataFrame,
                tratados: pd.DataFrame, att: pd.DataFrame, am: pd.DataFrame) -> pd.DataFrame:
    jogos = times_temporada(partidas)
    chave = ["temporada", "clube"]
    base = jogos.groupby(chave).agg(jogos=("partida_id", "size"), pontos=("pontos", "sum"))

    temp = partidas.set_index("partida_id")["temporada"]
    v = eventos[eventos["tipo"] == "vermelho"].assign(temporada=lambda d: d["partida_id"].map(temp))
    v["ate75"] = v["faixa"] <= FAIXA_75

    def conta(d: pd.DataFrame, nome: str) -> pd.Series:
        return d.groupby(chave).size().rename(nome)

    a = am.assign(temporada=am["partida_id"].map(temp))
    partes = [
        conta(v, "vermelhos"),
        conta(v[v["vermelho_tipo"] == "2o_amarelo"], "vermelhos_2o_amarelo"),
        conta(v[(v["vermelho_tipo"] == "2o_amarelo") & v["ate75"]], "vermelhos_2o_amarelo_ate75"),
        conta(v[v["ate75"]], "vermelhos_ate75"),
        conta(v[v["posicao"] == "Zagueiro"], "vermelhos_zagueiro"),
        conta(a[(a["posicao"] == "Zagueiro") & (a["tempo"] == 1)], "zagueiros_advertidos_1t"),
    ]

    # Pontos perdidos estimados: ATT da faixa de cada 1º vermelho pareado (até os 90').
    att_faixa = att.set_index("grupo")["att"]
    rot = {i: f"faixa {f}".replace("76–90+", "76–90") for i, f in enumerate(FAIXAS)}
    t = tratados.merge(jogos[["partida_id", "lado", "temporada", "clube"]], on=["partida_id", "lado"])
    t["custo"] = -t["faixa"].map(rot).map(att_faixa)
    partes.append(t.groupby(chave)["custo"].sum().rename("pontos_perdidos_estimados"))

    # Minutos e gols sofridos com um a menos.
    clube = jogos.set_index(["partida_id", "lado"])["clube"]
    e = exposicao[exposicao["vantagem_numerica"] < 0].copy()
    e["clube"] = clube.reindex(pd.MultiIndex.from_frame(e[["partida_id", "lado"]])).to_numpy()
    partes.append(e.groupby(chave)["exposicao"].sum().rename("minutos_com_menos"))
    partes.append(e.groupby(chave)["gols_contra"].sum().rename("gols_sofridos_com_menos"))
    partes.append(e.groupby(chave)["gols_pro"].sum().rename("gols_marcados_com_menos"))

    ind = base.join(partes).fillna(0).reset_index()
    return ind


def resumo_liga(ind: pd.DataFrame) -> pd.DataFrame:
    colunas = [c for c in ind.columns if c not in ("temporada", "clube", "jogos")]
    linhas = []
    for c in colunas:
        x = ind[c].astype(float)
        linhas.append({"metrica": c, "times_temporada": len(x), "media": x.mean(), "p25": x.quantile(0.25),
                       "mediana": x.median(), "p75": x.quantile(0.75), "maximo": x.max(),
                       "pct_zero": (x == 0).mean()})
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# 3. Metas
# ---------------------------------------------------------------------------

def taxas_gols(exposicao: pd.DataFrame) -> dict:
    g = exposicao.groupby(np.sign(exposicao["vantagem_numerica"]))[["exposicao", "gols_contra"]].sum()
    return {"igual": g.loc[0, "gols_contra"] / g.loc[0, "exposicao"] * 90,
            "com_menos": g.loc[-1, "gols_contra"] / g.loc[-1, "exposicao"] * 90}


def metas(liga: pd.DataFrame, exposicao: pd.DataFrame) -> pd.DataFrame:
    l = liga.set_index("metrica")
    linhas = []
    # I1 e I2: contagens por temporada; meta = quartil inferior da liga.
    for ins, met in (("I1", "vermelhos_2o_amarelo_ate75"), ("I2", "vermelhos_zagueiro")):
        media, meta = l.loc[met, "media"], l.loc[met, "p25"]
        linhas.append({"insight": ins, "metrica": met, "periodo_jogos": 38, "liga_media": media,
                       "liga_mediana": l.loc[met, "mediana"], "meta": meta, "regra": "≤ quartil inferior da liga",
                       "chance_acaso": stats.poisson.cdf(meta, media)})
    # I3: gols sofridos por 90' com um a menos, em 2 temporadas; meta = metade do caminho até a taxa com 11.
    tx = taxas_gols(exposicao)
    meta = (tx["igual"] + tx["com_menos"]) / 2
    minutos = TEMPORADAS_I3 * l.loc["minutos_com_menos", "mediana"]
    mu = tx["com_menos"] * minutos / 90
    linhas.append({"insight": "I3", "metrica": "gols_sofridos_por_90_com_menos", "periodo_jogos": 38 * TEMPORADAS_I3,
                   "liga_media": tx["com_menos"], "liga_mediana": np.nan, "meta": meta,
                   "regra": "≤ ponto médio entre a taxa da liga com 10 e com 11",
                   "chance_acaso": stats.poisson.cdf(np.floor(meta * minutos / 90), mu),
                   "taxa_com_11": tx["igual"], "minutos_tipicos": minutos})
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# 4. Escala: pontos que separam o 16º do 17º
# ---------------------------------------------------------------------------

def corte_rebaixamento(partidas: pd.DataFrame) -> pd.DataFrame:
    pts = times_temporada(partidas).groupby(["temporada", "clube"])["pontos"].sum()
    linhas = []
    for temporada, s in pts.groupby(level=0):
        s = s.sort_values(ascending=False).to_numpy()
        linhas.append({"temporada": temporada, "pontos_16": s[15], "pontos_17": s[16], "diferenca": s[15] - s[16]})
    return pd.DataFrame(linhas)


def main() -> None:
    eventos = pd.read_parquet(PROCESSED_DIR / "eventos.parquet")
    partidas = pd.read_parquet(PROCESSED_DIR / "partidas.parquet")
    exposicao = pd.read_parquet(PROCESSED_DIR / "exposicao.parquet")
    tratados = pd.read_parquet(PROCESSED_DIR / "pareamento_tratados.parquet")
    att = pd.read_csv(TABELAS_DIR / "h1_pareamento_att.csv")

    am = primeiros_amarelos(eventos)
    conv, testes = conversao_amarelo(am)
    ind = indicadores(eventos, partidas, exposicao, tratados, att, am)
    liga = resumo_liga(ind)
    mt = metas(liga, exposicao)
    corte = corte_rebaixamento(partidas)

    conv.to_csv(TABELAS_DIR / "insights_conversao_amarelo.csv", index=False)
    testes.to_csv(TABELAS_DIR / "insights_testes.csv", index=False)
    ind.to_csv(TABELAS_DIR / "insights_time_temporada.csv", index=False)
    liga.to_csv(TABELAS_DIR / "insights_liga.csv", index=False)
    mt.to_csv(TABELAS_DIR / "insights_metas.csv", index=False)
    corte.to_csv(TABELAS_DIR / "insights_corte_rebaixamento.csv", index=False)

    with pd.option_context("display.width", 200, "display.float_format", "{:.4g}".format):
        print(conv.to_string(index=False))
        print(testes.to_string(index=False))
        print(liga.to_string(index=False))
        print(mt.to_string(index=False))
        print(corte.to_string(index=False))


if __name__ == "__main__":
    main()
