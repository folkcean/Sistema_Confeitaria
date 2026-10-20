"""
app / models / cliente.py

CLIENTE (tabela CLIENTE)
Seus endereços ficam em endereco.py

Além de guardar os dados do cliente, esta classe decide QUAIS dados cada perfil pode ver
(privacidade): o próprio cliente e o administrador veem tudo; o funcionário só o necessário para produzir/entregar
"""

from __future__ import annotations

from app.exceptions import AcessoNegadoError, ValidacaoError
from app.validators.campos import Validador, garantir

from .endereco import Endereco
from .enums import Perfil
from .usuario import Usuario


class Cliente(Usuario):
    """
    DER (além de USUÁRIO): apelido, cliente_vip, instagram (nulo), restricoes_alimentares (nulo),
    observacoes (texto, nulo), preferencias (texto, nulo)
    """

    def __init__(
        self,
        nome: str,
        email: str | None,
        telefone: str,
        cpf: str | None,
        apelido: str = "",
        cliente_vip: bool = False,
        instagram: str = "",
        restricoes_alimentares: str = "",
        observacoes: str = "",
        preferencias: str = "",
        **kwargs,
    ):

        # `**kwargs` junta todos os parâmetros nomeados que não foram listados acima num dicionário
        # Os da classe mãe (senha, id_usuario, data_nascimento, data_cadastro, ativo)
        # Em `super().__init__(..., **kwargs)` o `**` faz o caminho inverso: espalha o dicionário de volta como parâmetros nomeados
        # Assim o Cliente não precisa repetir todos os parâmetros do Usuario

        super().__init__(nome, email, telefone, cpf, **kwargs)
        # DER: apelido é NOT NULL. `apelido or nome` usa o próprio nome quando o apelido veio vazio
        self._apelido = Validador.texto(apelido or nome, "apelido")
        self._cliente_vip = bool(cliente_vip)
        self._instagram = Validador.textoOpcional(instagram, "instagram")
        self._restricoes_alimentares = Validador.textoOpcional(
            restricoes_alimentares, "restrições alimentares"
        )
        # Colunas do tipo `text` no DER aceitam textos longos: limite de 10.000 caracteres
        self._observacoes = Validador.textoOpcional(
            observacoes, "observações", max_len=10_000
        )
        self._preferencias = Validador.textoOpcional(
            preferencias, "preferências", max_len=10_000
        )
        # Lista dos endereços deste cliente (relação 1:N), começa vazia
        self._enderecos: list[Endereco] = []

    # CONTRATO DE USUARIO (obrigatório por causa dos @abstractmethod da classe mãe)
    @property
    def perfil(self) -> Perfil:
        """Este usuário é um cliente."""
        return Perfil.CLIENTE

    @property
    def acessa_dados_sensiveis(self) -> bool:
        """Cliente não acessa dados sensíveis de ninguém."""
        return False

    # DADOS DO CLIENTE (getter = leitura; setter = alteração com validação)
    @property
    def apelido(self) -> str:
        return self._apelido

    @apelido.setter
    def apelido(self, valor: str) -> None:
        """Altera o apelido (obrigatório)."""
        self._apelido = Validador.texto(valor, "apelido")

    # Só leitura: VIP muda apenas por promoverVip()/removerVip().
    @property
    def cliente_vip(self) -> bool:
        return self._cliente_vip

    @property
    def instagram(self) -> str | None:
        return self._instagram

    @instagram.setter
    def instagram(self, valor: str) -> None:
        """Altera o Instagram (vazio vira None)."""
        self._instagram = Validador.textoOpcional(valor, "instagram")

    @property
    def restricoes_alimentares(self) -> str | None:
        return self._restricoes_alimentares

    @restricoes_alimentares.setter
    def restricoes_alimentares(self, valor: str) -> None:
        """Altera as restrições alimentares (vazio vira None)."""
        self._restricoes_alimentares = Validador.textoOpcional(
            valor, "restrições alimentares"
        )

    @property
    def observacoes(self) -> str | None:
        return self._observacoes

    @observacoes.setter
    def observacoes(self, valor: str) -> None:
        """Altera as observações (vazio vira None)."""
        self._observacoes = Validador.textoOpcional(
            valor, "observações", max_len=10_000
        )

    @property
    def preferencias(self) -> str | None:
        return self._preferencias

    @preferencias.setter
    def preferencias(self, valor: str) -> None:
        """Altera as preferências (vazio vira None)."""
        self._preferencias = Validador.textoOpcional(
            valor, "preferências", max_len=10_000
        )

    @property
    def enderecos(self) -> tuple[Endereco, ...]:
        """
        Devolve uma CÓPIA IMUTÁVEL (tupla) da lista: assim ninguém de fora altera a lista interna
        """
        return tuple(self._enderecos)

    # ENDEREÇOS (1:N)
    def adicionarEndereco(self, endereco: Endereco) -> None:
        """
        Vincula o endereço a este cliente
        Um endereço só pode ter um dono
        LÓGICA: confere que o endereço ainda não tem dono; avisa ao endereço quem é o dono; guarda na lista
        """
        garantir(
            endereco.cliente is None,
            ValidacaoError("Este endereço já pertence a um cliente"),
        )
        endereco._vincular(self)
        self._enderecos.append(endereco)

    def removerEndereco(self, endereco: Endereco) -> None:
        """
        Remove o endereço deste cliente e desfaz o vínculo (o endereço volta a não ter dono)
        """
        # `x in lista` = "x está na lista?"
        garantir(
            endereco in self._enderecos,
            ValidacaoError("Este endereço não pertence a este cliente"),
        )
        self._enderecos.remove(endereco)
        endereco._vincular(None)

    # VIP
    def promoverVip(self) -> None:
        """
        Marca o cliente como VIP
        """
        self._cliente_vip = True

    def removerVip(self) -> None:
        """
        Remove a marcação de VIP
        """
        self._cliente_vip = False

    # PRIVACIDADE: O QUE CADA PERFIL ENXERGA
    def acessoAosDados(self, solicitante: Usuario) -> dict:
        """
        Pergunta ao solicitante o que ele pode ver; cada perfil responde do seu jeito
        """
        return solicitante.consultarCliente(self)

    def dadosCompletos(self, solicitante: Usuario) -> dict:
        """
        Todos os dados do cliente, em um dicionário ({"chave": valor})
        O CPF passa por obterCpf(), que confere a permissão mais uma vez
        """
        return {
            "nome": self._nome,
            "apelido": self._apelido,
            "email": self._email,
            "telefone": self._telefone,
            "cpf": self.obterCpf(solicitante),
            "data_nascimento": self._data_nascimento,
            "vip": self._cliente_vip,
            "instagram": self._instagram,
            "restricoes_alimentares": self._restricoes_alimentares,
            "observacoes": self._observacoes,
            "preferencias": self._preferencias,
            # [e.formatado() for e in self._enderecos] = "list comprehension": uma lista nova com o texto
            # formatado de cada endereço.
            "enderecos": [e.formatado() for e in self._enderecos],
        }

    def dadosOperacionais(self) -> dict:
        """
        Só o que a produção/entrega precisa: como chamar, contato, restrições alimentares (saúde) e onde entregar
        """
        return {
            "apelido": self._apelido,
            "telefone": self._telefone,
            "restricoes_alimentares": self._restricoes_alimentares,
            "enderecos": [e.formatado() for e in self._enderecos],
        }

    def consultarCliente(self, cliente) -> dict:
        """
        Quando quem pede é um cliente: ele só pode ver os próprios dados, nunca os de outro cliente
        """
        garantir(
            cliente is self,
            AcessoNegadoError("Um cliente só pode consultar os próprios dados"),
        )
        return cliente.dadosCompletos(self)
