"""Executa o pipeline completo: download → limpeza → resumo → features → testes → modelos → insights → avaliação → documentos Typst.

Uso (a partir da raiz do repositório):
    python -m src.run_all            # pipeline completo
    python -m src.run_all --force    # baixa os CSVs de novo
    python -m src.run_all --sem-docs # não compila os documentos Typst
"""
import argparse
import shutil
import subprocess

from src import clean, download, evaluate, features, insights, models, resumo_base, stats_tests
from src.clean import RAIZ

DOCUMENTOS = ["presentation/relatorio.typ", "presentation/slides.typ"]


def compilar_documentos() -> None:
    typst = shutil.which("typst")
    if typst is None:
        raise SystemExit("typst não encontrado no PATH (use --sem-docs para pular)")
    for doc in DOCUMENTOS:
        subprocess.run([typst, "compile", "--root", ".", doc], cwd=RAIZ, check=True)
        print(f"ok  {doc}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="baixa os CSVs de novo")
    parser.add_argument("--sem-docs", action="store_true", help="não compila os documentos Typst")
    args = parser.parse_args()

    etapas = [
        ("download", lambda: download.main(args.force)),
        ("limpeza", clean.main),
        ("resumo da base", resumo_base.main),
        ("features", features.main),
        ("testes de hipótese (H3, H5)", stats_tests.main),
        ("modelos do efeito (H1, H2, H4)", models.main),
        ("insights (metas e linha de base da liga)", insights.main),
        ("comparação de modelos", evaluate.main),
    ]
    if not args.sem_docs:
        etapas.append(("documentos", compilar_documentos))

    for i, (nome, etapa) in enumerate(etapas, start=1):
        print(f"\n=== [{i}/{len(etapas)}] {nome} ===")
        etapa()
    print("\npipeline concluído")


if __name__ == "__main__":
    main()
