"""Divisão de uma decisão em relatório, fundamentação e dispositivo (art. 489 do CPC)."""

from __future__ import annotations

import re
from dataclasses import dataclass

_FIM_RELATORIO = re.compile(
    r"(?im)^\s*(?:é\s+o\s+(?:breve\s+|sucinto\s+)?relat[óo]rio|relatei|relatados?|"
    r"(?:fundamento\s+e\s+)?decido|fundamenta[çc][ãa]o|fundamento|"
    r"dispensado\s+o\s+relat[óo]rio)\b[^\n]*$"
)

_INICIO_DISPOSITIVO = re.compile(
    r"(?im)\b(?:ante\s+(?:todo\s+)?o\s+exposto|diante\s+(?:de\s+todo\s+)?(?:do\s+)?exposto|"
    r"pelo\s+exposto|por\s+todo\s+o\s+exposto|do\s+exposto|em\s+face\s+do\s+exposto|"
    r"isto\s+posto|isso\s+posto|posto\s+isso|face\s+ao\s+exposto|"
    r"diante\s+do\s+quanto\s+exposto|ante\s+o\s+quanto\s+exposto)\b|"
    r"^\s*(?:III?\s*[-–.]\s*)?dispositivo\s*$"
)

_JULGO = re.compile(r"(?i)\b(?:julgo|julgamos|acordam|homologo|extingo|dou|nego|negam|d[ãa]o)\b")


@dataclass(frozen=True)
class Secoes:
    relatorio: str
    fundamentacao: str
    dispositivo: str
    dispositivo_localizado: bool  # False quando caiu na heurística de fallback


def dividir(texto: str) -> Secoes:
    """Separa as três partes da decisão.

    O dispositivo começa no último marcador conclusivo ("Ante o exposto", "Isto posto"...). Sem
    marcador, usa o último "julgo"/"acordam"/"homologo"; sem nada disso, o último quinto do texto.
    """
    inicio_dispositivo = None
    marcadores = list(_INICIO_DISPOSITIVO.finditer(texto))
    if marcadores:
        inicio_dispositivo = marcadores[-1].start()
    else:
        julgamentos = list(_JULGO.finditer(texto))
        if julgamentos:
            inicio_dispositivo = julgamentos[-1].start()

    localizado = inicio_dispositivo is not None
    if inicio_dispositivo is None:
        inicio_dispositivo = int(len(texto) * 0.8)

    antes = texto[:inicio_dispositivo]
    fim_relatorio = _FIM_RELATORIO.search(antes)
    corte = fim_relatorio.end() if fim_relatorio else 0
    return Secoes(
        relatorio=antes[:corte].strip(),
        fundamentacao=antes[corte:].strip(),
        dispositivo=texto[inicio_dispositivo:].strip(),
        dispositivo_localizado=localizado,
    )
