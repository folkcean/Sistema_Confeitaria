"""
app / validators / senha.py

Regras de força da senha (tamanho, letras, números, caractere especial)

Aqui só decide se a senha é forte o suficiente. Guardar/proteger a senha é outra resposabilidade, e fica em app / models / senha.py

Ideia: Cada exigência é um objeto (RegraSenha), para criar uma nova exigência basta acrescentar um item na lista REGRAS
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.exceptions import SenhaFracaError
from app.validators.campos import garantir


# @dataclass(frozen=True) acima da classe é uma função que "embrulha" a classe e acrescenta comportamento
# 1. cria o __init__ sozinho
# 2. com frozen=True deixa o objeto imutável
@dataclass(frozen=True)
class RegraSenha:
    """
    Uma exigência da senha: descrição (para a mensagem de erro) + padrão que a senha precisa casar
    """

    descricao: str
    padrao: re.Pattern

    def violada(self, senha: str) -> bool:
        """
        True se a senha NÃO casa com o padrão da regra
        """
        # .search procura o padrão em qualquer lugar do texto: devolve um objeto (verdadeiro) se achou, None se não
        # `not` inverte: achou => False (não violou); não achou => True (violou)
        return not self.padrao.search(senha)


class ValidadorSenha:
    """
    Aplica todas as RegraSenha e informa de uma vez tudo o que está errado
    """

    #   \A.{8,128}\Z  -> do início (\A) ao fim (\Z) do texto, de 8 a 128 quaisquer caracteres
    #   [A-Za-z]      -> pelo menos uma letra
    #   \d            -> pelo menos um dígito
    #   [^A-Za-z0-9]  -> pelo menos um caractere que NÃO seja letra nem número (o ^ dentro de [] significa "não")
    REGRAS = (
        RegraSenha(
            "ter entre 8 e 128 caracteres", re.compile(r"\A.{8,128}\Z", re.DOTALL)
        ),
        RegraSenha("conter letras", re.compile(r"[A-Za-z]")),
        RegraSenha("conter números", re.compile(r"\d")),
        RegraSenha(
            "conter ao menos um caractere especial (ex.: @, #, !)",
            re.compile(r"[^A-Za-z0-9]"),
        ),
    )

    @classmethod
    def validar(cls, senha: str) -> None:
        """
        Acumula as regras violadas e lança um único SenhaFracaError com a lista completa
        """

        # Se vier None, usa texto vazio
        texto = senha or ""
        # filter(funcao, lista) devolve só os itens em que a função devolve verdadeiro
        violadas = filter(lambda regra: regra.violada(texto), cls.REGRAS)
        # Monta uma lista nova a partir de outra -> descrição de cada regra violada
        problemas = [regra.descricao for regra in violadas]
        # Lista vazia é falsa: `not problemas` é True quando nenhuma regra foi violada -> senha ok
        garantir(
            not problemas, SenhaFracaError("A senha deve " + ", ".join(problemas) + ".")
        )
        garantir(
            not problemas, SenhaFracaError("A senha deve " + ", ".join(problemas) + ".")
        )
