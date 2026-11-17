"""
tests / db / test_contextoIARepositorio.py

repositories/contexto_ia_rep.py: o retrato do banco que vai para a IA
Confere os números no seed (DB_fill.sql), a privacidade (nenhum dado de cliente) e a proteção
de somente leitura (o PostgreSQL recusa qualquer escrita dentro do montar)
"""
import json
from datetime import timedelta
from decimal import Decimal

import psycopg
import pytest

from app.repositories import contexto_ia_rep
from app.repositories.contexto_ia_rep import RepositorioContextoIA


@pytest.fixture
def contexto(conexao, seed):
    # O repositório espera uma FUNÇÃO que devolve a conexão: o lambda é essa função
    return RepositorioContextoIA(lambda: conexao).montar()


def insumo(contexto, nome):
    """A linha de um insumo do contexto, pelo nome"""
    return next(filter(lambda linha: linha["insumo"] == nome, contexto["insumos"]))


def test_acucar_abaixo_do_minimo_na_unidade_de_compra(contexto):
    acucar = insumo(contexto, "Acucar refinado")

    assert (acucar["saldo"], acucar["minimo"], acucar["unidade"]) == (Decimal("8.73"), Decimal("10.00"), "kg")
    # 280 g da massa de chocolate do pedido 6 (orçamento), que ainda não baixou o estoque
    assert acucar["reservado_em_pedidos"] == Decimal("0.280")


def test_leite_condensado_tem_compra_a_caminho(contexto, hoje_no_banco):
    leite = insumo(contexto, "Leite condensado (395g)")

    assert leite["a_caminho"] == Decimal("24")
    assert leite["entrega_prevista"] == hoje_no_banco + timedelta(days=2)
    assert leite["fornecedor"] == "Casa do Confeiteiro"


def test_prazo_do_fornecedor_vem_das_compras_recebidas(contexto):
    # Compra 1 do Atacadão: comprada num dia, entregue no seguinte
    assert insumo(contexto, "Farinha de trigo")["prazo_entrega_dias"] == Decimal("1.0")


def test_insumo_inativo_fica_de_fora(contexto):
    assert "Fita de cetim" not in [linha["insumo"] for linha in contexto["insumos"]]


def test_nenhum_dado_de_cliente_vai_para_a_ia(contexto, banco):
    # Pega do próprio banco o nome, e-mail, telefone e CPF de TODOS os clientes do seed
    banco.execute("SELECT nome, email, telefone, cpf FROM usuario WHERE perfil = 'cliente'")
    dados_de_clientes = [dado for linha in banco.fetchall() for dado in linha if dado]
    texto = json.dumps(contexto, default=str, ensure_ascii=False)

    assert dados_de_clientes, "o seed precisa ter clientes para o teste valer"
    assert [dado for dado in dados_de_clientes if dado in texto] == []


def test_a_leitura_e_somente_leitura(conexao, seed, monkeypatch):
    # Troca uma das consultas por um UPDATE: o PostgreSQL precisa recusar
    monkeypatch.setattr(contexto_ia_rep, "SQL_PEDIDOS_EM_ABERTO", "UPDATE insumo SET nome = nome RETURNING nome")

    with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        RepositorioContextoIA(lambda: conexao).montar()