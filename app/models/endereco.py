"""
app / models / endereco.py

DER: um CLIENTE tem vários ENDEREÇOS (1:N). Cada endereço pertence a um só cliente
(FK CLIENTEUSUÁRIOID_usuário) e some junto com ele (ON DELETE CASCADE)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.validators.campos import Validador

from .base import Entidade

if TYPE_CHECKING:
    # Só para os type hints: importar de verdade criaria um ciclo (Cliente também importa Endereco)
    from .cliente import Cliente


class Endereco(Entidade):
    """
    DER: ID_endereco, CLIENTEUSUÁRIOID_usuário (FK), apelido (nulo), logradouro, numero,
    complemento (nulo), bairro, cidade, cep char(8)
    Imutável depois de criado: para mudar, remove-se e cadastra-se outro
    """

    def __init__(
        self,
        logradouro: str,
        numero: str,
        bairro: str,
        cidade: str,
        cep: str,
        complemento: str = "",
        apelido: str = "",
        id_endereco: int | None = None,
    ):
        """
        Valida e normaliza todos os campos
        """
        super().__init__(id_endereco)
        self._logradouro = Validador.texto(logradouro, "logradouro")
        self._numero = Validador.texto(numero, "número")
        self._bairro = Validador.texto(bairro, "bairro")
        self._cidade = Validador.texto(cidade, "cidade")
        # Validador.cep tira traços/pontos e confere os 8 dígitos: "28000-000" vira "28000000"
        self._cep = Validador.cep(cep)
        self._complemento = Validador.textoOpcional(complemento, "complemento")
        self._apelido = Validador.textoOpcional(apelido, "apelido")
        # Dono do endereço. O cliente pode ser criado antes de ter id; a FK é lida dele quando for gravar
        self._cliente: Cliente | None = None

    # Leitura simples dos campos (sem setters: o endereço é imutável)
    @property
    def logradouro(self) -> str:
        return self._logradouro

    @property
    def numero(self) -> str:
        return self._numero

    @property
    def complemento(self) -> str | None:
        return self._complemento

    @property
    def bairro(self) -> str:
        return self._bairro

    @property
    def cidade(self) -> str:
        return self._cidade

    @property
    def cep(self) -> str:
        return self._cep

    @property
    def apelido(self) -> str | None:
        return self._apelido

    @property
    def cliente(self) -> Cliente | None:
        return self._cliente

    @property
    def id_cliente(self) -> int | None:
        """
        Valor da FK CLIENTEUSUÁRIOID_usuário: o id do dono, ou None se ainda não tem dono/id
        """
        # `a and b` devolve `a` se a for falso; senão devolve `b`.
        #   sem cliente (None, falso)  -> devolve None
        #   com cliente (verdadeiro)   -> devolve o id dele
        return self._cliente and self._cliente.id

    def _vincular(self, cliente: Cliente | None) -> None:
        """
        Uso interno: chamado por Cliente.adicionarEndereco/removerEndereco para definir ou desfazer o dono
        """
        self._cliente = cliente

    def formatado(self) -> str:
        """
        Endereço por extenso, ex.: 'Rua A, 10, Apto 2 - Centro, Campos - CEP 28000-000'
        """
        # filter(None, ...) descarta o complemento quando ele é None, sem precisar de if
        rua = ", ".join(
            filter(None, (self._logradouro, self._numero, self._complemento))
        )
        return f"{rua} - {self._bairro}, {self._cidade} - CEP {self._cep[:5]}-{self._cep[5:]}"

    def __repr__(self) -> str:
        """
        Texto exibido ao imprimir o objeto
        """
        return f"Endereco({self.formatado()})"
