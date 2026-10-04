"""Autos completos do eproc: separa as peças e lê só a decisão. Texto fictício."""

from dikemetria import autos
from dikemetria.avaliacao import avaliar

NUM = "1001234-88.2023.8.26.0100/SP"


def _pagina(evento: int, tipo: str, pagina: int, corpo: str) -> str:
    return f"Processo {NUM}, Evento {evento}, {tipo}, Página {pagina}\n{corpo}"


def _separacao(evento: int, descricao: str, data: str) -> str:
    return (
        f"PÁGINA DE SEPARAÇÃO\n(Gerada automaticamente pelo sistema.)\nEvento {evento}\n"
        f"Evento:\n{descricao}\nData:\n{data} 10:00:00\nUsuário:\nXX - FULANO - ADVOGADO\n"
        f"Processo:\n{NUM}\nSequência Evento:\n{evento}"
    )


AUTOS = "\f".join(
    [
        "Tipo documento: CAPA PROCESSO\nPROCESSO\nNº 1001234-88.2023.8.26.0100",
        _separacao(1, "DISTRIBUIDO POR SORTEIO", "01/04/2026"),
        _pagina(1, "INIC1", 1, "EXCELENTÍSSIMO SENHOR JUIZ\nA autora propõe ação indenizatória."),
        _pagina(1, "INIC1", 2, "Ante o exposto, requer a procedência do pedido."),
        _pagina(1, "PROC2", 1, "PROCURAÇÃO\nOutorgante: Beltrana de Tal, CPF ..."),
        _separacao(33, "CONTESTACAO", "25/06/2026"),
        _pagina(33, "CONTES1", 1, "CONTESTAÇÃO\nDiante do exposto, requer a improcedência."),
        _separacao(48, "JULGADO IMPROCEDENTE O PEDIDO", "20/08/2026"),
        _pagina(
            48,
            "SENT1",
            1,
            "SENTENÇA\nVistos.\nÉ o relatório.\nDecido.\nNo mérito, a ação não procede.",
        ),
        _pagina(48, "SENT1", 2, "Posto isso, JULGO IMPROCEDENTES os pedidos formulados."),
        _separacao(60, "DESPACHO", "10/09/2026"),
        _pagina(
            60,
            "DESPADEC1",
            1,
            "Vistos.\nDiante do exposto, recebo a apelação e intime-se o "
            "apelado para contrarrazões.",
        ),
    ]
)


def test_reconhece_e_divide_os_autos():
    assert autos.eh_autos_eproc(AUTOS)
    assert not autos.eh_autos_eproc("SENTENÇA\nPosto isso, julgo procedente.")
    pecas = autos.dividir(AUTOS)
    assert [(p.evento, p.sigla, p.classe) for p in pecas] == [
        (1, "INIC", "parte"),
        (1, "PROC", "anexo"),
        (33, "CONTES", "parte"),
        (48, "SENT", "decisão"),
        (60, "DESPADEC", "decisão"),
    ]
    inicial = pecas[0]
    assert inicial.paginas == 2 and "requer a procedência" in inicial.texto
    assert "Processo" not in inicial.texto  # o marcador de página sai do texto
    sentenca = pecas[3]
    assert sentenca.data == "2026-08-20"
    assert sentenca.descricao_evento == "JULGADO IMPROCEDENTE O PEDIDO"
    assert sentenca.nome == "sentença"


def test_decisao_final_e_a_sentenca_nao_o_ultimo_despacho():
    # Lidos inteiros, os autos dão o resultado do último "Diante do exposto" (um despacho).
    assert avaliar(AUTOS)[0].resultado.value != "improcedente"
    finais = autos.decisoes_finais(AUTOS)
    assert [p.sigla for p in finais] == ["SENT"]
    assert avaliar(finais[0].texto)[0].resultado.value == "improcedente"


def test_texto_sem_quebra_de_pagina_tambem_divide():
    colado = AUTOS.replace("\f", "\n")
    finais = autos.decisoes_finais(colado)
    assert [p.sigla for p in finais] == ["SENT"]
    assert "SEPARAÇÃO" not in finais[0].texto and finais[0].data == "2026-08-20"


def test_ingestao_de_autos_guarda_so_a_sentenca(tmp_path):
    from dikemetria.coleta import arquivos

    (tmp_path / "autos.txt").write_text(AUTOS, encoding="utf-8")
    resultados = list(arquivos.coletar(tmp_path))
    documentos = [d for d, _, _ in resultados if d is not None]
    assert len(documentos) == 1
    sentenca = documentos[0]
    assert sentenca.resultado == "improcedente"
    assert sentenca.tipo == "sentença" and sentenca.data == "2026-08-20"
    assert "PROCURAÇÃO" not in sentenca.texto


def test_comando_autos_exporta_pecas_sem_anexos(tmp_path):
    import csv

    from dikemetria.cli import main

    entrada = tmp_path / "autos.txt"
    entrada.write_text(AUTOS, encoding="utf-8")
    saida = tmp_path / "pecas"
    assert main(["autos", str(entrada), "--saida", str(saida)]) == 0
    linhas = list(csv.DictReader(open(saida / "indice.csv", encoding="utf-8")))
    assert [linha["tipo"] for linha in linhas] == ["INIC", "CONTES", "SENT", "DESPADEC"]
    assert "Beltrana" not in "".join(p.read_text() for p in saida.glob("*.txt"))
