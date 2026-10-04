"""Autos completos: separa as peças e devolve só o que interessa à pesquisa.

O PDF de "autos completos" traz no mesmo arquivo a inicial, procurações, documentos pessoais,
atas societárias, contestação, decisões e sentença. Ler o arquivo inteiro como uma decisão erra
o resultado (vale o último "Ante o exposto" dos autos, que pode ser de um despacho) e expõe
dados de terceiros que a pseudonimização por regras não alcança.

Formato reconhecido: eproc (TJSP, TRFs, TJSC, TJRS...), em que cada página traz
"Processo 0000000-00.0000.0.00.0000/UF, Evento 48, SENT1, Página 1" e cada evento tem uma página
de separação com descrição e data. As peças são classificadas pelo tipo do eproc:

- decisão: sentença, acórdão, voto, decisões e despachos;
- parte: inicial, contestação, réplica, petições e recursos;
- anexo: procurações, documentos pessoais, comprovantes e o resto, descartados por padrão.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_MARCADOR = re.compile(
    r"Processo\s+[\d.\-]+/[A-Z]{2},\s*Evento\s+(\d+),\s*([A-Z]+)(\d*),\s*P[áa]gina\s+(\d+)"
)
_EVENTO = re.compile(
    r"Evento:\s*\n\s*(?P<descricao>[^\n]+(?:\n(?!\s*Data:)[^\n]+)?)\s*\n\s*Data:\s*\n\s*"
    r"(?P<data>\d{2}/\d{2}/\d{4})(?:.*?Sequ[êe]ncia Evento:\s*\n\s*(?P<numero>\d+))?",
    re.DOTALL,
)

# Tipos do eproc (sigla sem o número de ordem).
DECISOES = {
    "SENT": "sentença",
    "ACOR": "acórdão",
    "VOTO": "voto",
    "RELVOTO": "relatório e voto",
    "EMENTA": "ementa",
    "DECMONO": "decisão monocrática",
    "DESPADEC": "despacho/decisão",
    "DECIS": "decisão",
    "DESPAOFC": "despacho/ofício",
    "DESP": "despacho",
}
PARTES = {
    "INIC": "petição inicial",
    "EMENDAINIC": "emenda à inicial",
    "CONTES": "contestação",
    "REPLICA": "réplica",
    "PET": "petição",
    "APELACAO": "apelação",
    "CONTRAZ": "contrarrazões",
    "CONTRAZAP": "contrarrazões",
    "RECURSO": "recurso",
    "AGRAVO": "agravo",
    "EMBDECL": "embargos de declaração",
    "ALEGACOES": "alegações finais",
    "MEMORIAIS": "memoriais",
    "IMPUGNACAO": "impugnação",
    "RECONV": "reconvenção",
}
# Decisões que julgam o pedido ou o recurso: as únicas que entram no corpus como decisão.
DECISOES_FINAIS = {"SENT", "ACOR", "DECMONO"}


@dataclass
class Peca:
    evento: int
    sigla: str  # tipo do eproc, sem o número de ordem ("SENT")
    ordem: str  # número de ordem no evento ("1" em "SENT1")
    paginas: int
    texto: str
    data: str | None = None  # AAAA-MM-DD, da página de separação do evento
    descricao_evento: str | None = None

    @property
    def classe(self) -> str:
        if self.sigla in DECISOES:
            return "decisão"
        if self.sigla in PARTES:
            return "parte"
        return "anexo"

    @property
    def nome(self) -> str:
        return DECISOES.get(self.sigla) or PARTES.get(self.sigla) or self.sigla.lower()


def eh_autos_eproc(texto: str) -> bool:
    """Verdadeiro se o texto tem marcadores de página do eproc de mais de uma peça."""
    pecas = {(m.group(1), m.group(2), m.group(3)) for m in _MARCADOR.finditer(texto)}
    return len(pecas) >= 2


def _data_iso(data: str) -> str:
    dia, mes, ano = data.split("/")
    return f"{ano}-{mes}-{dia}"


def _paginas(texto: str) -> list[str]:
    if "\f" in texto:
        return texto.split("\f")
    # Sem quebras de página (texto já colado): cada marcador abre uma página.
    inicios = [m.start() for m in _MARCADOR.finditer(texto)]
    if not inicios:
        return [texto]
    limites = [0, *inicios, len(texto)]
    return [texto[a:b] for a, b in zip(limites, limites[1:], strict=False)]


def dividir(texto: str) -> list[Peca]:
    """Peças dos autos, na ordem em que aparecem. Lista vazia se o formato não for reconhecido."""
    pecas: dict[tuple[int, str, str], Peca] = {}
    eventos: dict[int, tuple[str, str]] = {}
    for pagina in _paginas(texto):
        # A página de separação (descrição e data do evento) nunca faz parte de uma peça.
        corpo, _, separacao = pagina.partition("PÁGINA DE SEPARAÇÃO")
        if not _MARCADOR.search(corpo):
            corpo, separacao = "", pagina
        for m in _EVENTO.finditer(separacao):
            if m.group("numero"):
                descricao = " ".join(m.group("descricao").split())
                eventos[int(m.group("numero"))] = (descricao, _data_iso(m.group("data")))
        marcador = _MARCADOR.search(corpo)
        if marcador is None:
            continue
        evento, sigla, ordem = int(marcador.group(1)), marcador.group(2), marcador.group(3)
        corpo = _MARCADOR.sub("", corpo).strip()
        chave = (evento, sigla, ordem)
        if chave not in pecas:
            pecas[chave] = Peca(evento, sigla, ordem, 0, "")
        peca = pecas[chave]
        peca.paginas += 1
        peca.texto = f"{peca.texto}\n{corpo}".strip()
    for peca in pecas.values():
        if peca.evento in eventos:
            peca.descricao_evento, peca.data = eventos[peca.evento]
    return list(pecas.values())


def decisoes_finais(texto: str) -> list[Peca]:
    """Sentenças, acórdãos e decisões monocráticas dos autos, em ordem de evento."""
    return [p for p in dividir(texto) if p.sigla in DECISOES_FINAIS]
