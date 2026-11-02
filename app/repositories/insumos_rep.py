from typing import Any

from psycopg.errors import UniqueViolation

from app.exceptions import ValidacaoError
from app.models import Insumo, MovimentacaoEstoque
from app.repositories.base import RepositorioBase


class RepositorioInsumos(RepositorioBase):
    """Busca e grava insumos e as movimentações do estoque"""

    MENSAGEM_NOME_REPETIDO = "Já existe um insumo com este nome."

    def listar(self) -> list[Any]:
        """Todos os insumos (ativos e inativos), em ordem de nome. O Estoque filtra e ordena por tipo"""
        linhas = self._todasLinhas("SELECT * FROM insumo ORDER BY nome", ())
        insumos = []
        for linha in linhas:
            insumo = Insumo(**linha)
            insumos.append(insumo)
        return insumos

    def buscarPorId(self, id_insumo):
        """Insumo com essa PK, ou None"""
        linha = self._umaLinha("SELECT * FROM insumo WHERE id_insumo = %s", (id_insumo,))
        # `and`: sem linha (None) devolve None; com linha, monta o insumo
        return linha and Insumo(**linha)

    FILTROS = {
        "": lambda insumo: insumo.ativo,
        "ingrediente": lambda insumo: insumo.ativo and insumo.tipo.value == "ingrediente",
        "embalagem": lambda insumo: insumo.ativo and insumo.tipo.value == "embalagem",
        "decoracao": lambda insumo: insumo.ativo and insumo.tipo.value == "decoracao",
        "baixo": lambda insumo: insumo.ativo and insumo.abaixo_do_minimo,
        "inativos": lambda insumo: not insumo.ativo,
    }

    def listarComFiltro(self, filtro="", busca=""):
        """Insumos de uma aba da tela de estoque, com busca por nome. Aba desconhecida = "Todos" """
        sql = "SELECT * FROM insumo WHERE nome ILIKE %s ORDER BY nome"
        parametros = ("%" + busca + "%",)
        linhas = self._todasLinhas(sql, parametros)

        insumos = []
        for linha in linhas:
            insumos.append(Insumo(**linha))

        # Escolhe a condição da aba (sem if); filtro desconhecido cai no padrão
        condicao = self.FILTROS.get(filtro, self.FILTROS[""])
        return list(filter(condicao, insumos))

    def buscarMovimentacao(self, id_movimentacao, estoque):
        """
        Movimentação com essa PK, ou None, ligada ao MESMO objeto Insumo que está no `estoque`

        O Estoque confere com `is` se o insumo da movimentação é um dos dele: um Insumo
        carregado à parte (outro objeto, mesmo com o mesmo id) seria recusado
        """
        linha = self._umaLinha(
            "SELECT * FROM movimentacao_estoque WHERE id_movimentacao_estoque = %s",
            (id_movimentacao,),
        )
        return linha and self._montarMovimentacao(linha, estoque)

    def _montarMovimentacao(self, linha, estoque):
        """Troca os nomes das colunas pelos parâmetros do construtor e pega o insumo do estoque"""
        insumos_por_id: dict[int, object] = {}
        for insumo in estoque.insumos:
            insumos_por_id[insumo.id] = insumo

        return MovimentacaoEstoque(
            insumo=insumos_por_id[linha["id_insumo"]],
            tipo=linha["tipo"],
            quantidade=linha["quantidade"],
            motivo=linha["motivo"],
            id_pedido=linha["id_pedido"],
            id_compra=linha["id_compra_insumo"],
            data=linha["data"],
            id_movimentacao=linha["id_movimentacao_estoque"],
        )

    def salvar(self, insumo):
        """
        Grava o cadastro do insumo: INSERT se ainda não tem id, UPDATE se já tem

        O UPDATE não toca no saldo: quantidade muda só por registrarMovimentacao
        """
        acoes = {
            True: self._inserir,
            False: self._atualizar,
        }
        eh_novo = insumo.id is None
        acao = acoes[eh_novo]
        try:
            acao(insumo)
        except UniqueViolation as erro:
            raise ValidacaoError(self.MENSAGEM_NOME_REPETIDO) from erro
        return insumo

    def _inserir(self, insumo):
        """INSERT do insumo novo (único momento em que a quantidade vem do formulário)"""
        sql = (
            "INSERT INTO insumo (nome, unidade_medida, quantidade_atual, estoque_minimo, custo_por_unidade, "
            "data_atualizacao, unidade_receita, fator_conversao, tipo, ativo) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "RETURNING id_insumo"
        )
        parametros = (
            insumo.nome, insumo.unidade_medida, insumo.quantidade_atual, insumo.estoque_minimo,
            insumo.custo_por_unidade, insumo.data_atualizacao, insumo.unidade_receita,
            insumo.fator_conversao, insumo.tipo.value, insumo.ativo,
        )
        linha = self._umaLinha(sql, parametros)
        insumo.atribuirID(linha["id_insumo"])

    def _atualizar(self, insumo):
        """UPDATE do cadastro (sem quantidade_atual e sem data_atualizacao, que são do saldo)"""
        sql = (
            "UPDATE insumo SET nome = %s, unidade_medida = %s, estoque_minimo = %s, custo_por_unidade = %s, "
            "unidade_receita = %s, fator_conversao = %s, tipo = %s, ativo = %s "
            "WHERE id_insumo = %s"
        )
        parametros = (
            insumo.nome, insumo.unidade_medida, insumo.estoque_minimo, insumo.custo_por_unidade,
            insumo.unidade_receita, insumo.fator_conversao, insumo.tipo.value, insumo.ativo,
            insumo.id,
        )
        self._executar(sql, parametros)

    def registrarMovimentacao(self, insumo, movimentacao):
        """
        Grava o saldo novo do insumo E a movimentação que causou a mudança, juntos:
        ou os dois ficam no banco, ou nenhum. O id gerado vai para a movimentação
        """
        with self._transacao():
            self._executar(
                "UPDATE insumo SET quantidade_atual = %s, data_atualizacao = %s WHERE id_insumo = %s",
                (insumo.quantidade_atual, insumo.data_atualizacao, insumo.id),
            )
            linha = self._umaLinha(
                "INSERT INTO movimentacao_estoque (id_insumo, tipo, quantidade, data, motivo, id_pedido, id_compra_insumo) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                "RETURNING id_movimentacao_estoque",
                (
                    insumo.id, movimentacao.tipo.value, movimentacao.quantidade, movimentacao.data,
                    movimentacao.motivo, movimentacao.id_pedido, movimentacao.id_compra,
                ),
            )
        movimentacao.atribuirID(linha["id_movimentacao_estoque"])
        return movimentacao
