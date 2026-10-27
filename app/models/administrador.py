"""
app / models / administrador.py

Administrador (tabela ADMINISTRADOR)
"""

from __future__ import annotations

from app.exceptions import AcessoNegadoError
from app.validators.campos import Validador, garantir

from .contratos import ClienteConsultavel, Recomendador
from .enums import Perfil
from .usuario import Usuario
from .estoque import Estoque
from .insumo import Insumo
from .movimentacao_estoque import MovimentacaoEstoque


class Administrador(Usuario):
    """
    Único perfil que acessa dados sensíveis e pode ajustar estoque manualmente
    """

    def __init__(
        self,
        nome: str,
        email: str | None,
        telefone: str,
        cpf: str | None,
        nivel_privilegio: str = "total",
        acesso_financeiro: bool = False,
        **kwargs,
    ):

        # acesso_financeiro nasce False (default do DER): quem precisa de relatórios recebe a permissão de forma explícita
        # `**kwargs` recebe o restante dos parâmetros (senha, id_usuario...) e repassa à classe mãe.
        super().__init__(nome, email, telefone, cpf, **kwargs)
        self._nivel_privilegio = Validador.texto(
            nivel_privilegio, "nível de privilégio"
        )
        self._acesso_financeiro = bool(acesso_financeiro)

    # Contrato de Usuario
    @property
    def perfil(self) -> Perfil:
        """
        Este usuário é um administrador
        """
        return Perfil.ADMINISTRADOR

    @property
    def acessa_dados_sensiveis(self) -> bool:
        """
        Administrador é o único perfil com acesso a dados sensíveis
        """
        return True

    def consultarCliente(self, cliente: ClienteConsultavel) -> dict:
        """
        Administrador recebe a visão completa do cliente
        """
        return cliente.dadosCompletos(self)

    @property
    def nivel_privilegio(self) -> str:
        return self._nivel_privilegio

    @property
    def acesso_financeiro(self) -> bool:
        return self._acesso_financeiro

    # Ações exclusivas
    def ajustarEstoque(self, estoque: Estoque, ingrediente, nova_quantidade: float, motivo: str) -> None:
        """
        Ajusta manualmente a quantidade de um ingrediente e devolve a movimentação registrada (o motivo fica registrado na movimentação)
        """
        return estoque.ajustarManual(ingrediente, nova_quantidade, motivo)

    def desfazerAjusteEstoque(self, estoque: Estoque, movimentacao: MovimentacaoEstoque) -> MovimentacaoEstoque:
        """
        Desfaz um ajuste manual registrando um ajuste contrário
        """
        return estoque.desfazerAjuste(movimentacao)

    def consultarSugestaoDeCompras(self, estoque: Estoque) -> list[dict]:
        """
        Lista de copra sugerida: insumos que atingiram o estoque mínimo e o quanto falta para voltar a ele
        """
        return estoque.sugerirCompras()

    def consultarCpfCliente(self, cliente) -> str | None:
        """
        Lê o CPF de um cliente (obterCpf aceita porque quem pede é administrador)
        """
        return cliente.obterCpf(self)

    def gerarRelatorioReposicao(self, recomendador: Recomendador, estoque: Estoque, historico) -> list[dict]:
        """
        Aciona o módulo de recomendação de compras. Exige a permissão de acesso financeiro
        """
        garantir(
            self._acesso_financeiro,
            AcessoNegadoError("Este administrador não possui acesso a relatórios financeiros")
        )
        return recomendador.recomendar(estoque, historico)
