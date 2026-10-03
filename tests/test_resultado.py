import pytest

from dikemetria.resultado import (
    Resultado,
    classificar_movimento,
    classificar_movimentos,
    classificar_texto,
)

R = Resultado


@pytest.mark.parametrize(
    ("dispositivo", "esperado"),
    [
        ("Ante o exposto, JULGO PROCEDENTE o pedido", R.PROCEDENTE),
        ("julgo procedentes os pedidos formulados", R.PROCEDENTE),
        ("JULGO IMPROCEDENTES os pedidos", R.IMPROCEDENTE),
        ("Rejeito os pedidos e julgo extinto com resolução do mérito", R.IMPROCEDENTE),
        ("julgo PARCIALMENTE PROCEDENTES os pedidos", R.PARCIALMENTE_PROCEDENTE),
        ("julgo procedente em parte a ação", R.PARCIALMENTE_PROCEDENTE),
        ("JULGO EXTINTO o processo, sem resolução do mérito (art. 485, VI)", R.EXTINTO_SEM_MERITO),
        ("Homologo, por sentença, o acordo celebrado entre as partes", R.HOMOLOGACAO_ACORDO),
        ("Acordam em negar provimento ao recurso", R.NAO_PROVIDO),
        ("Recurso não provido.", R.NAO_PROVIDO),
        ("deram parcial provimento ao recurso", R.PARCIALMENTE_PROVIDO),
        ("Dou provimento ao recurso para reformar a sentença", R.PROVIDO),
        ("Recurso provido.", R.PROVIDO),
        ("Não conheço do recurso.", R.NAO_CONHECIDO),
        ("Intime-se a parte para se manifestar.", R.INDETERMINADO),
        ("julgo improcedente a reconvenção e procedente o pedido inicial", R.INDETERMINADO),
    ],
)
def test_classificar_texto(dispositivo, esperado):
    assert classificar_texto(dispositivo).resultado == esperado


@pytest.mark.parametrize(
    ("codigo", "nome", "esperado"),
    [
        (219, "Procedência", R.PROCEDENTE),
        (220, "Improcedência", R.IMPROCEDENTE),
        (221, "Procedência em Parte", R.PARCIALMENTE_PROCEDENTE),
        (None, "Não-Provimento", R.NAO_PROVIDO),
        (None, "Provimento em Parte", R.PARCIALMENTE_PROVIDO),
        (None, "Provimento", R.PROVIDO),
        (None, "Homologação de Transação", R.HOMOLOGACAO_ACORDO),
        (None, "Desistência", R.EXTINTO_SEM_MERITO),
        (None, "Concessão da Antecipação de tutela", None),
        (None, "Acolhimento de Embargos de Declaração", None),
        (11010, "Mero expediente", None),
    ],
)
def test_classificar_movimento(codigo, nome, esperado):
    assert classificar_movimento(codigo, nome) == esperado


def test_primeiro_julgamento_em_ordem_cronologica():
    movimentos = [
        {"codigo": 219, "nome": "Procedência", "dataHora": "2023-05-01T10:00:00"},
        {"codigo": 26, "nome": "Distribuição", "dataHora": "2021-03-10T10:00:00"},
        {"codigo": 220, "nome": "Improcedência", "dataHora": "2022-08-15T10:00:00"},
    ]
    classificacao, data = classificar_movimentos(movimentos)
    assert classificacao.resultado == R.IMPROCEDENTE
    assert data == "2022-08-15T10:00:00"


def test_sem_julgamento():
    classificacao, data = classificar_movimentos([{"codigo": 26, "nome": "Distribuição"}])
    assert classificacao.resultado == R.INDETERMINADO and data is None
