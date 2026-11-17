"""
tests / services / test_verificacao_email.py

app/services/verificacao_email.py: gerar o link, enviar o e-mail e confirmar quando o link é aberto.
Sem banco e sem rede: o repositório é um dicionário (RepositorioEmMemoria) e o e-mail vai para o EnviadorFalso.

COMO RODAR SÓ ESTE ARQUIVO:   pytest tests/services/test_verificacao_email.py -v
"""
import pytest

from app.exceptions import EnvioEmailError, ValidacaoError
from app.models.cliente import Cliente
from app.services.autenticacao import Autenticacao
from app.services.verificacao_email import VerificacaoEmail
from tests.falsos import EnviadorFalso

CHAVE = "chave-de-teste-123"


class RepositorioEmMemoria:
    """Repositório de mentira: guarda os usuários por id e anota quem foi gravado como verificado"""

    def __init__(self, *usuarios):
        self._por_id = {usuario.id: usuario for usuario in usuarios}
        self.gravados = []

    def buscarPorId(self, id_usuario):
        return self._por_id.get(id_usuario)

    def marcarEmailVerificado(self, usuario):
        self.gravados.append(usuario.id)


@pytest.fixture
def ana():
    """Cliente com e-mail, ainda não verificado (fixture local: não depende do conftest da pasta)"""
    return Cliente("Ana Souza", "ana@exemplo.com", "22999990001", None, id_usuario=10)


@pytest.fixture
def enviador():
    return EnviadorFalso()


@pytest.fixture
def repositorio(ana):
    return RepositorioEmMemoria(ana)


@pytest.fixture
def verificacao(enviador, repositorio):
    return VerificacaoEmail(enviador, repositorio, CHAVE)


def montarLink(token):
    return f"http://localhost:5000/verificar-email/{token}"


def tokenEnviado(enviador):
    """Pega o token do link que foi no e-mail (o que vem depois de /verificar-email/)"""
    return enviador.enviados[-1]["texto"].split("/verificar-email/")[1].split()[0]


# ENVIO
def test_envia_o_link_para_o_email_do_usuario(verificacao, enviador, ana):
    verificacao.enviarLink(ana, montarLink)

    assert len(enviador.enviados) == 1
    email = enviador.enviados[0]
    assert email["para"] == "ana@exemplo.com"
    assert email["assunto"] == VerificacaoEmail.ASSUNTO
    assert "Olá, Ana!" in email["texto"]
    assert "http://localhost:5000/verificar-email/" in email["texto"]
    assert "não responda" in email["texto"]


def test_nao_envia_para_quem_nao_tem_email(verificacao, enviador):
    beto = Cliente("Beto Lima", None, "22999990004", None, id_usuario=11)

    with pytest.raises(ValidacaoError, match="Cadastre um e-mail"):
        verificacao.enviarLink(beto, montarLink)

    assert enviador.enviados == []


def test_nao_envia_para_quem_ja_confirmou(verificacao, enviador, ana):
    ana.marcarEmailVerificado()

    with pytest.raises(ValidacaoError, match="já está confirmado"):
        verificacao.enviarLink(ana, montarLink)

    assert enviador.enviados == []


def test_falha_no_envio_sobe_para_quem_chamou(repositorio, ana):
    verificacao = VerificacaoEmail(EnviadorFalso(falhar=True), repositorio, CHAVE)

    with pytest.raises(EnvioEmailError):
        verificacao.enviarLink(ana, montarLink)


# CONFIRMAÇÃO
def test_link_valido_confirma_o_email_e_grava(verificacao, enviador, repositorio, ana):
    verificacao.enviarLink(ana, montarLink)

    confirmado = verificacao.confirmar(tokenEnviado(enviador))

    assert confirmado is ana
    assert ana.email_verificado is True
    assert repositorio.gravados == [10]


def test_abrir_o_link_duas_vezes_nao_da_erro(verificacao, enviador, ana):
    verificacao.enviarLink(ana, montarLink)
    token = tokenEnviado(enviador)

    verificacao.confirmar(token)
    verificacao.confirmar(token)

    assert ana.email_verificado is True


def test_link_vencido(verificacao, enviador, ana, monkeypatch):
    verificacao.enviarLink(ana, montarLink)
    # Validade negativa: qualquer token já nasce vencido (evita esperar 24 h no teste)
    monkeypatch.setattr(VerificacaoEmail, "VALIDADE_SEGUNDOS", -1)

    with pytest.raises(ValidacaoError, match="venceu"):
        verificacao.confirmar(tokenEnviado(enviador))

    assert ana.email_verificado is False


@pytest.mark.parametrize("token", ["lixo", "", "abc.def.ghi"])
def test_link_inventado(verificacao, ana, token):
    with pytest.raises(ValidacaoError, match="inválido"):
        verificacao.confirmar(token)

    assert ana.email_verificado is False


def test_link_adulterado(verificacao, enviador, ana):
    verificacao.enviarLink(ana, montarLink)
    token = tokenEnviado(enviador)
    adulterado = token[:-3] + ("AAA" if not token.endswith("AAA") else "BBB")

    with pytest.raises(ValidacaoError, match="inválido"):
        verificacao.confirmar(adulterado)


def test_link_assinado_com_outra_chave(enviador, repositorio, ana):
    VerificacaoEmail(enviador, repositorio, "outra-chave").enviarLink(ana, montarLink)

    with pytest.raises(ValidacaoError, match="inválido"):
        VerificacaoEmail(enviador, repositorio, CHAVE).confirmar(tokenEnviado(enviador))


def test_token_de_login_nao_confirma_email(verificacao, ana, repositorio):
    # O "salt" é diferente: o token que serve de sessão não pode ser usado como link de confirmação
    token_de_login = Autenticacao(repositorio, CHAVE).gerarToken(ana)

    with pytest.raises(ValidacaoError, match="inválido"):
        verificacao.confirmar(token_de_login)


def test_link_para_conta_que_nao_existe_mais(enviador, ana):
    VerificacaoEmail(enviador, RepositorioEmMemoria(ana), CHAVE).enviarLink(ana, montarLink)
    sem_ninguem = VerificacaoEmail(enviador, RepositorioEmMemoria(), CHAVE)

    with pytest.raises(ValidacaoError, match="não vale mais"):
        sem_ninguem.confirmar(tokenEnviado(enviador))


def test_link_de_conta_desativada(verificacao, enviador, repositorio):
    inativa = Cliente("Cida", "cida@exemplo.com", "22999990005", None, id_usuario=12, ativo=False)
    repositorio._por_id[12] = inativa
    # O link é gerado por quem teria o e-mail; a conta foi desativada depois
    token = verificacao.gerarToken(inativa)

    with pytest.raises(ValidacaoError, match="não vale mais"):
        verificacao.confirmar(token)

    assert inativa.email_verificado is False


def test_link_antigo_nao_vale_depois_de_trocar_o_email(verificacao, enviador, ana):
    verificacao.enviarLink(ana, montarLink)
    token_do_email_antigo = tokenEnviado(enviador)

    ana.email = "ana.nova@exemplo.com"

    with pytest.raises(ValidacaoError, match="não vale mais"):
        verificacao.confirmar(token_do_email_antigo)

    assert ana.email_verificado is False