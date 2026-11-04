"""Testes de hipótese H3 (vermelho × placar no momento) e H5 (posição e minuto).

Lê data/processed/ e grava tabelas em reports/tabelas/h3_*.csv e h5_*.csv e
figuras em reports/figures/.

Uso: python -m src.stats_tests
"""
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint, proportions_ztest

from src import figuras
from src.clean import INTERIM_DIR
from src.features import FAIXAS, FAIXAS_FINAS, PROCESSED_DIR, TABELAS_DIR

N_BOOTSTRAP = 2000
SEMENTE = 42
POSICOES = ["Goleiro", "Zagueiro", "Meio-campo", "Atacante"]
ESTADOS = ["perdendo", "empatando", "vencendo"]
VANTAGEM = {-1: "inferior", 0: "igual", 1: "superior"}
TIPOS_VERMELHO = {"vermelhos": "todos", "vermelhos_direto": "direto",
                  "vermelhos_2o_amarelo": "2º amarelo"}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def cramer_v_aderencia(chi2: float, n: int, k: int) -> float:
    return float(np.sqrt(chi2 / (n * (k - 1))))


def cramer_v_tabela(chi2: float, tabela: np.ndarray) -> float:
    n = tabela.sum()
    return float(np.sqrt(chi2 / (n * (min(tabela.shape) - 1))))


def matriz_desenho(celulas: pd.DataFrame, categoricas: dict, numericas: list | None = None) -> pd.DataFrame:
    """Intercepto + dummies (sem a categoria de referência) + colunas numéricas."""
    partes = [pd.Series(1.0, index=celulas.index, name="const")]
    for col, referencia in categoricas.items():
        niveis = [n for n in pd.unique(celulas[col]) if n != referencia]
        for nivel in sorted(niveis, key=str):
            partes.append((celulas[col] == nivel).astype(float).rename(f"{col}[{nivel}]"))
    for col in numericas or []:
        partes.append(celulas[col].astype(float))
    return pd.concat(partes, axis=1)


def ajustar_poisson(y: np.ndarray, exposicao: np.ndarray, X: pd.DataFrame):
    """Poisson com offset log(exposição), em dados agregados por célula."""
    m = exposicao > 0
    modelo = sm.GLM(y[m], X[m], family=sm.families.Poisson(), offset=np.log(exposicao[m]))
    return modelo.fit()


def dispersao_pearson(ajuste) -> float:
    """Qui-quadrado de Pearson / gl residual (NaN quando não há gl)."""
    return float(ajuste.pearson_chi2 / ajuste.df_resid) if ajuste.df_resid > 0 else np.nan


class Reamostrador:
    """Bootstrap por partida: sorteia partidas com reposição e devolve pesos por linha."""

    def __init__(self, partida_ids: pd.Series, n: int = N_BOOTSTRAP, semente: int = SEMENTE):
        codigos, self.partidas = pd.factorize(partida_ids)
        self.codigos = codigos
        rng = np.random.default_rng(semente)
        n_p = len(self.partidas)
        self.pesos_partida = [np.bincount(rng.integers(0, n_p, n_p), minlength=n_p) for _ in range(n)]

    def pesos(self):
        for w in self.pesos_partida:
            yield w[self.codigos]


def percentis(amostras: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return np.nanpercentile(amostras, 2.5, axis=0), np.nanpercentile(amostras, 97.5, axis=0)


# ---------------------------------------------------------------------------
# Painel de exposição (time × faixa × estado)
# ---------------------------------------------------------------------------

def carregar_painel() -> pd.DataFrame:
    exp = pd.read_parquet(PROCESSED_DIR / "exposicao.parquet")
    tp = pd.read_parquet(PROCESSED_DIR / "time_partida.parquet")
    elo = tp[["partida_id", "mando", "elo_diff"]].rename(columns={"mando": "lado"})
    elo["elo_quintil"] = pd.qcut(elo["elo_diff"], 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"]).astype(str)
    exp = exp.merge(elo[["partida_id", "lado", "elo_quintil"]], on=["partida_id", "lado"], how="left")
    exp["estado"] = np.select([exp["saldo"] < 0, exp["saldo"] == 0], ["perdendo", "empatando"], "vencendo")
    exp["saldo5"] = exp["saldo"].clip(-2, 2).map(lambda s: f"{s:+d}" if s else "0")
    exp["vantagem"] = np.sign(exp["vantagem_numerica"]).map(VANTAGEM)
    exp["faixa_rotulo"] = np.take(FAIXAS, exp["faixa"])
    return exp


def taxas_por_grupo(painel: pd.DataFrame, grupo: str, y: str, ordem: list,
                    reamostrador: Reamostrador) -> pd.DataFrame:
    """Vermelhos por 90 minutos de exposição em cada grupo, com IC bootstrap."""
    codigos = pd.Categorical(painel[grupo], categories=ordem).codes
    k = len(ordem)
    yv, ev = painel[y].to_numpy(float), painel["exposicao"].to_numpy(float)
    amostras = np.array([
        np.bincount(codigos, yv * w, k) / np.bincount(codigos, ev * w, k) * 90
        for w in reamostrador.pesos()
    ])
    ic_inf, ic_sup = percentis(amostras)
    obs, exp = np.bincount(codigos, yv, k), np.bincount(codigos, ev, k)
    return pd.DataFrame({grupo: ordem, "vermelhos": obs.astype(int), "exposicao_min": exp,
                         "taxa_90": obs / exp * 90, "ic95_inf": ic_inf, "ic95_sup": ic_sup})


def aderencia_exposicao(taxas: pd.DataFrame, rotulo: str) -> dict:
    """Qui-quadrado: vermelhos observados × esperados pela exposição de cada grupo."""
    obs = taxas["vermelhos"].to_numpy()
    esp = obs.sum() * taxas["exposicao_min"].to_numpy() / taxas["exposicao_min"].sum()
    chi2, p = stats.chisquare(obs, esp)
    return {"teste": rotulo, "estatistica": chi2, "gl": len(obs) - 1, "p_valor": p,
            "efeito": "V de Cramér", "valor_efeito": cramer_v_aderencia(chi2, obs.sum(), len(obs)),
            "ic95_inf": np.nan, "ic95_sup": np.nan, "n": int(obs.sum())}


def modelo_irr(painel: pd.DataFrame, nome: str, y: str, categoricas: dict, termos: list,
               reamostrador: Reamostrador, numericas: list | None = None) -> pd.DataFrame:
    """Poisson agregado por célula; IRR com IC percentil e p de Wald, ambos bootstrap por partida.

    O p-valor usa z = log(IRR) / DP bootstrap de log(IRR), o que incorpora a
    dependência entre trechos da mesma partida e a sobredispersão.
    """
    covariaveis = list(categoricas) + (numericas or [])
    celula = painel.groupby(covariaveis, sort=True).ngroup().to_numpy()
    celulas = painel.groupby(covariaveis, sort=True, as_index=False).size()[covariaveis]
    X = matriz_desenho(celulas, categoricas, numericas)
    n_c = len(celulas)
    yv, ev = painel[y].to_numpy(float), painel["exposicao"].to_numpy(float)

    idx = [X.columns.get_loc(t) for t in termos]
    amostras = []
    with warnings.catch_warnings():
        # Células vazias em réplicas e modelos sem gl residual geram avisos inofensivos.
        warnings.simplefilter("ignore")
        ajuste = ajustar_poisson(np.bincount(celula, yv, n_c), np.bincount(celula, ev, n_c), X)
        for w in reamostrador.pesos():
            try:
                fit = ajustar_poisson(np.bincount(celula, yv * w, n_c), np.bincount(celula, ev * w, n_c), X)
                amostras.append(np.exp(np.asarray(fit.params)[idx]))
            except (np.linalg.LinAlgError, ValueError):
                amostras.append(np.full(len(idx), np.nan))
    amostras = np.array(amostras)
    ic_inf, ic_sup = percentis(amostras)
    log_irr = np.asarray(ajuste.params)[idx]
    ep_boot = np.nanstd(np.log(amostras), axis=0, ddof=1)
    return pd.DataFrame({
        "modelo": nome, "y": y, "termo": termos,
        "irr": np.exp(log_irr),
        "ic95_inf": ic_inf, "ic95_sup": ic_sup,
        "p_valor": 2 * stats.norm.sf(np.abs(log_irr / ep_boot)),
        "ep_log_irr_bootstrap": ep_boot,
        "replicas_validas": int(np.isfinite(amostras).all(axis=1).sum()),
        "dispersao_pearson": dispersao_pearson(ajuste), "n_celulas": int(ajuste.nobs),
        "vermelhos": int(yv.sum()),
    })


# ---------------------------------------------------------------------------
# H3
# ---------------------------------------------------------------------------

def analisar_h3(painel: pd.DataFrame, reamostrador: Reamostrador) -> dict:
    taxas = pd.concat([
        taxas_por_grupo(painel, "estado", y, ESTADOS, reamostrador).assign(tipo=rotulo)
        for y, rotulo in TIPOS_VERMELHO.items()
    ], ignore_index=True)

    ref = {"estado": "empatando"}
    controles = {"faixa_rotulo": FAIXAS[0], "lado": "mandante", "elo_quintil": "Q3", "vantagem": "igual"}
    termos = ["estado[perdendo]", "estado[vencendo]"]
    termos5 = ["saldo5[-2]", "saldo5[-1]", "saldo5[+1]", "saldo5[+2]"]
    sem_90 = painel[painel["faixa_fina"] != FAIXAS_FINAS.index("90+")]
    especificacoes = [
        ("sem ajuste", painel, "vermelhos", ref, termos, True),
        ("ajustado", painel, "vermelhos", {**ref, **controles}, termos, True),
        ("ajustado — direto", painel, "vermelhos_direto", {**ref, **controles}, termos, True),
        ("ajustado — 2º amarelo", painel, "vermelhos_2o_amarelo", {**ref, **controles}, termos, True),
        ("robustez — saldo em 5 níveis", painel, "vermelhos", {"saldo5": "0", **controles}, termos5, False),
        ("robustez — sem 90+", sem_90, "vermelhos", {**ref, **controles}, termos, False),
        ("robustez — 2015–2024", painel[painel["temporada"] >= 2015], "vermelhos",
         {**ref, **controles}, termos, False),
    ]
    irr = []
    for nome, dados, y, cats, ts, principal in especificacoes:
        r = Reamostrador(dados["partida_id"]) if dados is not painel else reamostrador
        irr.append(modelo_irr(dados, nome, y, cats, ts, r).assign(principal=principal))
        print(f"  H3: {nome}")
    irr = pd.concat(irr, ignore_index=True)

    testes = [aderencia_exposicao(taxas[taxas["tipo"] == "todos"],
                                  "H3 aderência: vermelhos por estado × exposição")]
    for linha in irr[irr["principal"]].itertuples():
        testes.append({"teste": f"H3 IRR {linha.termo} vs empatando ({linha.modelo})",
                       "estatistica": np.nan, "gl": np.nan, "p_valor": linha.p_valor,
                       "efeito": "IRR", "valor_efeito": linha.irr,
                       "ic95_inf": linha.ic95_inf, "ic95_sup": linha.ic95_sup, "n": linha.vermelhos})
    return {"taxas": taxas, "irr": irr, "testes": pd.DataFrame(testes)}


# ---------------------------------------------------------------------------
# H5 — minuto
# ---------------------------------------------------------------------------

def analisar_h5_minuto(painel: pd.DataFrame, reamostrador: Reamostrador) -> dict:
    painel = painel.assign(faixa_fina_rotulo=np.take(FAIXAS_FINAS, painel["faixa_fina"]))
    taxas = pd.concat([
        taxas_por_grupo(painel, "faixa_rotulo", y, FAIXAS, reamostrador).assign(tipo=rotulo)
        for y, rotulo in TIPOS_VERMELHO.items()
    ], ignore_index=True)
    taxas_finas = taxas_por_grupo(painel, "faixa_fina_rotulo", "vermelhos", FAIXAS_FINAS, reamostrador)

    tendencia = pd.concat([
        modelo_irr(painel, f"tendência por faixa — {rotulo}", y, {}, ["faixa"], reamostrador,
                   numericas=["faixa"])
        for y, rotulo in TIPOS_VERMELHO.items()
    ], ignore_index=True)
    print("  H5: minuto")

    testes = []
    for rotulo in TIPOS_VERMELHO.values():
        testes.append(aderencia_exposicao(taxas[taxas["tipo"] == rotulo],
                                          f"H5 aderência: vermelhos por faixa × exposição ({rotulo})"))
    for linha in tendencia.itertuples():
        testes.append({"teste": f"H5 IRR por faixa de 15 min ({linha.modelo})", "estatistica": np.nan,
                       "gl": np.nan, "p_valor": linha.p_valor, "efeito": "IRR", "valor_efeito": linha.irr,
                       "ic95_inf": linha.ic95_inf, "ic95_sup": linha.ic95_sup, "n": linha.vermelhos})
    return {"taxas": taxas, "taxas_finas": taxas_finas, "tendencia": tendencia, "testes": testes}


# ---------------------------------------------------------------------------
# H5 — posição
# ---------------------------------------------------------------------------

def linhas_formacao(formacao: str | float, pontas_no_ataque: bool) -> np.ndarray | None:
    """Jogadores por posição (Goleiro, Zagueiro, Meio-campo, Atacante) numa formação."""
    if not isinstance(formacao, str):
        return None
    try:
        linhas = [int(x) for x in formacao.split("-")]
    except ValueError:
        return None
    if sum(linhas) != 10 or len(linhas) < 3:
        return None
    ataque = linhas[-1] + (linhas[-2] if pontas_no_ataque and len(linhas) >= 4 else 0)
    zaga = linhas[0]
    return np.array([1, zaga, 10 - zaga - ataque, ataque], dtype=float)


def analisar_h5_posicao(eventos: pd.DataFrame, cartoes: pd.DataFrame) -> dict:
    partidas = pd.read_parquet(INTERIM_DIR / "partidas.parquet").set_index("partida_id")
    verm = eventos[(eventos["tipo"] == "vermelho") & eventos["posicao"].notna()].copy()
    verm["formacao"] = np.where(
        verm["lado"] == "mandante",
        partidas["formacao_mandante"].reindex(verm["partida_id"]).to_numpy(),
        partidas["formacao_visitante"].reindex(verm["partida_id"]).to_numpy(),
    )

    linhas, testes = [], []
    for variante, pontas in (("principal", False), ("sensibilidade — pontas no ataque", True)):
        cota = verm["formacao"].map(lambda f: linhas_formacao(f, pontas))
        ok = cota.notna()
        v = verm[ok]
        esperado_por_vermelho = np.vstack(cota[ok].to_numpy()) / 11
        posicao_idx = pd.Categorical(v["posicao"], categories=POSICOES).codes
        obs = np.bincount(posicao_idx, minlength=4)
        esp = esperado_por_vermelho.sum(axis=0)
        chi2, p = stats.chisquare(obs, esp)
        testes.append({"teste": f"H5 aderência: posição dos vermelhos × formação ({variante})",
                       "estatistica": chi2, "gl": 3, "p_valor": p, "efeito": "V de Cramér",
                       "valor_efeito": cramer_v_aderencia(chi2, obs.sum(), 4),
                       "ic95_inf": np.nan, "ic95_sup": np.nan, "n": int(obs.sum())})

        reamostrador = Reamostrador(v["partida_id"])
        amostras = []
        for w in reamostrador.pesos():
            o = np.bincount(posicao_idx, weights=w, minlength=4)
            e = (esperado_por_vermelho * w[:, None]).sum(axis=0)
            amostras.append(o / e)
        ic_inf, ic_sup = percentis(np.array(amostras))
        n = obs.sum()
        p_binom = [stats.binomtest(int(o), int(n), e / n).pvalue for o, e in zip(obs, esp)]
        linhas.append(pd.DataFrame({
            "variante": variante, "posicao": POSICOES, "observados": obs, "esperados": esp,
            "razao_obs_esp": obs / esp, "ic95_inf": ic_inf, "ic95_sup": ic_sup,
            "p_binomial": p_binom,
            "p_holm": multipletests(p_binom, method="holm")[1],
        }))
    formacao = pd.concat(linhas, ignore_index=True)
    formacao["sem_formacao"] = int(verm["formacao"].map(lambda f: linhas_formacao(f, False)).isna().sum())

    # P(expulso | recebeu cartão): unidade = atleta × partida punido com algum cartão.
    c = cartoes[cartoes["atleta"].notna() & cartoes["posicao"].notna()]
    punidos = c.groupby(["partida_id", "clube", "atleta"]).agg(
        posicao=("posicao", "first"), expulso=("cartao", lambda s: (s == "Vermelho").any()))
    tab = punidos.groupby("posicao")["expulso"].agg(["count", "sum"]).reindex(POSICOES)
    inf, sup = proportion_confint(tab["sum"], tab["count"], method="wilson")
    cartao = pd.DataFrame({"posicao": POSICOES, "punidos": tab["count"].to_numpy(),
                           "expulsos": tab["sum"].to_numpy(), "proporcao": (tab["sum"] / tab["count"]).to_numpy(),
                           "ic95_inf": inf.to_numpy(), "ic95_sup": sup.to_numpy()})
    contingencia = np.column_stack([tab["sum"], tab["count"] - tab["sum"]])
    chi2, p, gl, _ = stats.chi2_contingency(contingencia)
    testes.append({"teste": "H5 independência: posição × expulsão entre punidos", "estatistica": chi2,
                   "gl": gl, "p_valor": p, "efeito": "V de Cramér",
                   "valor_efeito": cramer_v_tabela(chi2, contingencia), "ic95_inf": np.nan,
                   "ic95_sup": np.nan, "n": int(tab["count"].sum())})
    pares = []
    for i in range(4):
        for j in range(i + 1, 4):
            _, pz = proportions_ztest(tab["sum"].iloc[[i, j]].to_numpy(), tab["count"].iloc[[i, j]].to_numpy())
            pares.append({"posicao_a": POSICOES[i], "posicao_b": POSICOES[j],
                          "diferenca_pp": 100 * (cartao["proporcao"][i] - cartao["proporcao"][j]),
                          "p_valor": pz})
    pares = pd.DataFrame(pares)
    pares["p_holm"] = multipletests(pares["p_valor"], method="holm")[1]
    print("  H5: posição")
    return {"formacao": formacao, "cartao": cartao, "pares": pares, "testes": testes,
            "vermelhos": verm}


def analisar_h5_posicao_faixa(vermelhos: pd.DataFrame) -> dict:
    """Independência posição × faixa de minuto, com resíduos padronizados ajustados."""
    tabela = pd.crosstab(pd.Categorical(vermelhos["posicao"], categories=POSICOES),
                         pd.Categorical(np.take(FAIXAS, vermelhos["faixa"]), categories=FAIXAS))
    obs = tabela.to_numpy()
    chi2, p, gl, esp = stats.chi2_contingency(obs)
    n = obs.sum()
    lin, col = obs.sum(axis=1, keepdims=True) / n, obs.sum(axis=0, keepdims=True) / n
    residuo = (obs - esp) / np.sqrt(esp * (1 - lin) * (1 - col))
    p_cel = 2 * stats.norm.sf(np.abs(residuo))
    longo = pd.DataFrame({
        "posicao": np.repeat(POSICOES, len(FAIXAS)), "faixa": np.tile(FAIXAS, len(POSICOES)),
        "observados": obs.ravel(), "esperados": esp.ravel(), "residuo_ajustado": residuo.ravel(),
        "p_valor": p_cel.ravel(), "p_holm": multipletests(p_cel.ravel(), method="holm")[1],
    })
    teste = {"teste": "H5 independência: posição × faixa de minuto (vermelhos)", "estatistica": chi2,
             "gl": gl, "p_valor": p, "efeito": "V de Cramér", "valor_efeito": cramer_v_tabela(chi2, obs),
             "ic95_inf": np.nan, "ic95_sup": np.nan, "n": int(n),
             "obs": f"{(esp < 5).sum()} de {esp.size} células com esperado < 5"}
    return {"celulas": longo, "teste": teste}


# ---------------------------------------------------------------------------

def com_holm(testes: pd.DataFrame) -> pd.DataFrame:
    testes = testes.copy()
    testes["p_holm"] = multipletests(testes["p_valor"], method="holm")[1]
    return testes


def main() -> None:
    TABELAS_DIR.mkdir(parents=True, exist_ok=True)
    painel = carregar_painel()
    eventos = pd.read_parquet(PROCESSED_DIR / "eventos.parquet")
    cartoes = pd.read_parquet(INTERIM_DIR / "cartoes.parquet")
    reamostrador = Reamostrador(painel["partida_id"])

    h3 = analisar_h3(painel, reamostrador)
    h3["testes"] = com_holm(h3["testes"])
    h3["taxas"].to_csv(TABELAS_DIR / "h3_taxas_estado.csv", index=False)
    h3["irr"].to_csv(TABELAS_DIR / "h3_irr.csv", index=False)
    h3["testes"].to_csv(TABELAS_DIR / "h3_testes.csv", index=False)

    minuto = analisar_h5_minuto(painel, reamostrador)
    posicao = analisar_h5_posicao(eventos, cartoes)
    pos_faixa = analisar_h5_posicao_faixa(posicao["vermelhos"])
    h5_testes = com_holm(pd.DataFrame(minuto["testes"] + posicao["testes"] + [pos_faixa["teste"]]))
    minuto["taxas"].to_csv(TABELAS_DIR / "h5_taxas_faixa.csv", index=False)
    minuto["taxas_finas"].to_csv(TABELAS_DIR / "h5_taxas_faixa_fina.csv", index=False)
    minuto["tendencia"].to_csv(TABELAS_DIR / "h5_tendencia.csv", index=False)
    posicao["formacao"].to_csv(TABELAS_DIR / "h5_posicao_formacao.csv", index=False)
    posicao["cartao"].to_csv(TABELAS_DIR / "h5_posicao_cartao.csv", index=False)
    posicao["pares"].to_csv(TABELAS_DIR / "h5_posicao_cartao_pares.csv", index=False)
    pos_faixa["celulas"].to_csv(TABELAS_DIR / "h5_posicao_faixa.csv", index=False)
    h5_testes.to_csv(TABELAS_DIR / "h5_testes.csv", index=False)

    figuras.h3_taxa_estado(h3["taxas"])
    figuras.h3_irr(h3["irr"])
    figuras.h5_taxa_faixa(minuto["taxas"])
    figuras.h5_posicao(posicao["formacao"])
    figuras.h5_posicao_faixa(pos_faixa["celulas"])

    with pd.option_context("display.width", 200, "display.max_colwidth", 80, "display.float_format", "{:.4g}".format):
        print(h3["testes"][["teste", "valor_efeito", "ic95_inf", "ic95_sup", "p_valor", "p_holm"]].to_string(index=False))
        print(h5_testes[["teste", "valor_efeito", "ic95_inf", "ic95_sup", "p_valor", "p_holm"]].to_string(index=False))


if __name__ == "__main__":
    main()
