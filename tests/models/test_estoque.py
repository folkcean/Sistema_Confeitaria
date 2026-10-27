"""
tests/models/test_estoque.py

Testes de Estoque: filtro por tipo, alertas, consumo tudo-ou-nada, entradas e ajuste com desfazer.
"""
from decimal import Decimal

import pytest

from app.exceptions import EstoqueInsuficienteError, ValidacaoError
from app.models import Estoque, Insumo, TipoInsumo


# CONJUNTO E TIPOS
def test_nome_duplicado_e_recusado(estoque):
    with pytest.raises(ValidacaoError):
        estoque.adicionar(Insumo("Farinha", "kg", "g", 1000))


def test_insumo_de_fora_e_recusado(farinha):
    with pytest.raises(ValidacaoError):
        Estoque().consumir([(farinha, 100)])


def test_resumo_so_ativos_agrupado_por_tipo_e_nome(estoque, caixa):
    estoque.adicionar(caixa)
    estoque.adicionar(Insumo("Ovo", "dúzia", "un", 12, ativo=False))
    linhas = [(l["tipo"], l["nome"]) for l in estoque.resumo()]
    # embalagem vem antes de ingrediente (ordem alfabética do tipo); o Ovo está inativo e não aparece
    assert linhas == [("embalagem", "Caixa de bolo"), ("ingrediente", "Farinha"), ("ingrediente", "Leite condensado")]


def test_por_tipo(estoque, caixa):
    estoque.adicionar(caixa)
    assert [i.nome for i in estoque.porTipo(TipoInsumo.EMBALAGEM)] == ["Caixa de bolo"]
    assert [i.nome for i in estoque.porTipo("ingrediente")] == ["Farinha", "Leite condensado"]
    assert estoque.porTipo(TipoInsumo.DECORACAO) == []
    with pytest.raises(ValidacaoError):
        estoque.porTipo("inexistente")


# ALERTAS E SUGESTÃO DE COMPRA
def test_sugestao_de_compras_lista_quem_atingiu_o_minimo(estoque, farinha):
    # leite: 40 latas e mínimo 40 -> já está no mínimo; farinha: 10 kg e mínimo 3 -> ok
    assert [i.nome for i in estoque.insumosAbaixoDoMinimo()] == ["Leite condensado"]
    farinha.registrarConsumo(Decimal("8"))  # sobram 2 kg (< 3)
    sugestao = {item["insumo"]: item["falta_para_minimo"] for item in estoque.sugerirCompras()}
    assert sugestao == {"Farinha": Decimal("1"), "Leite condensado": Decimal("0")}


def test_sugestao_de_compras_traz_o_tipo(estoque, caixa):
    caixa.registrarConsumo(90)  # sobram 10 (< 20)
    estoque.adicionar(caixa)
    tipos = {item["insumo"]: item["tipo"] for item in estoque.sugerirCompras()}
    assert tipos["Caixa de bolo"] == "embalagem"


# CONSUMO TUDO OU NADA
def test_consumir_desconta_na_unidade_de_estoque(estoque, farinha, leite_condensado):
    movs = estoque.consumir([(farinha, 300), (leite_condensado, 395)], id_pedido=7)
    assert farinha.quantidade_atual == Decimal("9.7")
    assert leite_condensado.quantidade_atual == 39
    assert len(movs) == 2 and all(m.id_pedido == 7 for m in movs)


def test_consumir_soma_o_mesmo_insumo_repetido(estoque, farinha):
    movs = estoque.consumir([(farinha, 300), (farinha, 200)])
    assert len(movs) == 1  # um registro por insumo
    assert farinha.quantidade_atual == Decimal("9.5")


def test_consumir_e_tudo_ou_nada(estoque, farinha, leite_condensado):
    leite_condensado.ajustarPara(1, "contagem")  # só 1 lata
    with pytest.raises(EstoqueInsuficienteError) as erro:
        estoque.consumir([(farinha, 300), (leite_condensado, 1000)])  # 1000 g = 2,532 latas
    assert farinha.quantidade_atual == 10  # a farinha NÃO foi descontada
    assert leite_condensado.quantidade_atual == 1
    assert [f["insumo"] for f in erro.value.faltas] == ["Leite condensado"]
    assert erro.value.faltas[0]["faltam"] == Decimal("1.532")


def test_faltas_somam_o_total_do_mesmo_insumo(estoque, farinha):
    # cada pedaço cabe (6 kg e 6 kg < 10 kg), mas juntos (12 kg) não
    with pytest.raises(EstoqueInsuficienteError):
        estoque.consumir([(farinha, 6000), (farinha, 6000)])
    assert farinha.quantidade_atual == 10


def test_verificar_disponibilidade_nao_altera_o_estoque(estoque, farinha):
    faltas = estoque.verificarDisponibilidade([(farinha, 12000)])
    assert faltas[0]["faltam"] == Decimal("2")
    assert farinha.quantidade_atual == 10
    assert estoque.verificarDisponibilidade([(farinha, 1000)]) == []


# ENTRADAS, PERDAS, AJUSTES
def test_receber_da_entrada_em_varios_itens(estoque, farinha, leite_condensado):
    movs = estoque.receber([(farinha, 5), (leite_condensado, 10)], id_compra=3)
    assert farinha.quantidade_atual == 15 and leite_condensado.quantidade_atual == 50
    assert all(m.id_compra == 3 for m in movs)


def test_receber_valida_tudo_antes_de_aplicar(estoque, farinha, leite_condensado):
    with pytest.raises(ValidacaoError):
        estoque.receber([(farinha, 5), (leite_condensado, -1)])
    assert farinha.quantidade_atual == 10  # a primeira entrada NÃO foi aplicada


def test_registrar_perda(estoque, farinha):
    estoque.registrarPerda(farinha, 1, "derramou")
    assert farinha.quantidade_atual == 9


def test_ajuste_manual_e_desfazer(estoque, farinha):
    mov = estoque.ajustarManual(farinha, 8, "contagem")
    assert farinha.quantidade_atual == 8
    contra = estoque.desfazerAjuste(mov)
    assert farinha.quantidade_atual == 10
    assert contra.variacao == 2 and "Desfaz" in contra.motivo  # histórico preservado: 2 registros


def test_so_ajuste_pode_ser_desfeito(estoque, farinha):
    entrada = farinha.registrarEntrada(1)
    with pytest.raises(ValidacaoError):
        estoque.desfazerAjuste(entrada)