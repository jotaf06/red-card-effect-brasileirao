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
    """Carrega o dicionário contendo todas as tabelas analíticas pré-calculadas."""
    nomes = [
        "resumo_base",
        "h1_custo_minuto",
        "h1_pareamento_att",
        "h1_gols_irr",
        "h3_irr",
        "h5_taxas_faixa",
        "h5_posicao_cartao",
        "h5_posicao_formacao",
        "modelos_metricas",
        "modelos_shap_importancia",
        "modelos_custo_curvas",
        "h1_modelo_estado_coeficientes",
    ]
    return {nome: carregar_tabela(nome) for nome in nomes}


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
    
    if minuto <= 15:
        faixa = "faixa 0–15"
    elif minuto <= 30:
        faixa = "faixa 16–30"
    elif minuto <= 45:
        faixa = "faixa 31–45+"
    elif minuto <= 60:
        faixa = "faixa 46–60"
    elif minuto <= 75:
        faixa = "faixa 61–75"
    else:
        faixa = "faixa 76–90"
        
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
        
    return {
        "faixa": faixa,
        "att": float(r_faixa["att"]),
        "ic95_inf": float(r_faixa["ic95_inf"]),
        "ic95_sup": float(r_faixa["ic95_sup"]),
        "n_tratados": int(r_faixa["n_tratados"]),
        "att_lado": att_lado,
        "att_estado": att_estado,
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
    
    taxa_conv = float(row_pos.iloc[0]["proporcao"]) * 100 if not row_pos.empty else 5.0
    razao = float(row_form.iloc[0]["razao_obs_esp"]) if not row_form.empty else 1.0
    p_val = float(row_form.iloc[0]["p_holm"]) if not row_form.empty else 1.0
    
    return {
        "posicao": posicao,
        "taxa_conversao": taxa_conv,
        "razao_obs_esp": razao,
        "p_holm": p_val,
    }
