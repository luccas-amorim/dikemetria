"""Análise de uma decisão isolada."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, field

from dikemetria import estrutura, referencias, resultado
from dikemetria.limpeza import normalizar, sem_acentos, tokens_relevantes

TERMOS_JURIDICOS = (
    "boa-fé",
    "má-fé",
    "litigância de má-fé",
    "ônus da prova",
    "inversão do ônus da prova",
    "dano moral",
    "danos morais",
    "dano material",
    "danos materiais",
    "lucros cessantes",
    "repetição do indébito",
    "em dobro",
    "inexigibilidade",
    "inexistência de débito",
    "nulidade",
    "prescrição",
    "decadência",
    "responsabilidade objetiva",
    "nexo causal",
    "falha na prestação do serviço",
    "fortuito interno",
    "culpa exclusiva",
    "cadastro de inadimplentes",
    "negativação",
    "inscrição indevida",
    "mero aborrecimento",
    "enriquecimento sem causa",
    "razoabilidade",
    "proporcionalidade",
    "tutela de urgência",
    "justiça gratuita",
    "revelia",
    "ilegitimidade",
    "cerceamento de defesa",
    "coisa julgada",
    "honorários advocatícios",
    "sucumbência",
    "jurisprudência",
    "precedente",
)

MARCADORES_ARGUMENTATIVOS = (
    "considerando que",
    "diante disso",
    "isso porque",
    "dessa forma",
    "desse modo",
    "assim sendo",
    "por conseguinte",
    "com efeito",
    "nesse sentido",
    "nos termos do art",
    "com base no art",
    "restou comprovad",
    "não restou comprovad",
    "restou demonstrad",
    "não restou demonstrad",
    "não se desincumbiu",
    "cabia ao",
    "incumbia ao",
    "é cediço",
    "é pacífico",
    "conforme entendimento",
)

_FIM_DE_FRASE = re.compile(r"(?<=[.!?;])\s+(?=[A-ZÀ-Ý\"“(])")


@dataclass
class AnaliseDocumento:
    numeros_processo: list[str]
    resultado: str
    evidencia_resultado: str
    dispositivo_localizado: bool
    tamanho: dict[str, int]
    citacoes: dict[str, int]
    termos_juridicos: dict[str, int]
    argumentos: list[str]
    palavras_frequentes: list[tuple[str, int]] = field(default_factory=list)

    def como_dict(self) -> dict:
        return asdict(self)


def frases(texto: str) -> list[str]:
    texto = re.sub(r"\s*\n\s*", " ", texto)
    return [f.strip() for f in _FIM_DE_FRASE.split(texto) if f.strip()]


def contar_termos(texto: str, termos=TERMOS_JURIDICOS) -> dict[str, int]:
    """Ocorrências de cada termo (com várias palavras ou hífen), sem distinguir acentos."""
    base = sem_acentos(texto.lower())
    contagem = {}
    for termo in termos:
        padrao = r"(?<!\w)" + re.escape(sem_acentos(termo)).replace(r"\ ", r"\s+") + r"(?!\w)"
        n = len(re.findall(padrao, base))
        if n:
            contagem[termo] = n
    return dict(sorted(contagem.items(), key=lambda par: -par[1]))


def argumentos(texto: str, marcadores=MARCADORES_ARGUMENTATIVOS, limite: int = 30) -> list[str]:
    """Frases da fundamentação que contêm marcadores argumentativos."""
    alvos = [sem_acentos(m) for m in marcadores]
    achadas = [f for f in frases(texto) if any(a in sem_acentos(f.lower()) for a in alvos)]
    return achadas[:limite]


def analisar_documento(texto: str, top: int = 20) -> AnaliseDocumento:
    texto = normalizar(texto)
    secoes = estrutura.dividir(texto)
    classificacao = resultado.classificar_texto(secoes.dispositivo)
    return AnaliseDocumento(
        numeros_processo=referencias.numeros_cnj(texto),
        resultado=classificacao.resultado.value,
        evidencia_resultado=classificacao.evidencia,
        dispositivo_localizado=secoes.dispositivo_localizado,
        tamanho={
            "caracteres": len(texto),
            "relatorio": len(secoes.relatorio),
            "fundamentacao": len(secoes.fundamentacao),
            "dispositivo": len(secoes.dispositivo),
        },
        citacoes=dict(referencias.contar_citacoes(texto).most_common()),
        termos_juridicos=contar_termos(texto),
        argumentos=argumentos(secoes.fundamentacao or texto),
        palavras_frequentes=Counter(tokens_relevantes(texto)).most_common(top),
    )
