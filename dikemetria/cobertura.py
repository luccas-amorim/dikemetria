"""Cobertura do DataJud: quantos dos casos novos de cada tribunal estão no índice.

Compara, por tribunal e ano, os processos de primeiro grau e de juizado (G1 e JE) ajuizados no ano
que o DataJud devolve com os casos novos do mesmo ano no Justiça em Números (CNJ), na base de dados
publicada em https://www.cnj.jus.br/pesquisas-judiciarias/justica-em-numeros/base-de-dados/.

A razão não é exata: o DataJud tem classes que o Justiça em Números não conta como caso novo
(cartas precatórias, incidentes), e os critérios mudam entre tribunais. Serve para achar lacunas
grandes. Em 2024, a maioria dos tribunais estaduais ficou entre 0,89 e 1,18; o TJDFT ficou em 0,15
(índice incompleto) e o TJMG em 1,71 (provável duplicidade). Tribunal fora da faixa
`FAIXA_ACEITAVEL` não deve entrar em comparação regional sem correção.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dikemetria.coleta import datajud
from dikemetria.coleta.http import Cliente
from dikemetria.coleta.tribunais import Tribunal
from dikemetria.recorte import RecorteDataJud

FAIXA_ACEITAVEL = (0.8, 1.25)

# Casos novos de conhecimento e de execução extrajudicial no 1º grau e nos juizados.
CAMPOS_PRIMEIRO_GRAU = (
    "cnccrim1",
    "cncncrim1",
    "cnextfisc1",
    "cnextnfisc1",
    "cnccrimje",
    "cncncrimje",
    "cnextje",
)


@dataclass(frozen=True)
class Cobertura:
    tribunal: str
    ano: int
    datajud: int | None
    casos_novos: float | None

    @property
    def razao(self) -> float | None:
        if not self.datajud or not self.casos_novos:
            return None
        return self.datajud / self.casos_novos

    @property
    def aceitavel(self) -> bool:
        return self.razao is not None and FAIXA_ACEITAVEL[0] <= self.razao <= FAIXA_ACEITAVEL[1]


def _numero(valor: str | None) -> float:
    try:
        return float(str(valor).replace(",", "."))
    except ValueError:
        return 0.0  # "nd" (não disponível) e vazios


def casos_novos(caminho: str | Path, ano: int) -> dict[str, float]:
    """Casos novos de 1º grau e juizados por sigla (minúsculas), do CSV do Justiça em Números."""
    totais: dict[str, float] = {}
    with open(caminho, encoding="latin-1", newline="") as arquivo:
        for linha in csv.DictReader(arquivo, delimiter=";"):
            if linha.get("ano") != str(ano):
                continue
            total = sum(_numero(linha.get(campo)) for campo in CAMPOS_PRIMEIRO_GRAU)
            if total:
                totais[linha["sigla"].strip().lower()] = total
    return totais


def medir(
    cliente: Cliente, tribunais: Iterable[Tribunal], ano: int, caminho_jn: str | Path
) -> list[Cobertura]:
    """Razão DataJud ÷ Justiça em Números para cada tribunal com primeiro grau."""
    oficiais = casos_novos(caminho_jn, ano)
    recorte = RecorteDataJud(
        graus=["G1", "JE"],
        ajuizamento_desde=date(ano, 1, 1),
        ajuizamento_ate=date(ano, 12, 31),
        ordem="atualizacao",
    )
    resultado = []
    for tribunal in tribunais:
        if tribunal.ramo == "superior":
            continue
        resultado.append(
            Cobertura(
                tribunal.sigla,
                ano,
                datajud.contar(cliente, tribunal, recorte),
                oficiais.get(tribunal.sigla),
            )
        )
    return resultado
