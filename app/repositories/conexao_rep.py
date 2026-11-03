import psycopg
from flask import current_app, g


def _abrirEGuardar():
    """Abre a conexão com os dados da config e guarda em g (uso interno)"""
    config = current_app.config
    g.conexao = psycopg.connect(
        host=config["POSTGRES_HOST"],
        port=config["POSTGRES_PORT"],
        user=config["POSTGRES_USER"],
        password=config["POSTGRES_PASSWORD"],
        dbname=config["POSTGRES_DB"],
        # Cada comando confirma sozinho; o que for tudo ou nada vai em `with conexao.transaction():`
        autocommit=True,
    )
    return g.conexao


def obterConexao():
    """Devolve a conexão desta requisição, abrindo na primeira vez"""
    # g.get devolve None se ainda não abriu; o `or` só chama _abrirEGuardar nesse caso
    return g.get("conexao") or _abrirEGuardar()


def fecharConexao(Erro=None):
    """Fecha a conexão no fim da requisição (registrada com app.teardown_appcontext)"""
    # pop tira de g e devolve a conexão, ou None se a requisição nunca usou o banco
    conexao = g.pop("conexao", None)
    # `and` curto-circuita: com None, o close() nem é chamado
    conexao and conexao.close()
