"""A guarda do repositório barra autos, bancos e documentos reais (CPF, CNPJ, CNJ válidos)."""

import json

import pytest

from dikemetria.guarda import cnj_valido, cnpj_valido, cpf_valido, verificar_arquivo

# Documentos válidos montados em partes, para que o próprio teste passe pela guarda.
CPF = "111.444." + "777-35"
CNPJ = "11.222.333/" + "0001-81"
CNJ = "0000001-39." + "2024.8.26.0100"


def test_digitos_verificadores():
    assert cpf_valido(CPF.replace(".", "").replace("-", ""))
    assert not cpf_valido("111444" + "77736")
    assert not cpf_valido("11111111111")
    assert cnpj_valido("11222333" + "000181")
    assert not cnpj_valido("11222333" + "000180")
    assert cnj_valido("0000001", "39", "2024", "8", "26", "0100")
    assert not cnj_valido("0000001", "40", "2024", "8", "26", "0100")


@pytest.mark.parametrize(
    "caminho",
    [
        "docs/processo-temp/autos.pdf",
        "notas/decisao.docx",
        "dados/corpus.sqlite",
        "saida/relatorio.csv",
        "fotos/peticao.jpg",
    ],
)
def test_barra_documentos_e_caminhos_de_dados(caminho):
    assert verificar_arquivo(caminho, b"x")


def test_barra_documentos_validos_no_texto_e_aceita_ficticios():
    real = f"inscrita no CPF {CPF} e no CNPJ {CNPJ}, processo {CNJ}"
    motivos = [a.motivo for a in verificar_arquivo("docs/nota.md", real.encode())]
    assert len(motivos) == 3
    ficticio = "CPF 123.456.789-09, CPF 123.456.789-00, CNPJ 12.345.678/0001-90"
    assert verificar_arquivo("tests/caso.py", ficticio.encode()) == []


def test_barra_arquivo_grande_e_notebook_com_saida():
    assert verificar_arquivo("docs/grande.md", b"a" * 1_000_001)
    com_saida = {"cells": [{"cell_type": "code", "outputs": [{"text": "JULGO PROCEDENTE"}]}]}
    sem_saida = {"cells": [{"cell_type": "code", "outputs": []}]}
    assert verificar_arquivo("notebooks/a.ipynb", json.dumps(com_saida).encode())
    assert verificar_arquivo("notebooks/b.ipynb", json.dumps(sem_saida).encode()) == []


def test_codigo_comum_passa():
    assert verificar_arquivo("dikemetria/x.py", b'NUMERO = "12345"\n') == []
