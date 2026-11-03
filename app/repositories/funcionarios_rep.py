"""
app / repositories / funcionarios_rep.py

O que é só de FUNCIONÁRIO: lista da equipe, cadastro e atualização

Herda do RepositorioUsuarios: buscarPorId, atualizarSenha e o _camposDeUsuario vêm de lá
"""

from psycopg.errors import UniqueViolation

from app.exceptions import ValidacaoError
from app.models import Funcionario
from app.repositories.usuarios_rep import RepositorioUsuarios


class RepositorioFuncionarios(RepositorioUsuarios):
    """Grava e lista os funcionários"""

    def listarFuncionarios(self):
        """Toda a equipe (ativos e desligados), em ordem de nome. Não inclui administradores"""
        linhas = self._todasLinhas(
            "SELECT * FROM usuario JOIN funcionario USING (id_usuario) ORDER BY nome",
            (),
        )

        funcionarios = []
        for linha in linhas:
            funcionarios.append(Funcionario(**self._camposDeUsuario(linha)))
        return funcionarios

    def cadastrarFuncionario(self, funcionario):
        """INSERT em USUARIO + FUNCIONARIO numa transação; o id gerado vai para o objeto"""
        try:
            with self._transacao():
                linha = self._umaLinha(
                    "INSERT INTO usuario (nome, email, telefone, senha_hash, data_cadastro, ativo, cpf, data_nascimento, perfil) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'funcionario') RETURNING id_usuario",
                    (funcionario.nome, funcionario.email, funcionario.telefone, funcionario.senha_hash,
                     funcionario.data_cadastro, funcionario.ativo, funcionario.cpf_persistencia,
                     funcionario.data_nascimento),
                )
                funcionario.atribuirID(linha["id_usuario"])
                self._executar(
                    "INSERT INTO funcionario (id_usuario, cargo, data_contratacao) VALUES (%s, %s, %s)",
                    (funcionario.id, funcionario.cargo, funcionario.data_contratacao),
                )
        except UniqueViolation as erro:
            raise ValidacaoError(self.MENSAGEM_DUPLICADO) from erro
        return funcionario

    def atualizarFuncionario(self, funcionario):
        """
        Grava os dados do funcionário (USUARIO + FUNCIONARIO) numa transação.
        Não mexe na senha: a troca de senha é o atualizarSenha
        """
        try:
            with self._transacao():
                self._executar(
                    "UPDATE usuario SET nome = %s, email = %s, telefone = %s, ativo = %s, "
                    "cpf = %s, data_nascimento = %s "
                    "WHERE id_usuario = %s",
                    (funcionario.nome, funcionario.email, funcionario.telefone, funcionario.ativo,
                     funcionario.cpf_persistencia, funcionario.data_nascimento, funcionario.id),
                )
                self._executar(
                    "UPDATE funcionario SET cargo = %s, data_contratacao = %s WHERE id_usuario = %s",
                    (funcionario.cargo, funcionario.data_contratacao, funcionario.id),
                )
        except UniqueViolation as erro:
            raise ValidacaoError(self.MENSAGEM_DUPLICADO) from erro
        return funcionario
