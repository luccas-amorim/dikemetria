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


# Medidas sobre unidades consolidadas (consolidacao.py) -------------------------------------

_MERITO = {R.PROCEDENTE.value, R.PARCIALMENTE_PROCEDENTE.value, R.IMPROCEDENTE.value}
_ACOLHIDOS = {R.PROCEDENTE.value, R.PARCIALMENTE_PROCEDENTE.value}
_RECURSO_MERITO = {R.PROVIDO.value, R.PARCIALMENTE_PROVIDO.value, R.NAO_PROVIDO.value}
_PROVIDOS = {R.PROVIDO.value, R.PARCIALMENTE_PROVIDO.value}

# Faixa de valores plausíveis para estatísticas de condenação (fora dela, erro de leitura).
VALOR_MINIMO, VALOR_MAXIMO = 1.0, 10_000_000.0


def taxa_nacional(unidades: Iterable[dict], minimo: int | None = None) -> list[dict]:
    """Taxa agregada (todos os casos juntos) e média entre tribunais (cada tribunal pesa igual).

    A agregada responde "qual a proporção dos casos do país"; ela é dominada pelos tribunais
    grandes. A média entre tribunais responde "como decide um tribunal típico".
    """
    minimo = politica.MINIMO_PUBLICAVEL if minimo is None else minimo
    unidades = list(unidades)
    medidas = [
        ("procedência", _MERITO, {R.PROCEDENTE.value}),
        ("acolhimento", _MERITO, _ACOLHIDOS),
        ("provimento", _RECURSO_MERITO, _PROVIDOS),
    ]
    linhas = []
    for nome, denominador, numerador in medidas:
        casos = [u for u in unidades if u["resultado"] in denominador]
        if len(casos) < minimo:
            continue
        p, lo, hi = estatistica.wilson(sum(u["resultado"] in numerador for u in casos), len(casos))
        por_tribunal: dict[str, list[bool]] = defaultdict(list)
        for u in casos:
            por_tribunal[u.get("tribunal") or "?"].append(u["resultado"] in numerador)
        taxas = [sum(v) / len(v) for v in por_tribunal.values() if len(v) >= minimo]
        linhas.append(
            {
                "medida": nome,
                "n": len(casos),
                "agregada": p,
                "agregada_ic_inf": lo,
                "agregada_ic_sup": hi,
                "tribunais": len(taxas),
                "media_tribunais": sum(taxas) / len(taxas) if taxas else None,
                "minimo_tribunais": min(taxas) if taxas else None,
                "maximo_tribunais": max(taxas) if taxas else None,
            }
        )
    return linhas


def provimento_por_recurso(unidades: Iterable[dict], minimo: int | None = None) -> dict | None:
    """Conta cada capítulo recursal forte separadamente: "dou provimento ao recurso do autor e
    nego ao do réu" são dois recursos, um provido e um não."""
    minimo = politica.MINIMO_PUBLICAVEL if minimo is None else minimo
    resultados = [
        c["resultado"]
        for u in unidades
        for c in u.get("capitulos") or []
        if c["objeto"] == "recurso" and c["forca"] == "forte" and c["resultado"] in _RECURSO_MERITO
    ]
    if len(resultados) < minimo:
        return None
    p, lo, hi = estatistica.wilson(sum(r in _PROVIDOS for r in resultados), len(resultados))
    return {"recursos": len(resultados), "provimento": p, "ic_inf": lo, "ic_sup": hi}


def _final_para_o_autor(primeira: str, segunda: dict) -> str:
    """Resultado da ação depois do recurso (docs/REGRAS.md, "Reforma em segundo grau")."""
    acao_depois = segunda.get("resultado_acao")
    if acao_depois in _MERITO:
        return acao_depois  # o acórdão disse expressamente como fica o pedido
    recurso = segunda["resultado"]
    if recurso in (R.NAO_PROVIDO.value, R.NAO_CONHECIDO.value):
        return primeira
    if "anulação" in (segunda.get("motivo") or ""):
        return "sentença anulada"
    if primeira == R.PARCIALMENTE_PROCEDENTE.value:
        return "indeterminado (ambas as partes podem ter recorrido)"
    if recurso == R.PROVIDO.value:
        return R.IMPROCEDENTE.value if primeira == R.PROCEDENTE.value else R.PROCEDENTE.value
    if recurso == R.PARCIALMENTE_PROVIDO.value:
        return R.PARCIALMENTE_PROCEDENTE.value
    return R.INDETERMINADO.value


def reforma(unidades: Iterable[dict]) -> dict:
    """Cruza a sentença e o acórdão do mesmo processo.

    Infere quem recorreu pela sucumbência: de sentença totalmente procedente só o réu tem
    interesse em recorrer; de improcedente, só o autor. Por isso a inferência só vale para esses
    dois casos, e o recurso adesivo e o recurso de terceiro ficam fora do modelo.
    """
    por_numero: dict[str, dict[str, dict]] = defaultdict(dict)
    for u in unidades:
        if not u["numero"].startswith("doc:"):
            por_numero[u["numero"]][u["instancia"]] = u

    cruzamento: Counter = Counter()
    finais: Counter = Counter()
    for instancias in por_numero.values():
        primeira, segunda = instancias.get("1"), instancias.get("2")
        if not primeira or not segunda or primeira["resultado"] not in _MERITO:
            continue
        if segunda["resultado"] not in _RECURSO_MERITO | {R.NAO_CONHECIDO.value}:
            continue
        cruzamento[(primeira["resultado"], segunda["resultado"])] += 1
        finais[(primeira["resultado"], _final_para_o_autor(primeira["resultado"], segunda))] += 1

    julgados = sum(q for (_, r), q in cruzamento.items() if r in _RECURSO_MERITO)
    reformados = sum(q for (_, r), q in cruzamento.items() if r in _PROVIDOS)
    return {
        "pares": sum(cruzamento.values()),
        "taxa_reforma": reformados / julgados if julgados else None,
        "cruzamento": [
            {"sentenca": a, "recurso": b, "n": n} for (a, b), n in cruzamento.most_common()
        ],
        "resultado_final": [
            {"sentenca": a, "final": b, "n": n} for (a, b), n in finais.most_common()
        ],
    }


def valores_condenacao(
    unidades: Iterable[dict],
    categoria: str = "danos_morais",
    agrupamento: str = "tribunal",
    minimo: int | None = None,
) -> list[dict]:
    """Valor de referência da categoria nas sentenças que acolheram o pedido, por grupo.

    Valor de referência: o primeiro valor da categoria no dispositivo (docs/REGRAS.md).
    Valores fora de [VALOR_MINIMO, VALOR_MAXIMO] são descartados como erro de leitura.
    """
    minimo = politica.MINIMO_PUBLICAVEL if minimo is None else minimo
    chave = AGRUPAMENTOS[agrupamento]
    por_grupo: dict[str, list[float]] = defaultdict(list)
    for u in unidades:
        if u["instancia"] != "1" or u["resultado"] not in _ACOLHIDOS:
            continue
        valor = next(
            (
                v["valor"]
                for v in (u.get("calculo") or {}).get("valores", [])
                if v["categoria"] == categoria
            ),
            None,
        )
        if valor is None or not VALOR_MINIMO <= valor <= VALOR_MAXIMO:
            continue
        for grupo in chave(u):
            por_grupo[grupo].append(valor)
    linhas = [
        {
            "grupo": grupo,
            "n": len(valores),
            "mediana": estatistica.mediana(valores),
            "q1": estatistica.quantil(valores, 0.25),
            "q3": estatistica.quantil(valores, 0.75),
        }
        for grupo, valores in por_grupo.items()
        if len(valores) >= minimo
    ]
    return sorted(linhas, key=lambda linha: -linha["n"])


def parametros_calculo(unidades: Iterable[dict], minimo: int | None = None) -> list[dict]:
    """Frequência de honorários, repetição, termos iniciais e índices nas sentenças acolhidas."""
    minimo = politica.MINIMO_PUBLICAVEL if minimo is None else minimo
    contagens: dict[str, Counter] = defaultdict(Counter)
    for u in unidades:
        if u["instancia"] != "1" or u["resultado"] not in _ACOLHIDOS:
            continue
        calculo = u.get("calculo") or {}
        if calculo.get("honorarios_percentual") is not None:
            pct = calculo["honorarios_percentual"]
            contagens["honorários (%)"][f"{pct:g}%"] += 1
        if calculo.get("repeticao"):
            contagens["repetição do indébito"][calculo["repeticao"]] += 1
        for termo in calculo.get("juros_termos_iniciais") or []:
            contagens["juros: termo inicial"][termo] += 1
        if calculo.get("juros_taxa"):
            contagens["juros: taxa"][calculo["juros_taxa"]] += 1
        for termo in calculo.get("correcao_termos_iniciais") or []:
            contagens["correção: termo inicial"][termo] += 1
        if calculo.get("correcao_indice"):
            contagens["correção: índice"][calculo["correcao_indice"]] += 1
    linhas = []
    for parametro, contagem in contagens.items():
        total = sum(contagem.values())
        for valor, n in contagem.most_common():
            if n >= minimo:
                linhas.append(
                    {"parametro": parametro, "valor": valor, "n": n, "proporcao": n / total}
                )
    return linhas


def motivos(unidades: Iterable[dict], resultado: str = R.EXTINTO_SEM_MERITO.value) -> list[dict]:
    """Motivos, só entre as decisões cujo resultado veio do texto (os movimentos não os trazem)."""
    contagem = Counter(
        (u.get("motivo") or "não identificado")
        for u in unidades
        if u["resultado"] == resultado and u.get("fonte_resultado", "texto") == "texto"
    )
    total = sum(contagem.values())
    return [{"motivo": m, "n": n, "proporcao": n / total} for m, n in contagem.most_common()]


def qualidade(unidades: Iterable[dict]) -> dict:
    """Indicadores da própria classificação: confiança, fontes e divergências."""
    unidades = list(unidades)
    ambos = [u for u in unidades if u["fonte"] == "ambos"]
    return {
        "unidades": len(unidades),
        "indeterminadas": sum(u["resultado"] == R.INDETERMINADO.value for u in unidades),
        "confianca": dict(Counter(u.get("confianca") or "—" for u in unidades)),
        "fontes": dict(Counter(u["fonte"] for u in unidades)),
        "com_duas_fontes": len(ambos),
        "divergentes": sum(u["divergente"] for u in ambos),
    }
