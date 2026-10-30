"""
app / repositories / usuarios.py

Acesso às tabelas USUARIO, CLIENTE, FUNCIONARIO, ADMINISTRADOR e ENDERECO
"""

from psycopg.rows import dict_row

from app.models import Cliente, Endereco, Senha


class RepositorioUsuarios:
    """Busca e grava usuários, montando o objeto do perfil certo"""

    def __init__(self, obter_conexao):
        """Recebe a função que devolve a conexão da requisição"""
        self._obter_conexao = obter_conexao

    def buscarPorEmail(self, email):
        """Usuário com esse e-mail (já em minúsculas) ou None. É o contrato que a Autenticacao espera"""
        linha = self._umaLinha("SELECT id_usuario, perfil FROM usuario WHERE email = %s", (email,))
        return linha and self._carregar(linha)

    def buscarPorId(self, id_usuario):
        """Usuário com essa PK ou None (usado para transformar o token no usuário logado)"""
        linha = self._umaLinha("SELECT id_usuario, perfil FROM usuario WHERE id_usuario = %s", (id_usuario,))
        return linha and self._carregar(linha)

    # Montagem por perfil
    def _carregar(self, linha):
        """Escolhe quem monta o objeto pela coluna perfil (Factory por dicionário, sem if)"""
        carregadores = {
            "cliente": self._carregarCliente,
            "funcionario": self._carregarFuncionario,
            "administrador": self._carregarAdministrador,
        }
        return carregadores[linha["perfil"]](linha["id_usuario"])

    def _carregarCliente(self, id_usuario):
        """USUARIO + CLIENTE numa linha só, depois os endereços dele"""
        linha = self._umaLinha(
            "SELECT * FROM usuario JOIN cliente USING (id_usuario) WHERE id_usuario = %s",
            (id_usuario,),
        )
        # cria objeto.
        cliente = Cliente(**self._camposDeUsuario(linha))
        for linha_endereco in self._todasLinhas(
                "SELECT * FROM endereco WHERE id_cliente = %s ORDER BY id_endereco", (id_usuario,)
        ):
            # A FK não é parâmetro do Endereco: o vínculo é feito pelo adicionarEndereco
            linha_endereco.pop("id_cliente")
            cliente.adicionarEndereco(Endereco(**linha_endereco))
        return cliente

    def _carregarFuncionario(self, id_usuario):
        pass

    def _carregarAdministrador(self, id_usuario):
        pass

    @staticmethod
    def _camposDeUsuario(linha):
        """Adapta a linha do banco aos parâmetros do construtor"""
        # perfil escolhe a classe, não é parâmetro dela
        linha.pop("perfil")
        hash_senha = linha.pop("senha_hash")
        # NULL no banco vira None, e o Usuario usa a SenhaAusente
        linha["senha"] = hash_senha and Senha.deHash(hash_senha)
        return linha

    # Execução do SQL
    def _umaLinha(self, sql, parametros):
        """Primeira linha do resultado como dicionário, ou None"""
        with self._obter_conexao().cursor(row_factory=dict_row) as cursor:
            cursor.execute(sql, parametros)
            return cursor.fetchone()

    def _todasLinhas(self, sql, parametros):
        """Todas as linhas do resultado, cada uma como dicionário"""
        with self._obter_conexao().cursor(row_factory=dict_row) as cursor:
            cursor.execute(sql, parametros)
            return cursor.fetchall()
