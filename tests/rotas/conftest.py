"""
tests / rotas / conftest.py

Fixtures dos testes de rota

"""

from pathlib import Path

import pytest
from flask import g, message_flashed, template_rendered

from app import create_app
from app.config import ConfigTeste
from app.repositories.usuarios_rep import RepositorioUsuarios

# O mesmo DB_fill.sql da fixture `seed` (tests/conftest.py)
SEED = Path(__file__).resolve().parent.parent / "db" / "DB_fill.sql"


class ConexaoDeTeste:
    """
    A conexão dos testes, embrulhada para o app não conseguir fechá-la

    O app fecha a conexão no fim de toda requisição (fecharConexao). No teste ela precisa
    continuar aberta até o fim, para o rollback desfazer tudo. Então o close() daqui não faz
    nada, e qualquer outro atributo (cursor, transaction...) vem da conexão de verdade
    """

    def __init__(self, conexao):
        """Guarda a conexão real"""
        self._conexao = conexao

    def __getattr__(self, nome):
        """O Python chama este método para todo atributo que a classe não tem: repassa para a conexão real"""
        return getattr(self._conexao, nome)

    def close(self):
        """Não fecha: quem fecha é a fixture `conexao`, no fim de todos os testes"""


def app_com_a_conexao_de_teste(conexao):
    """
    Cria o app de teste e faz toda requisição dele usar a conexão do teste

    O obterConexao do app procura a conexão em `g` antes de abrir uma nova. O before_request
    deixa a conexão de teste lá no começo de cada requisição: assim os repositórios das rotas
    usam a transação do teste, e nada é gravado de verdade no seu banco
    """
    aplicacao = create_app(ConfigTeste)

    def usar_conexao_de_teste():
        g.conexao = ConexaoDeTeste(conexao)

    aplicacao.before_request(usar_conexao_de_teste)
    return aplicacao


@pytest.fixture
def app(conexao, seed):
    """App Flask de teste, com o DB_fill.sql carregado (um app e um seed novos por teste)"""
    return app_com_a_conexao_de_teste(conexao)


@pytest.fixture(scope="module")
def app_somente_leitura(conexao):
    """
    Um app e um seed para o ARQUIVO de teste inteiro, em vez de um por teste

    Criar o app (~0,07 s, por causa do hash isca da Autenticacao) e carregar o seed (~0,05 s)
    em cada teste pesa na matriz de acesso, que tem quase 200 casos. Lá pode compartilhar porque
    nenhum teste grava nada no banco: quem não pode entrar é barrado antes, e quem pode só abre
    páginas (GET). Teste que grava alguma coisa usa o `app` normal
    """
    with conexao.cursor() as cursor:
        cursor.execute("select 1")
        cursor.execute(SEED.read_text(encoding="utf-8"))
        yield app_com_a_conexao_de_teste(conexao)
    conexao.rollback()


@pytest.fixture
def navegador(app):
    """
    O "navegador" dos testes (test_client do Flask)

    Não se chama `cliente` porque essa fixture já é o Cliente da confeitaria (tests/conftest.py)
    """
    return app.test_client()


@pytest.fixture
def entrar_como(app, navegador, conexao):
    """
    Função que deixa o navegador logado como o usuário com esse id, e devolve o usuário

    Põe na sessão o mesmo token que o POST /entrar poria, sem gastar o tempo do hash da senha.
    O login de verdade, com e-mail e senha, é testado em test_acesso.py
    """
    usuarios = RepositorioUsuarios(lambda: conexao)

    def entrar(id_usuario):
        usuario = usuarios.buscarPorId(id_usuario)
        token = app.extensions["autenticacao"].gerarToken(usuario)
        # session_transaction: abre a sessão do navegador para o teste mexer nela
        with navegador.session_transaction() as sessao:
            sessao["token"] = token
        return usuario

    return entrar


@pytest.fixture
def como_cliente(entrar_como):
    """Navegador logado como a cliente Ana (id 10)"""
    return entrar_como(10)


@pytest.fixture
def como_funcionario(entrar_como):
    """Navegador logado como o funcionário Joao (id 2)"""
    return entrar_como(2)


@pytest.fixture
def como_admin(entrar_como):
    """Navegador logado como a administradora Rosangela (id 1), que tem acesso financeiro"""
    return entrar_como(1)


@pytest.fixture
def templates(app):
    """
    Lista dos templates que o Flask renderizou no teste, cada um como (nome, variáveis)

    O Flask avisa por um "sinal" (template_rendered) toda vez que renderiza um template.
    Assim o teste confere o que a rota mandou para a tela sem garimpar o HTML:
        nome, variaveis = templates[-1]
        assert nome == "loja/catalogo.html"
    """
    renderizados = []

    def anotar(remetente, template, context, **extras):
        renderizados.append((template.name, context))

    template_rendered.connect(anotar, app)
    yield renderizados
    template_rendered.disconnect(anotar, app)


@pytest.fixture
def mensagens(app):
    """
    Lista dos flash() dados no teste, cada um como (categoria, texto)

    Também usa um sinal do Flask (message_flashed). Vale para os dois casos: rota que redireciona
    (a mensagem só apareceria na próxima página) e rota que renderiza a página na hora
    """
    recebidas = []

    def anotar(remetente, message, category, **extras):
        recebidas.append((category, message))

    message_flashed.connect(anotar, app)
    yield recebidas
    message_flashed.disconnect(anotar, app)
