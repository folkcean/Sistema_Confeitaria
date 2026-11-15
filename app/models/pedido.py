"""
app/models/pedido.py

Módulo de pedidos: Pedido (tabela PEDIDO), ItemPedido (ITEM_PEDIDO), ItemPedidoOpcao (ITEM_PEDIDO_OPCAO) e Pagamento

Pagamento não é tabela no DER: o pagamento vive em colunas do PEDIDO (status_pagamento, forma_pagamento_sinal,
forma_pagamento_restante). Por isso é um OBJETO-VALOR: classe sem id, que o Pedido carrega dentro de si

REGRAS DE NEGÓCIO (entrevista seções 4 e 5, e relatório 2.3) GARANTIDAS AQUI:
    - o pedido só vira "Confirmado" depois que o SINAL de 50% está pago;
    - depois de confirmado, o pedido (e seus itens) NÃO pode mais ser alterado;
    - cancelar só é possível depois de confirmado, exige MOTIVO e NÃO devolve o sinal;
    - respeita o prazo mínimo (antecedencia_horas do produto) entre a criação e a entrega/retirada;
    - só vira "Finalizado" com o pagamento integral (restante pago)
O autômato dos status (quais mudanças são permitidas) está em enums.py (StatusPedido._TRANSICOES); este arquivo o usa

A baixa de estoque na confirmação NÃO é feita aqui: será do serviço de pedidos (semana 5), que chama
Estoque.consumir() com os insumos de Produto.necessidades().
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from app.exceptions import ValidacaoError
from app.validators.campos import Validador, garantir
from .base import Entidade
from .enums import FormaPagamento, StatusPagamento, StatusPedido, TipoEntrega

if TYPE_CHECKING:
    from .cliente import Cliente
    from .endereco import Endereco
    from .opcao_personalizacao import OpcaoPersonalizacao
    from .produto import Produto

# TABELAS DE REGRAS (no lugar de vários if/elif)
# Status em que o pedido ainda pode ser montado/alterado. Depois de Confirmado, nada muda.
_STATUS_EDITAVEIS = frozenset({StatusPedido.SOLICITADO, StatusPedido.ORCAMENTO})
# Status em que o restante (os outros 50%) já pode ser pago.
_STATUS_QUITAVEIS = frozenset({StatusPedido.CONFIRMADO, StatusPedido.EM_PRODUCAO,
                               StatusPedido.PRONTO, StatusPedido.ENTREGUE})
# Cada tipo de entrega exige endereço? (entrega: sim; retirada: não)
_EXIGE_ENDERECO = {TipoEntrega.ENTREGA: True, TipoEntrega.RETIRADA: False}
# Zero em dinheiro (2 casas), reaproveitado nas somas.
_ZERO = Decimal("0.00")


class Pagamento:
    """
    Objeto-valor: situação do pagamento de UM pedido (sinal de 50% + restante)

    Não guarda valores em R$: quem sabe o total é o Pedido, e passa o total para os métodos de cálculo.
    Fluxo: AGUARDANDO_SINAL -> SINAL_PAGO -> PAGO. (A entrevista diz que "não pago" não existe, pois há sinal; o status inicial do DER é 'aguardando_sinal')
    """

    # Percentual do sinal (entrevista: "metade do valor")
    _FRACAO_SINAL = Decimal("0.5")
    _CENTAVOS = Decimal("0.01")

    def __init__(self,
                 status: StatusPagamento = StatusPagamento.AGUARDANDO_SINAL,
                 forma_sinal: FormaPagamento | None = None,
                 forma_restante: FormaPagamento | None = None):
        """
        Aceita os Enums ou os textos vindos do banco (ex.: 'sinal_pago')
        As formas são anuláveis no DER
        """
        self._status = Validador.opcaoDe(StatusPagamento, status, "status do pagamento")
        self._forma_sinal = self._formaOpcional(forma_sinal, "forma de pagamento do sinal")
        self._forma_restante = self._formaOpcional(forma_restante, "forma de pagamento do restante")

    @staticmethod
    def _formaOpcional(forma, campo: str) -> FormaPagamento | None:
        """
        None continua None; qualquer outro valor precisa ser uma FormaPagamento válida

        `lambda v, c: ...` é uma função de uma linha, sem nome. Aqui ela adapta Validador.opcaoDe
        (que pede o Enum como 1º parâmetro) ao formato que opcionalSeInformado espera (valor primeiro)
        """
        return Validador.opcionalSeInformado(
            lambda valor, nome_campo: Validador.opcaoDe(FormaPagamento, valor, nome_campo), forma, campo
        )

    @property
    def status(self) -> StatusPagamento: return self._status

    @property
    def forma_sinal(self) -> FormaPagamento | None: return self._forma_sinal

    @property
    def forma_restante(self) -> FormaPagamento | None: return self._forma_restante

    @property
    def sinal_pago(self) -> bool:
        """
        True quando o sinal já foi pago (inclusive quando já está tudo pago)
        """
        return self._status in {StatusPagamento.SINAL_PAGO, StatusPagamento.PAGO}

    @property
    def quitado(self) -> bool:
        """
        True quando o valor integral foi pago (entrevista)
        """
        return self._status is StatusPagamento.PAGO

    # Cálculos
    def sinal(self, valor_total: Decimal) -> Decimal:
        """
        Valor do sinal: 50% do total, em centavos (arredondamento padrão)
        """
        return (valor_total * self._FRACAO_SINAL).quantize(self._CENTAVOS, rounding=ROUND_HALF_UP)

    def restante(self, valor_total: Decimal) -> Decimal:
        """
        O que sobra depois do sinal. Calculado como total - sinal, assim as duas partes SEMPRE somam o total (evita sobrar/faltar um centavo por arredondamento)
        """
        return valor_total - self.sinal(valor_total)

    def valorEmAberto(self, valor_total: Decimal) -> Decimal:
        """
        Quanto ainda falta pagar, conforme o status

        TABELA: cada status aponta para uma função que calcula o valor. O dicionário escolhe o caminho,
        no lugar de um if/elif por status. As funções só rodam quando chamadas com `()` no final
        """
        em_aberto = {
            StatusPagamento.AGUARDANDO_SINAL: lambda: valor_total,
            StatusPagamento.SINAL_PAGO: lambda: self.restante(valor_total),
            StatusPagamento.PAGO: lambda: _ZERO,
        }
        return em_aberto[self._status]()

    # Registro dos pagamentos
    def registrarSinal(self, forma: FormaPagamento) -> None:
        """
        Marca o sinal como pago
        Só vale se ainda estava aguardando o sinal
        """
        forma_valida = Validador.opcaoDe(FormaPagamento, forma, "forma de pagamento do sinal")
        garantir(
            self._status is StatusPagamento.AGUARDANDO_SINAL,
            ValidacaoError("O sinal deste pedido já foi registrado")
        )
        self._forma_sinal = forma_valida
        self._status = StatusPagamento.SINAL_PAGO

    def registrarRestante(self, forma: FormaPagamento) -> None:
        """
        Marca o restante como pago
        Só vale depois do sinal e antes da quitação"""
        forma_valida = Validador.opcaoDe(FormaPagamento, forma, "forma de pagamento do restante")
        garantir(
            self._status is StatusPagamento.SINAL_PAGO,
            ValidacaoError("O restante só pode ser pago depois do sinal e uma única vez")
        )
        self._forma_restante = forma_valida
        self._status = StatusPagamento.PAGO

    def __repr__(self) -> str:
        """
        Texto exibido ao imprimir o objeto
        """
        return f"<Pagamento {self._status.value}>"


class ItemPedidoOpcao:
    """
    Uma opção de personalização escolhida em um item (tabela ITEM_PEDIDO_OPCAO, chave composta, sem id próprio)

    DER: ITEM_PEDIDOID, OPCAO_PERSONALIZACAOID, quantidade (padrão 1), custo_cobrado numeric(10,2)

    `custo_cobrado` é o valor de UMA unidade da opção, FIXADO no momento da escolha: se a dona mudar o preço da
    opção depois, os pedidos antigos continuam com o valor que foi cobrado
    Exemplo (entrevista 5.4): brigadeiro no bolo, R$ 3,00 cada; 4 brigadeiros -> subtotal R$ 12,00
    """

    def __init__(self,
                 opcao: OpcaoPersonalizacao,
                 quantidade: int = 1,
                 custo_cobrado=None):
        """
        Sem `custo_cobrado`, copia o custo atual da opção (fixa o preço). Ao recarregar do banco, passe o gravado
        """
        self._opcao = opcao
        self._quantidade = Validador.inteiroPositivo(quantidade, "quantidade da opção")
        # Tabela no lugar de if/else: a chave (custo_cobrado is None) escolhe a função que será executada
        origens = {
            True: lambda: opcao.custo_adicional,
            False: lambda: Validador.dinheiro(custo_cobrado, "custo cobrado")
        }
        self._custo_cobrado = origens[custo_cobrado is None]()

    @property
    def opcao(self) -> OpcaoPersonalizacao: return self._opcao

    @property
    def quantidade(self) -> int: return self._quantidade

    @property
    def custo_cobrado(self) -> Decimal: return self._custo_cobrado

    @property
    def subtotal(self) -> Decimal:
        """
        Custo cobrado x quantidade
        """
        return self._custo_cobrado * self._quantidade

    def __repr__(self) -> str:
        """
        Texto exibido ao imprimir o objeto 
        """
        return f"<ItemPedidoOpcao {self._quantidade} x {self._opcao.nome!r} R$ {self._custo_cobrado}>"


class ItemPedido(Entidade):
    """Uma linha do pedido: um produto, a quantidade e as personalizações escolhidas.

    DER: id_item_pedido, PRODUTOID_produto, PEDIDOID_pedido, quantidade, preco_unitario, personalizacao (nulo),
    custo_personalizacao (padrão 0), desconto (padrão 0), observacoes (nulo), custo_unitario

    `preco_unitario` e `custo_unitario` são FIXADOS aqui (cópia do cálculo no momento do pedido): o histórico não muda se o produto mudar de preço depois
    `custo_personalizacao` é o total das opções da LINHA inteira (não por unidade)
    """

    def __init__(self,
                 produto: Produto,
                 quantidade: int,
                 preco_unitario,
                 custo_unitario,
                 personalizacao: str = "",
                 desconto=0, observacoes: str = "",
                 id_item_pedido: int | None = None):
        """Valida tudo na criação. As opções são acrescentadas depois, por adicionarOpcao()"""
        super().__init__(id_item_pedido)
        self._produto = produto
        self._quantidade = Validador.inteiroPositivo(quantidade, "quantidade")
        self._preco_unitario = Validador.dinheiro(preco_unitario, "preço unitário")
        self._custo_unitario = Validador.dinheiro(custo_unitario, "custo unitário")
        self._personalizacao = Validador.textoOpcional(personalizacao, "personalização")
        self._desconto = Validador.dinheiro(desconto, "desconto")
        self._observacoes = Validador.textoOpcional(observacoes, "observações")
        garantir(
            self._desconto <= self.subtotal_bruto,
            ValidacaoError("O desconto não pode ser maior que o valor do item"),
        )
        self._opcoes: list[ItemPedidoOpcao] = []
        # Pedido dono (None até o Pedido.adicionarItem). `_travado` = pedido confirmado, nada mais muda.
        self._pedido: Pedido | None = None
        self._travado = False

    @property
    def produto(self) -> Produto: return self._produto

    @property
    def quantidade(self) -> int: return self._quantidade

    @property
    def preco_unitario(self) -> Decimal: return self._preco_unitario

    @property
    def custo_unitario(self) -> Decimal: return self._custo_unitario

    @property
    def personalizacao(self) -> str | None: return self._personalizacao

    @property
    def desconto(self) -> Decimal: return self._desconto

    @property
    def observacoes(self) -> str | None: return self._observacoes

    @property
    def pedido(self) -> Pedido | None: return self._pedido

    @property
    def produto_id(self) -> int | None:
        """Valor da FK PRODUTOID_produto"""
        return self._produto.id

    @property
    def pedido_id(self) -> int | None:
        """Valor da FK PEDIDOID_pedido (None se ainda não tem pedido ou o pedido não foi gravado)"""
        return self._pedido and self._pedido.id

    @property
    def opcoes(self) -> tuple[ItemPedidoOpcao, ...]:
        """Cópia imutável das opções escolhidas. Para acrescentar, use adicionarOpcao()"""
        return tuple(self._opcoes)

    # Valores
    @property
    def subtotal_bruto(self) -> Decimal:
        """Preço unitário x quantidade (sem personalização e sem desconto)"""
        return self._preco_unitario * self._quantidade

    @property
    def custo_personalizacao(self) -> Decimal:
        """Soma dos subtotais das opções. `sum(itens, inicio)` soma começando de `inicio` (aqui, zero em dinheiro)"""
        return sum((escolha.subtotal for escolha in self._opcoes), _ZERO)

    @property
    def subtotal(self) -> Decimal:
        """Valor da linha = bruto + personalização - desconto"""
        return self.subtotal_bruto + self.custo_personalizacao - self._desconto

    @property
    def custo_total(self) -> Decimal:
        """Custo de produção da linha (custo unitário x quantidade), base para o lucro"""
        return self._custo_unitario * self._quantidade

    # Personalização
    def adicionarOpcao(self, opcao: OpcaoPersonalizacao, quantidade: int = 1) -> ItemPedidoOpcao:
        """
        Escolhe uma opção de personalização para este item

        Confere: item não travado; a opção é DESTE produto; está ativa; ainda não foi escolhida neste item
        """
        garantir(not self._travado, ValidacaoError("Este item não pode mais ser alterado (pedido confirmado)"))
        garantir(
            opcao in self._produto.opcoes,
            ValidacaoError(f"A opção {opcao.nome!r} não pertence a este produto"),
        )
        garantir(opcao.ativo, ValidacaoError(f"A opção {opcao.nome!r} está indisponível"))
        garantir(
            not any(escolha.opcao is opcao for escolha in self._opcoes),
            ValidacaoError(f"A opção {opcao.nome!r} já foi escolhida neste item"),
        )
        escolha = ItemPedidoOpcao(opcao, quantidade)
        self._opcoes.append(escolha)
        return escolha

    # Uso interno
    def _vincular(self, pedido: Pedido | None) -> None:
        """Define (ou desfaz, com None) o pedido dono. Chamado por Pedido.adicionarItem/removerItem"""
        self._pedido = pedido

    def _travar(self) -> None:
        """Impede novas alterações. Chamado pelo Pedido quando é confirmado"""
        self._travado = True

    def _carregarOpcao(self, opcao, quantidade, custo_cobrado):
        opcaoAdicionada = ItemPedidoOpcao(opcao, quantidade, custo_cobrado)
        self._opcoes.append(opcaoAdicionada)
        return opcaoAdicionada

    def __repr__(self) -> str:
        """Texto exibido ao imprimir o objeto"""
        return f"<ItemPedido {self._quantidade} x {self._produto.nome!r} R$ {self.subtotal}>"


class Pedido(Entidade):
    """Um pedido de um cliente

    DER: id_pedido, ENDEREÇOID_endereco (nulo), CLIENTEUSUÁRIOID_usuário, data_criacao, data_entrega_ou_retirada,
    valor_total, taxa_entrega (padrão 0), status (padrão 'solicitado'), status_pagamento (padrão 'aguardando_sinal'),
    tipo_entrega, motivo_cancelamento (nulo), rastreamento (nulo), observacoes (nulo),
    forma_pagamento_sinal (nulo), forma_pagamento_restante (nulo), nome_recebedor (nulo)

    `valor_total` NÃO é guardado: é calculado (itens + taxa de entrega) e o repositório grava o resultado
    """

    def __init__(self,
                 cliente: Cliente,
                 tipo_entrega: TipoEntrega,
                 data_entrega_ou_retirada: datetime,
                 endereco: Endereco | None = None,
                 nome_recebedor: str = "",
                 observacoes: str = "",
                 taxa_entrega=0,
                 data_criacao: datetime | None = None,
                 status: StatusPedido = StatusPedido.SOLICITADO,
                 pagamento: Pagamento | None = None,
                 motivo_cancelamento: str = "",
                 rastreamento: str = "",
                 id_pedido: int | None = None):
        """Valida e normaliza. `data_criacao` pode ser informada (testes e recarga do banco); senão é agora"""
        super().__init__(id_pedido)
        garantir(cliente is not None, ValidacaoError("O pedido precisa de um cliente"))
        self._cliente = cliente
        self._tipo_entrega = Validador.opcaoDe(TipoEntrega, tipo_entrega, "tipo de entrega")
        # `a or b`: se data_criacao foi informada usa ela; senão usa o momento atual.
        self._data_criacao = data_criacao or datetime.now()
        # isinstance(x, datetime) é verdadeiro se x é um datetime. Rejeita texto, date puro e None.
        garantir(
            isinstance(data_entrega_ou_retirada, datetime),
            ValidacaoError("A data de entrega/retirada deve ser uma data e hora válidas"),
        )
        garantir(
            data_entrega_ou_retirada > self._data_criacao,
            ValidacaoError("A data de entrega/retirada deve ser depois da criação do pedido"),
        )
        self._data_entrega_ou_retirada = data_entrega_ou_retirada
        # Entrega exige endereço; retirada não (consulta a tabela _EXIGE_ENDERECO).
        garantir(
            endereco is not None or not _EXIGE_ENDERECO[self._tipo_entrega],
            ValidacaoError("Pedidos para entrega precisam de um endereço"),
        )
        # O endereço precisa ser um dos endereços DESTE cliente.
        garantir(
            endereco is None or endereco in cliente.enderecos,
            ValidacaoError("O endereço informado não pertence ao cliente do pedido"),
        )
        self._endereco = endereco
        self._nome_recebedor = Validador.textoOpcional(nome_recebedor, "nome de quem recebe")
        self._observacoes = Validador.textoOpcional(observacoes, "observações")
        self._taxa_entrega = Validador.dinheiro(taxa_entrega, "taxa de entrega")
        self._status = Validador.opcaoDe(StatusPedido, status, "status do pedido")
        # Pagamento novo (aguardando sinal) quando não vier um pronto do banco.
        self._pagamento = pagamento or Pagamento()
        self._motivo_cancelamento = Validador.textoOpcional(motivo_cancelamento, "motivo do cancelamento")
        self._rastreamento = Validador.textoOpcional(rastreamento, "rastreamento")
        self._itens: list[ItemPedido] = []

    @property
    def cliente(self) -> Cliente: return self._cliente

    @property
    def tipo_entrega(self) -> TipoEntrega: return self._tipo_entrega

    @property
    def data_criacao(self) -> datetime: return self._data_criacao

    @property
    def data_entrega_ou_retirada(self) -> datetime: return self._data_entrega_ou_retirada

    @property
    def endereco(self) -> Endereco | None: return self._endereco

    @property
    def nome_recebedor(self) -> str | None: return self._nome_recebedor

    @property
    def observacoes(self) -> str | None: return self._observacoes

    @property
    def taxa_entrega(self) -> Decimal: return self._taxa_entrega

    @property
    def status(self) -> StatusPedido: return self._status

    @property
    def pagamento(self) -> Pagamento: return self._pagamento

    @property
    def motivo_cancelamento(self) -> str | None: return self._motivo_cancelamento

    @property
    def rastreamento(self) -> str | None: return self._rastreamento

    @property
    def cliente_id(self) -> int | None:
        """Valor da FK CLIENTEUSUÁRIOID_usuário"""
        return self._cliente.id

    @property
    def endereco_id(self) -> int | None:
        """Valor da FK ENDEREÇOID_endereco (None na retirada)"""
        return self._endereco and self._endereco.id

    @property
    def itens(self) -> tuple[ItemPedido, ...]:
        """Cópia imutável dos itens. Para alterar, use adicionarItem/removerItem"""
        return tuple(self._itens)

    # VALORES
    @property
    def subtotal_itens(self) -> Decimal:
        """Soma dos subtotais de todos os itens."""
        return sum((item.subtotal for item in self._itens), _ZERO)

    @property
    def valor_total(self) -> Decimal:
        """Itens + taxa de entrega (coluna valor_total do DER)"""
        return self.subtotal_itens + self._taxa_entrega

    @property
    def valor_sinal(self) -> Decimal:
        """Os 50% de entrada."""
        return self._pagamento.sinal(self.valor_total)

    @property
    def valor_restante(self) -> Decimal:
        """Os outros 50%."""
        return self._pagamento.restante(self.valor_total)

    @property
    def valor_em_aberto(self) -> Decimal:
        """Quanto ainda falta pagar neste momento (entrevista)"""
        return self._pagamento.valorEmAberto(self.valor_total)

    # MONTAGEM DO PEDIDO (só enquanto editável)
    def _exigirEditavel(self) -> None:
        """Garante que o pedido ainda pode ser alterado (Solicitado ou Orçamento). Depois de Confirmado, nunca mais"""
        garantir(
            self._status in _STATUS_EDITAVEIS,
            ValidacaoError(f"Um pedido '{self._status.value}' não pode mais ser alterado"),
        )

    def adicionarItem(self, item: ItemPedido) -> None:
        """Inclui um item. O item não pode já pertencer a outro pedido"""
        self._exigirEditavel()
        garantir(item.pedido is None, ValidacaoError("Este item já pertence a um pedido"))
        item._vincular(self)
        self._itens.append(item)

    def removerItem(self, item: ItemPedido) -> None:
        """Remove um item e desfaz o vínculo"""
        self._exigirEditavel()
        garantir(item in self._itens, ValidacaoError("Este item não pertence a este pedido"))
        self._itens.remove(item)
        item._vincular(None)

    def definirTaxaEntrega(self, taxa) -> None:
        """Define a taxa de entrega (calculada pela CalculadoraPreco a partir da distância)"""
        self._exigirEditavel()
        self._taxa_entrega = Validador.dinheiro(taxa, "taxa de entrega")

    def alterarRastreamento(self, texto: str) -> None:
        """Código/observação de rastreio da entrega. Pode mudar em qualquer status (não afeta valores)"""
        self._rastreamento = Validador.textoOpcional(texto, "rastreamento")

    # Pagamento
    def registrarSinal(self, forma: FormaPagamento) -> None:
        """Registra o pagamento do sinal (50%). Só depois do orçamento (fluxo da entrevista)"""
        garantir(
            self._status is StatusPedido.ORCAMENTO,
            ValidacaoError("O sinal só pode ser pago quando o pedido está em orçamento"),
        )
        self._pagamento.registrarSinal(forma)

    def registrarPagamentoRestante(self, forma: FormaPagamento) -> None:
        """Registra o pagamento do restante. Só depois de confirmado"""
        garantir(
            self._status in _STATUS_QUITAVEIS,
            ValidacaoError("O restante só pode ser pago depois que o pedido foi confirmado"),
        )
        self._pagamento.registrarRestante(forma)

    # Prazo mínimo
    def validarPrazo(self) -> None:
        """Confere o prazo mínimo (relatório 2.3): data de entrega >= criação + maior antecedência entre os produtos

        `max(gerador, default=0)`: o maior valor; se não houver itens, usa 0 (sem isso max() daria erro)
        timedelta(hours=n) representa "n horas" e pode ser somado a um datetime
        """
        antecedencia = max((item.produto.antecedencia_horas for item in self._itens), default=0)
        minimo = self._data_criacao + timedelta(hours=antecedencia)
        garantir(
            self._data_entrega_ou_retirada >= minimo,
            ValidacaoError(
                f"Prazo insuficiente: os produtos pedem {antecedencia}h de antecedência "
                f"(entrega a partir de {minimo:%d/%m/%Y %H:%M})"
            ),
        )

    # Mudança de status (autômato em enums.StatusPedido + efeitos ao ENTRAR em cada status)
    def avancarStatus(self, novo_status: StatusPedido, motivo: str = "") -> None:
        """
        Muda o status seguindo o fluxo e aplicando a regra de negócio do status de destino

        LÓGICA:
        1) converte para StatusPedido (aceita o texto do banco);
        2) o autômato (StatusPedido.validarTransicao) recusa mudanças proibidas;
        3) executa o "efeito de entrada" do status de destino (pode recusar, ex.: confirmar sem sinal);
        4) só então grava o novo status. Se qualquer passo falhar, o status continua o antigo
        """
        destino = Validador.opcaoDe(StatusPedido, novo_status, "status do pedido")
        self._status.validarTransicao(destino)
        # TABELA: destino -> método com a regra de quem ENTRA naquele status. `.get(chave, padrão)` usa o
        # padrão (_semEfeito) quando o status não tem regra própria, e `(motivo)` no final chama o método.
        efeitos = {
            StatusPedido.ORCAMENTO: self._aoOrcar,
            StatusPedido.CONFIRMADO: self._aoConfirmar,
            StatusPedido.FINALIZADO: self._aoFinalizar,
            StatusPedido.CANCELADO: self._aoCancelar,
        }
        efeitos.get(destino, self._semEfeito)(motivo)
        self._status = destino

    def _semEfeito(self, motivo: str) -> None:
        """Status sem regra extra de entrada (Em produção, Pronto, Entregue). `pass` = não faz nada"""
        pass

    def _aoOrcar(self, motivo: str) -> None:
        """Para virar Orçamento: precisa ter ao menos um item e respeitar o prazo mínimo"""
        garantir(self._itens, ValidacaoError("Adicione ao menos um item antes de gerar o orçamento"))
        self.validarPrazo()

    def _aoConfirmar(self, motivo: str) -> None:
        """Para virar Confirmado: o sinal precisa estar pago. Depois disso o pedido e os itens ficam travados"""
        garantir(
            self._pagamento.sinal_pago,
            ValidacaoError("Não é possível confirmar o pedido: o sinal de 50% ainda não foi pago"),
        )
        # for sem if: trava todos os itens (imutabilidade depois de confirmado).
        for item in self._itens:
            item._travar()

    def _aoFinalizar(self, motivo: str) -> None:
        """Para virar Finalizado: o pagamento precisa estar integral (entrevista)"""
        garantir(
            self._pagamento.quitado,
            ValidacaoError("Não é possível finalizar: o pagamento integral ainda não foi registrado"),
        )

    def _aoCancelar(self, motivo: str) -> None:
        """Para virar Cancelado: exige motivo (entrevista 4.11). O sinal NÃO é devolvido(entrevista)"""
        self._motivo_cancelamento = Validador.texto(motivo, "motivo do cancelamento")

    # Uso interno
    def _carregarItem(self, item: ItemPedido) -> None:
        """
        Uso interno do repositório: anexa um item lido do banco, sem as checagens de adicionarItem.
        Se o pedido já passou da fase editável, o item chega travado, igual ficaria após a confirmação
        """
        item._vincular(self)
        self._itens.append(item)

        opcoes = {True: item._travar, False: lambda: None}
        chave = self._status not in _STATUS_EDITAVEIS

        funcao = opcoes[chave]
        funcao()

    def __repr__(self) -> str:
        """Texto exibido ao imprimir o objeto"""
        return f"<Pedido id={self.id} {self._status.value} R$ {self.valor_total} ({len(self._itens)} itens)>"
