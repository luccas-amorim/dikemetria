"""Guarda do repositório: impede que dados pessoais entrem no git.

Roda no CI e antes de cada commit (`.githooks/pre-commit`):

    python -m dikemetria.guarda            # arquivos versionados
    python -m dikemetria.guarda --staged   # só o que vai no próximo commit

Falha quando encontra:

1. documento ou banco versionado (PDF, DOCX, RTF, imagens, SQLite...): autos e decisões reais
   chegam nesses formatos;
2. arquivo em caminho reservado a dados locais (`dados/`, `saida/`, `docs/processo-temp/`...);
3. arquivo maior que 1 MB;
4. CPF, CNPJ ou número de processo CNJ com dígitos verificadores **válidos**: números inventados
   para testes quase nunca têm dígito válido; os poucos que têm ficam em `FICTICIOS`;
5. notebook com saídas gravadas, que podem conter texto de decisões.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

TAMANHO_MAXIMO = 1_000_000  # bytes

EXTENSOES_PROIBIDAS = {
    ".pdf", ".doc", ".docx", ".odt", ".rtf", ".msg", ".eml",
    ".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".bmp", ".heic", ".webp",
    ".sqlite", ".sqlite3", ".db", ".zip", ".7z", ".rar", ".gz", ".xlsx", ".xls",
}  # fmt: skip

CAMINHOS_PROIBIDOS = ("dados/", "saida/", "temp/", "docs/processo-temp/")

# Números com dígito válido usados de propósito nos testes: o CPF clássico de exemplo e os
# processos de `tests/conftest.py`, que testam a validação do número CNJ.
FICTICIOS = {"12345678909", "10012348820238260100", "00045670820224047000"}

_CPF = re.compile(r"(?<![\d.])(\d{3})\.?(\d{3})\.?(\d{3})-?(\d{2})(?![\d.])")
_CNPJ = re.compile(r"(?<![\d.])(\d{2})\.?(\d{3})\.?(\d{3})/?(\d{4})-?(\d{2})(?![\d.])")
_CNJ = re.compile(r"(?<!\d)(\d{7})-?(\d{2})\.?(\d{4})\.?(\d)\.?(\d{2})\.?(\d{4})(?!\d)")


@dataclass(frozen=True)
class Achado:
    arquivo: str
    motivo: str
    linha: int | None = None

    def __str__(self) -> str:
        onde = f"{self.arquivo}:{self.linha}" if self.linha else self.arquivo
        return f"{onde}: {self.motivo}"


def cpf_valido(digitos: str) -> bool:
    if len(digitos) != 11 or len(set(digitos)) == 1:
        return False
    for posicao in (9, 10):
        soma = sum(int(d) * (posicao + 1 - i) for i, d in enumerate(digitos[:posicao]))
        if (soma * 10 % 11) % 10 != int(digitos[posicao]):
            return False
    return True


def cnpj_valido(digitos: str) -> bool:
    if len(digitos) != 14 or len(set(digitos)) == 1:
        return False
    for posicao in (12, 13):
        pesos = list(range(posicao - 7, 1, -1)) + list(range(9, 1, -1))
        soma = sum(int(d) * p for d, p in zip(digitos[:posicao], pesos, strict=True))
        resto = soma % 11
        if (0 if resto < 2 else 11 - resto) != int(digitos[posicao]):
            return False
    return True


def cnj_valido(numero: str, dv: str, ano: str, segmento: str, tribunal: str, origem: str) -> bool:
    """Dígito verificador do número único (Resolução CNJ 65/2008, módulo 97)."""
    base = int(f"{numero}{ano}{segmento}{tribunal}{origem}")
    return 98 - (base * 100 % 97) == int(dv)


def _documentos_validos(texto: str) -> list[tuple[int, str]]:
    achados = []
    for numero_linha, linha in enumerate(texto.splitlines(), start=1):
        for m in _CPF.finditer(linha):
            digitos = "".join(m.groups())
            if digitos not in FICTICIOS and cpf_valido(digitos):
                achados.append((numero_linha, "CPF com dígito verificador válido"))
        for m in _CNPJ.finditer(linha):
            digitos = "".join(m.groups())
            if digitos not in FICTICIOS and cnpj_valido(digitos):
                achados.append((numero_linha, "CNPJ com dígito verificador válido"))
        for m in _CNJ.finditer(linha):
            if "".join(m.groups()) not in FICTICIOS and cnj_valido(*m.groups()):
                achados.append((numero_linha, "número de processo CNJ válido"))
    return achados


def _saidas_de_notebook(conteudo: bytes) -> bool:
    try:
        notebook = json.loads(conteudo)
    except ValueError:
        return False
    return any(celula.get("outputs") for celula in notebook.get("cells", []))


def verificar_arquivo(caminho: str, conteudo: bytes) -> list[Achado]:
    """Achados de um arquivo, pelo caminho relativo à raiz do repositório e pelo conteúdo."""
    achados = []
    relativo = PurePosixPath(caminho)
    if relativo.suffix.lower() in EXTENSOES_PROIBIDAS:
        achados.append(
            Achado(caminho, f"formato {relativo.suffix.lower()} não pode ser versionado")
        )
    if any(str(relativo).startswith(prefixo) for prefixo in CAMINHOS_PROIBIDOS):
        achados.append(Achado(caminho, "caminho reservado a dados locais"))
    if len(conteudo) > TAMANHO_MAXIMO:
        achados.append(Achado(caminho, f"arquivo com {len(conteudo):,} bytes (máximo 1 MB)"))
    if relativo.suffix == ".ipynb" and _saidas_de_notebook(conteudo):
        achados.append(Achado(caminho, "notebook com saídas gravadas; limpe antes do commit"))
    try:
        texto = conteudo.decode("utf-8")
    except UnicodeDecodeError:
        return achados
    achados += [Achado(caminho, motivo, linha) for linha, motivo in _documentos_validos(texto)]
    return achados


def _arquivos(staged: bool) -> list[str]:
    comando = (
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"]
        if staged
        else ["git", "ls-files", "-z"]
    )
    saida = subprocess.run(comando, capture_output=True, check=True).stdout
    return [nome for nome in saida.decode("utf-8").split("\0") if nome]


def _conteudo(caminho: str, staged: bool) -> bytes:
    if staged:
        return subprocess.run(["git", "show", f":{caminho}"], capture_output=True).stdout
    return Path(caminho).read_bytes() if Path(caminho).is_file() else b""


def verificar(staged: bool = False) -> list[Achado]:
    achados = []
    for caminho in _arquivos(staged):
        achados += verificar_arquivo(caminho, _conteudo(caminho, staged))
    return achados


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--staged", action="store_true", help="só os arquivos do próximo commit")
    args = parser.parse_args(argv)
    achados = verificar(args.staged)
    for achado in achados:
        print(achado, file=sys.stderr)
    if achados:
        print(
            f"\n{len(achados)} problema(s). Dados reais ficam fora do git (README, LGPD).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
