"""
app / controllers / acesso.py

Telas de entrada: início, entrar, criar conta e sair
"""

from flask import Blueprint, render_template

acesso = Blueprint("acesso", __name__)


@acesso.get("/")
def inicio():
    """Tela inicial (splash) para quem ainda não entrou"""
    return render_template("acesso/inicio.html")


@acesso.get("/entrar")
def login():
    """Mostra o formulário de login"""
    return render_template("acesso/login.html")


@acesso.post("/entrar")
def loginEnviar():
    """Recebe e-mail e senha do formulário de login"""
    return "em construção"


@acesso.get("/cadastro")
def cadastro():
    """Mostra o formulário de criar conta"""
    return render_template("acesso/cadastro.html")


@acesso.post("/cadastro")
def cadastroEnviar():
    """Recebe os dados da conta nova"""
    return "em construção"


@acesso.get("/sair")
def sair():
    """Encerra a sessão e volta ao início"""
    # redirect.
    return "..."
