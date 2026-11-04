import warnings
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
RAW_DIR = RAIZ / "data" / "raw"
INTERIM_DIR = RAIZ / "data" / "interim"
MANUAL_POSICAO = RAIZ / "data" / "manual" / "posicao_vermelhos.csv"
POSICOES_VALIDAS = {"Goleiro", "Zagueiro", "Meio-campo", "Atacante"}
LIMIAR_IMPUTACAO = 0.8

COLUNAS_ESTATISTICA = [
    "chutes", "chutes_no_alvo", "posse_de_bola", "passes",
    "precisao_passes", "faltas", "impedimentos", "escanteios",
]
PRIMEIRA_TEMPORADA_COM_EVENTOS = 2014
PRIMEIRA_TEMPORADA_380 = 2006
FIM_TEMPORADA_2020 = pd.Timestamp("2021-03-01")


def ler(nome: str) -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / f"campeonato-brasileiro-{nome}.csv")


def separar_minuto(minuto: pd.Series) -> pd.DataFrame:
    partes = minuto.astype(str).str.extract(r"^(\d+)(?:\+(\d+))?$")
    if partes[0].isna().any():
        raise ValueError(f"minutos fora do formato esperado: {minuto[partes[0].isna()].unique()}")
    base = partes[0].astype(int)
    acrescimo = partes[1].fillna(0).astype(int)
    return pd.DataFrame({
        "tempo": np.where(base <= 45, 1, 2),
        "minuto_base": base,
        "acrescimo": acrescimo,
        "minuto_jogado": base + acrescimo,
        "ordem": base + acrescimo / 100,
    })


def limpar_partidas(bruto: pd.DataFrame) -> pd.DataFrame:
    p = bruto.rename(columns={"ID": "partida_id", "rodata": "rodada"})
    p["data"] = pd.to_datetime(p["data"], format="%d/%m/%Y")
    p["temporada"] = p["data"].dt.year
    p.loc[(p["temporada"] == 2021) & (p["data"] < FIM_TEMPORADA_2020), "temporada"] = 2020

    saldo = p["mandante_Placar"] - p["visitante_Placar"]
    p["resultado_mandante"] = np.select([saldo > 0, saldo == 0], ["V", "E"], default="D")
    do_vencedor = np.select(
        [p["vencedor"] == p["mandante"], p["vencedor"] == "-"], ["V", "E"], default="D"
    )
    divergentes = p[p["resultado_mandante"] != do_vencedor]
    if len(divergentes):
        warnings.warn(f"vencedor diverge do placar em {len(divergentes)} partida(s): "
                      f"{divergentes['partida_id'].tolist()}")

    jogos = p.groupby("temporada").size()
    for temporada, n in jogos[jogos.index >= PRIMEIRA_TEMPORADA_380].items():
        if n == 380:
            continue
        if temporada == 2016 and n == 379:
            warnings.warn("temporada 2016 tem 379 jogos (rodada 38 incompleta)")
        else:
            raise ValueError(f"temporada {temporada} tem {n} jogos, esperado 380")
    return p


def limpar_estatisticas(bruto: pd.DataFrame, partidas: pd.DataFrame) -> pd.DataFrame:
    e = bruto.copy()
    for coluna in ("posse_de_bola", "precisao_passes"):
        e[coluna] = pd.to_numeric(e[coluna].astype("string").str.rstrip("%"), errors="coerce")
    ausente = (e["chutes"] == 0) & (e["passes"] == 0) & (e["faltas"] == 0)
    e.loc[ausente, COLUNAS_ESTATISTICA] = np.nan

    if len(e) != 2 * len(partidas):
        raise ValueError("estatisticas deveria ter 2 linhas por partida")
    e = e.merge(partidas[["partida_id", "temporada"]], on="partida_id", validate="many_to_one")
    print("linhas de estatística anuladas por temporada:")
    print(e[ausente.reindex(e.index, fill_value=False)].groupby("temporada").size().to_string())
    return e.drop(columns="temporada")


def limpar_eventos(bruto: pd.DataFrame, partidas: pd.DataFrame) -> pd.DataFrame:
    if not bruto["partida_id"].isin(partidas["partida_id"]).all():
        raise ValueError("evento com partida_id inexistente")
    return pd.concat([bruto, separar_minuto(bruto["minuto"])], axis=1)


def preencher_posicao(cartoes: pd.DataFrame) -> pd.DataFrame:
    c = cartoes.copy()
    c["posicao"] = c["posicao"].replace({"Zagueira": "Zagueiro"})
    c["posicao_origem"] = c["posicao"].where(c["posicao"].isna(), "original")

    frequencias = (
        c.dropna(subset=["posicao"]).groupby("atleta")["posicao"]
        .value_counts(normalize=True).rename("proporcao").reset_index()
        .sort_values("proporcao", ascending=False).drop_duplicates("atleta")
    )
    frequencias = frequencias[frequencias["proporcao"] >= LIMIAR_IMPUTACAO]
    moda = frequencias.set_index("atleta")["posicao"]
    imputavel = c["posicao"].isna() & c["atleta"].isin(moda.index)
    c.loc[imputavel, "posicao"] = c.loc[imputavel, "atleta"].map(moda)
    c.loc[imputavel, "posicao_origem"] = "imputada"

    manual = pd.read_csv(MANUAL_POSICAO).dropna(subset=["posicao"])
    invalidas = set(manual["posicao"]) - POSICOES_VALIDAS
    if invalidas:
        raise ValueError(f"posições manuais inválidas: {invalidas}")
    chave = ["partida_id", "atleta"]
    valores = manual.set_index(chave)["posicao"]
    sem_posicao_original = cartoes["posicao"].isna()
    indice = pd.MultiIndex.from_frame(c.loc[sem_posicao_original, chave])
    preenchido = valores.reindex(indice)
    achou = preenchido.notna().to_numpy()
    alvo = c.index[sem_posicao_original][achou]
    c.loc[alvo, "posicao"] = preenchido.to_numpy()[achou]
    c.loc[alvo, "posicao_origem"] = "manual"
    return c


def validar_gols(gols: pd.DataFrame, partidas: pd.DataFrame) -> None:
    alvo = partidas[partidas["temporada"] >= PRIMEIRA_TEMPORADA_COM_EVENTOS]
    contados = gols.groupby(["partida_id", "clube"]).size()
    for lado, placar in (("mandante", "mandante_Placar"), ("visitante", "visitante_Placar")):
        chaves = pd.MultiIndex.from_arrays([alvo["partida_id"], alvo[lado]])
        obtido = contados.reindex(chaves).fillna(0).to_numpy()
        if (obtido != alvo[placar].to_numpy()).any():
            raise ValueError(f"gols do {lado} não batem com o placar")


def main() -> None:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    partidas = limpar_partidas(ler("full"))
    estatisticas = limpar_estatisticas(ler("estatisticas-full"), partidas)
    gols = limpar_eventos(ler("gols"), partidas)
    cartoes = limpar_eventos(ler("cartoes"), partidas)
    cartoes = preencher_posicao(cartoes)
    print(cartoes["posicao_origem"].value_counts(dropna=False).to_string())
    validar_gols(gols, partidas)

    for nome, tabela in {
        "partidas": partidas, "estatisticas": estatisticas, "gols": gols, "cartoes": cartoes,
    }.items():
        tabela.to_parquet(INTERIM_DIR / f"{nome}.parquet", index=False)
        print(f"ok  {nome}.parquet  ({len(tabela)} linhas)")


if __name__ == "__main__":
    main()
