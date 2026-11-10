"""
app / repositories / receitas_rep.py

Acesso aas tabelas RECEITA e ITEM_RECEITA

"""
from psycopg.errors import UniqueViolation

from app.exceptions import ValidacaoError
from app.models import Receita, ItemReceita
from app.repositories.base import RepositorioBase


class RepositorioReceita(RepositorioBase):

    def listar(self, filtro_ativas, busca):
        sql = (
            "SELECT * FROM receita "
            "WHERE ativa = %s "
            "AND COALESCE(nome, '') ILIKE '%%' || %s || '%%' "
            "ORDER BY nome"
        )
        parametros = (filtro_ativas, busca)
        self._todasLinhas(sql, parametros)

        linhas = self._todasLinhas(sql, parametros)
        linhas(sql, )

        receitas = []
        for linha in linhas:
            receita = Receita(**linha)
            receitas.append(receita)

        return receitas

    def _insumosPorId(self, estoque):
        """Dicionário id -> insumo, com os mesmos objetos que estão dentro do estoque"""
        insumos_por_id = {}
        for insumo in estoque.insumos:
            insumos_por_id[insumo.id] = insumo
        return insumos_por_id

    def _montarReceitas(self, linhas, estoque):
        """
        Cria as Receitas a partir das linhas de RECEITA, na mesma ordem, cada uma com os seus ingredientes
        Os insumos vêm de dentro do `estoque`, para serem os mesmos objetos que o Estoque conhece (ele compara com `is`)
        """
        receitas = []
        receitas_por_id = {}
        for linha in linhas:
            receita = Receita(**linha)
            receitas.append(receita)
            receitas_por_id[receita.id] = receita

        insumos_por_id = self._insumosPorId(estoque)

        ids = []
        for id_receita in receitas_por_id:
            ids.append(id_receita)

        sql = "SELECT * FROM item_receita WHERE id_receita = ANY(%s) ORDER BY id_item_receita"
        parametros = (ids,)
        linhas_itens = self._todasLinhas(sql, parametros)

        for linha in linhas_itens:
            id_receita = linha.pop("id_receita")
            id_insumo = linha.pop("id_insumo")
            insumo = insumos_por_id[id_insumo]
            item = ItemReceita(insumo, **linha)
            receitas_por_id[id_receita].adicionarItem(item)

        return receitas

    # Abas da tela de receitas (painel/receitas.html): "" = ativas, "inativas" = fora de uso
    FILTROS = {
        "": lambda receita: receita.ativa,
        "inativas": lambda receita: not receita.ativa,
    }

    def listar(self, estoque, filtro="", busca=""):
        """Receitas de uma aba da tela, com busca pelo nome, em ordem de nome. Aba desconhecida = ativas"""
        sql = "SELECT * FROM receita WHERE COALESCE(nome, '') ILIKE %s ORDER BY nome"
        parametros = ("%" + busca + "%",)
        linhas = self._todasLinhas(sql, parametros)
        receitas = self._montarReceitas(linhas, estoque)

        # Escolhe a condição da aba (sem if); filtro desconhecido cai no padrão
        condicao = self.FILTROS.get(filtro, self.FILTROS[""])
        resultado = []

        for receita in receitas:
            if condicao(receita):
                resultado.append(receita)
        return resultado

    def buscarPorId(self, id_receita, estoque):
        """Receita com essa PK, já com os ingredientes, ou None"""
        sql = "SELECT * FROM receita WHERE id_receita = %s"
        parametros = (id_receita,)
        linha = self._umaLinha(sql, parametros)

        return linha and self._montarReceitas([linha], estoque)[0]

    def buscarVarias(self, ids, estoque):
        """Dicionário id -> Receita com as receitas desses ids (ativas e inativas). Lista vazia = {}"""
        sql = "SELECT * FROM receita WHERE id_receita = ANY(%s)"
        parametros = (list(ids),)
        linhas = self._todasLinhas(sql, parametros)

        receitas_por_id = {}
        for receita in self._montarReceitas(linhas, estoque):
            receitas_por_id[receita.id] = receita
        return receitas_por_id

    MENSAGEM_INSUMO_REPETIDO = "Um mesmo insumo aparece duas vezes nesta receita."

    def salvar(self, receita):
        """Grava a receita (nova ou existente) e substitui todos os ingredientes dela, numa transação só"""
        acoes = {True: self._inserir,
                 False: self._atualizar}

        try:
            with self._transacao():
                acoes[receita.id is None](receita)
                self._gravarItens(receita)
        except UniqueViolation as erro:
            # uq_receita_insumo: o mesmo insumo duas vezes na receita. O `with` já desfez tudo
            raise ValidacaoError(self.MENSAGEM_INSUMO_REPETIDO) from erro
        return receita

    def _inserir(self, receita):
        """INSERT da receita nova; o banco gera o id e ele é guardado no objeto"""
        sql = (
            "INSERT INTO receita (nome, modo_preparo, tempo_preparo, rendimento_qtd, rendimento_un, "
            "complexidade, data_criacao, ativa) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
            "RETURNING id_receita"
        )
        parametros = (
            receita.nome, receita.modo_preparo, receita.tempo_preparo, receita.rendimento_qtd,
            receita.rendimento_un, receita.complexidade, receita.data_criacao, receita.ativa,
        )
        linha = self._umaLinha(sql, parametros)
        receita.atribuirID(linha["id_receita"])

    def _atualizar(self, receita):
        """UPDATE dos campos da receita que já existe. A data_criacao não muda"""
        sql = (
            "UPDATE receita SET nome = %s, modo_preparo = %s, tempo_preparo = %s, rendimento_qtd = %s, "
            "rendimento_un = %s, complexidade = %s, ativa = %s "
            "WHERE id_receita = %s"
        )
        parametros = (
            receita.nome, receita.modo_preparo, receita.tempo_preparo, receita.rendimento_qtd,
            receita.rendimento_un, receita.complexidade, receita.ativa, receita.id,
        )
        self._executar(sql, parametros)

    def _gravarItens(self, receita):
        """
        Apaga os ingredientes gravados e insere os da receita
        Item novo (sem id) ganha id da sequência; item que veio do banco volta com o mesmo id
        """
        self._executar("DELETE FROM item_receita WHERE id_receita = %s", (receita.id,))

        sql = (
            "INSERT INTO item_receita (id_item_receita, id_insumo, id_receita, quantidade_necessaria, observacoes) "
            "VALUES (COALESCE(%s, nextval(pg_get_serial_sequence('item_receita', 'id_item_receita'))), %s, %s, %s, %s) "
            "RETURNING id_item_receita"
        )
        for item in receita.itens:
            parametros = (item.id, item.insumo_id, receita.id, item.quantidade_necessaria, item.observacoes)
            linha = self._umaLinha(sql, parametros)
            # Só o item novo recebe o id; o que já tinha continua com o dele
            atribuir = {True: item.atribuirID, False: lambda id_gerado: None}
            atribuir[item.id is None](linha["id_item_receita"])
