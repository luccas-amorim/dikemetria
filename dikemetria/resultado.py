"""Classificação do resultado de uma decisão.

Duas fontes, que podem ser comparadas entre si:

* o texto do dispositivo (regras sobre "julgo procedente", "nego provimento"...);
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


# Regras sobre texto sem acentos e em minúsculas. A ordem importa: as formas parciais vêm antes.
_REGRAS_TEXTO: list[tuple[Resultado, re.Pattern]] = [
    (
        Resultado.PARCIALMENTE_PROCEDENTE,
        re.compile(
            r"\b(?:parcialmente\s+procedentes?|procedentes?\s+em\s+parte|"
            r"parcial\s+procedencia|acolho\s+(?:em\s+parte|parcialmente))\b"
        ),
    ),
    (
        Resultado.IMPROCEDENTE,
        re.compile(
            r"\b(?:julg\w*\s+(?:totalmente\s+)?improcedentes?|improcedentes?\s+(?:o|os|a|as)\s+"
            r"(?:pedidos?|acao|demanda|pretens\w+)|rejeit\w+\s+(?:o|os)\s+pedidos?)\b"
        ),
    ),
    (
        Resultado.PROCEDENTE,
        re.compile(
            r"\b(?:julg\w*\s+(?:totalmente\s+)?procedentes?|procedentes?\s+(?:o|os|a|as)\s+"
            r"(?:pedidos?|acao|demanda|pretens\w+)|acolh\w+\s+(?:o|os)\s+pedidos?)\b"
        ),
    ),
    (
        Resultado.HOMOLOGACAO_ACORDO,
        re.compile(r"\bhomolog\w*[^.]{0,80}?\b(?:acordo|transacao|composicao)\b"),
    ),
    (
        Resultado.EXTINTO_SEM_MERITO,
        re.compile(
            r"\b(?:sem\s+(?:resolucao|julgamento|exame)\s+d[oe]\s+merito|"
            r"art(?:igo)?\.?\s*485\b|indefiro\s+a\s+peticao\s+inicial)"
        ),
    ),
    (
        Resultado.NAO_CONHECIDO,
        re.compile(r"\bnao\s+(?:conheco|conhecer|conheceram|conhecido)\b"),
    ),
    (
        Resultado.PARCIALMENTE_PROVIDO,
        re.compile(
            r"\b(?:d(?:ou|ar|eram|ao|a-se)\s+parcial\s+provimento|parcialmente\s+provid[oa]s?|"
            r"provid[oa]s?\s+em\s+parte|provimento\s+parcial)\b"
        ),
    ),
    (
        Resultado.NAO_PROVIDO,
        re.compile(
            r"\b(?:neg(?:o|ar|aram|am|a-se)\s+provimento|nao\s+provid[oa]s?|desprovid[oa]s?|"
            r"improvid[oa]s?)\b"
        ),
    ),
    (
        Resultado.PROVIDO,
        re.compile(r"\b(?:d(?:ou|ar|eram|ao|a-se)\s+(?:integral\s+)?provimento|provid[oa]s?)\b"),
    ),
]

# Combinações que, juntas no mesmo dispositivo, não permitem um rótulo único.
_CONFLITOS = [
    {Resultado.PROCEDENTE, Resultado.IMPROCEDENTE},
    {Resultado.PROVIDO, Resultado.NAO_PROVIDO},
]


def classificar_texto(dispositivo: str) -> Classificacao:
    """Classifica pelo texto do dispositivo."""
    texto = sem_acentos(dispositivo.lower())
    achados: dict[Resultado, str] = {}
    for rotulo, padrao in _REGRAS_TEXTO:
        m = padrao.search(texto)
        if m and rotulo not in achados:
            achados[rotulo] = m.group(0)

    # "nao provido" contém "provido"; "parcialmente provido" também. Evita dupla contagem.
    if Resultado.PROVIDO in achados and (
        Resultado.NAO_PROVIDO in achados or Resultado.PARCIALMENTE_PROVIDO in achados
    ):
        trecho = achados[Resultado.PROVIDO]
        if re.fullmatch(r"provid[oa]s?", trecho):
            del achados[Resultado.PROVIDO]

    if not achados:
        return Classificacao(Resultado.INDETERMINADO, "", "texto")

    for parcial in (Resultado.PARCIALMENTE_PROCEDENTE, Resultado.PARCIALMENTE_PROVIDO):
        if parcial in achados:
            return Classificacao(parcial, achados[parcial], "texto")

    for conflito in _CONFLITOS:
        if conflito <= achados.keys():
            evidencia = " | ".join(achados[r] for r in conflito)
            return Classificacao(Resultado.INDETERMINADO, evidencia, "texto")

    rotulo = next(iter(achados))  # a primeira regra que casou, na ordem de prioridade
    return Classificacao(rotulo, achados[rotulo], "texto")


# Nomes de movimentos da TPU (CNJ) sem acentos. Código 219, 220 e 221 = procedência,
# improcedência e procedência em parte; os nomes cobrem variações entre tribunais.
_MOVIMENTOS: list[tuple[Resultado, re.Pattern]] = [
    (Resultado.PARCIALMENTE_PROCEDENTE, re.compile(r"procedencia em parte|procedente em parte")),
    (Resultado.IMPROCEDENTE, re.compile(r"\bimprocedencia\b")),
    (Resultado.PROCEDENTE, re.compile(r"(?<!im)procedencia\b(?! em parte)")),
    (Resultado.HOMOLOGACAO_ACORDO, re.compile(r"homologacao de (?:transacao|acordo)")),
    (
        Resultado.EXTINTO_SEM_MERITO,
        re.compile(
            r"sem resolucao d[oe] merito|desistencia|abandono da causa|"
            r"indeferimento da peticao inicial|ausencia (?:das|de) condic|"
            r"ausencia de pressupostos|perempcao|litispendencia|coisa julgada"
        ),
    ),
    (Resultado.PARCIALMENTE_PROVIDO, re.compile(r"provimento em parte")),
    (Resultado.NAO_PROVIDO, re.compile(r"nao[- ]provimento")),
    (Resultado.PROVIDO, re.compile(r"(?<!nao-)(?<!nao )\bprovimento\b(?! em parte)")),
    (Resultado.NAO_CONHECIDO, re.compile(r"nao[- ]conhecimento")),
]

CODIGOS_TPU = {
    219: Resultado.PROCEDENTE,
    220: Resultado.IMPROCEDENTE,
    221: Resultado.PARCIALMENTE_PROCEDENTE,
}

# Movimentos que nunca são o julgamento do pedido principal, mesmo contendo palavras parecidas.
_IGNORAR_MOVIMENTO = re.compile(
    r"embargos de declaracao|liminar|tutela|antecipacao|justica gratuita|assistencia judiciaria|"
    r"impugnacao ao valor|excecao|incidente|cumprimento de sentenca"
)


def classificar_movimento(codigo: int | None, nome: str | None) -> Resultado | None:
    """Rótulo de um único movimento, ou None se ele não for um julgamento."""
    nome_norm = sem_acentos((nome or "").lower())
    if nome_norm and _IGNORAR_MOVIMENTO.search(nome_norm):
        return None
    if codigo in CODIGOS_TPU:
        return CODIGOS_TPU[codigo]
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
