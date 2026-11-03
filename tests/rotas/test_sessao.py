"""
tests / rotas / test_sessao.py

"""

from urllib.parse import parse_qs, urlsplit

from app.models import Cliente
from app.services.autenticacao import Autenticacao


def token_na_sessao(navegador):
    """O token guardado na sessão do navegador (None se não tiver)"""
    with navegador.session_transaction() as sessao:
        return sessao.get("token")


def destino_do_login(resposta):
    """Do Location "/entrar?proximo=/painel", devolve ("/entrar", "/painel")"""
    endereco = urlsplit(resposta.headers["Location"])
    # parse_qs devolve uma lista por parâmetro: {"proximo": ["/painel"]}
    proximo = parse_qs(endereco.query)["proximo"][0]
    return endereco.path, proximo


def test_token_adulterado_vira_visitante_e_sai_da_sessao(navegador, como_cliente):
    with navegador.session_transaction() as sessao:
        sessao["token"] = sessao["token"][:-2] + "xx"

    resposta = navegador.get("/loja/perfil")

    assert resposta.status_code == 302
    assert token_na_sessao(navegador) is None


def test_token_vencido_vira_visitante(navegador, como_cliente, monkeypatch):
    # Validade negativa: todo token parece vencido (só durante este teste)
    monkeypatch.setattr(Autenticacao, "VALIDADE_TOKEN_SEGUNDOS", -1)

    resposta = navegador.get("/loja/perfil")

    assert resposta.status_code == 302
    assert token_na_sessao(navegador) is None


def test_conta_desativada_depois_do_login_perde_o_acesso(navegador, como_funcionario, banco):
    # O funcionário estava logado e a administradora o desligou
    banco.execute("UPDATE usuario SET ativo = false WHERE id_usuario = 2")

    resposta = navegador.get("/painel")

    assert destino_do_login(resposta) == ("/entrar", "/painel")
    assert token_na_sessao(navegador) is None


def test_token_de_usuario_que_nao_existe_vira_visitante(app, navegador):
    fantasma = Cliente("Fantasma", None, "22900000000", None, id_usuario=999)
    with navegador.session_transaction() as sessao:
        sessao["token"] = app.extensions["autenticacao"].gerarToken(fantasma)

    resposta = navegador.get("/loja/perfil")

    assert resposta.status_code == 302
    assert token_na_sessao(navegador) is None


def test_com_token_invalido_a_loja_continua_abrindo_como_visitante(navegador, templates):
    with navegador.session_transaction() as sessao:
        sessao["token"] = "lixo"

    resposta = navegador.get("/loja")

    assert resposta.status_code == 200
    assert templates[-1][1]["usuario_atual"] is None


def test_usuario_logado_vai_ao_banco_uma_vez_por_requisicao(app, navegador, como_cliente, monkeypatch):
    # O @soCliente e o menu (context_processor) perguntam quem está logado; o `g` guarda a resposta
    repositorio = app.extensions["usuarios"]
    buscar_de_verdade = repositorio.buscarPorId
    chamadas = []

    def buscar_contando(id_usuario):
        chamadas.append(id_usuario)
        return buscar_de_verdade(id_usuario)

    monkeypatch.setattr(repositorio, "buscarPorId", buscar_contando)

    navegador.get("/loja/perfil")

    assert chamadas == [10]


def test_visitante_recebe_aviso_para_entrar(navegador, mensagens):
    navegador.get("/loja/perfil")

    assert mensagens == [("aviso", "Entre na sua conta para continuar.")]


def test_proximo_guarda_tambem_a_busca_da_url(navegador):
    resposta = navegador.get("/painel/estoque?filtro=baixo&q=leite")

    assert destino_do_login(resposta) == ("/entrar", "/painel/estoque?filtro=baixo&q=leite")


def test_perfil_errado_recebe_a_pagina_403_com_o_motivo(navegador, como_cliente, templates):
    resposta = navegador.get("/painel")

    assert resposta.status_code == 403
    nome, variaveis = templates[-1]
    assert nome == "erro.html"
    assert variaveis["titulo"] == "Acesso negado"
    assert variaveis["mensagem"] == "Você não tem acesso a esta página."
