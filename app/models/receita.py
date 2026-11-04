"""
app/models/receita.py

Receita (tabela RECEITA) e seus ingredientes (tabela ITEM_RECEITA)

Diz quanto de cada insumo é preciso para produzir um certo rendimento
Exemplo: "Massa de bolo" rende 1 un e usa 300 g de farinha, 200 g de açúcar
"""
from __future__ import annotations

from datetime import datetime
from decimal import ROUND_UP, Decimal
from typing import TYPE_CHECKING

from app.exceptions import ValidacaoError
from app.validators.campos import Validador, garantir

from .base import Entidade

if TYPE_CHECKING:
    from .insumo import Insumo


class ItemReceita(Entidade):
    """
    Um ingrediente dentro de uma receita

    DER: id_item_receita, ingredienteID (FK do insumo), receitaID (FK da receita),
    quantidade_necessaria numeric(10,3), observacoes (nulo)

    `quantidade_necessaria` está na unidade de receita do insumo (ex.: gramas), não na do estoque (kg)
    """

    def __init__(self, 
                 insumo: Insumo, 
                 quantidade_necessaria, 
                 observacoes: str = "",
                 id_item_receita: int | None = None):
        """
        Valida a quantidade (> 0, 3 casas) e guarda o insumo
        O vínculo com a receita é feito por Receita.adicionarItem()
        """
        super().__init__(id_item_receita)
        self._insumo = insumo
        self._quantidade_necessaria = Validador.quantidadePositiva(quantidade_necessaria, "quantidade necessária")
        self._observacoes = Validador.textoOpcional(observacoes, "observações")
        # Receita dona deste item -> começa sem dona (None)
        self._receita: Receita | None = None

    @property
    def insumo(self) -> Insumo: return self._insumo
    @property
    def quantidade_necessaria(self) -> Decimal: return self._quantidade_necessaria
    @property
    def observacoes(self) -> str | None: return self._observacoes
    @property
    def receita(self) -> Receita | None: return self._receita

    @property
    def receita_id(self) -> int | None:
        """
        Valor da FK receitaID: id da receita dona, ou None. `a and b` devolve `a` se for falso; senão `b`
        """
        return self._receita and self._receita.id

    @property
    def insumo_id(self) -> int | None:
        """
        Valor da FK ingredienteID: id do insumo (None se o insumo ainda não foi gravado)
        """
        return self._insumo.id

    def _vincular(self, receita: Receita | None) -> None:
        """
        Uso interno: Receita.adicionarItem/removerItem chamam isto para definir (ou desfazer, com None) a dona
        """
        self._receita = receita

    def alterarQuantidade(self, nova_quantidade) -> None:
        """
        Altera a quantidade necessária (na unidade da receita)
        """
        self._quantidade_necessaria = Validador.quantidadePositiva(nova_quantidade, "quantidade necessária")

    def __repr__(self) -> str:
        """
        Texto exibido ao imprimir o objeto
        """
        return f"<ItemReceita {self._insumo.nome!r} {self._quantidade_necessaria} {self._insumo.unidade_receita}>"


class Receita(Entidade):
    """
    Modo de fazer e lista de ingredientes

    DER: id_receita, modo_preparo (texto, nulo), tempo_preparo int4, rendimento_qtd numeric(10,3),
    rendimento_un varchar(100), complexidade (nulo), data_criacao, ativa (padrão true)

    * O DER não tem `nome` na receita: ela só é identificada pelo produto que a usa
    ** A unidade do `tempo_preparo` não está no DER, aqui usei minutos
    """

    _MILESIMOS = Decimal("0.001")

    def __init__(self, 
                 rendimento_qtd, 
                 rendimento_un: str, 
                 tempo_preparo: int = 0, 
                 modo_preparo: str = "",
                 complexidade: str = "", 
                 ativa: bool = True, 
                 data_criacao: datetime | None = None,
                 id_receita: int | None = None):
        """
        Só `rendimento_qtd` e `rendimento_un` são obrigatórios
        """
        super().__init__(id_receita)
        # Rendimento: quanto esta receita produz (ex.: 50 un de brigadeiro)
        self._rendimento_qtd = Validador.quantidadePositiva(rendimento_qtd, "rendimento")
        self._rendimento_un = Validador.texto(rendimento_un, "unidade do rendimento", max_len=100)
        self._tempo_preparo = Validador.inteiroNaoNegativo(tempo_preparo, "tempo de preparo (minutos)")
        # modo_preparo é TEXT no DER
        self._modo_preparo = Validador.textoOpcional(modo_preparo, "modo de preparo", max_len=100_000)
        self._complexidade = Validador.textoOpcional(complexidade, "complexidade")
        self._ativa = bool(ativa)
        # `a or b`: se data_criacao foi informada usa ela; senão usa o momento atual
        self._data_criacao = data_criacao or datetime.now()
        # Ingredientes desta receita -> começa vazia
        self._itens: list[ItemReceita] = []

    @property
    def rendimento_qtd(self) -> Decimal: return self._rendimento_qtd
    @property
    def rendimento_un(self) -> str: return self._rendimento_un
    @property
    def tempo_preparo(self) -> int: return self._tempo_preparo
    @property
    def modo_preparo(self) -> str | None: return self._modo_preparo
    @property
    def complexidade(self) -> str | None: return self._complexidade
    @property
    def ativa(self) -> bool: return self._ativa
    @property
    def data_criacao(self) -> datetime: return self._data_criacao

    @property
    def itens(self) -> tuple[ItemReceita, ...]:
        """
        Cópia imutável: ninguém de fora altera a lista interna 
        Usar adicionarItem/removerItem
        """
        return tuple(self._itens)

    # Alterações
    def alternarAtiva(self) -> None:
        """
        Liga/desliga a receita. `not` inverte True/False"""
        self._ativa = not self._ativa

    def alterarRendimento(self, quantidade, unidade: str) -> None:
        """
        Altera o rendimento (quantidade > 0 e unidade obrigatória)
        """
        self._rendimento_qtd = Validador.quantidadePositiva(quantidade, "rendimento")
        self._rendimento_un = Validador.texto(unidade, "unidade do rendimento", max_len=100)

    def alterarModoPreparo(self, texto: str) -> None:
        """
        Altera o modo de preparo (vazio vira None)
        """
        self._modo_preparo = Validador.textoOpcional(texto, "modo de preparo", max_len=100_000)

    # Ingredientes (1:N)
    def adicionarItem(self, item: ItemReceita) -> None:
        """
        Inclui um ingrediente
         
        Um mesmo insumo não pode aparecer duas vezes na mesma receita

        Confere que o item ainda não tem dona e que o insumo não está repetido (comparando pelo NOME, que é único no DER); 
        depois avisa o item quem é a dona e guarda na lista

        `{i.insumo.nome for i in self._itens}` é um conjunto dos nomes já usados
        """
        garantir(
            item.receita is None, 
            ValidacaoError("Este item já pertence a uma receita")
        )
        garantir(
            item.insumo.nome not in {existente.insumo.nome for existente in self._itens},
            ValidacaoError(f"O insumo {item.insumo.nome!r} já está nesta receita")
        )
        item._vincular(self)
        self._itens.append(item)

    def removerItem(self, item: ItemReceita) -> None:
        """
        Remove o ingrediente e desfaz o vínculo (o item volta a não ter dona)
        """
        garantir(
            item in self._itens, 
            ValidacaoError("Este item não pertence a esta receita")
        )
        self._itens.remove(item)
        item._vincular(None)

    # Escala
    def escalar(self, quantidade_desejada) -> list[tuple[Insumo, Decimal]]:
        """
        O que é preciso para produzir `quantidade_desejada` (na mesma unidade do rendimento)

        Regra de três:  se a receita rende `rendimento_qtd` e usa X de um insumo,
                        para `quantidade_desejada` usa  X * quantidade_desejada / rendimento_qtd

        Exemplo: rende 50 un e usa 400 g de leite condensado -> para 100 un: 400 * 100 / 50 = 800 g
        """
        desejada = Validador.quantidadePositiva(quantidade_desejada, "quantidade desejada")
        # Multiplicador comum a todos os itens (calculado uma vez só)
        proporcao = desejada / self._rendimento_qtd
        # Compreensão de lista: um par (insumo, quantidade escalada) para cada item da receita
        return [
            (item.insumo, (item.quantidade_necessaria * proporcao).quantize(self._MILESIMOS, rounding=ROUND_UP))
            for item in self._itens
        ]

    def necessidadesBase(self) -> list[tuple[Insumo, Decimal]]:
        """
        Insumos para UMA receita inteira (a quantidade do rendimento, sem escalar)
        """
        return self.escalar(self._rendimento_qtd)

    def __repr__(self) -> str:
        """
        Texto exibido ao imprimir o objeto
        """
        return f"<Receita id={self.id} rende {self._rendimento_qtd} {self._rendimento_un} ({len(self._itens)} itens)>"