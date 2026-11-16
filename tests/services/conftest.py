"""
tests / services / conftest.py

Fixures compartilhadas pelos testes de baixa de estoque, alerta e PedidoService (s5)
Este arquivo vale só para tests/services/ (não substitui o tests/conftest.py do banco)

CENÁRIO (números fáceis de conferir):
    estoque: farinha 10 kg (mínimo 3, fator 1000 g/kg) e leite condensado 40 latas (mínimo 40, 395 g/lata)
    receita do bolo: rende 1 un e usa 500 g de farinha + 395 g de leite (1 lata)
    1 bolo consome 0,500 kg de farinha e 1,000 lata de leite.
"""
from datetime import datetime

import pytest

from app.models.cliente import Cliente
from app.models.endereco import Endereco
from app.models.estoque import Estoque
from app.models.insumo import Insumo
from app.models.produto import Produto
from app.models.receita import ItemReceita, Receita
from decimal import Decimal

CRIACAO = datetime(2026, 11, 2, 10, 0)
ENTREGA_OK = datetime(2026, 11, 10, 15, 0)


@pytest.fixture
def farinha():
    return Insumo("Farinha", "kg", "g", fator_conversao=1000, quantidade_atual=10,
                  estoque_minimo=3, custo_por_unidade=Decimal("8"))


@pytest.fixture
def leite():
    return Insumo("Leite condensado", "lata", "g", fator_conversao=395, quantidade_atual=40,
                  estoque_minimo=10, custo_por_unidade=Decimal("6.5"))


@pytest.fixture
def estoque(farinha, leite):
    return Estoque([farinha, leite])


@pytest.fixture
def bolo(farinha, leite):
    """Produto 'Bolo' (encomenda, 48 h) ligado a uma receita que usa 500 g de farinha e 395 g de leite."""
    receita = Receita(1, "un")
    receita.adicionarItem(ItemReceita(farinha, 500))
    receita.adicionarItem(ItemReceita(leite, 395))
    produto = Produto("Bolo", 50)
    produto.adicionarReceita(receita)
    return produto


@pytest.fixture
def cliente():
    maria = Cliente("Maria Silva", "maria@email.com", "22999998888", None)
    maria.adicionarEndereco(Endereco("Rua A", "10", "Centro", "Campos", "28000-000"))
    return maria