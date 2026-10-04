"""Classificação do resultado de uma decisão.

Duas fontes, que podem ser comparadas entre si:

* o texto do dispositivo (regras em dikemetria/avaliacao.py);
* os movimentos processuais do DataJud, nomeados pela Tabela Processual Unificada do CNJ.

Os rótulos descrevem o que o juízo decidiu sobre o pedido ou recurso. Não dizem quem "ganhou":
procedência é favorável ao autor e desfavorável ao réu.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from dikemetria.limpeza import sem_acentos


class Resultado(StrEnum):
    PROCEDENTE = "procedente"
    PARCIALMENTE_PROCEDENTE = "parcialmente_procedente"
    IMPROCEDENTE = "improcedente"
    EXTINTO_SEM_MERITO = "extinto_sem_merito"
    HOMOLOGACAO_ACORDO = "homologacao_acordo"
    PROVIDO = "provido"
    PARCIALMENTE_PROVIDO = "parcialmente_provido"
    NAO_PROVIDO = "nao_provido"
    NAO_CONHECIDO = "nao_conhecido"
    INDETERMINADO = "indeterminado"


MERITO_PRIMEIRO_GRAU = (
    Resultado.PROCEDENTE,
    Resultado.PARCIALMENTE_PROCEDENTE,
    Resultado.IMPROCEDENTE,
)
MERITO_RECURSAL = (Resultado.PROVIDO, Resultado.PARCIALMENTE_PROVIDO, Resultado.NAO_PROVIDO)


@dataclass(frozen=True)
class Classificacao:
    resultado: Resultado
    evidencia: str  # trecho ou movimento que sustentou a decisão
    fonte: str  # "texto" ou "movimentos"


def classificar_texto(dispositivo: str) -> Classificacao:
    """Resultado principal do dispositivo. Para capítulos, motivo e confiança, use
    `dikemetria.avaliacao.avaliar_dispositivo`."""
    from dikemetria.avaliacao import avaliar_dispositivo

    avaliacao = avaliar_dispositivo(dispositivo)
    return Classificacao(avaliacao.resultado, avaliacao.evidencia, "texto")


# Nomes de movimentos da TPU (CNJ) sem acentos. Código 219, 220 e 221 = procedência,
# improcedência e procedência em parte; os nomes cobrem variações entre tribunais.
_MOVIMENTOS: list[tuple[Resultado, re.Pattern]] = [
    (
        Resultado.PARCIALMENTE_PROCEDENTE,
        re.compile(r"procedencia (?:em parte|parcial)|procedente em parte|parcial procedencia"),
    ),
    (
        Resultado.IMPROCEDENTE,
        re.compile(r"\bprescricao\b|\bdecadencia\b|renuncia a pretensao|renuncia ao direito"),
    ),
    (Resultado.IMPROCEDENTE, re.compile(r"\bimprocedencia\b|\bimprocedente\b|nao[- ]procedencia")),
    (Resultado.PROCEDENTE, re.compile(r"(?<!im)procedencia\b(?! em parte)|(?<!im)procedente\b")),
    (Resultado.HOMOLOGACAO_ACORDO, re.compile(r"homologacao de (?:transacao|acordo)")),
    (
        Resultado.EXTINTO_SEM_MERITO,
        re.compile(
            r"sem resolucao d[oe] merito|desistencia|abandono da causa|"
            r"indeferimento da peticao inicial|ausencia (?:das|de) condic|"
            r"ausencia de pressupostos|perempcao|litispendencia|coisa julgada|"
            r"ausencia do autor a audiencia|inadmissibilidade do procedimento sumarissimo|"
            r"ausencia do reclamante|ausencia de citacao de sucessores|"
            r"ausencia de requerimento administrativo"
        ),
    ),
    # Recursos: "conhecimento para negar provimento", "dar parcial provimento"...
    (Resultado.NAO_CONHECIDO, re.compile(r"nao[- ]conhecimento|nao conhecer")),
    (
        Resultado.PARCIALMENTE_PROVIDO,
        re.compile(r"provimento em parte|parcial provimento|provimento parcial"),
    ),
    (
        Resultado.NAO_PROVIDO,
        re.compile(r"nao[- ]provimento|desprovimento|neg(?:ar|ou|o|ado) provimento"),
    ),
    (Resultado.PROVIDO, re.compile(r"(?<!nao-)(?<!nao )\bprovimento\b(?! em parte)")),
]

# Códigos lidos pelo número, conferidos com a hierarquia e o texto oficial da TPU (SGT/CNJ,
# versão de 12/09/2026). Valem quando o nome que o tribunal manda ao DataJud é genérico
# ("Segurança", "Arquivamento", "Negação de Seguimento") ou enganoso.
CODIGOS_TPU = {
    219: Resultado.PROCEDENTE,
    220: Resultado.IMPROCEDENTE,
    221: Resultado.PARCIALMENTE_PROCEDENTE,
    # Writs: concedida (210), denegada (212) e concedida em parte (214) a segurança, o habeas
    # corpus e o habeas data.
    442: Resultado.PROCEDENTE,
    443: Resultado.PROCEDENTE,
    444: Resultado.PROCEDENTE,
    446: Resultado.IMPROCEDENTE,
    447: Resultado.IMPROCEDENTE,
    448: Resultado.IMPROCEDENTE,
    450: Resultado.PARCIALMENTE_PROCEDENTE,
    451: Resultado.PARCIALMENTE_PROCEDENTE,
    # Recursos: sentença confirmada, confirmada em parte, desconstituída ou anulada; provimento
    # negado monocraticamente; seguimento negado; recurso prejudicado.
    12252: Resultado.NAO_PROVIDO,
    12253: Resultado.PARCIALMENTE_PROVIDO,
    12254: Resultado.PROVIDO,
    11373: Resultado.PROVIDO,
    901: Resultado.NAO_PROVIDO,
    236: Resultado.NAO_CONHECIDO,
    230: Resultado.NAO_CONHECIDO,
    # Extinção sem resolução do mérito: no JEC (Lei 9.099, art. 51: ausência do autor,
    # inadmissibilidade do rito, incompetência territorial ou em razão da pessoa, falecimento do
    # autor); negligência das partes, arbitragem, ação intransmissível, confusão, continência,
    # perda do objeto, ação prejudicada; arquivamento trabalhista (CLT, arts. 844 e 852-B); e na
    # execução (cancelamento da dívida ativa, devedor não encontrado, falta de bens penhoráveis).
    11376: Resultado.EXTINTO_SEM_MERITO,
    11377: Resultado.EXTINTO_SEM_MERITO,
    11378: Resultado.EXTINTO_SEM_MERITO,
    11379: Resultado.EXTINTO_SEM_MERITO,
    11380: Resultado.EXTINTO_SEM_MERITO,
    456: Resultado.EXTINTO_SEM_MERITO,
    457: Resultado.EXTINTO_SEM_MERITO,
    462: Resultado.EXTINTO_SEM_MERITO,
    464: Resultado.EXTINTO_SEM_MERITO,
    465: Resultado.EXTINTO_SEM_MERITO,
    12256: Resultado.EXTINTO_SEM_MERITO,
    12325: Resultado.EXTINTO_SEM_MERITO,
    12459: Resultado.EXTINTO_SEM_MERITO,
    228: Resultado.EXTINTO_SEM_MERITO,
    472: Resultado.EXTINTO_SEM_MERITO,
    12298: Resultado.EXTINTO_SEM_MERITO,
    11374: Resultado.EXTINTO_SEM_MERITO,
    11375: Resultado.EXTINTO_SEM_MERITO,
}

# Julgamento da impugnação à execução (12450): incidente do cumprimento, não o pedido.
CODIGOS_IGNORADOS = {12451, 12452, 12453}

# Movimentos que nunca são o julgamento do pedido principal, mesmo contendo palavras parecidas.
_IGNORAR_MOVIMENTO = re.compile(
    r"embargos de declaracao|liminar|tutela|antecipacao|justica gratuita|assistencia judiciaria|"
    r"impugnacao ao valor|excecao|incidente|cumprimento de sentenca"
)


def classificar_movimento(codigo: int | None, nome: str | None) -> Resultado | None:
    """Rótulo de um único movimento, ou None se ele não for um julgamento."""
    nome_norm = sem_acentos((nome or "").lower())
    if codigo in CODIGOS_IGNORADOS or (nome_norm and _IGNORAR_MOVIMENTO.search(nome_norm)):
        return None
    if codigo in CODIGOS_TPU:
        return CODIGOS_TPU[codigo]
    # "Procedência do pedido e improcedência do pedido contraposto": só o pedido do autor conta.
    nome_norm = re.split(r"\s+e\s+(?=\S+(?: em parte)? do pedido contraposto)", nome_norm)[0]
    for rotulo, padrao in _MOVIMENTOS:
        if padrao.search(nome_norm):
            return rotulo
    return None


def classificar_movimentos(movimentos: list[dict]) -> tuple[Classificacao, str | None]:
    """Primeiro julgamento em ordem cronológica e a data dele.

    Cada movimento é um dict com "codigo", "nome" e "dataHora" (formato do DataJud). O primeiro
    julgamento é a sentença ou o acórdão; os seguintes costumam ser embargos ou incidentes.
    """
    ordenados = sorted(movimentos, key=lambda mov: mov.get("dataHora") or "")
    for mov in ordenados:
        rotulo = classificar_movimento(mov.get("codigo"), mov.get("nome"))
        if rotulo is not None:
            evidencia = f"{mov.get('codigo')} {mov.get('nome')}".strip()
            return Classificacao(rotulo, evidencia, "movimentos"), mov.get("dataHora")
    return Classificacao(Resultado.INDETERMINADO, "", "movimentos"), None
