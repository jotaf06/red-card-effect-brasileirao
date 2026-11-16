"""Carregador de dados e funções matemáticas de apoio para o Dashboard."""
import numpy as np
import pandas as pd
import streamlit as st

from src.dashboard.config import TABELAS_DIR


@st.cache_data
def carregar_tabela(nome: str) -> pd.DataFrame:
    """Carrega um arquivo CSV da pasta reports/tabelas em cache de memória."""
    caminho = TABELAS_DIR / f"{nome}.csv"
    if not caminho.exists():
        raise FileNotFoundError(f"Tabela não encontrada: {caminho}")
    return pd.read_csv(caminho)


@st.cache_data
def carregar_todas_tabelas() -> dict[str, pd.DataFrame]:
    """Carrega o dicionário contendo as principais tabelas analíticas pré-calculadas."""
    nomes = [
        "resumo_base",
        "h1_custo_minuto",
        "h1_pareamento_att",
        "h1_gols_irr",
        "h3_irr",
        "h5_taxas_faixa",
        "h5_posicao_cartao",
        "h5_posicao_formacao",
        "insights_conversao_amarelo",
        "insights_testes",
        "insights_liga",
        "insights_metas",
        "modelos_metricas",
        "modelos_shap_importancia",
        "modelos_custo_curvas",
        "h1_modelo_estado_coeficientes",
    ]
    return {nome: carregar_tabela(nome) for nome in nomes}


def formatar_decimal(valor: float, casas: int = 2) -> str:
    """Formata um número decimal no padrão brasileiro com vírgula."""
    return f"{valor:.{casas}f}".replace(".", ",")


def formatar_p_valor(p_valor: float) -> str:
    """Formata um p-valor com comparador evitando arredondamentos para zero."""
    if pd.isna(p_valor):
        return "= —"
    if p_valor < 1e-4:
        return "< 0,0001"
    return f"= {formatar_decimal(p_valor, 4)}"


def obter_faixa_minuto(minuto: float, incluir_acrescimo_final: bool = False) -> str:
    """Mapeia o minuto de jogo para a faixa analítica padrão correspondente."""
    limites = [
        (15, "0–15"),
        (30, "16–30"),
        (45, "31–45+"),
        (60, "46–60"),
        (75, "61–75"),
    ]
    for limite, rotulo in limites:
        if minuto <= limite:
            return rotulo
    return "76–90+" if incluir_acrescimo_final else "76–90"


@st.cache_data
def obter_coeficientes_multinomial() -> dict[str, dict[str, float]]:
    """Carrega e organiza os coeficientes da regressão logística multinomial."""
    df = carregar_tabela("h1_modelo_estado_coeficientes")
    mult = df[df["modelo"] == "multinomial"]
    
    coefs = {"E_vs_D": {}, "V_vs_D": {}}
    for _, row in mult.iterrows():
        param = row["parametro"]
        if param.startswith("E vs D: "):
            chave = param.replace("E vs D: ", "")
            coefs["E_vs_D"][chave] = float(row["coef"])
        elif param.startswith("V vs D: "):
            chave = param.replace("V vs D: ", "")
            coefs["V_vs_D"][chave] = float(row["coef"])
    return coefs


def predizer_probabilidades_multinomial(
    minuto: float,
    saldo_mandante: float,
    elo_diff: float = 0.0,
    verm_mandante: int = 0,
    verm_visitante: int = 0,
    duracao_total: float = 97.0,
) -> dict[str, float]:
    """Calcula as probabilidades P(V), P(E) e P(D) do mandante a partir do modelo de estado."""
    coefs = obter_coeficientes_multinomial()
    
    t_restante = max(0.0, duracao_total - minuto)
    tr = t_restante / 90.0
    elo = elo_diff / 100.0
    saldo_escalado = saldo_mandante / np.sqrt(t_restante + 1.0)
    
    def logit_valor(grupo: str) -> float:
        """Calcula a combinação linear de logit para a classe informada."""
        c = coefs[grupo]
        val = c.get("const", 0.0)
        val += c.get("saldo", 0.0) * saldo_mandante
        val += c.get("saldo_escalado", 0.0) * saldo_escalado
        val += c.get("tr", 0.0) * tr
        val += c.get("elo", 0.0) * elo
        val += c.get("elo_x_tr", 0.0) * (elo * tr)
        val += c.get("verm_mandante", 0.0) * verm_mandante
        val += c.get("verm_mandante_x_tr", 0.0) * (verm_mandante * tr)
        val += c.get("verm_visitante", 0.0) * verm_visitante
        val += c.get("verm_visitante_x_tr", 0.0) * (verm_visitante * tr)
        return val

    logit_e = logit_valor("E_vs_D")
    logit_v = logit_valor("V_vs_D")
    
    max_l = max(0.0, logit_e, logit_v)
    exp_d = np.exp(0.0 - max_l)
    exp_e = np.exp(logit_e - max_l)
    exp_v = np.exp(logit_v - max_l)
    soma = exp_d + exp_e + exp_v
    
    return {
        "P(V)": float(exp_v / soma),
        "P(E)": float(exp_e / soma),
        "P(D)": float(exp_d / soma),
    }


def calcular_pontos_esperados(probabilidades: dict[str, float], lado: str) -> float:
    """Calcula os pontos esperados finais de acordo com a condição de mandante ou visitante."""
    pv = probabilidades["P(V)"]
    pe = probabilidades["P(E)"]
    pd_val = probabilidades["P(D)"]
    
    if lado == "mandante":
        return 3.0 * pv + 1.0 * pe
    else:
        return 3.0 * pd_val + 1.0 * pe


def obter_att_pareamento(minuto: float, lado: str = "todos", saldo: int = 0) -> dict[str, float]:
    """Retorna as estimativas de efeito causal ATT por pareamento para o contexto fornecido."""
    df = carregar_tabela("h1_pareamento_att")
    faixa = f"faixa {obter_faixa_minuto(minuto)}"

    linha_faixa = df[df["grupo"] == faixa]
    if linha_faixa.empty:
        linha_faixa = df[df["grupo"] == "todos"]
    r_faixa = linha_faixa.iloc[0]

    chave_lado = f"lado {lado}"
    linha_lado = df[df["grupo"] == chave_lado]
    att_lado = float(linha_lado.iloc[0]["att"]) if not linha_lado.empty else float(r_faixa["att"])

    if saldo < 0:
        chave_estado = "estado perdendo"
    elif saldo == 0:
        chave_estado = "estado empatando"
    else:
        chave_estado = "estado vencendo"
    linha_estado = df[df["grupo"] == chave_estado]
    att_estado = float(linha_estado.iloc[0]["att"]) if not linha_estado.empty else float(r_faixa["att"])

    def _att_grupo(nome_grupo: str) -> dict[str, float]:
        linha = df[df["grupo"] == nome_grupo].iloc[0]
        return {
            "att": float(linha["att"]),
            "ic95_inf": float(linha["ic95_inf"]),
            "ic95_sup": float(linha["ic95_sup"]),
            "p_valor": float(linha["p_valor"]),
            "n_tratados": int(linha["n_tratados"]),
        }

    return {
        "faixa": faixa,
        "att": float(r_faixa["att"]),
        "ic95_inf": float(r_faixa["ic95_inf"]),
        "ic95_sup": float(r_faixa["ic95_sup"]),
        "p_valor": float(r_faixa["p_valor"]),
        "n_tratados": int(r_faixa["n_tratados"]),
        "att_lado": att_lado,
        "att_estado": att_estado,
        "todos": _att_grupo("todos"),
        "ate_75": _att_grupo("até 75'"),
        "depois_75": _att_grupo("depois de 75'"),
    }


def obter_dinamica_gols(lado: str = "todos") -> dict[str, dict[str, float]]:
    """Retorna as razões de taxa de gols (IRR) sob desvantagem e vantagem numérica."""
    df = carregar_tabela("h1_gols_irr")
    
    modelo_filtro = f"lado {lado}" if lado in ["mandante", "visitante"] else "todos"
    subset = df[df["modelo"] == modelo_filtro]
    if subset.empty:
        subset = df[df["modelo"] == "todos"]
        
    efeito_fixo = df[df["modelo"].str.startswith("efeito fixo")]
    
    inf_row = subset[subset["termo"] == "vantagem[inferior]"].iloc[0]
    sup_row = subset[subset["termo"] == "vantagem[superior]"].iloc[0]
    
    inf_ef = efeito_fixo[efeito_fixo["termo"] == "vantagem[inferior]"].iloc[0]
    sup_ef = efeito_fixo[efeito_fixo["termo"] == "vantagem[superior]"].iloc[0]
    
    return {
        "especifico": {
            "gols_pro_irr": float(inf_row["irr"]),
            "gols_pro_inf": float(inf_row["ic95_inf"]),
            "gols_pro_sup": float(inf_row["ic95_sup"]),
            "gols_contra_irr": float(sup_row["irr"]),
            "gols_contra_inf": float(sup_row["ic95_inf"]),
            "gols_contra_sup": float(sup_row["ic95_sup"]),
        },
        "intra_partida": {
            "gols_pro_irr": float(inf_ef["irr"]),
            "gols_contra_irr": float(sup_ef["irr"]),
        }
    }


def obter_comparacao_modelos_cenario(minuto: float, saldo: int, lado: str) -> dict[str, float]:
    """Retorna a estimativa de Delta PE nos 4 modelos de aprendizado para o cenário atual."""
    df = carregar_tabela("modelos_custo_curvas")
    
    landmarks = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85]
    landmark_prox = min(landmarks, key=lambda x: abs(x - minuto))
    saldo_clip = max(-1, min(1, saldo))
    
    filtro = (
        (df["landmark"] == landmark_prox) &
        (df["saldo_punido"] == saldo_clip) &
        (df["lado_punido"] == lado)
    )
    linha = df[filtro]
    if linha.empty:
        linha = df[(df["landmark"] == landmark_prox) & (df["lado_punido"] == lado)]
    if linha.empty:
        return {}
        
    r = linha.iloc[0]
    return {
        "Logística Multinomial": float(r["logística multinomial"]),
        "Logística Ordinal": float(r["logística ordinal"]),
        "Random Forest": float(r["random forest"]),
        "LightGBM": float(r["LightGBM"]),
        "landmark_utilizado": landmark_prox,
        "saldo_utilizado": saldo_clip,
    }


def obter_dados_posicao(posicao: str) -> dict[str, float]:
    """Retorna taxas de conversão para expulsão e razão observado/esperado da posição."""
    df_pos = carregar_tabela("h5_posicao_cartao")
    df_form = carregar_tabela("h5_posicao_formacao")
    form_princ = df_form[df_form["variante"] == "principal"]

    row_pos = df_pos[df_pos["posicao"] == posicao]
    row_form = form_princ[form_princ["posicao"] == posicao]
    if row_pos.empty or row_form.empty:
        raise ValueError(f"Posição não encontrada nas tabelas analíticas: {posicao}")

    return {
        "posicao": posicao,
        "punidos": int(row_pos.iloc[0]["punidos"]),
        "expulsos": int(row_pos.iloc[0]["expulsos"]),
        "taxa_conversao": float(row_pos.iloc[0]["proporcao"]) * 100,
        "observados_formacao": int(row_form.iloc[0]["observados"]),
        "razao_obs_esp": float(row_form.iloc[0]["razao_obs_esp"]),
        "ic95_inf": float(row_form.iloc[0]["ic95_inf"]),
        "ic95_sup": float(row_form.iloc[0]["ic95_sup"]),
        "p_holm": float(row_form.iloc[0]["p_holm"]),
    }


def obter_irr_saldo(saldo_time: int) -> dict[str, float | str | bool | None]:
    """Retorna a razão de taxas (IRR) de expulsão pelo saldo no momento (tabela H3)."""
    df = carregar_tabela("h3_irr")

    mapa_saldo5 = {
        -2: ("saldo5[-2]", "desvantagem de 2+ gols"),
        -1: ("saldo5[-1]", "desvantagem de 1 gol"),
        1: ("saldo5[+1]", "vantagem de 1 gol"),
        2: ("saldo5[+2]", "vantagem de 2+ gols"),
    }

    perd_geral = df[(df["modelo"] == "ajustado") & (df["termo"] == "estado[perdendo]")].iloc[0]
    venc_geral = df[(df["modelo"] == "ajustado") & (df["termo"] == "estado[vencendo]")].iloc[0]

    if saldo_time == 0:
        return {
            "irr": 1.0,
            "ic95_inf": 1.0,
            "ic95_sup": 1.0,
            "p_valor": None,
            "significativo": False,
            "descricao": "placar empatado (referência)",
            "irr_perdendo_geral": float(perd_geral["irr"]),
            "ic_perdendo_inf": float(perd_geral["ic95_inf"]),
            "ic_perdendo_sup": float(perd_geral["ic95_sup"]),
            "p_perdendo_geral": float(perd_geral["p_valor"]),
            "irr_vencendo_geral": float(venc_geral["irr"]),
        }

    chave_saldo = max(-2, min(2, int(saldo_time)))
    termo, descricao = mapa_saldo5[chave_saldo]
    row = df[(df["modelo"] == "robustez — saldo em 5 níveis") & (df["termo"] == termo)].iloc[0]
    p_val = float(row["p_valor"])

    return {
        "irr": float(row["irr"]),
        "ic95_inf": float(row["ic95_inf"]),
        "ic95_sup": float(row["ic95_sup"]),
        "p_valor": p_val,
        "significativo": p_val < 0.05,
        "descricao": descricao,
        "irr_perdendo_geral": float(perd_geral["irr"]),
        "ic_perdendo_inf": float(perd_geral["ic95_inf"]),
        "ic_perdendo_sup": float(perd_geral["ic95_sup"]),
        "p_perdendo_geral": float(perd_geral["p_valor"]),
        "irr_vencendo_geral": float(venc_geral["irr"]),
    }


def obter_taxas_faixa() -> dict[str, object]:
    """Retorna as taxas históricas observadas por faixa (H5) e a proporção no terço final."""
    df = carregar_tabela("h5_taxas_faixa")
    todos = df[df["tipo"] == "todos"].copy().reset_index(drop=True)
    total_vermelhos = int(todos["vermelhos"].sum())
    vermelhos_terco_final = int(todos[todos["faixa_rotulo"].isin(["61–75", "76–90+"])]["vermelhos"].sum())
    pct_terco_final = (vermelhos_terco_final / total_vermelhos * 100) if total_vermelhos else 0.0
    return {
        "tabela": todos,
        "total_vermelhos": total_vermelhos,
        "vermelhos_terco_final": vermelhos_terco_final,
        "pct_terco_final": pct_terco_final,
    }


def obter_resumo_base() -> dict[str, float]:
    """Retorna os indicadores gerais do conjunto de dados a partir de resumo_base.csv."""
    df = carregar_tabela("resumo_base")
    return {str(row["chave"]): float(row["valor"]) for _, row in df.iterrows()}


def obter_dados_insights() -> dict[str, object]:
    """Consolida todas as tabelas oficiais geradas em P1 para os três insights acionáveis."""
    df_metas = carregar_tabela("insights_metas").set_index("insight")
    df_liga = carregar_tabela("insights_liga").set_index("metrica")
    df_conv = carregar_tabela("insights_conversao_amarelo").set_index("grupo")
    df_testes = carregar_tabela("insights_testes").set_index("teste")
    df_att = carregar_tabela("h1_pareamento_att").set_index("grupo")
    df_gols = carregar_tabela("h1_gols_irr")
    df_form = carregar_tabela("h5_posicao_formacao")
    df_irr = carregar_tabela("h3_irr")

    form_princ = df_form[df_form["variante"] == "principal"].set_index("posicao")
    gols_todos = df_gols[df_gols["modelo"] == "todos"].set_index("termo")
    gols_fixo = df_gols[df_gols["modelo"].str.startswith("efeito fixo")].set_index("termo")

    return {
        "metas": df_metas,
        "liga": df_liga,
        "conversao": df_conv,
        "testes": df_testes,
        "att": df_att,
        "gols_todos": gols_todos,
        "gols_fixo": gols_fixo,
        "formacao": form_princ,
        "irr_perdendo": df_irr[(df_irr["modelo"] == "ajustado") & (df_irr["termo"] == "estado[perdendo]")].iloc[0],
        "irr_saldo_m1": df_irr[(df_irr["modelo"] == "robustez — saldo em 5 níveis") & (df_irr["termo"] == "saldo5[-1]")].iloc[0],
    }
