"""
app / models / fornecedor.py

Tabela FORNECEDOR no DER: de quem a confeitaria compra os insumos (entrevista 8.1 a 8.3)

Fornecedor não é apagado: é desativado (alternarAtivo), porque as compras antigas continuam
apontando para ele (FK de COMPRA_INSUMO)

"""

from __future__ import annotations

from app.validators.campos import Validador
from .base import Entidade


class Fornecedor(Entidade):
    """
    DER: ID_fornecedor, nome, telefone, endereco (obrigatórios), email, cnpj (único), contato_principal
    (anuláveis) e ativo (default true)
    """

    def __init__(
            self,
            nome: str,
            telefone: str,
            endereco: str,
            email: str | None = None,
            cnpj: str | None = None,
            contato_principal: str | None = None,
            ativo: bool = True,
            id_fornecedor: int | None = None
    ):
        """Valida e normaliza os campos. Os três primeiros são NOT NULL no DER; o resto pode ficar vazio"""
        super().__init__(id_fornecedor)
        self._nome = Validador.texto(nome, "nome do fornecedor")
        self._telefone = Validador.telefone(telefone)
        self._endereco = Validador.texto(endereco, "endereço")
        # opcional: vazio vira None (NULL no banco); preenchido passa pelo validador do campo
        self._email = Validador.opcional(Validador.email, email)
        self._cnpj = Validador.opcional(Validador.cnpj, cnpj)
        self._contato_principal = Validador.textoOpcional(contato_principal, "contato principal")
        self._ativo = bool(ativo)

    # Leitura dos campos
    @property
    def nome(self) -> str:
        return self._nome

    @property
    def telefone(self) -> str:
        return self._telefone

    @property
    def endereco(self) -> str:
        return self._endereco

    @property
    def email(self) -> str | None:
        return self._email

    @property
    def cnpj(self) -> str | None:
        return self._cnpj

    @property
    def contato_principal(self) -> str | None:
        return self._contato_principal

    @property
    def ativo(self) -> bool:
        return self._ativo

    # Alterações cadastrais (cada uma valida o próprio campo, como no Produto)
    def alterarNome(self, valor: str) -> None:
        """Troca o nome (obrigatório)"""
        self._nome = Validador.texto(valor, "nome do fornecedor")

    def alterarTelefone(self, valor: str) -> None:
        """Troca o telefone (obrigatório, com DDD)"""
        self._telefone = Validador.telefone(valor)

    def alterarEndereco(self, valor: str) -> None:
        """Troca o endereço (obrigatório, texto livre: o DER guarda numa coluna só)"""
        self._endereco = Validador.texto(valor, "endereço")

    def alterarEmail(self, valor: str | None) -> None:
        """Troca o e-mail (vazio apaga)"""
        self._email = Validador.opcional(Validador.email, valor)

    def alterarCnpj(self, valor: str | None) -> None:
        """Troca o CNPJ (vazio apaga). Repetido é barrado pelo UNIQUE do banco"""
        self._cnpj = Validador.opcional(Validador.cnpj, valor)

    def alterarContatoPrincipal(self, valor: str | None) -> None:
        """Troca o nome da pessoa de contato (vazio apaga)"""
        self._contato_principal = Validador.textoOpcional(valor, "contato principal")

    def alternarAtivo(self) -> None:
        """Ativa/desativa. Inativo não aparece para compras novas, mas continua nas compras antigas"""
        self._ativo = not self._ativo

    def __repr__(self) -> str:
        """Texto exibido ao imprimir o objeto"""
        status = {True: "ativo", False: "inativo"}[self._ativo]
        return f"<Fornecedor id={self.id} {self._nome!r} ({status})>"
