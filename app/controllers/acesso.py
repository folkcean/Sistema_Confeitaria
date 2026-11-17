"""
app / controllers / acesso.py

Telas de entrada: início, entrar, criar conta e sair
"""
import time

from flask import Blueprint, current_app, render_template, redirect, url_for, request, flash, session

from app import usuarioLogado
from app.controllers.sessao import autenticacao, soCliente
from app.exceptions import AutenticacaoError, ValidacaoError, EnvioEmailError
from app.models import Perfil, Cliente, Senha
from app.repositories.clientes_rep import RepositorioClientes
from app.repositories.conexao_rep import obterConexao
from app.validators.campos import garantir, Validador
from app.validators.senha import ValidadorSenha

acesso = Blueprint("acesso", __name__)
repo_clientes = RepositorioClientes(obterConexao)

# Intervalo mínimo entre dois e-mails de confirmação pedidos pela mesma pessoa (evita spam no provedor)
INTERVALO_REENVIO_EM_SEGUNDOS = 60 

TIPOS_DE_SAIDA = {
    Perfil.CLIENTE: "loja.home",
    Perfil.ADMINISTRADOR: "painel.inicio",
    Perfil.FUNCIONARIO: "painel.inicio",
}


@acesso.get("/")
def inicio():
    usuario = usuarioLogado()
    # Se o usuario NÃO estiver logado, carrega a pagina inicial de visitante.
    # Caso contrario, carrega a pagina especifica do tipo de usuario.
    saidas = {
        False: lambda: render_template("acesso/inicio.html"),
        True: lambda: redirect(url_for(TIPOS_DE_SAIDA[usuario.perfil]))
    }

    return saidas[usuario is not None]()

    """Tela inicial (splash) para quem ainda não entrou"""
    return render_template("acesso/inicio.html")


@acesso.get("/entrar")
def login():
    """Mostra o formulário de login"""
    return render_template("acesso/login.html", proximo=request.args.get("proximo"))


@acesso.post("/entrar")
def loginEnviar():
    email = request.form.get("email", "")
    senha_bruta = request.form.get("senha", "")
    lembrar = "lembrar" in request.form
    proximo = request.form.get("proximo")

    try:
        usuario = autenticacao().autenticar(email, senha_bruta)
    except AutenticacaoError as error:
        flash(str(error), "erro")
        pagina = render_template("acesso/login.html", proximo=proximo)
        return pagina, 400

    # Se ele chegou aqui, ele conseguiu logar.
    session["token"] = autenticacao().gerarToken(usuario)
    session.permanent = lembrar
    # .split separa as palavras do nome em um vetor.
    # [0] pega so a primeira palavra do nome desse vetor.
    flash(f"Bem-vindo(a) de volta, {usuario.nome.split()[0]}.", "sucesso")
    destino_padrao = url_for(TIPOS_DE_SAIDA[usuario.perfil])

    return redirect(proximo or destino_padrao)


@acesso.get("/cadastro")
def cadastro():
    """Mostra o formulário de criar conta"""
    descricao_regras = []
    for regra in ValidadorSenha.REGRAS:
        descricao = regra.descricao
        descricao_regras.append(descricao)

    return render_template("acesso/cadastro.html", regras_senha=descricao_regras)


@acesso.post("/cadastro")
def cadastroEnviar():
    """Cria a conta do cliente, já deixa logado e manda para a loja"""
    nome = request.form.get("nome")
    apelido = request.form.get("apelido", "")
    telefone = request.form.get("telefone")
    email = request.form.get("email")
    data_nascimento = request.form.get("data_nascimento", "")
    senha_bruta = request.form.get("senha")
    confirmar_senha = request.form.get("confirmar_senha")

    try:
        # Regra da tela: o Cliente não sabe que existe "confirmar senha"
        garantir(senha_bruta == confirmar_senha, ValidacaoError("As senhas não são iguais."))
        # No model o e-mail é opcional, mas o login é só por e-mail: aqui ele é obrigatório
        Validador.email(email)
        # Senha.criar valida a força (SenhaFracaError); o Cliente valida o resto
        cliente = Cliente(
            nome=nome,
            email=email,
            telefone=telefone,
            cpf=None,
            data_nascimento=data_nascimento,
            apelido=apelido,
            senha=Senha.criar(senha_bruta),
        )
        # E-mail ou telefone repetido vira ValidacaoError dentro do repositório
        repo_clientes.cadastrarCliente(cliente)
    except ValidacaoError as erro:
        flash(str(erro), "erro")

        descricao_regras = []
        for regra in ValidadorSenha.REGRAS:
            descricao = regra.descricao
            descricao_regras.append(descricao)

        pagina = render_template("acesso/cadastro.html", regras_senha=descricao_regras)
        return pagina, 400

    # Já entra logado: o mesmo token que o login gera
    session["token"] = autenticacao().gerarToken(cliente)
    flash("Conta criada! Que bom ter você aqui.", "sucesso")
    # A conta já existe: se o e-mail de confirmação falhar, a pessoa não perde o cadastro.
    # O aviso no topo da loja oferece reenviar
    try:
        enviarLinkDeVerificacao(cliente)
    except EnvioEmailError:
        flash("Não conseguimos enviar o e-mail de confirmação agora. Peça um novo link no aviso do topo da loja.",
              "aviso")
    return redirect(url_for("loja.home"))

def enviarLinkDeVerificacao(usuario):
    """
    Manda o e-mail com o link de confirmação e anota na sessão a hora do envio (para o intervalo do reenvio)

    O lambda monta o endereço completo: url_for(..., _external=True) devolve 'http://host/verificar-email/<token>'
    """
    montarLink = lambda token: url_for("acesso.verificarEmail", token=token, _external=True)
    current_app.extensions["verificacao_email"].enviarLink(usuario, montarLink)
    session["ultimo_envio_verificacao"] = time.time()


@acesso.get("/verificar-email/<token>")
def verificarEmail(token):
    """
    Abre o link recebido por e-mail e confirma o e-mail. Não exige login: a pessoa pode abrir o
    e-mail em outro aparelho. Sempre volta para o início (quem está logado segue para a sua área)
    """
    try:
        current_app.extensions["verificacao_email"].confirmar(token)
        flash("E-mail confirmado! Obrigada.", "sucesso")
    except ValidacaoError as erro:
        flash(str(erro), "erro")
    return redirect(url_for("acesso.inicio"))


@acesso.post("/verificar-email/reenviar")
@soCliente
def reenviarVerificacao():
    """Envia outro link de confirmação para o cliente logado (no máximo um por minuto)"""
    cliente = usuarioLogado()
    try:
        segundos_desde_o_ultimo = time.time() - session.get("ultimo_envio_verificacao", 0)
        garantir(
            segundos_desde_o_ultimo >= INTERVALO_REENVIO_EM_SEGUNDOS,
            ValidacaoError("Aguarde um minuto antes de pedir outro e-mail de confirmação."),
        )
        enviarLinkDeVerificacao(cliente)
        flash(f"Enviamos um novo link para {cliente.email}.", "sucesso")
    except (ValidacaoError, EnvioEmailError) as erro:
        flash(str(erro), "erro")
    return redirect(url_for("loja.home"))

@acesso.get("/sair")
def sair():
    """Encerra a sessão e volta ao início"""
    session.clear()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("acesso.inicio"))
