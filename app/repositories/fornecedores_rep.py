"""
app / repositories / fornecedores_rep.py

Acesso à tabela FORNECEDOR
"""
from psycopg.errors import UniqueViolation

from app.exceptions import ValidacaoError
from app.models import Fornecedor
from app.repositories.base import RepositorioBase


class RepositorioFornecedores(RepositorioBase):
    """Busca e grava fornecedores. Fornecedor não é apagado: é desativado (alternarAtivo)"""

    MENSAGEM_CNPJ_REPETIDO = "Já existe um fornecedor com esse CNPJ."

    # Abas da tela de fornecedores: "" = ativos, "inativos" = desativados
    FILTROS = {
        "": True,
        "inativos": False,
    }

    def listar(self, filtro=""):
        ativo = self.FILTROS.get(filtro, self.FILTROS[""])
        linhas = self._todasLinhas(
            "SELECT * FROM fornecedor WHERE ativo = %s ORDER BY nome",
            (ativo,),
        )

        fornecedores = []
        for linha in linhas:
            # As colunas têm os mesmos nomes dos parâmetros do construtor
            fornecedores.append(Fornecedor(**linha))
        return fornecedores

    def buscarPorId(self, id_fornecedor):
        """Fornecedor com essa PK, ou None"""
        linha = self._umaLinha(
            "SELECT * FROM fornecedor WHERE id_fornecedor = %s",
            (id_fornecedor,),
        )
        # `and`: sem linha (None) devolve None; com linha, monta o fornecedor
        return linha and Fornecedor(**linha)

    def salvar(self, fornecedor):
        """Grava o fornecedor: INSERT se ainda não tem id, UPDATE se já tem"""
        acoes = {
            True: self._inserir,
            False: self._atualizar,
        }
        try:
            # A transação vira savepoint se já houver uma aberta (nos testes), então
            # o erro desfaz só este comando e a conexão continua utilizável
            with self._transacao():
                acoes[fornecedor.id is None](fornecedor)
        except UniqueViolation as erro:
            # O único UNIQUE da tabela é o cnpj
            raise ValidacaoError(self.MENSAGEM_CNPJ_REPETIDO) from erro
        return fornecedor

    def _inserir(self, fornecedor):
        """INSERT do fornecedor novo; o banco gera o id e ele é guardado no objeto"""
        sql = (
            "INSERT INTO fornecedor (nome, telefone, endereco, email, cnpj, contato_principal, ativo) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) "
            "RETURNING id_fornecedor"
        )
        parametros = (
            fornecedor.nome, fornecedor.telefone, fornecedor.endereco, fornecedor.email,
            fornecedor.cnpj, fornecedor.contato_principal, fornecedor.ativo,
        )
        linha = self._umaLinha(sql, parametros)
        fornecedor.atribuirID(linha["id_fornecedor"])

    def _atualizar(self, fornecedor):
        """UPDATE de todos os campos do fornecedor que já existe (inclusive ativo, para desativar/reativar)"""
        sql = (
            "UPDATE fornecedor SET nome = %s, telefone = %s, endereco = %s, email = %s, "
            "cnpj = %s, contato_principal = %s, ativo = %s "
            "WHERE id_fornecedor = %s"
        )
        parametros = (
            fornecedor.nome, fornecedor.telefone, fornecedor.endereco, fornecedor.email,
            fornecedor.cnpj, fornecedor.contato_principal, fornecedor.ativo,
            fornecedor.id,
        )
        self._executar(sql, parametros)
