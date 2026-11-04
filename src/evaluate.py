"""Comparação de modelos de resultado a partir do estado do jogo (seção "Métodos Avaliados").

Validação temporal: treino em 2014–2021, teste em 2022–2024. Hiperparâmetros por
k-fold agrupado por partida dentro do treino (landmarks do mesmo jogo nunca ficam
dos dois lados). Métricas: log-loss, Brier, RPS, AUC um contra todos, acurácia,
F1 macro, com IC bootstrap por partida no teste. SHAP no LightGBM.

Uso: python -m src.evaluate
"""
import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold, ParameterGrid

from src import figuras
from src.features import PROCESSED_DIR, TABELAS_DIR
from src.models import (COLUNAS_ESTADO, ajustar_multinomial, ajustar_ordinal, cenarios,
                        custo_expulsao, matriz_ordinal, preditor_multinomial, preditor_ordinal)

SEMENTE = 42
ULTIMA_TEMPORADA_TREINO = 2021
N_BOOTSTRAP = 1000
N_SHAP = 3000
CLASSES = ["D", "E", "V"]

GRADES = {
    "random forest": {"min_samples_leaf": [50, 200], "max_depth": [12, None]},
    "LightGBM": {"num_leaves": [15, 31], "min_child_samples": [100, 400]},
}


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------

def brier(y: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Brier multiclasse por linha: soma dos erros quadráticos nas 3 classes."""
    return ((p - np.eye(3)[y]) ** 2).sum(axis=1)


def rps(y: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Ranked probability score por linha (resultados ordenados D < E < V)."""
    acum_p = np.cumsum(p, axis=1)[:, :2]
    acum_y = np.cumsum(np.eye(3)[y], axis=1)[:, :2]
    return ((acum_p - acum_y) ** 2).sum(axis=1) / 2


def perda_log(y: np.ndarray, p: np.ndarray) -> np.ndarray:
    return -np.log(np.clip(p[np.arange(len(y)), y], 1e-15, 1))


def metricas(y: np.ndarray, p: np.ndarray | None, pred: np.ndarray) -> dict:
    m = {"acuracia": accuracy_score(y, pred), "f1_macro": f1_score(y, pred, average="macro")}
    if p is None:
        return {**m, "log_loss": np.nan, "brier": np.nan, "rps": np.nan, "auc_ovr": np.nan}
    return {**m, "log_loss": perda_log(y, p).mean(), "brier": brier(y, p).mean(), "rps": rps(y, p).mean(),
            "auc_ovr": roc_auc_score(y, p, multi_class="ovr", average="macro")}


def ic_bootstrap(partidas: np.ndarray, valores: dict, n: int = N_BOOTSTRAP) -> dict:
    """IC 95% por partida para a média de cada vetor de perdas por linha."""
    codigos, unicas = pd.factorize(partidas)
    rng = np.random.default_rng(SEMENTE)
    somas = {k: np.bincount(codigos, v, len(unicas)) for k, v in valores.items()}
    cont = np.bincount(codigos, minlength=len(unicas))
    saida = {k: [] for k in valores}
    for _ in range(n):
        w = np.bincount(rng.integers(0, len(unicas), len(unicas)), minlength=len(unicas))
        for k in valores:
            saida[k].append((somas[k] * w).sum() / (cont * w).sum())
    return {k: (np.percentile(v, 2.5), np.percentile(v, 97.5)) for k, v in saida.items()}


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------

def novo_modelo(nome: str, params: dict):
    if nome == "random forest":
        return RandomForestClassifier(n_estimators=300, random_state=SEMENTE, n_jobs=-1, **params)
    return lgb.LGBMClassifier(objective="multiclass", n_estimators=400, learning_rate=0.03,
                              subsample=0.8, subsample_freq=1, colsample_bytree=1.0,
                              random_state=SEMENTE, verbose=-1, **params)


def ajustar_arvore(nome: str, treino: pd.DataFrame) -> tuple:
    """Escolhe hiperparâmetros por log-loss em GroupKFold(5) por partida e reajusta no treino todo."""
    X, y, g = treino[COLUNAS_ESTADO], treino["resultado"].to_numpy(), treino["partida_id"].to_numpy()
    resultados = []
    for params in ParameterGrid(GRADES[nome]):
        perdas = []
        for tr, va in GroupKFold(n_splits=5).split(X, y, g):
            m = novo_modelo(nome, params).fit(X.iloc[tr], y[tr])
            perdas.append(log_loss(y[va], m.predict_proba(X.iloc[va]), labels=[0, 1, 2]))
        resultados.append({"modelo": nome, **{k: str(v) for k, v in params.items()},
                           "log_loss_cv": float(np.mean(perdas))})
    melhor = min(resultados, key=lambda r: r["log_loss_cv"])
    params = {k: (None if v == "None" else int(v)) for k, v in melhor.items() if k in GRADES[nome]}
    return novo_modelo(nome, params).fit(X, y), pd.DataFrame(resultados)


def prever_estatistico(ajuste, preditor, df: pd.DataFrame) -> np.ndarray:
    params, _, prever = preditor(ajuste)
    return prever(params, df)


def main() -> None:
    TABELAS_DIR.mkdir(parents=True, exist_ok=True)
    lm = pd.read_parquet(PROCESSED_DIR / "landmarks.parquet")
    elo = pd.read_parquet(PROCESSED_DIR / "elo.parquet").set_index("partida_id")
    treino = lm[lm["temporada"] <= ULTIMA_TEMPORADA_TREINO].reset_index(drop=True)
    teste = lm[lm["temporada"] > ULTIMA_TEMPORADA_TREINO].reset_index(drop=True)
    y_te = teste["resultado"].to_numpy()

    probs = {}
    freq = np.bincount(treino["resultado"], minlength=3) / len(treino)
    probs["frequências históricas"] = np.tile(freq, (len(teste), 1))
    probs["Elo pré-jogo"] = elo.loc[teste["partida_id"], ["p_elo_D", "p_elo_E", "p_elo_V"]].to_numpy()
    ordinal = ajustar_ordinal(treino)
    multi = ajustar_multinomial(treino)
    probs["logística ordinal"] = prever_estatistico(ordinal, preditor_ordinal, teste)
    probs["logística multinomial"] = prever_estatistico(multi, preditor_multinomial, teste)
    print("  estatísticos ajustados")

    arvores, grades = {}, []
    for nome in GRADES:
        arvores[nome], grade = ajustar_arvore(nome, treino)
        grades.append(grade)
        probs[nome] = arvores[nome].predict_proba(teste[COLUNAS_ESTADO])
        print(f"  {nome} ajustado")

    # Métricas no teste (todos os landmarks e só os que já têm vermelho).
    com_verm = ((teste["vermelhos_mandante"] + teste["vermelhos_visitante"]) > 0).to_numpy()
    linhas = []
    sempre = np.full(len(teste), 2)
    for subconj, mask in (("todos os landmarks", np.ones(len(teste), bool)), ("landmarks com vermelho", com_verm)):
        linhas.append({"modelo": "sempre mandante", "subconjunto": subconj,
                       **metricas(y_te[mask], None, sempre[mask])})
        for nome, p in probs.items():
            ic = ic_bootstrap(teste["partida_id"].to_numpy()[mask],
                              {"log_loss": perda_log(y_te[mask], p[mask]), "rps": rps(y_te[mask], p[mask])})
            linhas.append({"modelo": nome, "subconjunto": subconj,
                           **metricas(y_te[mask], p[mask], p[mask].argmax(axis=1)),
                           "log_loss_ic95_inf": ic["log_loss"][0], "log_loss_ic95_sup": ic["log_loss"][1],
                           "rps_ic95_inf": ic["rps"][0], "rps_ic95_sup": ic["rps"][1]})
    tabela = pd.DataFrame(linhas)
    tabela["n_linhas"] = np.where(tabela["subconjunto"] == "todos os landmarks", len(teste), int(com_verm.sum()))

    # Diferença pareada de log-loss contra a multinomial (IC por partida).
    ref = perda_log(y_te, probs["logística multinomial"])
    difs = []
    for nome, p in probs.items():
        if nome == "logística multinomial":
            continue
        d = perda_log(y_te, p) - ref
        ic = ic_bootstrap(teste["partida_id"].to_numpy(), {"d": d})["d"]
        difs.append({"modelo": nome, "dif_log_loss_vs_multinomial": d.mean(), "ic95_inf": ic[0], "ic95_sup": ic[1]})
    difs = pd.DataFrame(difs)

    melhor = tabela[tabela["subconjunto"] == "todos os landmarks"].dropna(subset=["log_loss"]) \
        .sort_values("log_loss").iloc[0]["modelo"]
    cm = pd.DataFrame(confusion_matrix(y_te, probs[melhor].argmax(axis=1), labels=[0, 1, 2]),
                      index=[f"real {c}" for c in CLASSES], columns=[f"previsto {c}" for c in CLASSES])

    # Curva de custo implícita em cada modelo (cenários do models.py).
    c = cenarios(lm)
    curvas = c.copy()
    curvas["logística multinomial"] = custo_expulsao(lambda e: prever_estatistico(multi, preditor_multinomial, e), c)
    curvas["logística ordinal"] = custo_expulsao(lambda e: prever_estatistico(ordinal, preditor_ordinal, e), c)
    for nome, m in arvores.items():
        curvas[nome] = custo_expulsao(lambda e, m=m: m.predict_proba(e[COLUNAS_ESTADO]), c)

    # SHAP (LightGBM, classe V do mandante, amostra do teste).
    amostra = teste.sample(min(N_SHAP, len(teste)), random_state=SEMENTE)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        valores = shap.TreeExplainer(arvores["LightGBM"]).shap_values(amostra[COLUNAS_ESTADO])
    valores = np.asarray(valores)
    if valores.ndim == 3 and valores.shape[0] == 3:  # formato antigo: lista por classe
        valores = np.moveaxis(valores, 0, -1)
    shap_v = pd.DataFrame(valores[:, :, 2], columns=COLUNAS_ESTADO, index=amostra.index)
    importancia = pd.DataFrame({"variavel": COLUNAS_ESTADO,
                                "shap_medio_abs_V": np.abs(valores[:, :, 2]).mean(axis=0),
                                "shap_medio_abs_todas": np.abs(valores).mean(axis=(0, 2))}) \
        .sort_values("shap_medio_abs_todas", ascending=False)
    dependencia = amostra[COLUNAS_ESTADO].assign(shap_verm_mandante_V=shap_v["vermelhos_mandante"],
                                                 shap_verm_visitante_V=shap_v["vermelhos_visitante"])

    tabela.to_csv(TABELAS_DIR / "modelos_metricas.csv", index=False)
    difs.to_csv(TABELAS_DIR / "modelos_dif_log_loss.csv", index=False)
    pd.concat(grades).to_csv(TABELAS_DIR / "modelos_grade_cv.csv", index=False)
    cm.to_csv(TABELAS_DIR / "modelos_matriz_confusao.csv")
    curvas.to_csv(TABELAS_DIR / "modelos_custo_curvas.csv", index=False)
    importancia.to_csv(TABELAS_DIR / "modelos_shap_importancia.csv", index=False)
    dependencia.to_csv(TABELAS_DIR / "modelos_shap_dependencia.csv", index=False)

    figuras.modelos_calibracao(y_te, {k: probs[k] for k in
                                      ("logística multinomial", "logística ordinal", "LightGBM")})
    figuras.modelos_custo_comparacao(curvas)
    figuras.modelos_shap_dependencia(dependencia)

    with pd.option_context("display.width", 220, "display.float_format", "{:.4f}".format):
        print(tabela[["modelo", "subconjunto", "log_loss", "brier", "rps", "auc_ovr", "acuracia", "f1_macro"]]
              .to_string(index=False))
        print(difs.to_string(index=False))
        print(f"melhor por log-loss: {melhor}")
        print(cm.to_string())
        print(importancia.to_string(index=False))


if __name__ == "__main__":
    main()
