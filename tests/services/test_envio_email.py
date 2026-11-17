"""
tests / services / test_envio_email.py

app/services/envio_email.py: EnviadorEmailSMTP, EnviadorEmailNoTerminal e criarEnviador.
O smtplib.SMTP é trocado por um servidor de mentira (ServidorSmtpFalso): nenhum teste usa a rede.

COMO RODAR SÓ ESTE ARQUIVO:   pytest tests/services/test_envio_email.py -v
"""
import smtplib

import pytest

from app.config import ConfigTeste
from app.exceptions import EnvioEmailError
from app.services import envio_email
from app.services.envio_email import EnviadorEmailNoTerminal, EnviadorEmailSMTP, criarEnviador


def lancar(erro):
    """Levanta a exceção (um `raise` não pode ficar dentro de uma expressão `a or b`)"""
    raise erro


class ServidorSmtpFalso:
    """Imita o smtplib.SMTP: anota o que o enviador fez. A classe guarda a última instância criada"""

    ultimo = None
    falhar_com = None

    def __init__(self, servidor, porta, timeout):
        self.endereco = (servidor, porta)
        self.timeout = timeout
        self.passos = []
        self.mensagem = None
        ServidorSmtpFalso.ultimo = self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.passos.append("fechou")

    def starttls(self):
        self.passos.append("starttls")

    def login(self, usuario, senha):
        self.passos.append(("login", usuario, senha))

    def send_message(self, mensagem):
        self.passos.append("enviou")
        self.mensagem = mensagem
        # Quem falha é decidido pelo teste (atributo da classe). `a or b`: sem erro configurado, não faz nada
        erro = ServidorSmtpFalso.falhar_com
        erro is None or lancar(erro)


@pytest.fixture(autouse=True)
def servidor_falso(monkeypatch):
    """Troca o smtplib.SMTP pelo falso em todos os testes deste arquivo"""
    ServidorSmtpFalso.ultimo = None
    ServidorSmtpFalso.falhar_com = None
    monkeypatch.setattr(envio_email.smtplib, "SMTP", ServidorSmtpFalso)
    return ServidorSmtpFalso


def enviador(**trocas):
    dados = dict(servidor="smtp.exemplo.com", porta=587, usuario="conta", senha="segredo",
                 remetente="Dolce Bea <noreply@exemplo.com>", usar_tls=True)
    return EnviadorEmailSMTP(**(dados | trocas))


def test_envia_com_tls_e_login():
    enviador().enviar("ana@exemplo.com", "Assunto", "Corpo com acentuação: você")

    servidor = ServidorSmtpFalso.ultimo
    assert servidor.endereco == ("smtp.exemplo.com", 587)
    assert servidor.passos == ["starttls", ("login", "conta", "segredo"), "enviou", "fechou"]


def test_monta_a_mensagem_com_remetente_destinatario_e_assunto():
    enviador().enviar("ana@exemplo.com", "Confirme", "Olá, Ana")

    mensagem = ServidorSmtpFalso.ultimo.mensagem
    assert mensagem["From"] == "Dolce Bea <noreply@exemplo.com>"
    assert mensagem["To"] == "ana@exemplo.com"
    assert mensagem["Subject"] == "Confirme"
    assert "Olá, Ana" in mensagem.get_content()


def test_sem_tls_e_sem_usuario_so_envia():
    enviador(usar_tls=False, usuario="", senha="").enviar("ana@exemplo.com", "A", "B")

    assert ServidorSmtpFalso.ultimo.passos == ["enviou", "fechou"]


def test_tem_tempo_limite_para_nao_travar_o_site():
    enviador().enviar("ana@exemplo.com", "A", "B")

    assert ServidorSmtpFalso.ultimo.timeout == 15


@pytest.mark.parametrize("erro", [smtplib.SMTPAuthenticationError(535, b"senha errada"),
                                  smtplib.SMTPRecipientsRefused({}), ConnectionRefusedError("sem servidor"),
                                  TimeoutError("demorou")],
                         ids=["senha errada", "destinatário recusado", "conexão recusada", "tempo esgotado"])
def test_falha_do_servidor_vira_envio_email_error(erro):
    ServidorSmtpFalso.falhar_com = erro

    with pytest.raises(EnvioEmailError, match="Não foi possível enviar o e-mail") as info:
        enviador().enviar("ana@exemplo.com", "A", "B")

    # `from erro` guarda o motivo técnico para quem for investigar
    assert info.value.__cause__ is erro


def test_enviador_do_terminal_mostra_o_email_sem_enviar(capsys):
    EnviadorEmailNoTerminal().enviar("ana@exemplo.com", "Confirme", "http://localhost:5000/verificar-email/abc")

    saida = capsys.readouterr().out
    assert "ana@exemplo.com" in saida and "Confirme" in saida and "/verificar-email/abc" in saida
    assert ServidorSmtpFalso.ultimo is None


def configuracao(**trocas):
    base = {"EMAIL_SMTP_HOST": "", "EMAIL_SMTP_PORTA": "587", "EMAIL_SMTP_USUARIO": "",
            "EMAIL_SMTP_SENHA": "", "EMAIL_SMTP_TLS": True, "EMAIL_REMETENTE": "Dolce Bea <noreply@localhost>"}
    return base | trocas


def test_sem_host_na_configuracao_usa_o_terminal():
    assert isinstance(criarEnviador(configuracao()), EnviadorEmailNoTerminal)


def test_com_host_na_configuracao_usa_smtp():
    criado = criarEnviador(configuracao(EMAIL_SMTP_HOST="smtp.exemplo.com", EMAIL_SMTP_PORTA="2525",
                                        EMAIL_SMTP_TLS=False))

    assert isinstance(criado, EnviadorEmailSMTP)
    criado.enviar("ana@exemplo.com", "A", "B")
    assert ServidorSmtpFalso.ultimo.endereco == ("smtp.exemplo.com", 2525)
    assert "starttls" not in ServidorSmtpFalso.ultimo.passos


def test_configuracao_de_teste_nao_envia_email_de_verdade():
    # Sem EMAIL_SMTP_HOST no .env, o app usa o enviador do terminal
    assert ConfigTeste.EMAIL_SMTP_HOST == ""