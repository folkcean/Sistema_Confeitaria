from functools import wraps

from flask import (
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.exceptions import AcessoNegadoError, AutenticacaoError
from app.models.enums import Perfil
from app.validators.campos import garantir

# Perfis que formam a "equipe" (podem entrar no painel)
EQUIPE = (Perfil.FUNCIONARIO, Perfil.ADMINISTRADOR)


def autenticacao():
    """A Autenticacao criada uma vez na fábrica (create_app)"""
    return current_app.extensions["autenticacao"]


def repositorioUsuarios():
    """O RepositorioUsuarios criado uma vez na fábrica (create_app)"""
    return current_app.extensions["usuarios"]


def usuarioLogado():
    """
    O usuário dono da sessão, ou None se ninguém estiver logado

    Vai ao banco no máximo uma vez por requisição: o resultado fica guardado em g
    """
    # `or`: se já está em g, usa; se não está (None), carrega da sessão
    return g.get("usuario_logado") or _carregarUsuarioDaSessao()


def _carregarUsuarioDaSessao():
    """Lê o token da sessão, busca o usuário e guarda em g"""
    token = session.get("token")
    # `and`: sem token (None) o resultado é None e nem tenta validar
    usuario = token and _usuarioDoToken(token)
    g.usuario_logado = usuario
    return usuario


def _usuarioDoToken(token):
    """
    Usuário dono do token, ou None se o token não vale mais

    Token vencido, adulterado, de usuário que não existe mais ou de conta desativada:
    tira o token da sessão e devolve None. Assim quem estava logado continua navegando
    na loja como visitante, em vez de dar erro
    """
    try:
        dados = autenticacao().validarToken(token)
        usuario = repositorioUsuarios().buscarPorId(dados["uid"])
        garantir(
            usuario is not None and usuario.ativo,
            AutenticacaoError("Sessão inválida."),
        )
    except AutenticacaoError:
        session.pop("token", None)
        return None
    return usuario


# ------------------------------------------------------------------ Controle de acesso

def conferirPerfil(perfis):
    """
    Levanta AutenticacaoError se ninguém está logado,
    ou AcessoNegadoError se o perfil de quem está logado não está em `perfis`
    """
    usuario = usuarioLogado()
    garantir(
        usuario is not None,
        AutenticacaoError("Entre na sua conta para continuar."),
    )
    garantir(
        usuario.perfil in perfis,
        AcessoNegadoError("Você não tem acesso a esta página."),
    )


def exigirPerfil(*perfis):
    """
    Decorator: a rota só roda se quem está logado tiver um dos perfis

    Uso:
        @loja.get("/conta")
        @exigirPerfil(Perfil.CLIENTE)
        def conta(): ...
    """

    def decorador(funcao_da_rota):
        # wraps copia o nome da função original: sem ele, todas as rotas protegidas
        # e se chamariam "protegida" e o Flask acusaria endpoint repetido
        @wraps(funcao_da_rota)
        def funcao_da_rota_protegida(*args, **kwargs):
            conferirPerfil(perfis)
            return funcao_da_rota(*args, **kwargs)

        return funcao_da_rota_protegida

    return decorador


# Atalhos: decorators já configurados
soCliente = exigirPerfil(Perfil.CLIENTE)
soEquipe = exigirPerfil(*EQUIPE)
soAdmin = exigirPerfil(Perfil.ADMINISTRADOR)


def conferirEquipe():
    """
    Para o @painel.before_request: roda antes de TODA rota do painel

    Devolver None (não ter return) deixa a requisição seguir para a rota
    """
    conferirPerfil(EQUIPE)


def tratarNaoLogado(erro):
    """AutenticacaoError: avisa e manda para o login, lembrando de onde a pessoa veio"""
    flash(str(erro), "aviso")
    # full_path termina em "?" quando não há query string ("/painel/?"): o rstrip tira
    proximo = request.full_path.rstrip("?")
    return redirect(url_for("acesso.login", proximo=proximo))


def tratarAcessoNegado(erro):
    """AcessoNegadoError: está logado, mas o perfil não pode ver esta página"""
    pagina = render_template(
        "erro.html",
        codigo=403,
        titulo="Acesso negado",
        mensagem=str(erro),
    )
    return pagina, 403
