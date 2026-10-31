"""
app / repositories / usuarios_rep.py

Acesso às tabelas USUARIO, CLIENTE, FUNCIONARIO, ADMINISTRADOR e ENDERECO
"""

from psycopg.errors import UniqueViolation

from app.exceptions import ValidacaoError
from app.models import Cliente, Endereco, Senha, Funcionario, Administrador
from app.repositories.base import RepositorioBase


class RepositorioUsuarios(RepositorioBase):
    """Busca e grava usuários, montando o objeto do perfil certo"""

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
        """USUARIO + FUNCIONARIO numa linha só"""
        linha = self._umaLinha(
            "SELECT * FROM usuario JOIN funcionario USING (id_usuario) WHERE id_usuario = %s",
            (id_usuario,),
        )
        return Funcionario(**self._camposDeUsuario(linha))

    def _carregarAdministrador(self, id_usuario):
        """USUARIO + ADMINISTRADOR numa linha só"""
        linha = self._umaLinha(
            "SELECT * FROM usuario JOIN administrador USING (id_usuario) WHERE id_usuario = %s",
            (id_usuario,),
        )
        return Administrador(**self._camposDeUsuario(linha))

    @staticmethod
    def _camposDeUsuario(linha):
        """Adapta a linha do banco aos parâmetros do construtor"""
        # perfil escolhe a classe, não é parâmetro dela
        linha.pop("perfil")
        hash_senha = linha.pop("senha_hash")
        # NULL no banco vira None, e o Usuario usa a SenhaAusente
        linha["senha"] = hash_senha and Senha.deHash(hash_senha)
        return linha

    # Mensagem usada quando o banco recusa por e-mail, telefone ou CPF repetido (colunas UNIQUE)
    MENSAGEM_DUPLICADO = "Já existe uma conta com este e-mail, telefone ou CPF."

    def cadastrarCliente(self, cliente):
        try:
            with self._obter_conexao().transaction():
                linha = self._umaLinha(
                    "INSERT INTO usuario (nome, email, telefone, senha_hash, data_cadastro, ativo, cpf, data_nascimento, perfil) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'cliente') RETURNING id_usuario",
                    (cliente.nome, cliente.email, cliente.telefone, cliente.senha_hash, cliente.data_cadastro,
                     cliente.ativo, cliente.cpf_persistencia, cliente.data_nascimento),
                )
                cliente.atribuirID(linha["id_usuario"])
                self._executar(
                    "INSERT INTO cliente (id_usuario, apelido, cliente_vip, instagram, restricoes_alimentares, observacoes, preferencias) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (cliente.id, cliente.apelido, cliente.cliente_vip, cliente.instagram,
                     cliente.restricoes_alimentares, cliente.observacoes, cliente.preferencias),
                )
        except UniqueViolation as erro:
            # O with já fez ROLLBACK; aqui só troca o erro do banco por um erro do projeto
            raise ValidacaoError(self.MENSAGEM_DUPLICADO) from erro
        return cliente

    def cadastrarFuncionario(self, funcionario):
        try:
            with self._obter_conexao().transaction():
                linha = self._umaLinha(
                    "INSERT INTO usuario (nome, email, telefone, senha_hash, data_cadastro, ativo, cpf, data_nascimento, perfil) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'funcionario') RETURNING id_usuario",
                    (funcionario.nome, funcionario.email, funcionario.telefone, funcionario.senha_hash,
                     funcionario.data_cadastro,
                     funcionario.ativo, funcionario.cpf_persistencia, funcionario.data_nascimento),
                )
                funcionario.atribuirID(linha["id_usuario"])
                self._executar("INSERT INTO funcionario (id_usuario, cargo, data_contratacao) "
                               "VALUES (%s, %s, %s)",
                               (funcionario.id, funcionario.cargo, funcionario.data_contratacao))
        except UniqueViolation as erro:
            raise ValidacaoError(self.MENSAGEM_DUPLICADO) from erro
        return funcionario

    def cadastrarAdministrador(self, administrador):
        try:
            with self._obter_conexao().transaction():
                linha = self._umaLinha(
                    "INSERT INTO usuario (nome, email, telefone, senha_hash, data_cadastro, ativo, cpf, data_nascimento, perfil) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'administrador') RETURNING id_usuario",
                    (administrador.nome, administrador.email, administrador.telefone, administrador.senha_hash,
                     administrador.data_cadastro,
                     administrador.ativo, administrador.cpf_persistencia, administrador.data_nascimento),
                )
                administrador.atribuirID(linha["id_usuario"])
                self._executar("INSERT INTO administrador (id_usuario, nivel_privilegio, acesso_financeiro) "
                               "VALUES (%s, %s, %s)",
                               (administrador.id, administrador.nivel_privilegio, administrador.acesso_financeiro))
        except UniqueViolation as erro:
            raise ValidacaoError(self.MENSAGEM_DUPLICADO) from erro
        return administrador

    def atualizarCliente(self, cliente):
        try:
            with self._obter_conexao().transaction():
                self._executar(
                    "UPDATE usuario SET nome = %s, email = %s, telefone = %s, ativo = %s, data_nascimento = %s "
                    "WHERE id_usuario = %s",
                    (cliente.nome, cliente.email, cliente.telefone, cliente.ativo,
                     cliente.data_nascimento, cliente.id),
                )
                self._executar(
                    "UPDATE cliente SET apelido = %s, instagram = %s, restricoes_alimentares = %s, "
                    "observacoes = %s, preferencias = %s "
                    "WHERE id_usuario = %s",
                    (cliente.apelido, cliente.instagram, cliente.restricoes_alimentares,
                     cliente.observacoes, cliente.preferencias, cliente.id),
                )
        except UniqueViolation as erro:
            # Trocar o e-mail ou telefone para um que outra pessoa já usa também cai aqui
            raise ValidacaoError(self.MENSAGEM_DUPLICADO) from erro
        return cliente

    def atualizarSenha(self, usuario):
        self._executar(
            "UPDATE usuario SET senha_hash = %s WHERE id_usuario = %s",
            (usuario.senha_hash, usuario.id),
        )
