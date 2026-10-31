"""
app/models/senha.py

Senha já protegida (hash) e seu Null Object

Não guarda a senha real, apenas o hash
    Dá para transformar senha em hash, não hash em senha
    Para conferir o login, gera-se o hash da senha digitada e verifica com o hash guardado
    O Werkzeug (Flask) acrescenta um 'salt' aleatório: duas senhas iguais geram hashes diferentes

"""

from __future__ import annotations

# generate_password_hash(senha) -> devolve o hash (com salt) para guardar
# check_password_hash(hash, senha) -> True se a senha digitada corresponde ao hash
from werkzeug.security import check_password_hash, generate_password_hash

from app.validators.senha import ValidadorSenha


class Senha:
    """
    Objeto que representa a senha já protegida (hash). Quem tem uma Senha nunca tem acesso ao texto original
    """

    def __init__(self, hash_senha: str | None):
        """
        Guarda o hash
        """
        self._hash = hash_senha

    @classmethod
    def criar(cls, senha_plana: str) -> "Senha":
        """
        1) valida a força (levanta SenhaFracaError se for fraca); 2) gera o hash; 3) devolve o objeto
        """
        ValidadorSenha.validar(senha_plana)
        return cls(generate_password_hash(senha_plana))

    @classmethod
    def deHash(cls, hash_senha: str) -> "Senha":
        """
         Recria o objeto Senha a partir do hash salvo no banco (não recupera a senha original e não valida força: ela já foi validada no cadastro)
        """
        return cls(hash_senha)

    @property
    def hash(self) -> str | None:
        """
        Hash para gravar na coluna `senha` do banco
        """
        return self._hash

    def verificar(self, senha_plana: str) -> bool:
        """
        Compara a senha digitada com o hash guardado
        """
        return check_password_hash(self._hash, senha_plana or "")


class SenhaAusente(Senha):
    """
    Null Object: usuário sem senha cadastrada (coluna NULL)

    "NULL OBJECT": em vez de guardar None e perguntar `if senha is None` em todo lugar, guardamos um
    objeto que tem os mesmos métodos mas já se comporta como "sem senha". Assim o resto do código trata
    todo mundo igual, sem precisar de if
    """

    def __init__(self):
        """
        Sem hash nenhum

        `super().__init__(None)` chama o __init__ da classe mãe (Senha) passando None como hash
        """
        super().__init__(None)

    def verificar(self, senha_plana: str) -> bool:
        """
        Sem senha cadastrada, nenhuma tentativa de login é válida
        """
        return False
