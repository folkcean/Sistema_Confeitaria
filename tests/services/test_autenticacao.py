import pytest

from app.exceptions import AutenticacaoError, ValidacaoError
from app.models.cliente import Cliente
from app.services.autenticacao import Autenticacao
from app.services.controle_login import ControleLogin, PoliticaBloqueio


class RepositorioFalso:
    """Repositório de mentira: guarda os usuários num dicionário por e-mail"""

    def __init__(self, *usuarios):
        self._por_email = {usuario.email: usuario for usuario in usuarios}

    def buscarPorEmail(self, email):
        return self._por_email.get(email)


@pytest.fixture
def auth(cliente):
    """Autenticacao com Ana (tem senha) e Beto (sem senha), bloqueio em 2 falhas"""
    beto = Cliente("Beto Lima", "beto@exemplo.com", "22999990004", None, id_usuario=11)
    return Autenticacao(
        RepositorioFalso(cliente, beto),
        "chave-de-teste-123",
        controle=ControleLogin(PoliticaBloqueio(max_tentativas=2)),
    )


def mensagem_de(auth, email, senha):
    """Tenta o login, exige que falhe e devolve a mensagem do erro"""
    with pytest.raises(AutenticacaoError) as info:
        auth.autenticar(email, senha)
    return str(info.value)


# Construtor
def test_chave_secreta_com_15_caracteres_levanta_erro():
    with pytest.raises(ValidacaoError, match="ao menos 16 caracteres"):
        Autenticacao(RepositorioFalso(), "a" * 15)


def test_chave_secreta_com_16_caracteres_e_aceita():
    Autenticacao(RepositorioFalso(), "a" * 16)


def test_chave_secreta_vazia_levanta_erro():
    with pytest.raises(ValidacaoError, match="ao menos 16 caracteres"):
        Autenticacao(RepositorioFalso(), "")


# Login
def test_login_com_credenciais_certas_devolve_o_proprio_cliente(
    auth, cliente, senha_forte
):
    assert auth.autenticar("ana@exemplo.com", senha_forte) is cliente


def test_login_normaliza_o_email(auth, cliente, senha_forte):
    assert auth.autenticar(" ANA@EXEMPLO.COM ", senha_forte) is cliente


def test_senha_errada_levanta_erro_com_a_mensagem_de_falha(auth):
    mensagem = mensagem_de(auth, "ana@exemplo.com", "senha-errada")

    assert mensagem == Autenticacao.MENSAGEM_FALHA


def test_toda_falha_de_login_devolve_a_mesma_mensagem(auth, cliente, senha_forte):
    cliente.desativar()

    mensagens = {
        mensagem_de(auth, "ninguem@exemplo.com", senha_forte),  # e-mail inexistente
        mensagem_de(auth, "ana@exemplo.com", senha_forte),  # conta inativa
        mensagem_de(auth, "beto@exemplo.com", senha_forte),  # usuário sem senha
    }

    assert mensagens == {Autenticacao.MENSAGEM_FALHA}


# Bloqueio dentro do login
def test_terceira_tentativa_com_senha_certa_e_barrada_pelo_bloqueio(auth, senha_forte):
    mensagem_de(auth, "ana@exemplo.com", "errada-1")
    mensagem_de(auth, "ana@exemplo.com", "errada-2")

    with pytest.raises(AutenticacaoError, match="Muitas tentativas"):
        auth.autenticar("ana@exemplo.com", senha_forte)


def test_falhas_com_maiusculas_e_minusculas_contam_juntas(auth, senha_forte):
    mensagem_de(auth, "ANA@EXEMPLO.COM", "errada")
    mensagem_de(auth, "ana@exemplo.com", "errada")

    with pytest.raises(AutenticacaoError, match="Muitas tentativas"):
        auth.autenticar("Ana@Exemplo.com", senha_forte)


def test_sucesso_zera_a_contagem_de_falhas(auth, senha_forte):
    mensagem_de(auth, "ana@exemplo.com", "errada")
    auth.autenticar("ana@exemplo.com", senha_forte)
    mensagem_de(auth, "ana@exemplo.com", "errada")

    auth.autenticar("ana@exemplo.com", senha_forte)


# Tokens
def test_token_valido_devolve_uid_e_perfil(auth, cliente):
    token = auth.gerarToken(cliente)

    assert auth.validarToken(token) == {"uid": 10, "perfil": "cliente"}


def test_token_do_administrador_traz_o_perfil_administrador(auth, administrador):
    token = auth.gerarToken(administrador)

    assert auth.validarToken(token) == {"uid": 1, "perfil": "administrador"}


def test_token_adulterado_levanta_sessao_invalida(auth, cliente):
    token = auth.gerarToken(cliente)
    adulterado = token[:-5] + "xxxxx"

    with pytest.raises(AutenticacaoError, match="Sessão inválida"):
        auth.validarToken(adulterado)


def test_texto_qualquer_levanta_sessao_invalida(auth):
    with pytest.raises(AutenticacaoError, match="Sessão inválida"):
        auth.validarToken("lixo")


def test_token_gerado_com_outra_chave_levanta_sessao_invalida(auth, cliente):
    outra = Autenticacao(RepositorioFalso(), "outra-chave-secreta-1")
    token_de_outra_chave = outra.gerarToken(cliente)

    with pytest.raises(AutenticacaoError, match="Sessão inválida"):
        auth.validarToken(token_de_outra_chave)


def test_token_vencido_levanta_sessao_expirada(auth, cliente, monkeypatch):
    token = auth.gerarToken(cliente)
    monkeypatch.setattr(Autenticacao, "VALIDADE_TOKEN_SEGUNDOS", -1)

    with pytest.raises(AutenticacaoError, match="Sessão expirada"):
        auth.validarToken(token)
