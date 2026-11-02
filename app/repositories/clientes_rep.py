from psycopg.errors import ForeignKeyViolation, UniqueViolation

from app.exceptions import ValidacaoError
from app.repositories.usuarios_rep import RepositorioUsuarios


class RepositorioClientes(RepositorioUsuarios):
    """Grava e lista clientes e os endereços deles"""

    MENSAGEM_ENDERECO_EM_USO = "Este endereço já foi usado em um pedido e não pode ser removido."

    # Condição de cada aba da lista de clientes do painel
    FILTROS_CLIENTES = {
        "": lambda cliente: cliente.ativo,
        "vip": lambda cliente: cliente.ativo and cliente.cliente_vip,
        "inativos": lambda cliente: not cliente.ativo,
    }

    # ------------------------------------------------------------------ Leitura

    def listarClientes(self, filtro="", busca=""):
        """Clientes de uma aba, buscando pelo nome ou pelo telefone. Aba desconhecida = ativos"""
        padrao_busca = "%" + busca + "%"
        linhas = self._todasLinhas(
            "SELECT id_usuario FROM usuario "
            "WHERE perfil = 'cliente' AND (nome ILIKE %s OR telefone LIKE %s) "
            "ORDER BY nome",
            (padrao_busca, padrao_busca),
        )

        clientes = []
        for linha in linhas:
            clientes.append(self._carregarCliente(linha["id_usuario"]))

        condicao = self.FILTROS_CLIENTES.get(filtro, self.FILTROS_CLIENTES[""])
        return list(filter(condicao, clientes))

    # ------------------------------------------------------------------ Gravação

    def cadastrarCliente(self, cliente):
        """INSERT em USUARIO + CLIENTE numa transação; o id gerado vai para o objeto"""
        try:
            with self._transacao():
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

    def atualizarCliente(self, cliente):
        """
        Grava os dados do cliente (USUARIO + CLIENTE) numa transação.
        Usado pelo "meus dados" da loja e pela edição, VIP e desativar do painel
        """
        try:
            with self._transacao():
                self._executar(
                    "UPDATE usuario SET nome = %s, email = %s, telefone = %s, ativo = %s, "
                    "cpf = %s, data_nascimento = %s "
                    "WHERE id_usuario = %s",
                    (cliente.nome, cliente.email, cliente.telefone, cliente.ativo,
                     cliente.cpf_persistencia, cliente.data_nascimento, cliente.id),
                )
                self._executar(
                    "UPDATE cliente SET apelido = %s, cliente_vip = %s, instagram = %s, "
                    "restricoes_alimentares = %s, observacoes = %s, preferencias = %s "
                    "WHERE id_usuario = %s",
                    (cliente.apelido, cliente.cliente_vip, cliente.instagram,
                     cliente.restricoes_alimentares, cliente.observacoes, cliente.preferencias,
                     cliente.id),
                )
        except UniqueViolation as erro:
            # Trocar e-mail, telefone ou CPF para um que outra pessoa já usa também cai aqui
            raise ValidacaoError(self.MENSAGEM_DUPLICADO) from erro
        return cliente

    # ------------------------------------------------------------------ Endereços

    def salvarEndereco(self, endereco):
        """INSERT do endereço novo (já vinculado ao cliente); o id gerado vai para o objeto"""
        linha = self._umaLinha(
            "INSERT INTO endereco (id_cliente, apelido, logradouro, numero, complemento, bairro, cidade, cep) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
            "RETURNING id_endereco",
            (endereco.id_cliente, endereco.apelido, endereco.logradouro, endereco.numero,
             endereco.complemento, endereco.bairro, endereco.cidade, endereco.cep),
        )
        endereco.atribuirID(linha["id_endereco"])
        return endereco

    def removerEndereco(self, endereco):
        """DELETE do endereço. Se algum pedido usou esse endereço, o banco recusa e vira ValidacaoError"""
        try:
            self._executar("DELETE FROM endereco WHERE id_endereco = %s", (endereco.id,))
        except ForeignKeyViolation as erro:
            raise ValidacaoError(self.MENSAGEM_ENDERECO_EM_USO) from erro
