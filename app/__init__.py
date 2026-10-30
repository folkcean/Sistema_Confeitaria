"""
app / __init__.py

Fábrica do app: cria e configura o Flask
"""

from flask import Flask, render_template

from app.config import Config
from app.repositories.conexao import fecharConexao


def paginaNaoEncontrada(erro):
    return render_template("erro.html", codigo=404, titulo="Pagina não encontrada",
                           mensagem="O endereço pode ter mudado, Volte ao início e tente novamente"), 404


def acessoNegado(erro):
    return render_template("erro.html", codigo=403, titulo="Pagina com acesso restrito.",
                           mensagem="Infelizmente, você não possuí permissão para acessar essa área."), 403


def erroInterno(erro):
    return render_template("erro.html", codigo=500, titulo="Erro Interno",
                           mensagem="Ocorreu um erro interno nos nossos servidores. Tente novamente mais tarde."), 500


def variaveisGlobais():
    return {"usuario_atual": None,
            "qtd_carrinho": len(session.get("carrinho", []))}


def create_app(config=Config):
    """Cria o app com a configuração recebida (a de teste troca só isso)"""
    app = Flask(__name__)
    app.config.from_object(config)

    # Import aqui dentro: os controllers importam coisas de `app`;
    # no topo do arquivo, um importaria o outro antes de terminar de carregar
    from app.controllers.acesso import acesso
    from app.controllers.loja import loja
    from app.controllers.painel import painel

    app.register_blueprint(acesso)
    app.register_blueprint(loja)
    app.register_blueprint(painel)

    # tratadores de erro (404, 403, 500)
    app.register_error_handler(404, paginaNaoEncontrada)
    app.register_error_handler(403, acessoNegado)
    app.register_error_handler(500, erroInterno)

    # context_processor (usuario_atual, qtd_carrinho)

    app.teardown_appcontext(fecharConexao)
    return app
