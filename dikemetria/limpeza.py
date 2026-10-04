"""Normalização e tokenização de texto jurídico em português."""

from __future__ import annotations

import html
import re
import unicodedata

# Stopwords do português (lista do NLTK) e ruído processual frequente em decisões.
STOPWORDS = frozenset(
    """
    a à ao aos aquela aquelas aquele aqueles aquilo as às até com como da das de dela delas dele
    deles depois do dos e é ela elas ele eles em entre era eram éramos essa essas esse esses esta
    está estamos estão estas estava estavam estávamos este esteja estejam estejamos estes esteve
    estive estivemos estiver estivera estiveram estivéramos estiverem estivermos estivesse
    estivessem estivéssemos estou eu foi fomos for fora foram fôramos forem formos fosse fossem
    fôssemos fui há haja hajam hajamos hão havemos havia hei houve houvemos houver houvera
    houverá houveram houvéramos houverão houverei houverem houveremos houveria houveriam
    houveríamos houvermos houvesse houvessem houvéssemos isso isto já lhe lhes mais mas me mesmo
    meu meus minha minhas muito na não nas nem no nos nós nossa nossas nosso nossos num numa o os
    ou para pela pelas pelo pelos por qual quando que quem são se seja sejam sejamos sem ser será
    serão serei seremos seria seriam seríamos seu seus só somos sou sua suas também te tem têm
    temos tenha tenham tenhamos tenho terá terão terei teremos teria teriam teríamos teu teus
    teve tinha tinham tínhamos tive tivemos tiver tivera tiveram tivéramos tiverem tivermos
    tivesse tivessem tivéssemos tu tua tuas um uma você vocês vos
    """.split()
)

RUIDO_PROCESSUAL = frozenset(
    """
    fls fl id pág págs art arts nº inc cf sobre acima abaixo sob ainda bem cada sendo inclusive
    quanto portanto seguintes assim conforme referido referida presente presentes autos
    """.split()
)

_PALAVRA = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*")
_TAGS = re.compile(r"<[^>]+>")
_ESPACOS = re.compile(r"[ \t\r\f\v]+")


def normalizar(texto: str) -> str:
    """Unicode NFC, espaços colapsados e quebras de linha preservadas."""
    texto = unicodedata.normalize("NFC", texto)
    texto = texto.replace(" ", " ")
    linhas = (_ESPACOS.sub(" ", linha).strip() for linha in texto.splitlines())
    return "\n".join(linhas)


def sem_acentos(texto: str) -> str:
    decomposto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn")


def tokenizar(texto: str) -> list[str]:
    """Palavras em minúsculas, mantendo acentos e hífens internos (boa-fé)."""
    return _PALAVRA.findall(unicodedata.normalize("NFC", texto).lower())


def tokens_relevantes(texto: str, remover_ruido: bool = True, tamanho_minimo: int = 3) -> list[str]:
    """Tokens sem stopwords, sem ruído processual e com tamanho mínimo."""
    excluir = STOPWORDS | RUIDO_PROCESSUAL if remover_ruido else STOPWORDS
    return [t for t in tokenizar(texto) if len(t) >= tamanho_minimo and t not in excluir]


def html_para_texto(conteudo: str) -> str:
    conteudo = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", conteudo)
    return normalizar(html.unescape(_TAGS.sub(" ", conteudo)))
