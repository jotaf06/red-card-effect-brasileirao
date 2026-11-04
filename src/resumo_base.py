import pandas as pd

from src.clean import INTERIM_DIR, RAIZ, RAW_DIR, PRIMEIRA_TEMPORADA_COM_EVENTOS

SAIDA = RAIZ / "reports" / "tabelas" / "resumo_base.csv"


def colunas_raw(nome: str) -> int:
    return pd.read_csv(RAW_DIR / f"campeonato-brasileiro-{nome}.csv", nrows=0).shape[1]


def main() -> None:
    partidas = pd.read_parquet(INTERIM_DIR / "partidas.parquet")
    estatisticas = pd.read_parquet(INTERIM_DIR / "estatisticas.parquet")
    cartoes = pd.read_parquet(INTERIM_DIR / "cartoes.parquet")
    gols = pd.read_parquet(INTERIM_DIR / "gols.parquet")

    analise = partidas[partidas["temporada"] >= PRIMEIRA_TEMPORADA_COM_EVENTOS]
    vermelhos = cartoes[cartoes["cartao"] == "Vermelho"]
    anuladas = estatisticas.merge(partidas[["partida_id", "temporada"]], on="partida_id")
    anuladas = anuladas[anuladas["chutes"].isna()]
    origem = cartoes["posicao_origem"].value_counts()
    taxas = partidas["resultado_mandante"].value_counts(normalize=True) * 100

    metricas = {
        "partidas_total": len(partidas),
        "partidas_2014_2024": len(analise),
        "temporadas_total": partidas["temporada"].nunique(),
        "colunas_partidas": colunas_raw("full"),
        "estatisticas_linhas": len(estatisticas),
        "colunas_estatisticas": colunas_raw("estatisticas-full"),
        "gols_linhas": len(gols),
        "colunas_gols": colunas_raw("gols"),
        "cartoes_linhas": len(cartoes),
        "colunas_cartoes": colunas_raw("cartoes"),
        "amarelos": (cartoes["cartao"] == "Amarelo").sum(),
        "vermelhos": len(vermelhos),
        "partidas_com_vermelho": vermelhos["partida_id"].nunique(),
        "pct_partidas_com_vermelho": round(
            100 * vermelhos["partida_id"].nunique() / len(analise), 1),
        "vermelhos_1o_tempo_regulamentar": (
            (vermelhos["tempo"] == 1) & (vermelhos["acrescimo"] == 0)).sum(),
        "vermelhos_acrescimo_1o_tempo": (
            (vermelhos["tempo"] == 1) & (vermelhos["acrescimo"] > 0)).sum(),
        "estatisticas_anuladas_total": len(anuladas),
        "estatisticas_anuladas_2015_2023": anuladas["temporada"].between(2015, 2023).sum(),
        "posicao_nula_original": cartoes["posicao"].isna().sum() + origem.get("imputada", 0)
        + origem.get("manual", 0),
        "posicao_imputada": origem.get("imputada", 0),
        "posicao_manual": origem.get("manual", 0),
        "posicao_nula_final": cartoes["posicao"].isna().sum(),
        "vermelhos_posicao_nula_final": vermelhos["posicao"].isna().sum(),
        "pct_vitoria_mandante": round(taxas["V"], 1),
        "pct_empate": round(taxas["E"], 1),
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    pd.Series(metricas, name="valor", dtype=object).rename_axis("chave").astype(str).to_csv(SAIDA)
    print(pd.Series(metricas, dtype=object).to_string())


if __name__ == "__main__":
    main()
