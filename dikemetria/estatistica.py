"""Estatística descritiva usada nos relatórios. Só biblioteca padrão."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Sequence


def wilson(sucessos: int, total: int, z: float = 1.96) -> tuple[float, float, float]:
    """Proporção e intervalo de confiança de Wilson (95% por padrão)."""
    if total == 0:
        return (math.nan, math.nan, math.nan)
    p = sucessos / total
    denominador = 1 + z**2 / total
    centro = (p + z**2 / (2 * total)) / denominador
    margem = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominador
    return (p, max(0.0, centro - margem), min(1.0, centro + margem))


def mediana(valores: Sequence[float]) -> float:
    if not valores:
        return math.nan
    ordenados = sorted(valores)
    meio = len(ordenados) // 2
    if len(ordenados) % 2:
        return float(ordenados[meio])
    return (ordenados[meio - 1] + ordenados[meio]) / 2


def quantil(valores: Sequence[float], q: float) -> float:
    """Quantil por interpolação linear (método 7, o padrão do R e do numpy)."""
    if not valores:
        return math.nan
    ordenados = sorted(valores)
    posicao = (len(ordenados) - 1) * q
    baixo = math.floor(posicao)
    alto = math.ceil(posicao)
    return ordenados[baixo] + (ordenados[alto] - ordenados[baixo]) * (posicao - baixo)


def log_odds_dirichlet(
    grupo_a: Iterable[str],
    grupo_b: Iterable[str],
    alfa_total: float = 1000.0,
    minimo: int = 5,
) -> list[tuple[str, float, int, int]]:
    """Log-odds com prior de Dirichlet informativo (Monroe, Colaresi e Quinn, 2008).

    Mede quais palavras distinguem o vocabulário do grupo A do grupo B, encolhendo palavras
    raras em direção a zero. Devolve (palavra, escore z, contagem em A, contagem em B),
    do mais típico de A ao mais típico de B. É uma medida descritiva de associação, não um
    preditor de resultado.
    """
    contagem_a, contagem_b = Counter(grupo_a), Counter(grupo_b)
    fundo = contagem_a + contagem_b
    total_fundo = sum(fundo.values())
    n_a, n_b = sum(contagem_a.values()), sum(contagem_b.values())
    if not total_fundo or not n_a or not n_b:
        return []

    resultado = []
    for palavra, freq in fundo.items():
        if freq < minimo:
            continue
        alfa = alfa_total * freq / total_fundo
        y_a, y_b = contagem_a[palavra], contagem_b[palavra]
        delta = math.log((y_a + alfa) / (n_a + alfa_total - y_a - alfa)) - math.log(
            (y_b + alfa) / (n_b + alfa_total - y_b - alfa)
        )
        variancia = 1 / (y_a + alfa) + 1 / (y_b + alfa)
        resultado.append((palavra, delta / math.sqrt(variancia), y_a, y_b))
    return sorted(resultado, key=lambda linha: -linha[1])
