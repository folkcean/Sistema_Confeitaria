"""
tests / rotas / test_matriz_de_acesso.py

"""

from urllib.parse import parse_qs, urlsplit

import pytest


@pytest.fixture
def app(app_somente_leitura):
    """Neste arquivo, todo teste usa o mesmo app e o mesmo seed (ver o conftest)"""
    return app_somente_leitura


def destino_do_login(resposta):
    """Do Location "/entrar?proximo=/painel", devolve ("/entrar", "/painel")"""
    endereco = urlsplit(resposta.headers["Location"])
    # parse_qs devolve uma lista por parâmetro: {"proximo": ["/painel"]}
    return endereco.path, parse_qs(endereco.query)["proximo"][0]


# {endpoint: (método, URL de exemplo)}. Os ids existem no DB_fill.sql

# Qualquer pessoa, logada ou não
ABERTAS = {
    "acesso.inicio": ("GET", "/"),
    "acesso.login": ("GET", "/entrar"),
    "acesso.loginEnviar": ("POST", "/entrar"),
    "acesso.cadastro": ("GET", "/cadastro"),
    "acesso.cadastroEnviar": ("POST", "/cadastro"),
    "acesso.sair": ("GET", "/sair"),
    "loja.home": ("GET", "/loja"),
    "loja.catalogo": ("GET", "/loja/cardapio"),
    "loja.produto": ("GET", "/loja/produtos/1"),
    "loja.carrinho": ("GET", "/loja/carrinho"),
    "loja.carrinhoAdicionar": ("POST", "/loja/carrinho/adicionar"),
    "loja.carrinhoAtualizar": ("POST", "/loja/carrinho/0/atualizar"),
    "loja.carrinhoRemover": ("POST", "/loja/carrinho/0/remover"),
}

# Só cliente logado (@soCliente)
DO_CLIENTE = {
    "loja.perfil": ("GET", "/loja/perfil"),
    "loja.meusDados": ("GET", "/loja/perfil/dados"),
    "loja.meusDadosSalvar": ("POST", "/loja/perfil/dados"),
    "loja.alterarSenha": ("POST", "/loja/perfil/senha"),
    "loja.enderecos": ("GET", "/loja/perfil/enderecos"),
    "loja.enderecoAdicionar": ("POST", "/loja/perfil/enderecos/novo"),
    "loja.enderecoRemover": ("GET", "/loja/perfil/enderecos/1/remover"),
    "loja.enderecoRemoverConfirmado": ("POST", "/loja/perfil/enderecos/1/remover"),
    "loja.pedidoEnviar": ("POST", "/loja/carrinho/enviar"),
    "loja.pedidos": ("GET", "/loja/pedidos"),
    "loja.pedido": ("GET", "/loja/pedidos/1"),
}

# Painel, funcionário e administrador (só o conferirEquipe do before_request)
DA_EQUIPE = {
    "painel.inicio": ("GET", "/painel"),
    "painel.pedidos": ("GET", "/painel/pedidos"),
    "painel.pedido": ("GET", "/painel/pedidos/1"),
    "painel.pedidoStatus": ("POST", "/painel/pedidos/1/status"),
    "painel.produtos": ("GET", "/painel/produtos"),
    "painel.receitas": ("GET", "/painel/receitas"),
    "painel.receita": ("GET", "/painel/receitas/1"),
    "painel.estoque": ("GET", "/painel/estoque"),
    "painel.listaCompras": ("GET", "/painel/estoque/lista-de-compras"),
}

# Painel, só administrador (@soAdmin)
SO_ADMIN = {
    "painel.pedidoPagamento": ("POST", "/painel/pedidos/1/pagamento"),
    "painel.pedidoCancelar": ("GET", "/painel/pedidos/1/cancelar"),
    "painel.pedidoCancelarConfirmado": ("POST", "/painel/pedidos/1/cancelar"),
    "painel.produtoNovo": ("GET", "/painel/produtos/novo"),
    "painel.produtoNovoSalvar": ("POST", "/painel/produtos/novo"),
    "painel.produtoEditar": ("GET", "/painel/produtos/1"),
    "painel.produtoEditarSalvar": ("POST", "/painel/produtos/1"),
    "painel.produtoDesativar": ("GET", "/painel/produtos/1/desativar"),
    "painel.produtoDesativarConfirmado": ("POST", "/painel/produtos/1/desativar"),
    "painel.produtoReativar": ("POST", "/painel/produtos/17/reativar"),
    "painel.opcaoAdicionar": ("POST", "/painel/produtos/1/opcoes"),
    "painel.opcaoAlternar": ("POST", "/painel/opcoes/1/alternar"),
    "painel.produtoReceitaAdicionar": ("POST", "/painel/produtos/1/receitas"),
    "painel.produtoReceitaRemover": ("POST", "/painel/produtos/1/receitas/2/remover"),
    "painel.receitaNova": ("GET", "/painel/receitas/nova"),
    "painel.receitaNovaSalvar": ("POST", "/painel/receitas/nova"),
    "painel.receitaEditar": ("GET", "/painel/receitas/1/editar"),
    "painel.receitaEditarSalvar": ("POST", "/painel/receitas/1/editar"),
    "painel.receitaDesativar": ("GET", "/painel/receitas/1/desativar"),
    "painel.receitaDesativarConfirmado": ("POST", "/painel/receitas/1/desativar"),
    "painel.receitaReativar": ("POST", "/painel/receitas/12/reativar"),
    "painel.insumoNovo": ("GET", "/painel/estoque/novo"),
    "painel.insumoNovoSalvar": ("POST", "/painel/estoque/novo"),
    "painel.insumoEditar": ("GET", "/painel/estoque/1/editar"),
    "painel.insumoEditarSalvar": ("POST", "/painel/estoque/1/editar"),
    "painel.insumoAjustar": ("GET", "/painel/estoque/22/ajustar"),
    "painel.insumoAjustarSalvar": ("POST", "/painel/estoque/22/ajustar"),
    "painel.ajusteDesfazer": ("POST", "/painel/estoque/ajustes/18/desfazer"),
    "painel.insumoDesativar": ("GET", "/painel/estoque/1/desativar"),
    "painel.insumoDesativarConfirmado": ("POST", "/painel/estoque/1/desativar"),
    "painel.insumoReativar": ("POST", "/painel/estoque/26/reativar"),
    "painel.compras": ("GET", "/painel/compras"),
    "painel.compraNova": ("GET", "/painel/compras/nova"),
    "painel.compraNovaSalvar": ("POST", "/painel/compras/nova"),
    "painel.compraReceber": ("GET", "/painel/compras/2/receber"),
    "painel.compraReceberConfirmado": ("POST", "/painel/compras/2/receber"),
    "painel.compraCancelar": ("GET", "/painel/compras/2/cancelar"),
    "painel.compraCancelarConfirmado": ("POST", "/painel/compras/2/cancelar"),
    "painel.fornecedores": ("GET", "/painel/fornecedores"),
    "painel.fornecedorNovo": ("GET", "/painel/fornecedores/novo"),
    "painel.fornecedorNovoSalvar": ("POST", "/painel/fornecedores/novo"),
    "painel.fornecedorEditar": ("GET", "/painel/fornecedores/1/editar"),
    "painel.fornecedorEditarSalvar": ("POST", "/painel/fornecedores/1/editar"),
    "painel.fornecedorDesativar": ("GET", "/painel/fornecedores/1/desativar"),
    "painel.fornecedorDesativarConfirmado": ("POST", "/painel/fornecedores/1/desativar"),
    "painel.fornecedorReativar": ("POST", "/painel/fornecedores/4/reativar"),
    "painel.clientes": ("GET", "/painel/clientes"),
    "painel.cliente": ("GET", "/painel/clientes/10"),
    "painel.clienteNovo": ("GET", "/painel/clientes/novo"),
    "painel.clienteNovoSalvar": ("POST", "/painel/clientes/novo"),
    "painel.clienteEditar": ("GET", "/painel/clientes/10/editar"),
    "painel.clienteEditarSalvar": ("POST", "/painel/clientes/10/editar"),
    "painel.clienteVip": ("POST", "/painel/clientes/10/vip"),
    "painel.clienteDesativar": ("GET", "/painel/clientes/10/desativar"),
    "painel.clienteDesativarConfirmado": ("POST", "/painel/clientes/10/desativar"),
    "painel.clienteReativar": ("POST", "/painel/clientes/15/reativar"),
    "painel.funcionarios": ("GET", "/painel/funcionarios"),
    "painel.funcionarioNovo": ("GET", "/painel/funcionarios/novo"),
    "painel.funcionarioNovoSalvar": ("POST", "/painel/funcionarios/novo"),
    "painel.funcionarioEditar": ("GET", "/painel/funcionarios/2/editar"),
    "painel.funcionarioEditarSalvar": ("POST", "/painel/funcionarios/2/editar"),
    "painel.funcionarioDesativar": ("GET", "/painel/funcionarios/2/desativar"),
    "painel.funcionarioDesativarConfirmado": ("POST", "/painel/funcionarios/2/desativar"),
    "painel.funcionarioReativar": ("POST", "/painel/funcionarios/2/reativar"),
    "painel.relatorios": ("GET", "/painel/relatorios"),
    "painel.relatorioExportar": ("GET", "/painel/relatorios/exportar"),
}

# Rotas que ainda não seguem a regra da lista em que estão: o teste delas é xfail
# (falha esperada). Quando a rota for corrigida, o xfail(strict=True) vira erro para lembrar de tirar daqui
SEM_SO_CLIENTE = pytest.mark.xfail(
    strict=True,
    reason="Em construção (Tarefa 10) e ainda sem @soCliente: hoje qualquer pessoa abre",
)
PENDENTES = {
    "loja.pedidoEnviar": SEM_SO_CLIENTE,
    "loja.pedidos": SEM_SO_CLIENTE,
    "loja.pedido": SEM_SO_CLIENTE,
}


def casos(rotas, pendentes=None):
    """
    Transforma {endpoint: (método, url)} nos casos do parametrize

    O id de cada caso é o endpoint: o relatório mostra "painel.produtoNovo" em vez de "POST-/painel/..."
    `pendentes`: {endpoint: marca} das rotas que ainda não cumprem a regra
    """
    marcas = pendentes or {}
    return [
        pytest.param(metodo, url, id=endpoint, marks=marcas.get(endpoint, ()))
        for endpoint, (metodo, url) in rotas.items()
    ]


def so_get(rotas):
    """Só as rotas GET: dá para abrir todas sem mudar nada no banco"""
    return dict(filter(lambda item: item[1][0] == "GET", rotas.items()))


def test_toda_rota_do_app_esta_na_matriz(app):
    rotas_do_app = {regra.endpoint for regra in app.url_map.iter_rules()} - {"static"}

    assert rotas_do_app == set(ABERTAS) | set(DO_CLIENTE) | set(DA_EQUIPE) | set(SO_ADMIN)


# Quem não pode, não passa
@pytest.mark.parametrize("metodo, url", casos(DO_CLIENTE | DA_EQUIPE, PENDENTES))
def test_visitante_e_mandado_para_o_login(navegador, metodo, url):
    resposta = navegador.open(url, method=metodo)

    assert resposta.status_code == 302
    assert destino_do_login(resposta) == ("/entrar", url)


@pytest.mark.parametrize("id_usuario", [2, 1], ids=["funcionario", "administradora"])
@pytest.mark.parametrize("metodo, url", casos(DO_CLIENTE, PENDENTES))
def test_equipe_nao_entra_nas_paginas_do_cliente(navegador, entrar_como, id_usuario, metodo, url):
    entrar_como(id_usuario)

    assert navegador.open(url, method=metodo).status_code == 403


@pytest.mark.parametrize("metodo, url", casos(DA_EQUIPE | SO_ADMIN))
def test_cliente_nao_entra_no_painel(navegador, como_cliente, metodo, url):
    assert navegador.open(url, method=metodo).status_code == 403


@pytest.mark.parametrize("metodo, url", casos(SO_ADMIN))
def test_funcionario_nao_entra_no_que_e_so_da_administracao(navegador, como_funcionario, metodo, url):
    assert navegador.open(url, method=metodo).status_code == 403


# Quem pode, entra
PAGINAS_ABERTAS = so_get(ABERTAS)
# O /sair é GET, mas não é página: ele redireciona (está em test_acesso.py)
PAGINAS_ABERTAS.pop("acesso.sair")


@pytest.mark.parametrize("metodo, url", casos(PAGINAS_ABERTAS))
def test_visitante_abre_as_paginas_abertas(navegador, metodo, url):
    assert navegador.open(url, method=metodo).status_code == 200


@pytest.mark.parametrize("metodo, url", casos(so_get(DO_CLIENTE)))
def test_cliente_abre_as_paginas_dele(navegador, como_cliente, metodo, url):
    assert navegador.open(url, method=metodo).status_code == 200


@pytest.mark.parametrize("metodo, url", casos(so_get(DA_EQUIPE)))
def test_funcionario_abre_as_paginas_da_equipe(navegador, como_funcionario, metodo, url):
    assert navegador.open(url, method=metodo).status_code == 200


@pytest.mark.parametrize("metodo, url", casos(so_get(DA_EQUIPE | SO_ADMIN)))
def test_administradora_abre_todas_as_paginas_do_painel(navegador, como_admin, metodo, url):
    assert navegador.open(url, method=metodo).status_code == 200
