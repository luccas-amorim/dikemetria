"""Pseudonimização de decisões antes de qualquer armazenamento ou análise (LGPD, art. 7º, § 3º).

Substitui por marcadores os dados que identificam pessoas naturais: nomes, CPF, RG, endereços,
CEP, telefones, e-mails, números de OAB e contas bancárias. Nomes de pessoas jurídicas e entes
públicos ficam no texto, porque não são dados pessoais e interessam à pesquisa.

A remoção de nomes combina três fontes, da mais à menos precisa:

1. nomes já conhecidos (por exemplo, os destinatários de uma intimação no DJEN);
2. nomes depois de papéis processuais ("Autor:", "Juiz de Direito", "Dr.") ou seguidos de
   qualificação ("FULANO DE TAL, brasileiro, casado");
3. opcionalmente, o reconhecimento de entidades do spaCy, se instalado.

Nenhum método é perfeito. Por isso o projeto não redistribui texto integral, só agregados.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

_MAIUSC = "A-ZÀ-ÖØ-Ý"
_MINUSC = "a-zß-öø-ÿ"
_PALAVRA_NOME = rf"(?:[{_MAIUSC}][{_MINUSC}]+|[{_MAIUSC}]{{2,}})"
_CONECTIVO = r"(?:d[aeo]s?|e)"
NOME_PROPRIO = rf"{_PALAVRA_NOME}(?:[ \t]+(?:{_CONECTIVO}[ \t]+)?{_PALAVRA_NOME})+"

_PAPEIS = (
    r"autor[a]?|autores|requerente|requerid[oa]s?|r[ée]u|r[ée]|exequente|executad[oa]|"
    r"apelante|apelad[oa]|agravante|agravad[oa]|impetrante|reclamante|reclamad[oa]|"
    r"embargante|embargad[oa]|recorrente|recorrid[oa]|interessad[oa]|paciente|"
    r"advogad[oa]|procurador[a]?|ju[ií]z[a]?(?:\s+de\s+direito)?(?:\s+substitut[oa])?|"
    r"relator[a]?|desembargador[a]?|promotor[a]?(?:\s+de\s+justi[çc]a)?|defensor[a]?|"
    r"perit[oa]|testemunha|curador[a]?|inventariante|dr\.?|dra\.?|sr\.?|sra\.?"
)

_DEPOIS_DE_PAPEL = re.compile(
    rf"(?P<papel>\b(?:(?:{_PAPEIS})\b[ \t]*)+)(?P<sep>[ \t]*[:\-–]?[ \t]*)"
    rf"(?P<nome>(?-i:{NOME_PROPRIO}))",
    re.IGNORECASE,
)

_QUALIFICADO = re.compile(
    rf"(?P<nome>{NOME_PROPRIO})(?=\s*,\s*(?:brasileir|estrangeir|solteir|casad|divorciad|"
    r"vi[úu]v|separad|convivente|menor|portador|inscrit|nascid|maior|residente|domiciliad))"
)

_ANTES_DE_PAPEL = re.compile(
    rf"(?m)^(?P<nome>(?-i:{NOME_PROPRIO}))[ \t]*\n[ \t]*(?=(?:{_PAPEIS})\b)", re.IGNORECASE
)

# Advogados ao lado do número da OAB, já trocado por [OAB]: "FULANO DE TAL [OAB]",
# "Fulano de Tal, ([OAB]" e, no eproc, "[OAB] - FULANO DE TAL - ADVOGADO".
_ANTES_DE_OAB = re.compile(rf"(?P<nome>{NOME_PROPRIO})[ \t]*,?[ \t]*\(?[ \t]*\[OAB\]")
_DEPOIS_DE_OAB = re.compile(rf"\[OAB\][ \t]*[-–][ \t]*(?P<nome>{NOME_PROPRIO})")

# Palavras que indicam pessoa jurídica ou ente público: o nome fica no texto.
_ENTIDADE = re.compile(
    r"\b(?:S\.?/?A\.?|LTDA|EIRELI|ME|EPP|BANCO|CIA|COMPANHIA|COOPERATIVA|ASSOCIA[ÇC][ÃA]O|"
    r"FUNDA[ÇC][ÃA]O|INSTITUTO|INSS|UNI[ÃA]O|ESTADO|MUNIC[ÍI]PIO|FAZENDA|MINIST[ÉE]RIO|"
    r"DEFENSORIA|PROCURADORIA|SECRETARIA|CAIXA|TELEF[ÔO]NICA|TELECOM|SEGURADORA|SEGUROS|"
    r"LIMITADA|CONDOM[ÍI]NIO|EMPRESA|COM[ÉE]RCIO|SERVI[ÇC]OS|PARTICIPA[ÇC][ÕO]ES|TRIBUNAL|VARA|"
    r"JU[ÍI]ZO|C[ÂA]MARA|COMARCA|PODER|JUDICI[ÁA]RIO|REP[ÚU]BLICA)\b",
    re.IGNORECASE,
)

# Sufixo de pessoa jurídica logo depois do nome: "EXEMPLO VAREJO S.A., inscrita no CNPJ".
_ENTIDADE_SEGUINTE = re.compile(
    r"[ \t]*,?[ \t]*(?:S[ \t]*[./]?[ \t]*A\b|LTDA|LIMITADA|EIRELI)", re.IGNORECASE
)

# Nome não começa por conectivo ou preposição: "DE DIREITO DA", "PELA IMPROCEDÊNCIA".
_COMECA_COM_CONECTIVO = re.compile(r"^(?:d[aeo]s?|e|pel[ao]s?|para|com|sem|n[ao]s?)\s", re.I)

# Expressões em maiúsculas que parecem nomes mas são termos da própria decisão.
_NAO_NOME = re.compile(
    r"^(?:JULGO|ANTE|DIANTE|ISTO|POSTO|SENTEN[ÇC]A|RELAT[ÓO]RIO|FUNDAMENTA[ÇC][ÃA]O|DISPOSITIVO|"
    r"DECIDO|VISTOS|AC[ÓO]RD[ÃA]O|EMENTA|PROCEDENTE|IMPROCEDENTE|PUBLIQUE|INTIMEM|CITE|"
    r"CUMPRA|DECIS[ÃA]O|DESPACHO|PODER|ESTADO|COMARCA|FORO)\b",
    re.IGNORECASE,
)

_DOCUMENTOS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")),
    ("CNPJ", re.compile(r"(?<!\d)\d{2}\.?\d{3}\.?\d{3}/\d{4}-?\d{2}(?!\d)")),
    ("CPF", re.compile(r"(?<![\d.])\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)|\bCPF[^\d\n]{0,12}\d{11}\b")),
    ("RG", re.compile(r"\bR\.?G\.?\s*(?:n[º°o.]*)?\s*[:\-]?\s*[\dA-Z][\d.\-xX]{4,}", re.I)),
    ("OAB", re.compile(r"\bOAB\s*/?\s*[A-Z]{2}\s*(?:n[º°o.]*)?\s*[:\-]?\s*\d[\d.]*[A-Z]?", re.I)),
    # Formato do eproc: UF e número juntos ("SP123456").
    (
        "OAB",
        re.compile(
            r"(?<![\w/])(?:AC|AL|AM|AP|BA|CE|DF|ES|GO|MA|MG|MS|MT|PA|PB|PE|PI|PR|RJ|RN|RO|RR|"
            r"RS|SC|SE|SP|TO)\d{5,6}[A-Z]?\b"
        ),
    ),
    ("CEP", re.compile(r"\bCEP\s*[:\-]?\s*\d{2}\.?\d{3}-?\d{3}\b|(?<!\d)\d{5}-\d{3}(?!\d)", re.I)),
    (
        "TELEFONE",
        re.compile(r"(?<![\d.])(?:\(\d{2}\)\s*|\b\d{2}\s)?9?\d{4}-\d{4}(?![\d.])"),
    ),
    (
        "CONTA",
        re.compile(
            r"\b(?:ag[êe]ncia|conta(?:\s+corrente|\s+poupan[çc]a)?|c/c)\s*(?:n[º°o.]*)?\s*[:\-]?"
            r"\s*\d[\d.\-xX]{2,}",
            re.I,
        ),
    ),
    (
        "ENDERECO",
        re.compile(
            r"\b(?:Rua|R\.|Avenida|Av\.|Travessa|Tv\.|Alameda|Al\.|Estrada|Rodovia|Pra[çc]a|"
            r"Largo|Viela|Quadra|Setor)\s+[^,\n;]{2,60}?,?\s*(?:n[º°o.]*\s*)?\d+[A-Za-z]?"
            r"(?:\s*,\s*(?:apto|apartamento|casa|bloco|sala|lote)\.?\s*\w+)*",
        ),
    ),
]


@dataclass
class Pseudonimizado:
    texto: str
    substituicoes: Counter = field(default_factory=Counter)


_COMECA_COM_PAPEL = re.compile(rf"^(?:{_PAPEIS})\b", re.IGNORECASE)


def _eh_entidade(nome: str) -> bool:
    """Verdadeiro para pessoa jurídica, ente público ou expressão que não é nome."""
    return bool(
        _ENTIDADE.search(nome)
        or _NAO_NOME.match(nome)
        or _COMECA_COM_PAPEL.match(nome)
        or _COMECA_COM_CONECTIVO.match(nome)
    )


def _assinaturas(texto: str) -> list[str]:
    """Nomes numa linha de assinatura, com a OAB na linha de baixo (um ou mais, lado a lado)."""
    linhas = texto.splitlines()
    nomes = []
    for linha, seguinte in zip(linhas, linhas[1:], strict=False):
        if "[OAB]" not in seguinte:
            continue
        partes = [p for p in re.split(r"[ \t]{2,}", linha.strip()) if p]
        if partes and all(re.fullmatch(NOME_PROPRIO, p) for p in partes):
            nomes.extend(partes)
    return nomes


class _Pseudonimos:
    """Atribui [PESSOA_1], [PESSOA_2]... e repete o mesmo marcador para o mesmo nome."""

    def __init__(self) -> None:
        self._por_nome: dict[str, str] = {}

    def marcador(self, nome: str) -> str:
        chave = re.sub(r"\s+", " ", nome.strip().lower())
        if chave not in self._por_nome:
            self._por_nome[chave] = f"[PESSOA_{len(self._por_nome) + 1}]"
        return self._por_nome[chave]

    def nomes(self) -> list[str]:
        return list(self._por_nome)


def pseudonimizar(
    texto: str,
    nomes_conhecidos: Iterable[str] = (),
    usar_spacy: bool = False,
) -> Pseudonimizado:
    """Substitui dados pessoais por marcadores e conta as substituições por tipo."""
    contagem: Counter = Counter()
    pseudonimos = _Pseudonimos()

    # Documentos primeiro: evitam que números de CPF ou OAB sobrem ao lado de um nome removido.
    for tipo, padrao in _DOCUMENTOS:
        texto, n = padrao.subn(f"[{tipo}]", texto)
        contagem[tipo] += n

    nomes = {n.strip() for n in nomes_conhecidos if n and len(n.strip()) >= 4}
    nomes = {n for n in nomes if not _eh_entidade(n)}

    def registrar(nome: str, depois: str = "") -> None:
        if not (_eh_entidade(nome) or _ENTIDADE_SEGUINTE.match(depois)):
            nomes.add(nome.strip())

    for padrao in (_DEPOIS_DE_PAPEL, _QUALIFICADO, _ANTES_DE_PAPEL, _ANTES_DE_OAB, _DEPOIS_DE_OAB):
        for m in padrao.finditer(texto):
            registrar(m.group("nome"), texto[m.end("nome") : m.end("nome") + 12])
    for nome in _assinaturas(texto):
        registrar(nome)

    if usar_spacy:
        nomes |= {n for n in _nomes_spacy(texto) if not _eh_entidade(n)}

    # Nomes mais longos primeiro, para não substituir "Maria" dentro de "Maria da Silva".
    for nome in sorted(nomes, key=len, reverse=True):
        partes = r"\s+".join(map(re.escape, nome.split()))
        padrao = re.compile(rf"(?<!\w){partes}(?!\w)", re.IGNORECASE)
        texto, n = padrao.subn(pseudonimos.marcador(nome), texto)
        contagem["PESSOA"] += n

    return Pseudonimizado(texto=texto, substituicoes=+contagem)


def _nomes_spacy(texto: str) -> set[str]:
    try:
        import spacy
    except ImportError as erro:
        raise RuntimeError("usar_spacy=True exige `pip install dikemetria[nlp]`") from erro
    nlp = _carregar_spacy(spacy)
    return {ent.text for ent in nlp(texto).ents if ent.label_ == "PER" and " " in ent.text}


_SPACY_CACHE: dict[str, object] = {}


def _carregar_spacy(spacy):
    if "nlp" not in _SPACY_CACHE:
        _SPACY_CACHE["nlp"] = spacy.load("pt_core_news_sm")
    return _SPACY_CACHE["nlp"]


def residuos(texto: str) -> list[str]:
    """Documentos que ainda aparecem no texto. Lista vazia é o esperado depois de pseudonimizar."""
    return [m.group(0) for _, padrao in _DOCUMENTOS for m in padrao.finditer(texto)]
