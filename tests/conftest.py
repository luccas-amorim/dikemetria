"""Dados fictícios para os testes. Nenhum nome, documento ou processo aqui é real."""

from __future__ import annotations

import json

import pytest

# Números CNJ com dígito verificador válido.
CNJ_TJSP = "1001234-88.2023.8.26.0100"
CNJ_TRF4 = "0004567-08.2022.4.04.7000"

SENTENCA_PROCEDENTE = f"""PODER JUDICIÁRIO
TRIBUNAL DE JUSTIÇA DO ESTADO DE SÃO PAULO
SENTENÇA
Processo nº {CNJ_TJSP}
Autor: JOÃO CARLOS DA SILVA
Réu: BANCO EXEMPLO S.A.

Vistos.
JOÃO CARLOS DA SILVA, brasileiro, casado, inscrito no CPF sob o nº 123.456.789-09, residente na
Rua das Flores, nº 123, CEP 01234-567, ajuizou ação declaratória de inexigibilidade de débito
cumulada com indenização por danos morais em face de BANCO EXEMPLO S.A. Alega que teve o nome
incluído em cadastro de inadimplentes por dívida que desconhece.
É o relatório. Fundamento e decido.
A relação é de consumo, nos termos do art. 14 do CDC. Isso porque o réu não se desincumbiu do
ônus da prova (art. 373, II, do CPC), deixando de juntar o contrato. A inscrição indevida gera
dano moral in re ipsa. Não se aplica a Súmula 385 do STJ, pois não há inscrições anteriores.
Ante o exposto, JULGO PROCEDENTE o pedido para declarar a inexigibilidade do débito e condenar o
réu ao pagamento de R$ 5.000,00 a título de danos morais.
P.R.I.
Ana Beatriz Costa
Juíza de Direito
"""

SENTENCA_IMPROCEDENTE = f"""SENTENÇA
Processo nº {CNJ_TJSP}
Requerente: MARIA APARECIDA SOUZA
Vistos. Trata-se de ação declaratória de inexigibilidade de débito.
É o relatório. Decido.
O réu juntou o contrato assinado e as faturas. A autora não impugnou a assinatura, e a dívida
restou comprovada. A negativação foi exercício regular de direito (art. 188, I, do Código Civil).
Aplica-se a Súmula 385 do STJ, diante das inscrições preexistentes.
Ante o exposto, JULGO IMPROCEDENTES os pedidos. Condeno a autora nas custas e honorários de 10%
do valor da causa, observada a gratuidade (art. 98, § 3º, do CPC).
"""


class RespostaFalsa:
    def __init__(self, dados, status: int = 200):
        self.status_code = status
        self.content = json.dumps(dados).encode()
        self.text = self.content.decode()
        self._dados = dados

    def json(self):
        return self._dados


class SessaoFalsa:
    """Substitui requests.Session: devolve respostas em fila e registra as requisições."""

    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.requisicoes = []
        self.headers = {}

    def request(self, metodo, url, params=None, json=None, timeout=None):
        self.requisicoes.append({"metodo": metodo, "url": url, "params": params, "json": json})
        resposta = self.respostas.pop(0)
        return resposta if isinstance(resposta, RespostaFalsa) else RespostaFalsa(resposta)


@pytest.fixture
def cliente_falso():
    from dikemetria.coleta.http import Cliente

    def criar(respostas):
        sessao = SessaoFalsa(respostas)
        return Cliente(intervalo=0, sessao=sessao), sessao

    return criar


def hit_datajud(numero: str, movimentos, sort, **extra) -> dict:
    fonte = {
        "numeroProcesso": numero,
        "classe": {"codigo": 7, "nome": "Procedimento Comum Cível"},
        "assuntos": [{"codigo": 6226, "nome": "Inclusão Indevida em Cadastro de Inadimplentes"}],
        "grau": "G1",
        "dataAjuizamento": "20210310000000",
        "orgaoJulgador": {"codigo": 1234, "nome": "1ª Vara Cível", "codigoMunicipioIBGE": 3550308},
        "nivelSigilo": 0,
        "movimentos": movimentos,
    }
    fonte.update(extra)
    return {"_source": fonte, "sort": sort}
