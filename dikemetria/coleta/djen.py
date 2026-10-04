"""Diário de Justiça Eletrônico Nacional (DJEN, Comunica PJe): texto das decisões publicadas.

O DJEN reúne as comunicações processuais de todos os tribunais (Resolução CNJ 455/2022). Cada
comunicação traz o texto do ato (sentença, acórdão, decisão, despacho) e os destinatários.

Os nomes dos destinatários servem só para pseudonimizar o texto com precisão: são usados e
descartados, nunca gravados. O texto original também não é gravado, só a versão pseudonimizada e
o hash do original.

Os nomes dos campos seguem a API pública em https://comunicaapi.pje.jus.br. Antes de uma coleta
grande, rode `dikemetria sondar --fonte djen` para conferir se a API não mudou.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, timedelta

from dikemetria import politica, referencias
from dikemetria.avaliacao import avaliar
from dikemetria.coleta.http import Cliente, Proveniencia
from dikemetria.coleta.tribunais import Tribunal
from dikemetria.limpeza import html_para_texto, sem_acentos
from dikemetria.pseudonimizacao import pseudonimizar
from dikemetria.recorte import RecorteDJEN
from dikemetria.valores import calcular

log = logging.getLogger(__name__)

URL = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"


@dataclass
class Documento:
    id: str
    fonte: str
    tribunal: str
    numero: str | None
    tipo: str | None
    data: str | None
    classe_nome: str | None
    texto: str  # já pseudonimizado
    sha256_original: str
    resultado: str = "indeterminado"
    evidencia: str = ""
    sensivel: bool = False
    substituicoes: dict = field(default_factory=dict)
    url: str | None = None
    avaliacao: dict = field(default_factory=dict)  # capítulos, motivo, confiança e cálculo


def _primeiro(item: dict, *chaves: str):
    for chave in chaves:
        valor = item.get(chave)
        if valor not in (None, ""):
            return valor
    return None


def nomes_destinatarios(item: dict) -> list[str]:
    nomes = [d.get("nome") for d in item.get("destinatarios") or [] if isinstance(d, dict)]
    for adv in item.get("destinatarioadvogados") or []:
        if isinstance(adv, dict):
            nomes.append((adv.get("advogado") or {}).get("nome") or adv.get("nome"))
    return [n for n in nomes if n]


def converter_documento(item: dict, tribunal: str, fonte: str = "djen") -> Documento | None:
    """Pseudonimiza e classifica uma comunicação. None se for segredo de justiça ou vazia."""
    bruto = _primeiro(item, "texto", "conteudo") or ""
    texto = html_para_texto(bruto) if "<" in bruto else bruto
    if not texto.strip() or politica.em_segredo(texto=texto):
        return None

    numero = _primeiro(item, "numeroprocessocommascara", "numero_processo", "numeroProcesso")
    if numero:
        encontrados = referencias.numeros_cnj(str(numero))
        numero = encontrados[0] if encontrados else str(numero)

    pseudo = pseudonimizar(texto, nomes_conhecidos=nomes_destinatarios(item))
    avaliacao, dispositivo = avaliar(pseudo.texto)
    classe = _primeiro(item, "nomeClasse", "classe")
    return Documento(
        id=f"{fonte}:{_primeiro(item, 'id', 'hash') or hashlib.sha256(bruto.encode()).hexdigest()}",
        fonte=fonte,
        tribunal=tribunal,
        numero=numero,
        tipo=_primeiro(item, "tipoDocumento", "tipoComunicacao"),
        data=str(_primeiro(item, "data_disponibilizacao", "datadisponibilizacao") or "")[:10]
        or None,
        classe_nome=classe,
        texto=pseudo.texto,
        sha256_original=hashlib.sha256(bruto.encode("utf-8")).hexdigest(),
        resultado=avaliacao.resultado.value,
        evidencia=avaliacao.evidencia,
        sensivel=politica.materia_sensivel(classe, texto[:5000]),
        substituicoes=dict(pseudo.substituicoes),
        url=_primeiro(item, "link"),
        avaliacao={**avaliacao.como_dict(), "calculo": calcular(dispositivo).como_dict()},
    )


def _tipo_aceito(item: dict, tipos: list[str]) -> bool:
    if not tipos:
        return True
    tipo = sem_acentos(str(_primeiro(item, "tipoDocumento", "tipoComunicacao") or "").lower())
    return any(sem_acentos(t.lower()) in tipo for t in tipos)


def coletar(
    cliente: Cliente,
    tribunal: Tribunal,
    recorte: RecorteDJEN,
    retomar_em: date | None = None,
) -> Iterator[tuple[list[Documento], date, Proveniencia]]:
    """Percorre o período dia a dia, página a página.

    Rende (documentos, dia concluído ou em andamento, proveniência). Um dia por vez mantém as
    páginas curtas e permite retomar a coleta do ponto em que parou.
    """
    inicio = retomar_em or recorte.data_inicio or date.today() - timedelta(days=1)
    fim = recorte.data_fim or inicio
    vistos = 0
    dia = inicio
    while dia <= fim:
        pagina = 1
        while True:
            params = {
                "siglaTribunal": tribunal.sigla_djen,
                "dataDisponibilizacaoInicio": dia.isoformat(),
                "dataDisponibilizacaoFim": dia.isoformat(),
                "pagina": pagina,
                "itensPorPagina": recorte.itens_por_pagina,
            }
            if recorte.texto:
                params["texto"] = recorte.texto
            dados, proveniencia = cliente.requisitar("GET", URL, params=params)
            itens = dados.get("items") or dados.get("itens") or []
            documentos = []
            for item in itens:
                if not _tipo_aceito(item, recorte.tipos_documento):
                    continue
                documento = converter_documento(item, tribunal.sigla)
                if documento:
                    documentos.append(documento)
            vistos += len(documentos)
            yield documentos, dia, proveniencia
            if recorte.limite_por_tribunal is not None and vistos >= recorte.limite_por_tribunal:
                return
            if len(itens) < recorte.itens_por_pagina:
                break
            pagina += 1
        dia += timedelta(days=1)
