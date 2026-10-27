"""
tests / models / conftest.py

Aqui estão as fixtures dos testes de estoque (farinha, leite_condensado, caixa, estoque)

Uma fixture é uma função marcada com @pytest.fixture que PREPARA um objeto para os testes

O pytest entrega o objeto ao teste pelo NOME do parâmetro: se o teste é `def test_x(farinha):`, o pytest roda a fixture `farinha` e passa o resultado

Cada teste recebe objetos NOVOS (a fixture roda de novo a cada teste), então um teste não atrapalha o outro

Este arquivo é lido automaticamente pelo pytest; não precisa importar
"""
from decimal import Decimal
 
import pytest
 
from app.models import Estoque, Insumo, TipoInsumo
 
 
@pytest.fixture
def farinha():
    """10 kg em estoque, mínimo 3 kg, R$ 8,00 por kg. A receita escreve em gramas (1 kg = 1000 g)."""
    return Insumo("Farinha", "kg", "g", fator_conversao=1000, quantidade_atual=10,
                  estoque_minimo=3, custo_por_unidade=Decimal("8"))
 
 
@pytest.fixture
def leite_condensado():
    """40 latas, mínimo 40, R$ 6,50 por lata. Cada lata tem 395 g."""
    return Insumo("Leite condensado", "lata", "g", fator_conversao=395, quantidade_atual=40,
                  estoque_minimo=40, custo_por_unidade=Decimal("6.5"))
 
 
@pytest.fixture
def caixa():
    """Uma EMBALAGEM (outro tipo de insumo): 100 caixas, mínimo 20."""
    return Insumo("Caixa de bolo", "un", "un", quantidade_atual=100, estoque_minimo=20,
                  tipo=TipoInsumo.EMBALAGEM)
 
 
@pytest.fixture
def estoque(farinha, leite_condensado):
    """Estoque com a farinha e o leite condensado (os dois são do tipo ingrediente)."""
    return Estoque([farinha, leite_condensado])
 