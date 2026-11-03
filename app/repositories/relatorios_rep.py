from decimal import Decimal

from app.repositories.base import RepositorioBase

# Status que contam como venda (do confirmado ao finalizado)
STATUS_DE_VENDA = ["confirmado", "em_producao", "pronto", "entregue", "finalizado"]

# Filtro de pedido vendido no período, usado em várias consultas
# (os três %s: a lista de status, o início e o fim)
FILTRO_VENDA = (
    "p.status = ANY(%s) "
    "AND p.data_entrega_ou_retirada::date BETWEEN %s AND %s"
)


class RepositorioRelatorios(RepositorioBase):
    """Números de vendas, produtos e insumos de um período (inicio e fim inclusos)"""

    def resumoVendas(self, inicio, fim):
        """Faturamento, número de pedidos, ticket médio e lucro estimado"""
        parametros = (STATUS_DE_VENDA, inicio, fim)

        totais = self._umaLinha(
            "SELECT COUNT(*) AS pedidos, COALESCE(SUM(p.valor_total), 0) AS faturamento "
            "FROM pedido p WHERE " + FILTRO_VENDA,
            parametros,
        )
        custos = self._umaLinha(
            "SELECT COALESCE(SUM(i.quantidade * i.custo_unitario), 0) AS custo "
            "FROM item_pedido i JOIN pedido p USING (id_pedido) WHERE " + FILTRO_VENDA,
            parametros,
        )

        faturamento = totais["faturamento"]
        pedidos = totais["pedidos"]
        # max(pedidos, 1): sem pedidos, divide por 1 (dá 0) em vez de dividir por zero
        ticket_medio = (faturamento / max(pedidos, 1)).quantize(Decimal("0.01"))
        return {
            "faturamento": faturamento,
            "pedidos": pedidos,
            "ticket_medio": ticket_medio,
            "lucro_estimado": faturamento - custos["custo"],
        }

    def vendasPorDia(self, inicio, fim):
        """
        Um item por dia do período (dia, total), inclusive os dias sem venda (total 0)

        generate_series cria uma linha para cada dia entre inicio e fim; o LEFT JOIN
        junta os pedidos vendidos de cada dia (dia sem pedido fica com SUM nulo -> 0)
        """
        return self._todasLinhas(
            "SELECT dia::date AS dia, COALESCE(SUM(p.valor_total), 0) AS total "
            "FROM generate_series(%s::date, %s::date, interval '1 day') AS dia "
            "LEFT JOIN pedido p ON p.data_entrega_ou_retirada::date = dia::date "
            "AND p.status = ANY(%s) "
            "GROUP BY dia ORDER BY dia",
            (inicio, fim, STATUS_DE_VENDA),
        )

    def vendasPorProduto(self, inicio, fim):
        """
        Um item por produto (nome, quantidade, faturamento, lucro), em ordem de nome.

        Entram os produtos ATIVOS mesmo sem venda (quantidade 0: aparecem nos menos
        vendidos) e os inativos que venderam no período.
        Faturamento do item = quantidade × preço + personalização − desconto
        """
        return self._todasLinhas(
            "SELECT pr.nome, "
            "COALESCE(SUM(v.quantidade), 0) AS quantidade, "
            "COALESCE(SUM(v.receita), 0) AS faturamento, "
            "COALESCE(SUM(v.receita - v.custo), 0) AS lucro "
            "FROM produto pr "
            "LEFT JOIN ("
            "  SELECT i.id_produto, i.quantidade, "
            "  i.quantidade * i.preco_unitario + i.custo_personalizacao - i.desconto AS receita, "
            "  i.quantidade * i.custo_unitario AS custo "
            "  FROM item_pedido i JOIN pedido p USING (id_pedido) "
            "  WHERE " + FILTRO_VENDA +
            ") v USING (id_produto) "
            "WHERE pr.ativo OR v.id_produto IS NOT NULL "
            "GROUP BY pr.id_produto, pr.nome "
            "ORDER BY pr.nome",
            (STATUS_DE_VENDA, inicio, fim),
        )

    def insumosConsumidos(self, inicio, fim):
        """
        Um item por insumo consumido no período (nome, quantidade, unidade, custo),
        do maior custo para o menor, pelas movimentações do tipo "consumo".

        O saldo e as movimentações estão na unidade da RECEITA (como no DB_fill.sql):
        divide pelo fator para mostrar na unidade de COMPRA, que é a do custo_por_unidade.
        Se a decisão com a Anna mudar a unidade do saldo, a divisão sai daqui
        """
        return self._todasLinhas(
            "SELECT ins.nome, ins.unidade_medida AS unidade, "
            "ROUND(SUM(m.quantidade) / ins.fator_conversao, 2) AS quantidade, "
            "ROUND(SUM(m.quantidade) / ins.fator_conversao * COALESCE(ins.custo_por_unidade, 0), 2) AS custo "
            "FROM movimentacao_estoque m JOIN insumo ins USING (id_insumo) "
            "WHERE m.tipo = 'consumo' AND m.data::date BETWEEN %s AND %s "
            "GROUP BY ins.id_insumo, ins.nome, ins.unidade_medida, ins.fator_conversao, ins.custo_por_unidade "
            "ORDER BY custo DESC, ins.nome",
            (inicio, fim),
        )
