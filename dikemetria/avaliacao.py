"""Avaliação do dispositivo de uma decisão: o que foi decidido, sobre o quê e por quê.

As regras estão descritas, com exemplos, em docs/REGRAS.md. Em resumo:

1. O dispositivo é lido em busca de **comandos decisórios** ("julgo procedente", "nego
   provimento", "homologo o acordo", "sem resolução do mérito"...). Cada comando vira um
   **capítulo**, com um rótulo, uma força (forte ou fraca) e um objeto.
2. O **objeto** de cada capítulo (ação principal, reconvenção, pedido contraposto, embargos de
   declaração, denunciação da lide, impugnação, recurso) vem das palavras logo depois do comando
   ou, se não houver, logo antes.
3. Os capítulos da ação principal e os do recurso são **agregados** separadamente, por regras
   fixas (todos procedentes = procedente; mistura = parcialmente procedente...).
4. Comandos **fracos** ("mantida a sentença", "condeno o réu") só contam quando não há nenhum
   comando forte do mesmo tipo.

Todas as regras rodam sobre o texto em minúsculas e sem acentos.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from dikemetria.limpeza import sem_acentos
from dikemetria.resultado import Resultado

R = Resultado

ACAO = "acao"
RECURSO = "recurso"
EMBARGOS_DECLARACAO = "embargos_declaracao"


@dataclass(frozen=True)
class Capitulo:
    resultado: Resultado
    objeto: str  # acao, reconvencao, pedido_contraposto, embargos_declaracao, denunciacao, ...
    forca: str  # forte ou fraca
    trecho: str
    motivo: str | None = None


@dataclass
class Avaliacao:
    resultado: Resultado  # do recurso, se a decisão julga recurso; senão, da ação principal
    resultado_acao: Resultado | None  # da ação principal, inclusive quando fixado no recurso
    tipo_decisao: str  # sentenca, acordao, decisao_monocratica, embargos_declaracao, outro
    confianca: str  # alta, media, baixa
    motivo: str | None = None
    unanimidade: bool | None = None
    capitulos: list[Capitulo] = field(default_factory=list)

    @property
    def evidencia(self) -> str:
        return " | ".join(c.trecho for c in self.capitulos)

    def como_dict(self) -> dict:
        dados = asdict(self)
        dados["resultado"] = self.resultado.value
        dados["resultado_acao"] = self.resultado_acao.value if self.resultado_acao else None
        for capitulo in dados["capitulos"]:
            capitulo["resultado"] = capitulo["resultado"].value
        return dados


@dataclass(frozen=True)
class _Regra:
    resultado: Resultado
    padrao: re.Pattern
    natureza: str  # acao ou recurso
    forca: str = "forte"
    motivo: str | None = None
    objeto: str | None = None  # objeto fixo, quando o próprio comando o revela


_DAR = r"d(?:ou|a|ar|ao|eram|emos|ando|e|eu)(?:-(?:se|lhe|lhes))?"
_NEGAR = r"neg(?:o|a|ar|am|aram|amos|ando|ue|ou)(?:-(?:se|lhe|lhes))?"
_NAO_NEGADO = r"(?<!nao )(?<!deixo de )(?<!deixa de )(?<!afasto a )"
# Embargos que são a própria ação (do executado ou de terceiro) e embargos à monitória.
_EMBARGOS_ACAO = r"embargos\s+(?:a\s+execucao|do\s+devedor|do\s+executado|de\s+terceiros?)\b"
_EMBARGOS_MONITORIOS = r"embargos\s+(?:monitorios|a\s+(?:acao\s+)?monitoria)\b"
_NAO_ED = (
    r"(?!\s+(?:a\s+execucao|do\s+devedor|do\s+executado|de\s+terceiro|monitorios|a\s+monitoria))"
)
_SENTENCA = r"(?:a\s+|na\s+integra\s+a\s+)?(?:r\.\s*|douta\s+|respeitavel\s+)?sentenca"
_ART = r"\bart(?:igo)?s?\.?\s*"


def _r(padrao: str) -> re.Pattern:
    return re.compile(padrao)


# A ordem é a prioridade: quando dois comandos se sobrepõem no texto, vale o que vem antes aqui.
REGRAS: list[_Regra] = [
    # Ação: procedência parcial antes de procedência, para "procedente em parte".
    _Regra(
        R.PARCIALMENTE_PROCEDENTE,
        _r(
            r"\b(?:parcialmente\s+procedentes?|procedentes?,?\s+(?:em\s+parte|parcialmente)|"
            r"em\s+parte,?\s+procedentes?|parcial\s+procedencia|procedencia\s+parcial)\b"
        ),
        ACAO,
    ),
    _Regra(
        R.PARCIALMENTE_PROCEDENTE,
        _r(r"\bacolh\w*(?:-(?:o|os|a|as|se))?\s+(?:em\s+parte|parcialmente)\b(?!\s+os\s+embargos)"),
        ACAO,
    ),
    # Embargos do executado ou de terceiro são a própria ação: acolhidos = procedente.
    _Regra(
        R.PARCIALMENTE_PROCEDENTE,
        _r(
            r"\bacolh\w*(?:-(?:os|se))?\s+(?:em\s+parte|parcialmente)\s+(?:os\s+)?" + _EMBARGOS_ACAO
        ),
        ACAO,
    ),
    _Regra(R.PROCEDENTE, _r(r"\bacolh\w*(?:-(?:os|se))?\s+(?:os\s+)?" + _EMBARGOS_ACAO), ACAO),
    _Regra(
        R.IMPROCEDENTE,
        _r(r"\b(?:rejeit|desacolh)\w*(?:-(?:os|se))?\s+(?:os\s+)?" + _EMBARGOS_ACAO),
        ACAO,
    ),
    # Embargos à monitória são a defesa do réu: rejeitados = procedente o pedido monitório.
    _Regra(
        R.PARCIALMENTE_PROCEDENTE,
        _r(
            r"\bacolh\w*(?:-(?:os|se))?\s+(?:em\s+parte|parcialmente)\s+(?:os\s+)?"
            + _EMBARGOS_MONITORIOS
        ),
        ACAO,
    ),
    _Regra(
        R.IMPROCEDENTE, _r(r"\bacolh\w*(?:-(?:os|se))?\s+(?:os\s+)?" + _EMBARGOS_MONITORIOS), ACAO
    ),
    _Regra(
        R.PROCEDENTE,
        _r(r"\b(?:rejeit|desacolh)\w*(?:-(?:os|se))?\s+(?:os\s+)?" + _EMBARGOS_MONITORIOS),
        ACAO,
    ),
    # Mandado de segurança.
    _Regra(
        R.PARCIALMENTE_PROCEDENTE,
        _r(
            r"\bconced\w*(?:-se)?\s+(?:em\s+parte|parcialmente)\s+a\s+seguranca|"
            r"\bseguranca\s+(?:parcialmente\s+concedida|concedida\s+em\s+parte)"
        ),
        ACAO,
    ),
    _Regra(
        R.PROCEDENTE,
        _r(r"\bconced\w*(?:-se)?\s+(?:a\s+)?seguranca|\bseguranca\s+concedida"),
        ACAO,
    ),
    _Regra(
        R.IMPROCEDENTE,
        _r(r"\bdeneg\w*(?:-se)?\s+(?:a\s+)?seguranca|\bseguranca\s+denegada"),
        ACAO,
    ),
    # Ação penal: absolvição = improcedência da pretensão punitiva.
    _Regra(R.IMPROCEDENTE, _r(r"\babsolv\w*(?:-(?:o|a|os|as|se))?\b"), ACAO),
    _Regra(
        R.PROCEDENTE,
        _r(
            r"\bcondeno-?(?:o|a|os|as)?\s+(?:o\s+|a\s+)?(?:reu|re|acusad[oa]s?|denunciad[oa]s?)?\s*"
            r"(?:como\s+)?incurs[oa]s?\b"
        ),
        ACAO,
    ),
    # Mérito resolvido por prescrição, decadência, reconhecimento ou renúncia (art. 487, II e III).
    _Regra(
        R.IMPROCEDENTE,
        _r(
            _NAO_NEGADO
            + r"\b(?:pronunci|reconhec|declar|acolh|decret)\w*(?:-se)?\s+(?:de\s+oficio\s+)?"
            r"(?:a\s+)?(?:ocorrencia\s+da\s+)?(?:prejudicial\s+(?:de\s+merito\s+)?(?:de\s+|da\s+)?)?"
            r"prescricao"
        ),
        ACAO,
        motivo="prescrição",
    ),
    _Regra(
        R.IMPROCEDENTE,
        _r(
            _NAO_NEGADO
            + r"\b(?:pronunci|reconhec|declar|acolh|decret)\w*(?:-se)?\s+(?:de\s+oficio\s+)?"
            r"(?:a\s+)?(?:ocorrencia\s+da\s+)?decadencia"
        ),
        ACAO,
        motivo="decadência",
    ),
    _Regra(R.IMPROCEDENTE, _r(_ART + r"487,?\s*(?:inciso\s+)?ii\b"), ACAO, motivo="art. 487, II"),
    _Regra(
        R.PROCEDENTE,
        _r(
            r"\breconhecimento\s+(?:juridico\s+)?(?:da\s+procedencia\s+)?do\s+pedido|"
            + _ART
            + r"487,?\s*(?:inciso\s+)?iii,?\s*(?:alinea\s+)?\W?a\b"
        ),
        ACAO,
        motivo="reconhecimento do pedido",
    ),
    _Regra(
        R.IMPROCEDENTE,
        _r(
            r"\brenuncia\s+(?:a\s+pretensao|ao\s+direito)|"
            + _ART
            + r"487,?\s*(?:inciso\s+)?iii,?\s*(?:alinea\s+)?\W?c\b"
        ),
        ACAO,
        motivo="renúncia à pretensão",
    ),
    _Regra(
        R.HOMOLOGACAO_ACORDO,
        _r(
            r"\bhomolog\w*(?:-se)?\b[^.;]{0,120}?\b(?:acordo|transacao|composicao|conciliacao|"
            r"autocomposicao)\b|" + _ART + r"487,?\s*(?:inciso\s+)?iii,?\s*(?:alinea\s+)?\W?b\b"
        ),
        ACAO,
    ),
    # Extinção sem resolução do mérito (art. 485).
    _Regra(
        R.EXTINTO_SEM_MERITO,
        _r(r"\bhomolog\w*(?:-se)?\b[^.;]{0,60}?\bdesistencia\b|\bdesistencia\s+da\s+acao\b"),
        ACAO,
        motivo="desistência (art. 485, VIII)",
    ),
    _Regra(
        R.EXTINTO_SEM_MERITO,
        _r(r"\bsem\s+(?:resolucao|julgamento|exame|apreciacao|analise)\s+d[oe]\s+merito"),
        ACAO,
    ),
    _Regra(R.EXTINTO_SEM_MERITO, _r(_ART + r"485\b"), ACAO),
    _Regra(
        R.EXTINTO_SEM_MERITO,
        _r(
            r"\bindefiro\s+(?:a\s+)?(?:peticao\s+)?inicial|\bindeferimento\s+da\s+(?:peticao\s+)?"
            r"inicial"
        ),
        ACAO,
        motivo="indeferimento da inicial (art. 485, I)",
    ),
    _Regra(
        R.EXTINTO_SEM_MERITO,
        _r(
            r"\b(?:julgo|declaro|decreto|julga-se)\s+extint[oa]\s+(?:o\s+)?(?:processo|feito|acao)\b"
            r"(?![^.;]{0,80}\bcom\s+(?:resolucao|julgamento|exame)\b)"
        ),
        ACAO,
        forca="fraca",
    ),
    # Improcedência e procedência.
    _Regra(
        R.IMPROCEDENTE,
        _r(r"\bimprocedentes?\b|\bimprocedencia\s+d[oa]s?\s+(?:pedidos?|acao|demanda)\b"),
        ACAO,
    ),
    _Regra(
        R.IMPROCEDENTE,
        _r(
            r"\b(?:rejeit|desacolh)\w*(?:-(?:o|os|se))?\s+(?:integralmente\s+|totalmente\s+)?"
            r"(?:o|os)\s+pedidos?\b|\bnao\s+acolh\w*\s+(?:o|os)\s+pedidos?\b"
        ),
        ACAO,
    ),
    _Regra(
        R.PROCEDENTE,
        _r(r"(?<![\w-])procedentes?\b|\bprocedencia\s+d[oa]s?\s+(?:pedidos?|acao|demanda)\b"),
        ACAO,
    ),
    _Regra(
        R.PROCEDENTE,
        _r(
            r"\bacolh\w*(?:-(?:o|os|se))?\s+(?:integralmente\s+|totalmente\s+)?(?:o|os)\s+"
            r"pedidos?\b"
        ),
        ACAO,
    ),
    _Regra(
        R.PROCEDENTE,
        _r(r"\bcondeno\s+(?:o|a|os|as)\s+(?:re[ua]?s?|requerid[oa]s?|demandad[oa]s?)\b"),
        ACAO,
        forca="fraca",
    ),
    # Embargos de declaração: o objeto é fixo.
    _Regra(
        R.PARCIALMENTE_PROVIDO,
        _r(
            r"\bacolh\w*(?:-(?:os|se))?\s+(?:em\s+parte|parcialmente)\s+(?:os\s+)?(?:presentes\s+)?"
            r"embargos\b"
        ),
        RECURSO,
        objeto=EMBARGOS_DECLARACAO,
    ),
    _Regra(
        R.PROVIDO,
        _r(r"\bacolh\w*(?:-(?:os|se))?\s+(?:os\s+)?(?:presentes\s+)?embargos\b" + _NAO_ED),
        RECURSO,
        objeto=EMBARGOS_DECLARACAO,
    ),
    _Regra(
        R.NAO_PROVIDO,
        _r(
            r"\b(?:rejeit|desacolh)\w*(?:-(?:os|se))?\s+(?:os\s+)?(?:presentes\s+)?embargos\b"
            + _NAO_ED
        ),
        RECURSO,
        objeto=EMBARGOS_DECLARACAO,
    ),
    # Recursos.
    _Regra(
        R.PARCIALMENTE_PROVIDO,
        _r(
            rf"\b{_DAR}\s+(?:parcial\s+provimento|provimento\s+parcial|provimento\s+em\s+parte)\b|"
            r"\bparcialmente\s+provid[oa]s?\b|\bprovid[oa]s?,?\s+(?:em\s+parte|parcialmente)\b|"
            r"\bprovimento\s+parcial\b|\bparcial\s+provimento\b"
        ),
        RECURSO,
    ),
    _Regra(
        R.NAO_PROVIDO,
        _r(
            rf"\b{_NEGAR}\s+(?:integral\s+)?provimento\b|\bnao\s+provid[oa]s?\b|"
            r"\b(?:des|im)provid[oa]s?\b|\b(?:des|im)provimento\b"
        ),
        RECURSO,
    ),
    _Regra(
        R.PROVIDO,
        _r(rf"\b{_DAR}\s+(?:integral\s+|total\s+)?provimento\b|\bprovid[oa]s?\b"),
        RECURSO,
    ),
    _Regra(
        R.PROVIDO,
        _r(r"\b(?:anul|cass|desconstitu)\w*(?:-se)?\s+" + _SENTENCA + r"\b"),
        RECURSO,
        motivo="anulação da sentença",
    ),
    _Regra(
        R.NAO_CONHECIDO,
        _r(
            r"\bnao\s+(?:se\s+)?conhe(?:co|ce|cer|ceram|cemos|cido|cida|ceu)\b"
            r"(?!\s+(?:de\s+)?(?:parte|em\s+parte|parcialmente))"
        ),
        RECURSO,
    ),
    _Regra(
        R.NAO_CONHECIDO,
        _r(
            r"\b(?:julg\w*\s+)?prejudicad[oa]s?\s+(?:o\s+|os\s+)?(?:recursos?|apelo|apelac\w+)|"
            r"\b(?:recursos?|apelo|apelacao)\s+prejudicad[oa]s?\b"
        ),
        RECURSO,
        motivo="recurso prejudicado",
    ),
    # Comandos fracos do recurso: só valem sem comando forte.
    _Regra(
        R.PARCIALMENTE_PROVIDO,
        _r(
            r"\breform\w*(?:-se)?\s+(?:em\s+parte|parcialmente)\s+" + _SENTENCA + r"|"
            r"\bsentenca\s+(?:parcialmente\s+reformada|reformada\s+em\s+parte)"
        ),
        RECURSO,
        forca="fraca",
    ),
    _Regra(
        R.PROVIDO,
        _r(r"\breform\w*(?:-se)?\s+(?:integralmente\s+)?" + _SENTENCA + r"|\bsentenca\s+reformada"),
        RECURSO,
        forca="fraca",
    ),
    _Regra(
        R.NAO_PROVIDO,
        _r(
            r"\b(?:mantid[oa]|mantenho|mantem-se|mantiveram|manter|confirm\w*)\s+(?:-se\s+)?"
            + _SENTENCA
            + r"|\bsentenca\s+(?:mantida|confirmada)"
        ),
        RECURSO,
        forca="fraca",
    ),
]

# Objetos reconhecidos na vizinhança de um comando, em ordem de prioridade.
_OBJETOS: list[tuple[str, re.Pattern]] = [
    ("reconvencao", _r(r"reconven")),
    ("pedido_contraposto", _r(r"pedido\s+contraposto|contrapedido")),
    (EMBARGOS_DECLARACAO, _r(r"embargos\s+de\s+declaracao|declaratorios|aclaratorios")),
    ("denunciacao", _r(r"denuncia(?:cao|d)|lide\s+secundaria|chamamento\s+ao\s+processo")),
    ("impugnacao", _r(r"\bimpugnac")),
    ("incidente", _r(r"\bincidente\b|\bexcecao\s+de\b|\bhabilitacao\b")),
]

_OBJETO_PRINCIPAL = _r(r"\b(?:pedidos?|acao|demanda|pretens\w+|inicial|lide)\b")
_CONHECIMENTO_PARCIAL = _r(
    r"\bnao\s+conhe\w*\s+(?:de\s+)?(?:parte|em\s+parte)|\bconhe\w*\s+(?:em\s+parte|parcialmente)|"
    r"\bna\s+parte\s+conhecida\b"
)

_INCISOS_485 = {
    "i": "indeferimento da inicial",
    "ii": "paralisação por negligência das partes",
    "iii": "abandono da causa",
    "iv": "falta de pressuposto processual",
    "v": "perempção, litispendência ou coisa julgada",
    "vi": "ilegitimidade ou falta de interesse",
    "vii": "convenção de arbitragem",
    "viii": "desistência",
    "ix": "ação intransmissível",
    "x": "outros casos legais",
}
_PALAVRAS_485 = [
    ("vi", _r(r"ilegitimidade|interesse\s+(?:de\s+agir|processual)|carencia\s+(?:de|da)\s+acao")),
    ("v", _r(r"litispendencia|coisa\s+julgada|perempcao")),
    ("iii", _r(r"abandono")),
    ("viii", _r(r"desistencia")),
    ("vii", _r(r"arbitragem|compromisso\s+arbitral")),
    ("iv", _r(r"pressupostos?\s+(?:processua|de\s+constituicao)")),
    ("i", _r(r"inepcia|indefir\w*\s+(?:a\s+)?(?:peticao\s+)?inicial")),
]

_UNANIME = _r(r"\bpor\s+unanimidade\b|\bv\.\s*u\.|\bvotacao\s+unanime\b|\bunanimemente\b")
_MAIORIA = _r(r"\bpor\s+maioria\b|\bvencid[oa]s?\s+(?:o|a|os|as)\s+\w+|\bmaioria\s+de\s+votos\b")
_ACORDAO = _r(
    r"\bacord(?:am|ao)\b|\bvoto\s+(?:n|do\s+relator|condutor)|\brelator(?:a)?\b|"
    r"\bturma\s+recursal\b|\bcamara\s+(?:de\s+direito|civel|criminal)|\bapelacao\s+civel\b"
)
_MONOCRATICA = _r(r"\bdecisao\s+monocratica\b|\bmonocraticamente\b|\bart\.?\s*932\b")
_SENTENCA_CABECALHO = _r(r"\bsentenca\b")
_ED_CABECALHO = _r(r"\bembargos\s+de\s+declaracao\b")


def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos, espaços colapsados: a base de todas as regras."""
    return re.sub(r"\s+", " ", sem_acentos(texto.lower())).strip()


def _sobrepoe(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def _comandos(texto: str) -> list[tuple[int, int, _Regra]]:
    """Comandos decisórios sem sobreposição; a regra de maior prioridade fica com o trecho."""
    aceitos: list[tuple[int, int, _Regra]] = []
    for regra in REGRAS:
        for m in regra.padrao.finditer(texto):
            span = m.span()
            if not any(_sobrepoe(span, (ini, fim)) for ini, fim, _ in aceitos):
                aceitos.append((span[0], span[1], regra))
    return sorted(aceitos, key=lambda item: item[0])


def _objeto(texto: str, inicio: int, fim: int, anterior: int, proximo: int) -> str | None:
    """Objeto do comando: palavras logo depois (até o próximo comando ou fim da frase); se não
    houver, logo antes (desde o comando anterior ou o início da frase)."""
    depois = texto[fim : min(fim + 110, proximo)]
    depois = re.split(r"[.;]", depois, maxsplit=1)[0]
    antes = texto[max(anterior, inicio - 110) : inicio]
    antes = re.split(r"[.;:]", antes)[-1]
    for nome, padrao in _OBJETOS:
        if padrao.search(depois):
            return nome
    if _OBJETO_PRINCIPAL.search(depois):
        return None  # "procedente o pedido inicial": o próprio comando nomeia a ação principal
    for nome, padrao in _OBJETOS:
        if padrao.search(antes):
            return nome
    return None


def _motivo_485(texto: str) -> str | None:
    m = re.search(r"485,?\s*(?:caput\s*,?\s*)?(?:inciso\s+)?\b([ivx]+)\b", texto)
    if m and m.group(1) in _INCISOS_485:
        return f"{_INCISOS_485[m.group(1)]} (art. 485, {m.group(1).upper()})"
    for inciso, padrao in _PALAVRAS_485:
        if padrao.search(texto):
            return f"{_INCISOS_485[inciso]} (art. 485, {inciso.upper()})"
    return None


def capitulos(dispositivo: str) -> list[Capitulo]:
    texto = normalizar(dispositivo)
    comandos = _comandos(texto)
    resultado = []
    for i, (inicio, fim, regra) in enumerate(comandos):
        anterior = comandos[i - 1][1] if i else 0
        proximo = comandos[i + 1][0] if i + 1 < len(comandos) else len(texto)
        objeto = regra.objeto or _objeto(texto, inicio, fim, anterior, proximo)
        if regra.natureza == RECURSO and objeto != EMBARGOS_DECLARACAO:
            objeto = RECURSO  # recurso sobre a reconvenção continua sendo recurso
        elif objeto is None:
            objeto = ACAO
        motivo = regra.motivo
        if regra.resultado == R.EXTINTO_SEM_MERITO and motivo is None:
            motivo = _motivo_485(texto)
        resultado.append(Capitulo(regra.resultado, objeto, regra.forca, texto[inicio:fim], motivo))
    return resultado


def _validos(caps: list[Capitulo]) -> tuple[list[Capitulo], bool]:
    """Fortes, se houver; senão, fracos. Devolve também se recorreu aos fracos."""
    fortes = [c for c in caps if c.forca == "forte"]
    return (fortes, False) if fortes else (caps, bool(caps))


def agregar_acao(caps: list[Capitulo]) -> tuple[Resultado, str | None, str]:
    """Resultado da ação principal a partir dos seus capítulos: (resultado, motivo, confiança)."""
    validos, fraco = _validos(caps)
    if not validos:
        return R.INDETERMINADO, None, "baixa"
    rotulos = {c.resultado for c in validos}
    motivos = [c.motivo for c in validos if c.motivo]
    merito = rotulos & {R.PROCEDENTE, R.PARCIALMENTE_PROCEDENTE, R.IMPROCEDENTE}
    confianca = "baixa" if fraco else "alta"

    if merito:
        if merito == {R.PROCEDENTE}:
            resultado = R.PROCEDENTE
        elif merito == {R.IMPROCEDENTE}:
            resultado = R.IMPROCEDENTE
        else:
            resultado = R.PARCIALMENTE_PROCEDENTE
            if R.PARCIALMENTE_PROCEDENTE not in merito:
                motivos.append("capítulos com resultados distintos")
                confianca = "media" if not fraco else confianca
        if rotulos - merito:
            motivos.append("extinção ou acordo parcial")
            confianca = "media" if not fraco else confianca
    elif R.HOMOLOGACAO_ACORDO in rotulos:
        resultado = R.HOMOLOGACAO_ACORDO
    elif R.EXTINTO_SEM_MERITO in rotulos:
        resultado = R.EXTINTO_SEM_MERITO
    else:
        resultado = R.INDETERMINADO

    if (
        any(c.motivo for c in validos)
        and confianca == "alta"
        and resultado
        in (
            R.PROCEDENTE,
            R.IMPROCEDENTE,
        )
    ):
        confianca = "media"  # mérito resolvido por regra indireta (prescrição, art. 487...)
    motivo = "; ".join(dict.fromkeys(motivos)) or None
    return resultado, motivo, confianca


def agregar_recurso(caps: list[Capitulo]) -> tuple[Resultado, str | None, str]:
    validos, fraco = _validos(caps)
    if not validos:
        return R.INDETERMINADO, None, "baixa"
    rotulos = {c.resultado for c in validos}
    motivos = [c.motivo for c in validos if c.motivo]
    if len(rotulos) > 1 and R.NAO_CONHECIDO in rotulos:
        rotulos.discard(R.NAO_CONHECIDO)
        motivos.append("conhecimento parcial ou recurso não conhecido ao lado de outro")
    if len(rotulos) == 1:
        resultado = rotulos.pop()
        confianca = "baixa" if fraco else ("media" if motivos else "alta")
    else:
        resultado = R.INDETERMINADO
        motivos.append("recursos com resultados distintos")
        confianca = "baixa"
    return resultado, "; ".join(dict.fromkeys(motivos)) or None, confianca


def tipo_decisao(texto: str, caps: list[Capitulo]) -> str:
    cabecalho = normalizar(texto[:4000])
    objetos = {c.objeto for c in caps}
    if objetos and objetos <= {EMBARGOS_DECLARACAO} or _ED_CABECALHO.search(cabecalho[:400]):
        return EMBARGOS_DECLARACAO
    if _MONOCRATICA.search(cabecalho):
        return "decisao_monocratica"
    if RECURSO in objetos or _ACORDAO.search(cabecalho):
        return "acordao"
    if ACAO in objetos or _SENTENCA_CABECALHO.search(cabecalho):
        return "sentenca"
    return "outro"


def unanimidade(texto: str) -> bool | None:
    base = normalizar(texto)
    if _MAIORIA.search(base):
        return False
    if _UNANIME.search(base):
        return True
    return None


def avaliar_dispositivo(dispositivo: str, texto_completo: str | None = None) -> Avaliacao:
    """Avalia o dispositivo. `texto_completo` ajuda a reconhecer o tipo de decisão e a votação."""
    caps = capitulos(dispositivo)
    acao = [c for c in caps if c.objeto == ACAO]
    recurso = [c for c in caps if c.objeto == RECURSO]
    completo = texto_completo or dispositivo

    resultado_acao, motivo_acao, confianca_acao = agregar_acao(acao)
    if recurso:
        resultado, motivo, confianca = agregar_recurso(recurso)
        if _CONHECIMENTO_PARCIAL.search(normalizar(dispositivo)):
            motivo = "; ".join(filter(None, [motivo, "conhecimento parcial"]))
        if motivo_acao and resultado_acao != R.INDETERMINADO:
            motivo = "; ".join(filter(None, [motivo, f"ação: {motivo_acao}"]))
    else:
        resultado, motivo, confianca = resultado_acao, motivo_acao, confianca_acao

    return Avaliacao(
        resultado=resultado,
        resultado_acao=resultado_acao if acao else None,
        tipo_decisao=tipo_decisao(completo, caps),
        confianca=confianca,
        motivo=motivo,
        unanimidade=unanimidade(completo) if recurso or texto_completo else None,
        capitulos=caps,
    )


def avaliar(texto: str) -> tuple[Avaliacao, str]:
    """Avalia a decisão inteira. Devolve a avaliação e o dispositivo usado (para o cálculo).

    Em acórdãos, o parágrafo "ACORDAM" é a decisão do colegiado. Se o resultado do recurso nele
    for determinado e diferente do resultado do voto (relator vencido, por exemplo), prevalece o
    "ACORDAM", e o resultado da ação só é mantido se o próprio "ACORDAM" o disser.
    """
    from dikemetria.estrutura import dividir

    secoes = dividir(texto)
    avaliacao = avaliar_dispositivo(secoes.dispositivo, texto)
    if not secoes.decisao_colegiada:
        return avaliacao, secoes.dispositivo

    colegiada = avaliar_dispositivo(secoes.decisao_colegiada, texto)
    if colegiada.resultado == R.INDETERMINADO or not any(
        c.objeto in (RECURSO, EMBARGOS_DECLARACAO) for c in colegiada.capitulos
    ):
        return avaliacao, secoes.dispositivo
    if colegiada.resultado == avaliacao.resultado:
        return avaliacao, secoes.dispositivo
    colegiada.motivo = "; ".join(
        filter(None, [colegiada.motivo, "prevalece o ACORDAM sobre o voto"])
    )
    colegiada.tipo_decisao = (
        avaliacao.tipo_decisao if avaliacao.tipo_decisao != "outro" else (colegiada.tipo_decisao)
    )
    return colegiada, secoes.decisao_colegiada
