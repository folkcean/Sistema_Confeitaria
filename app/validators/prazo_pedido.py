"""
app / validators / prazo_pedido.py

REGRAS DE PRAZO DO PEDIDO

Só trabalha com DATAS e NÚMEROS (não conhece Pedido nem Produto: a pasta validators/ não depende de entidades).
Quem usa é o Pedido, que entrega a este validador o que ele precisa saber de cada item.

Regras (relatório 2.3 e entrevistas 1.1 e 4.5):
    ENCOMENDA      -> a entrega só pode ser a partir de: criação do pedido + antecedência do produto (padrão 48 h;
                      doces simples podem ter 24 h). Com vários itens vale a MAIOR antecedência.
    PRONTA ENTREGA -> o pedido precisa ser feito até 1 hora antes do fechamento (fecha 18h -> pedir até 17h).
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, time, timedelta

from app.exceptions import ValidacaoError
from app.validators.campos import Validador, garantir


class PrazoPedido:
    """
    Confere os prazos de um pedido
    Todos os métodos levantam ValidacaoError quando o prazo não é cumprido
    """

    # Horário de encerramento das atividades 
    FECHAMENTO_PADRAO = time(18, 0)
    # Pronta entrega: o pedido precisa entrar 1 hora antes do fechamento
    ANTECEDENCIA_PRONTA_ENTREGA = timedelta(hours=1)

    @classmethod
    def validarEncomenda(cls, criacao: datetime, entrega: datetime, antecedencia_horas: int) -> None:
        """A entrega precisa ser, no mínimo, `antecedencia_horas` horas depois da criação do pedido.

        `timedelta(hours=n)` representa "n horas" e pode ser somado a um datetime.
        O limite é INCLUSIVO: entregar exatamente na hora mínima é permitido.
        """
        horas = Validador.inteiroNaoNegativo(antecedencia_horas, "antecedência (horas)")
        minimo = criacao + timedelta(hours=horas)
        garantir(
            entrega >= minimo,
            ValidacaoError(
                f"Prazo insuficiente: este pedido pede {horas}h de antecedência "
                f"(entrega a partir de {minimo:%d/%m/%Y %H:%M})"
            ),
        )

    @classmethod
    def validarProntaEntrega(cls, criacao: datetime, fechamento: time = FECHAMENTO_PADRAO) -> None:
        """O pedido precisa ser feito até (fechamento - 1 hora) do MESMO dia da criação.

        `datetime.combine(dia, hora)` junta uma data e um horário num datetime.
        """
        limite = datetime.combine(criacao.date(), fechamento) - cls.ANTECEDENCIA_PRONTA_ENTREGA
        garantir(
            criacao <= limite,
            ValidacaoError(
                f"Pedidos de pronta entrega devem ser feitos até as {limite:%H:%M} "
                f"(1 hora antes do fechamento, às {fechamento:%H:%M})"
            ),
        )

    @classmethod
    def validar(cls, criacao: datetime, entrega: datetime, itens: Iterable[tuple[bool, int]],
                fechamento: time = FECHAMENTO_PADRAO) -> None:
        """Valida o pedido inteiro. `itens` é uma lista de pares (é_pronta_entrega, antecedencia_horas).

        LÓGICA:
        1) separa os itens de pronta entrega dos de encomenda (filter mantém só quem satisfaz a função);
        2) encomenda: vale a MAIOR antecedência (`max(..., default=0)`: sem encomendas, 0 = nada a exigir);
        3) pronta entrega: só confere se houver algum item de pronta entrega (`not prontas or ...`:
           sem itens assim, a condição já é verdadeira e a conferência nem roda, igual ao garantir()).
        """
        garantir(isinstance(criacao, datetime), ValidacaoError("A data de criação do pedido é inválida"))
        garantir(isinstance(entrega, datetime), ValidacaoError("A data de entrega/retirada é inválida"))
        lista = list(itens)
        prontas = list(filter(lambda item: item[0], lista))
        encomendas = list(filter(lambda item: not item[0], lista))

        antecedencia = max((horas for _, horas in encomendas), default=0)
        cls.validarEncomenda(criacao, entrega, antecedencia)

        # Passa o limite para uma variável para só rodar a conferência quando há pronta entrega.
        # O limite das 17h só vale quando há pronta entrega E a entrega é no MESMO dia do pedido
        # (pedir às 19h para amanhã é permitido).
        para_hoje = bool(prontas) and entrega.date() == criacao.date()
        conferencias = {True: lambda: cls.validarProntaEntrega(criacao, fechamento), False: lambda: None}
        conferencias[para_hoje]()
