"""
app / services / conversor_unidades.py

Responsável pela conversão entre unidades padrão (kg<->g, l<->ml)

Não faz conversões irregulares (1 lata de leite condensado = 395g), estas usam o "fator_conversao" do Insumo

Como usar:
    ConversorUnidades.fator("kg", "g") -> 1000
    ConversorUnidades.converter(1.5, "kg", "g") -> 1500.000
"""

from __future__ import annotations
 
from decimal import ROUND_HALF_UP, Decimal
 
from app.exceptions import ValidacaoError
from app.validators.campos import Validador, garantir

class ConversorUnidades:
    """
    Converte unidades entre unidades padrão usando uma tabela
    """
    # Três casas decimais (BD)
    _MILESIMOS = Decimal("0.001")

    # TABELA (unidade de origem , unidade de destino): quanto multiplicar
    # Par chave-valor, a chave eh uma tupla de 2 textos
    # Exemplo: ("kg", "g"): Decimal("1000") diz que para ir de kg para g deve multiplicar por 1000
    _FATORES = {
        # Conversões de verdade
        ("kg", "g"): Decimal("1000"),
        ("g", "kg"): Decimal("0.001"),
        ("l", "ml"): Decimal("1000"),
        ("ml", "l"): Decimal("0.001"),
        # Mesma unidade nos dois lados: não muda nada (fator 1)
        ("g", "g"): Decimal("1"),
        ("kg", "kg"): Decimal("1"),
        ("ml", "ml"): Decimal("1"),
        ("l", "l"): Decimal("1"),
        ("un", "un"): Decimal("1"),
    }

    @classmethod
    def fator(cls, de: str, para: str) -> Decimal:
        """
        Devolve quanto multiplicar de unidade 'de' até unidade 'para'
        
        Exemplo: fator("kg", "g") devolve 1000
        """

        # 1: limpa o que foi digitado
        origem = Validador.texto(de, "unidade de origem", max_len=20).lower()
        destino = Validador.texto(para, "unidade de destino", max_len=20).lower()
        # 2: monta o par que vai ser procurado na tabela
        par = (origem, destino)
        # 3: confere se o par existe na tabela
        garantir(
            par in cls._FATORES,
            ValidacaoError(f"Não sei converter '{origem}' para '{destino}'"
                           f"Informe o fator de conversão manualmente")
        )
        # 4: busca o fator
        return cls._FATORES[par]

    @classmethod
    def converter(cls, quantidade, de: str, para: str) -> Decimal:
        """Converte uma quantidade de uma unidade para outra
 
        Exemplo: converter(1.5, "kg", "g") devolve 1500.000
        """
        # 1: valida a quantidade
        numero = Validador.quantidade(quantidade, "quantidade")
 
        # 2: descobre por quanto multiplicar
        fator = cls.fator(de, para)
 
        # 3: multiplica e arredonda em 3 casas (.quantize). ROUND_HALF_UP é o arredondamento
        resultado = numero * fator
        return resultado.quantize(cls._MILESIMOS, rounding=ROUND_HALF_UP)