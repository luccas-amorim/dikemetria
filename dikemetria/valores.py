"""Extração dos parâmetros de cálculo fixados no dispositivo.

Lê, do texto do dispositivo (nunca da fundamentação, que discute valores pedidos e rejeitados):

* valores em reais, classificados pela finalidade (danos morais, danos materiais, restituição,
  lucros cessantes, multa, honorários, pensão, valor da causa, outros);
* honorários de sucumbência em percentual e a base de cálculo;
* repetição do indébito em dobro ou simples;
* termo inicial e taxa dos juros de mora, termo inicial e índice da correção monetária;
* gratuidade da justiça (exigibilidade suspensa, art. 98, § 3º, do CPC).

As regras estão descritas em docs/REGRAS.md.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from dikemetria.avaliacao import normalizar

_MOEDA = re.compile(
    r"r\$\s*(?P<inteiro>\d{1,3}(?:\.\d{3})+|\d+)(?:,(?P<centavos>\d{1,2}))?"
    r"(?:\s*(?P<escala>mil|milhoes|milhao)\b)?"
)

# Categoria pela palavra-chave mais próxima do valor (antes ou depois).
CATEGORIAS: list[tuple[str, re.Pattern]] = [
    ("valor_causa", re.compile(r"valor\s+(?:atualizado\s+)?da\s+causa")),
    ("honorarios", re.compile(r"honorarios")),
    ("danos_morais", re.compile(r"danos?\s+mora(?:l|is)|dano\s+extrapatrimonial")),
    ("danos_materiais", re.compile(r"danos?\s+materia(?:l|is)|danos?\s+emergentes?")),
    ("lucros_cessantes", re.compile(r"lucros?\s+cessantes?")),
    (
        "restituicao",
        re.compile(r"restitui|repeticao|devolu|reembols|ressarc|indebito|cobrad[oa]s?\s+indevid"),
    ),
    ("debito_inexigivel", re.compile(r"inexig\w+|inexistencia\s+d[eo]\s+debito|\bdebito\b")),
    ("multa", re.compile(r"\bmulta\b|astreintes?")),
    ("pensao", re.compile(r"\bpensao\b|pensionamento|alimentos")),
    ("custas", re.compile(r"\bcustas\b")),
]

_JANELA = 90

_EXTENSO = {"cinco": 5, "dez": 10, "doze": 12, "quinze": 15, "vinte": 20}
_HONORARIOS_PCT = re.compile(
    r"honorarios[^;]{0,200}?\b(?:(?P<num>\d{1,2}(?:,\d{1,2})?)\s*%|"
    r"(?P<ext>cinco|dez|doze|quinze|vinte)\s+por\s+cento)"
)
_HONORARIOS_BASE = [
    (
        "valor da condenação",
        re.compile(r"(?:sobre\s+o\s+)?valor\s+(?:atualizado\s+)?da\s+condenacao"),
    ),
    ("valor da causa", re.compile(r"(?:sobre\s+o\s+)?valor\s+(?:atualizado\s+)?da\s+causa")),
    ("proveito econômico", re.compile(r"proveito\s+economico")),
]

_DOBRO = re.compile(r"\bem\s+dobro\b|\bdobrad[oa]\b")
_SIMPLES = re.compile(r"\bde\s+forma\s+simples\b|\bna\s+forma\s+simples\b|\bsimples(?:mente)?\b")

_MARCOS = [
    ("citação", r"citacao"),
    (
        "evento danoso",
        r"evento\s+danoso|data\s+do\s+(?:fato|evento|ilicito)|"
        r"(?:inscricao|negativacao)\s+indevida|data\s+da\s+(?:inscricao|negativacao)",
    ),
    (
        "arbitramento",
        r"arbitramento|(?:data\s+d[ae]sta|prolacao\s+da)\s+(?:sentenca|decisao)|"
        r"publicacao\s+d[ae]sta",
    ),
    (
        "desembolso",
        r"(?:cada\s+)?desembolso|pagamento\s+indevido|(?:cada\s+)?cobranca|"
        r"(?:cada\s+)?desconto",
    ),
    ("vencimento", r"vencimento"),
    ("trânsito em julgado", r"transito\s+em\s+julgado"),
    ("ajuizamento", r"ajuizamento|propositura|distribuicao"),
]
_MARCO = "|".join(f"(?P<m{i}>{padrao})" for i, (_, padrao) in enumerate(_MARCOS))
_A_PARTIR = (
    r"(?:desde|a\s+partir\s+d[aeo]s?|a\s+contar\s+d[aeo]s?|contad[oa]s?\s+d[aeo]s?)\s+"
    r"(?:a\s+|o\s+|cada\s+)?"
)
_CORRECAO = r"(?:correc\w+\s+monetaria|corrigid[oa]s?|atualizad[oa]s?\s+monetariamente)"

_JUROS_MARCO = re.compile(r"juros[^;]{0,160}?" + _A_PARTIR + rf"(?:{_MARCO})")
_CORRECAO_MARCO = re.compile(_CORRECAO + r"[^;]{0,160}?" + _A_PARTIR + rf"(?:{_MARCO})")
_JUROS_TAXA = [
    ("Selic", re.compile(r"juros[^;]{0,120}?selic|selic[^;]{0,60}?juros")),
    (
        "1% ao mês",
        re.compile(r"juros[^;]{0,80}?\b1\s*%\s*(?:\(um\s+por\s+cento\)\s*)?(?:ao|a\.)\s*m"),
    ),
    ("taxa legal (art. 406 CC)", re.compile(r"juros[^;]{0,120}?(?:art\.?\s*406|taxa\s+legal)")),
]
_CORRECAO_INDICE = [
    ("IPCA-E", re.compile(r"ipca-e\b")),
    ("IPCA", re.compile(r"\bipca\b(?!-e)")),
    ("INPC", re.compile(r"\binpc\b")),
    ("IGP-M", re.compile(r"\bigp-?m\b")),
    ("Tabela Prática do TJSP", re.compile(r"tabela\s+pratica")),
    ("Selic", re.compile(r"correc\w+[^;]{0,120}?selic")),
]
_GRATUIDADE = re.compile(
    r"gratuidade|justica\s+gratuita|assistencia\s+judiciaria|art\.?\s*98,?\s*(?:§|par\w*)\s*3|"
    r"exigibilidade\s+suspensa|condicao\s+suspensiva"
)
_CADA = re.compile(
    r"\bpara\s+cada\s+(?:um\s+d[oa]s\s+)?(?:autor|autora|requerente|parte)|\bpor\s+autor\b"
)


@dataclass(frozen=True)
class Valor:
    categoria: str
    valor: float
    trecho: str


@dataclass
class Calculo:
    valores: list[Valor] = field(default_factory=list)
    honorarios_percentual: float | None = None
    honorarios_base: str | None = None
    repeticao: str | None = None  # "em dobro", "simples" ou None
    juros_termos_iniciais: list[str] = field(default_factory=list)
    juros_taxa: str | None = None
    correcao_termos_iniciais: list[str] = field(default_factory=list)
    correcao_indice: str | None = None
    gratuidade: bool = False
    valor_por_autor: bool = False

    def total(self, categoria: str) -> float | None:
        """Primeiro valor da categoria (ver docs/REGRAS.md, "Valor de referência")."""
        for v in self.valores:
            if v.categoria == categoria:
                return v.valor
        return None

    def como_dict(self) -> dict:
        return asdict(self)


def _valor(m: re.Match) -> float:
    inteiro = int(m.group("inteiro").replace(".", ""))
    centavos = int((m.group("centavos") or "0").ljust(2, "0"))
    valor = inteiro + centavos / 100
    escala = m.group("escala")
    if escala == "mil":
        valor *= 1_000
    elif escala:
        valor *= 1_000_000
    return valor


def _categoria(texto: str, inicio: int, fim: int) -> str:
    """Palavra-chave mais próxima, olhando até _JANELA caracteres antes e depois, sem atravessar
    ponto e vírgula nem outro valor em reais."""
    antes = texto[max(0, inicio - _JANELA) : inicio]
    antes = re.split(r";|r\$", antes)[-1]
    depois = texto[fim : fim + _JANELA]
    depois = re.split(r";|r\$", depois)[0]
    melhor: tuple[int, str] | None = None
    for nome, padrao in CATEGORIAS:
        for m in padrao.finditer(antes):
            distancia = len(antes) - m.end()
            if melhor is None or distancia < melhor[0]:
                melhor = (distancia, nome)
        m = padrao.search(depois)
        if m and (melhor is None or m.start() < melhor[0]):
            melhor = (m.start(), nome)
    return melhor[1] if melhor else "outros"


def _marco(m: re.Match) -> str:
    for i, (nome, _) in enumerate(_MARCOS):
        if m.group(f"m{i}"):
            return nome
    return "outro"


def calcular(dispositivo: str) -> Calculo:
    texto = normalizar(dispositivo)
    calculo = Calculo()

    for m in _MOEDA.finditer(texto):
        calculo.valores.append(
            Valor(_categoria(texto, m.start(), m.end()), _valor(m), texto[m.start() : m.end()])
        )

    m = _HONORARIOS_PCT.search(texto)
    if m:
        bruto = m.group("num")
        calculo.honorarios_percentual = (
            float(bruto.replace(",", ".")) if bruto else float(_EXTENSO[m.group("ext")])
        )
        janela = texto[m.end() : m.end() + 120]
        for nome, padrao in _HONORARIOS_BASE:
            if padrao.search(janela):
                calculo.honorarios_base = nome
                break

    if _DOBRO.search(texto):
        calculo.repeticao = "em dobro"
    elif re.search(r"restitui|repeticao|devolu", texto) and _SIMPLES.search(texto):
        calculo.repeticao = "simples"

    calculo.juros_termos_iniciais = list(dict.fromkeys(map(_marco, _JUROS_MARCO.finditer(texto))))
    for nome, padrao in _JUROS_TAXA:
        if padrao.search(texto):
            calculo.juros_taxa = nome
            break
    calculo.correcao_termos_iniciais = list(
        dict.fromkeys(map(_marco, _CORRECAO_MARCO.finditer(texto)))
    )
    for nome, padrao in _CORRECAO_INDICE:
        if padrao.search(texto):
            calculo.correcao_indice = nome
            break

    calculo.gratuidade = bool(_GRATUIDADE.search(texto))
    calculo.valor_por_autor = bool(_CADA.search(texto))
    return calculo
