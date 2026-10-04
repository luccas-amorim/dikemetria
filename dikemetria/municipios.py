"""Município da unidade judiciária, com código do IBGE confiável.

O DataJud informa `orgaoJulgador.codigoMunicipioIBGE`, mas alguns tribunais preenchem o campo
com numeração própria (o TJRN usa códigos de quatro dígitos). Um código errado produziria viés
regional falso, por isso:

1. o código só é aceito se existir na lista de municípios do IBGE (`dados/municipios.csv`);
2. senão, a tabela `dados/municipios_tribunais.csv` (tribunal, código do tribunal, código IBGE),
   para os tribunais com numeração própria;
3. senão, procura-se o município no nome do órgão julgador ("Vara Única da Comarca de Touros",
   "15ª Vara JEF - Salvador"), só entre os municípios da UF do tribunal;
4. senão, o município fica vazio, e o código original é guardado à parte.

Em outubro de 2026, TJRN e TRF5 usam numeração própria ou zero, o TJMT não informa o campo e
parte do TRF1 só se resolve pelo nome. A tabela de conversão ainda precisa ser montada com o
cadastro de serventias do CNJ, que este ambiente não alcança.

Fonte da lista: IBGE, via github.com/kelvins/municipios-brasileiros (licença MIT).
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import cache
from importlib import resources

from dikemetria.limpeza import sem_acentos


@dataclass(frozen=True)
class Municipio:
    codigo_ibge: int
    nome: str
    uf: str  # minúsculas, como em `tribunais.UFS`
    capital: bool


@cache
def municipios() -> dict[int, Municipio]:
    arquivo = resources.files("dikemetria").joinpath("dados/municipios.csv")
    with arquivo.open(encoding="utf-8") as conteudo:
        return {
            int(linha["codigo_ibge"]): Municipio(
                int(linha["codigo_ibge"]),
                linha["nome"],
                linha["uf"].lower(),
                linha["capital"] == "1",
            )
            for linha in csv.DictReader(conteudo)
        }


@cache
def conversoes() -> dict[tuple[str, str], int]:
    """Tabela (tribunal, código do tribunal) → código IBGE, para quem usa numeração própria."""
    arquivo = resources.files("dikemetria").joinpath("dados/municipios_tribunais.csv")
    with arquivo.open(encoding="utf-8") as conteudo:
        return {
            (linha["tribunal"], linha["codigo_tribunal"]): int(linha["codigo_ibge"])
            for linha in csv.DictReader(conteudo)
        }


def _normalizar(texto: str) -> str:
    texto = sem_acentos(texto.lower()).replace("'", " ").replace("-", " ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", texto)).strip()


@cache
def _por_nome(uf: str) -> dict[str, int]:
    return {_normalizar(m.nome): m.codigo_ibge for m in municipios().values() if m.uf == uf}


# "Vara Única da Comarca de Touros", "Foro de Touros": o município vem depois da palavra.
_LOCAL = re.compile(r"\b(?:comarca|foro|termo|municipio|cidade)\s+(?:de|do|da|dos|das)\s+(.+)$")


def municipio_no_nome(nome_orgao: str | None, ufs: tuple[str, ...]) -> int | None:
    """Código IBGE do município citado no nome do órgão, ou None se não houver um só candidato.

    Depois de "comarca de" / "foro de", basta o nome começar pelo município; no fim do nome
    ("... - Salvador", "... de Campo Grande"), o trecho tem de ser exatamente o município. A busca
    fica restrita às UFs do tribunal, e um nome ambíguo não é resolvido.
    """
    if not nome_orgao or not ufs:
        return None
    nome = _normalizar(nome_orgao.replace("/", " "))
    por_nome = {n: c for uf in ufs for n, c in _por_nome(uf).items()}
    candidatos: set[tuple[int, int]] = set()
    local = _LOCAL.search(nome)
    if local:
        for nome_municipio, codigo in por_nome.items():
            if re.match(rf"{re.escape(nome_municipio)}\b", local.group(1)):
                candidatos.add((len(nome_municipio), codigo))
    if not candidatos:
        # Último trecho depois de " - " ou de "de/do/da", sem a UF no fim.
        segmentos = [
            _normalizar(p) for p in re.split(r"\s*[-–]\s+|\s+[-–]\s*", nome_orgao.replace("/", " "))
        ]
        trechos = [segmentos[-1]] if len(segmentos) > 1 else []
        trechos += [nome[m.end() :] for m in re.finditer(r"\s(?:de|do|da|dos|das)\s", nome)]
        for trecho in trechos:
            trecho = re.sub(rf"\s(?:{'|'.join(ufs)})$", "", trecho.strip())
            if trecho in por_nome:
                candidatos.add((len(trecho), por_nome[trecho]))
                break
        if not candidatos and len(segmentos) > 1:
            # "2ª TR - R1 Teresina": o município fecha o último trecho.
            ultimo = re.sub(rf"\s(?:{'|'.join(ufs)})$", "", segmentos[-1])
            for nome_municipio, codigo in por_nome.items():
                if ultimo.endswith(" " + nome_municipio):
                    candidatos.add((len(nome_municipio), codigo))
    if not candidatos:
        return None
    maior = max(tamanho for tamanho, _ in candidatos)
    melhores = {codigo for tamanho, codigo in candidatos if tamanho == maior}
    return melhores.pop() if len(melhores) == 1 else None


def resolver(
    codigo: object, nome_orgao: str | None, ufs: tuple[str, ...], tribunal: str | None = None
) -> tuple[int | None, str]:
    """(código IBGE, método): "ibge", "tabela", "nome do órgão" ou "não resolvido"."""
    try:
        numero = int(str(codigo).strip())
    except (TypeError, ValueError):
        numero = None
    if numero in municipios() and (not ufs or municipios()[numero].uf in ufs):
        return numero, "ibge"
    if tribunal and (tribunal, str(codigo)) in conversoes():
        return conversoes()[(tribunal, str(codigo))], "tabela"
    pelo_nome = municipio_no_nome(nome_orgao, ufs)
    if pelo_nome is not None:
        return pelo_nome, "nome do órgão"
    return None, "não resolvido"
