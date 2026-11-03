"""
tests / rotas / test_painel_produtos.py

controllers/painel.py, produtos: lista com abas, cadastro (com foto), edição, tirar do cardápio
e voltar, e as opções de personalização

"""

import io
from decimal import Decimal

import pytest

from app.repositories.produtos_rep import RepositorioProdutos

ATIVOS_EM_ORDEM = [
    "Beijinho",
    "Bolo de cenoura com chocolate",
    "Bolo de chocolate com brigadeiro",
    "Brigadeiro",
    "Cento de beijinho",
    "Cento de brigadeiro",
    "Cento de docinhos sortidos",
    "Fatia de bolo de chocolate",
    "Kit festa",
]


@pytest.fixture
def produtos(conexao, seed):
    """Repositório para conferir no banco o que as rotas gravaram"""
    return RepositorioProdutos(lambda: conexao)


def nomes(lista):
    """Só os nomes, na ordem em que vieram"""
    return [item.nome for item in lista]


def formulario_do_produto(**trocas):
    """Formulário de produto preenchido certo; `trocas` muda algum campo"""
    dados = {
        "nome": "Torta de limão",
        "preco_base": "65.5",
        "descricao": "Torta de limão com merengue",
        "disponibilidade": "encomenda",
        "custo_mao_de_obra": "15",
        "margem_lucro": "2.5",
        "custo_embalagem": "3",
        "custo_indireto": "1",
        "percentual_perda": "3",
        "antecedencia_horas": "24",
        "tamanho": "20 cm",
    }
    return dados | trocas


def contar_produtos(banco):
    """Quantas linhas a tabela PRODUTO tem agora"""
    banco.execute("SELECT count(*) FROM produto")
    return banco.fetchone()[0]


@pytest.fixture
def pasta_static(app, tmp_path):
    """
    Troca a pasta static do app por uma pasta temporária (tmp_path, do pytest)

    Assim a foto enviada no teste não vai parar em app/static/fotos do projeto
    """
    (tmp_path / "fotos").mkdir()
    app.static_folder = str(tmp_path)
    return tmp_path


def test_lista_mostra_os_produtos_ativos(navegador, como_funcionario, templates):
    resposta = navegador.get("/painel/produtos")

    assert resposta.status_code == 200
    nome, variaveis = templates[-1]
    assert nome == "painel/produtos.html"
    assert nomes(variaveis["produtos"]) == ATIVOS_EM_ORDEM


@pytest.mark.parametrize(
    "filtro, esperados",
    [
        ("pronta_entrega", ["Beijinho", "Brigadeiro", "Fatia de bolo de chocolate"]),
        ("encomenda", [
            "Bolo de cenoura com chocolate",
            "Bolo de chocolate com brigadeiro",
            "Cento de beijinho",
            "Cento de brigadeiro",
            "Cento de docinhos sortidos",
            "Kit festa",
        ]),
        ("inativos", ["Bolo red velvet", "Brownie"]),
        ("aba-que-nao-existe", ATIVOS_EM_ORDEM),
    ],
)
def test_cada_aba_mostra_os_seus_produtos(navegador, como_funcionario, templates, filtro, esperados):
    navegador.get(f"/painel/produtos?filtro={filtro}")

    variaveis = templates[-1][1]
    assert nomes(variaveis["produtos"]) == esperados
    assert variaveis["filtro"] == filtro


def test_busca_dentro_da_aba(navegador, como_funcionario, templates):
    navegador.get("/painel/produtos?filtro=pronta_entrega&q=bri")

    variaveis = templates[-1][1]
    assert nomes(variaveis["produtos"]) == ["Brigadeiro"]
    assert variaveis["busca"] == "bri"


def test_formulario_de_produto_novo(navegador, como_admin, templates):
    navegador.get("/painel/produtos/novo")

    nome, variaveis = templates[-1]
    assert nome == "painel/produto_form.html"
    assert variaveis["produto"] is None


def test_cadastrar_produto_grava_e_abre_a_edicao_dele(navegador, como_admin, mensagens, produtos):
    resposta = navegador.post("/painel/produtos/novo", data=formulario_do_produto())

    torta = produtos.listar(busca="Torta de limão")[0]
    assert resposta.status_code == 302
    assert resposta.headers["Location"] == f"/painel/produtos/{torta.id}"
    assert mensagens == [("sucesso", "Torta de limão cadastrado.")]
    assert torta.preco_base == Decimal("65.50")
    assert torta.disponibilidade == "encomenda"
    assert torta.antecedencia_horas == 24
    assert torta.percentual_perda == Decimal("3.00")
    assert torta.ativo is True
    # Sem foto enviada
    assert torta.caminho_foto is None


def test_cadastrar_com_foto_salva_o_arquivo_com_nome_novo(navegador, como_admin, produtos, pasta_static):
    formulario = formulario_do_produto(foto=(io.BytesIO(b"conteudo da imagem"), "minha foto.PNG"))

    navegador.post("/painel/produtos/novo", data=formulario, content_type="multipart/form-data")

    caminho = produtos.listar(busca="Torta de limão")[0].caminho_foto
    # Nome único gerado pelo sistema (uuid), com a extensão em minúsculas
    assert caminho.startswith("fotos/")
    assert caminho.endswith(".png")
    assert "minha foto" not in caminho
    assert (pasta_static / caminho).read_bytes() == b"conteudo da imagem"


def test_foto_que_nao_e_imagem_e_recusada(navegador, como_admin, mensagens, banco, pasta_static):
    antes = contar_produtos(banco)
    formulario = formulario_do_produto(foto=(io.BytesIO(b"GIF89a"), "animacao.gif"))

    resposta = navegador.post("/painel/produtos/novo", data=formulario, content_type="multipart/form-data")

    assert resposta.status_code == 400
    assert mensagens == [("erro", "A foto precisa ser JPG, PNG ou WEBP.")]
    assert contar_produtos(banco) == antes
    assert list((pasta_static / "fotos").iterdir()) == []


@pytest.mark.parametrize(
    "trocas, mensagem",
    [
        ({"nome": ""}, "O campo 'nome do produto' é obrigatório"),
        ({"preco_base": "-1"}, "O campo 'preço base' não pode ser negativo"),
        ({"preco_base": "abc"}, "O campo 'preço base' deve ser um número"),
        ({"percentual_perda": "101"}, "O campo 'percentual de perda' deve estar entre 0 e 100"),
        ({"antecedencia_horas": ""}, "O campo 'antecedência (horas)' deve ser um número inteiro"),
    ],
    ids=["sem_nome", "preco_negativo", "preco_nao_numerico", "perda_acima_de_100", "sem_antecedencia"],
)
def test_cadastrar_com_problema_volta_para_o_formulario(navegador, como_admin, templates, mensagens, banco,
                                                        trocas, mensagem):
    antes = contar_produtos(banco)

    resposta = navegador.post("/painel/produtos/novo", data=formulario_do_produto(**trocas))

    assert resposta.status_code == 400
    nome, variaveis = templates[-1]
    assert nome == "painel/produto_form.html"
    assert variaveis["produto"] is None
    assert mensagens == [("erro", mensagem)]
    assert contar_produtos(banco) == antes


def test_disponibilidade_fora_das_duas_opcoes_e_barrada_pelo_banco(navegador, como_admin, mensagens):
    resposta = navegador.post("/painel/produtos/novo", data=formulario_do_produto(disponibilidade="Sob encomenda"))

    assert resposta.status_code == 400
    assert mensagens == [("erro", RepositorioProdutos.MENSAGEM_PRODUTO_INVALIDO)]
    # O CHECK do banco recusou o INSERT: depois desse erro o PostgreSQL recusa comandos até o
    # rollback do fim do teste, então este teste não confere mais nada no banco


def test_formulario_de_edicao_traz_o_produto_com_as_opcoes(navegador, como_admin, templates):
    navegador.get("/painel/produtos/1")

    nome, variaveis = templates[-1]
    assert nome == "painel/produto_form.html"
    assert variaveis["produto"].id == 1
    assert [opcao.id for opcao in variaveis["produto"].opcoes] == [1, 2, 3, 4, 5]


def test_editar_produto_inexistente_da_404(navegador, como_admin):
    assert navegador.get("/painel/produtos/999").status_code == 404
    assert navegador.post("/painel/produtos/999", data=formulario_do_produto()).status_code == 404


def test_editar_grava_e_mantem_a_foto_quando_nao_vem_outra(navegador, como_admin, mensagens, produtos):
    resposta = navegador.post(
        "/painel/produtos/1",
        data=formulario_do_produto(nome="Bolo de chocolate (receita nova)", preco_base="105"),
    )

    assert resposta.headers["Location"] == "/painel/produtos/1"
    assert mensagens == [("sucesso", "Bolo de chocolate (receita nova) atualizado.")]
    bolo = produtos.buscarPorId(1)
    assert bolo.nome == "Bolo de chocolate (receita nova)"
    assert bolo.preco_base == Decimal("105.00")
    assert bolo.caminho_foto == "fotos/produto_01.jpg"


def test_editar_com_foto_nova_troca_o_caminho(navegador, como_admin, produtos, pasta_static):
    formulario = formulario_do_produto(foto=(io.BytesIO(b"foto nova"), "bolo.webp"))

    navegador.post("/painel/produtos/1", data=formulario, content_type="multipart/form-data")

    caminho = produtos.buscarPorId(1).caminho_foto
    assert caminho != "fotos/produto_01.jpg"
    assert (pasta_static / caminho).read_bytes() == b"foto nova"


def test_editar_com_problema_nao_grava_nada(navegador, como_admin, templates, mensagens, produtos):
    resposta = navegador.post(
        "/painel/produtos/1", data=formulario_do_produto(nome="Nome Que Não Pode Ficar", percentual_perda="150")
    )

    assert resposta.status_code == 400
    assert templates[-1][1]["produto"].id == 1
    assert mensagens == [("erro", "O campo 'percentual de perda' deve estar entre 0 e 100")]
    assert produtos.buscarPorId(1).nome == "Bolo de chocolate com brigadeiro"


def test_tirar_do_cardapio_pergunta_antes(navegador, como_admin, templates):
    navegador.get("/painel/produtos/1/desativar")

    nome, variaveis = templates[-1]
    assert nome == "confirmar.html"
    assert variaveis["titulo"] == "Tirar Bolo de chocolate com brigadeiro do cardápio?"
    assert variaveis["acao"] == "/painel/produtos/1/desativar"


def test_tirar_do_cardapio_desativa_e_oferece_desfazer(navegador, como_admin, mensagens, produtos):
    resposta = navegador.post("/painel/produtos/1/desativar")

    assert resposta.headers["Location"] == "/painel/produtos"
    assert produtos.buscarPorId(1).ativo is False
    # A categoria "desfazer:<url>" vira o botão Desfazer (requisito 11.7)
    assert mensagens == [
        ("desfazer:/painel/produtos/1/reativar", "Bolo de chocolate com brigadeiro saiu do cardápio.")
    ]


def test_tirar_do_cardapio_um_produto_que_ja_saiu_nao_o_reativa(navegador, como_admin, mensagens, produtos):
    # alternarAtivo inverte o estado: sem a conferência da rota, "desativar" um inativo o reativaria
    navegador.post("/painel/produtos/17/desativar")

    assert mensagens == [("erro", "Bolo red velvet já está fora do cardápio.")]
    assert produtos.buscarPorId(17).ativo is False


def test_voltar_ao_cardapio(navegador, como_admin, mensagens, produtos):
    resposta = navegador.post("/painel/produtos/17/reativar")

    assert resposta.headers["Location"] == "/painel/produtos"
    assert mensagens == [("sucesso", "Bolo red velvet voltou ao cardápio.")]
    assert produtos.buscarPorId(17).ativo is True


def test_voltar_ao_cardapio_um_produto_ativo_nao_o_desativa(navegador, como_admin, mensagens, produtos):
    navegador.post("/painel/produtos/1/reativar")

    assert mensagens == [("erro", "Bolo de chocolate com brigadeiro já está no cardápio.")]
    assert produtos.buscarPorId(1).ativo is True


@pytest.mark.parametrize(
    "metodo, url",
    [
        ("GET", "/painel/produtos/999/desativar"),
        ("POST", "/painel/produtos/999/desativar"),
        ("POST", "/painel/produtos/999/reativar"),
        ("POST", "/painel/produtos/999/opcoes"),
    ],
)
def test_produto_inexistente_da_404(navegador, como_admin, metodo, url):
    assert navegador.open(url, method=metodo).status_code == 404


def test_adicionar_opcao_grava_ligada_ao_produto(navegador, como_admin, mensagens, produtos):
    resposta = navegador.post(
        "/painel/produtos/1/opcoes", data={"nome": "Confeitos", "custo_adicional": "4.5", "descricao": ""}
    )

    assert resposta.headers["Location"] == "/painel/produtos/1"
    assert mensagens == [("sucesso", "Opção Confeitos adicionada.")]
    nova = produtos.buscarPorId(1).opcoes[-1]
    assert nova.nome == "Confeitos"
    assert nova.custo_adicional == Decimal("4.50")
    assert nova.ativo is True


@pytest.mark.parametrize(
    "formulario, mensagem",
    [
        ({"nome": "", "custo_adicional": "4"}, "O campo 'nome da opção' é obrigatório"),
        ({"nome": "Confeitos", "custo_adicional": "-4"}, "O campo 'custo adicional' não pode ser negativo"),
    ],
    ids=["sem_nome", "custo_negativo"],
)
def test_adicionar_opcao_com_problema_volta_para_o_produto(navegador, como_admin, templates, mensagens, produtos,
                                                           formulario, mensagem):
    resposta = navegador.post("/painel/produtos/1/opcoes", data=formulario)

    assert resposta.status_code == 400
    assert templates[-1][0] == "painel/produto_form.html"
    assert mensagens == [("erro", mensagem)]
    assert len(produtos.buscarPorId(1).opcoes) == 5


@pytest.mark.xfail(
    strict=True,
    raises=AttributeError,
    reason="opcaoAlternar ainda não funciona: o RepositorioProdutos não tem buscarPorOpcao, e o "
           "_opcaoDoProduto da rota tem uma função dentro da outra e devolve None",
)
def test_ligar_e_desligar_opcao(navegador, como_admin, mensagens, produtos):
    resposta = navegador.post("/painel/opcoes/2/alternar")

    assert resposta.headers["Location"] == "/painel/produtos/1"
    assert mensagens == [("sucesso", "Opção Nozes no recheio desligada.")]
    assert produtos.buscarPorId(1).opcoes[1].ativo is False
