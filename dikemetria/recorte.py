"""Recorte de pesquisa: o que coletar, de quais tribunais, em que período.

Lido de um arquivo TOML (veja recortes/exemplo.toml).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass
class RecorteDataJud:
    assuntos_codigos: list[int] = field(default_factory=list)
    assuntos_nomes: list[str] = field(default_factory=list)
    classes_codigos: list[int] = field(default_factory=list)
    graus: list[str] = field(default_factory=list)  # G1, G2, JE, TR, SUP...
    ajuizamento_desde: date | None = None
    ajuizamento_ate: date | None = None
    limite_por_tribunal: int | None = None
    tamanho_pagina: int = 500


@dataclass
class RecorteDJEN:
    texto: str | None = None
    tipos_documento: list[str] = field(default_factory=lambda: ["Sentença", "Acórdão"])
    data_inicio: date | None = None
    data_fim: date | None = None
    limite_por_tribunal: int | None = None
    itens_por_pagina: int = 100


@dataclass
class Recorte:
    nome: str
    descricao: str = ""
    tribunais: list[str] = field(default_factory=lambda: ["todos"])
    incluir_sensiveis: bool = False
    datajud: RecorteDataJud = field(default_factory=RecorteDataJud)
    djen: RecorteDJEN = field(default_factory=RecorteDJEN)


def _data(valor) -> date | None:
    if valor is None or isinstance(valor, date):
        return valor
    return date.fromisoformat(str(valor))


def carregar(caminho: str | Path) -> Recorte:
    with open(caminho, "rb") as arquivo:
        dados = tomllib.load(arquivo)

    dj = dict(dados.pop("datajud", {}))
    for chave in ("ajuizamento_desde", "ajuizamento_ate"):
        dj[chave] = _data(dj.get(chave))
    djen = dict(dados.pop("djen", {}))
    for chave in ("data_inicio", "data_fim"):
        djen[chave] = _data(djen.get(chave))

    if "nome" not in dados:
        raise ValueError(f"O recorte {caminho} precisa de um campo 'nome'.")
    return Recorte(**dados, datajud=RecorteDataJud(**dj), djen=RecorteDJEN(**djen))
