"""Relatório público de um recorte (Fase 5): HTML autocontido, tabelas CSV e dicionário de dados.

Só sai daqui o agregado: nenhum texto de decisão, nenhum número de processo, nenhum grupo com
menos de `politica.MINIMO_PUBLICAVEL` casos.
"""

from __future__ import annotations

import csv
import html
import json
import math
from datetime import UTC, datetime
from pathlib import Path

from dikemetria import __version__, jurimetria, politica
from dikemetria.consolidacao import consolidar
from dikemetria.corpus import Corpus

ROTULOS = {
    "procedente": "Procedente",
    "parcialmente_procedente": "Parcialmente procedente",
    "improcedente": "Improcedente",
    "extinto_sem_merito": "Extinto sem mérito",
    "homologacao_acordo": "Acordo homologado",
    "provido": "Provido",
    "parcialmente_provido": "Parcialmente provido",
    "nao_provido": "Não provido",
    "nao_conhecido": "Não conhecido",
    "indeterminado": "Indeterminado",
}

LARGURA = 720
ROTULO_X = 230
ALTURA_LINHA = 28


def _e(texto) -> str:
    return html.escape(str(texto), quote=True)


def _pct(valor: float | None) -> str:
    return "—" if valor is None or math.isnan(valor) else f"{valor * 100:.1f}%".replace(".", ",")


def _num(valor: float | int | None) -> str:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "—"
    return f"{valor:,.0f}".replace(",", ".")


def _curto(texto: str, limite: int = 30) -> str:
    return texto if len(texto) <= limite else texto[: limite - 1] + "…"


def _barra(x0: float, y: float, largura: float, altura: float, classe: str, titulo: str) -> str:
    """Barra horizontal com a ponta arredondada (4px) e base reta."""
    if largura <= 0:
        return ""
    r = min(4, largura, altura / 2)
    d = (
        f"M{x0:.1f},{y:.1f}h{largura - r:.1f}a{r},{r} 0 0 1 {r},{r}v{altura - 2 * r:.1f}"
        f"a{r},{r} 0 0 1 -{r},{r}h-{largura - r:.1f}z"
    )
    return f'<path class="{classe}" d="{d}"><title>{_e(titulo)}</title></path>'


def _barra_esquerda(x0: float, y: float, largura: float, altura: float, classe: str, titulo: str):
    """Barra que cresce para a esquerda a partir de x0 (gráfico divergente)."""
    if largura <= 0:
        return ""
    r = min(4, largura, altura / 2)
    d = (
        f"M{x0:.1f},{y:.1f}h-{largura - r:.1f}a{r},{r} 0 0 0 -{r},{r}v{altura - 2 * r:.1f}"
        f"a{r},{r} 0 0 0 {r},{r}h{largura - r:.1f}z"
    )
    return f'<path class="{classe}" d="{d}"><title>{_e(titulo)}</title></path>'


def _svg(altura: float, corpo: str, descricao: str) -> str:
    return (
        f'<svg viewBox="0 0 {LARGURA} {altura:.0f}" role="img" aria-label="{_e(descricao)}" '
        f'preserveAspectRatio="xMinYMin meet">{corpo}</svg>'
    )


def svg_autonomo(svg: str) -> str:
    """Gráfico SVG avulso, com as cores do tema claro embutidas."""
    estilo = (
        "text{font:13px system-ui,sans-serif;fill:#52514e}.valor{fill:#0b0b0b}"
        ".serie-1{fill:#2a78d6}.base{stroke:#8a8984}"
    )
    svg = svg.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
    fundo = '<rect width="100%" height="100%" fill="#fcfcfb"/>'
    return svg.replace(">", f"><style>{estilo}</style>{fundo}", 1)


def _eixo_percentual(x0: float, x1: float, y0: float, y1: float) -> str:
    partes = []
    for i in range(0, 5):
        x = x0 + (x1 - x0) * i / 4
        partes.append(f'<line class="grade" x1="{x:.1f}" x2="{x:.1f}" y1="{y0}" y2="{y1}"/>')
        partes.append(
            f'<text class="eixo" x="{x:.1f}" y="{y1 + 16}" text-anchor="middle">{i * 25}%</text>'
        )
    return "".join(partes)


def grafico_barras(linhas: list[tuple[str, float, str]], descricao: str) -> str:
    """Barras horizontais de uma série: (rótulo, proporção 0–1, texto do valor)."""
    x0, x1 = ROTULO_X, LARGURA - 120
    altura = len(linhas) * ALTURA_LINHA + 10
    maximo = max((v for _, v, _ in linhas), default=1) or 1
    partes = []
    for i, (rotulo, valor, texto) in enumerate(linhas):
        y = 5 + i * ALTURA_LINHA
        largura = (x1 - x0) * valor / maximo
        partes.append(
            f'<text class="rotulo" x="{x0 - 10}" y="{y + 17}" text-anchor="end">'
            f"<title>{_e(rotulo)}</title>{_e(_curto(rotulo))}</text>"
        )
        partes.append(_barra(x0, y + 4, largura, 18, "serie-1", f"{rotulo}: {texto}"))
        partes.append(
            f'<text class="valor" x="{x0 + largura + 6:.1f}" y="{y + 17}">{_e(texto)}</text>'
        )
    partes.append(f'<line class="base" x1="{x0}" x2="{x0}" y1="0" y2="{altura}"/>')
    return _svg(altura, "".join(partes), descricao)


def grafico_intervalos(linhas: list[dict], campo: str, descricao: str) -> str:
    """Ponto (proporção) com bigodes do IC de 95%, uma linha por grupo."""
    x0, x1 = ROTULO_X, LARGURA - 20
    altura = len(linhas) * ALTURA_LINHA + 30
    partes = [_eixo_percentual(x0, x1, 0, altura - 26)]
    for i, linha in enumerate(linhas):
        y = 5 + i * ALTURA_LINHA + 13
        p, lo, hi = linha[campo], linha[f"{campo}_ic_inf"], linha[f"{campo}_ic_sup"]
        dica = (
            f"{linha['grupo']}: {_pct(p)} (IC 95%: {_pct(lo)} a {_pct(hi)}; "
            f"n = {_num(linha['merito'] if campo != 'provimento' else linha['recursos'])})"
        )
        xp, xl, xh = (x0 + (x1 - x0) * v for v in (p, lo, hi))
        partes.append(
            f'<text class="rotulo" x="{x0 - 10}" y="{y + 4}" text-anchor="end">'
            f"<title>{_e(linha['grupo'])}</title>{_e(_curto(linha['grupo']))}</text>"
        )
        partes.append(
            f'<g class="alvo"><title>{_e(dica)}</title>'
            f'<rect x="{x0}" y="{y - 13}" width="{x1 - x0}" height="{ALTURA_LINHA}" '
            f'fill="transparent"/>'
            f'<line class="ic" x1="{xl:.1f}" x2="{xh:.1f}" y1="{y}" y2="{y}"/>'
            f'<circle class="ponto" cx="{xp:.1f}" cy="{y}" r="5"/></g>'
        )
    return _svg(altura, "".join(partes), descricao)


def grafico_divergente(acolhido: list[dict], rejeitado: list[dict], descricao: str) -> str:
    """Palavras típicas de cada lado: barras para a direita (acolhido) e esquerda (rejeitado)."""
    meio = LARGURA / 2
    metade = meio - 130
    n = max(len(acolhido), len(rejeitado))
    altura = n * 24 + 40
    maximo = max((abs(item["z"]) for item in acolhido + rejeitado), default=1) or 1
    partes = [
        f'<text class="legenda" x="{meio + 8}" y="14">'
        f'<tspan class="chave-1">■</tspan> mais típicas de acolhidos</text>',
        f'<text class="legenda" x="{meio - 8}" y="14" text-anchor="end">mais típicas de rejeitados '
        f'<tspan class="chave-2">■</tspan></text>',
        f'<line class="base" x1="{meio}" x2="{meio}" y1="24" y2="{altura}"/>',
    ]
    for i in range(n):
        y = 30 + i * 24
        if i < len(acolhido):
            item = acolhido[i]
            largura = metade * item["z"] / maximo
            partes.append(
                _barra(
                    meio + 1, y, largura, 16, "serie-1", f"{item['palavra']}: z = {item['z']:.1f}"
                )
            )
            partes.append(
                f'<text class="rotulo" x="{meio + largura + 6:.1f}" y="{y + 13}">'
                f"{_e(item['palavra'])}</text>"
            )
        if i < len(rejeitado):
            item = rejeitado[i]
            largura = metade * abs(item["z"]) / maximo
            partes.append(
                _barra_esquerda(
                    meio - 1, y, largura, 16, "serie-2", f"{item['palavra']}: z = {item['z']:.1f}"
                )
            )
            partes.append(
                f'<text class="rotulo" x="{meio - largura - 6:.1f}" y="{y + 13}" '
                f'text-anchor="end">{_e(item["palavra"])}</text>'
            )
    return _svg(altura, "".join(partes), descricao)


def grafico_halteres(linhas: list[dict], descricao: str) -> str:
    """Proporção de documentos acolhidos e rejeitados que citam cada norma."""
    x0, x1 = ROTULO_X, LARGURA - 20
    altura = len(linhas) * ALTURA_LINHA + 56
    partes = [
        f'<text class="legenda" x="{x0}" y="14"><tspan class="chave-1">●</tspan> em acolhidos'
        f'   <tspan class="chave-2">●</tspan> em rejeitados</text>',
        _eixo_percentual(x0, x1, 24, altura - 26),
    ]
    for i, linha in enumerate(linhas):
        y = 30 + i * ALTURA_LINHA + 13
        a, r = linha["em_acolhidos"] or 0, linha["em_rejeitados"] or 0
        xa, xr = x0 + (x1 - x0) * a, x0 + (x1 - x0) * r
        dica = (
            f"{linha['citacao']}: {_pct(a)} dos acolhidos, {_pct(r)} dos rejeitados "
            f"({_num(linha['documentos'])} documentos)"
        )
        partes.append(
            f'<text class="rotulo" x="{x0 - 10}" y="{y + 4}" text-anchor="end">'
            f"{_e(_curto(linha['citacao']))}</text>"
        )
        partes.append(
            f'<g class="alvo"><title>{_e(dica)}</title>'
            f'<rect x="{x0}" y="{y - 13}" width="{x1 - x0}" height="{ALTURA_LINHA}" '
            f'fill="transparent"/>'
            f'<line class="ic" x1="{min(xa, xr):.1f}" x2="{max(xa, xr):.1f}" '
            f'y1="{y}" y2="{y}"/>'
            f'<circle class="ponto-2" cx="{xr:.1f}" cy="{y}" r="5"/>'
            f'<circle class="ponto" cx="{xa:.1f}" cy="{y}" r="5"/></g>'
        )
    return _svg(altura, "".join(partes), descricao)


def grafico_faixas(linhas: list[dict], descricao: str, unidade: str = "R$") -> str:
    """Mediana (ponto) e intervalo entre o 1º e o 3º quartis (traço), em valores absolutos."""
    x0, x1 = ROTULO_X, LARGURA - 20
    altura = len(linhas) * ALTURA_LINHA + 30
    maximo = max((x["q3"] for x in linhas), default=1) or 1
    passo = 10 ** max(0, len(str(int(maximo))) - 1)
    topo = math.ceil(maximo / passo) * passo
    partes = []
    for i in range(5):
        valor = topo * i / 4
        x = x0 + (x1 - x0) * i / 4
        partes.append(f'<line class="grade" x1="{x:.1f}" x2="{x:.1f}" y1="0" y2="{altura - 26}"/>')
        partes.append(
            f'<text class="eixo" x="{x:.1f}" y="{altura - 10}" text-anchor="middle">'
            f"{_e(_num(valor))}</text>"
        )
    for i, linha in enumerate(linhas):
        y = 5 + i * ALTURA_LINHA + 13
        xm, xa, xb = (x0 + (x1 - x0) * linha[k] / topo for k in ("mediana", "q1", "q3"))
        dica = (
            f"{linha['grupo']}: mediana {unidade} {_num(linha['mediana'])}; metade central entre "
            f"{unidade} {_num(linha['q1'])} e {unidade} {_num(linha['q3'])} (n = {linha['n']})"
        )
        partes.append(
            f'<text class="rotulo" x="{x0 - 10}" y="{y + 4}" text-anchor="end">'
            f"{_e(_curto(linha['grupo']))}</text>"
            f'<g class="alvo"><title>{_e(dica)}</title>'
            f'<rect x="{x0}" y="{y - 13}" width="{x1 - x0}" height="{ALTURA_LINHA}" '
            f'fill="transparent"/>'
            f'<line class="ic" x1="{xa:.1f}" x2="{xb:.1f}" y1="{y}" y2="{y}"/>'
            f'<circle class="ponto" cx="{xm:.1f}" cy="{y}" r="5"/></g>'
        )
    return _svg(altura, "".join(partes), descricao)


def _secoes_calculo(m: dict) -> list[str]:
    """Reforma em 2º grau, motivos de extinção, valores e parâmetros de cálculo."""
    secoes = []
    reforma = m["reforma"]
    if reforma["pares"]:
        rotulo = lambda r: ROTULOS.get(r, r)  # noqa: E731
        cruzamento = [
            {**x, "sentenca": rotulo(x["sentenca"]), "recurso": rotulo(x["recurso"])}
            for x in reforma["cruzamento"]
        ]
        finais = [
            {**x, "sentenca": rotulo(x["sentenca"]), "final": rotulo(x["final"])}
            for x in reforma["resultado_final"]
        ]
        secoes.append(
            '<section class="figura"><h3>Reforma em segundo grau</h3>'
            f'<p class="sub">{_num(reforma["pares"])} processos com sentença de mérito e '
            f"acórdão. Taxa de reforma (recurso provido ou parcialmente provido): "
            f"{_pct(reforma['taxa_reforma'])}. O resultado final infere quem recorreu pela "
            "sucumbência; ver a metodologia.</p>"
            + tabela(
                cruzamento,
                [("sentenca", "Sentença", "txt"), ("recurso", "Recurso", "txt"), ("n", "n", "num")],
            )
            + tabela(
                finais,
                [
                    ("sentenca", "Sentença", "txt"),
                    ("final", "Resultado após o recurso", "txt"),
                    ("n", "n", "num"),
                ],
            )
            + "</section>"
        )

    motivos = m["motivos_extincao"]
    if motivos and sum(x["n"] for x in motivos) >= politica.MINIMO_PUBLICAVEL:
        secoes.append(
            _figura(
                "Motivos de extinção sem resolução do mérito",
                "Inciso do art. 485 do CPC citado no dispositivo, ou causa nomeada no texto; só "
                "decisões avaliadas pelo texto.",
                grafico_barras(
                    [
                        (x["motivo"], x["proporcao"], f"{_pct(x['proporcao'])} ({_num(x['n'])})")
                        for x in motivos[:12]
                    ],
                    "Motivos de extinção",
                ),
                tabela(
                    motivos,
                    [
                        ("motivo", "Motivo", "txt"),
                        ("n", "n", "num"),
                        ("proporcao", "Proporção", "pct"),
                    ],
                ),
            )
        )

    danos = m["danos_morais_tribunal"][:30]
    if danos:
        secoes.append(
            _figura(
                "Indenização por danos morais nas sentenças que acolheram o pedido",
                "Mediana e metade central (1º ao 3º quartil) do valor fixado no dispositivo, "
                "por tribunal, em reais nominais da data da sentença.",
                grafico_faixas(danos, "Danos morais por tribunal"),
                tabela(
                    danos,
                    [
                        ("grupo", "Tribunal", "txt"),
                        ("n", "n", "num"),
                        ("mediana", "Mediana (R$)", "num"),
                        ("q1", "1º quartil", "num"),
                        ("q3", "3º quartil", "num"),
                    ],
                ),
            )
        )

    parametros = m["parametros_calculo"]
    if parametros:
        secoes.append(
            '<section class="figura"><h3>Parâmetros de cálculo fixados nas condenações</h3>'
            '<p class="sub">Honorários, repetição do indébito, termos iniciais e índices de juros '
            "e correção monetária lidos no dispositivo das sentenças que acolheram o pedido.</p>"
            + tabela(
                parametros,
                [
                    ("parametro", "Parâmetro", "txt"),
                    ("valor", "Valor", "txt"),
                    ("n", "n", "num"),
                    ("proporcao", "Proporção", "pct"),
                ],
            )
            + "</section>"
        )
    return secoes


def tabela(linhas: list[dict], colunas: list[tuple[str, str, str]]) -> str:
    """colunas: (chave, título, formato: 'pct', 'num' ou 'txt')."""
    formatos = {"pct": _pct, "num": _num, "txt": str, "z": lambda v: f"{v:.2f}"}
    cabecalho = "".join(f"<th>{_e(t)}</th>" for _, t, _ in colunas)
    corpo = "".join(
        "<tr>"
        + "".join(f'<td class="{f}">{_e(formatos[f](linha.get(k)))}</td>' for k, _, f in colunas)
        + "</tr>"
        for linha in linhas
    )
    return (
        f'<div class="tabela-rolagem"><table><thead><tr>{cabecalho}</tr></thead>'
        f"<tbody>{corpo}</tbody></table></div>"
    )


def _figura(titulo: str, subtitulo: str, grafico: str, tabela_html: str) -> str:
    return (
        f'<section class="figura"><h3>{_e(titulo)}</h3><p class="sub">{_e(subtitulo)}</p>'
        f'<div class="grafico">{grafico}</div>'
        f"<details><summary>Ver a tabela</summary>{tabela_html}</details></section>"
    )


def _gravar_csv(caminho: Path, linhas: list[dict]) -> None:
    if not linhas:
        return
    campos = list(dict.fromkeys(k for linha in linhas for k in linha))
    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(linhas)


def calcular(corpus: Corpus, incluir_sensiveis: bool = False) -> dict:
    processos = list(corpus.processos(incluir_sensiveis))
    documentos = list(corpus.documentos(incluir_sensiveis))
    unidades = consolidar(processos, documentos)
    primeira = [u for u in unidades if u["instancia"] == "1"]
    segunda = [u for u in unidades if u["instancia"] == "2"]
    return {
        "resumo": corpus.resumo(),
        "qualidade": jurimetria.qualidade(unidades),
        "distribuicao_primeira": jurimetria.distribuicao(primeira),
        "distribuicao_segunda": jurimetria.distribuicao(segunda),
        "taxa_nacional": jurimetria.taxa_nacional(unidades),
        "provimento_por_recurso": jurimetria.provimento_por_recurso(segunda),
        "taxas_ramo": jurimetria.taxas(unidades, "ramo"),
        "taxas_tribunal": jurimetria.taxas(unidades, "tribunal"),
        "taxas_ano": sorted(jurimetria.taxas(unidades, "ano"), key=lambda x: x["grupo"]),
        "taxas_grau": jurimetria.taxas(unidades, "grau"),
        "taxas_assunto": jurimetria.taxas(unidades, "assunto"),
        "reforma": jurimetria.reforma(unidades),
        "motivos_extincao": jurimetria.motivos(primeira),
        "danos_morais_tribunal": jurimetria.valores_condenacao(primeira, "danos_morais"),
        "parametros_calculo": jurimetria.parametros_calculo(primeira),
        "duracao_tribunal": jurimetria.duracoes(processos, "tribunal"),
        "citacoes": jurimetria.citacoes_por_resultado(documentos),
        "vocabulario": jurimetria.vocabulario(documentos),
    }


def gerar(
    corpus: Corpus,
    saida: str | Path,
    titulo: str = "Dikemetria",
    descricao: str = "",
    incluir_sensiveis: bool = False,
) -> Path:
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    m = calcular(corpus, incluir_sensiveis)

    for nome, valor in m.items():
        if isinstance(valor, list):
            _gravar_csv(saida / f"{nome}.csv", valor)
    _gravar_csv(saida / "reforma_cruzamento.csv", m["reforma"]["cruzamento"])
    _gravar_csv(saida / "reforma_resultado_final.csv", m["reforma"]["resultado_final"])
    for lado, linhas in m["vocabulario"].items():
        _gravar_csv(saida / f"vocabulario_{lado}.csv", linhas)
    gerado_em = datetime.now(UTC).isoformat(timespec="seconds")
    (saida / "metadados.json").write_text(
        json.dumps(
            {
                "titulo": titulo,
                "descricao": descricao,
                "gerado_em": gerado_em,
                "versao_dikemetria": __version__,
                "minimo_publicavel": politica.MINIMO_PUBLICAVEL,
                "inclui_materias_sensiveis": incluir_sensiveis,
                "resumo": m["resumo"],
                "qualidade_da_classificacao": m["qualidade"],
                "taxa_de_reforma": m["reforma"]["taxa_reforma"],
                "provimento_por_recurso": m["provimento_por_recurso"],
                "licenca": "CC BY 4.0",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (saida / "DICIONARIO.md").write_text(DICIONARIO, encoding="utf-8")
    pagina = saida / "relatorio.html"
    pagina.write_text(_html(m, titulo, descricao, gerado_em), encoding="utf-8")
    return pagina


def _html(m: dict, titulo: str, descricao: str, gerado_em: str) -> str:
    secoes = []
    resumo = m["resumo"]
    if not (resumo["processos"] or resumo["documentos"]):
        return PAGINA.format(
            titulo=_e(titulo),
            descricao=_e(descricao),
            gerado_em=_e(gerado_em[:10]),
            versao=_e(__version__),
            minimo=politica.MINIMO_PUBLICAVEL,
            conteudo="<p>O corpus ainda está vazio.</p>",
            concordancia="",
        )
    secoes.append(
        '<div class="numeros">'
        f'<div><span class="grande">{_num(resumo["processos"])}</span>processos (DataJud)</div>'
        f'<div><span class="grande">{_num(resumo["documentos"])}</span>decisões com texto</div>'
        f'<div><span class="grande">{_num(resumo["tribunais"])}</span>tribunais</div>'
        f'<div><span class="grande">{_num(resumo["sensiveis"])}</span>'
        "registros sensíveis excluídos</div></div>"
    )

    for chave, nome in (
        ("distribuicao_primeira", "na 1ª instância"),
        ("distribuicao_segunda", "na 2ª instância"),
    ):
        linhas = m[chave]
        if not linhas:
            continue
        grafico = grafico_barras(
            [
                (
                    ROTULOS.get(x["resultado"], x["resultado"]),
                    x["proporcao"],
                    f"{_pct(x['proporcao'])} ({_num(x['n'])})",
                )
                for x in linhas
            ],
            f"Distribuição dos resultados segundo {nome}",
        )
        secoes.append(
            _figura(
                f"Resultados {nome}",
                "Uma decisão por processo e instância (texto ou movimentos). Proporção sobre "
                "o total de decisões.",
                grafico,
                tabela(
                    linhas,
                    [
                        ("resultado", "Resultado", "txt"),
                        ("n", "n", "num"),
                        ("proporcao", "Proporção", "pct"),
                    ],
                ),
            )
        )

    nacional = m["taxa_nacional"]
    if nacional:
        secoes.append(
            '<section class="figura"><h3>Taxas no conjunto dos tribunais</h3>'
            '<p class="sub">A taxa agregada soma todos os casos e pesa mais os tribunais grandes; '
            "a média entre tribunais dá peso igual a cada tribunal com casos suficientes.</p>"
            + tabela(
                nacional,
                [
                    ("medida", "Medida", "txt"),
                    ("n", "Decisões", "num"),
                    ("agregada", "Agregada", "pct"),
                    ("agregada_ic_inf", "IC inf.", "pct"),
                    ("agregada_ic_sup", "IC sup.", "pct"),
                    ("tribunais", "Tribunais", "num"),
                    ("media_tribunais", "Média entre tribunais", "pct"),
                    ("minimo_tribunais", "Menor", "pct"),
                    ("maximo_tribunais", "Maior", "pct"),
                ],
            )
            + "</section>"
        )

    colunas_taxa = [
        ("grupo", "Grupo", "txt"),
        ("merito", "Decisões de mérito", "num"),
        ("procedencia", "Procedência total", "pct"),
        ("acolhimento", "Acolhimento", "pct"),
        ("acolhimento_ic_inf", "IC inf.", "pct"),
        ("acolhimento_ic_sup", "IC sup.", "pct"),
    ]
    for chave, nome in (
        ("taxas_ramo", "ramo da Justiça"),
        ("taxas_tribunal", "tribunal"),
        ("taxas_grau", "grau"),
        ("taxas_ano", "ano do julgamento"),
        ("taxas_assunto", "assunto"),
    ):
        linhas = [x for x in m[chave] if "acolhimento" in x][:30]
        if not linhas:
            continue
        secoes.append(
            _figura(
                f"Acolhimento do pedido por {nome}",
                "Procedentes e parcialmente procedentes sobre as decisões de mérito, com "
                "intervalo de confiança de 95% (Wilson). Passe o mouse para ver os valores.",
                grafico_intervalos(linhas, "acolhimento", f"Acolhimento por {nome}"),
                tabela(linhas, colunas_taxa),
            )
        )

    recursos = [x for x in m["taxas_tribunal"] if "provimento" in x][:30]
    if recursos:
        secoes.append(
            _figura(
                "Provimento de recursos por tribunal",
                "Providos e parcialmente providos sobre os recursos julgados no mérito, IC de 95%.",
                grafico_intervalos(recursos, "provimento", "Provimento por tribunal"),
                tabela(
                    recursos,
                    [
                        ("grupo", "Tribunal", "txt"),
                        ("recursos", "Recursos", "num"),
                        ("provimento", "Provimento", "pct"),
                        ("provimento_ic_inf", "IC inf.", "pct"),
                        ("provimento_ic_sup", "IC sup.", "pct"),
                    ],
                ),
            )
        )

    duracao = m["duracao_tribunal"][:30]
    if duracao:
        maximo = max(x["mediana_dias"] for x in duracao) or 1
        secoes.append(
            _figura(
                "Tempo até o primeiro julgamento, por tribunal",
                "Mediana de dias entre o ajuizamento e o primeiro julgamento (mérito ou extinção).",
                grafico_barras(
                    [
                        (x["grupo"], x["mediana_dias"] / maximo, f"{_num(x['mediana_dias'])} dias")
                        for x in duracao
                    ],
                    "Mediana de dias até o julgamento",
                ),
                tabela(
                    duracao,
                    [
                        ("grupo", "Tribunal", "txt"),
                        ("n", "n", "num"),
                        ("mediana_dias", "Mediana", "num"),
                        ("q1_dias", "1º quartil", "num"),
                        ("q3_dias", "3º quartil", "num"),
                    ],
                ),
            )
        )

    secoes += _secoes_calculo(m)

    if m["citacoes"]:
        secoes.append(
            _figura(
                "Normas citadas em decisões acolhidas e rejeitadas",
                "Proporção dos documentos de cada lado que citam a norma ao menos uma vez.",
                grafico_halteres(m["citacoes"][:20], "Normas citadas por resultado"),
                tabela(
                    m["citacoes"],
                    [
                        ("citacao", "Norma", "txt"),
                        ("documentos", "Documentos", "num"),
                        ("em_acolhidos", "Em acolhidos", "pct"),
                        ("em_rejeitados", "Em rejeitados", "pct"),
                    ],
                ),
            )
        )

    vocab = m["vocabulario"]
    if vocab["acolhido"] or vocab["rejeitado"]:
        secoes.append(
            _figura(
                "Vocabulário da fundamentação",
                "Log-odds com prior de Dirichlet informativo (escore z). Medida descritiva de "
                "associação entre palavra e resultado; não indica causa nem chance de êxito.",
                grafico_divergente(
                    vocab["acolhido"][:15],
                    vocab["rejeitado"][:15],
                    "Palavras típicas de cada resultado",
                ),
                tabela(
                    vocab["acolhido"] + vocab["rejeitado"],
                    [
                        ("palavra", "Palavra", "txt"),
                        ("z", "z", "z"),
                        ("n_acolhidos", "Em acolhidos", "num"),
                        ("n_rejeitados", "Em rejeitados", "num"),
                    ],
                ),
            )
        )

    q = m["qualidade"]
    nota_concordancia = (
        f"Em {_num(q['com_duas_fontes'])} decisões com as duas fontes, texto e movimentos "
        f"divergiram em {_num(q['divergentes'])}; prevaleceu o texto."
        if q["com_duas_fontes"]
        else "Ainda não há decisões com as duas fontes para comparar."
    )
    nota_concordancia += (
        f" Ficaram sem resultado determinado {_num(q['indeterminadas'])} de "
        f"{_num(q['unidades'])} decisões."
    )

    return PAGINA.format(
        titulo=_e(titulo),
        descricao=_e(descricao),
        gerado_em=_e(gerado_em[:10]),
        versao=_e(__version__),
        minimo=politica.MINIMO_PUBLICAVEL,
        conteudo="\n".join(secoes),
        concordancia=_e(nota_concordancia),
    )


PAGINA = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<style>
:root {{
  color-scheme: light;
  --surface: #fcfcfb; --surface-2: #f3f2ef; --text: #0b0b0b; --text-2: #52514e;
  --muted: #8a8984; --grid: #e4e3df; --series-1: #2a78d6; --series-2: #e34948;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    color-scheme: dark;
    --surface: #1a1a19; --surface-2: #252524; --text: #ffffff; --text-2: #c3c2b7;
    --muted: #8f8e88; --grid: #383835; --series-1: #3987e5; --series-2: #e66767;
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --surface: #1a1a19; --surface-2: #252524; --text: #ffffff; --text-2: #c3c2b7;
  --muted: #8f8e88; --grid: #383835; --series-1: #3987e5; --series-2: #e66767;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--surface); color: var(--text);
  font: 16px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }}
main {{ max-width: 820px; margin: 0 auto; padding: 32px 16px 64px; }}
h1 {{ font-size: 28px; margin: 0 0 4px; }}
h2 {{ font-size: 20px; margin: 40px 0 8px; }}
h3 {{ font-size: 17px; margin: 0; }}
p, li {{ color: var(--text-2); }}
.sub {{ margin: 2px 0 12px; font-size: 14px; }}
.numeros {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px; margin: 24px 0; }}
.numeros div {{ background: var(--surface-2); border-radius: 8px; padding: 12px 14px;
  color: var(--text-2); font-size: 14px; }}
.grande {{ display: block; font-size: 26px; font-weight: 600; color: var(--text); }}
.figura {{ margin: 32px 0; }}
.grafico {{ overflow-x: auto; }}
svg {{ width: 100%; min-width: 640px; height: auto; display: block; overflow: visible; }}
svg text {{ font-size: 13px; fill: var(--text-2); }}
svg .valor, svg .legenda {{ fill: var(--text); }}
svg .eixo {{ fill: var(--muted); font-size: 12px; }}
svg .grade {{ stroke: var(--grid); stroke-width: 1; }}
svg .base {{ stroke: var(--muted); stroke-width: 1; }}
svg .serie-1, svg .ponto, svg .chave-1 {{ fill: var(--series-1); }}
svg .serie-2, svg .ponto-2, svg .chave-2 {{ fill: var(--series-2); }}
svg .ponto, svg .ponto-2 {{ stroke: var(--surface); stroke-width: 2; }}
svg .ic {{ stroke: var(--text-2); stroke-width: 2; stroke-linecap: round; }}
svg .alvo:hover rect {{ fill: var(--surface-2); }}
svg path:hover {{ opacity: .8; }}
details {{ margin-top: 8px; font-size: 14px; }}
summary {{ cursor: pointer; color: var(--text-2); }}
.tabela-rolagem, details {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 8px; font-size: 13px; }}
th, td {{ text-align: left; padding: 4px 8px; border-bottom: 1px solid var(--grid); }}
td.pct, td.num, td.z {{ text-align: right; font-variant-numeric: tabular-nums; }}
.aviso {{ border-left: 3px solid var(--muted); padding: 4px 12px; margin: 16px 0; }}
footer {{ margin-top: 48px; font-size: 13px; color: var(--muted); }}
</style>
</head>
<body>
<main>
<h1>{titulo}</h1>
<p>{descricao}</p>
<p class="sub">Gerado em {gerado_em} · Dikemetria {versao}</p>
<div class="aviso"><p>Medidas descritivas de como os tribunais decidiram. Não estimam a chance de
uma ação concreta, não recomendam estratégia e não constituem consultoria jurídica.</p></div>
{conteudo}
<h2>Metodologia</h2>
<ul>
<li><strong>Fontes.</strong> Metadados e movimentos da API Pública do DataJud (CNJ) e texto das
decisões publicadas no Diário de Justiça Eletrônico Nacional (DJEN), com URL, data e hash de cada
resposta.</li>
<li><strong>Resultado.</strong> Pelo dispositivo do texto, lido por capítulos (ação, reconvenção,
recurso, embargos), e pelos movimentos da Tabela Processual Unificada; uma decisão por processo e
instância, prevalecendo o texto. {concordancia} Regras completas em
<a href="https://github.com/luccas-amorim/dikemetria/blob/main/docs/REGRAS.md">docs/REGRAS.md</a>.</li>
<li><strong>Taxas.</strong> Acolhimento = procedentes + parcialmente procedentes sobre decisões de
mérito; extinções sem mérito e acordos ficam fora do denominador. Intervalos de Wilson a 95%.</li>
<li><strong>Valores.</strong> Primeiro valor de cada categoria no dispositivo, em reais nominais;
valores fora de R$ 1 a R$ 10 milhões são descartados.</li>
<li><strong>Vocabulário.</strong> Só relatório e fundamentação, porque o dispositivo repete o
resultado.</li>
<li><strong>Supressão.</strong> Grupos com menos de {minimo} casos não aparecem.</li>
</ul>
<h2>Limitações</h2>
<ul>
<li>A cobertura do DataJud e do DJEN varia entre tribunais e períodos.</li>
<li>A classificação automática erra; a taxa de acerto medida contra rotulagem manual acompanha
cada versão dos dados.</li>
<li>Associação não é causa: tribunais, matérias e partes diferem em muitos fatores não
observados.</li>
</ul>
<h2>Dados pessoais</h2>
<p>Textos pseudonimizados antes da análise; nenhum texto integral, número de processo ou perfil de
magistrado é publicado. Matérias sensíveis e processos em segredo de justiça ficam fora. Pedidos de
revisão ou remoção: abra uma issue no repositório.</p>
<footer>Resultados sob CC BY 4.0. Cite: Dikemetria, Luccas de Amorim,
https://github.com/luccas-amorim/dikemetria.</footer>
</main>
</body>
</html>
"""

DICIONARIO = """# Dicionário de dados

Todas as tabelas excluem matérias sensíveis (salvo indicação em `metadados.json`) e grupos com
menos casos que `minimo_publicavel`.

| Arquivo | Coluna | Significado |
|---|---|---|
| `distribuicao_*.csv` | resultado | rótulo do resultado (ver abaixo) |
| | n, proporcao | quantidade e proporção sobre o total classificado |
| `taxas_*.csv` | grupo | valor do agrupamento (ramo, tribunal, grau, ano, assunto) |
| | total | registros do grupo, de qualquer resultado |
| | merito | procedentes + parcialmente procedentes + improcedentes |
| | procedencia | procedentes / merito |
| | acolhimento | (procedentes + parcialmente procedentes) / merito |
| | recursos | recursos julgados no mérito |
| | provimento | (providos + parcialmente providos) / recursos |
| | *_ic_inf, *_ic_sup | intervalo de confiança de Wilson a 95% |
| `duracao_tribunal.csv` | mediana_dias, q1_dias, q3_dias | dias até o primeiro julgamento |
| `citacoes.csv` | citacao | norma citada, normalizada (ex.: `art. 14 CDC`, `Súmula 385 STJ`) |
| | em_acolhidos, em_rejeitados | proporção dos documentos de cada lado que citam a norma |
| `vocabulario_*.csv` | z | log-odds com prior de Dirichlet informativo; positivo = acolhido |

Rótulos de resultado: `procedente`, `parcialmente_procedente`, `improcedente`,
`extinto_sem_merito`, `homologacao_acordo`, `provido`, `parcialmente_provido`, `nao_provido`,
`nao_conhecido`, `indeterminado`.
"""
