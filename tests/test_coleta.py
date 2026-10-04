from datetime import date

import pytest

from dikemetria.coleta import arquivos, datajud, djen
from dikemetria.coleta.http import ErroColeta
from dikemetria.coleta.tribunais import selecionar
from dikemetria.recorte import RecorteDataJud, RecorteDJEN, carregar

from .conftest import CNJ_TJSP, SENTENCA_PROCEDENTE, RespostaFalsa, hit_datajud

TJSP = selecionar(["tjsp"])[0]
PROCEDENCIA = [{"codigo": 219, "nome": "Procedência", "dataHora": "2022-03-10T00:00:00.000Z"}]


def test_recorte_de_exemplo_carrega():
    recorte = carregar("recortes/exemplo.toml")
    assert recorte.nome == "negativacao-indevida"
    assert recorte.datajud.ajuizamento_desde == date(2020, 1, 1)
    assert recorte.djen.tipos_documento == ["Sentença"]
    assert len(selecionar(recorte.tribunais)) == 27


def test_consulta_combina_grupos_com_e_e_valores_com_ou():
    consulta = datajud.montar_consulta(
        RecorteDataJud(assuntos_codigos=[6226, 10433], graus=["G1"], ordem="atualizacao"),
        tamanho=100,
        apos=[123],
    )
    must = consulta["query"]["bool"]["must"]
    assert len(must) == 2
    assert must[0]["bool"]["should"] == [
        {"match": {"assuntos.codigo": 6226}},
        {"match": {"assuntos.codigo": 10433}},
    ]
    assert consulta["search_after"] == [123]
    assert consulta["sort"] == [{"@timestamp": {"order": "asc"}}]


def test_consulta_filtra_periodo_nos_dois_formatos_e_sorteia():
    recorte = RecorteDataJud(
        assuntos_codigos=[6226],
        ajuizamento_desde=date(2022, 1, 1),
        ajuizamento_ate=date(2023, 12, 31),
    )
    consulta = datajud.montar_consulta(recorte, tamanho=10)
    sorteio = consulta["query"]["function_score"]
    assert sorteio["random_score"] == {"seed": 2026, "field": "_seq_no"}
    periodo = sorteio["query"]["bool"]["must"][1]["bool"]["should"]
    faixas = [f["range"]["dataAjuizamento"] for f in periodo]
    # Cada formato do DataJud cai na sua faixa; o dia seguinte ao fim fica de fora.
    for faixa, dentro, depois in zip(
        faixas,
        ["20231231235959", "20231231", "2023-12-31T23:59:59.000Z"],
        ["20240101000000", "20240101", "2024-01-01T00:00:00.000Z"],
        strict=True,
    ):
        assert faixa["gte"] <= dentro <= faixa["lte"] < depois
    assert consulta["sort"][0] == {"_score": {"order": "desc"}}


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        ("20210310000000", "2021-03-10"),
        ("2021-03-10T00:00:00.000Z", "2021-03-10"),
        ("2021-03-10", "2021-03-10"),
        ("lixo", None),
        (None, None),
    ],
)
def test_converter_data(bruto, esperado):
    assert datajud.converter_data(bruto) == esperado


def test_converter_processo_calcula_resultado_e_duracao():
    hit = hit_datajud("10012348820238260100", PROCEDENCIA, [1])
    processo = datajud.converter_processo(hit["_source"], "tjsp")
    assert processo.resultado == "procedente"
    assert processo.data_ajuizamento == "2021-03-10"
    assert processo.duracao_dias == 365
    assert processo.municipio_ibge == 3550308
    assert not processo.sensivel


def test_materia_sensivel_e_marcada():
    hit = hit_datajud(
        "1", PROCEDENCIA, [1], classe={"codigo": 1, "nome": "Alimentos - Lei 5478/68"}
    )
    assert datajud.converter_processo(hit["_source"], "tjsp").sensivel


def test_coleta_datajud_pagina_descarta_sigilo_e_periodo(cliente_falso):
    pagina1 = {
        "hits": {
            "hits": [
                hit_datajud("1", PROCEDENCIA, [1]),
                hit_datajud("2", PROCEDENCIA, [2], nivelSigilo=1),
            ]
        }
    }
    pagina2 = {"hits": {"hits": [hit_datajud("3", PROCEDENCIA, [3], dataAjuizamento="20150101")]}}
    cliente, sessao = cliente_falso([pagina1, pagina2])
    recorte = RecorteDataJud(ajuizamento_desde=date(2020, 1, 1), tamanho_pagina=2)

    paginas = list(datajud.coletar(cliente, TJSP, recorte))
    assert [[p.numero for p in procs] for procs, _, _ in paginas] == [["1"], []]
    assert paginas[-1][1] == [3]  # cursor para retomar
    assert sessao.requisicoes[1]["json"]["search_after"] == [2]
    assert sessao.requisicoes[0]["url"].endswith("/api_publica_tjsp/_search")
    assert len(paginas[0][2].sha256) == 64


def test_coleta_datajud_respeita_limite(cliente_falso):
    pagina = {"hits": {"hits": [hit_datajud(str(i), PROCEDENCIA, [i]) for i in range(3)]}}
    cliente, sessao = cliente_falso([pagina])
    recorte = RecorteDataJud(limite_por_tribunal=3, tamanho_pagina=10)
    assert sum(len(p) for p, _, _ in datajud.coletar(cliente, TJSP, recorte)) == 3
    assert sessao.requisicoes[0]["json"]["size"] == 3


def test_limite_conta_os_guardados_e_para_de_ler(cliente_falso):
    fora = {"dataAjuizamento": "20150101"}
    pagina1 = {
        "hits": {
            "hits": [hit_datajud("1", PROCEDENCIA, [1], **fora), hit_datajud("2", PROCEDENCIA, [2])]
        }
    }
    pagina2 = {"hits": {"hits": [hit_datajud("3", PROCEDENCIA, [3])]}}
    cliente, sessao = cliente_falso([pagina1, pagina2])
    recorte = RecorteDataJud(
        ajuizamento_desde=date(2020, 1, 1), limite_por_tribunal=2, tamanho_pagina=2
    )
    guardados = [p.numero for procs, _, _ in datajud.coletar(cliente, TJSP, recorte) for p in procs]
    assert guardados == ["2", "3"]
    assert sessao.requisicoes[1]["json"]["size"] == 1  # só o que falta para o limite

    sempre_fora = {"hits": {"hits": [hit_datajud("9", PROCEDENCIA, [9], **fora)]}}
    cliente, sessao = cliente_falso([sempre_fora] * 20)
    recorte = RecorteDataJud(
        ajuizamento_desde=date(2020, 1, 1), limite_por_tribunal=1, tamanho_pagina=1
    )
    assert sum(len(p) for p, _, _ in datajud.coletar(cliente, TJSP, recorte)) == 0
    assert len(sessao.requisicoes) == datajud.LEITURAS_POR_GUARDADO


def test_contar(cliente_falso):
    cliente, _ = cliente_falso([{"hits": {"total": {"value": 4321}}}])
    assert datajud.contar(cliente, TJSP, RecorteDataJud()) == 4321


def test_cliente_tenta_de_novo_e_desiste_em_erro_permanente(cliente_falso, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    cliente, _ = cliente_falso([RespostaFalsa({}, 503), {"ok": True}])
    assert cliente.requisitar("GET", "https://exemplo")[0] == {"ok": True}
    cliente, _ = cliente_falso([RespostaFalsa({"erro": "x"}, 401)])
    with pytest.raises(ErroColeta, match="401"):
        cliente.requisitar("GET", "https://exemplo")


def item_djen(id_, texto, tipo="Sentença", **extra):
    item = {
        "id": id_,
        "data_disponibilizacao": "2025-01-02",
        "siglaTribunal": "TJSP",
        "tipoDocumento": tipo,
        "nomeClasse": "Procedimento Comum Cível",
        "numeroprocessocommascara": CNJ_TJSP,
        "texto": texto,
        "link": "https://exemplo/1",
        "destinatarios": [{"nome": "JOÃO CARLOS DA SILVA", "polo": "A"}],
        "destinatarioadvogados": [{"advogado": {"nome": "Pedro Henrique Alves"}}],
    }
    item.update(extra)
    return item


def test_documento_djen_e_pseudonimizado_e_classificado():
    texto = "<p>" + SENTENCA_PROCEDENTE.replace("\n", "<br>") + "</p>Adv. Pedro Henrique Alves"
    documento = djen.converter_documento(item_djen(1, texto), "tjsp")
    assert documento.resultado == "procedente"
    assert documento.numero == CNJ_TJSP
    assert "JOÃO CARLOS" not in documento.texto and "Pedro Henrique" not in documento.texto
    assert "<p>" not in documento.texto
    assert documento.id == "djen:1"
    assert len(documento.sha256_original) == 64


def test_documento_djen_em_segredo_e_descartado():
    texto = "Processo que tramita em segredo de justiça. JULGO PROCEDENTE o pedido."
    assert djen.converter_documento(item_djen(1, texto), "tjsp") is None


def test_coleta_djen_dia_a_dia_filtra_tipo(cliente_falso):
    dia1 = {"items": [item_djen(1, SENTENCA_PROCEDENTE), item_djen(2, "Cite-se.", "Despacho")]}
    dia2 = {"items": []}
    cliente, sessao = cliente_falso([dia1, dia2])
    recorte = RecorteDJEN(
        data_inicio=date(2025, 1, 2), data_fim=date(2025, 1, 3), itens_por_pagina=100
    )
    paginas = list(djen.coletar(cliente, TJSP, recorte))
    assert [len(docs) for docs, _, _ in paginas] == [1, 0]
    assert [dia for _, dia, _ in paginas] == [date(2025, 1, 2), date(2025, 1, 3)]
    assert sessao.requisicoes[0]["params"]["siglaTribunal"] == "TJSP"
    assert sessao.requisicoes[1]["params"]["dataDisponibilizacaoInicio"] == "2025-01-03"


def _pdf_com_texto(linhas: list[str]) -> bytes:
    """PDF mínimo e válido com texto extraível (Helvetica, uma página)."""
    conteudo = (
        "BT /F1 11 Tf 50 780 Td 14 TL "
        + " ".join(
            "(" + linha.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ") '"
            for linha in linhas
        )
        + " ET"
    )
    objetos = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(conteudo.encode('latin-1'))} >>\nstream\n{conteudo}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    saida = b"%PDF-1.4\n"
    posicoes = []
    for i, objeto in enumerate(objetos, 1):
        posicoes.append(len(saida))
        saida += f"{i} 0 obj\n{objeto}\nendobj\n".encode("latin-1")
    xref = len(saida)
    saida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    saida += b"".join(f"{p:010d} 00000 n \n".encode() for p in posicoes)
    rodape = f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF"
    return saida + rodape.encode()


def test_ingestao_de_arquivos_pdf_docx_txt(tmp_path):
    import docx

    (tmp_path / "a.txt").write_text(SENTENCA_PROCEDENTE, encoding="utf-8")
    documento = docx.Document()
    for linha in SENTENCA_PROCEDENTE.splitlines():
        documento.add_paragraph(linha)
    documento.save(tmp_path / "b.docx")
    (tmp_path / "c.pdf").write_bytes(
        _pdf_com_texto([f"Processo {CNJ_TJSP}", "Decido.", "Ante o exposto, JULGO IMPROCEDENTE."])
    )
    (tmp_path / "vazio.txt").write_text("   ", encoding="utf-8")

    resultados = {caminho.name: (doc, prov) for doc, caminho, prov in arquivos.coletar(tmp_path)}
    assert resultados["a.txt"][0].resultado == "procedente"
    assert resultados["a.txt"][0].tribunal == "tjsp"
    assert resultados["b.docx"][0].resultado == "procedente"
    assert resultados["c.pdf"][0].resultado == "improcedente"
    assert resultados["vazio.txt"][0] is None
    assert "JOÃO CARLOS" not in resultados["b.docx"][0].texto


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        ("2026-09-30", "2026-09-30"),
        ("2026-09-30T10:00:00", "2026-09-30"),
        ("30/09/2026", "2026-09-30"),
        (None, None),
    ],
)
def test_data_do_djen(bruto, esperado):
    assert djen._data_iso(bruto) == esperado


def test_estrutura_do_sondar_nao_mostra_valores():
    from dikemetria.cli import estrutura

    item = {
        "texto": "Fulano de Tal",
        "id": 7,
        "datadisponibilizacao": "30/09/2026",
        "destinatarios": [{"nome": "Fulano", "polo": "A"}],
        "ativo": True,
        "link": None,
    }
    esqueleto = estrutura(item)
    assert "Fulano" not in str(esqueleto)
    assert esqueleto["destinatarios"] == [{"nome": "texto", "polo": "texto"}]
    assert esqueleto["datadisponibilizacao"] == "texto (dd/mm/aaaa)"
    assert esqueleto["link"] == "nulo" and esqueleto["ativo"] == "lógico"
