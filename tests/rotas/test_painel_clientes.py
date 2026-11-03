"""
tests / rotas / test_painel_clientes.py

"""

import pytest

from app.repositories.clientes_rep import RepositorioClientes

pytestmark = pytest.mark.usefixtures("como_admin")

ATIVOS_EM_ORDEM = ["Ana Souza", "Antonio Peixoto", "Bruno Carvalho", "Carla Nunes", "Daniela Moreira"]


@pytest.fixture
def clientes(conexao, seed):
    """Repositório para conferir no banco o que as rotas gravaram"""
    return RepositorioClientes(lambda: conexao)


def nomes(lista):
    """Só os nomes, na ordem em que vieram"""
    return [item.nome for item in lista]


def formulario_do_cliente(**trocas):
    """Formulário de cliente preenchido certo (como quem pede pelo WhatsApp); `trocas` muda algum campo"""
    dados = {
        "nome": "Gabriela Rocha",
        "apelido": "Gabi",
        "telefone": "(22) 98765-4321",
        "email": "",
        "cpf": "",
        "data_nascimento": "",
        "instagram": "",
        "restricoes_alimentares": "Sem glúten",
        "preferencias": "",
        "observacoes": "Pede pelo WhatsApp",
    }
    return dados | trocas


def formulario_da_ana(**trocas):
    """Formulário de edição com os dados atuais da Ana; `trocas` muda algum campo"""
    dados = {
        "nome": "Ana Souza",
        "apelido": "Aninha",
        "telefone": "22999990010",
        "email": "ana@exemplo.com",
        "cpf": "529.982.247-25",
        "data_nascimento": "1992-11-05",
        "instagram": "@anasouza",
        "restricoes_alimentares": "",
        "preferencias": "Bolo de chocolate",
        "observacoes": "",
    }
    return dados | trocas


def contar_usuarios(banco):
    """Quantas linhas a tabela USUARIO tem agora"""
    banco.execute("SELECT count(*) FROM usuario")
    return banco.fetchone()[0]


def test_lista_mostra_os_clientes_ativos(navegador, templates):
    resposta = navegador.get("/painel/clientes")

    assert resposta.status_code == 200
    nome, variaveis = templates[-1]
    assert nome == "painel/clientes.html"
    assert nomes(variaveis["clientes"]) == ATIVOS_EM_ORDEM


@pytest.mark.parametrize(
    "filtro, esperados",
    [("vip", ["Bruno Carvalho"]), ("inativos", ["Eduardo Lima"]), ("aba-que-nao-existe", ATIVOS_EM_ORDEM)],
)
def test_cada_aba_mostra_os_seus_clientes(navegador, templates, filtro, esperados):
    navegador.get(f"/painel/clientes?filtro={filtro}")

    variaveis = templates[-1][1]
    assert nomes(variaveis["clientes"]) == esperados
    assert variaveis["filtro"] == filtro


@pytest.mark.parametrize("busca, esperados", [("ana", ["Ana Souza"]), ("0013", ["Antonio Peixoto"])])
def test_busca_por_nome_ou_telefone(navegador, templates, busca, esperados):
    navegador.get(f"/painel/clientes?q={busca}")

    variaveis = templates[-1][1]
    assert nomes(variaveis["clientes"]) == esperados
    assert variaveis["busca"] == busca


def test_ficha_traz_os_dados_completos_com_o_cpf(navegador, templates):
    resposta = navegador.get("/painel/clientes/10")

    assert resposta.status_code == 200
    nome, variaveis = templates[-1]
    assert nome == "painel/cliente.html"
    assert variaveis["cliente"].id == 10
    # A administradora vê tudo, inclusive o CPF (requisito 13.1)
    assert variaveis["dados"]["cpf"] == "52998224725"
    assert variaveis["dados"]["enderecos"] == [
        "Rua Ouvidor, 889 - Jockey Club, Campos dos Goytacazes - CEP 28020-493",
        "Rua Santa Rosa, 1473, Sala 659 - Pelinca, Campos dos Goytacazes - CEP 28035-573",
    ]


@pytest.mark.parametrize("id_usuario", [1, 2, 999], ids=["administradora", "funcionario", "inexistente"])
@pytest.mark.parametrize(
    "metodo, url",
    [
        ("GET", "/painel/clientes/{}"),
        ("GET", "/painel/clientes/{}/editar"),
        ("POST", "/painel/clientes/{}/editar"),
        ("POST", "/painel/clientes/{}/vip"),
        ("GET", "/painel/clientes/{}/desativar"),
        ("POST", "/painel/clientes/{}/desativar"),
        ("POST", "/painel/clientes/{}/reativar"),
    ],
)
def test_quem_nao_e_cliente_da_404(navegador, metodo, url, id_usuario):
    # Sem isso, daria para desativar a administradora pela tela de clientes
    assert navegador.open(url.format(id_usuario), method=metodo).status_code == 404


def test_formulario_de_cliente_novo(navegador, templates):
    navegador.get("/painel/clientes/novo")

    nome, variaveis = templates[-1]
    assert nome == "painel/cliente_form.html"
    assert (variaveis["cliente"], variaveis["dados"]) == (None, None)


def test_cadastrar_cliente_grava_sem_senha_e_abre_a_ficha(navegador, mensagens, clientes, banco):
    resposta = navegador.post("/painel/clientes/novo", data=formulario_do_cliente())

    gabi = clientes.listarClientes(busca="Gabriela")[0]
    assert resposta.status_code == 302
    assert resposta.headers["Location"] == f"/painel/clientes/{gabi.id}"
    assert mensagens == [("sucesso", "Gabriela Rocha cadastrado.")]
    assert gabi.telefone == "22987654321"
    assert gabi.email is None
    assert gabi.restricoes_alimentares == "Sem glúten"
    assert gabi.cliente_vip is False
    # Cadastrado pelo painel não tem senha: a pessoa cria a conta na loja depois, se quiser
    banco.execute("SELECT senha_hash FROM usuario WHERE id_usuario = %s", (gabi.id,))
    assert banco.fetchone() == (None,)


def test_cadastrar_com_vip_marcado(navegador, clientes):
    # Checkbox marcado vai no formulário; desmarcado, não vai
    navegador.post("/painel/clientes/novo", data=formulario_do_cliente(cliente_vip="on"))

    assert clientes.listarClientes(filtro="vip", busca="Gabriela")[0].cliente_vip is True


@pytest.mark.parametrize(
    "trocas, mensagem",
    [
        ({"nome": ""}, "O campo 'nome' é obrigatório"),
        ({"telefone": "123"}, "Telefone inválido: informe DDD + número"),
        ({"cpf": "111.111.111-11"}, "CPF inválido"),
        ({"email": "gabi"}, "E-mail inválido"),
        # Telefone e CPF da Ana: o banco recusa (UNIQUE)
        ({"telefone": "22999990010"}, "Já existe uma conta com este e-mail, telefone ou CPF."),
        ({"cpf": "529.982.247-25"}, "Já existe uma conta com este e-mail, telefone ou CPF."),
    ],
    ids=["sem_nome", "telefone_invalido", "cpf_invalido", "email_invalido", "telefone_repetido", "cpf_repetido"],
)
def test_cadastrar_com_problema_nao_grava_nada(navegador, templates, mensagens, banco, trocas, mensagem):
    antes = contar_usuarios(banco)

    resposta = navegador.post("/painel/clientes/novo", data=formulario_do_cliente(**trocas))

    assert resposta.status_code == 400
    assert templates[-1][0] == "painel/cliente_form.html"
    assert mensagens == [("erro", mensagem)]
    assert contar_usuarios(banco) == antes


def test_formulario_de_edicao_vem_preenchido(navegador, templates):
    navegador.get("/painel/clientes/10/editar")

    nome, variaveis = templates[-1]
    assert nome == "painel/cliente_form.html"
    assert variaveis["cliente"].id == 10
    assert variaveis["dados"]["cpf"] == "52998224725"


def test_editar_grava_e_volta_para_a_ficha(navegador, mensagens, clientes):
    resposta = navegador.post(
        "/painel/clientes/10/editar",
        data=formulario_da_ana(nome="Ana Souza Lima", restricoes_alimentares="Sem lactose", cpf=""),
    )

    assert resposta.headers["Location"] == "/painel/clientes/10"
    assert mensagens == [("sucesso", "Ana Souza Lima atualizado.")]
    ana = clientes.buscarPorId(10)
    assert ana.nome == "Ana Souza Lima"
    assert ana.restricoes_alimentares == "Sem lactose"
    # O CPF não tem setter no model: a edição monta o cliente de novo, e CPF em branco vira NULL
    assert ana.cpf_persistencia is None


def test_editar_mantem_senha_conta_ativa_e_data_de_cadastro(navegador, clientes, senha_forte):
    antes = clientes.buscarPorId(10)

    navegador.post("/painel/clientes/10/editar", data=formulario_da_ana(nome="Ana Souza Lima"))

    depois = clientes.buscarPorId(10)
    assert depois.verificarSenha(senha_forte) is True
    assert depois.ativo is True
    assert depois.data_cadastro == antes.data_cadastro


def test_editar_cliente_desativado_nao_o_reativa(navegador, clientes):
    navegador.post(
        "/painel/clientes/15/editar",
        data=formulario_da_ana(nome="Eduardo Lima", apelido="Edu", telefone="22999990015", email="edu@exemplo.com",
                               cpf="048.764.529-46"),
    )

    assert clientes.buscarPorId(15).ativo is False


def test_editar_com_problema_nao_grava_nada(navegador, templates, mensagens, clientes):
    resposta = navegador.post(
        "/painel/clientes/10/editar", data=formulario_da_ana(nome="Nome Que Não Pode Ficar", telefone="22999990011")
    )

    assert resposta.status_code == 400
    assert templates[-1][1]["cliente"].id == 10
    assert mensagens == [("erro", "Já existe uma conta com este e-mail, telefone ou CPF.")]
    assert clientes.buscarPorId(10).nome == "Ana Souza"


def test_vip_liga_e_desliga(navegador, mensagens, clientes):
    navegador.post("/painel/clientes/10/vip")
    assert clientes.buscarPorId(10).cliente_vip is True

    resposta = navegador.post("/painel/clientes/10/vip")

    assert resposta.headers["Location"] == "/painel/clientes/10"
    assert clientes.buscarPorId(10).cliente_vip is False
    assert mensagens == [("sucesso", "Ana Souza agora é VIP."), ("sucesso", "Ana Souza não é mais VIP.")]


def test_desativar_pergunta_antes(navegador, templates):
    navegador.get("/painel/clientes/10/desativar")

    nome, variaveis = templates[-1]
    assert nome == "confirmar.html"
    assert variaveis["titulo"] == "Desativar Ana Souza?"
    assert variaveis["acao"] == "/painel/clientes/10/desativar"
    assert variaveis["voltar"] == "/painel/clientes/10"


def test_desativar_cliente_oferece_desfazer(navegador, mensagens, clientes):
    resposta = navegador.post("/painel/clientes/10/desativar")

    assert resposta.headers["Location"] == "/painel/clientes/10"
    assert clientes.buscarPorId(10).ativo is False
    assert mensagens == [("desfazer:/painel/clientes/10/reativar", "Ana Souza desativado.")]


def test_cliente_desativado_nao_consegue_mais_entrar_na_loja(app, navegador, senha_forte):
    navegador.post("/painel/clientes/10/desativar")
    navegador_da_ana = app.test_client()

    resposta = navegador_da_ana.post("/entrar", data={"email": "ana@exemplo.com", "senha": senha_forte})

    assert resposta.status_code == 400


def test_desativar_quem_ja_esta_inativo(navegador, mensagens, clientes):
    navegador.post("/painel/clientes/15/desativar")

    assert mensagens == [("erro", "Eduardo Lima já está inativo.")]
    assert clientes.buscarPorId(15).ativo is False


def test_reativar_cliente(navegador, mensagens, clientes):
    resposta = navegador.post("/painel/clientes/15/reativar")

    assert resposta.headers["Location"] == "/painel/clientes/15"
    assert clientes.buscarPorId(15).ativo is True
    assert mensagens == [("sucesso", "Eduardo Lima reativado.")]


def test_reativar_quem_ja_esta_ativo(navegador, mensagens, clientes):
    navegador.post("/painel/clientes/10/reativar")

    assert mensagens == [("erro", "Ana Souza já está ativo.")]
    assert clientes.buscarPorId(10).ativo is True
