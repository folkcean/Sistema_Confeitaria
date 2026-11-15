"""
app / services / pedido_service.py

SERVIÇO DE PEDIDOS (s5) - orquestra o fluxo:

    carrinho -> criar pedido -> orçamento -> sinal pago -> CONFIRMAR (baixa o estoque) -> produção -> entrega
    -> restante pago -> finalizar            (ou CANCELAR com motivo)

O que cada parte faz:
    Carrinho         guarda as linhas escolhidas pelo cliente (ainda não é um pedido);
    CalculadoraPreco calcula preço, custo e taxa de entrega (s4);
    BaixaEstoque     desconta os insumos na confirmação (tudo ou nada);
    Pedido           guarda as regras do próprio pedido (fluxo de status, prazo, imutabilidade).
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from contextlib import nullcontext
from dataclasses import dataclass, field
from datetime import datetime

from app.exceptions import ValidacaoError
from app.models.cliente import Cliente
from app.models.endereco import Endereco
from app.models.enums import FormaPagamento, StatusPedido, TipoEntrega
from app.models.movimentacao_estoque import MovimentacaoEstoque
from app.models.opcao_personalizacao import OpcaoPersonalizacao
from app.models.pedido import Pedido
from app.models.produto import Produto
from app.services.baixa_estoque import BaixaEstoque
from app.services.precificacao import CalculadoraPreco
from app.validators.campos import Validador, garantir


@dataclass
class LinhaCarrinho:
    """
    Uma linha do carrinho: produto, quantidade e escolhas. (@dataclass cria o __init__ sozinho.)
    """
    produto: Produto
    quantidade: int
    escolhas: list[tuple[OpcaoPersonalizacao, int]] = field(default_factory=list)
    personalizacao: str = ""
    observacoes: str = ""


class Carrinho:
    """
    Carrinho do cliente: lista de linhas ainda sem preço fixado
    Vira Pedido em PedidoService.criarPedido
    """

    def __init__(self):
        self._linhas: list[LinhaCarrinho] = []

    @property
    def linhas(self) -> tuple[LinhaCarrinho, ...]:
        """
        Cópia imutável das linhas (quem lê não consegue alterar a lista interna)
        """
        return tuple(self._linhas)

    @property
    def vazio(self) -> bool:
        """
        True quando não há nenhuma linha. Lista vazia vale False, então `not lista` é True
        """
        return not self._linhas

    def adicionar(self, produto: Produto, quantidade: int,
                  escolhas: Iterable[tuple[OpcaoPersonalizacao, int]] = (),
                  personalizacao: str = "", observacoes: str = "") -> LinhaCarrinho:
        """
        Coloca um produto no carrinho. Só produtos ATIVOS e com quantidade inteira >= 1
        """
        garantir(
            produto.ativo, 
            ValidacaoError(f"O produto {produto.nome!r} não está disponível")
        )
        linha = LinhaCarrinho(produto, Validador.inteiroPositivo(quantidade, "quantidade"),
                              list(escolhas), personalizacao, observacoes)
        self._linhas.append(linha)
        return linha

    def remover(self, linha: LinhaCarrinho) -> None:
        """
        Tira uma linha do carrinho
        """
        garantir(
            linha in self._linhas, 
            ValidacaoError("Esta linha não está no carrinho")
        )
        self._linhas.remove(linha)

    def esvaziar(self) -> None:
        """
        Remove todas as linhas (depois de criar o pedido)
        """
        self._linhas.clear()


class PedidoService:
    """
    Casos de uso de pedido
    Cada método devolve o pedido já alterado e o salva (se houver gravação)
    """

    # Status que NÃO podem ser pedidos por avancar(): têm método próprio, com regras extras.
    _STATUS_COM_METODO_PROPRIO = {StatusPedido.CONFIRMADO, StatusPedido.CANCELADO}

    def __init__(self, calculadora: CalculadoraPreco, baixa: BaixaEstoque,
                 salvar_pedido: Callable[[Pedido], None] | None = None,
                 transacao: Callable[[], object] | None = None):
        self._calculadora = calculadora
        self._baixa = baixa
        # `a or b`: usa a função informada; se for None, usa a "vazia" (não grava / with sem efeito).
        self._salvar_pedido = salvar_pedido or self._naoSalvar
        self._transacao = transacao or nullcontext

    @staticmethod
    def _naoSalvar(pedido: Pedido) -> None:
        """
        Gravação vazia (sem banco). `pass` = não faz nada
        """
        pass

    # CRIAÇÃO
    def criarPedido(self, cliente: Cliente, carrinho: Carrinho, tipo_entrega: TipoEntrega,
                    data_entrega_ou_retirada: datetime, endereco: Endereco | None = None,
                    distancia_km=None, nome_recebedor: str = "", observacoes: str = "",
                    data_criacao: datetime | None = None) -> Pedido:
        """
        Transforma o carrinho em Pedido (status Solicitado), com preços e taxa de entrega fixados agora

        LÓGICA: carrinho não pode estar vazio -> cria o pedido -> converte cada linha em item (preço e custo
        são fixados neste momento) -> calcula a taxa pela distância -> confere o prazo -> salva
        Se algo falhar, nenhum pedido é devolvido nem salvo
        """
        garantir(
            not carrinho.vazio, 
            ValidacaoError("O carrinho está vazio")
        )
        pedido = Pedido(cliente, tipo_entrega, data_entrega_ou_retirada, endereco=endereco,
                        nome_recebedor=nome_recebedor, observacoes=observacoes, data_criacao=data_criacao)
        for linha in carrinho.linhas:
            item = self._calculadora.montarItem(linha.produto, linha.quantidade, linha.escolhas,
                                                linha.personalizacao, linha.observacoes)
            pedido.adicionarItem(item)
        pedido.definirTaxaEntrega(self._calculadora.taxaEntrega(tipo_entrega, distancia_km))
        pedido.validarPrazo()
        self._salvar_pedido(pedido)
        carrinho.esvaziar()
        return pedido

    # VALORES
    @staticmethod
    def total(pedido: Pedido):
        """
        Total do pedido (itens + taxa de entrega)
        """
        return pedido.valor_total

    @staticmethod
    def valorRestante(pedido: Pedido):
        """
        Valor do restante (total - sinal de 50%)
        """
        return pedido.valor_restante

    # FLUXO
    def enviarOrcamento(self, pedido: Pedido) -> Pedido:
        """
        Solicitado -> Orçamento (confere itens e prazo)
        """
        pedido.avancarStatus(StatusPedido.ORCAMENTO)
        self._salvar_pedido(pedido)
        return pedido

    def registrarSinal(self, pedido: Pedido, forma: FormaPagamento) -> Pedido:
        """
        Registra o sinal de 50% (só em orçamento)
        """
        pedido.registrarSinal(forma)
        self._salvar_pedido(pedido)
        return pedido

    def registrarPagamentoRestante(self, pedido: Pedido, forma: FormaPagamento) -> Pedido:
        """
        Registra o pagamento do restante (só depois de confirmado)
        """
        pedido.registrarPagamentoRestante(forma)
        self._salvar_pedido(pedido)
        return pedido

    def confirmar(self, pedido: Pedido) -> list[MovimentacaoEstoque]:
        """
        Confirma o pedido e BAIXA o estoque. Devolve as movimentações (para o alerta de estoque)

        ORDEM IMPORTANTE (evita descontar insumo de pedido que não pode ser confirmado):
        1) pedido.exigirConfirmavel(): fluxo permite e sinal pago (não altera nada)
        2) dentro de UMA transação: baixa o estoque (recusa com PedidoSemEstoqueError se faltar insumo) depois muda o status para Confirmado e salva o pedido
        Se qualquer passo falhar dentro do `with`, o banco deve desfazer tudo
        """
        pedido.exigirConfirmavel()
        with self._transacao():
            movimentacoes = self._baixa.executar(pedido)
            pedido.avancarStatus(StatusPedido.CONFIRMADO)
            self._salvar_pedido(pedido)
        return movimentacoes

    def cancelar(self, pedido: Pedido, motivo: str) -> Pedido:
        """
        Cancela com motivo obrigatório (só de Confirmado, Em produção ou Pronto)

        Atualmente o cancelamento NÃO devolve insumos
        """
        pedido.avancarStatus(StatusPedido.CANCELADO, motivo)
        self._salvar_pedido(pedido)
        return pedido

    def avancar(self, pedido: Pedido, novo_status: StatusPedido) -> Pedido:
        """
        Avança o status (Em produção, Pronto, Entregue, Finalizar...)
        Para Confirmado e Cancelado usa os métodos próprios
        """
        destino = Validador.opcaoDe(StatusPedido, novo_status, "status do pedido")
        garantir(
            destino not in self._STATUS_COM_METODO_PROPRIO,
            ValidacaoError("Para confirmar use confirmar(); para cancelar use cancelar(pedido, motivo)")
        )
        pedido.avancarStatus(destino)
        self._salvar_pedido(pedido)
        return pedido