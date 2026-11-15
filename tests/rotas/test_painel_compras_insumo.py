"""
tests / rotas / test_painel_compras.py

controllers/painel.py, compras: abas, registrar (com "Mais linhas"), receber com entrada no estoque
e cancelar
"""

from decimal import Decimal

import pytest

from app.repositories.insumos_rep import RepositorioInsumos

pytestmark = pytest.mark.usefixtures("como_admin")


@pytest.fixture
def insumos(conexao):
    return RepositorioInsumos(lambda: conexao)


def status_da_compra(banco, id_compra):
    banco.execute("SELECT status FROM compra_insumo WHERE id_compra_insumo = %s", (id_compra,))
    return banco.fetchone()[0]


# Lista

def test_abas_de_status(navegador, templates):
    navegador.get("/painel/compras")
    assert sorted(compra.id for compra in templates[-1][1]["compras"]) == [1, 2, 3]
    assert templates[-1][1]["status_filtro"] == ""

    navegador.get("/painel/compras?status=pendente")
    assert [compra.id for compra in templates[-1][1]["compras"]] == [2]
    assert templates[-1][1]["status_filtro"] == "pendente"


def test_formulario_traz_so_fornecedores_ativos(navegador, templates):
    navegador.get("/painel/compras/nova")

    nome, variaveis = templates[-1]
    assert nome == "painel/compra_form.html"
    # Embala Campos (4) está inativo
    assert 4 not in [fornecedor.id for fornecedor in variaveis["fornecedores"]]
    assert variaveis["linhas_extras"] == 5


# Registrar

FORMULARIO = {
    "id_fornecedor": "2",
    "data_entrega": "",
    "nota_fiscal": "NF 999",
    # Duas linhas preenchidas e uma em branco (ignorada)
    "insumo_id": ["4", "5", ""],
    "quantidade": ["12", "6", ""],
    "custo_unitario": ["7.50", "3.48", ""],
    "acao": "salvar",
}


def test_registrar_grava_a_compra_pendente(navegador, mensagens, banco):
    resposta = navegador.post("/painel/compras/nova", data=FORMULARIO)

    assert resposta.status_code == 302
    banco.execute("SELECT max(id_compra_insumo) FROM compra_insumo")
    id_novo = banco.fetchone()[0]
    assert mensagens == [("sucesso", f"Compra nº {id_novo} registrada.")]
    banco.execute("SELECT status, valor_total, nota_fiscal FROM compra_insumo WHERE id_compra_insumo = %s", (id_novo,))
    # 12 x 7,50 + 6 x 3,48
    assert banco.fetchone() == ("pendente", Decimal("110.88"), "NF 999")


def test_mais_linhas_nao_salva(navegador, templates, banco):
    banco.execute("SELECT count(*) FROM compra_insumo")
    antes = banco.fetchone()[0]

    resposta = navegador.post("/painel/compras/nova", data=FORMULARIO | {"acao": "mais_linhas"})

    assert resposta.status_code == 200
    assert templates[-1][0] == "painel/compra_form.html"
    banco.execute("SELECT count(*) FROM compra_insumo")
    assert banco.fetchone()[0] == antes


@pytest.mark.parametrize(
    "mudanca, mensagem",
    [
        ({"id_fornecedor": ""}, "Escolha um fornecedor."),
        ({"insumo_id": ["", "", ""]}, "Informe pelo menos um item da compra"),
        ({"insumo_id": ["4", "4", ""]}, "O insumo 'Leite condensado (395g)' já está nesta compra"),
    ],
    ids=["sem fornecedor", "sem itens", "insumo repetido"],
)
def test_formulario_com_problema_volta_com_400(navegador, mensagens, mudanca, mensagem):
    resposta = navegador.post("/painel/compras/nova", data=FORMULARIO | mudanca)

    assert resposta.status_code == 400
    assert mensagens == [("erro", mensagem)]


# Receber e cancelar

def test_registrar_e_receber_soma_no_estoque(navegador, mensagens, insumos, banco):
    # O roteiro do passo 6: registra, recebe e confere o saldo
    antes = insumos.buscarPorId(4).quantidade_atual
    navegador.post("/painel/compras/nova", data=FORMULARIO)
    banco.execute("SELECT max(id_compra_insumo) FROM compra_insumo")
    id_novo = banco.fetchone()[0]

    resposta = navegador.post(f"/painel/compras/{id_novo}/receber")

    assert resposta.status_code == 302
    assert mensagens[-1] == ("sucesso", f"Compra nº {id_novo} recebida. O estoque foi atualizado.")
    assert status_da_compra(banco, id_novo) == "recebida"
    leite = insumos.buscarPorId(4)
    assert leite.quantidade_atual == antes + Decimal("12")
    assert leite.custo_por_unidade == Decimal("7.50")


def test_confirmacao_de_receber(navegador, templates):
    resposta = navegador.get("/painel/compras/2/receber")

    assert resposta.status_code == 200
    nome, variaveis = templates[-1]
    assert nome == "confirmar.html"
    assert variaveis["titulo"] == "Receber a compra nº 2?"


def test_receber_compra_ja_recebida_avisa(navegador, mensagens, banco):
    navegador.post("/painel/compras/1/receber")

    assert mensagens == [("erro", "Uma compra 'recebida' não pode mais ser alterada")]
    assert status_da_compra(banco, 1) == "recebida"


def test_cancelar_compra_pendente(navegador, mensagens, insumos, banco):
    antes = insumos.buscarPorId(4).quantidade_atual

    navegador.post("/painel/compras/2/cancelar")

    assert mensagens == [("sucesso", "Compra nº 2 cancelada.")]
    assert status_da_compra(banco, 2) == "cancelada"
    assert insumos.buscarPorId(4).quantidade_atual == antes


@pytest.mark.parametrize(
    "metodo, url",
    [
        ("GET", "/painel/compras/999/receber"),
        ("POST", "/painel/compras/999/receber"),
        ("GET", "/painel/compras/999/cancelar"),
        ("POST", "/painel/compras/999/cancelar"),
    ],
)
def test_compra_inexistente_da_404(navegador, metodo, url):
    assert navegador.open(url, method=metodo).status_code == 404
