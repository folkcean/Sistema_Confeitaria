"""
tests / rotas / test_painel_ia.py

controllers/painel.py, aba Assistente IA: abrir a aba, gerar recomendações, perguntar
(digitado, atalho e foco num insumo) e os erros (API fora do ar, pergunta vazia, sem acesso financeiro)

O app de teste usa o ModeloFalso no lugar da Groq (tests/rotas/conftest.py): nada vai para a internet
"""
import pytest

from app.exceptions import GatewayIAError

pytestmark = pytest.mark.usefixtures("como_admin")


@pytest.fixture
def modelo(app):
    """O ModeloFalso que o app está usando (para combinar a resposta e conferir as chamadas)"""
    return app.extensions["ia"]


def test_abrir_a_aba_nao_chama_a_ia(navegador, modelo, templates):
    resposta = navegador.get("/painel/ia")

    assert resposta.status_code == 200
    assert templates[-1][0] == "painel/ia.html"
    assert modelo.chamadas == []
    # O <select> já vem com os insumos ativos
    assert ("Acucar refinado", "Acucar refinado") in templates[-1][1]["opcoes_insumo"]


def test_recomendacoes_mandam_o_banco_e_mostram_o_resultado(navegador, modelo, templates):
    resposta = navegador.post("/painel/ia/recomendacoes")

    assert resposta.status_code == 200
    # O retrato do banco foi junto, e as regras do reposicao.md foram como instruções
    assert "Acucar refinado" in modelo.chamadas[0]["mensagem"]
    assert "Regras de reposição" in modelo.chamadas[0]["instrucoes"]
    # A tela mostra o motivo e a data no formato brasileiro
    html = resposta.get_data(as_text=True)
    assert "Já está abaixo do mínimo." in html
    assert "pedir até 17/11/2026" in html
    assert templates[-1][1]["resultado"]["recomendacoes"][0]["prioridade"] == "alta"


def test_api_fora_do_ar_mostra_o_erro(navegador, modelo, mensagens):
    modelo.erro = GatewayIAError("Não foi possível falar com a API de IA: sem internet")

    resposta = navegador.post("/painel/ia/recomendacoes")

    assert resposta.status_code == 502
    assert mensagens == [("erro", "Não foi possível falar com a API de IA: sem internet")]


def test_pergunta_mostra_a_resposta(navegador, modelo):
    modelo.resposta = "Vai faltar leite condensado."

    resposta = navegador.post("/painel/ia/pergunta", data={"pergunta": "O que vai faltar?"})

    assert resposta.status_code == 200
    assert "Vai faltar leite condensado." in resposta.get_data(as_text=True)
    assert modelo.chamadas[0]["mensagem"].endswith("O que vai faltar?")


def test_atalho_manda_o_texto_da_tabela_e_nao_o_do_formulario(navegador, modelo):
    navegador.post("/painel/ia/pergunta", data={"atalho": "faltar", "pergunta": ""})

    assert modelo.chamadas[0]["mensagem"].endswith("O que vai faltar para os pedidos desta semana?")


def test_insumo_sem_pergunta_pede_a_explicacao_dele(navegador, modelo):
    navegador.post("/painel/ia/pergunta", data={"insumo": "Farinha de trigo", "pergunta": ""})

    assert "Sobre o insumo Farinha de trigo: Explique a situação deste insumo" in modelo.chamadas[0]["mensagem"]


def test_pergunta_vazia_volta_400(navegador, modelo, mensagens):
    resposta = navegador.post("/painel/ia/pergunta", data={"pergunta": "   "})

    assert resposta.status_code == 400
    assert modelo.chamadas == []
    assert mensagens == [("erro", "Escreva a pergunta antes de enviar.")]


def test_administrador_sem_acesso_financeiro_nao_chama_a_ia(navegador, modelo, banco):
    banco.execute("UPDATE administrador SET acesso_financeiro = false WHERE id_usuario = 1")

    assert navegador.get("/painel/ia").status_code == 403
    assert navegador.post("/painel/ia/recomendacoes").status_code == 403
    assert navegador.post("/painel/ia/pergunta", data={"pergunta": "Oi"}).status_code == 403
    assert modelo.chamadas == []