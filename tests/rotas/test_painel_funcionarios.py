"""
tests / rotas / test_painel_funcionarios.py

controllers/painel.py, funcionários (só a administração): lista da equipe, cadastro com senha
inicial, edição (com ou sem senha nova), desligar e reativar

"""

from datetime import date

import pytest

from app.repositories.funcionarios_rep import RepositorioFuncionarios
from app.validators.senha import ValidadorSenha

# Todo teste deste arquivo entra como a administradora
pytestmark = pytest.mark.usefixtures("como_admin")


@pytest.fixture
def funcionarios(conexao, seed):
    """Repositório para conferir no banco o que as rotas gravaram"""
    return RepositorioFuncionarios(lambda: conexao)


def formulario_da_funcionaria(**trocas):
    """Formulário de funcionária nova preenchido certo; `trocas` muda algum campo"""
    dados = {
        "nome": "Paula Mendes",
        "email": "paula@confeitaria.local",
        "telefone": "22988881111",
        "cpf": "",
        "cargo": "Confeiteira",
        "data_nascimento": "1995-04-10",
        "data_contratacao": "2026-10-01",
        "senha": "Bolo@2026",
    }
    return dados | trocas


def formulario_do_joao(**trocas):
    """Formulário de edição com os dados atuais do Joao (senha em branco); `trocas` muda algum campo"""
    dados = {
        "nome": "Joao Pedro Viana",
        "email": "joao@confeitaria.local",
        "telefone": "22999990002",
        "cpf": "879.730.911-73",
        "cargo": "Auxiliar de cozinha",
        "data_nascimento": "1999-07-02",
        "data_contratacao": "2025-12-01",
        "senha": "",
    }
    return dados | trocas


def contar_usuarios(banco):
    """Quantas linhas a tabela USUARIO tem agora"""
    banco.execute("SELECT count(*) FROM usuario")
    return banco.fetchone()[0]


def test_lista_mostra_a_equipe(navegador, templates):
    resposta = navegador.get("/painel/funcionarios")

    assert resposta.status_code == 200
    nome, variaveis = templates[-1]
    assert nome == "painel/funcionarios.html"
    assert [funcionario.nome for funcionario in variaveis["funcionarios"]] == [
        "Joao Pedro Viana",
        "Larissa Nunes Rangel",
    ]


@pytest.mark.parametrize("id_usuario", [1, 10, 999], ids=["administradora", "cliente", "inexistente"])
@pytest.mark.parametrize(
    "metodo, url",
    [
        ("GET", "/painel/funcionarios/{}/editar"),
        ("POST", "/painel/funcionarios/{}/editar"),
        ("GET", "/painel/funcionarios/{}/desativar"),
        ("POST", "/painel/funcionarios/{}/desativar"),
        ("POST", "/painel/funcionarios/{}/reativar"),
    ],
)
def test_quem_nao_e_funcionario_da_404(navegador, metodo, url, id_usuario):
    assert navegador.open(url.format(id_usuario), method=metodo).status_code == 404


def test_formulario_de_funcionario_novo(navegador, templates):
    navegador.get("/painel/funcionarios/novo")

    nome, variaveis = templates[-1]
    assert nome == "painel/funcionario_form.html"
    assert variaveis["funcionario"] is None
    assert variaveis["cpf"] is None
    assert variaveis["regras_senha"] == [regra.descricao for regra in ValidadorSenha.REGRAS]


def test_cadastrar_funcionario_grava_e_volta_para_a_equipe(navegador, mensagens, funcionarios):
    resposta = navegador.post("/painel/funcionarios/novo", data=formulario_da_funcionaria())

    assert resposta.headers["Location"] == "/painel/funcionarios"
    assert mensagens == [("sucesso", "Paula Mendes entrou para a equipe.")]
    paula = funcionarios.listarFuncionarios()[-1]
    assert paula.nome == "Paula Mendes"
    assert paula.cargo == "Confeiteira"
    assert paula.data_contratacao == date(2026, 10, 1)


def test_funcionario_cadastrado_entra_no_painel_com_a_senha_inicial(app, navegador):
    navegador.post("/painel/funcionarios/novo", data=formulario_da_funcionaria())
    navegador_da_paula = app.test_client()

    resposta = navegador_da_paula.post("/entrar", data={"email": "paula@confeitaria.local", "senha": "Bolo@2026"})

    assert resposta.headers["Location"] == "/painel"


def test_sem_data_de_contratacao_conta_como_hoje(navegador, funcionarios):
    navegador.post("/painel/funcionarios/novo", data=formulario_da_funcionaria(data_contratacao=""))

    assert funcionarios.listarFuncionarios()[-1].data_contratacao == date.today()


@pytest.mark.parametrize(
    "trocas, mensagem",
    [
        # A senha inicial é obrigatória: é com ela que o funcionário entra no painel
        ({"senha": ""}, "A senha deve ter entre 8 e 128 caracteres, conter letras, conter números, "
                        "conter ao menos um caractere especial (ex.: @, #, !)."),
        ({"data_nascimento": ""}, "A data de nascimento é obrigatória para funcionários"),
        ({"cargo": ""}, "O campo 'cargo' é obrigatório"),
        ({"email": "joao@confeitaria.local"}, "Já existe uma conta com este e-mail, telefone ou CPF."),
    ],
    ids=["sem_senha", "sem_nascimento", "sem_cargo", "email_repetido"],
)
def test_cadastrar_com_problema_nao_grava_nada(navegador, templates, mensagens, banco, trocas, mensagem):
    antes = contar_usuarios(banco)

    resposta = navegador.post("/painel/funcionarios/novo", data=formulario_da_funcionaria(**trocas))

    assert resposta.status_code == 400
    assert templates[-1][0] == "painel/funcionario_form.html"
    assert mensagens == [("erro", mensagem)]
    assert contar_usuarios(banco) == antes


def test_formulario_de_edicao_traz_o_funcionario_e_o_cpf(navegador, templates):
    navegador.get("/painel/funcionarios/2/editar")

    variaveis = templates[-1][1]
    assert variaveis["funcionario"].id == 2
    # Só quem acessa dados sensíveis vê o CPF: a administradora
    assert variaveis["cpf"] == "87973091173"


def test_editar_sem_senha_nova_mantem_a_senha(navegador, mensagens, funcionarios, senha_forte):
    resposta = navegador.post("/painel/funcionarios/2/editar", data=formulario_do_joao(cargo="Confeiteiro"))

    assert resposta.headers["Location"] == "/painel/funcionarios"
    assert mensagens == [("sucesso", "Joao Pedro Viana atualizado.")]
    joao = funcionarios.buscarPorId(2)
    assert joao.cargo == "Confeiteiro"
    assert joao.verificarSenha(senha_forte) is True


def test_editar_com_senha_nova_troca_a_senha(navegador, funcionarios, senha_forte):
    navegador.post("/painel/funcionarios/2/editar", data=formulario_do_joao(senha="Nova#Senha9"))

    joao = funcionarios.buscarPorId(2)
    assert joao.verificarSenha("Nova#Senha9") is True
    assert joao.verificarSenha(senha_forte) is False


def test_editar_com_senha_fraca_nao_grava_nada(navegador, mensagens, funcionarios, senha_forte):
    resposta = navegador.post("/painel/funcionarios/2/editar",
                              data=formulario_do_joao(cargo="Confeiteiro", senha="fraca"))

    assert resposta.status_code == 400
    assert mensagens[0][0] == "erro"
    # A senha é validada ANTES de gravar: nem o cargo pode ter mudado
    joao = funcionarios.buscarPorId(2)
    assert joao.cargo == "Auxiliar de cozinha"
    assert joao.verificarSenha(senha_forte) is True


def test_editar_com_problema_volta_para_o_formulario(navegador, templates, mensagens, funcionarios):
    resposta = navegador.post("/painel/funcionarios/2/editar", data=formulario_do_joao(cargo="", nome="Outro Nome"))

    assert resposta.status_code == 400
    assert templates[-1][1]["funcionario"].id == 2
    assert mensagens == [("erro", "O campo 'cargo' é obrigatório")]
    assert funcionarios.buscarPorId(2).nome == "Joao Pedro Viana"


def test_desligar_pergunta_antes(navegador, templates):
    navegador.get("/painel/funcionarios/2/desativar")

    nome, variaveis = templates[-1]
    assert nome == "confirmar.html"
    assert variaveis["titulo"] == "Desligar Joao Pedro Viana?"
    assert variaveis["acao"] == "/painel/funcionarios/2/desativar"


def test_desligar_oferece_desfazer(navegador, mensagens, funcionarios):
    resposta = navegador.post("/painel/funcionarios/2/desativar")

    assert resposta.headers["Location"] == "/painel/funcionarios"
    assert funcionarios.buscarPorId(2).ativo is False
    assert mensagens == [("desfazer:/painel/funcionarios/2/reativar", "Joao Pedro Viana desligado.")]


def test_desligar_quem_ja_foi_desligado(navegador, mensagens, funcionarios):
    navegador.post("/painel/funcionarios/2/desativar")

    navegador.post("/painel/funcionarios/2/desativar")

    assert mensagens[-1] == ("erro", "Joao Pedro Viana já está desligado.")
    assert funcionarios.buscarPorId(2).ativo is False


def test_reativar_funcionario(navegador, mensagens, funcionarios):
    navegador.post("/painel/funcionarios/2/desativar")

    resposta = navegador.post("/painel/funcionarios/2/reativar")

    assert resposta.headers["Location"] == "/painel/funcionarios"
    assert funcionarios.buscarPorId(2).ativo is True
    assert mensagens[-1] == ("sucesso", "Joao Pedro Viana voltou para a equipe.")


def test_reativar_quem_ja_esta_ativo(navegador, mensagens):
    navegador.post("/painel/funcionarios/2/reativar")

    assert mensagens == [("erro", "Joao Pedro Viana já está ativo.")]
