"""
app / services / verificacao_email.py

VERIFICAÇÃO DE E-MAIL

Fluxo:
    1. A pessoa se cadastra com um e-mail
    2. o sistema envia a esse e-mail um LINK com um token assinado (válido por 24 h)
    3. ao abrir o link, o sistema confere o token e marca o e-mail como verificado
Provar que a pessoa tem acesso à caixa de entrada é o que o formato "letra@letra.letra" não consegue

O token NÃO fica guardado no banco: ele é assinado com a SECRET_KEY (ItsDangerous, o mesmo que a Autenticacao
usa). Dentro dele vão o id do usuário e o e-mail que está sendo confirmado. Se a pessoa trocar o e-mail depois,
o link antigo deixa de valer (o e-mail do token não bate mais com o do cadastro)
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.exceptions import ValidacaoError
from app.models.contratos import EnviadorEmail
from app.models.usuario import Usuario
from app.validators.campos import garantir


class RepositorioDeVerificacao(Protocol):
    """O que a VerificacaoEmail precisa do repositório de usuários (o RepositorioUsuarios cumpre)"""

    def buscarPorId(self, id_usuario: int) -> Usuario | None: ...

    def marcarEmailVerificado(self, usuario: Usuario) -> None: ...


class VerificacaoEmail:
    """Envia o link de confirmação e confirma o e-mail quando o link é aberto"""

    VALIDADE_SEGUNDOS = 24 * 60 * 60
    # O "salt" separa este token dos outros usos da mesma chave: um token de LOGIN não confirma e-mail
    # e um token de confirmação não serve de login
    SAL = "confeitaria-verificacao-email"
    ASSUNTO = "Confirme seu e-mail - Dolce Bea"

    def __init__(self, enviador: EnviadorEmail, repositorio: RepositorioDeVerificacao, chave_secreta: str):
        self._enviador = enviador
        self._repositorio = repositorio
        self._serializer = URLSafeTimedSerializer(chave_secreta, salt=self.SAL)

    def gerarToken(self, usuario: Usuario) -> str:
        """Token assinado com o id e o e-mail que será confirmado"""
        return self._serializer.dumps({"uid": usuario.id, "email": usuario.email})

    def enviarLink(self, usuario: Usuario, montarLink: Callable[[str], str]) -> None:
        """
        Manda o e-mail com o link de confirmação para o e-mail do usuário

        `montarLink` recebe o token e devolve o endereço completo (http://.../verificar-email/<token>).
        Quem sabe montar a URL é a rota (Flask): este serviço não conhece o Flask
        """
        garantir(usuario.email is not None, ValidacaoError("Cadastre um e-mail para poder confirmá-lo"))
        garantir(not usuario.email_verificado, ValidacaoError("Seu e-mail já está confirmado"))
        link = montarLink(self.gerarToken(usuario))
        self._enviador.enviar(usuario.email, self.ASSUNTO, self._texto(usuario, link))

    def confirmar(self, token: str) -> Usuario:
        """
        Confere o token e marca o e-mail como verificado. Devolve o usuário confirmado

        Erros (ValidacaoError, com mensagem para a tela): link vencido, link inválido ou adulterado,
        conta que não existe/está desativada, e-mail que mudou depois do envio
        """
        dados = self._lerToken(token)
        usuario = self._repositorio.buscarPorId(dados["uid"])
        garantir(
            usuario is not None and usuario.ativo and usuario.email == dados["email"],
            ValidacaoError("Este link não vale mais. Peça um novo link de confirmação"),
        )
        usuario.marcarEmailVerificado()
        self._repositorio.marcarEmailVerificado(usuario)
        return usuario

    def _lerToken(self, token: str) -> dict:
        """
        Confere assinatura e validade (24 h) do token. SignatureExpired é subclasse de BadSignature,
        por isso o except dela vem primeiro
        """
        try:
            return self._serializer.loads(token, max_age=self.VALIDADE_SEGUNDOS)
        except SignatureExpired as erro:
            raise ValidacaoError("Este link venceu. Peça um novo link de confirmação") from erro
        except BadSignature as erro:
            raise ValidacaoError("Link de confirmação inválido") from erro

    @staticmethod
    def _texto(usuario: Usuario, link: str) -> str:
        """Corpo do e-mail (texto simples, sem imagem, para não cair no spam)"""
        primeiro_nome = usuario.nome.split()[0]
        return (
            f"Olá, {primeiro_nome}!\n\n"
            "Para confirmar seu e-mail na Dolce Bea, abra o link abaixo (vale por 24 horas):\n\n"
            f"{link}\n\n"
            "Se você não criou uma conta, ignore esta mensagem: nada será feito.\n\n"
            "Este é um e-mail automático. Por favor, não responda.\n"
        )