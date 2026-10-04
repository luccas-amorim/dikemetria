from dikemetria import estrutura, referencias
from dikemetria.analise import analisar_documento, contar_termos
from dikemetria.coleta.tribunais import TRIBUNAIS, selecionar, tribunal_por_cnj
from dikemetria.limpeza import tokenizar, tokens_relevantes

from .conftest import CNJ_TJSP, CNJ_TRF4, SENTENCA_IMPROCEDENTE, SENTENCA_PROCEDENTE


def test_tokenizar_preserva_acentos_e_hifens():
    # O código antigo apagava â, ê, ô e hífens: "três" virava "trs".
    assert tokenizar("Três meses; boa-fé objetiva, à vista") == [
        "três",
        "meses",
        "boa-fé",
        "objetiva",
        "à",
        "vista",
    ]


def test_tokens_relevantes_remove_stopwords_e_ruido():
    assert tokens_relevantes("O autor juntou aos autos as fls. 10 da inicial") == [
        "autor",
        "juntou",
        "inicial",
    ]


def test_citacoes_normalizadas():
    texto = (
        "Nos termos do art. 14 do CDC, do art. 5º, X, da CF/88 e dos arts. 373, II, do CPC; "
        "art. 42, parágrafo único, da Lei nº 8.078/90; Art. 1.022 do CPC; Lei 9.099/95; "
        "Súmula 385 do STJ; Súmula Vinculante 10; Tema 1.061 do STJ."
    )
    refs = [c.referencia for c in referencias.citacoes(texto)]
    assert refs == [
        "art. 14 CDC",
        "art. 5 CF",
        "art. 373 CPC",
        "art. 42 CDC",
        "art. 1.022 CPC",
        "Lei 9.099/1995",
        "Súmula 385 STJ",
        "Súmula Vinculante 10",
        "Tema 1.061 STJ",
    ]


def test_numero_cnj_confere_digito_verificador():
    assert referencias.numeros_cnj(f"Processo {CNJ_TJSP} e 1001234-11.2023.8.26.0100") == [CNJ_TJSP]
    assert referencias.digito_cnj_valido(CNJ_TRF4)


def test_tribunal_pelo_numero_cnj():
    assert tribunal_por_cnj(CNJ_TJSP) == "tjsp"
    assert tribunal_por_cnj(CNJ_TRF4) == "trf4"
    assert tribunal_por_cnj("0000001-00.2020.5.02.0001") == "trt2"
    assert tribunal_por_cnj("0000001-00.2020.8.07.0001") == "tjdft"
    assert tribunal_por_cnj("sem número") is None


def test_lista_de_tribunais_cobre_o_pais():
    assert len(TRIBUNAIS) == 91
    assert len(selecionar(["estadual"])) == 27
    assert len(selecionar(["trabalho", "tjsp"])) == 25


def test_divide_relatorio_fundamentacao_dispositivo():
    secoes = estrutura.dividir(SENTENCA_PROCEDENTE)
    assert secoes.dispositivo_localizado
    assert secoes.relatorio.endswith("Fundamento e decido.")
    assert "relação é de consumo" in secoes.fundamentacao
    assert secoes.dispositivo.startswith("Ante o exposto, JULGO PROCEDENTE")


def test_termos_com_varias_palavras():
    termos = contar_termos("O ônus da prova e a boa-fé; danos morais e Danos Morais.")
    assert termos == {"danos morais": 2, "boa-fé": 1, "ônus da prova": 1}


def test_analise_de_documento_completa():
    # O pipeline antigo quebrava aqui: desempacotava um dict de 5 chaves em 2 variáveis.
    analise = analisar_documento(SENTENCA_PROCEDENTE)
    assert analise.resultado == "procedente"
    assert analise.numeros_processo == [CNJ_TJSP]
    assert analise.citacoes["art. 14 CDC"] == 1
    assert "Súmula 385 STJ" in analise.citacoes
    assert analise.termos_juridicos["ônus da prova"] == 1
    assert any("Isso porque" in a for a in analise.argumentos)
    assert analisar_documento(SENTENCA_IMPROCEDENTE).resultado == "improcedente"


def test_tre_do_df_usa_o_indice_que_existe_no_datajud():
    siglas = {t.sigla for t in TRIBUNAIS}
    assert "tre-df" in siglas and "tre-dft" not in siglas
    assert tribunal_por_cnj("0600001-00.2024.6.07.0001") == "tre-df"
