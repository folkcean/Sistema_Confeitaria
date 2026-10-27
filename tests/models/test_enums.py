# Sem conexão com o banco ainda...

from itertools import product

import pytest

from app.exceptions import TransicaoStatusError
from app.models.enums import StatusPedido

S = StatusPedido

# Fluxo do pedido (regra 4.6 da entrevista)
PERMITIDAS = [
    (S.SOLICITADO, S.ORCAMENTO),
    (S.ORCAMENTO, S.CONFIRMADO),
    (S.CONFIRMADO, S.EM_PRODUCAO),
    (S.CONFIRMADO, S.CANCELADO),
    (S.EM_PRODUCAO, S.PRONTO),
    (S.EM_PRODUCAO, S.CANCELADO),
    (S.PRONTO, S.ENTREGUE),
    (S.PRONTO, S.CANCELADO),
    (S.ENTREGUE, S.FINALIZADO),
]

PROIBIDAS = [
    (S.SOLICITADO, S.CONFIRMADO),  # pula o orçamento
    (S.ORCAMENTO, S.EM_PRODUCAO),  # pula a confirmação
    (S.CONFIRMADO, S.ORCAMENTO),  # volta
    (S.ENTREGUE, S.CANCELADO),
    (S.FINALIZADO, S.CANCELADO),
    (S.CANCELADO, S.CONFIRMADO),
]


def nomes(pares):
    return [f"{origem.value}->{destino.value}" for origem, destino in pares]


@pytest.mark.parametrize("origem, destino", PERMITIDAS, ids=nomes(PERMITIDAS))
def test_transicao_permitida_e_aceita(origem, destino):
    assert origem.podeIrPara(destino) is True
    origem.validarTransicao(destino)


@pytest.mark.parametrize("origem, destino", PROIBIDAS, ids=nomes(PROIBIDAS))
def test_transicao_proibida_levanta_erro(origem, destino):
    assert origem.podeIrPara(destino) is False

    with pytest.raises(TransicaoStatusError, match="Não é possível mudar"):
        origem.validarTransicao(destino)


@pytest.mark.parametrize("status", [S.FINALIZADO, S.CANCELADO], ids=lambda s: s.name)
def test_status_finais_nao_tem_proximos(status):
    assert status.proximos() == frozenset()


@pytest.mark.parametrize("status", list(S), ids=lambda s: s.name)
def test_todo_status_tem_entrada_na_tabela_de_transicoes(status):
    assert isinstance(status.proximos(), frozenset)


def test_so_cancelado_exige_motivo():
    exigem = {status for status in S if status.exigeMotivo()}

    assert exigem == {S.CANCELADO}


def test_existem_exatamente_9_transicoes_permitidas():
    permitidas = [(o, d) for o, d in product(S, S) if o.podeIrPara(d)]

    assert len(permitidas) == 9
