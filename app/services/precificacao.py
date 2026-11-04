"""
app/services/precificacao.py

Calculadora de preço

Responde às perguntas de preço do sistema:
    - quanto CUSTA produzir um produto (ingredientes pela receita + perda + mão de obra + embalagem + custo indireto)?
    - quanto COBRAR (custo x multiplicador de margem)?
    - quanto custam as PERSONALIZAÇÕES escolhidas?
    - quanto é a TAXA DE ENTREGA para a distância informada?
    - como montar um ItemPedido com os valores já fixados?

Fica em services/ porque junta vários models (Produto, Receita, Insumo, ItemPedido) sem pertencer a nenhum deles
"""
from __future__ import annotations

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal

from app.exceptions import ValidacaoError
from app.models.enums import TipoEntrega
from app.models.opcao_personalizacao import OpcaoPersonalizacao
from app.models.pedido import ItemPedido, ItemPedidoOpcao
from app.models.produto import Produto
from app.validators.campos import Validador, garantir

# Zero em dinheiro (2 casas), reaproveitado nas somas
_ZERO = Decimal("0.00")


class CalculadoraPreco:
    """
    Calcula custos, preços, personalização e taxa de entrega. Todos os métodos devolvem Decimal
    """

    _CENTAVOS = Decimal("0.01")

    # Estimativa de faixas: (distância máxima em km, taxa em R$). Acima da última faixa não há entrega
    # SINTAXE: tupla de tuplas. Cada par é uma faixa "até X km, cobra R$ Y"
    FAIXAS_ENTREGA_PADRAO = (
        (Decimal("2"), Decimal("5.00")),
        (Decimal("5"), Decimal("8.00")),
        (Decimal("10"), Decimal("12.00")),
        (Decimal("15"), Decimal("18.00")),
    )

    def __init__(self, 
                 multiplicador_margem=Decimal("2.5"), 
                 faixas_entrega=None):
        """
        Guarda o multiplicador da margem e a tabela de faixas de entrega, validando os dois

        `faixas_entrega=None`: sem informar, usa FAIXAS_ENTREGA_PADRAO. Se informar, precisa estar em ordem
        crescente de distância e sem distâncias repetidas.
        """
        self._multiplicador = Validador.quantidadePositiva(multiplicador_margem, "multiplicador da margem")
        # Multiplicador menor que 1 faria o preço ficar abaixo do custo (prejuízo): recusamos.
        garantir(
            self._multiplicador >= 1,
            ValidacaoError("O multiplicador da margem não pode ser menor que 1 (venderia abaixo do custo)")
        )
        # `a or b`: usa as faixas informadas; se vier None, usa as padrão.
        bruto = faixas_entrega or self.FAIXAS_ENTREGA_PADRAO
        # Valida cada faixa: limite > 0 (em km) e taxa >= 0 (em R$). Compreensão de tupla de pares.
        self._faixas = tuple(
            (Validador.quantidadePositiva(limite, "limite da faixa (km)"), Validador.dinheiro(taxa, "taxa da faixa"))
            for limite, taxa in bruto
        )
        limites = [limite for limite, _ in self._faixas]
        # sorted(set(x)) = ordenado e sem repetidos. Se for igual à lista original, ela já estava em ordem estrita.
        garantir(
            limites == sorted(set(limites)),
            ValidacaoError("As faixas de entrega devem estar em ordem crescente de distância, sem repetição")
        )

    @property
    def multiplicador_margem(self) -> Decimal: return self._multiplicador
    @property
    def faixas_entrega(self) -> tuple[tuple[Decimal, Decimal], ...]: return self._faixas

    # Custo
    def custoIngredientes(self, produto: Produto, unidades: int = 1) -> Decimal:
        """
        Custo dos insumos de `unidades` do produto, somando o custo de cada insumo da receita

        LÓGICA: Produto.necessidades() devolve pares (insumo, quantidade na unidade da receita);
        Insumo.custoDe(quantidade) converte para a unidade de estoque e multiplica pelo custo por unidade.
        Insumo SEM custo cadastrado levanta ValidacaoError (melhor avisar que calcular errado).
        """
        total = sum((insumo.custoDe(quantidade) for insumo, quantidade in produto.necessidades(unidades)), Decimal("0"))
        return total.quantize(self._CENTAVOS, rounding=ROUND_HALF_UP)

    def custoUnitario(self, produto: Produto) -> Decimal:
        """
        Custo de produzir UMA unidade: ingredientes (com a perda do produto) + mão de obra + embalagem + indireto

        Reaproveita Produto.custoTotal, que já aplica o percentual de perda só sobre os ingredientes
        """
        return produto.custoTotal(self.custoIngredientes(produto))

    # Preço
    def precoUnitario(self, produto: Produto) -> Decimal:
        """
        Preço de venda de UMA unidade = custo unitário x multiplicador da margem, em centavos

        Exemplo: custo R$ 40,00 x 2,5 = R$ 100,00
        """
        return (self.custoUnitario(produto) * self._multiplicador).quantize(self._CENTAVOS, rounding=ROUND_HALF_UP)

    def precoPersonalizacao(self, escolhas: Iterable[tuple[OpcaoPersonalizacao, int]]) -> Decimal:
        """
        Total das personalizações. `escolhas` é uma lista de pares (opção, quantidade)

        Exemplo (entrevista 5.4): [(brigadeiro, 4)] com R$ 3,00 cada -> R$ 12,00
        """
        return sum((ItemPedidoOpcao(opcao, quantidade).subtotal for opcao, quantidade in escolhas), _ZERO)

    # Entrega
    def taxaEntrega(self, tipo_entrega: TipoEntrega, distancia_km=None) -> Decimal:
        """
        Taxa conforme o tipo: retirada = R$ 0,00; entrega = taxa da faixa da distância

        TABELA no lugar de if/else: o tipo de entrega escolhe qual função rodar (o `()` no final executa)
        Na retirada a distância é ignorada
        """
        tipo = Validador.opcaoDe(TipoEntrega, tipo_entrega, "tipo de entrega")
        calculos = {
            TipoEntrega.RETIRADA: lambda: _ZERO,
            TipoEntrega.ENTREGA: lambda: self._taxaPorFaixa(distancia_km),
        }
        return calculos[tipo]()

    def _taxaPorFaixa(self, distancia_km) -> Decimal:
        """
        Procura a primeira faixa cujo limite comporta a distância. Acima da última faixa: sem entrega

        `next(iterador, padrão)` pega o PRIMEIRO item que satisfaz o filtro, ou o padrão (None) se não houver
        As faixas estão em ordem crescente, então a primeira que comporta é a mais barata correta
        """
        garantir(distancia_km is not None, ValidacaoError("Informe a distância para calcular a taxa de entrega"))
        km = Validador.quantidade(distancia_km, "distância (km)")
        faixa = next(filter(lambda par: km <= par[0], self._faixas), None)
        garantir(
            faixa is not None,
            ValidacaoError(f"Fora da área de entrega: {km} km é mais que o máximo de {self._faixas[-1][0]} km")
        )
        return faixa[1]

    # Montagem
    def montarItem(self, 
                   produto: Produto, 
                   quantidade: int,
                   escolhas: Iterable[tuple[OpcaoPersonalizacao, int]] = (),
                   personalizacao: str = "", 
                   observacoes: str = "") -> ItemPedido:
        """
        Cria um ItemPedido com preço e custo unitários FIXADOS agora e as opções escolhidas

        O ItemPedido valida cada opção (do produto, ativa, não repetida). Devolve o item pronto para Pedido.adicionarItem()
        """
        item = ItemPedido(
            produto, quantidade,
            preco_unitario=self.precoUnitario(produto),
            custo_unitario=self.custoUnitario(produto),
            personalizacao=personalizacao, observacoes=observacoes,
        )
        for opcao, qtd in escolhas:
            item.adicionarOpcao(opcao, qtd)
        return item