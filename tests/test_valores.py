import pytest

from dikemetria.valores import calcular

DISPOSITIVO = (
    "Ante o exposto, JULGO PROCEDENTE o pedido para: a) declarar inexigível o débito de "
    "R$ 1.234,56; b) condenar o réu a restituir em dobro os valores descontados, no total de "
    "R$ 2.469,12, com correção monetária pelo IPCA desde cada desconto e juros de mora pela taxa "
    "Selic a partir da citação; c) condenar o réu ao pagamento de R$ 8.000,00 (oito mil reais) a "
    "título de indenização por danos morais, corrigidos desde o arbitramento (Súmula 362 do STJ) "
    "e com juros desde o evento danoso (Súmula 54). Fixo multa diária de R$ 500,00. Condeno o réu "
    "nas custas e honorários advocatícios, que fixo em 15% sobre o valor atualizado da condenação."
)


def test_valores_por_categoria():
    calculo = calcular(DISPOSITIVO)
    assert [(v.categoria, v.valor) for v in calculo.valores] == [
        ("debito_inexigivel", 1234.56),
        ("restituicao", 2469.12),
        ("danos_morais", 8000.0),
        ("multa", 500.0),
    ]
    assert calculo.total("danos_morais") == 8000.0
    assert calculo.total("lucros_cessantes") is None


def test_parametros_de_calculo():
    calculo = calcular(DISPOSITIVO)
    assert calculo.honorarios_percentual == 15.0
    assert calculo.honorarios_base == "valor da condenação"
    assert calculo.repeticao == "em dobro"
    assert calculo.juros_termos_iniciais == ["citação", "evento danoso"]
    assert calculo.juros_taxa == "Selic"
    assert calculo.correcao_termos_iniciais == ["desembolso", "arbitramento"]
    assert calculo.correcao_indice == "IPCA"
    assert not calculo.gratuidade


@pytest.mark.parametrize(
    ("trecho", "esperado"),
    [
        ("R$ 10.000,00", 10000.0),
        ("R$ 10 mil", 10000.0),
        ("R$ 1,5", 1.5),
        ("R$ 2 milhões", 2_000_000.0),
        ("R$ 350", 350.0),
    ],
)
def test_formatos_de_moeda(trecho, esperado):
    assert (
        calcular(f"condeno ao pagamento de {trecho} por danos morais").valores[0].valor == esperado
    )


def test_honorarios_por_extenso_e_gratuidade():
    calculo = calcular(
        "Condeno a autora em honorários de dez por cento do valor da causa, observada a "
        "gratuidade (art. 98, § 3º, do CPC)."
    )
    assert calculo.honorarios_percentual == 10.0
    assert calculo.honorarios_base == "valor da causa"
    assert calculo.gratuidade


def test_repeticao_simples_e_valor_por_autor():
    calculo = calcular(
        "Condeno a ré a restituir, de forma simples, os valores pagos, e a pagar R$ 3.000,00 para "
        "cada autor a título de danos morais."
    )
    assert calculo.repeticao == "simples"
    assert calculo.valor_por_autor
