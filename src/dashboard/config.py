"""Configurações, estilos visuais e constantes do Dashboard Interativo."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
TABELAS_DIR = RAIZ / "reports" / "tabelas"
FIGURES_DIR = RAIZ / "reports" / "figures"

PAGE_TITLE = "Quanto Custa uma Expulsão? | Painel Tático Série A"
PAGE_ICON = ""
LAYOUT = "wide"

CORES = {
    "azul_primario": "#339af0",
    "azul_escuro": "#1971c2",
    "azul_fundo": "rgba(25, 113, 194, 0.16)",
    "vermelho_alerta": "#ff6b6b",
    "vermelho_fundo": "rgba(255, 107, 107, 0.16)",
    "verde_sucesso": "#51cf66",
    "verde_fundo": "rgba(81, 207, 102, 0.16)",
    "amarelo_aviso": "#fcc419",
    "amarelo_fundo": "rgba(252, 196, 25, 0.16)",
    "cinza_suave": "#868e96",
    "cinza_borda": "rgba(134, 142, 150, 0.3)",
}

OPCOES_SALDO = {
    "Perdendo por 2 ou mais (-2)": -2,
    "Perdendo por 1 gol (-1)": -1,
    "Empatando (0)": 0,
    "Vencendo por 1 gol (+1)": 1,
    "Vencendo por 2 ou mais (+2)": 2,
}

OPCOES_ELO = {
    "Equilibrado (Elo 0)": 0.0,
    "Favorito Moderado (Elo +50)": 50.0,
    "Super Favorito (Elo +100)": 100.0,
    "Azarão Moderado (Elo -50)": -50.0,
    "Grande Azarão (Elo -100)": -100.0,
}

POSICOES = ["Zagueiro", "Meio-campo", "Atacante", "Goleiro"]

CUSTOM_CSS = """
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #339af0;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: inherit !important;
        opacity: 0.85;
        margin-bottom: 1.5rem;
    }
    .metric-card, .metric-card-danger, .metric-card-success {
        border-radius: 8px !important;
        padding: 14px 10px !important;
        text-align: center !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: space-between !important;
        height: 165px !important;
        min-height: 165px !important;
        max-height: 165px !important;
        box-sizing: border-box !important;
        color: inherit !important;
    }
    .metric-card {
        background-color: rgba(134, 142, 150, 0.14) !important;
        border: 1px solid rgba(134, 142, 150, 0.3) !important;
    }
    .metric-card-danger {
        background-color: rgba(255, 107, 107, 0.15) !important;
        border: 1px solid rgba(255, 107, 107, 0.35) !important;
    }
    .metric-card-success {
        background-color: rgba(81, 207, 102, 0.15) !important;
        border: 1px solid rgba(81, 207, 102, 0.35) !important;
    }
    .metric-value, .metric-value-danger, .metric-value-success {
        font-size: 2.05rem !important;
        font-weight: 800 !important;
        line-height: 1.1 !important;
        height: 44px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin-bottom: 2px !important;
    }
    .metric-value {
        color: #339af0 !important;
    }
    .metric-value-danger {
        color: #ff6b6b !important;
    }
    .metric-value-success {
        color: #51cf66 !important;
    }
    .metric-label {
        font-size: 0.90rem !important;
        font-weight: 600 !important;
        color: inherit !important;
        height: 24px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 2px 0px !important;
    }
    .metric-subtext {
        font-size: 0.78rem !important;
        color: inherit !important;
        opacity: 0.75 !important;
        line-height: 1.25 !important;
        height: 38px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
    }
    .tactical-box {
        background-color: rgba(25, 113, 194, 0.16) !important;
        border-left: 5px solid #339af0 !important;
        padding: 16px 20px !important;
        border-radius: 6px !important;
        margin: 14px 0px !important;
        color: inherit !important;
    }
    .tactical-box * {
        color: inherit !important;
    }
    .alert-box-critical {
        background-color: rgba(255, 107, 107, 0.16) !important;
        border-left: 5px solid #ff6b6b !important;
        padding: 16px 20px !important;
        border-radius: 6px !important;
        margin: 14px 0px !important;
        color: inherit !important;
    }
    .alert-box-critical * {
        color: inherit !important;
    }
    .alert-box-warning {
        background-color: rgba(252, 196, 25, 0.16) !important;
        border-left: 5px solid #fcc419 !important;
        padding: 16px 20px !important;
        border-radius: 6px !important;
        margin: 14px 0px !important;
        color: inherit !important;
    }
    .alert-box-warning * {
        color: inherit !important;
    }
    .info-card {
        background-color: rgba(134, 142, 150, 0.14) !important;
        border: 1px solid rgba(134, 142, 150, 0.3) !important;
        border-radius: 6px !important;
        padding: 16px 18px !important;
        color: inherit !important;
    }
    .info-card * {
        color: inherit !important;
    }
    .status-banner {
        border-radius: 6px !important;
        padding: 18px 22px !important;
        margin-bottom: 20px !important;
        border-left: 6px solid !important;
        color: inherit !important;
    }
    .status-banner * {
        color: inherit !important;
    }
    div[data-baseweb="select"] {
        cursor: pointer !important;
    }
    div[data-baseweb="select"] input {
        caret-color: transparent !important;
        cursor: pointer !important;
    }
</style>
"""
