from decimal import Decimal


class Carrinho:
    """O carrinho guardado na sessão: uma lista de linhas em sessao["carrinho"]"""

    CHAVE = "carrinho"

    def __init__(self, sessao):
        """Recebe a session do Flask (ou um dict comum, nos testes)"""
        self._sessao = sessao

    @property
    def linhas(self):
        """As linhas do carrinho (lista vazia se ainda não tem nada)"""
        return self._sessao.get(self.CHAVE, [])

    def adicionar(self, produto_id, quantidade, opcoes, observacoes):
        """Acrescenta uma linha no fim do carrinho"""
        nova_linha = {
            "produto_id": produto_id,
            "quantidade": quantidade,
            "opcoes": opcoes,
            "observacoes": observacoes,
        }
        linhas_novas = self.linhas + [nova_linha]  # lista NOVA: antigas + a nova
        self._sessao[self.CHAVE] = linhas_novas  # atribui no 1º nível → o Flask percebe

    def atualizar(self, indice, quantidade):
        """Troca a quantidade da linha `indice`. Quantidade 0 remove a linha (IndexError se não existir)"""
        linha_antiga = self.linhas[indice]

        nova_linha = {
            "produto_id": linha_antiga["produto_id"],
            "quantidade": quantidade,
            "opcoes": linha_antiga["opcoes"],
            "observacoes": linha_antiga["observacoes"],
        }

        linhas_novas = list(self.linhas)
        linhas_novas[indice] = nova_linha

        linhas_com_itens = []
        for linha in linhas_novas:
            if linha["quantidade"] > 0:
                linhas_com_itens.append(linha)

        self._sessao[self.CHAVE] = linhas_com_itens

    def remover(self, indice):
        """Tira a linha `indice` do carrinho (IndexError se não existir)"""
        linhas_novas = list(self.linhas)
        linhas_novas.pop(indice)
        self._sessao[self.CHAVE] = linhas_novas

    def quantidadeDeItens(self):
        """Total de unidades no carrinho (para o número no ícone do menu)"""
        total = 0
        for linha in self.linhas:
            total = total + linha["quantidade"]
        return total

    def esvaziar(self):
        """Tira tudo do carrinho (depois que o pedido é enviado)"""
        self._sessao[self.CHAVE] = []

    def montarCarrinho(self, repo_produtos):
        """
        O que a tela do carrinho precisa: cada linha com o Produto, as opções e o subtotal,
        e o subtotal geral. Os preços são recalculados aqui (nunca ficam na sessão)
        """
        itens = []
        subtotal_geral = Decimal("0")

        for linha in self.linhas:
            # 1) O produto, já com as suas opções
            produto = repo_produtos.buscarAtivo(linha["produto_id"])

            # 2) Dicionário id -> opção, para trocar os ids da sessão pelos objetos
            opcoes_por_id = {}
            for opcao in produto.opcoes:
                opcoes_por_id[opcao.id] = opcao

            # 3) Cada opção da linha é [id, quantidade]
            opcoes_para_preco = []  # para o calcularPreco: a opção repetida N vezes
            opcoes_para_tela = []  # para o template: nome, quantidade e custo
            for id_opcao, quantidade_opcao in linha["opcoes"]:
                opcao = opcoes_por_id[id_opcao]
                opcoes_para_preco = opcoes_para_preco + ([opcao] * quantidade_opcao)
                opcoes_para_tela.append({
                    "nome": opcao.nome,
                    "quantidade": quantidade_opcao,
                    "custo": opcao.custo_adicional * quantidade_opcao,
                })

            # 4) Preço de uma unidade (base + opções) e subtotal do item
            preco_unitario = produto.calcularPreco(opcoes_para_preco)
            subtotal_item = preco_unitario * linha["quantidade"]

            # 5) O item no formato que o carrinho.html espera
            itens.append({
                "produto": produto,
                "quantidade": linha["quantidade"],
                "opcoes": opcoes_para_tela,
                "observacoes": linha["observacoes"],
                "subtotal": subtotal_item,
            })
            subtotal_geral = subtotal_geral + subtotal_item

        return {"itens": itens, "subtotal": subtotal_geral}
