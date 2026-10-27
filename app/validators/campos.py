"""
app / validators / campos.py

Regras de validação de dados reutilizadas pelas entidades

Toda vez que um dado entra no sistema, ele passa por um desses validadores
Cada validador faz duas coisas
    1. Rejeita o dado inválido
    2. Devolve o dado normalizado -> pronto para ser guardado no BD
"""

# Faz o python tratar as dicas de tipos (': str', '-> int' e etc) como texto, sem executá-las
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.exceptions import ValidacaoError


def _lancar(erro: Exception) -> None:
    """
    Levanta a exceção recebida
    Existe para levantar erros dentro de uma expressão ('a ou _lancar(e)')
    'raise' puro (instrução: exceuta a ação sem retornar valor) não pode ser utilizada dentro de expressões (retornam valores)
    """
    raise erro


def garantir(condicao, erro: Exception) -> None:
    """
    Se a condição for verdadeira, não faz nada. Se for falsa, levanta 'erro'

    Substitui 'if condicao: raise erro'

    O 'or' funciona por curto-circuito:
    `condicao or _lancar(erro)' avalia o lado esquerdo (condicao). Se `condicao` for VERDADEIRO, o resultado já está decidido e o lado
    direito (_lancar(erro)) NEM É EXECUTADO. Se `condicao` for FALSO, aí sim o lado direito é executado
    """
    condicao or _lancar(erro)


class Validador:
    """
    Agrupa todos os validadores
    """

    # Padrão simples de email: xxx@xxx.xxx
    _PADRAO_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
    # Duas casas decimais
    _CENTAVOS = Decimal("0.01")
    # numeric (10,2): 10 dígitos totais, com 2 depois da vírgula -> 99.999.999,99
    _LIMITE_DINHEIRO = Decimal("100000000")
    # tipo_recebido -> como converter para date
    _CONVERSORES_DATA = {
        datetime: lambda valor: valor.date(),
        date: lambda valor: valor,
        str: date.fromisoformat,
    }

    _MILESIMOS = Decimal("0.001")
    _DECIMILESIMOS = Decimal("0.0001")
    # numeric(10,3) comporta até 9.999.999,999 e numeric(10,4) até 999.999,9999.
    _LIMITE_QUANTIDADE = Decimal("10000000")
    _LIMITE_CUSTO_UNITARIO = Decimal("1000000")

    # @staticmethod -> não tem acesso ao estado da classe, usado em funções utilitárias
    # @classmethod -> tem acesso ao estado da classe

    # TEXTO
    @staticmethod
    def texto(valor, campo: str, max_len: int = 255) -> str:
        """
        Texto obrigatório: remove espaços das pontas, rejeita vazio/None e respeita o tamanho da coluna
        """
        # `valor or ""` transforma None em ""
        # str() garante que é texto e strip() remove espações e quebras de linha no começo e no fim
        limpo = str(valor or "").strip()
        garantir(
            limpo, 
            ValidacaoError(f"O campo '{campo}' é obrigatório")
        )
        garantir(
            len(limpo) <= max_len,
            ValidacaoError(f"O campo '{campo}' deve ter no máximo {max_len} caracteres")
        )
        return limpo

    @staticmethod
    def textoOpcional(valor, campo: str, max_len: int = 255) -> str | None:
        """
        Texto para colunas NULL do DER: vazio ou só espaços vira None, equivalente ao NULL do banco
        """
        limpo = str(valor or "").strip()
        garantir(
            len(limpo) <= max_len,
            ValidacaoError(f"O campo '{campo}' deve ter no máximo {max_len} caracteres")
        )
        # 'limpo or None' devolve 'limpo' se limpo for verdadeiro; senão devolve 'None'
        return limpo or None

    @staticmethod
    def opcional(validador, valor, *argumentos):
        """
        Aplica `validador` só se houver valor. Sem valor (None ou vazio) devolve None, sem validar
        Usado nas colunas anuláveis

        'validador' é um função recebida como parâmetro
        *argumentos junta qualquer parâmetro extra numa tupla
        """
        #  `valor and validador(valor, *argumentos)`: valor vazio curto-circuito; valor preenchido executa e devolve o validado
        # or None troca qualquer resultado falso (" ") por None
        return (valor and validador(valor, *argumentos)) or None

    # CONTATO E DOCUMENTOS
    @classmethod
    def email(cls, valor) -> str:
        """
        Valida o formato do e-mail e converte para minúsculas
        """
        endereco = cls.texto(valor, "e-mail").lower()
        garantir(
            cls._PADRAO_EMAIL.fullmatch(endereco), ValidacaoError("E-mail inválido")
        )
        return endereco

    @classmethod
    def telefone(cls, valor) -> str:
        """
        Valida telefone fixo/celular com DDD (10 ou 11 dígitos) e devolve só os dígitos (DER: coluna varchar(11))
        """
        digitos = re.sub(r"\D", "", cls.texto(valor, "telefone"))
        garantir(
            len(digitos) in (10, 11),
            ValidacaoError("Telefone inválido: informe DDD + número")
        )
        return digitos

    @classmethod
    def cpf(cls, valor) -> str:
        """
        Valida os dois dígitos verificadores do CPF e devolve só os 11 dígitos (coluna char(11))
        """
        digitos = re.sub(r"\D", "", cls.texto(valor, "CPF"))
        # Rejeita tamanho errado e sequências repetidas (111.111.111-11)
        garantir(
            len(digitos) == 11 and digitos != digitos[0] * 11,
            ValidacaoError("CPF inválido"),
        )
        # digitos[:9] = fatia: os 9 primeiros dígitos. digitos[9] = o décimo dígito (o primeiro verificador)
        primeiro = cls._digitoVerificadorCpf(digitos[:9]) == int(digitos[9])
        # Para o segundo verificador, o recorte são os 10 primeiros
        segundo = cls._digitoVerificadorCpf(digitos[:10]) == int(digitos[10])
        garantir(
            primeiro and segundo, 
            ValidacaoError("CPF inválido"))
        return digitos

    @staticmethod
    def _digitoVerificadorCpf(base: str) -> int:
        """
        Calcula um dígito verificador:

        Regra: multiplica cada dígito da base por pesos decrescentes (a partir de len+1 até 2),
        soma tudo, multiplica por 10 e pega o resto da divisão por 11. Se der 10, vale 0

        Exemplo para "529982247" (9 dígitos, pesos 10..2):
        5*10 + 2*9 + 9*8 + 9*7 + 8*6 + 2*5 + 2*4 + 4*3 + 7*2 = 295  ->  295*10 % 11 = 2  ->  dígito 2
        """
        pesos = range(len(base) + 1, 1, -1)
        soma = sum(int(digito) * peso for digito, peso in zip(base, pesos))
        return (soma * 10 % 11) % 10

    @classmethod
    def cep(cls, valor) -> str:
        """
        Valida o CEP (8 dígitos) e devolve só os dígitos (coluna char(8))
        """
        digitos = re.sub(r"\D", "", str(valor or ""))
        garantir(
            len(digitos) == 8,
            ValidacaoError("CEP inválido: deve conter 8 dígitos")
        )
        return digitos

    # DATAS
    @classmethod
    def data(cls, valor, campo: str) -> date:
        """
        Converte date, datetime ou texto ISO (AAAA-MM-DD) para date
        """
        # Procura o conversor pelo tipo exato do valor; tipo desconhecido -> None -> erro
        conversor = cls._CONVERSORES_DATA.get(type(valor))
        garantir(
            conversor, 
            ValidacaoError(f"O campo '{campo}' deve ser uma data válida")
        )
        # Tenta executar, se der ValueError cai no except
        try:
            return conversor(valor)
        except ValueError as erro:
            raise ValidacaoError(f"O campo '{campo}' deve estar no formato AAAA-MM-DD") from erro

    @classmethod
    def dataNascimento(cls, valor) -> date:
        """
        Data válida e que não esteja no futuro
        """
        nascimento = cls.data(valor, "data de nascimento")
        garantir(
            nascimento <= date.today(),
            ValidacaoError("A data de nascimento não pode estar no futuro")
        )
        return nascimento

    # NÚMEROS
    @staticmethod
    def _decimal(valor, campo: str) -> Decimal:
        """
        Converte para decimal e rejeita texto não numérico, not a number (NaN) e infinito
        """
        try:
            numero = Decimal(str(valor))
        except InvalidOperation as erro:
            raise ValidacaoError(f"O campo '{campo}' deve ser um número") from erro
        # Decimal aceita NaN e infinito, is_finite rejeita os dois
        garantir(
            numero.is_finite(),
            ValidacaoError(f"O campo '{campo}' deve ser um número")
        )
        return numero

    @staticmethod
    def _decimalNaoNegativo(valor, campo: str) -> Decimal:
        """
        Converte para Decimal (evita erros de float) e rejeita texto, not a number (NaN), infinito e negativos
        """
        numero = Validador._decimal(valor, campo)
        garantir(
            numero >= 0,
            ValidacaoError(f"O campo '{campo}' não pode ser negativo")
        )
        return numero

    @classmethod
    def dinheiro(cls, valor, campo: str) -> Decimal:
        """
        Valor monetário >= 0, arredondado para 2 casas (numeric(10,2))
        """
        numero = cls._decimalNaoNegativo(valor, campo).quantize(cls._CENTAVOS, rounding=ROUND_HALF_UP)
        garantir(
            numero < cls._LIMITE_DINHEIRO,
            ValidacaoError(f"O campo '{campo}' excede o valor máximo permitido")
        )
        return numero

    @classmethod
    def percentual(cls, valor, campo: str) -> Decimal:
        """
        Percentual entre 0 e 100, com 2 casas (numeric(5,2), CHECK BETWEEN 0 AND 100)
        """
        numero = cls._decimalNaoNegativo(valor, campo).quantize(cls._CENTAVOS, rounding=ROUND_HALF_UP)
        garantir(
            numero <= 100, 
            ValidacaoError(f"O campo '{campo}' deve estar entre 0 e 100")
        )
        return numero

    @staticmethod
    def inteiroNaoNegativo(valor, campo: str) -> int:
        """
        Inteiro >= 0. Rejeita True/False
        """
        garantir(
            type(valor) is int,
            ValidacaoError(f"O campo '{campo}' deve ser um número inteiro")
        )
        garantir(
            valor >= 0, 
            ValidacaoError(f"O campo '{campo}' não pode ser negativo")
        )
        return valor

    # MÓDULO ESTOQUE
    @staticmethod
    def inteiroPositivo(valor, campo:str) -> int:
        """
        Inteiro >= 1. Rejeita True/False
        """
        garantir(
            type(valor) is int,
            ValidacaoError(f"O campo '{campo}' deve ser um número inteiro")
        )
        garantir(
            valor >= 1,
            ValidacaoError(f"O campo '{campo}' deve ser maior que zero")
        )
        return valor
    
    @staticmethod
    def opcionalSeInformado(validador, valor, *argumentos):
        """
        Parecido com 'opcional' mas só None é "ausente", 0 e " " são validados normalmente

        Razão de existência: 'opcional' usa falso=ausente, e 0 é tido como falso
        Para casos como custo de R$0,00 isso daria resultado errado

        O dicionário escolhe o caminho pelo resultado de 'valor is None', cada valor é um lambda
        """
        tratamentos={
            True: lambda: None,
            False: lambda: validador(valor, *argumentos)
        }
        return tratamentos[valor is None]()

    @staticmethod
    def opcaoDe(enumeracao, valor, campo: str):
        """
        Converte um texto em um membro do Enum, ou levanta ValidacaoError

        Exemplo: Validador.opcaoDe(TipoInsumo, "embalagem", "tipo) -> TipoInsumo.EMBALAGEM

        Chamar o Enum como função (ex: 'TipoInsumo("embalagem")') procura a opção pelo valor e levanta erro se não existir
        """
        try:
            return enumeracao(valor)
        except ValueError as erro:
            raise ValidacaoError(f"O campo '{campo}'  tem um valor inválido: {valor!r}") from erro

    # quantidades e custos de estoque
    @classmethod
    def quantidade(cls, valor, campo: str) -> Decimal:
        """
        Quantidade >= 0 com 3 casas decimais (DER: numeric(10,3))
        """
        numero = cls._decimalNaoNegativo(valor, campo)
        garantir(
            numero < cls._LIMITE_QUANTIDADE,
            ValidacaoError(f"O campo '{campo}' excede o valor máximo permitido")
        )
        return numero.quantize(cls._MILESIMOS, rounding=ROUND_HALF_UP)

    @classmethod
    def quantidadePositiva(cls, valor, campo: str) -> Decimal:
        """
        Quantidade > 0 (fatores de conversão, consumos, entradas)
        """
        numero = cls.quantidade(valor, campo)
        garantir(
            numero > 0, 
            ValidacaoError(f"O campo '{campo}' deve ser maior que zero")
            )
        return numero
 
    @classmethod
    def quantidadeAjuste(cls, valor, campo: str) -> Decimal:
        """
        Variação de um ajuste manual: pode ser negativa (tirou do estoque) ou positiva (acrescentou), mas nunca zero
 
        `abs(x)` é o valor absoluto (sem sinal): -5 vira 5. Serve para aplicar o mesmo limite aos dois lados
        """
        numero = cls._decimal(valor, campo)
        garantir(
            abs(numero) < cls._LIMITE_QUANTIDADE,
            ValidacaoError(f"O campo '{campo}' excede o valor máximo permitido")
        )
        numero = numero.quantize(cls._MILESIMOS, rounding=ROUND_HALF_UP)
        garantir(
            numero != 0,
            ValidacaoError(f"O campo '{campo}' não pode ser zero")
        )
        return numero
 
    @classmethod
    def custoUnitario(cls, valor, campo: str) -> Decimal:
        """
        Custo por unidade >= 0 com 4 casas decimais (numeric(10,4) no DER)
        
        Mais casas que o dinheiro comum porque o custo de um grama de insumo é uma fração de centavo
        """
        numero = cls._decimalNaoNegativo(valor, campo)
        garantir(
            numero < cls._LIMITE_CUSTO_UNITARIO,
            ValidacaoError(f"O campo '{campo}' excede o valor máximo permitido")
            )
        return numero.quantize(cls._DECIMILESIMOS, rounding=ROUND_HALF_UP)