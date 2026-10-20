"""
app / services / controle_login.py

Controle de tentativas de login

Padrão "State":
    Cada e-mail está sempre em UM de dois estados:
        Livre      -> pode tentar logar (guarda quantas falhas seguidas já ocorreram)
        Bloqueado  -> não pode tentar até certo horário

    Fluxo:  Livre(0) -> falha -> Livre(1) -> ... -> Livre(4) -> falha -> Bloqueado(até daqui a 15 min)
            Bloqueado -> (passam 15 min) -> nova falha -> Livre(1)   (recomeça a contar)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from app.exceptions import AutenticacaoError
from app.validators.campos import garantir


class EstadoLogin(ABC):
    """
    Contrato dos estados possíveis de um identificador
    """

    @abstractmethod
    def bloqueado(self, agora: datetime) -> bool:
        """True se o login deve ser recusado neste momento"""

    @abstractmethod
    def aposFalha(self, politica: PoliticaBloqueio, agora: datetime) -> EstadoLogin:
        """Devolve o novo estado depois de mais uma senha incorreta"""


class PoliticaBloqueio:
    """
    Define quantas falhas são toleradas e por quanto tempo o bloqueio dura
    """

    def __init__(
        self, max_tentativas: int = 5, tempo_bloqueio: timedelta = timedelta(minutes=15)
    ):
        """Guarda os limites"""
        self._max_tentativas = max_tentativas
        self._tempo_bloqueio = tempo_bloqueio

    def estadoPara(self, tentativas: int, agora: datetime) -> EstadoLogin:
        """
        Escolhe o estado conforme o número de falhas: atingiu o limite -> Bloqueado; senão -> Livre
        """
        fabricas = {
            True: lambda: Bloqueado(agora + self._tempo_bloqueio),
            False: lambda: Livre(tentativas),
        }
        return fabricas[tentativas >= self._max_tentativas]()


class Livre(EstadoLogin):
    """
    Pode tentar logar, guarda quantas falhas seguidas já ocorreram
    """

    def __init__(self, tentativas: int = 0):
        """Número de falhas seguidas"""
        self._tentativas = tentativas

    def bloqueado(self, agora: datetime) -> bool:
        """Estado livre nunca bloqueia"""
        return False

    def aposFalha(self, politica: PoliticaBloqueio, agora: datetime) -> EstadoLogin:
        """Soma uma falha e deixa a política decidir se já é hora de bloquear"""
        return politica.estadoPara(self._tentativas + 1, agora)


class Bloqueado(EstadoLogin):
    """
    Login recusado até um determinado horário
    """

    def __init__(self, ate: datetime):
        """Horário em que o bloqueio termina"""
        self._ate = ate

    def bloqueado(self, agora: datetime) -> bool:
        """Bloqueado enquanto o horário atual não passou do fim do bloqueio"""
        return agora < self._ate

    def aposFalha(self, politica: PoliticaBloqueio, agora: datetime) -> EstadoLogin:
        """
        Só chega aqui depois que o bloqueio expirou (antes disso o login é recusado sem conferir senha)
        Uma nova falha recomeça a contagem do zero -> falha número 1
        """
        return politica.estadoPara(1, agora)


class ControleLogin:
    """
    Guarda o estado de cada identificador (e-mail) e aplica a política
    """

    def __init__(self, politica: PoliticaBloqueio | None = None):
        """Usa a política padrão (5 falhas, 15 min) se nenhuma for informada"""
        self._politica = politica or PoliticaBloqueio()
        self._estados: dict[str, EstadoLogin] = {}

    def exigirLiberado(self, chave: str) -> None:
        """Lança AutenticacaoError se o identificador estiver bloqueado agora"""
        estado = self._estados.get(chave, Livre())
        garantir(
            not estado.bloqueado(datetime.now()),
            AutenticacaoError(
                "Muitas tentativas incorretas, tente novamente em alguns minutos"
            ),
        )

    def registrarFalha(self, chave: str) -> None:
        """Pede ao estado atual qual é o próximo estado após a falha e guarda"""
        estado = self._estados.get(chave, Livre())
        self._estados[chave] = estado.aposFalha(self._politica, datetime.now())

    def limpar(self, chave: str) -> None:
        """Login bem-sucedido: esquece as falhas anteriores"""
        self._estados.pop(chave, None)
