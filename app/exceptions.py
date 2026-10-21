"""
app / exceptions.py

Exceções de domínio do sistema

Hierarquia:
    Exception
      └── ConfeitariaError                 (base: qualquer erro do nosso sistema)
            ├── ValidacaoError             (dado inválido)
            │     ├── SenhaFracaError      (senha fraca é um tipo de dado inválido)
            │     └── TransicaoStatusError (mudança de status proibida é um tipo de dado inválido)
            ├── EstoqueInsuficienteError   (falta de ingrediente, guarda a lista do que falta)
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

class EstoqueInsuficienteError(ConfeitariaError):
    """
    Lançada quando falta ingrediente para uma operação
    
    Guarda em 'faltas' o que falta, para poder montar a sugestão de compra (RF)
    Cada item da lista é um dicionário: {"ingrediente": nome, "unidade": unidade, "faltam": quantidade}
    """

    def __init__(self, faltas: list[dict]):
        # Guarda a lista no objeto, capturado como erro.faltas
        self.faltas = faltas
        # Monta o texto "Farinha (faltam 0.500 kg); Açúcar (faltam 2.000 kg)"
        # "; ".join(...) junta os pedaços; a expressão dentro do join gera um texto por item da lista
        detalhes = "; ".join(
            f"{falta['ingrediente']} (faltam {falta['faltam']} {falta['unidade']})" for falta in faltas
        )
        # super().__init__(texto) define a mensagem do erro (a que aparece ao imprimir a exceção)
        super().__init__(f"Estoque insuficiente: {detalhes}")
