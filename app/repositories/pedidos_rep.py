"""
app / repositories / pedidos_rep.py

Acesso às tabelas PEDIDO, ITEM_PEDIDO e OPCAO_ESCOLHIDA
"""

from psycopg.errors import CheckViolation

from app.exceptions import ValidacaoError
from app.models import ItemPedido, Pagamento, Pedido
from app.repositories.base import RepositorioBase


def _doCache(cache, chave, carregar):
    """
    O objeto guardado no `cache` com essa chave. Se ainda não está lá, carrega, guarda e devolve
    O `or` só chama carregar(chave) quando cache.get(chave) dá None (a chave ainda não foi vista)
    """
    return cache.get(chave) or cache.setdefault(chave, carregar(chave))


class RepositorioPedidos(RepositorioBase):
    MENSAGEM_PEDIDO_INVALIDO = (
        "Algum valor do pedido não é aceito. "
        "Confira o tipo de entrega, as quantidades e as formas de pagamento."
    )
    STATUS_ENCERRADOS = ["entregue", "finalizado", "cancelado"]

    def __init__(self, obter_conexao, repo_usuarios, repo_produtos):
        """
        Montar um pedido exige o Cliente (com os endereços) e os Produto (com as opções):
        os repositórios que já fazem isso são reaproveitados, em vez de repetir o SQL deles aqui.
        repo_usuarios pode ser um RepositorioUsuarios ou um RepositorioClientes (os dois têm buscarPorId)
        """
        super().__init__(obter_conexao)
        self._repo_usuarios = repo_usuarios
        self._repo_produtos = repo_produtos

    # Leitura

    def buscarPorId(self, id_pedido):
        """Pedido com essa PK, já com itens e opções, ou None"""
        sql = "SELECT * FROM pedido WHERE id_pedido = %s"
        parametros = (id_pedido,)
        linha = self._umaLinha(sql, parametros)
        return linha and self._montarPedidos([linha])[0]

    def listarDoCliente(self, id_cliente):
        """Pedidos do cliente, do mais recente para o mais antigo (tela da loja)"""
        sql = "SELECT * FROM pedido WHERE id_cliente = %s ORDER BY data_criacao DESC"
        parametros = (id_cliente,)
        linhas = self._todasLinhas(sql, parametros)
        return self._montarPedidos(linhas)

    def listarEntregasEntre(self, inicio, fim):
        """
        Pedidos ainda em andamento com entrega/retirada entre as duas datas (incluindo as pontas),
        da mais próxima para a mais distante
        """
        sql = (
            "SELECT * FROM pedido "
            "WHERE data_entrega_ou_retirada::date BETWEEN %s AND %s "
            "AND NOT (status = ANY(%s)) "
            "ORDER BY data_entrega_ou_retirada"
        )
        parametros = (inicio, fim, self.STATUS_ENCERRADOS)
        linhas = self._todasLinhas(sql, parametros)
        return self._montarPedidos(linhas)

    def listar(self, busca="", status="", data=None):
        """
        Lista do painel, por data de entrega/retirada (mais recente primeiro)
        busca: nome ou telefone do cliente · status: texto do StatusPedido ("" = todos) · data: date ou None
        """
        sql = (
            "SELECT p.* FROM pedido p JOIN usuario u ON u.id_usuario = p.id_cliente "
            "WHERE (u.nome ILIKE %s OR u.telefone LIKE %s) "
            "AND (%s = '' OR p.status = %s) "
            "AND (%s::date IS NULL OR p.data_entrega_ou_retirada::date = %s::date) "
            "ORDER BY p.data_entrega_ou_retirada DESC"
        )
        padrao = "%" + busca + "%"
        # Cada filtro aparece duas vezes no SQL, então vai duas vezes aqui, na mesma ordem
        parametros = (padrao, padrao, status, status, data, data)
        linhas = self._todasLinhas(sql, parametros)
        return self._montarPedidos(linhas)

    def _montarPedidos(self, linhas):
        """
        Cria os Pedido a partir das linhas de PEDIDO, na mesma ordem, com itens e opções
        Os produtos vêm com as opções, mas sem as receitas (só a confirmação, Tarefa 6.4, precisa delas)
        """
        # Caches desta leitura: o mesmo cliente/produto é o mesmo objeto em todos os pedidos/itens
        clientes_por_id = {}
        produtos_por_id = {}

        # 1) Pedidos
        pedidos_por_id = {}
        for linha in linhas:
            cliente = _doCache(clientes_por_id, linha["id_cliente"], self._repo_usuarios.buscarPorId)

            # Tem que ser o objeto de dentro de cliente.enderecos (o Pedido confere com `in`)
            enderecos_por_id = {}
            for endereco in cliente.enderecos:
                enderecos_por_id[endereco.id] = endereco
            # Na retirada a coluna é NULL: .get(None) devolve None
            endereco = enderecos_por_id.get(linha["id_endereco_entrega"])

            pagamento = Pagamento(
                linha["status_pagamento"], linha["forma_pagamento_sinal"], linha["forma_pagamento_restante"]
            )

            # valor_total não é lido: o Pedido calcula o total pelos itens
            pedido = Pedido(
                cliente=cliente,
                tipo_entrega=linha["tipo_entrega"],
                data_entrega_ou_retirada=linha["data_entrega_ou_retirada"],
                endereco=endereco,
                nome_recebedor=linha["nome_recebedor"],
                observacoes=linha["observacoes"],
                taxa_entrega=linha["taxa_entrega"],
                data_criacao=linha["data_criacao"],
                status=linha["status"],
                pagamento=pagamento,
                motivo_cancelamento=linha["motivo_cancelamento"],
                rastreamento=linha["rastreamento"],
                id_pedido=linha["id_pedido"],
            )
            pedidos_por_id[pedido.id] = pedido

        # 2) Itens de todos os pedidos numa consulta só
        sql = "SELECT * FROM item_pedido WHERE id_pedido = ANY(%s) ORDER BY id_item_pedido"
        parametros = (list(pedidos_por_id),)
        itens_por_id = {}
        for linha in self._todasLinhas(sql, parametros):
            # buscarPorId, e não buscarAtivo: o histórico abre mesmo se o produto saiu do cardápio
            produto = _doCache(produtos_por_id, linha["id_produto"], self._repo_produtos.buscarPorId)

            # custo_personalizacao não é lido: o item calcula pelas opções
            item = ItemPedido(
                produto,
                linha["quantidade"],
                preco_unitario=linha["preco_unitario"],
                custo_unitario=linha["custo_unitario"],
                personalizacao=linha["personalizacao"],
                desconto=linha["desconto"],
                observacoes=linha["observacoes"],
                id_item_pedido=linha["id_item_pedido"],
            )
            # Trava o item se o pedido já passou da fase editável
            pedidos_por_id[linha["id_pedido"]]._carregarItem(item)
            itens_por_id[item.id] = item

        # 3) Opções de todos os itens numa consulta só
        sql = "SELECT * FROM opcao_escolhida WHERE id_item_pedido = ANY(%s)"
        parametros = (list(itens_por_id),)
        for linha in self._todasLinhas(sql, parametros):
            item = itens_por_id[linha["id_item_pedido"]]
            # Tem que ser o objeto de dentro de produto.opcoes
            opcoes_por_id = {}
            for opcao in item.produto.opcoes:
                opcoes_por_id[opcao.id] = opcao
            opcao = opcoes_por_id[linha["id_opcao"]]
            # Aceita opção desligada depois do pedido e item travado
            item._carregarOpcao(opcao, linha["quantidade"], linha["custo_cobrado"])

        # Mesma ordem das linhas recebidas
        pedidos = []
        for linha in linhas:
            pedidos.append(pedidos_por_id[linha["id_pedido"]])
        return pedidos

    #  Gravação

    def salvarNovo(self, pedido):
        """Grava um pedido que ainda não tem id, com itens e opções, numa transação só"""
        try:
            with self._transacao():
                self._inserirPedido(pedido)
                for item in pedido.itens:
                    self._inserirItem(pedido, item)
                    for escolha in item.opcoes:
                        self._inserirEscolha(item, escolha)
        except CheckViolation as erro:
            raise ValidacaoError(self.MENSAGEM_PEDIDO_INVALIDO) from erro
        return pedido

    def _inserirPedido(self, pedido):
        """INSERT do pedido; o id gerado vai para o objeto"""
        sql = (
            "INSERT INTO pedido (id_cliente, id_endereco_entrega, data_criacao, data_entrega_ou_retirada, "
            "valor_total, taxa_entrega, status, status_pagamento, tipo_entrega, motivo_cancelamento, "
            "rastreamento, observacoes, forma_pagamento_sinal, forma_pagamento_restante, nome_recebedor) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "RETURNING id_pedido"
        )
        pagamento = pedido.pagamento
        parametros = (
            pedido.cliente_id, pedido.endereco_id, pedido.data_criacao, pedido.data_entrega_ou_retirada,
            pedido.valor_total, pedido.taxa_entrega, pedido.status.value, pagamento.status.value,
            pedido.tipo_entrega.value, pedido.motivo_cancelamento, pedido.rastreamento, pedido.observacoes,
            # Forma que pode ser None, sem if: None and ... dá None; senão, o texto do Enum
            pagamento.forma_sinal and pagamento.forma_sinal.value,
            pagamento.forma_restante and pagamento.forma_restante.value,
            pedido.nome_recebedor,
        )
        linha = self._umaLinha(sql, parametros)
        pedido.atribuirID(linha["id_pedido"])

    def _inserirItem(self, pedido, item):
        """INSERT de um item do pedido; o id gerado vai para o objeto"""
        sql = (
            "INSERT INTO item_pedido (id_produto, id_pedido, quantidade, preco_unitario, personalizacao, "
            "custo_personalizacao, desconto, observacoes, custo_unitario) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "RETURNING id_item_pedido"
        )
        parametros = (
            item.produto_id, pedido.id, item.quantidade, item.preco_unitario, item.personalizacao,
            item.custo_personalizacao, item.desconto, item.observacoes, item.custo_unitario,
        )
        linha = self._umaLinha(sql, parametros)
        item.atribuirID(linha["id_item_pedido"])

    def _inserirEscolha(self, item, escolha):
        """INSERT de uma opção escolhida (custo_cobrado = preço de UMA unidade da opção)"""
        sql = (
            "INSERT INTO opcao_escolhida (id_item_pedido, id_opcao, quantidade, custo_cobrado) "
            "VALUES (%s, %s, %s, %s)"
        )
        parametros = (item.id, escolha.opcao.id, escolha.quantidade, escolha.custo_cobrado)
        self._executar(sql, parametros)

    def atualizar(self, pedido):
        """
        Grava o que muda depois do envio: status, pagamento, taxa, motivo e rastreamento (os itens nunca mudam)
        valor_total vai junto porque a taxa de entrega pode ter mudado no orçamento
        """
        sql = (
            "UPDATE pedido SET valor_total = %s, taxa_entrega = %s, status = %s, status_pagamento = %s, "
            "forma_pagamento_sinal = %s, forma_pagamento_restante = %s, motivo_cancelamento = %s, "
            "rastreamento = %s "
            "WHERE id_pedido = %s"
        )
        pagamento = pedido.pagamento
        parametros = (
            pedido.valor_total, pedido.taxa_entrega, pedido.status.value, pagamento.status.value,
            pagamento.forma_sinal and pagamento.forma_sinal.value,
            pagamento.forma_restante and pagamento.forma_restante.value,
            pedido.motivo_cancelamento, pedido.rastreamento,
            pedido.id,
        )
        try:
            # Savepoint: se o banco recusar, desfaz só este UPDATE e a conexão continua utilizável
            with self._transacao():
                self._executar(sql, parametros)
        except CheckViolation as erro:
            raise ValidacaoError(self.MENSAGEM_PEDIDO_INVALIDO) from erro
        return pedido

    def atualizarComMovimentacoes(self, pedido, movimentacoes, repo_estoque):
        """
        Confirmação com baixa: grava o pedido e as movimentações de estoque juntos, ou nada
        Os repositórios usam a mesma conexão da requisição, então o _transacao() de dentro do
        registrarMovimentacao vira um savepoint desta transação
        """
        with self._transacao():
            self.atualizar(pedido)
            for movimentacao in movimentacoes:
                repo_estoque.registrarMovimentacao(movimentacao.insumo, movimentacao)
        return pedido
