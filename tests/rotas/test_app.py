"""
tests / rotas / test_app.py

"""

from flask import abort

from app.repositories.usuarios_rep import RepositorioUsuarios
from app.services.autenticacao import Autenticacao


def test_app_tem_os_tres_blueprints(app):
    assert set(app.blueprints) == {"acesso", "loja", "painel"}


def test_app_guarda_o_repositorio_de_usuarios_e_a_autenticacao(app):
    assert isinstance(app.extensions["usuarios"], RepositorioUsuarios)
    assert isinstance(app.extensions["autenticacao"], Autenticacao)


# Páginas de erro
def test_endereco_que_nao_existe_mostra_a_pagina_404(navegador, templates):
    resposta = navegador.get("/pagina-que-nao-existe")

    assert resposta.status_code == 404
    nome, variaveis = templates[-1]
    assert nome == "erro.html"
    assert variaveis["titulo"] == "Página não encontrada"


def test_abort_403_mostra_a_pagina_de_acesso_restrito(app, navegador, templates):
    # Nenhuma rota do sistema chama abort(403) ainda: o teste cria uma só para ele
    app.add_url_rule("/teste-403", "teste_403", lambda: abort(403))

    resposta = navegador.get("/teste-403")

    assert resposta.status_code == 403
    assert templates[-1][1]["titulo"] == "Página com acesso restrito"


def test_erro_inesperado_mostra_a_pagina_500(app, navegador, templates):
    def rota_quebrada():
        raise RuntimeError("bug de propósito")

    app.add_url_rule("/teste-500", "teste_500", rota_quebrada)
    # Em modo de teste o Flask deixa o erro "vazar" para o teste (mais fácil de depurar).
    # Desligando isso, ele faz o que faria em produção: chama o tratador do erro 500
    app.config["PROPAGATE_EXCEPTIONS"] = False

    resposta = navegador.get("/teste-500")

    assert resposta.status_code == 500
    assert templates[-1][1]["titulo"] == "Erro interno"
    assert "bug de propósito" not in resposta.get_data(as_text=True)


def test_metodo_nao_aceito_responde_405(navegador):
    # /loja só tem GET
    assert navegador.post("/loja").status_code == 405


# Variáveis globais (context_processor)
def test_visitante_chega_nos_templates_como_usuario_atual_none(navegador, templates):
    navegador.get("/entrar")

    variaveis = templates[-1][1]
    assert variaveis["usuario_atual"] is None
    assert variaveis["qtd_carrinho"] == 0


def test_usuario_logado_chega_em_todo_template(navegador, como_cliente, templates):
    navegador.get("/loja/cardapio")

    assert templates[-1][1]["usuario_atual"].id == 10


def test_qtd_carrinho_soma_as_unidades_de_todas_as_linhas(navegador, templates):
    navegador.post("/loja/carrinho/adicionar", data={"produto_id": "18", "quantidade": "2"})
    navegador.post("/loja/carrinho/adicionar", data={"produto_id": "19", "quantidade": "3"})

    navegador.get("/loja")

    assert templates[-1][1]["qtd_carrinho"] == 5
