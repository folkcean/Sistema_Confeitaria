"""
tests / rotas / test_loja_perfil.py

controllers/loja.py, parte do cliente logado: perfil, meus dados, troca de senha e endereços
"""

import pytest

from app.repositories.clientes_rep import RepositorioClientes
from app.validators.senha import ValidadorSenha

# Todo teste deste arquivo entra como a Ana
pytestmark = pytest.mark.usefixtures("como_cliente")


@pytest.fixture
def clientes(conexao, seed):
    """Repositório para conferir no banco o que as rotas gravaram"""
    return RepositorioClientes(lambda: conexao)


def dados_da_ana(**trocas):
    """Formulário "Meus dados" preenchido com os dados atuais da Ana; `trocas` muda algum campo"""
    dados = {
        "nome": "Ana Souza",
        "apelido": "Aninha",
        "telefone": "22999990010",
        "email": "ana@exemplo.com",
        "data_nascimento": "1992-11-05",
        "instagram": "@anasouza",
        "restricoes_alimentares": "",
        "preferencias": "Bolo de chocolate",
    }
    return dados | trocas


def endereco_novo(**trocas):
    """Formulário de endereço novo; `trocas` muda algum campo"""
    dados = {
        "apelido": "Casa da vó",
        "cep": "28010-000",
        "logradouro": "Rua Nova",
        "numero": "5",
        "complemento": "",
        "bairro": "Centro",
        "cidade": "Campos dos Goytacazes",
    }
    return dados | trocas


def ids_dos_enderecos(clientes):
    """Ids dos endereços da Ana no banco"""
    return [endereco.id for endereco in clientes.buscarPorId(10).enderecos]


def test_perfil_abre(navegador, templates):
    assert navegador.get("/loja/perfil").status_code == 200
    assert templates[-1][0] == "loja/perfil.html"


def test_meus_dados_traz_a_cliente_logada_e_as_regras_da_senha(navegador, templates):
    navegador.get("/loja/perfil/dados")

    nome, variaveis = templates[-1]
    assert nome == "loja/meus_dados.html"
    assert variaveis["cliente"].id == 10
    assert variaveis["regras_senha"] == [regra.descricao for regra in ValidadorSenha.REGRAS]


def test_salvar_meus_dados_grava_e_volta_para_o_perfil(navegador, mensagens, clientes):
    resposta = navegador.post(
        "/loja/perfil/dados",
        data=dados_da_ana(nome="Ana Maria Souza", instagram="@anamaria", restricoes_alimentares="Sem lactose"),
    )

    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "/loja/perfil"
    assert mensagens == [("sucesso", "Dados atualizados.")]
    ana = clientes.buscarPorId(10)
    assert ana.nome == "Ana Maria Souza"
    assert ana.instagram == "@anamaria"
    assert ana.restricoes_alimentares == "Sem lactose"


def test_campo_opcional_apagado_vira_vazio_no_banco(navegador, clientes):
    navegador.post("/loja/perfil/dados", data=dados_da_ana(instagram="", preferencias=""))

    ana = clientes.buscarPorId(10)
    assert ana.instagram is None
    assert ana.preferencias is None


@pytest.mark.parametrize(
    "trocas, mensagem",
    [
        # No model o e-mail é opcional, mas o login depende dele
        ({"email": ""}, "O campo 'e-mail' é obrigatório"),
        ({"nome": ""}, "O campo 'nome' é obrigatório"),
        ({"apelido": ""}, "O campo 'apelido' é obrigatório"),
        ({"telefone": "123"}, "Telefone inválido: informe DDD + número"),
        ({"data_nascimento": "2999-01-01"}, "A data de nascimento não pode estar no futuro"),
        # O telefone é do Bruno: o banco recusa (UNIQUE)
        ({"telefone": "22999990011"}, "Já existe uma conta com este e-mail, telefone ou CPF."),
    ],
    ids=["sem_email", "sem_nome", "sem_apelido", "telefone_invalido", "nascimento_no_futuro", "telefone_do_bruno"],
)
def test_meus_dados_com_problema_nao_grava_nada(navegador, templates, mensagens, clientes, trocas, mensagem):
    resposta = navegador.post("/loja/perfil/dados", data=dados_da_ana(nome="Nome Que Não Pode Ficar") | trocas)

    assert resposta.status_code == 400
    assert templates[-1][0] == "loja/meus_dados.html"
    assert mensagens == [("erro", mensagem)]
    assert clientes.buscarPorId(10).nome == "Ana Souza"


def test_trocar_senha_grava_a_nova(navegador, mensagens, clientes, senha_forte):
    resposta = navegador.post(
        "/loja/perfil/senha",
        data={"senha_atual": senha_forte, "nova_senha": "Nova#Senha9", "confirmar_senha": "Nova#Senha9"},
    )

    assert resposta.headers["Location"] == "/loja/perfil"
    assert mensagens == [("sucesso", "Senha alterada.")]
    ana = clientes.buscarPorId(10)
    assert ana.verificarSenha("Nova#Senha9") is True
    assert ana.verificarSenha(senha_forte) is False


@pytest.mark.parametrize(
    "atual, nova, confirmacao, mensagem",
    [
        ("senha-errada", "Nova#Senha9", "Nova#Senha9", "A senha atual não confere."),
        ("Bolo@2026", "Nova#Senha9", "Nova#Senha8", "As senhas novas não conferem."),
        ("Bolo@2026", "fraca", "fraca",
         "A senha deve ter entre 8 e 128 caracteres, conter números, conter ao menos um caractere especial (ex.: @, #, !)."),
    ],
    ids=["atual_errada", "confirmacao_diferente", "nova_fraca"],
)
def test_trocar_senha_com_problema_mantem_a_antiga(navegador, templates, mensagens, clientes, senha_forte,
                                                   atual, nova, confirmacao, mensagem):
    resposta = navegador.post(
        "/loja/perfil/senha",
        data={"senha_atual": atual, "nova_senha": nova, "confirmar_senha": confirmacao},
    )

    assert resposta.status_code == 400
    assert templates[-1][0] == "loja/meus_dados.html"
    assert mensagens == [("erro", mensagem)]
    assert clientes.buscarPorId(10).verificarSenha(senha_forte) is True


def test_enderecos_mostra_so_os_da_cliente(navegador, templates):
    navegador.get("/loja/perfil/enderecos")

    nome, variaveis = templates[-1]
    assert nome == "loja/enderecos.html"
    assert [endereco.id for endereco in variaveis["enderecos"]] == [1, 2]


def test_cadastrar_endereco_grava_ligado_a_cliente(navegador, mensagens, clientes):
    resposta = navegador.post("/loja/perfil/enderecos/novo", data=endereco_novo())

    assert resposta.headers["Location"] == "/loja/perfil/enderecos"
    assert mensagens == [("sucesso", "Endereço cadastrado.")]
    novo = clientes.buscarPorId(10).enderecos[-1]
    assert novo.apelido == "Casa da vó"
    assert novo.cep == "28010000"
    assert novo.complemento is None
    assert len(ids_dos_enderecos(clientes)) == 3


@pytest.mark.parametrize(
    "trocas, mensagem",
    [
        ({"cep": "123"}, "CEP inválido: deve conter 8 dígitos"),
        ({"logradouro": ""}, "O campo 'logradouro' é obrigatório"),
        ({"numero": ""}, "O campo 'número' é obrigatório"),
    ],
    ids=["cep_invalido", "sem_logradouro", "sem_numero"],
)
def test_endereco_com_problema_nao_grava(navegador, templates, mensagens, clientes, trocas, mensagem):
    resposta = navegador.post("/loja/perfil/enderecos/novo", data=endereco_novo(**trocas))

    assert resposta.status_code == 400
    assert templates[-1][0] == "loja/enderecos.html"
    assert mensagens == [("erro", mensagem)]
    assert ids_dos_enderecos(clientes) == [1, 2]


def test_remover_endereco_pergunta_antes(navegador, templates):
    resposta = navegador.get("/loja/perfil/enderecos/2/remover")

    assert resposta.status_code == 200
    nome, variaveis = templates[-1]
    assert nome == "confirmar.html"
    assert variaveis["mensagem"] == "Rua Santa Rosa, 1473, Sala 659 - Pelinca, Campos dos Goytacazes - CEP 28035-573"
    assert variaveis["acao"] == "/loja/perfil/enderecos/2/remover"


def test_remover_endereco_que_nunca_foi_usado(navegador, mensagens, clientes):
    navegador.post("/loja/perfil/enderecos/novo", data=endereco_novo())
    id_novo = ids_dos_enderecos(clientes)[-1]

    resposta = navegador.post(f"/loja/perfil/enderecos/{id_novo}/remover")

    assert resposta.headers["Location"] == "/loja/perfil/enderecos"
    assert mensagens[-1] == ("sucesso", "Endereço removido.")
    assert ids_dos_enderecos(clientes) == [1, 2]


@pytest.mark.parametrize("metodo", ["GET", "POST"])
def test_endereco_de_outro_cliente_da_404(navegador, clientes, metodo):
    # O 3 é do Bruno: procurar só nos endereços da Ana é o que impede trocar o número na URL
    resposta = navegador.open("/loja/perfil/enderecos/3/remover", method=metodo)

    assert resposta.status_code == 404
    assert [endereco.id for endereco in clientes.buscarPorId(11).enderecos] == [3]


def test_endereco_usado_em_pedido_nao_pode_ser_removido(navegador, mensagens):
    resposta = navegador.post("/loja/perfil/enderecos/1/remover")

    assert resposta.headers["Location"] == "/loja/perfil/enderecos"
    assert mensagens == [("erro", "Este endereço já foi usado em um pedido e não pode ser removido.")]
    # O banco recusou o DELETE (FK do pedido 1). Depois desse erro o PostgreSQL recusa comandos
    # até o rollback do fim do teste: por isso este teste não confere mais nada no banco
