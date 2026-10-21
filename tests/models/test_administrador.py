import pytest

from app.exceptions import AcessoNegadoError
from app.models.administrador import Administrador
from app.models.enums import Perfil


class RecomendadorEspiao:
    """Recomendador de mentira: anota a chamada e devolve uma lista fixa"""

    def __init__(self):
        self.chamadas = []

    def recomendar(self, estoque, historico):
        self.chamadas.append((estoque, historico))
        return [{"ingrediente": "farinha", "comprar": 10}]


class EstoqueFalso:
    """Estoque de mentira: resumo fixo e ajustes anotados"""

    def __init__(self):
        self.ajustes = []

    def resumo(self):
        return [{"ingrediente": "farinha", "quantidade": 5000}]

    def ajustarManual(self, ingrediente, nova_quantidade, motivo):
        self.ajustes.append((ingrediente, nova_quantidade, motivo))


def test_administrador_tem_padroes_total_e_sem_acesso_financeiro(administrador):
    assert administrador.nivel_privilegio == "total"
    assert administrador.acesso_financeiro is False


def test_administrador_tem_perfil_administrador_e_acessa_dados_sensiveis(administrador):
    assert administrador.perfil is Perfil.ADMINISTRADOR
    assert administrador.acessa_dados_sensiveis is True


def test_ajustar_estoque_repassa_os_tres_argumentos_ao_estoque(administrador):
    estoque = EstoqueFalso()

    administrador.ajustarEstoque(estoque, "farinha", 3000, "contagem")

    assert estoque.ajustes == [("farinha", 3000, "contagem")]


def test_relatorio_sem_acesso_financeiro_levanta_erro_e_nao_chama_o_recomendador(
    administrador,
):
    recomendador = RecomendadorEspiao()

    with pytest.raises(AcessoNegadoError, match="acesso a relatórios financeiros"):
        administrador.gerarRelatorioReposicao(recomendador, EstoqueFalso(), [])

    assert recomendador.chamadas == []


def test_relatorio_com_acesso_financeiro_devolve_a_lista_do_recomendador():
    administrador = Administrador(
        "Rosângela Crespo", None, "22999990003", None, acesso_financeiro=True
    )
    recomendador = RecomendadorEspiao()
    estoque = EstoqueFalso()
    historico = ["historico de exemplo"]

    resultado = administrador.gerarRelatorioReposicao(recomendador, estoque, historico)

    assert resultado == [{"ingrediente": "farinha", "comprar": 10}]
    assert recomendador.chamadas == [(estoque, historico)]
