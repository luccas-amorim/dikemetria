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
        ("julgo improcedente a reconvenção e procedente o pedido inicial", R.PROCEDENTE),
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
        # Extinções do JEC (Lei 9.099, art. 51), vistas numa coleta real no TJRN.
        (11376, "Ausência do autor à audiência", R.EXTINTO_SEM_MERITO),
        (11377, "Inadmissibilidade do procedimento sumaríssimo", R.EXTINTO_SEM_MERITO),
        (11378, "Incompetência territorial", R.EXTINTO_SEM_MERITO),
        (None, "Incompetência territorial", None),  # fora do JEC, leva à remessa, não à extinção
        # Auditoria dos movimentos usados nos 91 tribunais (DataJud, outubro de 2026).
        (12435, "Conhecimento para negar provimento ao recurso especial", R.NAO_PROVIDO),
        (
            12438,
            "conhecimento para dar parcial provimento ao recurso especial",
            R.PARCIALMENTE_PROVIDO,
        ),
        (12434, "Conhecimento para dar provimento ao Recurso Especial", R.PROVIDO),
        (12436, "Conhecimento para não conhecer do Recurso Especial", R.NAO_CONHECIDO),
        (12441, "Conhecimento para conhecer o recurso especial", None),
        (12329, "Pedido conhecido em parte e procedente", R.PROCEDENTE),
        (12330, "Pedido conhecido em parte e procedente em parte", R.PARCIALMENTE_PROCEDENTE),
        (12331, "Pedido conhecido em parte e improcedente", R.IMPROCEDENTE),
        (455, "Renúncia ao direito pelo autor", R.IMPROCEDENTE),
        (473, "Ausência do Reclamante", R.EXTINTO_SEM_MERITO),
        (11381, "Ausência de citação de sucessores do réu falecido", R.EXTINTO_SEM_MERITO),
        (14848, "Ausência de Requerimento Administrativo Prévio", R.EXTINTO_SEM_MERITO),
        (196, "Extinção da execução ou do cumprimento da sentença", None),
        (None, "procedência parcial", R.PARCIALMENTE_PROCEDENTE),
        # Hierarquia e texto oficial da TPU (SGT/CNJ, versão de 12/09/2026).
        (12451, "Procedência", None),  # julgada procedente a impugnação à execução
        (12452, "procedência parcial", None),
        (12453, "improcedência", None),
        (442, "Segurança", R.PROCEDENTE),  # concedida a segurança
        (446, "Segurança", R.IMPROCEDENTE),  # denegada a segurança
        (450, "Segurança", R.PARCIALMENTE_PROCEDENTE),  # concedida em parte
        (443, "Habeas corpus", R.PROCEDENTE),
        (447, "Habeas corpus", R.IMPROCEDENTE),
        (12252, "Sentença confirmada", R.NAO_PROVIDO),
        (12253, "Sentença confirmada em parte", R.PARCIALMENTE_PROVIDO),
        (12254, "Sentença desconstituída", R.PROVIDO),
        (11373, "Anulação de sentença/acórdão", R.PROVIDO),
        (901, "Negação de seguimento", R.NAO_PROVIDO),  # negado monocraticamente o provimento
        (236, "Negação de Seguimento", R.NAO_CONHECIDO),
        (230, "Recurso prejudicado", R.NAO_CONHECIDO),
        (457, "Paralisação por negligência das partes", R.EXTINTO_SEM_MERITO),
        (12325, "Perda do objeto", R.EXTINTO_SEM_MERITO),
        (228, "Arquivamento", R.EXTINTO_SEM_MERITO),  # arquivamento trabalhista (CLT, art. 844)
        (12430, "Arquivamento", None),  # arquivamento do processo, não julgamento
        (12673, "Não-Procedência da Impugnação (Registro Deferido)", R.IMPROCEDENTE),
        # Pedido contraposto do JEC: vale o resultado do pedido do autor (REGRAS.md, 4.1).
        (11401, "Procedência do pedido e procedência do pedido contraposto", R.PROCEDENTE),
        (11402, "Procedência do pedido e procedência em parte do pedido contraposto", R.PROCEDENTE),
        (11403, "Procedência do pedido e improcedência do pedido contraposto", R.PROCEDENTE),
        (
            11406,
            "Procedência em parte do pedido e improcedência do pedido contraposto",
            R.PARCIALMENTE_PROCEDENTE,
        ),
        (11407, "Improcedência do pedido e procedência do pedido contraposto", R.IMPROCEDENTE),
        (
            11408,
            "Improcedência do pedido e procedência em parte do pedido contraposto",
            R.IMPROCEDENTE,
        ),
        (12200, "Mérito", None),  # marcação de pauta no 2º grau, antes do julgamento
        (12187, "Homologação de Decisão de Juiz Leigo", None),  # não diz o resultado
        (15164, "Não Acolhimento de Embargos de Declaração", None),
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


def test_tabela_de_auditoria_acompanha_as_regras():
    """docs/dados/movimentos_datajud.csv: códigos em uso nos 91 tribunais, com o nome que chega ao
    DataJud, o texto e a hierarquia oficiais da TPU e o rótulo esperado.

    Se uma mudança de regra alterar algum rótulo, confira o caso e regenere a tabela.
    """
    import csv
    from pathlib import Path

    tabela = Path(__file__).parent.parent / "docs" / "dados" / "movimentos_datajud.csv"
    divergentes = []
    with open(tabela, encoding="utf-8") as arquivo:
        for linha in csv.DictReader(arquivo):
            rotulo = classificar_movimento(int(linha["codigo"]), linha["nome"])
            if (rotulo.value if rotulo else "") != linha["rotulo"]:
                divergentes.append((linha["codigo"], linha["nome"], linha["rotulo"], rotulo))
    assert divergentes == []
