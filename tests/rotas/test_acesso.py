"""
tests / rotas / test_acesso.py

controllers/acesso.py: tela inicial, entrar (login), criar conta (cadastro) e sair

"""

from datetime import datetime, timezone

import pytest

from app.repositories.usuarios_rep import RepositorioUsuarios
from app.services.autenticacao import Autenticacao
from app.validators.senha import ValidadorSenha


@pytest.fixture
def usuarios(conexao, seed):
    """Repositório para conferir no banco o que as rotas gravaram"""
    return RepositorioUsuarios(lambda: conexao)


def token_na_sessao(navegador):
    """O token guardado na sessão do navegador (None se não tiver)"""
    with navegador.session_transaction() as sessao:
        return sessao.get("token")


def contar_usuarios(banco):
    """Quantas linhas a tabela USUARIO tem agora"""
    banco.execute("SELECT count(*) FROM usuario")
    return banco.fetchone()[0]


def test_visitante_ve_a_tela_inicial(navegador, templates):
    resposta = navegador.get("/")

    assert resposta.status_code == 200
    assert templates[-1][0] == "acesso/inicio.html"


@pytest.mark.parametrize(
    "id_usuario, destino",
    [(10, "/loja"), (2, "/painel"), (1, "/painel")],
    ids=["cliente", "funcionario", "administradora"],
)
def test_quem_ja_entrou_vai_direto_para_a_sua_area(navegador, entrar_como, id_usuario, destino):
    entrar_como(id_usuario)

    resposta = navegador.get("/")

    assert resposta.status_code == 302
    assert resposta.headers["Location"] == destino


def test_tela_de_login_recebe_o_proximo_da_url(navegador, templates):
    navegador.get("/entrar?proximo=/painel/estoque")

    nome, variaveis = templates[-1]
    assert nome == "acesso/login.html"
    assert variaveis["proximo"] == "/painel/estoque"


@pytest.mark.parametrize(
    "email, destino",
    [
        ("ana@exemplo.com", "/loja"),
        ("joao@confeitaria.local", "/painel"),
        ("rosangela@confeitaria.local", "/painel"),
    ],
    ids=["cliente", "funcionario", "administradora"],
)
def test_login_certo_leva_para_a_area_do_perfil(navegador, senha_forte, email, destino):
    resposta = navegador.post("/entrar", data={"email": email, "senha": senha_forte})

    assert resposta.status_code == 302
    assert resposta.headers["Location"] == destino


def test_login_guarda_na_sessao_o_token_do_usuario(app, navegador, senha_forte):
    navegador.post("/entrar", data={"email": "ana@exemplo.com", "senha": senha_forte})

    dados = app.extensions["autenticacao"].validarToken(token_na_sessao(navegador))
    assert dados == {"uid": 10, "perfil": "cliente"}


def test_login_da_boas_vindas_com_o_primeiro_nome(navegador, mensagens, senha_forte):
    navegador.post("/entrar", data={"email": "ana@exemplo.com", "senha": senha_forte})

    assert mensagens == [("sucesso", "Bem-vindo(a) de volta, Ana.")]


def test_login_aceita_email_com_maiusculas_e_espacos(navegador, senha_forte):
    resposta = navegador.post("/entrar", data={"email": "  ANA@EXEMPLO.COM ", "senha": senha_forte})

    assert resposta.headers["Location"] == "/loja"


def test_login_volta_para_a_pagina_que_pediu_o_login(navegador, senha_forte):
    resposta = navegador.post(
        "/entrar",
        data={"email": "ana@exemplo.com", "senha": senha_forte, "proximo": "/loja/perfil/enderecos"},
    )

    assert resposta.headers["Location"] == "/loja/perfil/enderecos"


@pytest.mark.parametrize(
    "email, senha",
    [
        ("ana@exemplo.com", "senha-errada"),
        ("ninguem@exemplo.com", "Bolo@2026"),
        # Eduardo existe e a senha está certa, mas a conta foi desativada
        ("edu@exemplo.com", "Bolo@2026"),
    ],
    ids=["senha_errada", "email_inexistente", "conta_desativada"],
)
def test_login_que_falha_mostra_a_mesma_mensagem_para_qualquer_motivo(navegador, templates, mensagens, email, senha):
    resposta = navegador.post("/entrar", data={"email": email, "senha": senha})

    assert resposta.status_code == 400
    assert templates[-1][0] == "acesso/login.html"
    # Mesma mensagem sempre: ninguém descobre quais e-mails têm conta (requisito 9.6)
    assert mensagens == [("erro", Autenticacao.MENSAGEM_FALHA)]
    assert token_na_sessao(navegador) is None


def test_login_que_falha_continua_lembrando_o_proximo(navegador, templates):
    navegador.post("/entrar", data={"email": "ana@exemplo.com", "senha": "x", "proximo": "/loja/perfil"})

    assert templates[-1][1]["proximo"] == "/loja/perfil"


def test_lembrar_de_mim_deixa_o_cookie_valendo_por_14_dias(navegador, senha_forte):
    navegador.post("/entrar", data={"email": "ana@exemplo.com", "senha": senha_forte, "lembrar": "on"})

    # Cookie com data de validade (expires) continua depois que o navegador fecha
    validade = navegador.get_cookie("session").expires - datetime.now(timezone.utc)
    assert round(validade.total_seconds() / 86400) == 14


def test_sem_lembrar_de_mim_o_cookie_some_ao_fechar_o_navegador(navegador, senha_forte):
    navegador.post("/entrar", data={"email": "ana@exemplo.com", "senha": senha_forte})

    # Sem data de validade, é um cookie "de sessão": o navegador apaga quando fecha
    assert navegador.get_cookie("session").expires is None


def test_cinco_senhas_erradas_bloqueiam_ate_a_senha_certa(navegador, mensagens, senha_forte):
    for _ in range(5):
        navegador.post("/entrar", data={"email": "ana@exemplo.com", "senha": "senha-errada"})

    resposta = navegador.post("/entrar", data={"email": "ana@exemplo.com", "senha": senha_forte})

    assert resposta.status_code == 400
    assert mensagens[-1] == ("erro", "Muitas tentativas incorretas, tente novamente em alguns minutos")


@pytest.mark.xfail(
    strict=True,
    reason="Redirecionamento aberto: o `proximo` vem do formulário e o login redireciona para "
           "qualquer endereço, até outro site. Um link falso de /entrar?proximo=https://... manda a "
           "pessoa, já logada, para fora da confeitaria",
)
def test_login_nao_redireciona_para_outro_site(navegador, senha_forte):
    resposta = navegador.post(
        "/entrar",
        data={"email": "ana@exemplo.com", "senha": senha_forte, "proximo": "https://site-falso.com/entrar"},
    )

    # O esperado: ignorar o `proximo` de fora e ir para a área do perfil
    assert resposta.headers["Location"] == "/loja"


def dados_do_cadastro(**trocas):
    """Formulário de cadastro preenchido certo; `trocas` muda algum campo"""
    dados = {
        "nome": "Fulana de Tal",
        "apelido": "Fulana",
        "telefone": "(22) 98888-7777",
        "email": "fulana@exemplo.com",
        "data_nascimento": "2000-01-15",
        "senha": "Bolo@2026",
        "confirmar_senha": "Bolo@2026",
    }
    return dados | trocas


def test_tela_de_cadastro_mostra_as_regras_da_senha(navegador, templates):
    navegador.get("/cadastro")

    nome, variaveis = templates[-1]
    assert nome == "acesso/cadastro.html"
    # As mesmas regras que o validador cobra: mudou lá, a tela acompanha
    assert variaveis["regras_senha"] == [regra.descricao for regra in ValidadorSenha.REGRAS]


def test_cadastro_cria_a_conta_e_vai_para_a_loja(navegador, mensagens, usuarios):
    resposta = navegador.post("/cadastro", data=dados_do_cadastro())

    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "/loja"
    assert mensagens == [("sucesso", "Conta criada! Que bom ter você aqui.")]
    nova = usuarios.buscarPorEmail("fulana@exemplo.com")
    assert nova.nome == "Fulana de Tal"
    assert nova.telefone == "22988887777"
    assert nova.apelido == "Fulana"
    # Pela loja o CPF não é pedido
    assert nova.cpf_persistencia is None


def test_cadastro_ja_deixa_a_pessoa_logada(app, navegador, usuarios):
    navegador.post("/cadastro", data=dados_do_cadastro())

    nova = usuarios.buscarPorEmail("fulana@exemplo.com")
    dados = app.extensions["autenticacao"].validarToken(token_na_sessao(navegador))
    assert dados == {"uid": nova.id, "perfil": "cliente"}


def test_cadastro_grava_a_senha_e_ela_serve_para_entrar(app, navegador):
    navegador.post("/cadastro", data=dados_do_cadastro())
    # Outro navegador, sem a sessão do cadastro: precisa entrar com e-mail e senha
    outro_navegador = app.test_client()

    resposta = outro_navegador.post("/entrar", data={"email": "fulana@exemplo.com", "senha": "Bolo@2026"})

    assert resposta.headers["Location"] == "/loja"


def test_cadastro_sem_apelido_e_sem_nascimento(navegador, usuarios):
    navegador.post("/cadastro", data=dados_do_cadastro(apelido="", data_nascimento=""))

    nova = usuarios.buscarPorEmail("fulana@exemplo.com")
    assert nova.apelido == "Fulana de Tal"
    assert nova.data_nascimento is None


@pytest.mark.parametrize(
    "trocas, mensagem",
    [
        ({"confirmar_senha": "Bolo@2027"}, "As senhas não são iguais."),
        # No model o e-mail é opcional, mas o login é por e-mail: na loja ele é obrigatório
        ({"email": ""}, "O campo 'e-mail' é obrigatório"),
        ({"email": "fulana"}, "E-mail inválido"),
        ({"nome": ""}, "O campo 'nome' é obrigatório"),
        ({"telefone": "123"}, "Telefone inválido: informe DDD + número"),
        ({"data_nascimento": "2999-01-01"}, "A data de nascimento não pode estar no futuro"),
        ({"senha": "fraca", "confirmar_senha": "fraca"},
         "A senha deve ter entre 8 e 128 caracteres, conter números, conter ao menos um caractere especial (ex.: @, #, !)."),
        # Telefone e e-mail da Ana: o banco recusa (UNIQUE)
        ({"telefone": "22999990010"}, "Já existe uma conta com este e-mail, telefone ou CPF."),
        ({"email": "ana@exemplo.com"}, "Já existe uma conta com este e-mail, telefone ou CPF."),
    ],
    ids=[
        "senhas_diferentes", "sem_email", "email_invalido", "sem_nome", "telefone_invalido",
        "nascimento_no_futuro", "senha_fraca", "telefone_repetido", "email_repetido",
    ],
)
def test_cadastro_com_problema_volta_para_o_formulario(navegador, banco, templates, mensagens, trocas, mensagem):
    antes = contar_usuarios(banco)

    resposta = navegador.post("/cadastro", data=dados_do_cadastro(**trocas))

    assert resposta.status_code == 400
    assert templates[-1][0] == "acesso/cadastro.html"
    assert mensagens == [("erro", mensagem)]
    assert contar_usuarios(banco) == antes
    assert token_na_sessao(navegador) is None


@pytest.mark.xfail(
    strict=True,
    raises=NameError,
    reason="acesso.sair chama `predirect` (erro de digitação de `redirect`): sair da conta dá erro 500",
)
def test_sair_limpa_a_sessao_e_volta_para_o_inicio(navegador, como_cliente, mensagens):
    resposta = navegador.get("/sair")

    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "/"
    assert token_na_sessao(navegador) is None
    assert mensagens == [("info", "Você saiu da sua conta.")]
