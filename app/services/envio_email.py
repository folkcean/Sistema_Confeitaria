"""
app / services / envio_email.py

ENVIO DE E-MAIL (padrão Adapter, igual ao gateway_abacatepay.py)

É o único arquivo do sistema que sabe falar com um servidor de e-mail (SMTP).
O resto do sistema só chama `enviar(destinatario, assunto, texto)` (contrato EnviadorEmail).

Há dois enviadores, e quem escolhe é a configuração (criarEnviador):
    EnviadorEmailSMTP       envia de verdade (precisa de servidor SMTP: EMAIL_SMTP_HOST no .env)
    EnviadorEmailNoTerminal desenvolvimento: NÃO envia nada, só escreve o e-mail no terminal do Flask.
                            Serve para testar o fluxo sem conta de e-mail nenhuma
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.exceptions import EnvioEmailError

TEMPO_LIMITE_SMTP_EM_SEGUNDOS = 15


class EnviadorEmailSMTP:
    """
    Envia e-mails por um servidor SMTP

    `remetente` é o endereço que aparece em "De" (ex.: 'Dolce Bea <noreply@seudominio.com>').
    Atenção: servidores como o Gmail trocam o "De" pela conta autenticada. Um "noreply" de verdade
    só aparece com domínio próprio (com SPF/DKIM configurados no provedor de e-mail)
    """

    def __init__(self, servidor: str, porta: int, usuario: str, senha: str,
                 remetente: str, usar_tls: bool = True):
        self._servidor = servidor
        self._porta = porta
        self._usuario = usuario
        self._senha = senha
        self._remetente = remetente
        self._usar_tls = usar_tls

    def enviar(self, destinatario: str, assunto: str, texto: str) -> None:
        """
        Monta a mensagem e envia. Qualquer falha de rede ou do servidor vira EnvioEmailError
        (mensagem genérica para a tela: o detalhe técnico fica na exceção original, `from erro`)
        """
        mensagem = self._montarMensagem(destinatario, assunto, texto)
        try:
            # `with` fecha a conexão sozinho no fim, mesmo se der erro no meio
            with smtplib.SMTP(self._servidor, self._porta, timeout=TEMPO_LIMITE_SMTP_EM_SEGUNDOS) as conexao:
                self._prepararConexao(conexao)
                conexao.send_message(mensagem)
        except (smtplib.SMTPException, OSError) as erro:
            raise EnvioEmailError("Não foi possível enviar o e-mail agora. Tente novamente em instantes.") from erro

    def _montarMensagem(self, destinatario: str, assunto: str, texto: str) -> EmailMessage:
        """Cria o e-mail (cabeçalhos + corpo em texto simples, UTF-8 para aceitar acentos)"""
        mensagem = EmailMessage()
        mensagem["From"] = self._remetente
        mensagem["To"] = destinatario
        mensagem["Subject"] = assunto
        mensagem.set_content(texto)
        return mensagem

    def _prepararConexao(self, conexao: smtplib.SMTP) -> None:
        """
        Liga a criptografia (STARTTLS) e faz o login, quando configurados

        Tabela {True: ação, False: nada} no lugar de if: `bool(...)` escolhe a chave, `()` executa
        """
        nada = lambda: None
        passos_tls = {True: conexao.starttls, False: nada}
        passos_tls[self._usar_tls]()
        passos_login = {True: lambda: conexao.login(self._usuario, self._senha), False: nada}
        passos_login[bool(self._usuario)]()


class EnviadorEmailNoTerminal:
    """
    Enviador de DESENVOLVIMENTO: escreve o e-mail no terminal em vez de enviar
    O link de confirmação aparece ali e é só copiar e colar no navegador
    """

    def enviar(self, destinatario: str, assunto: str, texto: str) -> None:
        """Mostra o e-mail no terminal (print com flush: aparece na hora, sem esperar o buffer encher)"""
        print(
            "\n=== E-MAIL DE DESENVOLVIMENTO (não foi enviado de verdade) ===\n"
            f"Para: {destinatario}\nAssunto: {assunto}\n\n{texto}\n"
            "==============================================================\n",
            flush=True,
        )


def criarEnviador(configuracao: dict):
    """
    Escolhe o enviador pela configuração do app (app.config)

    Com EMAIL_SMTP_HOST preenchido no .env, envia de verdade; sem ele, usa o do terminal.
    `bool("")` é False e `bool("smtp.exemplo.com")` é True: o dicionário escolhe a fábrica
    """
    fabricas = {
        True: lambda: EnviadorEmailSMTP(
            configuracao["EMAIL_SMTP_HOST"],
            int(configuracao["EMAIL_SMTP_PORTA"]),
            configuracao["EMAIL_SMTP_USUARIO"],
            configuracao["EMAIL_SMTP_SENHA"],
            configuracao["EMAIL_REMETENTE"],
            usar_tls=configuracao["EMAIL_SMTP_TLS"],
        ),
        False: EnviadorEmailNoTerminal,
    }
    return fabricas[bool(configuracao["EMAIL_SMTP_HOST"])]()