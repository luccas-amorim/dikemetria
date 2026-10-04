"""Linha de comando: `dikemetria <comando>` ou `python -m dikemetria <comando>`."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

from dikemetria import __version__

BANCO_PADRAO = "dados/corpus.sqlite"
log = logging.getLogger("dikemetria")


def _analisar(args) -> int:
    from dikemetria import autos
    from dikemetria.analise import analisar_documento
    from dikemetria.extracao import extrair_texto
    from dikemetria.pseudonimizacao import pseudonimizar

    texto = extrair_texto(args.arquivo)
    if autos.eh_autos_eproc(texto):
        finais = autos.decisoes_finais(texto)
        if not finais:
            raise SystemExit("Autos completos sem sentença nem acórdão; use `dikemetria autos`.")
        peca = finais[-1]
        print(
            f"Autos completos: analisando {peca.nome} do evento {peca.evento} "
            f"({len(finais)} decisão(ões) final(is) nos autos).",
            file=sys.stderr,
        )
        texto = peca.texto
    if not args.sem_pseudonimizar:
        texto = pseudonimizar(texto).texto
    analise = analisar_documento(texto, top=args.top).como_dict()
    saida = json.dumps(analise, ensure_ascii=False, indent=2)
    if args.json:
        Path(args.json).write_text(saida, encoding="utf-8")
        print(f"Análise gravada em {args.json}")
    else:
        print(saida)
    if args.svg:
        from dikemetria.relatorio import grafico_barras, svg_autonomo

        palavras = analise["palavras_frequentes"]
        maximo = max((n for _, n in palavras), default=1)
        svg = grafico_barras([(p, n / maximo, str(n)) for p, n in palavras], "Palavras frequentes")
        Path(args.svg).write_text(svg_autonomo(svg), encoding="utf-8")
        print(f"Gráfico gravado em {args.svg}")
    return 0


def _autos(args) -> int:
    """Separa as peças de autos completos, pseudonimizadas, para o sub-estudo com autos."""
    import csv

    from dikemetria import autos
    from dikemetria.extracao import extrair_texto
    from dikemetria.pseudonimizacao import pseudonimizar

    texto = extrair_texto(args.arquivo)
    if not autos.eh_autos_eproc(texto):
        raise SystemExit("Formato de autos não reconhecido (só eproc, por enquanto).")
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    gravadas = descartadas = 0
    with open(saida / "indice.csv", "w", newline="", encoding="utf-8") as indice:
        tabela = csv.writer(indice)
        tabela.writerow(["arquivo", "evento", "tipo", "peca", "classe", "paginas", "data"])
        for peca in autos.dividir(texto):
            if peca.classe == "anexo" and not args.incluir_anexos:
                descartadas += 1
                continue
            nome = f"evento-{peca.evento:03d}-{peca.sigla}{peca.ordem}.txt"
            (saida / nome).write_text(pseudonimizar(peca.texto).texto, encoding="utf-8")
            tabela.writerow(
                [nome, peca.evento, peca.sigla, peca.nome, peca.classe, peca.paginas, peca.data]
            )
            gravadas += 1
    print(f"{gravadas} peças pseudonimizadas em {saida}; {descartadas} anexos descartados.")
    print("Revise os nomes que restarem antes de qualquer uso; nada disso vai para o git.")
    return 0


def _pseudonimizar(args) -> int:
    from dikemetria.extracao import extrair_texto
    from dikemetria.pseudonimizacao import pseudonimizar

    resultado = pseudonimizar(extrair_texto(args.arquivo), usar_spacy=args.spacy)
    print(resultado.texto)
    print(f"\n# Substituições: {dict(resultado.substituicoes)}", file=sys.stderr)
    return 0


def _tribunais(args) -> int:
    from dikemetria.coleta.tribunais import TRIBUNAIS

    for t in TRIBUNAIS:
        print(f"{t.sigla:8} {t.ramo:10} {t.indice_datajud}")
    print(f"\n{len(TRIBUNAIS)} tribunais", file=sys.stderr)
    return 0


def _estimar(args) -> int:
    from dikemetria.coleta import datajud
    from dikemetria.coleta.http import ErroColeta
    from dikemetria.coleta.tribunais import selecionar
    from dikemetria.recorte import carregar

    recorte = carregar(args.recorte)
    cliente = datajud.cliente_datajud(args.intervalo)
    total = 0
    for tribunal in selecionar(args.tribunais or recorte.tribunais):
        try:
            n = datajud.contar(cliente, tribunal, recorte.datajud)
        except ErroColeta as erro:
            print(f"{tribunal.sigla:8} erro: {erro}")
            continue
        total += n
        print(f"{tribunal.sigla:8} {n:>12,}".replace(",", "."))
    print(f"{'total':8} {total:>12,}".replace(",", "."))
    return 0


def _coletar(args) -> int:
    from dikemetria.corpus import Corpus
    from dikemetria.recorte import carregar

    with Corpus(args.banco) as corpus:
        if args.fonte == "arquivos":
            return _coletar_arquivos(corpus, args)
        recorte = carregar(args.recorte)
        if args.fonte == "datajud":
            return _coletar_datajud(corpus, recorte, args)
        return _coletar_djen(corpus, recorte, args)


def _coletar_arquivos(corpus, args) -> int:
    from dikemetria.coleta import arquivos

    if not args.pasta:
        raise SystemExit("--fonte arquivos exige --pasta")
    gravados = falhas = 0
    for documento, caminho, proveniencia in arquivos.coletar(args.pasta):
        if documento is None:
            falhas += 1
            log.warning("%s ignorado: %s", caminho, proveniencia)
            continue
        gravados += corpus.gravar_documentos([documento], proveniencia)
    print(f"{gravados} documentos gravados, {falhas} ignorados")
    return 0


def _coletar_datajud(corpus, recorte, args) -> int:
    from dikemetria.coleta import datajud
    from dikemetria.coleta.http import ErroColeta
    from dikemetria.coleta.tribunais import selecionar

    cliente = datajud.cliente_datajud(args.intervalo)
    for tribunal in selecionar(args.tribunais or recorte.tribunais):
        cursor, concluido = corpus.cursor("datajud", recorte.nome, tribunal.sigla)
        if concluido and not args.refazer:
            log.info("%s já concluído", tribunal.sigla)
            continue
        if args.refazer:
            cursor = None
        n = 0
        try:
            paginas = datajud.coletar(cliente, tribunal, recorte.datajud, cursor)
            for processos, cursor, proveniencia in paginas:  # noqa: B020 (o cursor avança)
                n += corpus.gravar_processos(processos, proveniencia)
                corpus.salvar_cursor("datajud", recorte.nome, tribunal.sigla, cursor)
        except ErroColeta as erro:
            log.error("%s: %s (a próxima execução retoma daqui)", tribunal.sigla, erro)
            continue
        corpus.salvar_cursor("datajud", recorte.nome, tribunal.sigla, cursor, concluido=True)
        print(f"{tribunal.sigla:8} {n:>8} processos")
    print(json.dumps(corpus.resumo(), ensure_ascii=False))
    return 0


def _coletar_djen(corpus, recorte, args) -> int:
    from datetime import date

    from dikemetria.coleta import djen
    from dikemetria.coleta.http import Cliente, ErroColeta
    from dikemetria.coleta.tribunais import selecionar

    cliente = Cliente(intervalo=args.intervalo)
    for tribunal in selecionar(args.tribunais or recorte.tribunais):
        cursor, concluido = corpus.cursor("djen", recorte.nome, tribunal.sigla)
        if concluido and not args.refazer:
            continue
        retomar = date.fromisoformat(cursor) if cursor and not args.refazer else None
        n = 0
        try:
            for documentos, dia, proveniencia in djen.coletar(
                cliente, tribunal, recorte.djen, retomar
            ):
                if not recorte.incluir_sensiveis:
                    documentos = [d for d in documentos if not d.sensivel]
                n += corpus.gravar_documentos(documentos, proveniencia)
                corpus.salvar_cursor("djen", recorte.nome, tribunal.sigla, dia.isoformat())
        except ErroColeta as erro:
            log.error("%s: %s (a próxima execução retoma daqui)", tribunal.sigla, erro)
            continue
        corpus.salvar_cursor("djen", recorte.nome, tribunal.sigla, None, concluido=True)
        print(f"{tribunal.sigla:8} {n:>8} documentos")
    print(json.dumps(corpus.resumo(), ensure_ascii=False))
    return 0


def _sondar(args) -> int:
    """Busca um item de cada fonte e mostra os campos, para conferir se a API mudou."""
    from dikemetria.coleta import datajud, djen
    from dikemetria.coleta.http import Cliente
    from dikemetria.coleta.tribunais import selecionar

    tribunal = selecionar([args.tribunal])[0]
    if args.fonte == "datajud":
        dados, _ = datajud.cliente_datajud().requisitar(
            "POST", f"{datajud.URL_BASE}/{tribunal.indice_datajud}/_search", json_corpo={"size": 1}
        )
        hits = dados.get("hits", {}).get("hits", [])
        item = hits[0]["_source"] if hits else {}
    else:
        dados, _ = Cliente().requisitar(
            "GET", djen.URL, params={"siglaTribunal": tribunal.sigla_djen, "itensPorPagina": 1}
        )
        itens = dados.get("items") or dados.get("itens") or []
        item = itens[0] if itens else {}
    print("Chaves da resposta:", sorted(dados))
    print("Campos do item:", sorted(item))
    # Só tipos, nenhum valor: pode ser colado numa conversa ou issue sem expor dados pessoais.
    print("Estrutura do item:")
    print(json.dumps(estrutura(item), ensure_ascii=False, indent=2))
    return 0


def estrutura(valor):
    """Esqueleto de um JSON: as chaves e o tipo de cada valor, sem os valores."""
    if isinstance(valor, dict):
        return {chave: estrutura(v) for chave, v in sorted(valor.items())}
    if isinstance(valor, list):
        return [estrutura(valor[0])] if valor else []
    if isinstance(valor, str) and re.fullmatch(r"\d{2}/\d{2}/\d{4}.*", valor):
        return "texto (dd/mm/aaaa)"
    if isinstance(valor, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}.*", valor):
        return "texto (aaaa-mm-dd)"
    return {str: "texto", bool: "lógico", int: "inteiro", float: "decimal"}.get(
        type(valor), "nulo" if valor is None else type(valor).__name__
    )


def _classificar(args) -> int:
    """Reavalia os documentos do banco com as regras atuais de avaliação e cálculo."""
    from dikemetria.avaliacao import avaliar
    from dikemetria.corpus import Corpus
    from dikemetria.valores import calcular

    alterados = total = 0
    with Corpus(args.banco) as corpus:
        for doc in list(corpus.documentos(incluir_sensiveis=True)):
            total += 1
            avaliacao, dispositivo = avaliar(doc["texto"])
            dados = {**avaliacao.como_dict(), "calculo": calcular(dispositivo).como_dict()}
            if avaliacao.resultado.value != doc["resultado"]:
                alterados += 1
            corpus.atualizar_avaliacao_documento(
                doc["id"], avaliacao.resultado.value, avaliacao.evidencia, dados
            )
    print(f"{total} documentos reavaliados; {alterados} mudaram de resultado")
    return 0


def _amostra(args) -> int:
    from dikemetria.corpus import Corpus
    from dikemetria.validacao import gerar_amostra

    with Corpus(args.banco) as corpus:
        n = gerar_amostra(list(corpus.documentos()), args.n, args.saida, args.semente)
    print(
        f"{n} documentos em {args.saida}. Preencha a coluna resultado_manual e rode "
        f"`dikemetria validar {args.saida}`."
    )
    return 0


def _validar(args) -> int:
    from dikemetria.validacao import avaliar

    m = avaliar(args.csv)
    print(f"n = {m.n}   acurácia = {m.acuracia:.1%}")
    print(f"{'rótulo':26} {'precisão':>9} {'cobertura':>10} {'f1':>6} {'suporte':>8}")
    for rotulo, v in m.por_rotulo.items():
        print(
            f"{rotulo:26} {v['precisao']:>9.1%} {v['cobertura']:>10.1%} {v['f1']:>6.2f} "
            f"{v['suporte']:>8}"
        )
    erros = {k: v for k, v in m.confusao.items() if k[0] != k[1]}
    if erros:
        print("\nConfusões (manual -> automático):")
        for (manual, auto), q in sorted(erros.items(), key=lambda x: -x[1]):
            print(f"  {manual} -> {auto}: {q}")
    return 0


def _relatorio(args) -> int:
    from dikemetria.corpus import Corpus
    from dikemetria.relatorio import gerar

    titulo, descricao = args.titulo, ""
    if args.recorte:
        from dikemetria.recorte import carregar

        recorte = carregar(args.recorte)
        titulo = titulo or f"Dikemetria · {recorte.nome}"
        descricao = recorte.descricao
    with Corpus(args.banco) as corpus:
        pagina = gerar(
            corpus,
            args.saida,
            titulo or "Dikemetria",
            descricao,
            incluir_sensiveis=args.incluir_sensiveis,
        )
    print(f"Relatório em {pagina}")
    return 0


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dikemetria", description=__doc__)
    parser.add_argument("--version", action="version", version=f"dikemetria {__version__}")
    parser.add_argument("-v", "--verboso", action="store_true")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("analisar", help="analisa uma decisão (PDF, DOCX, TXT ou HTML)")
    p.add_argument("arquivo")
    p.add_argument("--json", help="grava a análise neste arquivo")
    p.add_argument("--svg", help="grava o gráfico de palavras frequentes neste arquivo")
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--sem-pseudonimizar", action="store_true")
    p.set_defaults(func=_analisar)

    p = sub.add_parser("pseudonimizar", help="mostra o texto de uma decisão pseudonimizado")
    p.add_argument("arquivo")
    p.add_argument("--spacy", action="store_true", help="usa também o NER do spaCy")
    p.set_defaults(func=_pseudonimizar)

    p = sub.add_parser("tribunais", help="lista os tribunais cobertos")
    p.set_defaults(func=_tribunais)

    def opcoes_coleta(p):
        p.add_argument("--tribunais", nargs="+", help="siglas ou ramos; padrão: os do recorte")
        p.add_argument("--intervalo", type=float, default=1.0, help="segundos entre requisições")

    p = sub.add_parser("estimar", help="conta, por tribunal, os processos do recorte no DataJud")
    p.add_argument("recorte")
    opcoes_coleta(p)
    p.set_defaults(func=_estimar)

    p = sub.add_parser("coletar", help="coleta para o banco local, retomando de onde parou")
    p.add_argument("recorte", nargs="?")
    p.add_argument("--fonte", choices=["datajud", "djen", "arquivos"], default="datajud")
    p.add_argument("--pasta", help="pasta com decisões, para --fonte arquivos")
    p.add_argument("--banco", default=BANCO_PADRAO)
    p.add_argument("--refazer", action="store_true", help="ignora o progresso salvo")
    opcoes_coleta(p)
    p.set_defaults(func=_coletar)

    p = sub.add_parser("autos", help="separa as peças de autos completos (eproc), pseudonimizadas")
    p.add_argument("arquivo")
    p.add_argument("--saida", default="dados/autos", help="pasta de saída, fora do git")
    p.add_argument("--incluir-anexos", action="store_true", help="grava também os anexos")
    p.set_defaults(func=_autos)

    p = sub.add_parser("sondar", help="confere os campos atuais da API de uma fonte")
    p.add_argument("--fonte", choices=["datajud", "djen"], default="datajud")
    p.add_argument("--tribunal", default="tjsp")
    p.set_defaults(func=_sondar)

    p = sub.add_parser(
        "classificar", help="reavalia resultado, capítulos e cálculo dos documentos do banco"
    )
    p.add_argument("--banco", default=BANCO_PADRAO)
    p.set_defaults(func=_classificar)

    p = sub.add_parser("amostra", help="gera CSV para validação manual dos resultados")
    p.add_argument("--banco", default=BANCO_PADRAO)
    p.add_argument("--n", type=int, default=200)
    p.add_argument("--saida", default="amostra_validacao.csv")
    p.add_argument("--semente", type=int, default=42)
    p.set_defaults(func=_amostra)

    p = sub.add_parser("validar", help="mede a classificação contra o CSV rotulado")
    p.add_argument("csv")
    p.set_defaults(func=_validar)

    p = sub.add_parser("relatorio", help="gera o relatório público (HTML e CSV)")
    p.add_argument("--banco", default=BANCO_PADRAO)
    p.add_argument("--saida", default="saida")
    p.add_argument("--recorte", help="recorte, para título e descrição")
    p.add_argument("--titulo")
    p.add_argument("--incluir-sensiveis", action="store_true")
    p.set_defaults(func=_relatorio)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verboso else logging.INFO, format="%(levelname)s %(message)s"
    )
    return args.func(args)
