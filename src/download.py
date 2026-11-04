import argparse
import csv
import urllib.request
from pathlib import Path

BASE_URL = "https://raw.githubusercontent.com/adaoduque/Brasileirao_Dataset/master"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

ARQUIVOS = {
    "campeonato-brasileiro-full.csv": (
        8785,
        ["ID", "rodata", "data", "hora", "mandante", "visitante", "formacao_mandante",
         "formacao_visitante", "tecnico_mandante", "tecnico_visitante", "vencedor", "arena",
         "mandante_Placar", "visitante_Placar", "mandante_Estado", "visitante_Estado"],
    ),
    "campeonato-brasileiro-estatisticas-full.csv": (
        17570,
        ["partida_id", "rodata", "clube", "chutes", "chutes_no_alvo", "posse_de_bola", "passes",
         "precisao_passes", "faltas", "cartao_amarelo", "cartao_vermelho", "impedimentos",
         "escanteios"],
    ),
    "campeonato-brasileiro-gols.csv": (
        9861,
        ["partida_id", "rodata", "clube", "atleta", "minuto", "tipo_de_gol"],
    ),
    "campeonato-brasileiro-cartoes.csv": (
        20953,
        ["partida_id", "rodata", "clube", "cartao", "atleta", "num_camisa", "posicao", "minuto"],
    ),
}


def baixar(nome: str, force: bool) -> Path:
    destino = RAW_DIR / nome
    if destino.exists() and not force:
        return destino
    temporario = destino.with_suffix(".csv.part")
    urllib.request.urlretrieve(f"{BASE_URL}/{nome}", temporario)
    temporario.replace(destino)
    return destino


def validar(caminho: Path, linhas_esperadas: int, colunas_esperadas: list[str]) -> None:
    with open(caminho, newline="", encoding="utf-8") as f:
        leitor = csv.reader(f)
        cabecalho = next(leitor)
        n_linhas = sum(1 for _ in leitor)
    if cabecalho != colunas_esperadas:
        raise ValueError(f"{caminho.name}: colunas diferentes do esperado: {cabecalho}")
    if n_linhas != linhas_esperadas:
        raise ValueError(f"{caminho.name}: {n_linhas} linhas, esperado {linhas_esperadas}")


def main(force: bool = False) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for nome, (linhas, colunas) in ARQUIVOS.items():
        caminho = baixar(nome, force)
        validar(caminho, linhas, colunas)
        print(f"ok  {nome}  ({linhas} linhas)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baixa os CSVs brutos para data/raw/.")
    parser.add_argument("--force", action="store_true", help="baixa novamente mesmo se já existir")
    main(parser.parse_args().force)
