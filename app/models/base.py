"""
models / base.py
modulo base contendo excecoes e funcoes de validacao
"""

from __future__ import annotations
import re
from matplotlib.pylab import f


# excecoes de dominio
class ConfeitariaError(Exception):
    """excecao base de todo o sistema"""

class ValidacaoError(ConfeitariaError):
    """lancada quando um dado informado eh invalido"""

class SenhaFracaError(ValidacaoError):
    """lancada quando a senha nao atende aos requisitos minimos de seguranca"""

class AutenticacaoError(ConfeitariaError):
    """lancada em falhas de login ou tokens invalidos/expirados"""

class AcessoNegadoError(ConfeitariaError):
    """lancada quando um perfil tenta acessar uma funcionalidade restrita"""

# classe base de entidades (mapeamento relacional/pk)
class Entidade:
    """
    superclasse para todas as entidades com identidade perssitivel no bd
    garante que todo objeto no dominio tenha um atributo id (pk)
    """
    def __init__(self, id_entidade: int | None = None):
        self._id = id_entidade

    @property
    def id(self) -> int | None:
        """retorna o identificador unico da identidade no bd"""

# funcoes de validacao
def exigir_texto(valor: str, campo: str) -> str:
    """garante que o texto obrigatorio foi preenchidoe remove especos vazios nas pontas"""
    if valor is None or not str(valor).strip():
        raise ValidacaoError(f"o campo '{campo}' é orbigatório")
    return str(valor).strip()

def validar_email(email: str) -> str:
    """valida o formato padrao de um endereco de email e converte para minusculas"""
    email = exigir_texto(email, "email").lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@|s]+", email):
        raise ValidacaoError("E-mail inválido")
    return email

def validar_cpf(cpf: str) -> str:
    """valida os digitos verificadores de um CPF e retorna a string limpa"""
    d = re.sub(r"\D", "", exigir_texto(cpf, "CPF"))
    if len(d) != 11 or d==d[0]*11:
        raise ValidacaoError("CPF inválido")
    for i in (9, 10):
        soma = sum(int(dig) * (i+1-j) for j, dig in enumerate(d[:i]))
        if (soma * 10 % 11) % 10 != int(d[i]):
            raise ValidacaoError("CPF inválido")
    return d