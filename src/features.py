"""Tabelas analíticas: eventos, estados de jogo, exposição, Elo, partidas e time × partida.

Lê data/interim/ e grava em data/processed/. Também grava os parâmetros e as
métricas do Elo em reports/tabelas/elo_parametros.csv.

Uso: python -m src.features
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.clean import INTERIM_DIR, PRIMEIRA_TEMPORADA_COM_EVENTOS, RAIZ

PROCESSED_DIR = RAIZ / "data" / "processed"
TABELAS_DIR = RAIZ / "reports" / "tabelas"

ULTIMA_TEMPORADA_CALIBRACAO_ELO = 2013  # fora da janela de análise (2014–2024)
ELO_INICIAL = 1500.0
# Prioridade no mesmo minuto: gol antes de cartão; amarelo antes de vermelho (2º amarelo).
PRIORIDADE = {"gol": 0, "amarelo": 1, "vermelho": 2}
PONTOS = {"V": 3, "E": 1, "D": 0}
# Faixas finas de minuto (acréscimos separados); as análises podem agregá-las em FAIXAS.
FAIXAS_FINAS = ["0–15", "16–30", "31–45", "45+", "46–60", "61–75", "76–90", "90+"]
FAIXAS = ["0–15", "16–30", "31–45+", "46–60", "61–75", "76–90+"]
FINA_PARA_FAIXA = [0, 1, 2, 2, 3, 4, 5, 5]
OUTRO_LADO = {"mandante": "visitante", "visitante": "mandante"}
# Partida usada como exemplo nos slides: Santos 3 × 1 Atlético-MG (09/09/2020),
# goleiro do Atlético expulso aos 16' com o jogo 0 × 0.
EXEMPLO_PARTIDA_ID = 6981


# ---------------------------------------------------------------------------
# Eventos
# ---------------------------------------------------------------------------

def classificar_vermelhos(cartoes: pd.DataFrame) -> pd.Series:
    """Classifica cada vermelho como 'direto', '2o_amarelo' ou 'indeterminado'.

    É 2º amarelo quando o mesmo atleta, do mesmo clube, tem um amarelo anterior na
    mesma partida (com a mesma camisa, quando as duas camisas são conhecidas).
    """
    vermelhos = cartoes[cartoes["cartao"] == "Vermelho"]
    amarelos = cartoes[cartoes["cartao"] == "Amarelo"]
    chave = ["partida_id", "clube", "atleta"]
    pares = vermelhos.reset_index().merge(
        amarelos[chave + ["num_camisa", "ordem"]], on=chave, how="left", suffixes=("", "_am")
    )
    camisa_ok = (
        pares["num_camisa"].isna() | pares["num_camisa_am"].isna()
        | (pares["num_camisa"] == pares["num_camisa_am"])
    )
    pares["tem_amarelo_antes"] = pares["ordem_am"].notna() & (pares["ordem_am"] <= pares["ordem"]) & camisa_ok
    segundo = pares.groupby("index")["tem_amarelo_antes"].any()

    tipo = pd.Series("direto", index=vermelhos.index)
    tipo[segundo.reindex(vermelhos.index).to_numpy()] = "2o_amarelo"
    tipo[vermelhos["atleta"].isna()] = "indeterminado"
    return tipo


def montar_eventos(partidas: pd.DataFrame, gols: pd.DataFrame, cartoes: pd.DataFrame) -> pd.DataFrame:
    """Gols e cartões numa linha do tempo única, com placar e jogadores antes/depois."""
    alvo = partidas[partidas["temporada"] >= PRIMEIRA_TEMPORADA_COM_EVENTOS]
    lados = alvo.set_index("partida_id")[["mandante", "visitante"]]

    colunas = ["partida_id", "clube", "atleta", "posicao", "minuto", "tempo",
               "minuto_base", "acrescimo", "ordem"]
    g = gols.assign(tipo="gol", posicao=pd.NA, vermelho_tipo=pd.NA)
    g["tipo_de_gol"] = g["tipo_de_gol"].fillna("Normal")
    c = cartoes.assign(tipo=cartoes["cartao"].str.lower(), tipo_de_gol=pd.NA)
    c["vermelho_tipo"] = pd.Series(pd.NA, index=c.index, dtype=object)
    c.loc[c["tipo"] == "vermelho", "vermelho_tipo"] = classificar_vermelhos(cartoes)
    extras = ["tipo", "tipo_de_gol", "vermelho_tipo"]
    ev = pd.concat([g[colunas + extras], c[colunas + extras]], ignore_index=True)
    ev = ev[ev["partida_id"].isin(lados.index)]

    m = lados.reindex(ev["partida_id"])
    ev["lado"] = np.where(ev["clube"].to_numpy() == m["mandante"].to_numpy(), "mandante",
                          np.where(ev["clube"].to_numpy() == m["visitante"].to_numpy(), "visitante", None))
    if ev["lado"].isna().any():
        raise ValueError("evento com clube que não é mandante nem visitante")

    ev["prioridade"] = ev["tipo"].map(PRIORIDADE)
    ev = ev.sort_values(["partida_id", "ordem", "prioridade"], kind="stable").reset_index(drop=True)
    ev["seq"] = ev.groupby("partida_id").cumcount()

    # Linha do tempo contínua: o 1º tempo dura 45 + acréscimo estimado do 1º tempo.
    acr = estimar_acrescimos(alvo, ev).reindex(ev["partida_id"])
    dur1 = (45 + acr["acr1"]).to_numpy()
    ev["t"] = np.where(ev["tempo"] == 1, ev["minuto_base"] + ev["acrescimo"],
                       dur1 + (ev["minuto_base"] - 45) + ev["acrescimo"])
    ev["t_restante"] = (90 + acr["acr1"] + acr["acr2"]).to_numpy() - ev["t"]
    cortes = limites_faixas(acr)[:, 1:-1]
    ev["faixa_fina"] = (ev["t"].to_numpy()[:, None] > cortes).sum(axis=1)
    ev["faixa"] = np.take(FINA_PARA_FAIXA, ev["faixa_fina"])

    for lado in ("mandante", "visitante"):
        gol = ((ev["tipo"] == "gol") & (ev["lado"] == lado)).astype(int)
        verm = ((ev["tipo"] == "vermelho") & (ev["lado"] == lado)).astype(int)
        ev[f"gols_{lado}_depois"] = gol.groupby(ev["partida_id"]).cumsum()
        ev[f"gols_{lado}_antes"] = ev[f"gols_{lado}_depois"] - gol
        ev[f"jogadores_{lado}_depois"] = 11 - verm.groupby(ev["partida_id"]).cumsum()
        ev[f"jogadores_{lado}_antes"] = ev[f"jogadores_{lado}_depois"] + verm

    # Saldo e jogadores do ponto de vista do time do evento, antes dele.
    mand = ev["lado"] == "mandante"
    ev["saldo_lado_antes"] = np.where(mand, 1, -1) * (ev["gols_mandante_antes"] - ev["gols_visitante_antes"])
    ev["vantagem_numerica_lado_antes"] = np.where(mand, 1, -1) * (
        ev["jogadores_mandante_antes"] - ev["jogadores_visitante_antes"]
    )
    return ev.drop(columns="prioridade")


def estimar_acrescimos(partidas: pd.DataFrame, eventos: pd.DataFrame) -> pd.DataFrame:
    """Acréscimo estimado de cada tempo, por partida (colunas acr1 e acr2).

    A base não registra o acréscimo dado pelo árbitro. A estimativa é o maior entre:
    - o maior acréscimo observado nos eventos daquele tempo, na partida; e
    - a mediana, na temporada, desse acréscimo observado entre as partidas que
      tiveram algum evento nos acréscimos daquele tempo.
    Sem o piso da mediana, um vermelho no último evento registrado ficaria sempre com
    tempo restante 0. As duas medidas ainda tendem a subestimar o acréscimo real.
    """
    ids = pd.Index(partidas["partida_id"])
    temporada = partidas.set_index("partida_id")["temporada"].reindex(ids)
    saida = {}
    for tempo in (1, 2):
        observado = (eventos[eventos["tempo"] == tempo].groupby("partida_id")["acrescimo"].max()
                     .reindex(ids).fillna(0))
        mediana = observado[observado > 0].groupby(temporada[observado > 0]).median()
        piso = temporada.map(mediana).fillna(0)
        saida[f"acr{tempo}"] = np.maximum(observado, piso)
    return pd.DataFrame(saida, index=ids)


def limites_faixas(acr: pd.DataFrame) -> np.ndarray:
    """Limites das faixas finas na linha do tempo contínua (9 colunas, de 0 ao fim)."""
    d1 = 45 + acr["acr1"].to_numpy()
    fim = d1 + 45 + acr["acr2"].to_numpy()
    zeros = np.zeros_like(d1)
    return np.column_stack([zeros, zeros + 15, zeros + 30, zeros + 45,
                            d1, d1 + 15, d1 + 30, d1 + 45, fim])


def duracao_partidas(partidas: pd.DataFrame, eventos: pd.DataFrame) -> pd.Series:
    """Duração estimada de cada partida: 90 + acréscimos estimados dos dois tempos."""
    acr = estimar_acrescimos(partidas, eventos)
    return 90 + acr["acr1"] + acr["acr2"]


# ---------------------------------------------------------------------------
# Estados de jogo
# ---------------------------------------------------------------------------

def montar_estados(partidas: pd.DataFrame, eventos: pd.DataFrame) -> pd.DataFrame:
    """Trechos com placar e número de jogadores constantes.

    Cada gol ou vermelho encerra exatamente um trecho; o último trecho termina no
    fim estimado da partida. Eventos simultâneos geram trechos de duração 0, que
    devem ser filtrados (duracao > 0) quando a duração entra como offset.
    A duração da partida vem de `estimar_acrescimos`.
    """
    alvo = partidas[partidas["temporada"] >= PRIMEIRA_TEMPORADA_COM_EVENTOS]
    duracao = duracao_partidas(alvo, eventos)

    muda = eventos[eventos["tipo"].isin(["gol", "vermelho"])]
    estado_cols = ["gols_mandante", "gols_visitante", "jogadores_mandante", "jogadores_visitante"]

    # Trechos encerrados por evento: estado "antes" do evento, de t anterior até t.
    fechados = muda[["partida_id", "t", "tipo", "lado"]].rename(
        columns={"t": "fim", "tipo": "evento_fim", "lado": "lado_evento_fim"})
    for col in estado_cols:
        fechados[col] = muda[f"{col}_antes"].to_numpy()

    # Trecho final: estado depois do último evento (ou 0×0, 11×11 se não houve evento).
    ultimo = muda.groupby("partida_id").tail(1).set_index("partida_id")
    final = pd.DataFrame({"partida_id": alvo["partida_id"].to_numpy()})
    final["fim"] = duracao.reindex(final["partida_id"]).to_numpy()
    final["evento_fim"] = "fim"
    final["lado_evento_fim"] = None
    for col in estado_cols:
        padrao = 11 if col.startswith("jogadores") else 0
        final[col] = ultimo[f"{col}_depois"].reindex(final["partida_id"]).fillna(padrao).astype(int).to_numpy()

    est = pd.concat([fechados, final], ignore_index=True)
    est["_ord"] = (est["evento_fim"] == "fim").astype(int)
    est = est.sort_values(["partida_id", "fim", "_ord"], kind="stable").drop(columns="_ord")
    est["inicio"] = est.groupby("partida_id")["fim"].shift(1).fillna(0)
    est["duracao"] = est["fim"] - est["inicio"]
    est["restante_no_inicio"] = duracao.reindex(est["partida_id"]).to_numpy() - est["inicio"]
    est["trecho"] = est.groupby("partida_id").cumcount()
    est["temporada"] = alvo.set_index("partida_id")["temporada"].reindex(est["partida_id"]).to_numpy()
    ordem = ["partida_id", "temporada", "trecho", "inicio", "fim", "duracao", "restante_no_inicio",
             *estado_cols, "evento_fim", "lado_evento_fim"]
    return est[ordem].reset_index(drop=True)


def montar_exposicao(partidas: pd.DataFrame, eventos: pd.DataFrame, estados: pd.DataFrame) -> pd.DataFrame:
    """Exposição e contagens por partida × lado × faixa fina × estado do lado.

    O estado é visto do lado: `saldo` (gols próprios − adversário) e
    `vantagem_numerica` (jogadores próprios − adversário). Cada gol ou vermelho é
    contado no estado imediatamente anterior a ele e na faixa do seu minuto.
    """
    alvo = partidas[partidas["temporada"] >= PRIMEIRA_TEMPORADA_COM_EVENTOS]
    limites = pd.DataFrame(limites_faixas(estimar_acrescimos(alvo, eventos)),
                           index=pd.Index(alvo["partida_id"]))
    chave = ["partida_id", "lado", "faixa_fina", "saldo", "vantagem_numerica"]

    # Minutos em cada faixa: sobreposição de cada trecho com cada faixa.
    b = limites.reindex(estados["partida_id"]).to_numpy()
    partes = []
    for lado, sinal in (("mandante", 1), ("visitante", -1)):
        saldo = sinal * (estados["gols_mandante"] - estados["gols_visitante"]).to_numpy()
        vant = sinal * (estados["jogadores_mandante"] - estados["jogadores_visitante"]).to_numpy()
        for j in range(len(FAIXAS_FINAS)):
            sobre = (np.minimum(estados["fim"].to_numpy(), b[:, j + 1])
                     - np.maximum(estados["inicio"].to_numpy(), b[:, j])).clip(min=0)
            partes.append(pd.DataFrame({
                "partida_id": estados["partida_id"].to_numpy(), "lado": lado, "faixa_fina": j,
                "saldo": saldo, "vantagem_numerica": vant, "exposicao": sobre,
            })[sobre > 0])
    exposicao = pd.concat(partes).groupby(chave, as_index=False)["exposicao"].sum()

    # Contagens: cada evento gera uma linha para o próprio lado e outra para o adversário.
    muda = eventos[eventos["tipo"].isin(["gol", "vermelho"])]
    gol = (muda["tipo"] == "gol").astype(int).to_numpy()
    verm = (muda["tipo"] == "vermelho").astype(int).to_numpy()
    proprio = pd.DataFrame({
        "partida_id": muda["partida_id"].to_numpy(), "lado": muda["lado"].to_numpy(),
        "faixa_fina": muda["faixa_fina"].to_numpy(),
        "saldo": muda["saldo_lado_antes"].to_numpy(),
        "vantagem_numerica": muda["vantagem_numerica_lado_antes"].to_numpy(),
        "vermelhos": verm,
        "vermelhos_direto": verm * (muda["vermelho_tipo"] == "direto").to_numpy(),
        "vermelhos_2o_amarelo": verm * (muda["vermelho_tipo"] == "2o_amarelo").to_numpy(),
        "vermelhos_adversario": 0, "gols_pro": gol, "gols_contra": 0,
    })
    adversario = proprio.assign(
        lado=proprio["lado"].map(OUTRO_LADO), saldo=-proprio["saldo"],
        vantagem_numerica=-proprio["vantagem_numerica"],
        vermelhos=0, vermelhos_direto=0, vermelhos_2o_amarelo=0,
        vermelhos_adversario=verm, gols_pro=0, gols_contra=gol,
    )
    contagens = pd.concat([proprio, adversario]).groupby(chave, as_index=False).sum()

    exp = exposicao.merge(contagens, on=chave, how="outer")
    exp["exposicao"] = exp["exposicao"].fillna(0)
    contagem_cols = [c for c in contagens.columns if c not in chave]
    exp[contagem_cols] = exp[contagem_cols].fillna(0).astype(int)
    exp["faixa"] = np.take(FINA_PARA_FAIXA, exp["faixa_fina"])
    exp["temporada"] = alvo.set_index("partida_id")["temporada"].reindex(exp["partida_id"]).to_numpy()
    return exp.sort_values(chave).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Elo
# ---------------------------------------------------------------------------

def preparar_jogos(partidas: pd.DataFrame) -> dict:
    p = partidas.sort_values(["data", "hora", "partida_id"], kind="stable").reset_index(drop=True)
    times = pd.Index(sorted(set(p["mandante"]) | set(p["visitante"])))
    temporadas = p["temporada"].to_numpy()
    times_por_temporada = {
        t: set(times.get_indexer(pd.concat([g["mandante"], g["visitante"]]).unique()))
        for t, g in p.groupby("temporada")
    }
    return {
        "partida_id": p["partida_id"].to_numpy(),
        "temporada": temporadas,
        "m": times.get_indexer(p["mandante"]),
        "v": times.get_indexer(p["visitante"]),
        "gm": p["mandante_Placar"].to_numpy(),
        "gv": p["visitante_Placar"].to_numpy(),
        "n_times": len(times),
        "times_por_temporada": times_por_temporada,
    }


def multiplicador_margem(saldo_abs: int) -> float:
    # Multiplicador do World Football Elo Ratings.
    if saldo_abs <= 1:
        return 1.0
    if saldo_abs == 2:
        return 1.5
    return (11 + saldo_abs) / 8


def rodar_elo(jogos: dict, k: float, mando: float, regressao: float, empate: float,
              margem: bool, ate_temporada: int | None = None):
    """Elo pré-jogo de cada partida e probabilidades V/E/D do mandante.

    P(V) = σ(x − c), P(D) = σ(−x − c), P(E) = 1 − P(V) − P(D),
    com x = (Elo_m + mando − Elo_v)·ln(10)/400 e c = `empate`.
    """
    n = len(jogos["m"]) if ate_temporada is None else int((jogos["temporada"] <= ate_temporada).sum())
    rating = np.full(jogos["n_times"], ELO_INICIAL)
    visto = np.zeros(jogos["n_times"], dtype=bool)
    pre_m, pre_v = np.empty(n), np.empty(n)
    escala = np.log(10) / 400
    temporada_atual, times_anteriores = None, set()

    for i in range(n):
        temp = jogos["temporada"][i]
        if temp != temporada_atual:
            atuais = jogos["times_por_temporada"][temp]
            sairam = list(times_anteriores - atuais)
            novos = [t for t in atuais if not visto[t]]
            if novos:
                rating[novos] = rating[sairam].mean() if sairam else ELO_INICIAL
                visto[novos] = True
            idx = list(atuais)
            media = rating[idx].mean()
            rating[idx] += regressao * (media - rating[idx])
            temporada_atual, times_anteriores = temp, atuais

        m, v = jogos["m"][i], jogos["v"][i]
        pre_m[i], pre_v[i] = rating[m], rating[v]
        esperado = 1 / (1 + np.exp(-(rating[m] + mando - rating[v]) * escala))
        gm, gv = jogos["gm"][i], jogos["gv"][i]
        real = 1.0 if gm > gv else 0.5 if gm == gv else 0.0
        fator = multiplicador_margem(abs(gm - gv)) if margem else 1.0
        delta = k * fator * (real - esperado)
        rating[m] += delta
        rating[v] -= delta

    x = (pre_m + mando - pre_v) * escala
    p_v = 1 / (1 + np.exp(-(x - empate)))
    p_d = 1 / (1 + np.exp(-(-x - empate)))
    probs = np.column_stack([p_v, 1 - p_v - p_d, p_d])
    return pre_m, pre_v, probs


def log_loss_resultado(probs: np.ndarray, gm: np.ndarray, gv: np.ndarray) -> float:
    coluna = np.where(gm > gv, 0, np.where(gm == gv, 1, 2))
    p = np.clip(probs[np.arange(len(coluna)), coluna], 1e-12, 1)
    return float(-np.log(p).mean())


def calibrar_elo(jogos: dict) -> tuple[dict, pd.DataFrame]:
    """Escolhe K, mando, regressão e c por log-loss em 2004–2013 (2003 é aquecimento)."""
    ate = ULTIMA_TEMPORADA_CALIBRACAO_ELO
    n = int((jogos["temporada"] <= ate).sum())
    avaliar = jogos["temporada"][:n] > jogos["temporada"].min()
    gm, gv = jogos["gm"][:n][avaliar], jogos["gv"][:n][avaliar]
    limites = [(5, 80), (0, 200), (0, 1), (0.01, 2)]

    linhas, melhores = [], None
    for margem in (False, True):
        def objetivo(theta):
            _, _, probs = rodar_elo(jogos, *theta, margem=margem, ate_temporada=ate)
            return log_loss_resultado(probs[avaliar], gm, gv)

        res = minimize(objetivo, x0=[20, 60, 0.2, 0.5], method="Powell", bounds=limites)
        params = dict(zip(["k", "mando", "regressao", "empate"], res.x), margem=margem)
        linhas.append({**params, "log_loss_2004_2013": res.fun})
        if melhores is None or res.fun < melhores[1]:
            melhores = (params, res.fun)

    # Baseline: frequências históricas de V/E/D no próprio período de calibração.
    freq = np.array([(gm > gv).mean(), (gm == gv).mean(), (gm < gv).mean()])
    linhas.append({"margem": "baseline_frequencias",
                   "log_loss_2004_2013": log_loss_resultado(np.tile(freq, (len(gm), 1)), gm, gv)})
    return melhores[0], pd.DataFrame(linhas)


def montar_elo(partidas: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    jogos = preparar_jogos(partidas)
    params, tabela = calibrar_elo(jogos)
    pre_m, pre_v, probs = rodar_elo(jogos, **params)
    elo = pd.DataFrame({
        "partida_id": jogos["partida_id"],
        "elo_mandante": pre_m,
        "elo_visitante": pre_v,
        "p_elo_V": probs[:, 0], "p_elo_E": probs[:, 1], "p_elo_D": probs[:, 2],
    })
    fora = jogos["temporada"] >= PRIMEIRA_TEMPORADA_COM_EVENTOS
    tabela["escolhido"] = [r.get("margem") == params["margem"] for r in tabela.to_dict("records")]
    tabela["log_loss_2014_2024"] = np.where(
        tabela["escolhido"], log_loss_resultado(probs[fora], jogos["gm"][fora], jogos["gv"][fora]), np.nan)
    return elo, tabela, params, jogos


def checar_vazamento_elo(jogos: dict, params: dict, elo: pd.DataFrame, n_testes: int = 5) -> None:
    """Alterar o resultado de um jogo não pode mudar o Elo pré-jogo dele nem dos anteriores."""
    rng = np.random.default_rng(42)
    for i in rng.choice(len(jogos["m"]), size=n_testes, replace=False):
        alterado = {**jogos, "gm": jogos["gm"].copy(), "gv": jogos["gv"].copy()}
        alterado["gm"][i], alterado["gv"][i] = jogos["gv"][i] + 3, jogos["gm"][i]
        pre_m, pre_v, _ = rodar_elo(alterado, **params)
        if not (np.allclose(pre_m[: i + 1], elo["elo_mandante"].to_numpy()[: i + 1])
                and np.allclose(pre_v[: i + 1], elo["elo_visitante"].to_numpy()[: i + 1])):
            raise AssertionError(f"vazamento no Elo: jogo {jogos['partida_id'][i]}")
        if np.allclose(pre_m[i + 1:], elo["elo_mandante"].to_numpy()[i + 1:]) and i + 1 < len(pre_m):
            raise AssertionError("alterar um resultado não mudou nenhum Elo posterior")


# ---------------------------------------------------------------------------
# Pontos por jogo na temporada (complemento ao Elo)
# ---------------------------------------------------------------------------

def pontos_por_jogo_previos(partidas: pd.DataFrame) -> pd.DataFrame:
    """PPG de cada time na temporada, considerando só jogos anteriores (por data)."""
    p = partidas.sort_values(["data", "hora", "partida_id"], kind="stable")
    pts_m = p["resultado_mandante"].map(PONTOS)
    pts_v = p["resultado_mandante"].map({"V": 0, "E": 1, "D": 3})
    longo = pd.concat([
        pd.DataFrame({"partida_id": p["partida_id"], "temporada": p["temporada"], "clube": p["mandante"],
                      "lado": "mandante", "pontos": pts_m, "_o": np.arange(len(p))}),
        pd.DataFrame({"partida_id": p["partida_id"], "temporada": p["temporada"], "clube": p["visitante"],
                      "lado": "visitante", "pontos": pts_v, "_o": np.arange(len(p))}),
    ]).sort_values("_o", kind="stable")
    grupo = longo.groupby(["temporada", "clube"])["pontos"]
    longo["ppg_previo"] = (grupo.cumsum() - longo["pontos"]) / grupo.cumcount().replace(0, np.nan)
    longo["jogos_previos"] = grupo.cumcount()
    return longo.pivot(index="partida_id", columns="lado", values=["ppg_previo", "jogos_previos"])


# ---------------------------------------------------------------------------
# Partidas e time × partida
# ---------------------------------------------------------------------------

def montar_partidas(partidas: pd.DataFrame, eventos: pd.DataFrame, estados: pd.DataFrame,
                    elo: pd.DataFrame) -> pd.DataFrame:
    p = partidas[partidas["temporada"] >= PRIMEIRA_TEMPORADA_COM_EVENTOS].copy()
    p = p[["partida_id", "temporada", "rodada", "data", "hora", "mandante", "visitante", "arena",
           "mandante_Placar", "visitante_Placar", "resultado_mandante"]]
    p["pontos_mandante"] = p["resultado_mandante"].map(PONTOS)
    p["pontos_visitante"] = p["resultado_mandante"].map({"V": 0, "E": 1, "D": 3})
    p = p.merge(elo, on="partida_id", how="left")
    p["elo_diff"] = p["elo_mandante"] - p["elo_visitante"]

    ppg = pontos_por_jogo_previos(partidas)
    for lado in ("mandante", "visitante"):
        p[f"ppg_previo_{lado}"] = ppg[("ppg_previo", lado)].reindex(p["partida_id"]).to_numpy()
        p[f"jogos_previos_{lado}"] = ppg[("jogos_previos", lado)].reindex(p["partida_id"]).to_numpy()

    p["duracao_estimada"] = estados.groupby("partida_id")["fim"].max().reindex(p["partida_id"]).to_numpy()

    verm = eventos[eventos["tipo"] == "vermelho"]
    for lado in ("mandante", "visitante"):
        v = verm[verm["lado"] == lado]
        p[f"vermelhos_{lado}"] = v.groupby("partida_id").size().reindex(p["partida_id"]).fillna(0).astype(int).to_numpy()
        for tipo in ("direto", "2o_amarelo"):
            cont = v[v["vermelho_tipo"] == tipo].groupby("partida_id").size()
            p[f"vermelhos_{tipo}_{lado}"] = cont.reindex(p["partida_id"]).fillna(0).astype(int).to_numpy()

    # Primeiro vermelho da partida.
    pv = verm.groupby("partida_id").head(1).set_index("partida_id")
    campos = {
        "pv_lado": "lado", "pv_minuto": "minuto", "pv_tempo": "tempo", "pv_t": "t",
        "pv_t_restante": "t_restante", "pv_tipo": "vermelho_tipo", "pv_posicao": "posicao",
        "pv_saldo_punido": "saldo_lado_antes",
    }
    for destino, origem in campos.items():
        p[destino] = pv[origem].reindex(p["partida_id"]).to_numpy()
    p["pv_estado_punido"] = pd.cut(p["pv_saldo_punido"], [-np.inf, -0.5, 0.5, np.inf],
                                   labels=["perdendo", "empatando", "vencendo"]).astype(object)

    # Houve vermelho do outro lado depois do primeiro?
    seq_pv = pv["seq"]
    depois = verm.join(seq_pv.rename("seq_pv"), on="partida_id")
    depois = depois[(depois["seq"] > depois["seq_pv"])]
    depois = depois.join(pv["lado"].rename("lado_pv"), on="partida_id")
    outro = depois[depois["lado"] != depois["lado_pv"]].groupby("partida_id").size()
    mesmo = depois[depois["lado"] == depois["lado_pv"]].groupby("partida_id").size()
    tem_pv = p["pv_lado"].notna()
    p["pv_outro_lado_depois"] = np.where(tem_pv, outro.reindex(p["partida_id"]).fillna(0).to_numpy() > 0, pd.NA)
    p["pv_mesmo_lado_depois"] = np.where(tem_pv, mesmo.reindex(p["partida_id"]).fillna(0).to_numpy() > 0, pd.NA)
    return p.reset_index(drop=True)


def montar_time_partida(partidas_proc: pd.DataFrame, estatisticas: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for lado, adv in (("mandante", "visitante"), ("visitante", "mandante")):
        t = pd.DataFrame({
            "partida_id": partidas_proc["partida_id"],
            "temporada": partidas_proc["temporada"],
            "data": partidas_proc["data"],
            "clube": partidas_proc[lado],
            "adversario": partidas_proc[adv],
            "mando": lado,
            "gols_pro": partidas_proc[f"{lado}_Placar"],
            "gols_contra": partidas_proc[f"{adv}_Placar"],
            "pontos": partidas_proc[f"pontos_{lado}"],
            "elo_proprio": partidas_proc[f"elo_{lado}"],
            "elo_adversario": partidas_proc[f"elo_{adv}"],
            "ppg_previo_proprio": partidas_proc[f"ppg_previo_{lado}"],
            "ppg_previo_adversario": partidas_proc[f"ppg_previo_{adv}"],
            "vermelhos_proprios": partidas_proc[f"vermelhos_{lado}"],
            "vermelhos_adversario": partidas_proc[f"vermelhos_{adv}"],
            "vermelhos_diretos_proprios": partidas_proc[f"vermelhos_direto_{lado}"],
            "vermelhos_2o_amarelo_proprios": partidas_proc[f"vermelhos_2o_amarelo_{lado}"],
            "primeiro_vermelho_e_proprio": np.where(
                partidas_proc["pv_lado"].isna(), pd.NA, partidas_proc["pv_lado"] == lado),
        })
        t["elo_diff"] = t["elo_proprio"] - t["elo_adversario"]
        t["resultado"] = np.select([t["gols_pro"] > t["gols_contra"], t["gols_pro"] == t["gols_contra"]],
                                   ["V", "E"], default="D")
        linhas.append(t)
    tp = pd.concat(linhas, ignore_index=True)
    stats = estatisticas.drop(columns=["rodata", "cartao_amarelo", "cartao_vermelho"], errors="ignore")
    tp = tp.merge(stats, on=["partida_id", "clube"], how="left")
    return tp.sort_values(["data", "partida_id", "mando"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Sanidade
# ---------------------------------------------------------------------------

def checar_sanidade(partidas_proc: pd.DataFrame, eventos: pd.DataFrame, estados: pd.DataFrame,
                    exposicao: pd.DataFrame, cartoes: pd.DataFrame) -> None:
    p = partidas_proc.set_index("partida_id")
    final = estados[estados["evento_fim"] == "fim"].set_index("partida_id").reindex(p.index)
    if not ((final["gols_mandante"] == p["mandante_Placar"]).all()
            and (final["gols_visitante"] == p["visitante_Placar"]).all()):
        raise AssertionError("placar reconstruído não bate com o placar final")

    jog = eventos[["jogadores_mandante_depois", "jogadores_visitante_depois"]]
    if not jog.isin(range(7, 12)).all().all():
        raise AssertionError("número de jogadores fora de 7–11")

    verm = eventos[(eventos["tipo"] == "vermelho") & eventos["atleta"].notna()]
    if verm.duplicated(["partida_id", "clube", "atleta"]).any():
        raise AssertionError("atleta com dois vermelhos na mesma partida")

    soma = estados.groupby("partida_id")["duracao"].sum()
    if not np.allclose(soma.reindex(p.index), p["duracao_estimada"]) or (estados["duracao"] < 0).any():
        raise AssertionError("durações dos trechos inconsistentes")

    n_gols = int(p["mandante_Placar"].sum() + p["visitante_Placar"].sum())
    if (exposicao["vermelhos"].sum() != (cartoes["cartao"] == "Vermelho").sum()
            or exposicao["gols_pro"].sum() != n_gols or exposicao["gols_contra"].sum() != n_gols):
        raise AssertionError("contagens da tabela de exposição não batem com os eventos")
    por_lado = exposicao.groupby(["partida_id", "lado"])["exposicao"].sum().unstack()
    if not (np.allclose(por_lado["mandante"].reindex(p.index), p["duracao_estimada"])
            and np.allclose(por_lado["visitante"].reindex(p.index), p["duracao_estimada"])):
        raise AssertionError("exposição por lado não soma a duração da partida")

    n_verm = (cartoes["cartao"] == "Vermelho").sum()
    if eventos["vermelho_tipo"].notna().sum() != n_verm or len(verm) + eventos["vermelho_tipo"].eq("indeterminado").sum() != n_verm:
        raise AssertionError("classificação de vermelhos não cobre todos os vermelhos")


LANDMARKS = list(range(0, 90, 5))  # minutos de relógio: 0, 5, ..., 85


def montar_landmarks(partidas_proc: pd.DataFrame, eventos: pd.DataFrame) -> pd.DataFrame:
    """Estado de cada partida em minutos fixos de relógio (landmarks), visto pelo mandante.

    O minuto 45 corresponde ao intervalo (fim do 1º tempo com acréscimo). O estado
    inclui todos os gols e vermelhos com t <= landmark. A saída inclui o resultado
    final, usado como alvo dos modelos de efeito e de previsão.
    """
    p = partidas_proc
    acr = estimar_acrescimos(p, eventos)
    d1 = (45 + acr["acr1"]).reindex(p["partida_id"]).to_numpy()
    duracao = p["duracao_estimada"].to_numpy()

    lm = pd.DataFrame({
        "partida_id": np.repeat(p["partida_id"].to_numpy(), len(LANDMARKS)),
        "landmark": np.tile(LANDMARKS, len(p)),
    })
    d1_l = np.repeat(d1, len(LANDMARKS))
    lm["t"] = np.where(lm["landmark"] < 45, lm["landmark"], d1_l + (lm["landmark"] - 45)).astype(float)
    lm["t_restante"] = np.repeat(duracao, len(LANDMARKS)) - lm["t"]

    muda = eventos[eventos["tipo"].isin(["gol", "vermelho"])][
        ["partida_id", "t", "seq", "gols_mandante_depois", "gols_visitante_depois",
         "jogadores_mandante_depois", "jogadores_visitante_depois"]
    ].sort_values(["t", "seq"])
    lm = pd.merge_asof(lm.sort_values("t"), muda.drop(columns="seq"), on="t", by="partida_id",
                       direction="backward", allow_exact_matches=True)
    lm = lm.sort_values(["partida_id", "landmark"]).reset_index(drop=True)
    gols_m = lm["gols_mandante_depois"].fillna(0).astype(int)
    gols_v = lm["gols_visitante_depois"].fillna(0).astype(int)
    lm["saldo"] = gols_m - gols_v
    lm["vermelhos_mandante"] = 11 - lm["jogadores_mandante_depois"].fillna(11).astype(int)
    lm["vermelhos_visitante"] = 11 - lm["jogadores_visitante_depois"].fillna(11).astype(int)
    lm = lm.drop(columns=[c for c in lm.columns if c.endswith("_depois")])

    info = p.set_index("partida_id")
    lm["temporada"] = info["temporada"].reindex(lm["partida_id"]).to_numpy()
    lm["elo_diff"] = info["elo_diff"].reindex(lm["partida_id"]).to_numpy()
    res = info["resultado_mandante"].reindex(lm["partida_id"])
    lm["resultado"] = res.map({"D": 0, "E": 1, "V": 2}).to_numpy()
    lm["pontos_mandante"] = res.map(PONTOS).to_numpy()
    return lm


def exportar_exemplo(partidas_proc: pd.DataFrame, eventos: pd.DataFrame, estados: pd.DataFrame) -> None:
    """Eventos e trechos da partida de exemplo, para a linha do tempo dos slides."""
    info = partidas_proc[partidas_proc["partida_id"] == EXEMPLO_PARTIDA_ID]
    if len(info) != 1:
        raise ValueError(f"partida de exemplo {EXEMPLO_PARTIDA_ID} não encontrada")
    info = info.iloc[0]
    ev = eventos[eventos["partida_id"] == EXEMPLO_PARTIDA_ID]
    ev = ev[["minuto", "t", "tipo", "lado", "clube", "posicao", "vermelho_tipo"]].assign(
        data=info["data"].strftime("%d/%m/%Y"), mandante=info["mandante"], visitante=info["visitante"],
        placar_mandante=info["mandante_Placar"], placar_visitante=info["visitante_Placar"], arena=info["arena"],
        duracao=info["duracao_estimada"])
    ev.to_csv(TABELAS_DIR / "exemplo_partida_eventos.csv", index=False)
    tr = estados[estados["partida_id"] == EXEMPLO_PARTIDA_ID]
    tr[["trecho", "inicio", "fim", "duracao", "gols_mandante", "gols_visitante", "jogadores_mandante",
        "jogadores_visitante"]].to_csv(TABELAS_DIR / "exemplo_partida_trechos.csv", index=False)


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    TABELAS_DIR.mkdir(parents=True, exist_ok=True)
    partidas = pd.read_parquet(INTERIM_DIR / "partidas.parquet")
    gols = pd.read_parquet(INTERIM_DIR / "gols.parquet")
    cartoes = pd.read_parquet(INTERIM_DIR / "cartoes.parquet")
    estatisticas = pd.read_parquet(INTERIM_DIR / "estatisticas.parquet")

    eventos = montar_eventos(partidas, gols, cartoes)
    estados = montar_estados(partidas, eventos)
    elo, tabela_elo, params, jogos = montar_elo(partidas)
    checar_vazamento_elo(jogos, params, elo)
    partidas_proc = montar_partidas(partidas, eventos, estados, elo)
    time_partida = montar_time_partida(partidas_proc, estatisticas)
    exposicao = montar_exposicao(partidas, eventos, estados)
    checar_sanidade(partidas_proc, eventos, estados, exposicao, cartoes)
    landmarks = montar_landmarks(partidas_proc, eventos)
    if landmarks[["saldo", "vermelhos_mandante", "elo_diff", "resultado"]].isna().any().any():
        raise AssertionError("landmarks com valores ausentes")

    tabela_elo.to_csv(TABELAS_DIR / "elo_parametros.csv", index=False)
    exportar_exemplo(partidas_proc, eventos, estados)
    verm = eventos[eventos["tipo"] == "vermelho"]
    tipos = verm["vermelho_tipo"].value_counts()
    resumo = {
        "eventos_linhas": len(eventos),
        "trechos": len(estados),
        "trechos_duracao_zero": int((estados["duracao"] == 0).sum()),
        "vermelhos_direto": int(tipos.get("direto", 0)),
        "vermelhos_2o_amarelo": int(tipos.get("2o_amarelo", 0)),
        "vermelhos_indeterminado": int(tipos.get("indeterminado", 0)),
        "vermelhos_90_mais": int(((verm["tempo"] == 2) & (verm["acrescimo"] > 0)).sum()),
        "vermelhos_t_restante_zero": int((verm["t_restante"] == 0).sum()),
        "partidas_2_mais_vermelhos": int((verm.groupby("partida_id").size() >= 2).sum()),
        "landmarks_linhas": len(landmarks),
        "duracao_mediana_2014": float(partidas_proc.loc[partidas_proc["temporada"] == 2014, "duracao_estimada"].median()),
        "duracao_mediana_2024": float(partidas_proc.loc[partidas_proc["temporada"] == 2024, "duracao_estimada"].median()),
    }
    pd.Series(resumo, name="valor", dtype=object).rename_axis("chave").to_csv(TABELAS_DIR / "features_resumo.csv")
    print(tabela_elo.to_string(index=False))
    print(eventos["vermelho_tipo"].value_counts().to_string())
    for nome, tabela in {"eventos": eventos, "estados": estados, "elo": elo,
                         "partidas": partidas_proc, "time_partida": time_partida,
                         "exposicao": exposicao, "landmarks": landmarks}.items():
        tabela.to_parquet(PROCESSED_DIR / f"{nome}.parquet", index=False)
        print(f"ok  {nome}.parquet  ({len(tabela)} linhas)")


if __name__ == "__main__":
    main()
