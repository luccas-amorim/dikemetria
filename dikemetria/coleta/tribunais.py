"""Tribunais brasileiros cobertos pelas fontes nacionais (DataJud e DJEN).

O STF não está no DataJud. A sigla em minúsculas forma o índice do DataJud
(api_publica_<sigla>); em maiúsculas, é o parâmetro siglaTribunal do DJEN.
"""

from __future__ import annotations

from dataclasses import dataclass

UFS = "ac al am ap ba ce df es go ma mg ms mt pa pb pe pi pr rj rn ro rr rs sc se sp to".split()


UFS_TRF = {
    1: ("ac", "am", "ap", "ba", "df", "go", "ma", "mt", "pa", "pi", "ro", "rr", "to"),
    2: ("es", "rj"),
    3: ("ms", "sp"),
    4: ("pr", "rs", "sc"),
    5: ("al", "ce", "pb", "pe", "rn", "se"),
    6: ("mg",),
}
UFS_TRT = {
    1: ("rj",), 2: ("sp",), 3: ("mg",), 4: ("rs",), 5: ("ba",), 6: ("pe",), 7: ("ce",),
    8: ("ap", "pa"), 9: ("pr",), 10: ("df", "to"), 11: ("am", "rr"), 12: ("sc",), 13: ("pb",),
    14: ("ac", "ro"), 15: ("sp",), 16: ("ma",), 17: ("es",), 18: ("go",), 19: ("al",),
    20: ("se",), 21: ("rn",), 22: ("pi",), 23: ("mt",), 24: ("ms",),
}  # fmt: skip


@dataclass(frozen=True)
class Tribunal:
    sigla: str  # ex.: "tjsp", "trf3", "trt2", "tre-sp"
    ramo: str  # superior, federal, estadual, trabalho, eleitoral, militar

    @property
    def indice_datajud(self) -> str:
        return f"api_publica_{self.sigla}"

    @property
    def sigla_djen(self) -> str:
        return self.sigla.upper()

    @property
    def ufs(self) -> tuple[str, ...]:
        """UFs da jurisdição; vazio para os tribunais superiores."""
        if self.ramo == "superior":
            return ()
        if self.sigla.startswith("trf"):
            return UFS_TRF[int(self.sigla[3:])]
        if self.sigla.startswith("trt"):
            return UFS_TRT[int(self.sigla[3:])]
        prefixo = {"militar": "tjm", "eleitoral": "tre-"}.get(self.ramo, "tj")
        uf = self.sigla.removeprefix(prefixo)
        return ("df",) if uf == "dft" else (uf,)


def _montar() -> tuple[Tribunal, ...]:
    tribunais = [Tribunal(s, "superior") for s in ("stj", "tst", "tse", "stm")]
    tribunais += [Tribunal(f"trf{n}", "federal") for n in range(1, 7)]
    tribunais += [Tribunal("tjdft" if uf == "df" else f"tj{uf}", "estadual") for uf in UFS]
    tribunais += [Tribunal(f"trt{n}", "trabalho") for n in range(1, 25)]
    # No eleitoral o DF é "tre-df" (o índice api_publica_tre-dft não existe no DataJud).
    tribunais += [Tribunal(f"tre-{uf}", "eleitoral") for uf in UFS]
    tribunais += [Tribunal(s, "militar") for s in ("tjmmg", "tjmrs", "tjmsp")]
    return tuple(tribunais)


TRIBUNAIS = _montar()
RAMOS = tuple(dict.fromkeys(t.ramo for t in TRIBUNAIS))


def selecionar(criterios: list[str] | None) -> list[Tribunal]:
    """Seleciona por sigla ("tjsp"), por ramo ("estadual") ou todos ("todos" ou vazio)."""
    if not criterios or "todos" in criterios:
        return list(TRIBUNAIS)
    por_sigla = {t.sigla: t for t in TRIBUNAIS}
    escolhidos: dict[str, Tribunal] = {}
    for criterio in criterios:
        criterio = criterio.lower().strip()
        if criterio in RAMOS:
            escolhidos.update({t.sigla: t for t in TRIBUNAIS if t.ramo == criterio})
        elif criterio in por_sigla:
            escolhidos[criterio] = por_sigla[criterio]
        else:
            raise ValueError(f"Tribunal ou ramo desconhecido: {criterio}")
    return list(escolhidos.values())


# Código TR do número CNJ para a Justiça Estadual e Eleitoral (Resolução CNJ 65/2008, anexo).
_UF_POR_TR = (
    "ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc se sp to".split()
)


def tribunal_por_cnj(numero: str) -> str | None:
    """Sigla do tribunal a partir do segmento J.TR do número CNJ (NNNNNNN-DD.AAAA.J.TR.OOOO)."""
    import re

    m = re.search(r"\d{7}-?\d{2}\.?\d{4}\.?(\d)\.?(\d{2})\.?\d{4}", numero or "")
    if not m:
        return None
    justica, tr = int(m.group(1)), int(m.group(2))
    uf = _UF_POR_TR[tr - 1] if 1 <= tr <= len(_UF_POR_TR) else None
    if justica == 8 and uf:
        return "tjdft" if uf == "df" else f"tj{uf}"
    if justica == 6 and uf:
        return f"tre-{uf}"
    if justica == 4 and 1 <= tr <= 6:
        return f"trf{tr}"
    if justica == 5 and 1 <= tr <= 24:
        return f"trt{tr}"
    if justica == 9 and uf in {"mg", "rs", "sp"}:
        return f"tjm{uf}"
    return {3: "stj", 7: "stm"}.get(justica)
