"""
app / repositories / base.py

O que todo repositório tem em comum: receber a conexão e executar SQL
"""

from psycopg.rows import dict_row


class RepositorioBase:
    """Classe mãe dos repositórios: guarda a conexão e oferece os auxiliares de SQL"""

    def __init__(self, obter_conexao):
        """Recebe a função que devolve a conexão da requisição"""
        self._obter_conexao = obter_conexao

    def _transacao(self):
        """Bloco em que os comandos são gravados juntos ou desfeitos juntos"""
        return self._obter_conexao().transaction()

    def _umaLinha(self, sql, parametros):
        """Primeira linha do resultado como dicionário, ou None"""
        with self._obter_conexao().cursor(row_factory=dict_row) as cursor:
            cursor.execute(sql, parametros)
            return cursor.fetchone()

    def _todasLinhas(self, sql, parametros):
        """Todas as dicionarios do resultado, cada uma como dicionário"""
        with self._obter_conexao().cursor(row_factory=dict_row) as cursor:
            cursor.execute(sql, parametros)
            return cursor.fetchall()

    def _executar(self, sql, parametros):
        """Executa um comando que não devolve dicionarios (INSERT sem RETURNING, UPDATE, DELETE)"""
        with self._obter_conexao().cursor() as cursor:
            cursor.execute(sql, parametros)
