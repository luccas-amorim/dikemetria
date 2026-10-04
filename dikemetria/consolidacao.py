"""Unidade de análise: uma decisão de mérito por processo e por instância.

O mesmo processo aparece várias vezes no corpus: o DataJud traz um registro por grau, e o DJEN
publica a mesma sentença uma vez por destinatário, além dos embargos de declaração e do acórdão.
Contar cada aparição distorceria as taxas. As regras (docs/REGRAS.md, "Unidade de análise"):

1. Instância: sentença = 1ª; acórdão e decisão monocrática em recurso = 2ª. Decisões só de
   embargos de declaração não formam unidade, porque não julgam o pedido.
2. Por processo e instância, vale a primeira decisão com resultado determinado, em ordem de data.
3. Texto e movimentos do mesmo processo e instância são unidos. O resultado do texto prevalece,
   porque o dispositivo é mais específico; os movimentos suprem o que o texto não resolveu.
   Quando os dois são determinados e diferentes, a unidade fica marcada como divergente.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from dikemetria.resultado import MERITO_PRIMEIRO_GRAU, MERITO_RECURSAL, Resultado

R = Resultado
INDETERMINADO = R.INDETERMINADO.value
_PRIMEIRA = {"G1", "JE"}
_SEGUNDA = {"G2", "TR"}
_SUPERIOR = {"SUP", "STJ", "TST", "TSE", "STM", "TS"}


def digitos(numero: str | None) -> str:
    return re.sub(r"\D", "", numero or "")


def instancia_do_grau(grau: str | None) -> str | None:
    grau = (grau or "").upper()
    if grau in _PRIMEIRA:
        return "1"
    if grau in _SEGUNDA:
        return "2"
    if grau in _SUPERIOR:
        return "3"
    return None


def instancia_do_documento(doc: dict) -> str | None:
    avaliacao = doc.get("avaliacao") or {}
    tipo = avaliacao.get("tipo_decisao")
    if tipo == "embargos_declaracao":
        return None
    if tipo == "sentenca":
        return "1"
    if tipo in ("acordao", "decisao_monocratica"):
        return "2"
    resultado = doc.get("resultado")
    if resultado in {r.value for r in MERITO_PRIMEIRO_GRAU} | {
        R.EXTINTO_SEM_MERITO.value,
        R.HOMOLOGACAO_ACORDO.value,
    }:
        return "1"
    if resultado in {r.value for r in MERITO_RECURSAL} | {R.NAO_CONHECIDO.value}:
        return "2"
    return None


def _grau_padrao(instancia: str) -> str:
    return {"1": "G1", "2": "G2", "3": "SUP"}.get(instancia, "")


def consolidar(processos: Iterable[dict], documentos: Iterable[dict]) -> list[dict]:
    """Uma unidade por (número, instância), unindo texto e movimentos."""
    textos: dict[tuple[str, str], dict] = {}
    for doc in sorted(documentos, key=lambda d: (d.get("data") or "9999", d["id"])):
        instancia = instancia_do_documento(doc)
        if instancia is None:
            continue
        chave = (digitos(doc.get("numero")) or f"doc:{doc['id']}", instancia)
        atual = textos.get(chave)
        if atual is None or (
            atual["resultado"] == INDETERMINADO and doc["resultado"] != INDETERMINADO
        ):
            textos[chave] = doc

    movimentos: dict[tuple[str, str], dict] = {}
    for proc in processos:
        instancia = instancia_do_grau(proc.get("grau"))
        if instancia is None:
            continue
        chave = (digitos(proc["numero"]), instancia)
        movimentos.setdefault(chave, proc)

    unidades = []
    for chave in sorted(set(textos) | set(movimentos)):
        doc, proc = textos.get(chave), movimentos.get(chave)
        unidades.append(_unir(chave, doc, proc))
    return unidades


def _unir(chave: tuple[str, str], doc: dict | None, proc: dict | None) -> dict:
    numero, instancia = chave
    avaliacao = (doc or {}).get("avaliacao") or {}
    r_texto = doc["resultado"] if doc else None
    r_mov = proc["resultado"] if proc else None

    if r_texto and r_texto != INDETERMINADO:
        resultado, fonte = r_texto, "texto"
    elif r_mov and r_mov != INDETERMINADO:
        resultado, fonte = r_mov, "movimentos"
    else:
        resultado, fonte = INDETERMINADO, "texto" if doc else "movimentos"

    divergente = bool(
        r_texto and r_mov and INDETERMINADO not in (r_texto, r_mov) and r_texto != r_mov
    )
    confianca = avaliacao.get("confianca") if fonte == "texto" else "media"
    base = proc or {}
    return {
        "numero": numero,
        "instancia": instancia,
        "tribunal": (doc or {}).get("tribunal") or base.get("tribunal"),
        "grau": base.get("grau") or _grau_padrao(instancia),
        "classe_nome": base.get("classe_nome") or (doc or {}).get("classe_nome"),
        "assuntos": base.get("assuntos") or [],
        "data_ajuizamento": base.get("data_ajuizamento"),
        "data_julgamento": base.get("data_julgamento") or (doc or {}).get("data"),
        "duracao_dias": base.get("duracao_dias"),
        "resultado": resultado,
        "resultado_texto": r_texto,
        "resultado_movimentos": r_mov,
        "resultado_acao": avaliacao.get("resultado_acao"),
        "fonte": "ambos" if doc and proc else fonte,
        "fonte_resultado": fonte,
        "divergente": divergente,
        "confianca": confianca,
        "motivo": avaliacao.get("motivo") if fonte == "texto" else None,
        "capitulos": avaliacao.get("capitulos") or [],
        "calculo": avaliacao.get("calculo") or {},
        "sensivel": bool((doc or {}).get("sensivel") or base.get("sensivel")),
    }
