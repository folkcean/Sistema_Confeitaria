"""
app / repositories / compras_rep.py

Acesso às tabelas COMPRA_INSUMO e ITEM_COMPRA_INSUMO
"""

from app.models import CompraInsumo, ItemCompraInsumo
from app.repositories.base import RepositorioBase


class RepositorioCompras(RepositorioBase):

    def __init__(self, obter_conexao, repo_fornecedores):
        """
        Montar uma compra exige o Fornecedor: o repositório de fornecedores já faz isso,
        então é reaproveitado (como o RepositorioPedidos faz com usuários e produtos)
        """
        super().__init__(obter_conexao)
        self._repo_fornecedores = repo_fornecedores

    def buscarPorId(self, id_compra, estoque):
        """Compra com essa PK, já com os itens, ou None"""
        linha = self._umaLinha(
            "SELECT * FROM compra_insumo WHERE id_compra_insumo = %s",
            (id_compra,),
        )
        return linha and self._montarCompras([linha], estoque)[0]

    def listar(self, estoque, status=""):

        linhas = self._todasLinhas(
            "SELECT * FROM compra_insumo "
            "WHERE (%s = '' OR status = %s) "
            "ORDER BY data_compra DESC, id_compra_insumo DESC",
            # O filtro aparece duas vezes no SQL, então vai duas vezes aqui
            (status, status),
        )
        return self._montarCompras(linhas, estoque)

    def _insumosPorId(self, estoque):
        """Dicionário id -> insumo, com os mesmos objetos que estão dentro do estoque"""
        insumos_por_id = {}
        for insumo in estoque.insumos:
            insumos_por_id[insumo.id] = insumo
        return insumos_por_id

    def _montarCompras(self, linhas, estoque):

        # Cache desta leitura: o mesmo fornecedor é o mesmo objeto em todas as compras
        fornecedores_por_id = {}

        # 1) Compras
        compras_por_id = {}
        for linha in linhas:
            id_fornecedor = linha.pop("id_fornecedor")
            linha.pop("valor_total")

            fornecedor = fornecedores_por_id.get(id_fornecedor) or fornecedores_por_id.setdefault(
                id_fornecedor, self._repo_fornecedores.buscarPorId(id_fornecedor)
            )

            compra = CompraInsumo(fornecedor, **linha)
            compras_por_id[compra.id] = compra

        # 2) Itens de todas as compras numa consulta só
        insumos_por_id = self._insumosPorId(estoque)
        linhas_itens = self._todasLinhas(
            "SELECT * FROM item_compra_insumo WHERE id_compra_insumo = ANY(%s) ORDER BY id_item_compra",
            (list(compras_por_id),),
        )
        for linha in linhas_itens:
            id_compra = linha.pop("id_compra_insumo")
            insumo = insumos_por_id[linha.pop("id_insumo")]
            item = ItemCompraInsumo(insumo, **linha)


            compras_por_id[id_compra]._carregarItem(item)

        # Mesma ordem das linhas recebidas
        compras = []
        for linha in linhas:
            compras.append(compras_por_id[linha["id_compra_insumo"]])
        return compras

    def salvarNova(self, compra):

        with self._transacao():
            linha = self._umaLinha(
                "INSERT INTO compra_insumo (id_fornecedor, data_compra, data_entrega, valor_total, status, nota_fiscal) "
                "VALUES (%s, %s, %s, %s, %s, %s) "
                "RETURNING id_compra_insumo",
                (
                    compra.fornecedor_id, compra.data_compra, compra.data_entrega,
                    compra.valor_total, compra.status.value, compra.nota_fiscal,
                ),
            )
            compra.atribuirID(linha["id_compra_insumo"])

            for item in compra.itens:
                linha = self._umaLinha(
                    "INSERT INTO item_compra_insumo (id_insumo, id_compra_insumo, quantidade, custo_unitario) "
                    "VALUES (%s, %s, %s, %s) "
                    "RETURNING id_item_compra",
                    (item.insumo_id, compra.id, item.quantidade, item.custo_unitario),
                )
                item.atribuirID(linha["id_item_compra"])
        return compra

    def atualizar(self, compra):
        """Grava o que muda depois de criada: status e data_entrega (os itens nunca mudam)"""
        self._executar(
            "UPDATE compra_insumo SET status = %s, data_entrega = %s WHERE id_compra_insumo = %s",
            (compra.status.value, compra.data_entrega, compra.id),
        )
        return compra

    def gravarRecebimento(self, compra, movimentacoes, repo_estoque):

        with self._transacao():
            self.atualizar(compra)
            for movimentacao in movimentacoes:
                repo_estoque.registrarMovimentacao(movimentacao.insumo, movimentacao)
            # O salvar do insumo é o que grava o custo_por_unidade novo (não mexe no saldo)
            for item in compra.itens:
                repo_estoque.salvar(item.insumo)
