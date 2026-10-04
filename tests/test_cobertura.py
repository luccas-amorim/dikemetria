"""Cobertura: DataJud contra os casos novos do Justiça em Números. Números fictícios."""

from dikemetria import cobertura
from dikemetria.coleta.tribunais import selecionar

CABECALHO = "ano;justica;sigla;" + ";".join(cobertura.CAMPOS_PRIMEIRO_GRAU)


def _csv(tmp_path, linhas):
    caminho = tmp_path / "jn.csv"
    caminho.write_text("\r\n".join([CABECALHO, *linhas]), encoding="latin-1")
    return caminho


def test_casos_novos_soma_primeiro_grau_e_juizados(tmp_path):
    caminho = _csv(
        tmp_path,
        [
            "2024;Estadual;TJXX;10;100;20;5;1;50;nd",
            "2023;Estadual;TJXX;1;1;1;1;1;1;1",
            "2024;Trabalho;TRT99;nd;300;nd;nd;nd;nd;nd",
        ],
    )
    assert cobertura.casos_novos(caminho, 2024) == {"tjxx": 186.0, "trt99": 300.0}


def test_razao_e_faixa():
    assert cobertura.Cobertura("tjxx", 2024, 90, 100).aceitavel
    incompleto = cobertura.Cobertura("tjdft", 2024, 15, 100)
    assert round(incompleto.razao, 2) == 0.15 and not incompleto.aceitavel
    assert not cobertura.Cobertura("tjmg", 2024, 171, 100).aceitavel
    assert cobertura.Cobertura("tjxx", 2024, None, 100).razao is None


def test_medir_conta_no_datajud_e_pula_superiores(tmp_path, cliente_falso):
    caminho = _csv(tmp_path, ["2024;Estadual;TJRN;0;100;0;0;0;0;0"])
    cliente, sessao = cliente_falso([{"hits": {"total": {"value": 95}}}])
    medidas = cobertura.medir(cliente, selecionar(["tjrn", "stj"]), 2024, caminho)
    assert [(m.tribunal, m.datajud, m.casos_novos) for m in medidas] == [("tjrn", 95, 100.0)]
    consulta = sessao.requisicoes[0]["json"]
    assert consulta["size"] == 0 and consulta["track_total_hits"] is True
