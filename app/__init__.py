from flask import Flask, render_template, session

from app.config import Config
from app.controllers.sessao import tratarAcessoNegado, tratarNaoLogado, usuarioLogado
from app.exceptions import AcessoNegadoError, AutenticacaoError
from app.repositories.conexao_rep import fecharConexao, obterConexao
from app.repositories.usuarios_rep import RepositorioUsuarios
from app.services.autenticacao import Autenticacao
from app.services.carrinho import Carrinho


def paginaNaoEncontrada(erro):
    """404: endereço que não existe (ou abort(404) numa rota)"""
    return render_template("erro.html", codigo=404, titulo="Página não encontrada",
                           mensagem="O endereço pode ter mudado. Volte ao início e tente novamente."), 404


def acessoNegado(erro):
    """403: abort(403) numa rota"""
    return render_template("erro.html", codigo=403, titulo="Página com acesso restrito",
                           mensagem="Infelizmente, você não possui permissão para acessar essa área."), 403


def erroInterno(erro):
    """500: erro inesperado no servidor (fora do modo debug)"""
    return render_template("erro.html", codigo=500, titulo="Erro interno",
                           mensagem="Ocorreu um erro interno nos nossos servidores. Tente novamente mais tarde."), 500


def variaveisGlobais():
    """Variáveis disponíveis em todo template"""
    return {
        "usuario_atual": usuarioLogado(),
        "qtd_carrinho": Carrinho(session).quantidadeDeItens(),
    }


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

    # Objetos criados uma vez só e usados pelo app inteiro
    repositorio = RepositorioUsuarios(obterConexao)
    app.extensions["usuarios"] = repositorio
    app.extensions["autenticacao"] = Autenticacao(repositorio, app.config["SECRET_KEY"])

    # Tratadores de erro: códigos HTTP e exceções do projeto
    app.register_error_handler(404, paginaNaoEncontrada)
    app.register_error_handler(403, acessoNegado)
    app.register_error_handler(500, erroInterno)
    app.register_error_handler(AutenticacaoError, tratarNaoLogado)
    app.register_error_handler(AcessoNegadoError, tratarAcessoNegado)

    # usuario_atual e qtd_carrinho em todo template
    app.context_processor(variaveisGlobais)

    # Fecha a conexão do banco no fim de cada requisição
    app.teardown_appcontext(fecharConexao)
    return app
