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
            │     └── PedidoSemEstoque     (Falta de ingredientes)
            ├── AutenticacaoError          (falha de login / token)
            ├── EnvioEmailError            (falha na verificação do email)
            ├── GatewayPagamentoError      (o gateway de pagamento recusou ou não respondeu)
            ├── GatewayIAError             (a API de IA recusou, não respondeu ou respondeu fora do formato)
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


class GatewayPagamentoError(ConfeitariaError):
    """Lançada quando o gateway de pagamento recusa o pedido ou não responde (chave errada, sem internet etc.)"""

class EnvioEmailError(ConfeitariaError):
    """Não foi possível enviar um e-mail (servidor de e-mail fora do ar, senha errada, sem internet...)"""

class GatewayIAError(ConfeitariaError):
    """Lançada quando a API de IA recusa, não responde ou devolve uma resposta cortada ou fora do formato"""


class AcessoNegadoError(ConfeitariaError):
    """Lançada quando um perfil tenta acessar uma funcionalidade restrita"""


class EstoqueInsuficienteError(ConfeitariaError):
    """
    Lançada quando falta insumo para uma operação
    
    Guarda em 'faltas' o que falta, para poder montar a sugestão de compra (RF)
    Cada item da lista é um dicionário: {"insumo": nome, "unidade": unidade, "faltam": quantidade}
    """

    def __init__(self, faltas: list[dict]):
        # Guarda a lista no objeto, capturado como erro.faltas
        self.faltas = faltas
        # Monta o texto "Farinha (faltam 0.500 kg); Açúcar (faltam 2.000 kg)"
        # "; ".join(...) junta os pedaços; a expressão dentro do join gera um texto por item da lista
        detalhes = "; ".join(
            f"{falta['insumo']} (faltam {falta['faltam']} {falta['unidade']})" for falta in faltas
        )
        # super().__init__(texto) define a mensagem do erro (a que aparece ao imprimir a exceção)
        super().__init__(f"Estoque insuficiente: {detalhes}")


class PedidoSemEstoqueError(EstoqueInsuficienteError):
    """
    Lançada quando um pedido não pode ser confirmado por falta de insumos

    É um tipo de EstoqueInsuficienteError (herança): `erro.faltas` continua com a lista do que falta
    Só muda a mensagem, que explica o que aconteceu e o que fazer
    """

    def __init__(self, faltas: list[dict]):
        super().__init__(faltas)  # A classe mãe guarda `faltas` e monta a mensagem padrão
        detalhes = "; ".join(
            f"{falta['insumo']} (faltam {falta['faltam']} {falta['unidade']})" for falta in faltas
        )
        # Troca a mensagem
        self.args = (f"Não foi possível confirmar o pedido por falta de insumos: {detalhes}. "
                     f"Reponha o estoque e tente confirmar novamente",)
