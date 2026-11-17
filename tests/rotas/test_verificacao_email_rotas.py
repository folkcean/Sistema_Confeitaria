"""
tests / rotas / test_verificacao_email_rotas.py

Verificação de e-mail pelas rotas: cadastro envia o link, o link confirma, o aviso na loja
e o reenvio (com intervalo). O e-mail vai para o EnviadorFalso (app.extensions["enviador_falso"]).

COMO RODAR SÓ ESTE ARQUIVO:   pytest tests/rotas/test_verificacao_email_rotas.py -v
"""
import pytest

from app.repositories.usuarios_rep import RepositorioUsuarios
from app.services.verificacao_email import VerificacaoEmail
from tests.falsos import EnviadorFalso


@pytest.fixture
def usuarios(conexao, seed):
    return RepositorioUsuarios(lambda: conexao)


@pytest.fixture
def enviados(app):
    """A lista de e-mails que o app mandou durante o teste"""
    return app.extensions["enviador_falso"].enviados


def dados_do_cadastro(**trocas):
    dados = {"nome": "Fulana de Tal", "apelido": "Fulana", "telefone": "22988887777",
             "email": "fulana@exemplo.com", "data_nascimento": "", "senha": "Bolo@2026",
             "confirmar_senha": "Bolo@2026"}
    return dados | trocas


def caminhoDoLink(enviado):
    """'/verificar-email/<token>' tirado do texto do e-mail (sem o http://localhost)"""
    return "/verificar-email/" + enviado["texto"].split("/verificar-email/")[1].split()[0]


# CADASTRO
def test_cadastro_envia_o_link_para_o_email_informado(navegador, enviados):
    navegador.post("/cadastro", data=dados_do_cadastro())

    assert len(enviados) == 1
    assert enviados[0]["para"] == "fulana@exemplo.com"
    assert "/verificar-email/" in enviados[0]["texto"]


def test_cadastro_com_erro_nao_envia_email(navegador, enviados):
    navegador.post("/cadastro", data=dados_do_cadastro(email="fulana"))

    assert enviados == []


def test_conta_nova_comeca_nao_verificada(navegador, usuarios):
    navegador.post("/cadastro", data=dados_do_cadastro())

    assert usuarios.buscarPorEmail("fulana@exemplo.com").email_verificado is False


def test_se_o_email_falhar_a_conta_e_criada_e_a_pessoa_e_avisada(app, navegador, usuarios, mensagens):
    app.extensions["verificacao_email"] = VerificacaoEmail(
        EnviadorFalso(falhar=True), app.extensions["usuarios"], app.config["SECRET_KEY"])

    resposta = navegador.post("/cadastro", data=dados_do_cadastro())

    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "/loja"
    assert usuarios.buscarPorEmail("fulana@exemplo.com") is not None
    assert [categoria for categoria, texto in mensagens] == ["sucesso", "aviso"]
    assert "Não conseguimos enviar o e-mail de confirmação" in mensagens[1][1]


# LINK
def test_abrir_o_link_confirma_o_email(navegador, enviados, usuarios, mensagens):
    navegador.post("/cadastro", data=dados_do_cadastro())
    mensagens.clear()
    # Outro navegador, sem login: o link funciona de qualquer aparelho
    outro_navegador = navegador.application.test_client()

    resposta = outro_navegador.get(caminhoDoLink(enviados[0]))

    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "/"
    assert mensagens == [("sucesso", "E-mail confirmado! Obrigada.")]
    assert usuarios.buscarPorEmail("fulana@exemplo.com").email_verificado is True


def test_link_inventado_mostra_erro_e_nao_confirma(navegador, usuarios, mensagens):
    resposta = navegador.get("/verificar-email/lixo")

    assert resposta.status_code == 302
    assert mensagens == [("erro", "Link de confirmação inválido")]


def test_link_vencido(navegador, enviados, mensagens, monkeypatch):
    navegador.post("/cadastro", data=dados_do_cadastro())
    mensagens.clear()
    monkeypatch.setattr(VerificacaoEmail, "VALIDADE_SEGUNDOS", -1)

    navegador.get(caminhoDoLink(enviados[0]))

    assert mensagens == [("erro", "Este link venceu. Peça um novo link de confirmação")]


# AVISO NA LOJA
def test_loja_mostra_o_aviso_para_quem_nao_confirmou(navegador, como_cliente):
    resposta = navegador.get("/loja")

    html = resposta.get_data(as_text=True)
    assert "Confirme seu e-mail" in html
    assert "ana@exemplo.com" in html
    assert "/verificar-email/reenviar" in html


def test_loja_nao_mostra_o_aviso_depois_de_confirmar(navegador, como_cliente, usuarios):
    como_cliente.marcarEmailVerificado()
    usuarios.marcarEmailVerificado(como_cliente)

    html = navegador.get("/loja").get_data(as_text=True)

    assert "Confirme seu e-mail" not in html


def test_visitante_nao_ve_o_aviso(navegador):
    assert "Confirme seu e-mail" not in navegador.get("/loja").get_data(as_text=True)


# REENVIO
def test_reenviar_manda_um_novo_link(navegador, como_cliente, enviados, mensagens):
    resposta = navegador.post("/verificar-email/reenviar")

    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "/loja"
    assert [e["para"] for e in enviados] == ["ana@exemplo.com"]
    assert mensagens == [("sucesso", "Enviamos um novo link para ana@exemplo.com.")]


def test_reenviar_duas_vezes_seguidas_e_barrado(navegador, como_cliente, enviados, mensagens):
    navegador.post("/verificar-email/reenviar")
    mensagens.clear()

    navegador.post("/verificar-email/reenviar")

    assert len(enviados) == 1
    assert mensagens == [("erro", "Aguarde um minuto antes de pedir outro e-mail de confirmação.")]


def test_reenviar_depois_do_intervalo_funciona(navegador, como_cliente, enviados):
    navegador.post("/verificar-email/reenviar")
    with navegador.session_transaction() as sessao:
        sessao["ultimo_envio_verificacao"] -= 61

    navegador.post("/verificar-email/reenviar")

    assert len(enviados) == 2


def test_reenviar_para_quem_ja_confirmou(navegador, como_cliente, usuarios, enviados, mensagens):
    como_cliente.marcarEmailVerificado()
    usuarios.marcarEmailVerificado(como_cliente)

    navegador.post("/verificar-email/reenviar")

    assert enviados == []
    assert mensagens == [("erro", "Seu e-mail já está confirmado")]


def test_reenviar_com_servidor_de_email_fora_do_ar(app, navegador, como_cliente, mensagens):
    app.extensions["verificacao_email"] = VerificacaoEmail(
        EnviadorFalso(falhar=True), app.extensions["usuarios"], app.config["SECRET_KEY"])

    navegador.post("/verificar-email/reenviar")

    assert mensagens == [("erro", "Não foi possível enviar o e-mail agora.")]


def test_visitante_nao_pode_pedir_reenvio(navegador, enviados):
    resposta = navegador.post("/verificar-email/reenviar")

    assert resposta.status_code == 302
    assert resposta.headers["Location"].startswith("/entrar")
    assert enviados == []