"""
app / repositories / produtos_rep.py

Acesso às tabelas PRODUTO e OPCAO_PERSONALIZACAO
"""
from typing import Any

from psycopg.errors import CheckViolation

from app.exceptions import ValidacaoError
from app.models import OpcaoPersonalizacao, Produto
from app.repositories.base import RepositorioBase


class RepositorioProdutos(RepositorioBase):
    """Busca e grava produtos, já com as opções de personalização"""

    # Mensagens usadas quando o banco recusa um valor por causa de um CHECK
    MENSAGEM_PRODUTO_INVALIDO = (
        "Algum valor do produto não é aceito. Confira a disponibilidade "
        "(pronta entrega ou encomenda), a antecedência e o percentual de perda."
    )
    MENSAGEM_OPCAO_INVALIDA = "Algum valor da opção de personalização não é aceito."

    def listar(self, disponibilidade: object = None, busca: object = "", ativos: object = True) -> list[Any]:
        """
        Produtos filtrados, em ordem de nome, cada um com as suas opções

        disponibilidade: None (todas), "pronta_entrega" ou "encomenda"
        busca: texto que o nome precisa conter ("" = sem filtro)
        ativos: True só os ativos (loja); False todos (painel)
        """
        padrao_busca = "%" + busca + "%"

        sql = (
            "SELECT * FROM produto "
            "WHERE (%s::text IS NULL OR disponibilidade = %s) "
            "AND nome ILIKE %s "
            "AND (ativo OR NOT %s) "
            "ORDER BY nome"
        )
        parametros = (disponibilidade, disponibilidade, padrao_busca, ativos)
        linhas = self._todasLinhas(sql, parametros)

        produtos = []
        for linha in linhas:
            produto = Produto(**linha)
            produtos.append(produto)

        self._carregarOpcoes(produtos)
        return produtos

    def buscarPorId(self, id_produto):
        """Produto com essa PK, já com as opções (ativas e inativas), ou None. Usado no painel"""
        sql = "SELECT * FROM produto WHERE id_produto = %s"
        parametros = (id_produto,)
        linha = self._umaLinha(sql, parametros)

        return linha and self._montarProduto(linha)

    def buscarAtivo(self, id_produto: object) -> Produto | Any:
        """Igual ao buscarPorId, mas produto desativado volta None. Usado na loja"""
        sql = "SELECT * FROM produto WHERE id_produto = %s AND ativo"
        parametros = (id_produto,)
        linha = self._umaLinha(sql, parametros)
        return linha and self._montarProduto(linha)

    def _montarProduto(self, linha):
        """Cria o Produto a partir da linha e carrega as opções dele"""
        produto = Produto(**linha)
        # _carregarOpcoes espera uma lista: aqui é uma lista com um produto só
        lista_com_um = [produto]
        self._carregarOpcoes(lista_com_um)
        return produto

    def _carregarOpcoes(self, produtos):
        """Uma consulta só para as opções de todos os produtos da lista"""
        # 1) Dicionário id -> produto, para achar o dono de cada opção sem percorrer a lista
        produtos_por_id = {}
        for produto in produtos:
            produtos_por_id[produto.id] = produto

        # 2) Lista só com os ids, que vai no ANY(%s) do SQL
        ids = []
        for id_produto in produtos_por_id:
            ids.append(id_produto)

        # 3) Busca as opções de todos esses produtos de uma vez
        sql = "SELECT * FROM opcao_personalizacao WHERE id_produto = ANY(%s) ORDER BY id_opcao"
        parametros = (ids,)
        linhas = self._todasLinhas(sql, parametros)

        # 4) Para cada opção: descobre o dono, cria o objeto e vincula ao produto
        for linha in linhas:
            # pop tira a FK do dicionário (não é parâmetro da OpcaoPersonalizacao) e devolve o valor
            id_dono = linha.pop("id_produto")
            dono = produtos_por_id[id_dono]
            opcao = OpcaoPersonalizacao(**linha)
            dono.adicionarOpcao(opcao)

    def salvar(self, produto):
        """
        Grava o produto: INSERT se ele ainda não tem id, UPDATE se já tem

        Não grava as opções: cada opção é salva com salvarOpcao
        """

        acoes = {
            True: self._inserirProduto,
            False: self._atualizarProduto,
        }
        eh_novo = produto.id is None
        acao = acoes[eh_novo]
        try:
            acao(produto)
        except CheckViolation as erro:
            # O Produto aceita qualquer texto em disponibilidade, o banco só aceita
            # 'pronta_entrega' e 'encomenda': o CHECK do banco é quem barra
            raise ValidacaoError(self.MENSAGEM_PRODUTO_INVALIDO) from erro
        return produto

    def _inserirProduto(self, produto):
        """INSERT do produto novo; o banco gera o id e ele é guardado no objeto"""
        sql = (
            "INSERT INTO produto (nome, descricao, disponibilidade, preco_base, custo_mao_de_obra, "
            "margem_lucro, tamanho, caminho_foto, ativo, antecedencia_horas, custo_embalagem, "
            "custo_indireto, percentual_perda) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "RETURNING id_produto"
        )
        parametros = (
            produto.nome, produto.descricao, produto.disponibilidade, produto.preco_base,
            produto.custo_mao_de_obra, produto.margem_lucro, produto.tamanho,
            produto.caminho_foto, produto.ativo, produto.antecedencia_horas,
            produto.custo_embalagem, produto.custo_indireto, produto.percentual_perda,
        )
        linha = self._umaLinha(sql, parametros)
        produto.atribuirID(linha["id_produto"])

    def _atualizarProduto(self, produto):
        """UPDATE de todos os campos do produto que já existe"""
        sql = (
            "UPDATE produto SET nome = %s, descricao = %s, disponibilidade = %s, preco_base = %s, "
            "custo_mao_de_obra = %s, margem_lucro = %s, tamanho = %s, caminho_foto = %s, "
            "ativo = %s, antecedencia_horas = %s, custo_embalagem = %s, custo_indireto = %s, "
            "percentual_perda = %s "
            "WHERE id_produto = %s"
        )
        # Mesma ordem do SET, e o id por último (é o %s do WHERE)
        parametros = (
            produto.nome, produto.descricao, produto.disponibilidade, produto.preco_base,
            produto.custo_mao_de_obra, produto.margem_lucro, produto.tamanho,
            produto.caminho_foto, produto.ativo, produto.antecedencia_horas,
            produto.custo_embalagem, produto.custo_indireto, produto.percentual_perda,
            produto.id,
        )
        self._executar(sql, parametros)

    def salvarOpcao(self, opcao):
        """
        Grava uma opção de personalização: INSERT se ainda não tem id, UPDATE se já tem

        A opção precisa já estar vinculada a um produto salvo (produto.adicionarOpcao + salvar)
        """
        acoes = {
            True: self._inserirOpcao,
            False: self._atualizarOpcao,
        }
        eh_nova = opcao.id is None
        acao = acoes[eh_nova]
        try:
            acao(opcao)
        except CheckViolation as erro:
            raise ValidacaoError(self.MENSAGEM_OPCAO_INVALIDA) from erro
        return opcao

    def _inserirOpcao(self, opcao):
        """INSERT da opção nova, ligada ao produto dono pelo produto_id"""
        sql = (
            "INSERT INTO opcao_personalizacao (id_produto, nome, descricao, custo_adicional, ativo) "
            "VALUES (%s, %s, %s, %s, %s) "
            "RETURNING id_opcao"
        )
        parametros = (
            opcao.produto_id, opcao.nome, opcao.descricao, opcao.custo_adicional, opcao.ativo,
        )
        linha = self._umaLinha(sql, parametros)
        opcao.atribuirID(linha["id_opcao"])

    def _atualizarOpcao(self, opcao):
        """UPDATE da opção que já existe (o produto dono não muda)"""
        sql = (
            "UPDATE opcao_personalizacao SET nome = %s, descricao = %s, custo_adicional = %s, ativo = %s "
            "WHERE id_opcao = %s"
        )
        parametros = (opcao.nome, opcao.descricao, opcao.custo_adicional, opcao.ativo, opcao.id)
        self._executar(sql, parametros)
