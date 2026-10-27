"""
tests / models / test_insumo.py

Testes de Insumo: conversão de unidades, alerta de mínimo, custo, tipo e movimentações
"""

from decimal import Decimal
 
import pytest
 
from app.exceptions import EstoqueInsuficienteError, ValidacaoError
from app.models import Insumo, TipoInsumo, TipoMovimentacao
 
 
# CONVERSÃO DE UNIDADES
def test_receita_para_estoque_em_kg(farinha):
    assert farinha.paraUnidadeEstoque(300) == Decimal("0.300")
 
 
def test_receita_para_estoque_em_latas(leite_condensado):
    # 100 g / 395 = 0,2531... -> arredonda PARA CIMA -> 0,254
    assert leite_condensado.paraUnidadeEstoque(100) == Decimal("0.254")
 
 
def test_conversao_nunca_desconta_menos_que_o_usado(farinha):
    assert farinha.paraUnidadeEstoque(Decimal("0.4")) == Decimal("0.001")
 
 
def test_estoque_para_receita(farinha):
    assert farinha.paraUnidadeReceita(Decimal("1.5")) == Decimal("1500")
 
 
# ALERTA DE MÍNIMO
def test_alerta_dispara_ao_atingir_o_minimo(farinha):
    assert not farinha.abaixo_do_minimo
    farinha.registrarConsumo(7)  # sobram 3 kg = exatamente o mínimo
    assert farinha.abaixo_do_minimo
    assert farinha.falta_para_minimo == 0
 
 
def test_falta_para_minimo(farinha):
    farinha.registrarConsumo(Decimal("7.5"))  # sobram 2,5 kg
    assert farinha.falta_para_minimo == Decimal("0.5")
 
 
# MOVIMENTAÇÕES
def test_entrada_soma_e_registra(farinha):
    mov = farinha.registrarEntrada(5, id_compra=9)
    assert farinha.quantidade_atual == 15
    assert mov.tipo is TipoMovimentacao.ENTRADA and mov.variacao == 5 and mov.id_compra == 9
 
 
def test_consumo_subtrai_e_registra(farinha):
    mov = farinha.registrarConsumo(2, id_pedido=4)
    assert farinha.quantidade_atual == 8
    assert mov.variacao == -2 and mov.id_pedido == 4
 
 
def test_consumo_maior_que_o_saldo_e_recusado_e_nada_muda(farinha):
    with pytest.raises(EstoqueInsuficienteError) as erro:
        farinha.registrarConsumo(15)
    assert farinha.quantidade_atual == 10
    assert erro.value.faltas == [{"insumo": "Farinha", "unidade": "kg", "faltam": Decimal("5")}]
 
 
def test_perda_e_ajuste_exigem_motivo(farinha):
    with pytest.raises(ValidacaoError):
        farinha.registrarPerda(1, "")
    with pytest.raises(ValidacaoError):
        farinha.ajustar(1, "")
    farinha.registrarPerda(1, "queimou")
    assert farinha.quantidade_atual == 9
 
 
def test_ajustar_para_valor_final(farinha):
    mov = farinha.ajustarPara(8, "contagem")
    assert farinha.quantidade_atual == 8 and mov.variacao == -2
 
 
def test_ajustar_para_o_mesmo_valor_e_recusado(farinha):
    with pytest.raises(ValidacaoError):
        farinha.ajustarPara(10, "contagem")
 
 
# CUSTO
def test_custo_de_uma_quantidade_da_receita(farinha):
    assert farinha.custoDe(300) == Decimal("2.4")  # 0,3 kg * R$ 8,00
 
 
def test_custo_sem_cadastro_e_recusado():
    sal = Insumo("Sal", "kg", "g", 1000)
    assert sal.custo_por_unidade is None
    with pytest.raises(ValidacaoError):
        sal.custoDe(10)
 
 
def test_custo_zero_e_valido():
    agua = Insumo("Água", "l", "ml", 1000, custo_por_unidade=0)
    assert agua.custo_por_unidade == Decimal("0")
    assert agua.custoDe(500) == 0
 
 
# TIPO DO INSUMO
def test_tipo_padrao_e_ingrediente():
    assert Insumo("Açúcar", "kg", "g", 1000).tipo is TipoInsumo.INGREDIENTE
 
 
def test_tipo_aceita_texto_do_banco_e_recusa_invalido():
    assert Insumo("Caixa", "un", "un", tipo="embalagem").tipo is TipoInsumo.EMBALAGEM
    with pytest.raises(ValidacaoError):
        Insumo("X", "kg", "g", tipo="inexistente")
 
 
# CADASTRO
def test_defaults_do_der():
    i = Insumo("Açúcar", "kg", "g", 1000)
    assert i.quantidade_atual == 0 and i.estoque_minimo == 0 and i.ativo
 
 
def test_dados_invalidos():
    with pytest.raises(ValidacaoError):
        Insumo("X", "kg", "g", fator_conversao=0)
    with pytest.raises(ValidacaoError):
        Insumo("X", "kg", "g" * 21)  # unidade_receita tem no máximo 20 caracteres
 