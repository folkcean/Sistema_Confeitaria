"""
app / services / autenticacao.py

Login de usuários e tokens de sessão

Fluxo: normaliza o e-mail -> confere se está bloqueado -> localiza o usuário -> confere senha e conta ativa
    -> (sucesso) emite um token  /  (falha) registra a falha e recusa

Login é feito só por e-mail
"""
from __future__ import annotations

from typing import Protocol

# Biblioteca ItsDangerous (Flask): gera e valida tokens assinados com validade
# URLSafeTimedSerializer -> cria/lê o token, BadSignature -> assinatura inválida, SignatureExpired -> venceu
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from app.exceptions import AutenticacaoError, ValidacaoError
from app.models.usuario import Usuario
from app.validators.campos import garantir
from app.services.controle_login import ControleLogin


class RepositorioUsuarios(Protocol):
    """
    Contrato que o repositório (camada de banco) precisa cumprir
    """

    def buscarPorEmail(self, email: str) -> Usuario | None:
        """Devolve o usuário com esse e-mail (já em minúsculas) ou None se não existir"""
        ...


class UsuarioInexistente:
    """
    Null Object: representa 'nenhum usuário com esse e-mail'
    """

    ativo = False

    def __init__(self, hash_isca: str):
        """Recebe um hash qualquer só para gastar tempo de processamento"""
        self._hash_isca = hash_isca

    def verificarSenha(self, senha_plana: str) -> bool:
        """Confere contra o hash isca (descarta o resultado) e reprova"""
        check_password_hash(self._hash_isca, senha_plana or "")
        return False


class Autenticacao:
    """
    Cuida do login, do bloqueio por tentativas e dos tokens de sessão
    """

    MENSAGEM_FALHA = "E-mail ou senha incorretos."
    VALIDADE_TOKEN_SEGUNDOS = 8 * 3600  # 8 horas

    def __init__(self, repositorio: RepositorioUsuarios, chave_secreta: str, controle: ControleLogin | None = None):
        """A chave secreta vem do .env e precisa ter ao menos 16 caracteres"""
        garantir(len(chave_secreta or "") >= 16, ValidacaoError("A chave secreta deve ter ao menos 16 caracteres"))
        self._repositorio = repositorio
        self._controle = controle or ControleLogin()
        # O "salt" separa o uso desta chave de outros usos da mesma chave na aplicação: um token gerado para outra finalidade não vale aqui
        self._serializer = URLSafeTimedSerializer(chave_secreta, salt="confeitaria-auth")
        # Hash qualquer, gerado uma vez, que serve de isca para o UsuarioInexistente
        self._hash_isca = generate_password_hash("Isca contra enumeração de usuários")

    def autenticar(self, email: str, senha: str) -> Usuario:
        """Valida as credenciais. Devolve o usuário ou lança AutenticacaoError (mensagem genérica de propósito)"""
        chave = (email or "").strip().lower()
        # 1) Se estiver bloqueado, recusa sem sequer conferir a senha
        self._controle.exigirLiberado(chave)
        # 2) `or` usa o Null Object quando o repositório devolve None
        usuario = self._repositorio.buscarPorEmail(chave) or UsuarioInexistente(self._hash_isca)
        # 3) Senha correta E conta ativa. A mensagem é a mesma para qualquer motivo de falha
        try:
            garantir(
                usuario.verificarSenha(senha) and usuario.ativo,
                AutenticacaoError(self.MENSAGEM_FALHA),
            )
        except AutenticacaoError:
            self._controle.registrarFalha(chave)
            raise
        # 4) Sucesso: zera o histórico de falhas
        self._controle.limpar(chave)
        return usuario

    def gerarToken(self, usuario: Usuario) -> str:
        """Token assinado com o id e o perfil do usuário"""
        return self._serializer.dumps({"uid": usuario.id, "perfil": usuario.perfil.value})

    def validarToken(self, token: str) -> dict:
        """Confere assinatura e validade (8h). SignatureExpired é subclasse de BadSignature,
        por isso precisa vir primeiro"""
        try:
            return self._serializer.loads(token, max_age=self.VALIDADE_TOKEN_SEGUNDOS)
        except SignatureExpired as erro:
            raise AutenticacaoError("Sessão expirada. Faça login novamente.") from erro
        except BadSignature as erro:
            raise AutenticacaoError("Sessão inválida.") from erro