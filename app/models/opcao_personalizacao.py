"""
app / models / opcao_personalizacao.py

Variação/adicional que o cliente pode escolher em um produto (tabela OPCAO_PERSONALIZACAO)

Relação do DER: um PRODUTO tem várias OPÇÕES (1:N). Cada opção pertence a um só produto
(FK PRODUTOID_produto) e some junto com ele (ON DELETE CASCADE)
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from app.validators.campos import Validador

from .base import Entidade

if TYPE_CHECKING:
    # Só para os type hints: importar de verdade criaria um ciclo (Produto também importa a opção)
    from .produto import Produto


class OpcaoPersonalizacao(Entidade):
    """
    DER: ID_opcao, PRODUTOID_produto (FK), nome, descricao (nula), custo_adicional numeric(10,2), ativo
    """

    def __init__(
        self,
        nome: str,
        custo_adicional=0,
        descricao: str = "",
        ativo: bool = True,
        id_opcao: int | None = None,
    ):
        """Valida e normaliza os campos. O vínculo com o produto é feito por Produto.adicionarOpcao"""
        super().__init__(id_opcao)
        self._nome = Validador.texto(nome, "nome da opção")
        self._descricao = Validador.textoOpcional(descricao, "descrição da opção")
        # Validador.dinheiro devolve Decimal com 2 casas e rejeita negativo
        self._custo_adicional = Validador.dinheiro(custo_adicional, "custo adicional")
        self._ativo = bool(ativo)
        # Produto dono desta opção. Começa sem dono (None)
        self._produto: Produto | None = None

    # Leitura simples dos campos
    @property
    def nome(self) -> str:
        return self._nome

    @property
    def descricao(self) -> str | None:
        return self._descricao

    @property
    def custo_adicional(self) -> Decimal:
        return self._custo_adicional

    @property
    def ativo(self) -> bool:
        return self._ativo

    @property
    def produto(self) -> Produto | None:
        return self._produto

    @property
    def produto_id(self) -> int | None:
        """Valor da FK PRODUTOID_produto: o id do produto dono, ou None se ainda não tem dono/id"""
        return self._produto and self._produto.id

    def _vincular(self, produto: Produto | None) -> None:
        """Uso interno: chamado por Produto.adicionarOpcao/removerOpcao para definir ou desfazer o dono"""
        self._produto = produto

    def alterarCusto(self, novo_custo) -> None:
        """Altera o custo adicional, validando como dinheiro (>= 0, 2 casas)"""
        self._custo_adicional = Validador.dinheiro(novo_custo, "custo adicional")

    def alternarAtivo(self) -> None:
        """Liga/desliga a opção (opção inativa não pode ser escolhida em novos pedidos)"""
        self._ativo = not self._ativo

    def __repr__(self) -> str:
        """Representação para depuração"""
        return f"<OpcaoPersonalizacao id={self.id} {self._nome!r} +R$ {self._custo_adicional}>"
