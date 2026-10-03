import csv
import json
import math
import random

import pytest

from dikemetria import estatistica, jurimetria, politica
from dikemetria.cli import main
from dikemetria.coleta.datajud import Processo
from dikemetria.coleta.djen import converter_documento
from dikemetria.corpus import Corpus
from dikemetria.relatorio import gerar
from dikemetria.validacao import avaliar, gerar_amostra

from .conftest import CNJ_TJSP, SENTENCA_IMPROCEDENTE, SENTENCA_PROCEDENTE


def test_wilson():
    p, lo, hi = estatistica.wilson(50, 100)
    assert p == 0.5
    assert lo == pytest.approx(0.4038, abs=1e-4) and hi == pytest.approx(0.5962, abs=1e-4)
    assert all(math.isnan(v) for v in estatistica.wilson(0, 0))


def test_quantis():
    assert estatistica.mediana([3, 1, 2, 4]) == 2.5
    assert estatistica.quantil([1, 2, 3, 4, 5], 0.25) == 2


def test_log_odds_aponta_o_lado_certo():
    a = ["contrato"] * 20 + ["desconhece"] * 300 + ["dano"] * 200
    b = ["contrato"] * 300 + ["desconhece"] * 20 + ["dano"] * 200
    escores = {p: z for p, z, _, _ in estatistica.log_odds_dirichlet(a, b, minimo=1)}
    assert escores["desconhece"] > 2 > -2 > escores["contrato"]
    assert abs(escores["dano"]) < 1


def _processo(i: int, tribunal: str, resultado: str, ano: int = 2022) -> Processo:
    return Processo(
        tribunal=tribunal,
        numero=f"{i:020d}",
        grau="G1",
        classe_codigo=7,
        classe_nome="Procedimento Comum Cível",
        assuntos=[{"codigo": 6226, "nome": "Inclusão Indevida em Cadastro de Inadimplentes"}],
        data_ajuizamento="2021-01-01",
        data_julgamento=f"{ano}-06-01",
        resultado=resultado,
    )


@pytest.fixture
def corpus(tmp_path):
    sorteio = random.Random(1)
    with Corpus(tmp_path / "corpus.sqlite") as corpus:
        processos = []
        for i in range(300):
            tribunal = sorteio.choice(["tjsp", "tjrj", "tjmg"])
            resultado = sorteio.choices(
                ["procedente", "parcialmente_procedente", "improcedente", "extinto_sem_merito"],
                weights=[4, 2, 3, 1],
            )[0]
            processos.append(_processo(i, tribunal, resultado))
        processos.append(_processo(999, "tjac", "procedente"))  # grupo pequeno: suprimido
        corpus.gravar_processos(processos)
        documentos = []
        for i in range(30):
            texto = SENTENCA_PROCEDENTE if i % 2 else SENTENCA_IMPROCEDENTE
            doc = converter_documento(
                {"id": i, "texto": texto, "numero_processo": CNJ_TJSP}, "tjsp"
            )
            documentos.append(doc)
        corpus.gravar_documentos(documentos)
        yield corpus


def test_taxas_suprimem_grupos_pequenos(corpus):
    linhas = jurimetria.taxas(list(corpus.processos()), "tribunal")
    grupos = {linha["grupo"] for linha in linhas}
    assert {"TJSP", "TJRJ", "TJMG"} <= grupos and "TJAC" not in grupos
    for linha in linhas:
        assert linha["merito"] >= politica.MINIMO_PUBLICAVEL
        assert linha["acolhimento_ic_inf"] <= linha["acolhimento"] <= linha["acolhimento_ic_sup"]
        assert linha["procedencia"] <= linha["acolhimento"]


def test_citacoes_e_vocabulario(corpus):
    documentos = list(corpus.documentos())
    citacoes = {c["citacao"]: c for c in jurimetria.citacoes_por_resultado(documentos)}
    assert citacoes["art. 14 CDC"]["em_acolhidos"] == 1.0
    assert citacoes["art. 14 CDC"]["em_rejeitados"] == 0.0
    assert citacoes["Súmula 385 STJ"]["em_rejeitados"] == 1.0
    vocab = jurimetria.vocabulario(documentos)
    acolhido = [v["palavra"] for v in vocab["acolhido"]]
    assert "procedente" not in acolhido and "pessoa" not in acolhido


def test_relatorio_publica_so_agregados(corpus, tmp_path):
    pagina = gerar(corpus, tmp_path / "saida", "Teste", "Recorte de teste")
    html = pagina.read_text(encoding="utf-8")
    assert "<svg" in html and "prefers-color-scheme: dark" in html
    assert "Acolhimento do pedido por tribunal" in html
    for proibido in ("JOÃO", "Ana Beatriz", CNJ_TJSP, "TJAC"):
        assert proibido not in html
    saida = tmp_path / "saida"
    with open(saida / "taxas_tribunal.csv", encoding="utf-8") as arquivo:
        assert {linha["grupo"] for linha in csv.DictReader(arquivo)} == {"TJSP", "TJRJ", "TJMG"}
    metadados = json.loads((saida / "metadados.json").read_text(encoding="utf-8"))
    assert metadados["licenca"] == "CC BY 4.0"
    assert (saida / "DICIONARIO.md").exists()


def test_relatorio_de_corpus_vazio(tmp_path):
    with Corpus(tmp_path / "vazio.sqlite") as corpus:
        html = gerar(corpus, tmp_path / "saida").read_text(encoding="utf-8")
    assert "O corpus ainda está vazio" in html


def test_amostra_e_validacao(corpus, tmp_path):
    caminho = tmp_path / "amostra.csv"
    assert gerar_amostra(list(corpus.documentos()), 10, caminho) == 10
    linhas = list(csv.DictReader(open(caminho, encoding="utf-8")))
    for linha in linhas:
        linha["resultado_manual"] = linha["resultado_automatico"]
    linhas[0]["resultado_manual"] = "parcialmente_procedente"
    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0]))
        escritor.writeheader()
        escritor.writerows(linhas)
    metricas = avaliar(caminho)
    assert metricas.n == 10 and metricas.acuracia == pytest.approx(0.9)


def test_cursor_de_retomada(corpus):
    corpus.salvar_cursor("datajud", "r", "tjsp", [123, "x"])
    assert corpus.cursor("datajud", "r", "tjsp") == ([123, "x"], False)
    corpus.salvar_cursor("datajud", "r", "tjsp", None, concluido=True)
    assert corpus.cursor("datajud", "r", "tjsp") == (None, True)


def test_cli_ponta_a_ponta(tmp_path, capsys):
    pasta = tmp_path / "decisoes"
    pasta.mkdir()
    (pasta / "a.txt").write_text(SENTENCA_PROCEDENTE, encoding="utf-8")
    (pasta / "b.txt").write_text(SENTENCA_IMPROCEDENTE, encoding="utf-8")
    banco = str(tmp_path / "corpus.sqlite")

    assert (
        main(
            [
                "analisar",
                str(pasta / "a.txt"),
                "--json",
                str(tmp_path / "a.json"),
                "--svg",
                str(tmp_path / "a.svg"),
            ]
        )
        == 0
    )
    analise = json.loads((tmp_path / "a.json").read_text(encoding="utf-8"))
    assert analise["resultado"] == "procedente"
    assert (tmp_path / "a.svg").read_text(encoding="utf-8").startswith("<svg xmlns=")

    assert main(["coletar", "--fonte", "arquivos", "--pasta", str(pasta), "--banco", banco]) == 0
    assert "2 documentos gravados" in capsys.readouterr().out
    assert main(["classificar", "--banco", banco]) == 0
    assert (
        main(
            [
                "relatorio",
                "--banco",
                banco,
                "--saida",
                str(tmp_path / "saida"),
                "--recorte",
                "recortes/exemplo.toml",
            ]
        )
        == 0
    )
    assert (tmp_path / "saida" / "relatorio.html").exists()
