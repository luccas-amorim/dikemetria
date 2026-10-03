"""Ingestão de decisões guardadas em arquivos locais (PDF, DOCX, TXT, HTML)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from dikemetria import referencias
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
        numeros = referencias.numeros_cnj(texto)
        item = {
            "id": hashlib.sha256(conteudo).hexdigest()[:32],
            "texto": texto,
            "numero_processo": numeros[0] if numeros else None,
        }
        tribunal = tribunal_por_cnj(numeros[0]) if numeros else None
        documento = converter_documento(item, tribunal, fonte="arquivo")
        if documento is None:
            yield None, arquivo, "segredo de justiça ou texto vazio"
            continue
        proveniencia = Proveniencia(
            url=arquivo.resolve().as_uri(),
            metodo="arquivo",
            parametros=json.dumps({"nome": arquivo.name}, ensure_ascii=False),
            coletado_em=datetime.now(UTC).isoformat(timespec="seconds"),
            sha256=hashlib.sha256(conteudo).hexdigest(),
        )
        yield documento, arquivo, proveniencia
