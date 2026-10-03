"""Medidas agregadas sobre o corpus (Fase 4).

Tudo aqui é descritivo: como os tribunais decidiram, não qual a chance de uma ação concreta.
Grupos com menos de `politica.MINIMO_PUBLICAVEL` casos são suprimidos das tabelas.
Não há agregação por órgão julgador ou magistrado (regra 5 do README).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Iterable

from dikemetria import estatistica, politica, referencias
from dikemetria.coleta.tribunais import TRIBUNAIS
from dikemetria.estrutura import dividir
from dikemetria.limpeza import tokens_relevantes
from dikemetria.resultado import Resultado

R = Resultado
RAMO_POR_TRIBUNAL = {t.sigla: t.ramo for t in TRIBUNAIS}

# Marcadores da pseudonimização e palavras que só refletem o próprio resultado.
_EXCLUIR_VOCABULARIO = frozenset(
    """
    pessoa cpf cnpj rg oab cep telefone email endereco conta procedente procedentes
    improcedente improcedentes procedência improcedência parcialmente julgo provimento
    poder judiciário tribunal justiça estado sentença vistos processo comarca vara foro
    """.split()
)

AGRUPAMENTOS: dict[str, Callable[[dict], Iterable[str]]] = {
    "ramo": lambda r: [RAMO_POR_TRIBUNAL.get(r.get("tribunal") or "", "desconhecido")],
    "tribunal": lambda r: [(r.get("tribunal") or "desconhecido").upper()],
    "grau": lambda r: [r.get("grau") or "não informado"],
    "ano": lambda r: [(r.get("data_julgamento") or r.get("data") or "")[:4] or "sem data"],
    "classe": lambda r: [r.get("classe_nome") or "não informada"],
    "assunto": lambda r: (
        [a["nome"] for a in r.get("assuntos") or [] if a.get("nome")] or ["não informado"]
    ),
}


def distribuicao(registros: Iterable[dict]) -> list[dict]:
    contagem = Counter(r["resultado"] for r in registros)
    total = sum(contagem.values())
    return [
        {"resultado": rotulo, "n": n, "proporcao": n / total}
        for rotulo, n in contagem.most_common()
    ]


def taxas(registros: Iterable[dict], agrupamento: str, minimo: int | None = None) -> list[dict]:
    """Taxas de procedência (1º grau) e de provimento (recursos) por grupo, com IC de Wilson.

    * procedência total = procedentes / decisões de mérito;
    * acolhimento = (procedentes + parcialmente procedentes) / decisões de mérito;
    * provimento = (providos + parcialmente providos) / recursos julgados no mérito.
    """
    minimo = politica.MINIMO_PUBLICAVEL if minimo is None else minimo
    chave = AGRUPAMENTOS[agrupamento]
    contagens: dict[str, Counter] = defaultdict(Counter)
    for registro in registros:
        for grupo in chave(registro):
            contagens[grupo][registro["resultado"]] += 1

    linhas = []
    for grupo, c in contagens.items():
        merito = (
            c[R.PROCEDENTE.value] + c[R.PARCIALMENTE_PROCEDENTE.value] + c[R.IMPROCEDENTE.value]
        )
        recursos = c[R.PROVIDO.value] + c[R.PARCIALMENTE_PROVIDO.value] + c[R.NAO_PROVIDO.value]
        linha = {"grupo": grupo, "total": sum(c.values()), "merito": merito, "recursos": recursos}
        if merito >= minimo:
            p, lo, hi = estatistica.wilson(c[R.PROCEDENTE.value], merito)
            linha |= {"procedencia": p, "procedencia_ic_inf": lo, "procedencia_ic_sup": hi}
            acolhidos = c[R.PROCEDENTE.value] + c[R.PARCIALMENTE_PROCEDENTE.value]
            p, lo, hi = estatistica.wilson(acolhidos, merito)
            linha |= {"acolhimento": p, "acolhimento_ic_inf": lo, "acolhimento_ic_sup": hi}
        if recursos >= minimo:
            providos = c[R.PROVIDO.value] + c[R.PARCIALMENTE_PROVIDO.value]
            p, lo, hi = estatistica.wilson(providos, recursos)
            linha |= {"provimento": p, "provimento_ic_inf": lo, "provimento_ic_sup": hi}
        if merito >= minimo or recursos >= minimo:
            linhas.append(linha)
    return sorted(linhas, key=lambda linha: -linha["total"])


def duracoes(processos: Iterable[dict], agrupamento: str, minimo: int | None = None) -> list[dict]:
    """Dias entre o ajuizamento e o primeiro julgamento: mediana e quartis."""
    minimo = politica.MINIMO_PUBLICAVEL if minimo is None else minimo
    chave = AGRUPAMENTOS[agrupamento]
    por_grupo: dict[str, list[int]] = defaultdict(list)
    for p in processos:
        if p.get("duracao_dias") is not None:
            for grupo in chave(p):
                por_grupo[grupo].append(p["duracao_dias"])
    linhas = [
        {
            "grupo": grupo,
            "n": len(dias),
            "mediana_dias": estatistica.mediana(dias),
            "q1_dias": estatistica.quantil(dias, 0.25),
            "q3_dias": estatistica.quantil(dias, 0.75),
        }
        for grupo, dias in por_grupo.items()
        if len(dias) >= minimo
    ]
    return sorted(linhas, key=lambda linha: -linha["n"])


def _lado(resultado: str) -> str | None:
    if resultado in (R.PROCEDENTE.value, R.PARCIALMENTE_PROCEDENTE.value):
        return "acolhido"
    if resultado == R.IMPROCEDENTE.value:
        return "rejeitado"
    if resultado in (R.PROVIDO.value, R.PARCIALMENTE_PROVIDO.value):
        return "acolhido"
    if resultado == R.NAO_PROVIDO.value:
        return "rejeitado"
    return None


def citacoes_por_resultado(
    documentos: Iterable[dict], top: int = 30, minimo: int | None = None
) -> list[dict]:
    """Em que proporção dos documentos acolhidos e rejeitados cada norma é citada."""
    minimo = politica.MINIMO_PUBLICAVEL if minimo is None else minimo
    totais: Counter = Counter()
    citam: dict[str, Counter] = defaultdict(Counter)
    for doc in documentos:
        lado = _lado(doc["resultado"])
        if not lado:
            continue
        totais[lado] += 1
        for ref in set(referencias.contar_citacoes(doc["texto"])):
            citam[ref][lado] += 1

    linhas = []
    for ref, c in citam.items():
        if sum(c.values()) < minimo:
            continue
        linhas.append(
            {
                "citacao": ref,
                "documentos": sum(c.values()),
                "em_acolhidos": c["acolhido"] / totais["acolhido"] if totais["acolhido"] else None,
                "em_rejeitados": c["rejeitado"] / totais["rejeitado"]
                if totais["rejeitado"]
                else None,
            }
        )
    return sorted(linhas, key=lambda linha: -linha["documentos"])[:top]


def vocabulario(documentos: Iterable[dict], top: int = 20) -> dict[str, list[dict]]:
    """Palavras mais típicas da fundamentação de decisões acolhidas e rejeitadas.

    Usa só relatório e fundamentação: o dispositivo repete o resultado e contaminaria a medida.
    """
    tokens: dict[str, list[str]] = {"acolhido": [], "rejeitado": []}
    for doc in documentos:
        lado = _lado(doc["resultado"])
        if not lado:
            continue
        secoes = dividir(doc["texto"])
        texto = f"{secoes.relatorio}\n{secoes.fundamentacao}"
        tokens[lado] += [t for t in tokens_relevantes(texto) if t not in _EXCLUIR_VOCABULARIO]

    escores = estatistica.log_odds_dirichlet(tokens["acolhido"], tokens["rejeitado"])

    def linhas(itens):
        return [{"palavra": p, "z": z, "n_acolhidos": a, "n_rejeitados": b} for p, z, a, b in itens]

    return {
        "acolhido": linhas([e for e in escores if e[1] > 0][:top]),
        "rejeitado": linhas([e for e in reversed(escores) if e[1] < 0][:top]),
    }
