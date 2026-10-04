"""Município da unidade: só código do IBGE confirmado, nunca a numeração própria do tribunal."""

import sqlite3

from dikemetria import municipios
from dikemetria.coleta import datajud
from dikemetria.coleta.tribunais import selecionar
from dikemetria.corpus import Corpus

from .conftest import hit_datajud

RN = ("rn",)


def test_lista_do_ibge():
    lista = municipios.municipios()
    assert len(lista) >= 5570
    assert lista[2408102].nome == "Natal" and lista[2408102].capital
    assert lista[3550308].uf == "sp"


def test_codigo_ibge_valido_e_da_uf_do_tribunal():
    assert municipios.resolver(2408003, "1ª Vara Cível", RN) == (2408003, "ibge")
    assert municipios.resolver("2408003", None, RN) == (2408003, "ibge")
    # Código de outra UF não vale para o TJRN.
    assert municipios.resolver(3550308, "1ª Vara Cível", RN) == (None, "não resolvido")


def test_numeracao_propria_do_tribunal_vira_nome_do_orgao_ou_vazio():
    assert municipios.resolver(3576, "1ª VARA CÍVEL", RN) == (None, "não resolvido")
    assert municipios.resolver(3576, "Vara Única da Comarca de Touros", RN) == (
        2414407,
        "nome do órgão",
    )
    # O nome mais longo vence ("São José de Mipibu", não "São José").
    codigo, _ = municipios.resolver(None, "JUIZADO ESPECIAL DA COMARCA DE SÃO JOSÉ DE MIPIBU", RN)
    assert municipios.municipios()[codigo].nome == "São José de Mipibu"


def test_municipio_no_fim_do_nome_do_orgao():
    trf1 = selecionar(["trf1"])[0].ufs
    assert municipios.municipio_no_nome("15ª Vara JEF - Salvador", trf1) == 2927408
    assert municipios.municipio_no_nome("1ª TR - R3 - São Luís", trf1) == 2111300
    ms = ("ms",)
    assert municipios.municipio_no_nome("2ª Vara do Juizado Especial de Dourados", ms) == 5003702
    for sem_municipio in ("Gabinete 09", "28ª Vara Federal", "Vara de Família"):
        assert municipios.municipio_no_nome(sem_municipio, trf1) is None


def test_ufs_dos_tribunais():
    assert selecionar(["tjrn"])[0].ufs == ("rn",)
    # "tjma", "tjms", "tjmt" e "tjmg" começam por "tjm", mas não são tribunais militares.
    assert [selecionar([s])[0].ufs for s in ("tjma", "tjms", "tjmt", "tjmg")] == [
        ("ma",),
        ("ms",),
        ("mt",),
        ("mg",),
    ]
    assert selecionar(["tjdft"])[0].ufs == ("df",)
    assert selecionar(["tre-df"])[0].ufs == ("df",)
    assert selecionar(["tjmsp"])[0].ufs == ("sp",)
    assert "pe" in selecionar(["trf5"])[0].ufs
    assert selecionar(["trt15"])[0].ufs == ("sp",)
    assert selecionar(["stj"])[0].ufs == ()


def test_processo_guarda_codigo_original_e_orgao():
    orgao = {"codigo": 5877, "nome": "1ª VARA CÍVEL", "codigoMunicipioIBGE": 3576}
    processo = datajud.converter_processo(
        hit_datajud("1", [], [1], orgaoJulgador=orgao)["_source"], "tjrn"
    )
    assert processo.municipio_ibge is None
    assert processo.municipio_codigo == "3576"
    assert processo.municipio_metodo == "não resolvido"
    assert processo.orgao_codigo == 5877


def test_banco_antigo_ganha_as_colunas_novas(tmp_path):
    caminho = tmp_path / "antigo.sqlite"
    with sqlite3.connect(caminho) as conexao:
        conexao.execute(
            "CREATE TABLE processos (tribunal TEXT NOT NULL, numero TEXT NOT NULL, grau TEXT NOT "
            "NULL DEFAULT '', classe_codigo INTEGER, classe_nome TEXT, assuntos TEXT, "
            "municipio_ibge INTEGER, data_ajuizamento TEXT, data_julgamento TEXT, duracao_dias "
            "INTEGER, resultado TEXT NOT NULL, evidencia TEXT, sensivel INTEGER NOT NULL "
            "DEFAULT 0, proveniencia TEXT, PRIMARY KEY (tribunal, numero, grau))"
        )
    processo = datajud.converter_processo(hit_datajud("1", [], [1])["_source"], "tjsp")
    with Corpus(caminho) as corpus:
        corpus.gravar_processos([processo])
        linha = next(corpus.processos())
    assert linha["municipio_ibge"] == 3550308
    assert linha["municipio_metodo"] == "ibge"
    assert linha["orgao_codigo"] == 1234


def test_tabela_de_conversao_do_tribunal(monkeypatch):
    assert municipios.conversoes() == {}  # a tabela versionada ainda está vazia
    monkeypatch.setattr(municipios, "conversoes", lambda: {("tjrn", "3576"): 2408102})
    assert municipios.resolver(3576, "3ª VARA CÍVEL", RN, "tjrn") == (2408102, "tabela")
    assert municipios.resolver(3576, "3ª VARA CÍVEL", RN, "trf5") == (None, "não resolvido")
