"""
tests / rotas / test_painel_fornecedores.py

controllers/painel.py, fornecedores: abas, cadastro, edição, desativar com desfazer e reativar
"""

import pytest

from app.repositories.fornecedores_rep import RepositorioFornecedores

NOVO = {
    "nome": "Laticínios Norte",
    "telefone": "(22) 2733-4444",
    "endereco": "Rua do Gás, 120, Centro",
    "email": "vendas@laticiniosnorte.local",
    "cnpj": "45.678.901/0001-23",
    "contato_principal": "",
}


@pytest.fixture
def repo(conexao):
    return RepositorioFornecedores(lambda: conexao)


def test_aba_ativos_e_aba_inativos(navegador, como_admin, templates):
    navegador.get("/painel/fornecedores")
    _, variaveis = templates[-1]
    # Embala Campos (4) está inativo no seed
    assert [f.id for f in variaveis["fornecedores"]] == [1, 2, 3]
    assert variaveis["filtro"] == ""

    navegador.get("/painel/fornecedores?filtro=inativos")
    _, variaveis = templates[-1]
    assert [f.id for f in variaveis["fornecedores"]] == [4]


def test_cadastrar_grava_e_volta_para_a_lista(navegador, como_admin, mensagens, repo):
    resposta = navegador.post("/painel/fornecedores/novo", data=NOVO)

    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/painel/fornecedores")
    assert mensagens == [("sucesso", "Laticínios Norte cadastrado.")]
    nomes = [f.nome for f in repo.listar()]
    assert "Laticínios Norte" in nomes


def test_cnpj_repetido_reabre_o_formulario_com_400(navegador, como_admin, mensagens, templates):
    dados = NOVO | {"cnpj": "12.345.678/0001-90"}  # CNPJ do Atacadao Campos
    resposta = navegador.post("/painel/fornecedores/novo", data=dados)

    assert resposta.status_code == 400
    assert templates[-1][0] == "painel/fornecedor_form.html"
    assert mensagens == [("erro", "Já existe um fornecedor com esse CNPJ.")]
    # O que foi digitado continua no formulário
    assert "Laticínios Norte" in resposta.get_data(as_text=True)


def test_editar_salva_os_campos(navegador, como_admin, repo):
    dados = {
        "nome": "Casa do Confeiteiro Centro",
        "telefone": "22999998888",
        "endereco": "Rua Formosa, 300, Centro",
        "email": "",
        "cnpj": "23456789000101",
        "contato_principal": "Ana Paula",
    }
    resposta = navegador.post("/painel/fornecedores/2/editar", data=dados)

    assert resposta.status_code == 302
    fornecedor = repo.buscarPorId(2)
    assert fornecedor.nome == "Casa do Confeiteiro Centro"
    assert fornecedor.telefone == "22999998888"
    assert fornecedor.email is None
    assert fornecedor.contato_principal == "Ana Paula"


def test_editar_com_telefone_invalido_da_400_e_nao_grava(navegador, como_admin, repo):
    dados = {"nome": "X", "telefone": "123", "endereco": "Rua Y", "email": "", "cnpj": "", "contato_principal": ""}
    resposta = navegador.post("/painel/fornecedores/2/editar", data=dados)

    assert resposta.status_code == 400
    assert repo.buscarPorId(2).nome == "Casa do Confeiteiro"


def test_desativar_e_desfazer(navegador, como_admin, mensagens, repo):
    navegador.post("/painel/fornecedores/1/desativar")

    assert not repo.buscarPorId(1).ativo
    assert mensagens == [("desfazer:/painel/fornecedores/1/reativar", "Atacadao Campos desativado.")]

    # O botão "Desfazer" faz POST na URL do flash
    navegador.post("/painel/fornecedores/1/reativar")
    assert repo.buscarPorId(1).ativo


def test_desativar_um_inativo_nao_reativa(navegador, como_admin, mensagens, repo):
    navegador.post("/painel/fornecedores/4/desativar")

    assert not repo.buscarPorId(4).ativo
    assert mensagens == [("erro", "Embala Campos já está inativo.")]


@pytest.mark.parametrize(
    "metodo, url",
    [
        ("GET", "/painel/fornecedores/999/editar"),
        ("POST", "/painel/fornecedores/999/editar"),
        ("GET", "/painel/fornecedores/999/desativar"),
        ("POST", "/painel/fornecedores/999/desativar"),
        ("POST", "/painel/fornecedores/999/reativar"),
    ],
)
def test_fornecedor_inexistente_da_404(navegador, como_admin, metodo, url):
    assert navegador.open(url, method=metodo).status_code == 404
