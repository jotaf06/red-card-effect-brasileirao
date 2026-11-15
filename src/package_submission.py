"""Confere e empacota a entrega final (Parte 2) num .zip.

O enunciado pede: documento final em PDF, código dos experimentos, apresentação e
arquivos adicionais. Antes de empacotar, o script verifica:

- os PDFs obrigatórios existem e são mais novos que seus .typ e que as tabelas;
- o artigo tem no máximo 12 páginas;
- o artigo não tem marcas de "Pendente" nem o "?" de métricas ausentes;
- o código e as tabelas de resultado estão presentes.

Ficam de fora os dados brutos e intermediários (o pipeline baixa e recria tudo),
ambientes virtuais, caches e arquivos de rascunho.

Uso: python -m src.package_submission [--saida entrega/arquivo.zip] [--forcar]
"""
import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from src.clean import RAIZ

MAX_PAGINAS = 12
PDFS = {
    "documento/artigo.pdf": "presentation/artigo.pdf",
    "apresentacao/presentation.pdf": "presentation/presentation.pdf",
}
# (padrão glob relativo à raiz, destino no .zip)
INCLUIR = [
    ("src/**/*.py", "codigo"),
    ("requirements.txt", "codigo"),
    ("data/manual/*.csv", "codigo"),
    ("presentation/*.typ", "codigo"),
    ("presentation/*.csl", "codigo"),
    ("presentation/*.bib", "codigo"),
    ("presentation/fonts/*", "codigo"),
    ("reports/tabelas/*.csv", "extras"),
    ("reports/figures/*.png", "extras"),
]
EXCLUIR = re.compile(r"(__pycache__|\.pyc$|prototipo\.|relatorio\.typ)")

LEIAME = """Quanto custa uma expulsão? Efeito do cartão vermelho no Brasileirão Série A (2014–2024)
José Felix e Rafael Anacleto · Ciência de Dados · UFAL/IC · 2026.2

documento/      artigo final (modelo SBC)
apresentacao/   pitch (5 min) + apresentação técnica (15 min)
codigo/         pipeline completo, com a mesma estrutura de pastas do repositório
extras/         tabelas de resultado (fonte de todo número citado) e figuras

Para reproduzir, a partir de codigo/:
    python -m venv venv && venv/bin/pip install -r requirements.txt
    venv/bin/python -m src.run_all              # baixa os dados, roda tudo e compila os PDFs (requer typst)
    venv/bin/python -m src.run_all --sem-docs   # só a análise
    venv/bin/streamlit run src/dashboard/app.py # dashboard interativo (extra)
"""


def paginas_pdf(caminho: Path) -> int | None:
    if shutil.which("pdfinfo"):
        saida = subprocess.run(["pdfinfo", str(caminho)], capture_output=True, text=True).stdout
        m = re.search(r"^Pages:\s+(\d+)", saida, re.M)
        if m:
            return int(m.group(1))
    return None


def texto_pdf(caminho: Path) -> str | None:
    if shutil.which("pdftotext"):
        return subprocess.run(["pdftotext", str(caminho), "-"], capture_output=True, text=True).stdout
    return None


def verificar() -> list[str]:
    problemas = []
    tabelas = list((RAIZ / "reports/tabelas").glob("*.csv"))
    tabela_mais_nova = max(p.stat().st_mtime for p in tabelas) if tabelas else 0
    for origem in PDFS.values():
        pdf = RAIZ / origem
        if not pdf.exists():
            problemas.append(f"falta {origem} (rode python -m src.run_all)")
            continue
        fonte = pdf.with_suffix(".typ")
        referencia = max(fonte.stat().st_mtime if fonte.exists() else 0, tabela_mais_nova)
        if pdf.stat().st_mtime < referencia:
            problemas.append(f"{origem} está desatualizado em relação ao .typ ou às tabelas")

    artigo = RAIZ / "presentation/artigo.pdf"
    if artigo.exists():
        n = paginas_pdf(artigo)
        if n is None:
            print("aviso: pdfinfo indisponível, número de páginas não conferido")
        elif n > MAX_PAGINAS:
            problemas.append(f"artigo com {n} páginas (máximo {MAX_PAGINAS})")
        texto = texto_pdf(artigo)
        if texto is None:
            print("aviso: pdftotext indisponível, pendências no texto não conferidas")
        else:
            if "Pendente" in texto:
                problemas.append("artigo ainda tem marcas de 'Pendente'")
            if re.search(r"\?\s*→\s*\?", texto):
                problemas.append("artigo tem métricas ausentes ('? → ?')")

    for obrigatorio in ("src/run_all.py", "requirements.txt", "presentation/dados.typ"):
        if not (RAIZ / obrigatorio).exists():
            problemas.append(f"falta {obrigatorio}")
    return problemas


def arquivos() -> list[tuple[Path, str]]:
    itens = []
    for destino_zip, origem in PDFS.items():
        itens.append((RAIZ / origem, destino_zip))
    for padrao, pasta in INCLUIR:
        for p in sorted(RAIZ.glob(padrao)):
            rel = p.relative_to(RAIZ).as_posix()
            if p.is_file() and not EXCLUIR.search(rel):
                itens.append((p, f"{pasta}/{rel}"))
    return itens


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--saida", default="entrega/red-card-effect-brasileirao.zip")
    parser.add_argument("--forcar", action="store_true", help="empacota mesmo com problemas")
    args = parser.parse_args()

    problemas = verificar()
    for p in problemas:
        print(f"problema: {p}")
    if problemas and not args.forcar:
        sys.exit("entrega não gerada (corrija os problemas ou use --forcar)")

    saida = RAIZ / args.saida
    saida.parent.mkdir(parents=True, exist_ok=True)
    itens = arquivos()
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("LEIAME.txt", LEIAME)
        for origem, destino in itens:
            z.write(origem, destino)
    tamanho = saida.stat().st_size / 1e6
    print(f"ok  {saida.relative_to(RAIZ)}: {len(itens) + 1} arquivos, {tamanho:.1f} MB")


if __name__ == "__main__":
    main()
