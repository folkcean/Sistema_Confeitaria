"""
app / repositories / contexto_ia_rep.py

O banco que vai para a IA: insumos, pedidos em aberto e vendas por semana
A IA não acessa o banco. o sistema roda estas consultas e manda o resultado.
"""
from app.repositories.base import RepositorioBase
from app.repositories.relatorios_rep import STATUS_DE_VENDA

# Um insumo ativo por linha, na unidade de COMPRA. %(dias)s é a janela do consumo médio
SQL_INSUMOS = """
              WITH consumo AS (SELECT id_insumo, SUM(quantidade) AS total
                               FROM movimentacao_estoque
                               WHERE tipo = 'consumo'
                                 AND data >= now() - make_interval(days => %(dias)s)
                               GROUP BY id_insumo),
                   a_caminho AS (SELECT i.id_insumo,
                                        SUM(i.quantidade)         AS quantidade,
                                        MIN(c.data_entrega)::date AS entrega_prevista
                                 FROM item_compra_insumo i
                                          JOIN compra_insumo c USING (id_compra_insumo)
                                 WHERE c.status = 'pendente'
                                 GROUP BY i.id_insumo),
                   reservado AS (SELECT ir.id_insumo,
                                        SUM(ip.quantidade * pr.quantidade * ir.quantidade_necessaria /
                                            r.rendimento_qtd)                 AS quantidade,
                                        MIN(p.data_entrega_ou_retirada)::date AS primeira_entrega
                                 FROM pedido p
                                          JOIN item_pedido ip USING (id_pedido)
                                          JOIN produto_receita pr USING (id_produto)
                                          JOIN receita r USING (id_receita)
                                          JOIN item_receita ir USING (id_receita)
                                 WHERE p.status IN ('solicitado', 'orcamento')
                                   AND p.data_entrega_ou_retirada >= now()
                                 GROUP BY ir.id_insumo),
                   ultimo_fornecedor AS (SELECT DISTINCT ON (i.id_insumo) i.id_insumo, c.id_fornecedor, f.nome
                                         FROM item_compra_insumo i
                                                  JOIN compra_insumo c USING (id_compra_insumo)
                                                  JOIN fornecedor f USING (id_fornecedor)
                                         WHERE c.status <> 'cancelada'
                                         ORDER BY i.id_insumo, c.data_compra DESC),
                   prazo AS (SELECT id_fornecedor, ROUND(AVG(data_entrega::date - data_compra::date), 1) AS dias
                             FROM compra_insumo
                             WHERE status = 'recebida'
                               AND data_entrega IS NOT NULL
                             GROUP BY id_fornecedor)
              SELECT ins.nome                                                         AS insumo,
                     ins.tipo,
                     ins.unidade_medida                                               AS unidade,
                     ROUND(ins.quantidade_atual / ins.fator_conversao, 2)             AS saldo,
                     ROUND(ins.estoque_minimo / ins.fator_conversao, 2)               AS minimo,
                     ROUND(COALESCE(co.total, 0) / ins.fator_conversao / %(dias)s, 3) AS consumo_por_dia,
                     ROUND(ins.quantidade_atual / NULLIF(co.total / %(dias)s, 0), 1)  AS dias_de_cobertura,
                     COALESCE(ac.quantidade, 0)                                       AS a_caminho,
                     ac.entrega_prevista,
                     ROUND(COALESCE(re.quantidade, 0) / ins.fator_conversao, 3)       AS reservado_em_pedidos,
                     re.primeira_entrega,
                     uf.nome                                                          AS fornecedor,
                     pz.dias                                                          AS prazo_entrega_dias,
                     ins.custo_por_unidade
              FROM insumo ins
                       LEFT JOIN consumo co USING (id_insumo)
                       LEFT JOIN a_caminho ac USING (id_insumo)
                       LEFT JOIN reservado re USING (id_insumo)
                       LEFT JOIN ultimo_fornecedor uf USING (id_insumo)
                       LEFT JOIN prazo pz USING (id_fornecedor)
              WHERE ins.ativo
              ORDER BY ins.tipo, ins.nome \
              """

# Pedidos com entrega de hoje em diante, sem nenhum dado do cliente
SQL_PEDIDOS_EM_ABERTO = """
                        SELECT p.id_pedido                                                          AS pedido,
                               p.status,
                               p.data_entrega_ou_retirada::date                                     AS entrega,
                               string_agg(ip.quantidade || ' x ' || pr.nome, '; ' ORDER BY pr.nome) AS itens
                        FROM pedido p
                                 JOIN item_pedido ip USING (id_pedido)
                                 JOIN produto pr USING (id_produto)
                        WHERE p.status IN ('solicitado', 'orcamento', 'confirmado', 'em_producao', 'pronto')
                          AND p.data_entrega_ou_retirada >= current_date
                        GROUP BY p.id_pedido
                        ORDER BY entrega, p.id_pedido \
                        """

# Quantidade vendida de cada produto por semana (pela data de entrega, como no relatório)
SQL_VENDAS_POR_SEMANA = """
                        SELECT date_trunc('week', p.data_entrega_ou_retirada)::date AS semana,
                               pr.nome                                              AS produto,
                               SUM(ip.quantidade)                                   AS quantidade
                        FROM pedido p
                                 JOIN item_pedido ip USING (id_pedido)
                                 JOIN produto pr USING (id_produto)
                        WHERE p.status = ANY (%(status)s)
                          AND p.data_entrega_ou_retirada >= current_date - make_interval(weeks => %(semanas)s)
                        GROUP BY 1, 2
                        ORDER BY 1, 2 \
                        """


class RepositorioContextoIA(RepositorioBase):
    """Monta o contexo do estoque e da demanda que vai para a IA"""

    def montar(self, dias=30, semanas=8):
        """Tudo numa transação SOMENTE LEITURA: se algum SQL tentar gravar, o PostgreSQL recusa"""
        with self._transacao():
            self._executar("SET TRANSACTION READ ONLY", ())
            return {
                "hoje": self._umaLinha("SELECT current_date AS hoje", ())["hoje"],
                "janela_consumo_dias": dias,
                "insumos": self._todasLinhas(SQL_INSUMOS, {"dias": dias}),
                "pedidos_em_aberto": self._todasLinhas(SQL_PEDIDOS_EM_ABERTO, ()),
                "vendas_por_semana": self._todasLinhas(
                    SQL_VENDAS_POR_SEMANA, {"status": STATUS_DE_VENDA, "semanas": semanas}
                ),
            }
