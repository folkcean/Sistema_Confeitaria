"""
models / usuario.py
Módulo de usuários e acessos de Sistema de Gestão de Confeitaria

Hierarquia do DER:
    Usuário (tabela USUÁRIO)
        ├── Cliente (tabela CLIENTE - PK/FK: USUÁRIOID_usuário)
        ├── Funcionário (tabela FUNCIONÁRIO - PK/FK: USUÁRIOID_usuário)
        └── Administrador (tabela ADMINISTRADOR - PK/FK: USUÁRIOID_usuário)
    Endereço (tabela ENDEREÇO - Cliente 1:N Endereço)
"""

# importa anotacoes futuras do python
from __future__ import annotations
# nativo para ER (usado em validacoes de CPF, CEP email e telefone)
import re
# nativo para criar classes abstratas e metodos nas subclasses
from abc import ABC, abstractmethod
# manipulacao de datas
from datetime import date, datetime, timedelta
# evitar dependencia circular em tempo de execucao (A precisa de B enquanto B precisa de A)
from typing import TYPE_CHECKING

# FLASK -> criacao e validacao de tokens de sessao seguros
from itsdangerous import BadSignature, SignatureExposed, URLSafeTimeSerializer
# FLASK -> hash seguro de senhas e verificacao
from werkzeug.security import check_password_hash, generate_password_hash

from .base import (
    Entidade, AcessoNegadoError, AutenticacaoError, SenhaFracaError, StatusPedido, ValidacaoError,
    exigirTexto, textoOpcional, validarCPF, validarData, validarEmail, validarTelefone
)

# ENDEREÇO (DER: CLIENTE 1:N ENDEREÇO)
class Endereco(Entidade):
    """ 
    Representa o endereço de entrega de um cliente
    DER: ID_endereco (PK), CLIENTEUSUÁRIOID_usuário (FK), apelido (nulo), logradouro, numero, complemento (nulo), bairro, cidade, cep char(8)
    """
    def __init__(self, logradouro: str, numero: str, bairro: str, cidade: str, cep: str, complemento: str = "", apelido: str = "", id_endereco: int | None = None):   
        # Guarda a pk id_endereco
        super().__init__(id_endereco)

        self._logradouro = exigirTexto(logradouro, "logradouro")

        # Atributos protegidos (_) -> lidos por @property
        self._logradouro = exigirTexto(logradouro, "logradouro")
        self._numero = exigirTexto(numero, "número")
        self._bairro = exigirTexto(bairro, "bairro")
        self._cidade = exigirTexto(cidade, "cidade")
        self._complemento = textoOpcional(complemento, "complemento")
        self._apelido = textoOpcional(apelido, "apelido")
        
        # Validação do cep
        # \D significa tudo que não for dígito numérico -> apaga traços, pontos, letras, espaços
        digitos = re.sub(r"\D", "", cep or "")
        if len(digitos) != 8:
            raise ValidacaoError("CEP inválido: deve conter 8 dígitos.")
        self._cep = digitos

        # FK CLIENTEUSUARIOID_usuario, o cliente pode ser criado antes de ter o ID e receber-lo após o INSERT
        self._cliente: "Cliente | None" = None

    # @property -> encapsulamento, cria um tipo de atalho de leitura
    # O endereço é imutável depois de criado, para mudar deve remover e cadastrar outro
    @property
    def logradouro(self): return self._logradouro
    @property
    def numero(self): return self._numero
    @property
    def complemento(self): return self._complemento
    @property
    def bairro(self): return self._bairro
    @property
    def cidade(self): return self._cidade
    @property
    def cep(self): return self._cep
    @property
    def apelido(self): return self._apelido

    @property
    def id_cliente(self) -> int | None:
        """Novo valor da fk para a tabela CLIENTE"""
        return self._id_cliente if self._cliente else None

    def _vincular(self, cliente: "Cliente | None") -> None:
        """Uso interno, ao adicicionar ou remover um endereço de um cliente"""
        self._if_cliente = cliente

    def formatado(self) -> str:
        """Retorna o endereço formatado por extenso"""
        # verifica se o cliente digitou algum complemento, caso sim, coloca uma virgula antes, caso nao, deixa vazio
        complemento = f", {self._complemento}" if self._complemento else ""
        # junta tudo em uma frase so e formata o cep colocando o traco
        return (f"{self._logradouro}, {self._numero}{complemento} - {self._bairro}, "
                f"{self._cidade} - CEP {self._cep[:5]}-{self._cep[5:]}")

    def __repr__(self) -> str:
        """representacao do texto"""
        return f"Endereco({self.formatado()})"

class ValidadorSenha:
    """
    Classe responsável por validar a senha informada com base nos requisitos de segurança
    """
    TAM_MIN = 8

    @classmethod
    # cls eh similar ao self, ms referencia a classe toda, permite acessar constantes
    def validar(cls, senha: str) -> None:
        """Acumula todos os problemas e lança um único erro com a lista completa"""
        # cria uma lista vazia para acumular todas as falhas que a senha apresentar
        problemas = []
        # verifica se a senha esta vazia ou se o tamanho total eh menor que o minimo, caso sim, add na lista de problemas
        if senha is None or len(senha) < cls.TAMANHO_MINIMO:
            problemas.append(f"Ter ao menos {cls.TAMANHO_MINIMO} caracteres")
        # usa ERs para procurar letras maiusculas e minusculas na senha, caso nao encontre, eh disparao um erro
        # senha or "" -> se o usuario passar um valor nulo, o codigo analisara uma string vazia
        if not re.search(r"[A-Za-z]", senha or ""):
            problemas.append("Conter letras")
        # usa ERs para verificar a presenca de numeros, se a senha noa tiver nenhum numero, o sistema lanca o aviso correspondente
        if not re.search(r"\d", senha or ""):
            problemas.append("Conter números")
        # ^ = negacao -> procura qualquer coisa que nao seja letra e nao seja numero, se nao houver caracteres especiais o problema eh registrado
        if not re.search(r"[^A-Za-z0-9]", senha or ""):
            problemas.append("conter ao menos um caractere especial (ex.: @, #, !)")
        # if problemas = se na lista de problemas houver pelo menos 1 registro significa que a senha falhou em algum requisito
        # exibe os problemas
        if problemas:
            raise SenhaFracaError("A senha deve " + ", ".join(problemas) + ".")
        
class Usuario(Entidade, ABC):
    """
    Superclasse que representa um usuário genérico no sistema

    DER: ID_usuario, nome, email (único), telefone (único), senha (hash), data_cadastro, ativo, cpf (único), data_nascimento
    """

    def __init__(self, nome: str, email: str, telefone: str, cpf: str, data_nascimento: date | datetime | None = None, senha_plana: str | None = None, 
        senha_hash: str | None = None, id_usuario: int | None = None, data_cadastro: datetime | None = None, ativo: bool = True):
       
        super().__init__(id_usuario)
        self._nome = exigirTexto(nome, "nome")
        self._email = validarEmail(email)
        self._telefone = validarTelefone(telefone)
        self._data_cadastro = data_cadastro or datetime.now()
        self._ativo = bool(ativo)
        self._data_nascimento = (validarData(data_nascimento, "data_nascimento") if data_nascimento else None)
        self.__cpf = validarCPF(cpf)
        # DER: "senha" guarda a senha hash, nunca a senha real
        self.__senha_hash = " "
        # Necessário olhar if/elif/else -> comentário do professor sobre utilizar autômatos
        if senha_hash:
            self.__senha_hash = senha_hash
        elif senha_plana is not None:
            self.definir_senha(senha_plana)
        else:
            raise ValidacaoError("É necessário informar uma senha")

    # Getters e setters
    @property
    def nome(self) -> str: return self._nome

    @nome.setter
    def nome(self, v: str):
        self._nome = exigirTexto(v, "nome")

    @property
    def email(self) -> str: return self._email

    @email.setter
    def email(self, v: str):
        self._email = validarEmail(v)

    @property
    def telefone(self) -> str: return self._telefone

    @telefone.setter
    def telefone(self, v: str):
        self._telefone = validarTelefone(v)

    @property
    def data_cadastro(self) -> datetime: return self._data_cadastro

    @property
    def data_nascimento(self) -> date | None:
        return self._data_nascimento

    @data_nascimento.setter
    def data_nascimento(self, v):
        self._data_nascimento = validarData(v, "data de nascimento")

    @property
    def ativo(self) -> bool: return self._ativo

    def ativar(self):
        self._ativo = True

    def desativar(self):
        self._ativo = False

    # Dados sensíveis
    @property
    def senha_hash(self) -> str:
        # Exposto apenas para gravar "senha"
        return self.__senha_hash

    @property
    def CPF_persis(self) -> str:
        # Exposto para gravar "cpf", para exibir para alguem deve-se usar obterCPF, que checa a permissão
        return self.__cpf

    def obterCPF(self, solicitante: "Usuario") -> str:
        """Só o próorio dono ou quem pode acessar dados sensíveis (admin) pode ver o CPF"""
        if solicitante is self or solicitante.podeAcessarDadosSensiveis:
            return self.__cpf
        raise AcessoNegadoError("Apenas o usuário admin pode consultar este CPF")

    # METODOS DE SENHAS -> ADICIONAR

    # Contrato
    @property
    @abstractmethod
    def perfil(self) -> str:
        """'cliente', 'funcionario' ou 'administrador'"""

    @property
    @abstractmethod
    def podeAcessarDadosSensiveis(self) -> bool:
        return f"<{self.__class__.__name__} id={self.id} nome={self._nome!r}>"

class Cliente(Usuario):
    pass
 
class Funcionario(Usuario):
    pass

class Administrador(Usuario):
    pass


