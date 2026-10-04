"""Localização de referências normativas e identificadores processuais.

Trabalha sobre o texto bruto (normalizado), nunca sobre o texto já limpo, porque a limpeza remove
os números e a pontuação de que as citações dependem.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass

NUMERO_CNJ = re.compile(r"\b(\d{7})-?(\d{2})\.?(\d{4})\.?(\d)\.?(\d{2})\.?(\d{4})\b")

# Diplomas reconhecidos depois de um artigo, do nome mais longo para o mais curto.
_DIPLOMAS = [
    (r"Constitui[çc][ãa]o(?:\s+(?:da\s+Rep[úu]blica|Federal))?(?:\s+de\s+1988)?", "CF"),
    (r"C[óo]digo\s+de\s+Processo\s+Civil", "CPC"),
    (r"C[óo]digo\s+de\s+Processo\s+Penal", "CPP"),
    (r"C[óo]digo\s+de\s+Defesa\s+do\s+Consumidor", "CDC"),
    (r"C[óo]digo\s+Tribut[áa]rio\s+Nacional", "CTN"),
    (r"C[óo]digo\s+Civil", "CC"),
    (r"C[óo]digo\s+Penal", "CP"),
    (r"Consolida[çc][ãa]o\s+das\s+Leis\s+do\s+Trabalho", "CLT"),
    (r"Estatuto\s+da\s+Crian[çc]a\s+e\s+do\s+Adolescente", "ECA"),
    (r"Lei\s+(?:Complementar\s+)?(?:n[º°o.]*\s*)?\d{1,2}\.?\d{3}(?:/\d{2,4})?", None),
    (r"CF(?:/88)?|CRFB(?:/88)?|CPC(?:/15|/2015)?|CPP|CDC|CTN|CLT|ECA|CC(?:/02|/2002)?|CP", None),
]
_DIPLOMA = "|".join(f"(?:{padrao})" for padrao, _ in _DIPLOMAS)

ARTIGO = re.compile(
    r"\bart(?:igo)?s?\.?\s*"
    r"(?P<numero>\d{1,4}(?:\.\d{3})?)\s*(?:º|°|o\b)?(?:-?(?P<letra>[A-Z])\b)?"
    r"(?P<desdobramento>(?:\s*,?\s*(?:§+\s*\d+\s*[º°o]?|par[áa]grafo\s+[úu]nico|caput|"
    r"inc(?:iso|\.)?\s+[IVXLC]+|[IVXLC]+\b|al[íi]nea\s+\"?[a-z]\"?))*)"
    r"(?:\s*,?\s*(?:d[aoe]s?|do\s+novo)\s+(?P<diploma>" + _DIPLOMA + r"))?",
    re.IGNORECASE,
)

LEI = re.compile(
    r"\bLei\s+(?P<complementar>Complementar\s+)?(?:Federal\s+)?(?:n[º°o.]*\s*)?"
    r"(?P<numero>\d{1,2}\.?\d{3})(?:\s*/\s*(?P<ano>\d{2,4}))?",
    re.IGNORECASE,
)

SUMULA = re.compile(
    r"\bS[úu]mula\s+(?P<vinculante>Vinculante\s+)?(?:n[º°o.]*\s*)?(?P<numero>\d{1,2}\.\d{3}|\d{1,4})"
    r"(?:\s*,?\s*d[oa]\s+(?:Colendo\s+|Egr[ée]gio\s+|E\.\s*)?(?P<tribunal>STF|STJ|TST|TSE|TJ[A-Z]{2}|"
    r"TRF\d|Supremo\s+Tribunal\s+Federal|Superior\s+Tribunal\s+de\s+Justi[çc]a))?",
    re.IGNORECASE,
)

TEMA = re.compile(
    r"\bTema\s+(?:n[º°o.]*\s*)?(?P<numero>\d{1,2}\.\d{3}|\d{1,4})"
    r"(?:\s*,?\s*d[oa]\s+(?P<tribunal>STF|STJ|TST))?",
    re.IGNORECASE,
)

# Leis que têm sigla própria: "art. 14 da Lei 8.078/90" é o mesmo que "art. 14 do CDC".
_LEIS_COM_SIGLA = {
    "Lei 8.078/1990": "CDC",
    "Lei 10.406/2002": "CC",
    "Lei 13.105/2015": "CPC",
    "Lei 5.172/1966": "CTN",
    "Lei 8.069/1990": "ECA",
}

_SIGLAS_POR_NOME = {
    "supremo tribunal federal": "STF",
    "superior tribunal de justiça": "STJ",
    "superior tribunal de justica": "STJ",
}


@dataclass(frozen=True)
class Citacao:
    tipo: str  # artigo, lei, sumula, tema
    referencia: str  # forma normalizada, ex.: "art. 14 CDC"
    trecho: str  # como aparece no texto

    def como_dict(self) -> dict:
        return asdict(self)


def formatar_cnj(grupos: tuple[str, ...]) -> str:
    n, dd, aaaa, j, tr, oooo = grupos
    return f"{n}-{dd}.{aaaa}.{j}.{tr}.{oooo}"


def digito_cnj_valido(numero: str) -> bool:
    """Confere os dígitos verificadores (módulo 97, Resolução CNJ 65/2008)."""
    digitos = re.sub(r"\D", "", numero)
    if len(digitos) != 20:
        return False
    n, dd, resto = digitos[:7], digitos[7:9], digitos[9:]
    return 98 - (int(n + resto + "00") % 97) == int(dd)


def numeros_cnj(texto: str) -> list[str]:
    """Números de processo no padrão CNJ com dígito verificador válido, sem repetição."""
    vistos: dict[str, None] = {}
    for m in NUMERO_CNJ.finditer(texto):
        numero = formatar_cnj(m.groups())
        if digito_cnj_valido(numero):
            vistos.setdefault(numero, None)
    return list(vistos)


def _sigla_diploma(diploma: str | None) -> str | None:
    if not diploma:
        return None
    for padrao, sigla in _DIPLOMAS:
        if re.fullmatch(padrao, diploma, re.IGNORECASE):
            if sigla:
                return sigla
            lei = LEI.fullmatch(diploma)
            if lei:
                formatada = _formatar_lei(lei)
                return _LEIS_COM_SIGLA.get(formatada, formatada)
            base = diploma.upper().split("/")[0]
            return {"CRFB": "CF"}.get(base, base)
    return diploma


def _milhar(numero: str) -> str:
    """'1022' ou '1.022' -> '1.022'."""
    return f"{int(numero.replace('.', '')):,}".replace(",", ".")


def _formatar_lei(m: re.Match) -> str:
    numero = _milhar(m.group("numero"))
    prefixo = "LC" if m.group("complementar") else "Lei"
    ano = m.group("ano")
    if ano and len(ano) == 2:
        ano = ("19" if int(ano) > 30 else "20") + ano
    return f"{prefixo} {numero}/{ano}" if ano else f"{prefixo} {numero}"


def citacoes(texto: str) -> list[Citacao]:
    """Todas as citações normativas do texto, na ordem em que aparecem."""
    encontradas: list[tuple[int, Citacao]] = []
    cobertos: list[tuple[int, int]] = []

    for m in ARTIGO.finditer(texto):
        numero = _milhar(m.group("numero"))
        letra = f"-{m.group('letra').upper()}" if m.group("letra") else ""
        diploma = _sigla_diploma(m.group("diploma"))
        ref = f"art. {numero}{letra}" + (f" {diploma}" if diploma else "")
        encontradas.append((m.start(), Citacao("artigo", ref, m.group(0).strip())))
        if m.group("diploma"):
            cobertos.append(m.span("diploma"))

    for m in LEI.finditer(texto):
        if any(ini <= m.start() < fim for ini, fim in cobertos):
            continue  # a lei já foi registrada como diploma de um artigo
        encontradas.append((m.start(), Citacao("lei", _formatar_lei(m), m.group(0).strip())))

    for m in SUMULA.finditer(texto):
        tribunal = m.group("tribunal")
        if tribunal:
            tribunal = _SIGLAS_POR_NOME.get(tribunal.lower(), tribunal.upper())
        tipo = "Súmula Vinculante" if m.group("vinculante") else "Súmula"
        ref = f"{tipo} {_milhar(m.group('numero'))}" + (f" {tribunal}" if tribunal else "")
        encontradas.append((m.start(), Citacao("sumula", ref, m.group(0).strip())))

    for m in TEMA.finditer(texto):
        tribunal = m.group("tribunal")
        ref = f"Tema {_milhar(m.group('numero'))}" + (f" {tribunal.upper()}" if tribunal else "")
        encontradas.append((m.start(), Citacao("tema", ref, m.group(0).strip())))

    return [c for _, c in sorted(encontradas, key=lambda par: par[0])]


def contar_citacoes(texto: str) -> Counter[str]:
    return Counter(c.referencia for c in citacoes(texto))
