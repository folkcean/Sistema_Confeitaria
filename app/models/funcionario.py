"""
app / models / funcionario.py

Funcionário (tabela FUNCIONÁRIO)
"""

from __future__ import annotations

from datetime import date, datetime

from app.exceptions import ValidacaoError
from app.validators.campos import Validador, garantir

from .contratos import ClienteConsultavel, Estoque, PedidoAvancavel
from .enums import Perfil, StatusPedido
from .usuario import Usuario


class Funcionario(Usuario):
    """
    Usuário que atua na produção e no atendimento. Vê só os dados operacionais dos clientes
    """

    def __init__(
        self,
        nome: str,
        email: str | None,
        telefone: str,
        cpf: str | None,
        cargo: str,
        data_nascimento: date | datetime | str,
        data_contratacao: date | datetime | str | None = None,
        **kwargs,
    ):

        # data_nascimento é nula no DER, mas para funcionário o sistema exige (entrevista)
        # `**kwargs` recebe o restante dos parâmetros (senha, id_usuario, ativo...) e repassa à classe mãe
        # data_nascimento=data_nascimento: parâmetro com nome=valor
        super().__init__(
            nome, email, telefone, cpf, data_nascimento=data_nascimento, **kwargs
        )
        # Depois que a classe mãe validou, self.data_nascimento é None se veio vazio. None é falso => erro.
        garantir(
            self.data_nascimento,
            ValidacaoError("A data de nascimento é obrigatória para funcionários"),
        )
        self._cargo = Validador.texto(cargo, "cargo")
        # Sem data informada, considera contratado hoje.
        self._data_contratacao = Validador.data(
            data_contratacao or date.today(), "data de contratação"
        )

    # Contrato de Usuario
    @property
    def perfil(self) -> Perfil:
        """
        Este usuário é um funcionário
        """
        return Perfil.FUNCIONARIO

    @property
    def acessa_dados_sensiveis(self) -> bool:
        """
        Funcionário não vê CPF nem outros dados sensíveis
        """
        return False

    def consultarCliente(self, cliente: ClienteConsultavel) -> dict:
        """
        Funcionário recebe apenas a visão operacional do cliente
        """
        return cliente.dadosOperacionais()

    @property
    def cargo(self) -> str:
        return self._cargo

    @cargo.setter
    def cargo(self, valor: str) -> None:
        """
        Altera o cargo (obrigatório)
        """
        self._cargo = Validador.texto(valor, "cargo")

    @property
    def data_contratacao(self) -> date:
        return self._data_contratacao

    # Ações do dia a dia
    # Pedido e Estoque ainda serão implementados
    def atualizarStatusPedido(
        self, pedido: PedidoAvancavel, novo_status: StatusPedido
    ) -> None:
        """
        Avança o pedido na fila de produção. O pedido valida se a transição é permitida
        """
        pedido.avancarStatus(novo_status)

    def consultarEstoque(self, estoque: Estoque) -> list[dict]:
        """
        Consulta o resumo do estoque (somente leitura)
        """
        return estoque.resumo()
