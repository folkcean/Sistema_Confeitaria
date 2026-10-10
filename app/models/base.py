"""
models / base.py
Módulo base do sistema
Contém exceções de domínio, classe mãe das entidades e funções de validação utilizadas por usuario.py e produto.py
"""

from __future__ import annotations
# Expressões Regulares
import re
# Evitar erros de arredondamento
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
# Status do pedido
from enum import Enum
# Validar datas
from datetime import date, datetime


# EXCEÇÕES DE DOMÍNIO:
class ConfeitariaError(Exception):
    """Exceção base de todo o sistema"""

class ValidacaoError(ConfeitariaError):
    """Lançada quando um dado informado é inválido"""

class SenhaFracaError(ValidacaoError):
    """Lançada quando a senha não atende aos requisitos mínimos de segurança"""

class AutenticacaoError(ConfeitariaError):
    """Lançada em falhas de login ou tokens inválidos/expirados"""

class AcessoNegadoError(ConfeitariaError):
    """Lançada quando um perfil tenta acessar uma funcionalidade restrita"""

# STATUS DO PEDIDO
# Fluxo segundo a entrevista: Solicitação -> Orçamento -> Sinal de 50% -> Confirmado -> Em Produção
# -> Pronto -> Entregue/Pago -> Finalizado
# CANCELADO pode ocorrer depois de confirmado, exige motivo e não tem reembolso
class StatusPedido(Enum):
    SOLICITADO = "soliciatado"
    ORCAMENTO = "orcamento"
    CONFIRMADO = "confirmado"
    EM_PRODUCAO = "em_producao"
    PRONTO = "pronto"
    ENTREGUE = "entregue"
    FINALIZADO = "finalizado"
    CANCELADO = "cancelado"

# CLASSE BASE DAS ENTIDADES:
class Entidade:
    """
    Superclasse de todas as entidades com identidade persistível no banco de dados
    Garante que todo objeto tenha um id (pk do DER)
    """
    def __init__(self, id_entidade: int | None = None):
        # Atributo protegido: subclasses podem ler, mas código externo deve usar property id
        self._id = id_entidade

    @property
    def id(self) -> int | None:
        """retorna o identificador unico da identidade no bd"""
        return self._id

    def atribuirID(self, novo_id: int) -> None:
        """Usado logo após o INSERT, quando o banco gera a pk, depois de definido é imutável"""
        if self._id is not None:
            raise ValidacaoError("Esta entidade já possui um ID (não alterável)")
        self._id = novo_id

# FUNÇÔES DE VALIDAÇÂO:
def exigirTexto(valor: str, campo: str, max_len: int = 255) -> str:
    """Garante que o texto obrigatório foi preenchido, remove espaços vazios das pontas e respeita o tamanho máximo da coluna"""
    if valor is None or not str(valor).strip():
        raise ValidacaoError(f"o campo '{campo}' é obrigatório")
    texto = str(valor).strip()
    if len(texto) > max_len:
        raise ValidacaoError(f"O campo '{campo}' deve ter no máximo {max_len} caracteres")
    return texto

def textoOpcional(valor: str | None, campo: str, max_len: int = 255) -> str | None:
    """Para colunas nuláveis do DER
    Texto vazio vira None, equivalente ao NULL do banco"""
    if valor is not None or not str(valor).strip:
        return None
    texto = str(valor).strip()
    if len(texto) > max_len:
        raise ValidacaoError(f"O campo '{campo}' deve ter no máximo {max_len} caracteres")
    return texto

def validarEmail(email: str) -> str:
    """Valida o formato de um endereço de email e converte para minúsculas"""
    email = exigirTexto(email, "email").lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValidacaoError("E-mail inválido")
    return email

def validarTelefone(telefone: str) -> str:
    """Valida um número de telefone (fixo ou celular, com DDD)"""
    digitos = re.sub(r"\D", " ", exigirTexto(telefone, "telefone"))
    if len(digitos) not in (10, 11):
        raise ValidacaoError("Telefone inválido: informe DDD + número")
    return digitos

def validarCPF(cpf: str) -> str:
    """Valida os dígitps verificadores de um CPF e devolve apenas os dígitos"""
    d = re.sub(r"\D", "", exigirTexto(cpf, "CPF"))
    # Rejeita o tamanho errado e sequências repetidas (111.111.111-11)
    if len(d) != 11 or d==d[0]*11:
        raise ValidacaoError("CPF inválido")
    # Calcula o primeiro e o segundo dígito verificador
    for i in (9, 10):
        soma = sum(int(dig) * (i+1-j) for j, dig in enumerate(d[:i]))
        if (soma * 10 % 11) % 10 != int(d[i]):
            raise ValidacaoError("CPF inválido")
    return d

def validarData():
    """"""

def validarDinheiro():
    """"""

def validarPercentual():
    """"""

def exigirAdministrador():
    """"""