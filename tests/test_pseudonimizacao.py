"""Testes que comprovam a remoção de dados pessoais (README, "Para onde vai")."""

from dikemetria.pseudonimizacao import pseudonimizar, residuos

from .conftest import SENTENCA_PROCEDENTE


def test_remove_nomes_documentos_e_endereco():
    resultado = pseudonimizar(SENTENCA_PROCEDENTE)
    texto = resultado.texto
    for dado in (
        "JOÃO CARLOS DA SILVA",
        "123.456.789-09",
        "Rua das Flores",
        "01234-567",
        "Ana Beatriz Costa",
    ):
        assert dado not in texto
    assert residuos(texto) == []
    assert resultado.substituicoes["CPF"] == 1
    assert resultado.substituicoes["PESSOA"] >= 3


def test_mantem_pessoas_juridicas_e_termos_da_decisao():
    texto = pseudonimizar(SENTENCA_PROCEDENTE).texto
    assert "BANCO EXEMPLO S.A." in texto
    assert "JULGO PROCEDENTE" in texto
    assert "art. 14 do CDC" in texto
    assert "Juíza de Direito" in texto


def test_mesmo_nome_recebe_o_mesmo_marcador():
    texto = pseudonimizar(SENTENCA_PROCEDENTE).texto
    assert texto.count("[PESSOA_1]") >= 2  # autor no cabeçalho e na qualificação


def test_nomes_conhecidos_em_qualquer_caixa():
    texto = "A parte Pedro Henrique Alves compareceu. PEDRO HENRIQUE ALVES assinou."
    resultado = pseudonimizar(texto, nomes_conhecidos=["Pedro Henrique Alves"])
    assert "Pedro" not in resultado.texto and "PEDRO" not in resultado.texto


def test_documentos_diversos():
    texto = (
        "RG nº 12.345.678-9, OAB/SP 123.456, e-mail fulano@exemplo.com.br, "
        "telefone (11) 98765-4321, conta corrente nº 12345-6, Avenida Brasil, 1000."
    )
    resultado = pseudonimizar(texto).texto
    for marcador in ("[RG]", "[OAB]", "[EMAIL]", "[TELEFONE]", "[CONTA]", "[ENDERECO]"):
        assert marcador in resultado
    assert residuos(resultado) == []


def test_nao_confunde_numero_cnj_com_telefone():
    texto = "Processo nº 1001234-88.2023.8.26.0100"
    assert pseudonimizar(texto).texto == texto


def test_papeis_encadeados_e_nome_antes_do_cargo():
    texto = "Relator Desembargador FULANO BELTRANO\nCarlos Eduardo Lima\nJuiz de Direito"
    resultado = pseudonimizar(texto).texto
    assert "FULANO" not in resultado and "Carlos" not in resultado


# Formatos dos autos do eproc, vistos num processo piloto. Nomes e números fictícios.


def test_pessoa_juridica_qualificada_fica_no_texto():
    texto = (
        "em face de EXEMPLO VAREJO DO BRASIL S.A., inscrita no CNPJ sob o nº "
        "12.345.678/0001-90. RÉU: EXEMPLO VAREJO DO BRASIL S.A .\n"
        "Citada, a ré Exemplo Varejo do Brasil S/A, inscrito no CNPJ, contestou."
    )
    resultado = pseudonimizar(texto).texto
    assert "EXEMPLO VAREJO DO BRASIL S.A." in resultado
    assert "Exemplo Varejo do Brasil S/A" in resultado
    assert "[PESSOA" not in resultado


def test_advogados_no_formato_do_eproc():
    texto = (
        "Procurador(es):\n"
        "FULANO DE TAL BELTRANO RJ123456\n"
        "Usuário:\nSP654321 - CICRANO SOUZA LIMA - ADVOGADO\n"
        "Requer intimações em nome de Fulano de Tal Beltrano, (OAB/RJ 123.456, a@b.com).\n"
        "Rio de Janeiro, 25 de junho de 2026\n"
        "Fulano de Tal Beltrano              Mévio Prado Nunes\n"
        "OAB/RJ 123.456                      OAB/RJ 222.333\n"
        "Procurador Citado/Intimado:\nCICRANO SOUZA LIMA, MÉVIO PRADO NUNES\n"
    )
    resultado = pseudonimizar(texto).texto
    for nome in ("FULANO", "Fulano", "CICRANO", "Mévio", "MÉVIO"):
        assert nome not in resultado
    assert "RJ123456" not in resultado and "SP654321" not in resultado
    assert residuos(resultado) == []


def test_conectivos_e_expressoes_nao_viram_pessoa():
    texto = (
        "EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO DA 2ª VARA CÍVEL\n"
        "APELO DO RÉU PELA IMPROCEDÊNCIA - INCONFORMISMO\n"
        "Fatos constitutivos da Autora."
    )
    resultado = pseudonimizar(texto).texto
    assert "JUIZ DE DIREITO DA 2ª VARA" in resultado
    assert "PELA IMPROCEDÊNCIA" in resultado
    assert "[PESSOA" not in resultado
