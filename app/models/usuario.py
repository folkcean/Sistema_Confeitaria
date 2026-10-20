"""
app / models / usuario.py

Superclasse abstrata dos usuários (tabela USUÁRIO)

Hierarquia do DER (cada subtipo tem PK/FK = USUÁRIO.ID_usuário):
    Usuario
      ├── Cliente        (cliente.py)
      ├── Funcionario    (funcionario.py)
      └── Administrador  (administrador.py)
"""

from __future__ import annotations

# ABC = "Abstract Base Class": a classe base para criar classes abstratas
# abstractmethod = decorador que marca um método como "obrigatório nas filhas"
from abc import ABC, abstractmethod
from datetime import date, datetime

from app.exceptions import AcessoNegadoError
from app.validators.campos import Validador, garantir

from .base import Entidade
from .contratos import ClienteConsultavel
from .enums import Perfil
from .senha import Senha, SenhaAusente


class Usuario(Entidade, ABC):
    """
    DER: ID_usuario, nome, email (nulo, único), telefone (único), senha (hash, nula),
    data_cadastro, ativo, cpf (nulo, único), data_nascimento (nula)
    """

    def __init__(
        self,
        nome: str,
        email: str | None,
        telefone: str,
        cpf: str | None,
        data_nascimento: date | datetime | str | None = None,
        senha: Senha | None = None,
        id_usuario: int | None = None,
        data_cadastro: datetime | None = None,
        ativo: bool = True,
    ):
        """
        Valida e normaliza cada campo. A senha chega pronta (objeto Senha), criada por Senha.criar ou Senha.deHash
        """

        # Chama o __init__ da classe mãe (Entidade), que guarda o id
        super().__init__(id_usuario)
        self._nome = Validador.texto(nome, "nome")
        # Validador.opcional: se vier vazio/None guarda None; se vier preenchido, valida e normaliza
        self._email = Validador.opcional(Validador.email, email)
        self._telefone = Validador.telefone(telefone)
        self._data_nascimento = Validador.opcional(
            Validador.dataNascimento, data_nascimento
        )
        # O CPF é dado sensível: só sai por obterCpf(), que confere a permissão
        self.__cpf = Validador.opcional(Validador.cpf, cpf)
        # `senha or SenhaAusente()`: se não veio senha (None), usa o "objeto de senha vazia"
        self._senha = senha or SenhaAusente()
        # Sem data de cadastro informada, usa o momento atual (datetime.now())
        self._data_cadastro = data_cadastro or datetime.now()
        # bool(x) converte para True/False
        self._ativo = bool(ativo)

    # Leitura e alteração dos dados cadastrais (cada setter revalida o valor recebido)
    # `@property` cria o getter (obj.nome) e `@nome.setter` cria o setter (obj.nome = "x")
    # Cada setter revalida o objeto antes de gravar, então o objeto nunca fica com dado inválido
    @property
    def nome(self) -> str:
        return self._nome

    @nome.setter
    def nome(self, valor: str) -> None:
        """
        Altera o nome, validando que não está vazio
        """
        self._nome = Validador.texto(valor, "nome")

    @property
    def email(self) -> str | None:
        return self._email

    @email.setter
    def email(self, valor: str | None) -> None:
        """
        Altera o e-mail (aceita vazio/None, pois a coluna é nula)
        """
        self._email = Validador.opcional(Validador.email, valor)

    @property
    def telefone(self) -> str:
        return self._telefone

    @telefone.setter
    def telefone(self, valor: str) -> None:
        """
        Altera o telefone, validando DDD + número
        """
        self._telefone = Validador.telefone(valor)

    @property
    def data_nascimento(self) -> date | None:
        return self._data_nascimento

    @data_nascimento.setter
    def data_nascimento(self, valor) -> None:
        """
        Altera a data de nascimento (aceita vazio/None, pois a coluna é nula)
        """
        self._data_nascimento = Validador.opcional(Validador.dataNascimento, valor)

    @property
    def data_cadastro(self) -> datetime:
        return self._data_cadastro

    @property
    def ativo(self) -> bool:
        return self._ativo

    def ativar(self) -> None:
        """
        Reativa a conta (volta a poder fazer login)
        """
        self._ativo = True

    def desativar(self) -> None:
        """Desativa a conta sem apagar o histórico dos pedidos"""
        self._ativo = False

    # Dados sensíveis
    @property
    def senha_hash(self) -> str | None:
        """
        Hash para gravar na coluna `senha`. Nunca é a senha real
        """
        return self._senha.hash

    @property
    def cpf_persistencia(self) -> str | None:
        """
        CPF cru, só para o repositório gravar na coluna `cpf`

        Para exibir a alguém deve-se usar obterCpf, que confere a permissão
        """
        return self.__cpf

    def obterCpf(self, solicitante: "Usuario") -> str | None:
        """
        Devolve o CPF só para o próprio dono ou para quem pode acessar dados sensíveis (administrador)
        """
        garantir(
            solicitante is self or solicitante.acessa_dados_sensiveis,
            AcessoNegadoError(
                "Apenas o próprio usuário ou o administrador pode consultar este CPF"
            ),
        )
        return self.__cpf

    # Senha
    def definirSenha(self, senha_plana: str) -> None:
        """
        Troca a senha: Senha.criar valida a força e gera o hash novo
        """
        self._senha = Senha.criar(senha_plana)

    def verificarSenha(self, senha_plana: str) -> bool:
        """
        Confere a senha, deixa a conferência com o objeto Senha (sem senha cadastrada, sempre False)
        """
        return self._senha.verificar(senha_plana)

    # CONTRATO QUE CADA SUBTIPO PRECISA CUMPRIR
    # Um método marcado com @abstractmethod não tem implementação aqui -> as classes filhas devem implementá-los
    # `@property` + `@abstractmethod` juntos -> toda filha deve ter esta propriedade
    @property
    @abstractmethod
    def perfil(self) -> Perfil:
        """
        Perfil do usuário (cliente, funcionário ou administrador)
        """

    @property
    @abstractmethod
    def acessa_dados_sensiveis(self) -> bool:
        """
        Indica se o perfil pode ver dados sensíveis (ex.: CPF de clientes)
        """

    @abstractmethod
    def consultarCliente(self, cliente: ClienteConsultavel) -> dict:
        """
        Devolve os dados do cliente que ESTE perfil tem direito de ver, ou lança AcessoNegadoError

        Cada perfil responde do seu jeito (admin vê tudo, funcionário só o operacional, cliente só o próprio)
        """
