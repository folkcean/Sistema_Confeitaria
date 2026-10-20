"""
app / exceptions.py

Exceções de domínio do sistema

Hierarquia:
    Exception
      └── ConfeitariaError                 (base: qualquer erro do nosso sistema)
            ├── ValidacaoError             (dado inválido)
            │     ├── SenhaFracaError      (senha fraca é um tipo de dado inválido)
            │     └── TransicaoStatusError (mudança de status proibida é um tipo de dado inválido)
            ├── AutenticacaoError          (falha de login / token)
            └── AcessoNegadoError          (perfil sem permissão)
"""


class ConfeitariaError(Exception):
    """Exceção base de todo o sistema"""


class ValidacaoError(ConfeitariaError):
    """Lançada quando um dado informado é inválido"""


class SenhaFracaError(ValidacaoError):
    """Lançada quando a senha não atende aos requisitos mínimos de segurança"""


class TransicaoStatusError(ValidacaoError):
    """Lançada quando o pedido tenta mudar para um status que o fluxo não permite"""


class AutenticacaoError(ConfeitariaError):
    """Lançada em falhas de login ou tokens inválidos/expirados"""


class AcessoNegadoError(ConfeitariaError):
    """Lançada quando um perfil tenta acessar uma funcionalidade restrita"""
