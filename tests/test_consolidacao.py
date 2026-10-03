"""Unidade de análise e medidas sobre unidades (docs/REGRAS.md)."""

import pytest

from dikemetria import jurimetria
from dikemetria.coleta.djen import converter_documento
from dikemetria.consolidacao import consolidar

NUM = "1001234-88.2023.8.26.0100"
DIGITOS = "10012348820238260100"


def doc(id_, texto, data="2024-01-10", numero=NUM):
    documento = converter_documento({"id": id_, "texto": texto, "numero_processo": numero}, "tjsp")
    registro = documento.__dict__ | {"data": data}
    return registro


def proc(resultado, grau="G1", numero=DIGITOS, tribunal="tjsp"):
    return {
        "numero": numero,
        "grau": grau,
        "tribunal": tribunal,
        "resultado": resultado,
        "classe_nome": "Procedimento Comum Cível",
        "assuntos": [],
        "data_julgamento": "2024-01-10",
        "data_ajuizamento": "2023-01-10",
        "duracao_dias": 365,
        "sensivel": 0,
    }


SENTENCA = "SENTENÇA\nÉ o relatório. Decido.\nAnte o exposto, JULGO PROCEDENTE o pedido."
EMBARGOS = "SENTENÇA\nEmbargos de declaração.\nAnte o exposto, rejeito os embargos de declaração."
ACORDAO = "ACÓRDÃO\nVistos.\nACORDAM, por unanimidade, em dar provimento ao recurso."


def test_uma_unidade_por_processo_e_instancia():
    unidades = consolidar(
        [proc("procedente"), proc("provido", grau="G2")],
        [
            doc(1, SENTENCA),
            doc(2, SENTENCA, "2024-01-11"),
            doc(3, EMBARGOS, "2024-02-01"),
            doc(4, ACORDAO, "2025-01-01"),
        ],
    )
    assert [(u["numero"], u["instancia"], u["fonte"]) for u in unidades] == [
        (DIGITOS, "1", "ambos"),
        (DIGITOS, "2", "ambos"),
    ]


def test_texto_prevalece_e_divergencia_e_marcada():
    (unidade,) = consolidar([proc("improcedente")], [doc(1, SENTENCA)])
    assert unidade["resultado"] == "procedente"
    assert unidade["resultado_movimentos"] == "improcedente"
    assert unidade["divergente"]


def test_movimentos_suprem_texto_indeterminado():
    (unidade,) = consolidar([proc("improcedente")], [doc(1, "SENTENÇA\nCite-se o réu.")])
    assert unidade["resultado"] == "improcedente" and not unidade["divergente"]


def _unidade(tribunal, resultado, instancia="1", numero="x", **extra):
    return {
        "tribunal": tribunal,
        "resultado": resultado,
        "instancia": instancia,
        "numero": numero,
        **extra,
    }


def test_taxa_nacional_agregada_e_media_entre_tribunais():
    unidades = (
        [_unidade("tjsp", "procedente")] * 90
        + [_unidade("tjsp", "improcedente")] * 10
        + [_unidade("tjac", "procedente")] * 2
        + [_unidade("tjac", "improcedente")] * 8
    )
    acolhimento = next(
        x for x in jurimetria.taxa_nacional(unidades) if x["medida"] == "acolhimento"
    )
    assert acolhimento["n"] == 110
    assert acolhimento["agregada"] == pytest.approx(92 / 110)
    assert acolhimento["media_tribunais"] == pytest.approx((0.9 + 0.2) / 2)
    assert acolhimento["tribunais"] == 2


def test_reforma_infere_resultado_final():
    pares = [
        ("procedente", {"resultado": "nao_provido"}, "procedente"),
        ("procedente", {"resultado": "provido"}, "improcedente"),
        ("improcedente", {"resultado": "provido"}, "procedente"),
        ("improcedente", {"resultado": "parcialmente_provido"}, "parcialmente_procedente"),
        (
            "parcialmente_procedente",
            {"resultado": "provido"},
            "indeterminado (ambas as partes podem ter recorrido)",
        ),
        (
            "improcedente",
            {"resultado": "provido", "resultado_acao": "parcialmente_procedente"},
            "parcialmente_procedente",
        ),
        (
            "procedente",
            {"resultado": "provido", "motivo": "anulação da sentença"},
            "sentença anulada",
        ),
    ]
    unidades = []
    for i, (primeira, segunda, _) in enumerate(pares):
        unidades.append(_unidade("tjsp", primeira, "1", str(i)))
        unidades.append(
            _unidade(
                "tjsp",
                segunda["resultado"],
                "2",
                str(i),
                resultado_acao=segunda.get("resultado_acao"),
                motivo=segunda.get("motivo"),
            )
        )
    reforma = jurimetria.reforma(unidades)
    finais = {(x["sentenca"], x["final"]) for x in reforma["resultado_final"]}
    for primeira, _, final in pares:
        assert (primeira, final) in finais
    assert reforma["pares"] == 7
    assert reforma["taxa_reforma"] == pytest.approx(6 / 7)


def test_valores_e_parametros_so_de_sentencas_acolhidas():
    def com_valor(resultado, valor, instancia="1"):
        return _unidade(
            "tjsp",
            resultado,
            instancia,
            calculo={
                "valores": [{"categoria": "danos_morais", "valor": valor, "trecho": ""}],
                "honorarios_percentual": 10.0,
                "juros_termos_iniciais": ["citação"],
            },
        )

    unidades = [com_valor("procedente", v) for v in range(1000, 11000, 1000)]
    unidades += [
        com_valor("improcedente", 99999),
        com_valor("provido", 99999, "2"),
        com_valor("procedente", 50_000_000),
    ]  # fora da faixa plausível
    (linha,) = jurimetria.valores_condenacao(unidades)
    assert linha["n"] == 10 and linha["mediana"] == 5500
    parametros = {
        (x["parametro"], x["valor"]): x["n"] for x in jurimetria.parametros_calculo(unidades)
    }
    assert parametros[("honorários (%)", "10%")] == 11
    assert parametros[("juros: termo inicial", "citação")] == 11


def test_provimento_conta_cada_recurso():
    capitulos = [
        {"resultado": "provido", "objeto": "recurso", "forca": "forte"},
        {"resultado": "nao_provido", "objeto": "recurso", "forca": "forte"},
    ]
    unidades = [_unidade("tjsp", "indeterminado", "2", capitulos=capitulos)] * 5
    medida = jurimetria.provimento_por_recurso(unidades)
    assert medida["recursos"] == 10 and medida["provimento"] == 0.5
