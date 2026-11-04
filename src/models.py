"""Efeito do cartão vermelho no resultado (H1, H2, H4).

Métodos:
1. Logística multinomial (principal) e ordinal (comparação) do resultado final a
   partir do estado do jogo em landmarks de 5 em 5 minutos. Delas sai o custo da
   expulsão em pontos esperados (ΔPE) por minuto e placar, com IC por simulação dos
   parâmetros (erro-padrão robusto agrupado por partida). A ordinal impõe chances
   proporcionais, rejeitadas pelo AIC; por isso a multinomial é a principal.
2. Pareamento: cada time expulso (1º vermelho até o minuto 90 regulamentar) é
   comparado a times de outras partidas no mesmo minuto, mando e saldo, ainda sem
   vermelho, com Elo próximo. Estima o ATT em pontos.
3. Poisson de gols marcados com e sem inferioridade/superioridade numérica.

Uso: python -m src.models
"""
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.miscmodels.ordinal_model import OrderedModel
from statsmodels.stats.multitest import multipletests

from src import figuras
from src.features import (FAIXAS, LANDMARKS, PONTOS, PROCESSED_DIR, TABELAS_DIR,
                          estimar_acrescimos)
from src.stats_tests import Reamostrador, carregar_painel, modelo_irr

SEMENTE = 42
N_SIMULACOES = 2000
N_BOOTSTRAP = 2000
K_CONTROLES = 5
SALDOS_CENARIO = [-1, 0, 1]
MINUTOS_H2 = (15, 75)  # comparação de custo cedo × tarde


# ---------------------------------------------------------------------------
# Matriz de desenho comum (também usada em src/evaluate.py)
# ---------------------------------------------------------------------------

COLUNAS_ESTADO = ["landmark", "t_restante", "saldo", "vermelhos_mandante", "vermelhos_visitante", "elo_diff"]


def matriz_ordinal(df: pd.DataFrame) -> pd.DataFrame:
    """Covariáveis do modelo de estado, do ponto de vista do mandante.

    - saldo e saldo / sqrt(tempo restante + 1): o mesmo saldo pesa mais perto do fim;
    - tr (fração de 90 min restante): vantagem de mando ainda por jogar;
    - Elo e Elo × tr: a força relativa importa mais quanto mais tempo resta;
    - vermelhos de cada lado e × tr: o custo do vermelho pode depender do tempo restante (H2),
      e lados separados permitem testar a assimetria mandante × visitante (H4).
    """
    tr = df["t_restante"].to_numpy(float) / 90
    elo = df["elo_diff"].to_numpy(float) / 100
    vm = df["vermelhos_mandante"].to_numpy(float)
    vv = df["vermelhos_visitante"].to_numpy(float)
    saldo = df["saldo"].to_numpy(float)
    return pd.DataFrame({
        "saldo": saldo,
        "saldo_escalado": saldo / np.sqrt(df["t_restante"].to_numpy(float) + 1),
        "tr": tr,
        "elo": elo,
        "elo_x_tr": elo * tr,
        "verm_mandante": vm,
        "verm_mandante_x_tr": vm * tr,
        "verm_visitante": vv,
        "verm_visitante_x_tr": vv * tr,
    }, index=df.index)


def ajustar_ordinal(landmarks: pd.DataFrame):
    X = matriz_ordinal(landmarks)
    modelo = OrderedModel(landmarks["resultado"].to_numpy(), X, distr="logit")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return modelo.fit(method="bfgs", maxiter=500, disp=False, cov_type="cluster",
                          cov_kwds={"groups": landmarks["partida_id"].to_numpy()})


def ajustar_multinomial(landmarks: pd.DataFrame):
    X = sm.add_constant(matriz_ordinal(landmarks))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return sm.MNLogit(landmarks["resultado"].to_numpy(), X).fit(
            method="bfgs", maxiter=1000, disp=False, cov_type="cluster",
            cov_kwds={"groups": landmarks["partida_id"].to_numpy()})


# ---------------------------------------------------------------------------
# Cenários e custo da expulsão (ΔPE)
# ---------------------------------------------------------------------------

def cenarios(landmarks: pd.DataFrame) -> pd.DataFrame:
    """Grade minuto × saldo do punido × lado punido, com Elo igual e tempo restante mediano."""
    tr = landmarks.groupby("landmark")["t_restante"].median()
    linhas = []
    for m in LANDMARKS:
        for s in SALDOS_CENARIO:
            for lado in ("mandante", "visitante"):
                linhas.append({"landmark": m, "saldo_punido": s, "lado_punido": lado,
                               "t_restante": tr[m], "elo_diff": 0.0})
    return pd.DataFrame(linhas)


def estados_cenario(c: pd.DataFrame, com_vermelho: bool) -> pd.DataFrame:
    """Estado do ponto de vista do mandante, com ou sem o vermelho no lado punido."""
    mand = c["lado_punido"] == "mandante"
    return pd.DataFrame({
        "landmark": c["landmark"], "t_restante": c["t_restante"], "elo_diff": c["elo_diff"],
        "saldo": np.where(mand, c["saldo_punido"], -c["saldo_punido"]),
        "vermelhos_mandante": np.where(mand & com_vermelho, 1, 0),
        "vermelhos_visitante": np.where(~mand & com_vermelho, 1, 0),
    })


def pontos_esperados_punido(probs: np.ndarray, lado_punido: pd.Series) -> np.ndarray:
    """PE do time punido: 3·P(vitória dele) + P(empate). probs = [D, E, V] do mandante."""
    pe_mand = 3 * probs[..., 2] + probs[..., 1]
    pe_vis = 3 * probs[..., 0] + probs[..., 1]
    return np.where((lado_punido == "mandante").to_numpy(), pe_mand, pe_vis)


def custo_expulsao(predizer, c: pd.DataFrame) -> np.ndarray:
    """ΔPE = PE(com vermelho) − PE(sem), para o time punido. `predizer`: DataFrame -> probs."""
    com = predizer(estados_cenario(c, True))
    sem = predizer(estados_cenario(c, False))
    return pontos_esperados_punido(com, c["lado_punido"]) - pontos_esperados_punido(sem, c["lado_punido"])


def preditor_ordinal(ajuste):
    """(vetor de parâmetros, estados) -> probs [D, E, V], para a ordinal."""
    def prever(p, estado):
        return ajuste.model.predict(p, exog=matriz_ordinal(estado).to_numpy())
    return np.asarray(ajuste.params), np.asarray(ajuste.cov_params()), prever


def preditor_multinomial(ajuste):
    """(vetor de parâmetros, estados) -> probs [D, E, V], para a multinomial.

    O vetor segue a ordem de cov_params(): todos os coeficientes da equação E vs D,
    depois os da equação V vs D (achatamento por coluna).
    """
    k, j = ajuste.params.shape
    nomes = list(ajuste.params.index)

    def prever(p, estado):
        X = sm.add_constant(matriz_ordinal(estado), has_constant="add")[nomes].to_numpy()
        return ajuste.model.predict(np.reshape(p, (k, j), order="F"), exog=X)
    return np.asarray(ajuste.params).ravel(order="F"), np.asarray(ajuste.cov_params()), prever


def custo_com_ic(preditor, c: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """ΔPE pontual e simulações com parâmetros ~ N(β̂, V robusta por partida)."""
    params, cov, prever = preditor
    com, sem = estados_cenario(c, True), estados_cenario(c, False)

    def delta(p):
        return (pontos_esperados_punido(prever(p, com), c["lado_punido"])
                - pontos_esperados_punido(prever(p, sem), c["lado_punido"]))

    rng = np.random.default_rng(SEMENTE)
    draws = rng.multivariate_normal(params, cov, size=N_SIMULACOES)
    return delta(params), np.array([delta(p) for p in draws])


def teste_simulado(nome: str, valor: float, sims: np.ndarray, efeito: str = "ΔPE") -> dict:
    """p bilateral por aproximação normal com o DP das simulações."""
    dp = sims.std(ddof=1)
    return {"teste": nome, "efeito": efeito, "valor_efeito": valor,
            "ic95_inf": np.percentile(sims, 2.5), "ic95_sup": np.percentile(sims, 97.5),
            "p_valor": 2 * stats.norm.sf(abs(valor / dp))}


def teste_wald(ajuste, nome: str, combinacoes: list[dict]) -> dict:
    """Wald conjunto para H0: R·β = 0 (cada dict mapeia parâmetro -> peso)."""
    nomes = list(ajuste.params.index)
    R = np.zeros((len(combinacoes), len(nomes)))
    for i, comb in enumerate(combinacoes):
        for p, w in comb.items():
            R[i, nomes.index(p)] = w
    b = R @ np.asarray(ajuste.params)
    V = R @ np.asarray(ajuste.cov_params()) @ R.T
    chi2 = float(b @ np.linalg.solve(V, b))
    return {"teste": nome, "efeito": "Wald χ²", "valor_efeito": chi2, "ic95_inf": np.nan,
            "ic95_sup": np.nan, "p_valor": float(stats.chi2.sf(chi2, len(combinacoes)))}


def analisar_estado(landmarks: pd.DataFrame) -> dict:
    """Modelos de estado do jogo: multinomial (principal) e ordinal (comparação).

    A ordinal impõe chances proporcionais; a multinomial não. A escolha da principal
    segue o AIC (tabela h1_modelo_estado_ajuste.csv) e é conferida na validação temporal.
    """
    ordinal = ajustar_ordinal(landmarks)
    multi = ajustar_multinomial(landmarks)
    c = cenarios(landmarks)
    custo = c.copy()
    sims = {}
    for nome, preditor in (("multinomial", preditor_multinomial(multi)), ("ordinal", preditor_ordinal(ordinal))):
        pont, sim = custo_com_ic(preditor, c)
        custo[f"delta_pe_{nome}"] = pont
        custo[f"ic95_inf_{nome}"] = np.percentile(sim, 2.5, axis=0)
        custo[f"ic95_sup_{nome}"] = np.percentile(sim, 97.5, axis=0)
        sims[nome] = (pont, sim)
    # Colunas genéricas = modelo principal.
    custo["delta_pe"], custo["ic95_inf"], custo["ic95_sup"] = (
        custo["delta_pe_multinomial"], custo["ic95_inf_multinomial"], custo["ic95_sup_multinomial"])

    def idx(m, s, lado):
        return int(np.flatnonzero((c["landmark"] == m) & (c["saldo_punido"] == s) & (c["lado_punido"] == lado))[0])

    i_m, i_v = idx(45, 0, "mandante"), idx(45, 0, "visitante")
    cedo, tarde = MINUTOS_H2
    testes = []
    for nome, (pont, sim) in sims.items():
        principal = nome == "multinomial"
        h1 = (sim[:, i_m] + sim[:, i_v]) / 2
        testes.append({**teste_simulado(f"H1 ΔPE de um vermelho no minuto 45, empatando (média dos lados) [{nome}]",
                                        (pont[i_m] + pont[i_v]) / 2, h1), "principal": principal})
        dif, val = 0, 0
        for lado in ("mandante", "visitante"):
            dif = dif + (sim[:, idx(cedo, 0, lado)] - sim[:, idx(tarde, 0, lado)]) / 2
            val += (pont[idx(cedo, 0, lado)] - pont[idx(tarde, 0, lado)]) / 2
        testes.append({**teste_simulado(f"H2 ΔPE(min {cedo}) − ΔPE(min {tarde}), empatando (média dos lados) [{nome}]",
                                        val, dif), "principal": principal})
        testes.append({**teste_simulado(f"H4 ΔPE mandante punido − ΔPE visitante punido (min 45, empatando) [{nome}]",
                                        pont[i_m] - pont[i_v], sim[:, i_m] - sim[:, i_v]), "principal": principal})

    verm = ["verm_mandante", "verm_mandante_x_tr", "verm_visitante", "verm_visitante_x_tr"]
    inter = ["verm_mandante_x_tr", "verm_visitante_x_tr"]
    nomes_multi = [f"{eq}:{p}" for eq, p in multi.cov_params().index]
    multi_vetor = pd.Series(np.asarray(multi.params).ravel(order="F"), index=nomes_multi)

    class _Wald:  # adaptador: Wald sobre o vetor achatado da multinomial
        params = multi_vetor
        def cov_params(self):
            return pd.DataFrame(np.asarray(multi.cov_params()), index=nomes_multi, columns=nomes_multi)

    testes.append({**teste_wald(_Wald(), "H1 Wald: vermelhos não afetam o resultado [multinomial]",
                                [{f"{eq}:{p}": 1} for eq in ("1", "2") for p in verm]), "principal": True})
    testes.append({**teste_wald(_Wald(), "H2 Wald: custo não depende do tempo restante [multinomial]",
                                [{f"{eq}:{p}": 1} for eq in ("1", "2") for p in inter]), "principal": True})
    testes.append({**teste_wald(ordinal, "H1 Wald: vermelhos não afetam o resultado [ordinal]",
                                [{p: 1} for p in verm]), "principal": False})
    testes.append({**teste_wald(ordinal, "H2 Wald: custo não depende do tempo restante [ordinal]",
                                [{p: 1} for p in inter]), "principal": False})

    coef = []
    for nome, ajuste in (("ordinal", ordinal), ("multinomial", multi)):
        if nome == "ordinal":
            par, ep, p = ajuste.params, ajuste.bse, ajuste.pvalues
            idx_nomes = list(par.index)
        else:
            par, ep, p = multi_vetor, pd.Series(np.sqrt(np.diag(np.asarray(multi.cov_params()))), index=nomes_multi), None
            idx_nomes = nomes_multi
            p = pd.Series(2 * stats.norm.sf(np.abs(par / ep)), index=nomes_multi)
        coef.append(pd.DataFrame({"modelo": nome, "parametro": idx_nomes, "coef": np.asarray(par),
                                  "ep_robusto": np.asarray(ep), "p_valor": np.asarray(p)}))
    coef = pd.concat(coef, ignore_index=True)
    coef["parametro"] = coef["parametro"].str.replace("^1:", "E vs D: ", regex=True).str.replace("^2:", "V vs D: ", regex=True)

    ajuste_info = pd.DataFrame([
        {"modelo": "ordinal", "log_verossimilhanca": ordinal.llf, "aic": ordinal.aic,
         "n_parametros": len(ordinal.params), "n_linhas": int(ordinal.nobs)},
        {"modelo": "multinomial", "log_verossimilhanca": multi.llf, "aic": multi.aic,
         "n_parametros": int(np.asarray(multi.params).size), "n_linhas": int(multi.nobs)},
    ])
    ajuste_info["delta_aic"] = ajuste_info["aic"] - ajuste_info["aic"].min()
    diff = (custo["delta_pe_ordinal"] - custo["delta_pe_multinomial"]).abs()
    ajuste_info["dif_abs_media_delta_pe"] = diff.mean()
    ajuste_info["dif_abs_max_delta_pe"] = diff.max()
    print("  modelos de estado ajustados")
    return {"coef": coef, "custo": custo, "testes": testes, "ajuste_info": ajuste_info}


# ---------------------------------------------------------------------------
# Pareamento
# ---------------------------------------------------------------------------

def tratados(eventos: pd.DataFrame, partidas: pd.DataFrame) -> pd.DataFrame:
    """1º vermelho de cada partida até o minuto 90 regulamentar, do ponto de vista do punido."""
    v = eventos[eventos["tipo"] == "vermelho"].groupby("partida_id").head(1)
    v = v[~((v["tempo"] == 2) & (v["acrescimo"] > 0))].copy()
    info = partidas.set_index("partida_id")
    sinal = np.where(v["lado"] == "mandante", 1, -1)
    v["elo_lado"] = sinal * info["elo_diff"].reindex(v["partida_id"]).to_numpy()
    pts = np.where(v["lado"] == "mandante", info["pontos_mandante"].reindex(v["partida_id"]),
                   info["pontos_visitante"].reindex(v["partida_id"]))
    v["pontos"] = pts
    v["saldo_c"] = v["saldo_lado_antes"].clip(-2, 2)
    return v[["partida_id", "lado", "tempo", "minuto_base", "acrescimo", "faixa", "saldo_lado_antes",
              "saldo_c", "elo_lado", "pontos", "vermelho_tipo"]].reset_index(drop=True)


def parear(trat: pd.DataFrame, eventos: pd.DataFrame, partidas: pd.DataFrame) -> pd.DataFrame:
    """k controles por tratado: mesmo lado, mesmo saldo (−2..2) e sem vermelho até o minuto."""
    acr = estimar_acrescimos(partidas, eventos)
    d1 = (45 + acr["acr1"]).reindex(partidas["partida_id"]).to_numpy()
    ids = partidas["partida_id"].to_numpy()
    info = partidas.set_index("partida_id")

    # Produto tratado × partida candidata (todas as partidas, exceto a do tratado).
    n_t, n_p = len(trat), len(ids)
    cand = pd.DataFrame({
        "tratado": np.repeat(np.arange(n_t), n_p),
        "partida_id": np.tile(ids, n_t),
    })
    t1 = (trat["minuto_base"] + trat["acrescimo"]).to_numpy()
    d1_c = np.tile(d1, n_t)
    tempo = np.repeat(trat["tempo"].to_numpy(), n_p)
    cand["t"] = np.where(tempo == 1, np.minimum(np.repeat(t1, n_p), d1_c),
                         d1_c + np.repeat(trat["minuto_base"].to_numpy() - 45, n_p)).astype(float)
    cand = cand[cand["partida_id"].to_numpy() != np.repeat(trat["partida_id"].to_numpy(), n_p)]

    # Estado estritamente antes do minuto do vermelho tratado.
    muda = eventos[eventos["tipo"].isin(["gol", "vermelho"])][
        ["partida_id", "t", "gols_mandante_depois", "gols_visitante_depois",
         "jogadores_mandante_depois", "jogadores_visitante_depois"]].sort_values("t")
    cand = pd.merge_asof(cand.sort_values("t"), muda, on="t", by="partida_id",
                         direction="backward", allow_exact_matches=False)
    gm = cand["gols_mandante_depois"].fillna(0).to_numpy()
    gv = cand["gols_visitante_depois"].fillna(0).to_numpy()
    sem_vermelho = (cand["jogadores_mandante_depois"].fillna(11).to_numpy() == 11) & \
                   (cand["jogadores_visitante_depois"].fillna(11).to_numpy() == 11)
    lado = trat["lado"].to_numpy()[cand["tratado"].to_numpy()]
    sinal = np.where(lado == "mandante", 1, -1)
    saldo_c = np.clip(sinal * (gm - gv), -2, 2)
    ok = sem_vermelho & (saldo_c == trat["saldo_c"].to_numpy()[cand["tratado"].to_numpy()])
    cand = cand.loc[ok, ["tratado", "partida_id"]].copy()
    sinal = sinal[ok]

    cand["elo_lado"] = sinal * info["elo_diff"].reindex(cand["partida_id"]).to_numpy()
    cand["pontos"] = np.where(sinal == 1, info["pontos_mandante"].reindex(cand["partida_id"]),
                              info["pontos_visitante"].reindex(cand["partida_id"]))
    cand["distancia"] = np.abs(cand["elo_lado"].to_numpy() - trat["elo_lado"].to_numpy()[cand["tratado"]])
    cand = cand.sort_values(["tratado", "distancia", "partida_id"])
    return cand.groupby("tratado").head(K_CONTROLES).reset_index(drop=True)


def analisar_pareamento(eventos: pd.DataFrame, partidas: pd.DataFrame) -> dict:
    trat = tratados(eventos, partidas)
    controles = parear(trat, eventos, partidas)
    ctrl = controles.groupby("tratado").agg(pontos_controle=("pontos", "mean"),
                                            elo_controle=("elo_lado", "mean"),
                                            n_controles=("pontos", "size"))
    trat = trat.join(ctrl)
    trat["diferenca"] = trat["pontos"] - trat["pontos_controle"]
    trat["faixa_rotulo"] = np.take(FAIXAS, trat["faixa"])
    trat["estado"] = np.select([trat["saldo_lado_antes"] < 0, trat["saldo_lado_antes"] == 0],
                               ["perdendo", "empatando"], "vencendo")

    rng = np.random.default_rng(SEMENTE)
    grupos = [("todos", trat.index)]
    grupos += [(f"faixa {f}", trat.index[trat["faixa_rotulo"] == f]) for f in FAIXAS if (trat["faixa_rotulo"] == f).any()]
    grupos += [(f"lado {l}", trat.index[trat["lado"] == l]) for l in ("mandante", "visitante")]
    grupos += [(f"estado {e}", trat.index[trat["estado"] == e]) for e in ("perdendo", "empatando", "vencendo")]
    grupos += [(f"tipo {t}", trat.index[trat["vermelho_tipo"] == t]) for t in ("direto", "2o_amarelo")]
    linhas = []
    for nome, idx in grupos:
        d = trat.loc[idx, "diferenca"].dropna().to_numpy()
        boot = np.array([rng.choice(d, size=len(d)).mean() for _ in range(N_BOOTSTRAP)])
        linhas.append({"grupo": nome, "n_tratados": len(d), "pontos_tratados": trat.loc[idx, "pontos"].mean(),
                       "pontos_controles": trat.loc[idx, "pontos_controle"].mean(), "att": d.mean(),
                       "ic95_inf": np.percentile(boot, 2.5), "ic95_sup": np.percentile(boot, 97.5),
                       "p_valor": 2 * stats.norm.sf(abs(d.mean() / boot.std(ddof=1)))})
    att = pd.DataFrame(linhas)
    # O 1º vermelho em 90+ fica fora, então a última faixa vai só até 90.
    att["grupo"] = att["grupo"].str.replace("faixa 76–90+", "faixa 76–90", regex=False)

    # H4: diferença de ATT mandante − visitante (bootstrap independente nos dois grupos).
    d_m = trat.loc[trat["lado"] == "mandante", "diferenca"].dropna().to_numpy()
    d_v = trat.loc[trat["lado"] == "visitante", "diferenca"].dropna().to_numpy()
    boot = np.array([rng.choice(d_m, len(d_m)).mean() - rng.choice(d_v, len(d_v)).mean()
                     for _ in range(N_BOOTSTRAP)])
    valor = d_m.mean() - d_v.mean()
    diferenca_lados = {"teste": "H4 pareamento: ATT mandante − ATT visitante", "efeito": "ΔATT",
                       "valor_efeito": valor, "ic95_inf": np.percentile(boot, 2.5),
                       "ic95_sup": np.percentile(boot, 97.5),
                       "p_valor": 2 * stats.norm.sf(abs(valor / boot.std(ddof=1)))}

    # Equilíbrio do Elo após o pareamento (diferença padronizada).
    dp = np.sqrt((trat["elo_lado"].var() + trat["elo_controle"].var()) / 2)
    equilibrio = pd.DataFrame([{
        "tratados": len(trat), "sem_controle": int(trat["n_controles"].isna().sum()),
        "controles_por_tratado_min": trat["n_controles"].min(),
        "elo_tratados": trat["elo_lado"].mean(), "elo_controles": trat["elo_controle"].mean(),
        "diferenca_padronizada_elo": (trat["elo_lado"].mean() - trat["elo_controle"].mean()) / dp,
        "distancia_elo_mediana": controles["distancia"].median(),
    }])
    print("  pareamento concluído")
    return {"att": att, "equilibrio": equilibrio, "tratados": trat, "diferenca_lados": diferenca_lados}


# ---------------------------------------------------------------------------
# Poisson de gols
# ---------------------------------------------------------------------------

def efeito_fixo_partida(painel: pd.DataFrame) -> pd.DataFrame:
    """Robustez: Poisson com efeito fixo de partida, só nas partidas com vermelho (antes × depois)."""
    com_verm = painel.groupby("partida_id")["vermelhos"].sum()
    p = painel[painel["partida_id"].isin(com_verm[com_verm > 0].index)]
    cel = p.groupby(["partida_id", "lado", "vantagem", "estado"], as_index=False)[["gols_pro", "exposicao"]].sum()
    cel = cel[cel["exposicao"] > 0]
    X = pd.get_dummies(cel[["partida_id", "lado", "vantagem", "estado"]].astype(str), drop_first=False, dtype=float)
    X = X.drop(columns=["partida_id_" + str(cel["partida_id"].iloc[0]), "lado_mandante", "vantagem_igual",
                        "estado_empatando"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = sm.GLM(cel["gols_pro"].to_numpy(), sm.add_constant(X), family=sm.families.Poisson(),
                     offset=np.log(cel["exposicao"].to_numpy())).fit(
            cov_type="cluster", cov_kwds={"groups": cel["partida_id"].to_numpy()})
    linhas = []
    for termo in ("vantagem_inferior", "vantagem_superior"):
        ic = np.exp(fit.conf_int().loc[termo].to_numpy())
        linhas.append({"modelo": "efeito fixo de partida (partidas com vermelho)", "y": "gols_pro",
                       "termo": termo.replace("vantagem_", "vantagem[") + "]", "irr": np.exp(fit.params[termo]),
                       "ic95_inf": ic[0], "ic95_sup": ic[1], "p_valor": fit.pvalues[termo],
                       "n_celulas": int(fit.nobs), "partidas": int(cel["partida_id"].nunique())})
    return pd.DataFrame(linhas)


def analisar_gols() -> pd.DataFrame:
    painel = carregar_painel()
    controles = {"faixa_rotulo": FAIXAS[0], "saldo5": "0", "elo_quintil": "Q3"}
    termos = ["vantagem[inferior]", "vantagem[superior]"]
    linhas = [modelo_irr(painel, "todos", "gols_pro", {"vantagem": "igual", "lado": "mandante", **controles},
                         termos, Reamostrador(painel["partida_id"]))]
    for lado in ("mandante", "visitante"):
        sub = painel[painel["lado"] == lado]
        linhas.append(modelo_irr(sub, f"lado {lado}", "gols_pro", {"vantagem": "igual", **controles},
                                 termos, Reamostrador(sub["partida_id"])))
    linhas.append(efeito_fixo_partida(painel))
    print("  Poisson de gols concluída")
    return pd.concat(linhas, ignore_index=True)


# ---------------------------------------------------------------------------

def main() -> None:
    TABELAS_DIR.mkdir(parents=True, exist_ok=True)
    landmarks = pd.read_parquet(PROCESSED_DIR / "landmarks.parquet")
    eventos = pd.read_parquet(PROCESSED_DIR / "eventos.parquet")
    partidas = pd.read_parquet(PROCESSED_DIR / "partidas.parquet")

    estado = analisar_estado(landmarks)
    pareamento = analisar_pareamento(eventos, partidas)
    gols = analisar_gols()

    testes = list(estado["testes"])
    geral = pareamento["att"].iloc[0]
    testes.append({"teste": "H1 pareamento: ATT em pontos (1º vermelho até o minuto 90)", "efeito": "ATT",
                   "valor_efeito": geral["att"], "ic95_inf": geral["ic95_inf"],
                   "ic95_sup": geral["ic95_sup"], "p_valor": geral["p_valor"], "principal": True})
    att = pareamento["att"].set_index("grupo")
    for lado in ("mandante", "visitante"):
        r = att.loc[f"lado {lado}"]
        testes.append({"teste": f"H4 pareamento: ATT com o {lado} punido", "efeito": "ATT",
                       "valor_efeito": r["att"], "ic95_inf": r["ic95_inf"], "ic95_sup": r["ic95_sup"],
                       "p_valor": r["p_valor"], "principal": True})
    dif = pareamento["diferenca_lados"]
    testes.append({**dif, "principal": True})
    for linha in gols[gols["modelo"] == "todos"].itertuples():
        testes.append({"teste": f"Gols marcados com {linha.termo} vs igualdade numérica", "efeito": "IRR",
                       "valor_efeito": linha.irr, "ic95_inf": linha.ic95_inf, "ic95_sup": linha.ic95_sup,
                       "p_valor": linha.p_valor, "principal": True})
    testes = pd.DataFrame(testes)
    # Holm na família principal; as linhas da ordinal (comparação) ficam fora da correção.
    testes["p_holm"] = np.nan
    princ = testes["principal"].to_numpy(bool)
    testes.loc[princ, "p_holm"] = multipletests(testes.loc[princ, "p_valor"], method="holm")[1]

    estado["coef"].to_csv(TABELAS_DIR / "h1_modelo_estado_coeficientes.csv", index=False)
    estado["custo"].to_csv(TABELAS_DIR / "h1_custo_minuto.csv", index=False)
    estado["ajuste_info"].to_csv(TABELAS_DIR / "h1_modelo_estado_ajuste.csv", index=False)
    pareamento["att"].to_csv(TABELAS_DIR / "h1_pareamento_att.csv", index=False)
    pareamento["equilibrio"].to_csv(TABELAS_DIR / "h1_pareamento_equilibrio.csv", index=False)
    gols.to_csv(TABELAS_DIR / "h1_gols_irr.csv", index=False)
    testes.to_csv(TABELAS_DIR / "h1_testes.csv", index=False)

    figuras.h1_custo_minuto(estado["custo"])
    figuras.h1_pareamento(pareamento["att"])
    figuras.h1_gols(gols)

    with pd.option_context("display.width", 220, "display.max_colwidth", 90, "display.float_format", "{:.4g}".format):
        print(testes[["teste", "valor_efeito", "ic95_inf", "ic95_sup", "p_valor", "p_holm"]].to_string(index=False))
        print(estado["ajuste_info"].to_string(index=False))
        print(pareamento["equilibrio"].to_string(index=False))


if __name__ == "__main__":
    main()
