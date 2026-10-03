"""Validação da classificação automática de resultados contra rotulagem manual.

Fluxo: `dikemetria amostra` gera um CSV com o dispositivo pseudonimizado e o rótulo automático;
uma pessoa preenche a coluna `resultado_manual`; `dikemetria validar` mede a concordância.
"""

from __future__ import annotations

import csv
import random
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from dikemetria.estrutura import dividir
from dikemetria.resultado import Resultado

CAMPOS = [
    "id",
    "tribunal",
    "tipo",
    "dispositivo",
    "resultado_automatico",
    "confianca",
    "motivo",
    "capitulos",
    "resultado_manual",
]
ROTULOS_VALIDOS = {r.value for r in Resultado}


def gerar_amostra(
    documentos: list[dict], tamanho: int, saida: str | Path, semente: int = 42
) -> int:
    """Amostra estratificada por resultado automático, para que rótulos raros apareçam."""
    por_rotulo: dict[str, list[dict]] = {}
    for doc in documentos:
        por_rotulo.setdefault(doc["resultado"], []).append(doc)

    sorteio = random.Random(semente)
    cota = max(1, tamanho // max(1, len(por_rotulo)))
    escolhidos: list[dict] = []
    for grupo in por_rotulo.values():
        escolhidos += sorteio.sample(grupo, min(cota, len(grupo)))
    restantes = [d for d in documentos if d not in escolhidos]
    escolhidos += sorteio.sample(restantes, min(len(restantes), tamanho - len(escolhidos)))
    sorteio.shuffle(escolhidos)

    with open(saida, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS)
        escritor.writeheader()
        for doc in escolhidos[:tamanho]:
            avaliacao = doc.get("avaliacao") or {}
            capitulos = "; ".join(
                f"{c['objeto']}: {c['resultado']}" for c in avaliacao.get("capitulos") or []
            )
            escritor.writerow(
                {
                    "id": doc["id"],
                    "tribunal": doc.get("tribunal"),
                    "tipo": doc.get("tipo"),
                    "dispositivo": dividir(doc["texto"]).dispositivo[:1500],
                    "resultado_automatico": doc["resultado"],
                    "confianca": avaliacao.get("confianca", ""),
                    "motivo": avaliacao.get("motivo") or "",
                    "capitulos": capitulos,
                    "resultado_manual": "",
                }
            )
    return min(tamanho, len(escolhidos))


@dataclass
class Metricas:
    n: int
    acuracia: float
    por_rotulo: dict[str, dict[str, float]]  # precisão, cobertura (recall), f1, suporte
    confusao: dict[tuple[str, str], int]  # (manual, automático) -> quantidade


def avaliar(caminho: str | Path) -> Metricas:
    pares: list[tuple[str, str]] = []
    with open(caminho, encoding="utf-8") as arquivo:
        for linha in csv.DictReader(arquivo):
            manual = (linha.get("resultado_manual") or "").strip().lower()
            if not manual:
                continue
            if manual not in ROTULOS_VALIDOS:
                raise ValueError(f"Rótulo manual inválido na linha {linha['id']}: {manual}")
            pares.append((manual, linha["resultado_automatico"]))
    if not pares:
        raise ValueError("Nenhuma linha com resultado_manual preenchido.")

    confusao = Counter(pares)
    rotulos = sorted({r for par in pares for r in par})
    por_rotulo = {}
    for rotulo in rotulos:
        vp = confusao[(rotulo, rotulo)]
        previstos = sum(q for (_, a), q in confusao.items() if a == rotulo)
        reais = sum(q for (m, _), q in confusao.items() if m == rotulo)
        precisao = vp / previstos if previstos else 0.0
        cobertura = vp / reais if reais else 0.0
        f1 = 2 * precisao * cobertura / (precisao + cobertura) if precisao + cobertura else 0.0
        por_rotulo[rotulo] = {
            "precisao": precisao,
            "cobertura": cobertura,
            "f1": f1,
            "suporte": reais,
        }
    acertos = sum(q for (m, a), q in confusao.items() if m == a)
    return Metricas(len(pares), acertos / len(pares), por_rotulo, dict(confusao))


def concordancia_fontes(processos: list[dict], documentos: list[dict]) -> dict:
    """Compara o resultado dos movimentos (DataJud) com o do texto (DJEN) no mesmo processo."""

    def so_digitos(numero: str | None) -> str:
        return re.sub(r"\D", "", numero or "")

    por_numero = {
        so_digitos(d["numero"]): d["resultado"]
        for d in documentos
        if d.get("numero") and d["resultado"] != Resultado.INDETERMINADO.value
    }
    pares = [
        (p["resultado"], por_numero[so_digitos(p["numero"])])
        for p in processos
        if so_digitos(p["numero"]) in por_numero and p["resultado"] != Resultado.INDETERMINADO.value
    ]
    iguais = sum(1 for a, b in pares if a == b)
    return {"pares": len(pares), "iguais": iguais, "taxa": iguais / len(pares) if pares else None}
