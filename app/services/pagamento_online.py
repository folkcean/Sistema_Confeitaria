"""
app / services / pagamento_online.py

PAGAMENTO ONLINE POR PIX (sinal e restante)

O pedido tem duas parcelas: o SINAL e o RESTANTE.

O cliente abre a página "Pagar com Pix" de uma parcela e o sistema decide o que fazer, olhando a
cobrança que o pedido já tem guardada para ela (Pagamento.cobranca_sinal ou Pagamento.cobranca_restante):

    PAID significa que o cliente já pagou: registra o pagamento da parcela e salva
    PENDING significa que o Pix ainda vale: devolve o mesmo (a tela mostra o mesmo QR)
    o resto significa que não tem cobrança, ou ela venceu/foi cancelada: cria um Pix novo e guarda o id no pedido

Pagar o sinal NÃO confirma o pedido: quem confirma é a dona, no painel, porque a confirmação baixa o estoque
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from app.exceptions import ValidacaoError
from app.models.cobranca import Cobranca
from app.models.contratos import GatewayPagamento
from app.models.enums import FormaPagamento
from app.models.pedido import Pedido
from app.validators.campos import garantir


@dataclass(frozen=True)
class Parcela:
    """
    As peças de uma parcela paga por Pix. Cada campo é uma função que recebe o pedido

    `Pedido.exigirSinalPendente` (sem os parênteses e sem objeto) é o método "solto": chamar
    `Pedido.exigirSinalPendente(pedido)` é o mesmo que `pedido.exigirSinalPendente()`
    """
    nome: str  # vai na referência do Pix: pedido-<id>-<nome>
    descricao: str  # aparece no Pix: "<descricao> do pedido <id>"
    exigirPendente: Callable[[Pedido], None]  # recusa (ValidacaoError) se não dá para pagar agora
    valor: Callable[[Pedido], Decimal]  # quanto cobrar
    cobrancaGuardada: Callable[[Pedido], str | None]  # id do Pix já guardado no pedido (ou None)
    vincular: Callable[[Pedido, str], None]  # guarda o id do Pix novo no pedido
    registrar: Callable[[Pedido, FormaPagamento], None]  # marca a parcela como paga


SINAL = Parcela(
    nome="sinal",
    descricao="Sinal",
    exigirPendente=Pedido.exigirSinalPendente,
    valor=lambda pedido: pedido.valor_sinal,
    cobrancaGuardada=lambda pedido: pedido.pagamento.cobranca_sinal,
    vincular=Pedido.vincularCobrancaSinal,
    registrar=Pedido.registrarSinal,
)

RESTANTE = Parcela(
    nome="restante",
    descricao="Restante",
    exigirPendente=Pedido.exigirRestantePendente,
    valor=lambda pedido: pedido.valor_restante,
    cobrancaGuardada=lambda pedido: pedido.pagamento.cobranca_restante,
    vincular=Pedido.vincularCobrancaRestante,
    registrar=Pedido.registrarPagamentoRestante,
)

# Cobrança "vazia" para a parcela que ainda não tem Pix: o status dela não está na tabela de ações,
# então cai criar um Pix novo
_SEM_COBRANCA = Cobranca(id="", status="SEM_COBRANCA")


class ServicoPagamentoOnline:
    """Gera, reaproveita e confere o Pix de uma parcela do pedido (sinal ou restante)"""

    def __init__(self, gateway: GatewayPagamento, salvar_pedido: Callable[[Pedido], None] | None = None):
        """
        `salvar_pedido` grava o pedido no banco (a rota passa repo_pedidos.atualizar)
        Sem ele (testes de serviço), nada é gravado, igual ao PedidoService
        """
        self._gateway = gateway
        self._salvar_pedido = salvar_pedido or self._naoSalvar

    @staticmethod
    def _naoSalvar(pedido: Pedido) -> None:
        """Gravação vazia (sem banco). `pass` = não faz nada"""
        pass

    # Casos de uso
    def obterPix(self, pedido: Pedido, parcela: Parcela) -> Cobranca:
        """
        Devolve a cobrança da parcela. Se ela vier com `paga` verdadeiro, o pagamento acabou de ser registrado
        """
        parcela.exigirPendente(pedido)
        cobranca_guardada = self._consultarCobrancaGuardada(pedido, parcela)
        acoes_por_status = {
            "PAID": self._registrarPagamento,
            "PENDING": self._reaproveitarPix,
        }
        acao = acoes_por_status.get(cobranca_guardada.status, self._criarPixNovo)

        return acao(pedido, parcela, cobranca_guardada)

    def simularPix(self, pedido: Pedido, parcela: Parcela) -> Cobranca:

        parcela.exigirPendente(pedido)
        id_cobranca = parcela.cobrancaGuardada(pedido)
        garantir(id_cobranca, ValidacaoError("Gere o Pix antes de simular o pagamento"))
        return self._gateway.simularPagamento(id_cobranca)


    def _consultarCobrancaGuardada(self, pedido: Pedido, parcela: Parcela) -> Cobranca:
        """
        A cobrança que o pedido tem guardada para a parcela, com o status atual no gateway
        Sem id guardado, devolve _SEM_COBRANCA. `a and b or c`: só consulta o gateway quando existe id
        """
        id_cobranca = parcela.cobrancaGuardada(pedido)
        return (id_cobranca and self._gateway.consultar(id_cobranca)) or _SEM_COBRANCA

    def _registrarPagamento(self, pedido: Pedido, parcela: Parcela, cobranca: Cobranca) -> Cobranca:
        """O cliente pagou: registra a parcela como paga por Pix e grava"""
        parcela.registrar(pedido, FormaPagamento.PIX)
        self._salvar_pedido(pedido)
        return cobranca

    def _reaproveitarPix(self, pedido: Pedido, parcela: Parcela, cobranca: Cobranca) -> Cobranca:
        """O Pix ainda vale: devolve o mesmo, sem gravar nada"""
        return cobranca

    def _criarPixNovo(self, pedido: Pedido, parcela: Parcela, cobranca_antiga: Cobranca) -> Cobranca:
        """
        Cria o Pix com o valor da parcela e guarda o id no pedido
        A referência (externalId) repetida protege de duplicar: com um Pix pendente, a API devolve o mesmo
        """
        cobranca_nova = self._gateway.criarPix(
            parcela.valor(pedido),
            f"pedido-{pedido.id}-{parcela.nome}",
            f"{parcela.descricao} do pedido {pedido.id}",
        )
        parcela.vincular(pedido, cobranca_nova.id)
        self._salvar_pedido(pedido)
        return cobranca_nova
