"""API Pública do DataJud (CNJ): metadados e movimentos de todos os tribunais, menos o STF.

Documentação: https://datajud-wiki.cnj.jus.br/api-publica/

A API exige uma chave pública, divulgada pelo CNJ na documentação acima e trocada de tempos em
tempos. A chave abaixo é a divulgada na data desta versão. Se ela parar de funcionar, defina a
variável de ambiente DATAJUD_API_KEY com a chave atual.

O DataJud não traz o texto das decisões, mas traz os movimentos da TPU, que incluem o julgamento
(procedência, improcedência, provimento...). É a fonte do resultado em escala nacional.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, datetime

from dikemetria import politica
from dikemetria.coleta.http import Cliente, Proveniencia
from dikemetria.coleta.tribunais import Tribunal
from dikemetria.recorte import RecorteDataJud
from dikemetria.resultado import classificar_movimentos

log = logging.getLogger(__name__)

URL_BASE = "https://api-publica.datajud.cnj.jus.br"
CHAVE_PUBLICA = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="


def cliente_datajud(intervalo: float = 1.0) -> Cliente:
    chave = os.environ.get("DATAJUD_API_KEY", CHAVE_PUBLICA)
    return Cliente(intervalo=intervalo, cabecalhos={"Authorization": f"APIKey {chave}"})


@dataclass
class Processo:
    tribunal: str
    numero: str
    grau: str | None
    classe_codigo: int | None
    classe_nome: str | None
    assuntos: list[dict] = field(default_factory=list)
    municipio_ibge: int | None = None
    data_ajuizamento: str | None = None  # AAAA-MM-DD
    data_julgamento: str | None = None
    resultado: str = "indeterminado"
    evidencia: str = ""
    nivel_sigilo: int = 0
    sensivel: bool = False

    @property
    def duracao_dias(self) -> int | None:
        if not (self.data_ajuizamento and self.data_julgamento):
            return None
        inicio = date.fromisoformat(self.data_ajuizamento)
        dias = (date.fromisoformat(self.data_julgamento) - inicio).days
        return dias if dias >= 0 else None


def converter_data(valor: str | None) -> str | None:
    """O DataJud mistura '20190528000000', '2019-05-28T00:00:00.000Z' e '2019-05-28'."""
    if not valor:
        return None
    valor = str(valor).strip()
    if valor[:8].isdigit() and (len(valor) == 8 or valor[8:].isdigit()):
        try:
            return datetime.strptime(valor[:8], "%Y%m%d").date().isoformat()
        except ValueError:
            return None
    try:
        return date.fromisoformat(valor[:10]).isoformat()
    except ValueError:
        return None


def montar_consulta(recorte: RecorteDataJud, tamanho: int, apos: list | None = None) -> dict:
    """Consulta Elasticsearch: cada grupo de critérios é um 'OU', e os grupos se somam com 'E'."""
    grupos: list[list[dict]] = []
    if recorte.assuntos_codigos:
        grupos.append([{"match": {"assuntos.codigo": c}} for c in recorte.assuntos_codigos])
    if recorte.assuntos_nomes:
        grupos.append([{"match_phrase": {"assuntos.nome": n}} for n in recorte.assuntos_nomes])
    if recorte.classes_codigos:
        grupos.append([{"match": {"classe.codigo": c}} for c in recorte.classes_codigos])
    if recorte.graus:
        grupos.append([{"match": {"grau": g}} for g in recorte.graus])

    must = [{"bool": {"should": grupo, "minimum_should_match": 1}} for grupo in grupos]
    consulta: dict = {
        "size": tamanho,
        "query": {"bool": {"must": must}} if must else {"match_all": {}},
        "sort": [{"@timestamp": {"order": "asc"}}],
    }
    if apos:
        consulta["search_after"] = apos
    return consulta


def converter_processo(fonte: dict, tribunal: str) -> Processo:
    classe = fonte.get("classe") or {}
    orgao = fonte.get("orgaoJulgador") or {}
    assuntos = []
    for assunto in fonte.get("assuntos") or []:
        # Alguns tribunais aninham listas de assuntos.
        for item in assunto if isinstance(assunto, list) else [assunto]:
            if isinstance(item, dict):
                assuntos.append({"codigo": item.get("codigo"), "nome": item.get("nome")})

    classificacao, data_julgamento = classificar_movimentos(fonte.get("movimentos") or [])
    nomes_assuntos = " ".join(a["nome"] or "" for a in assuntos)
    return Processo(
        tribunal=tribunal,
        numero=str(fonte.get("numeroProcesso", "")),
        grau=fonte.get("grau"),
        classe_codigo=classe.get("codigo"),
        classe_nome=classe.get("nome"),
        assuntos=assuntos,
        municipio_ibge=orgao.get("codigoMunicipioIBGE"),
        data_ajuizamento=converter_data(fonte.get("dataAjuizamento")),
        data_julgamento=converter_data(data_julgamento),
        resultado=classificacao.resultado.value,
        evidencia=classificacao.evidencia,
        nivel_sigilo=int(fonte.get("nivelSigilo") or 0),
        sensivel=politica.materia_sensivel(classe.get("nome"), nomes_assuntos),
    )


def _no_periodo(processo: Processo, recorte: RecorteDataJud) -> bool:
    # O formato de dataAjuizamento varia entre tribunais, então o período é filtrado aqui.
    if not (recorte.ajuizamento_desde or recorte.ajuizamento_ate):
        return True
    if not processo.data_ajuizamento:
        return False
    ajuizamento = date.fromisoformat(processo.data_ajuizamento)
    if recorte.ajuizamento_desde and ajuizamento < recorte.ajuizamento_desde:
        return False
    return not (recorte.ajuizamento_ate and ajuizamento > recorte.ajuizamento_ate)


def contar(cliente: Cliente, tribunal: Tribunal, recorte: RecorteDataJud) -> int:
    """Total de processos que casam com o recorte (antes do filtro de período)."""
    consulta = montar_consulta(recorte, tamanho=0)
    consulta.pop("sort")
    consulta["track_total_hits"] = True
    dados, _ = cliente.requisitar(
        "POST", f"{URL_BASE}/{tribunal.indice_datajud}/_search", json_corpo=consulta
    )
    total = dados.get("hits", {}).get("total", 0)
    return total.get("value", 0) if isinstance(total, dict) else int(total)


def coletar(
    cliente: Cliente,
    tribunal: Tribunal,
    recorte: RecorteDataJud,
    cursor: list | None = None,
) -> Iterator[tuple[list[Processo], list | None, Proveniencia]]:
    """Percorre as páginas de um tribunal.

    Rende (processos da página, cursor para retomar, proveniência). Processos em segredo de
    justiça e fora do período são descartados aqui, antes de chegar ao banco.
    """
    url = f"{URL_BASE}/{tribunal.indice_datajud}/_search"
    vistos = 0
    while True:
        tamanho = recorte.tamanho_pagina
        if recorte.limite_por_tribunal is not None:
            tamanho = min(tamanho, recorte.limite_por_tribunal - vistos)
            if tamanho <= 0:
                return
        dados, proveniencia = cliente.requisitar(
            "POST", url, json_corpo=montar_consulta(recorte, tamanho, cursor)
        )
        hits = dados.get("hits", {}).get("hits", [])
        if not hits:
            return
        vistos += len(hits)
        cursor = hits[-1].get("sort")
        processos = []
        for hit in hits:
            processo = converter_processo(hit.get("_source", {}), tribunal.sigla)
            if processo.nivel_sigilo or not _no_periodo(processo, recorte):
                continue
            processos.append(processo)
        yield processos, cursor, proveniencia
        if len(hits) < tamanho or cursor is None:
            return
