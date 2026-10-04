"""Ingestão de decisões guardadas em arquivos locais (PDF, DOCX, TXT, HTML).

Autos completos do eproc são reconhecidos e reduzidos às decisões que julgam o pedido ou o
recurso (`autos.py`); petições e anexos não entram no corpus.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from dikemetria import autos, referencias
from dikemetria.coleta.djen import Documento, converter_documento
from dikemetria.coleta.http import Proveniencia
from dikemetria.coleta.tribunais import tribunal_por_cnj
from dikemetria.extracao import ErroExtracao, extrair_texto

EXTENSOES = {".pdf", ".docx", ".txt", ".html", ".htm"}


def coletar(pasta: str | Path) -> Iterator[tuple[Documento | None, Path, Proveniencia | str]]:
    """Rende (documento, arquivo, proveniência) ou (None, arquivo, motivo) quando falha."""
    for arquivo in sorted(Path(pasta).rglob("*")):
        if arquivo.suffix.lower() not in EXTENSOES or not arquivo.is_file():
            continue
        try:
            texto = extrair_texto(arquivo)
        except ErroExtracao as erro:
            yield None, arquivo, str(erro)
            continue
        conteudo = arquivo.read_bytes()
        hash_arquivo = hashlib.sha256(conteudo).hexdigest()
        numeros = referencias.numeros_cnj(texto)
        tribunal = tribunal_por_cnj(numeros[0]) if numeros else None
        proveniencia = Proveniencia(
            url=arquivo.resolve().as_uri(),
            metodo="arquivo",
            parametros=json.dumps({"nome": arquivo.name}, ensure_ascii=False),
            coletado_em=datetime.now(UTC).isoformat(timespec="seconds"),
            sha256=hash_arquivo,
        )
        if autos.eh_autos_eproc(texto):
            # Autos completos: só sentenças, acórdãos e decisões monocráticas; o resto é descartado.
            finais = autos.decisoes_finais(texto)
            if not finais:
                yield None, arquivo, "autos sem sentença nem acórdão"
            for peca in finais:
                item = {
                    "id": f"{hash_arquivo[:24]}-e{peca.evento}{peca.sigla}{peca.ordem}",
                    "texto": peca.texto,
                    "numero_processo": numeros[0] if numeros else None,
                    "tipoDocumento": peca.nome,
                    "data_disponibilizacao": peca.data,
                }
                documento = converter_documento(item, tribunal, fonte="arquivo")
                if documento is None:
                    yield None, arquivo, f"evento {peca.evento}: segredo de justiça ou texto vazio"
                else:
                    yield documento, arquivo, proveniencia
            continue
        item = {
            "id": hash_arquivo[:32],
            "texto": texto,
            "numero_processo": numeros[0] if numeros else None,
        }
        documento = converter_documento(item, tribunal, fonte="arquivo")
        if documento is None:
            yield None, arquivo, "segredo de justiça ou texto vazio"
            continue
        yield documento, arquivo, proveniencia
