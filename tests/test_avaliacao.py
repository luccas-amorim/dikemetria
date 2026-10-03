"""Regras de avaliação do dispositivo (docs/REGRAS.md) contra o conjunto-referência."""

import csv
from pathlib import Path

import pytest

from dikemetria.avaliacao import avaliar, avaliar_dispositivo, capitulos, unanimidade

REFERENCIA = Path(__file__).parent / "dados" / "dispositivos.csv"
CASOS = list(csv.DictReader(open(REFERENCIA, encoding="utf-8")))


@pytest.mark.parametrize("caso", CASOS, ids=[c["dispositivo"][:50] for c in CASOS])
def test_conjunto_referencia(caso):
    avaliacao = avaliar_dispositivo(caso["dispositivo"])
    assert avaliacao.resultado.value == caso["resultado"]
    acao = avaliacao.resultado_acao.value if avaliacao.resultado_acao else ""
    assert acao == caso["resultado_acao"]
    assert caso["motivo_contem"] in (avaliacao.motivo or "")
    assert avaliacao.tipo_decisao == caso["tipo"]


def test_objetos_dos_capitulos():
    caps = capitulos(
        "Julgo improcedente a reconvenção, procedente o pedido contraposto e procedente o pedido "
        "inicial. Rejeito os embargos de declaração."
    )
    assert [(c.resultado.value, c.objeto) for c in caps] == [
        ("improcedente", "reconvencao"),
        ("procedente", "pedido_contraposto"),
        ("procedente", "acao"),
        ("nao_provido", "embargos_declaracao"),
    ]


def test_comando_fraco_so_vale_sem_forte():
    sozinho = avaliar_dispositivo("Sentença mantida por seus próprios fundamentos.")
    assert sozinho.resultado.value == "nao_provido" and sozinho.confianca == "baixa"
    junto = avaliar_dispositivo("Dou parcial provimento ao recurso. No mais, mantenho a sentença.")
    assert junto.resultado.value == "parcialmente_provido" and junto.confianca == "alta"


def test_confianca():
    assert avaliar_dispositivo("Julgo procedente o pedido.").confianca == "alta"
    assert avaliar_dispositivo("Pronuncio a prescrição.").confianca == "media"
    assert avaliar_dispositivo("Condeno o réu a pagar R$ 100,00.").confianca == "baixa"
    assert avaliar_dispositivo("Cite-se.").confianca == "baixa"


def test_unanimidade():
    assert unanimidade("ACORDAM, por unanimidade, negar provimento.") is True
    assert unanimidade("Por maioria, deram provimento, vencido o relator.") is False
    assert unanimidade("Negaram provimento.") is None


def test_serializa_para_o_banco():
    dados = avaliar_dispositivo("Julgo procedente o pedido.").como_dict()
    assert dados["resultado"] == "procedente"
    assert dados["capitulos"][0] == {
        "resultado": "procedente",
        "objeto": "acao",
        "forca": "forte",
        "trecho": "procedente",
        "motivo": None,
    }


ACORDAO_COM_VENCIDO = """APELAÇÃO CÍVEL. Relator: [PESSOA_1]
ACÓRDÃO
Vistos, relatados e discutidos estes autos, ACORDAM, por maioria, em negar provimento ao recurso,
vencido o 3º Juiz, que declarará voto.
VOTO
Trata-se de apelação contra sentença de improcedência.
É o relatório.
O contrato foi juntado e a dívida está comprovada.
Ante o exposto, nego provimento ao recurso.
DECLARAÇÃO DE VOTO VENCIDO
Divirjo da douta maioria. A assinatura não foi periciada.
Ante o exposto, dou provimento ao recurso para julgar procedente o pedido.
"""

ACORDAO_RELATOR_VENCIDO = """ACÓRDÃO
ACORDAM, por maioria, em dar provimento ao recurso, vencido o Relator.
VOTO DO RELATOR
É o relatório.
A sentença deve ser mantida.
Ante o exposto, nego provimento ao recurso.
"""

ACORDAO_COM_CONDENACAO = """ACÓRDÃO
ACORDAM, por unanimidade, em dar provimento ao recurso.
VOTO
É o relatório.
A negativação foi indevida.
Ante o exposto, dou provimento ao recurso para julgar procedente o pedido e condenar a ré ao
pagamento de R$ 10.000,00 a título de danos morais, com juros desde o evento danoso.
"""


def test_voto_vencido_nao_decide():
    avaliacao, dispositivo = avaliar(ACORDAO_COM_VENCIDO)
    assert avaliacao.resultado.value == "nao_provido"
    assert avaliacao.resultado_acao is None
    assert avaliacao.unanimidade is False
    assert "dou provimento" not in dispositivo


def test_acordam_prevalece_sobre_voto_do_relator_vencido():
    avaliacao, _ = avaliar(ACORDAO_RELATOR_VENCIDO)
    assert avaliacao.resultado.value == "provido"
    assert "prevalece o ACORDAM" in avaliacao.motivo


def test_acordao_com_condenacao_mantem_detalhes_do_voto():
    from dikemetria.valores import calcular

    avaliacao, dispositivo = avaliar(ACORDAO_COM_CONDENACAO)
    assert avaliacao.resultado.value == "provido"
    assert avaliacao.resultado_acao.value == "procedente"
    assert avaliacao.unanimidade is True
    assert calcular(dispositivo).total("danos_morais") == 10000.0
