"""
tests / rotas / test_loja.py

controllers/loja.py, parte aberta da loja: vitrine, cardápio, página do produto e carrinho

"""

from decimal import Decimal

import pytest

from app.exceptions import ValidacaoError

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


def nomes(produtos):
    """Só os nomes, na ordem em que vieram"""
    return [produto.nome for produto in produtos]


def linhas_do_carrinho(navegador):
    """As linhas do carrinho guardadas na sessão do navegador"""
    with navegador.session_transaction() as sessao:
        return sessao.get("carrinho", [])


def adicionar(navegador, **campos):
    """POST /loja/carrinho/adicionar com o produto 1, 1 unidade e sem opções, a não ser que `campos` mude"""
    formulario = {"produto_id": "1", "quantidade": "1", "observacoes": ""} | campos
    return navegador.post("/loja/carrinho/adicionar", data=formulario)


def test_vitrine_separa_pronta_entrega_e_encomendas(navegador, templates):
    resposta = navegador.get("/loja")

    assert resposta.status_code == 200
    nome, variaveis = templates[-1]
    assert nome == "loja/home.html"
    assert nomes(variaveis["pronta_entrega"]) == ["Beijinho", "Brigadeiro", "Fatia de bolo de chocolate"]
    assert nomes(variaveis["encomendas"]) == [
        "Bolo de cenoura com chocolate",
        "Bolo de chocolate com brigadeiro",
        "Cento de beijinho",
        "Cento de brigadeiro",
        "Cento de docinhos sortidos",
        "Kit festa",
    ]


def test_cardapio_mostra_os_produtos_ativos(navegador, templates):
    navegador.get("/loja/cardapio")

    nome, variaveis = templates[-1]
    assert nome == "loja/catalogo.html"
    # Bolo red velvet e Brownie saíram do cardápio
    assert nomes(variaveis["produtos"]) == ATIVOS_EM_ORDEM


def test_cardapio_filtra_por_disponibilidade_e_devolve_o_filtro_para_a_tela(navegador, templates):
    navegador.get("/loja/cardapio?disponibilidade=pronta_entrega")

    variaveis = templates[-1][1]
    assert nomes(variaveis["produtos"]) == ["Beijinho", "Brigadeiro", "Fatia de bolo de chocolate"]
    assert variaveis["disponibilidade"] == "pronta_entrega"


def test_cardapio_busca_pelo_nome(navegador, templates):
    navegador.get("/loja/cardapio?q=bolo")

    variaveis = templates[-1][1]
    assert nomes(variaveis["produtos"]) == [
        "Bolo de cenoura com chocolate",
        "Bolo de chocolate com brigadeiro",
        "Fatia de bolo de chocolate",
    ]
    assert variaveis["busca"] == "bolo"


def test_cardapio_com_disponibilidade_desconhecida_fica_vazio(navegador, templates):
    navegador.get("/loja/cardapio?disponibilidade=sob_medida")

    assert templates[-1][1]["produtos"] == []


def test_pagina_do_produto_traz_o_produto_com_as_opcoes(navegador, templates):
    resposta = navegador.get("/loja/produtos/1")

    assert resposta.status_code == 200
    nome, variaveis = templates[-1]
    assert nome == "loja/produto.html"
    assert variaveis["produto"].nome == "Bolo de chocolate com brigadeiro"
    assert [opcao.id for opcao in variaveis["produto"].opcoes] == [1, 2, 3, 4, 5]


@pytest.mark.parametrize("id_produto", [17, 999], ids=["inativo", "inexistente"])
def test_produto_inativo_ou_inexistente_da_404(navegador, id_produto):
    assert navegador.get(f"/loja/produtos/{id_produto}").status_code == 404


def test_carrinho_vazio(navegador, templates):
    resposta = navegador.get("/loja/carrinho")

    assert resposta.status_code == 200
    nome, variaveis = templates[-1]
    assert nome == "loja/carrinho.html"
    assert variaveis["carrinho"] == {"itens": [], "subtotal": Decimal("0")}
    # Visitante não tem endereço cadastrado
    assert list(variaveis["enderecos"]) == []


def test_adicionar_guarda_a_linha_na_sessao_e_vai_para_o_carrinho(navegador, mensagens):
    resposta = adicionar(
        navegador, quantidade="2", opcoes=["1", "2"], qtd_opcao_1="3", observacoes="Feliz aniversário"
    )

    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "/loja/carrinho"
    assert mensagens == [("sucesso", "Bolo de chocolate com brigadeiro foi para o carrinho.")]
    # Cada opção vira [id, quantidade]; sem qtd_opcao_2 no formulário, a opção 2 vai com 1
    assert linhas_do_carrinho(navegador) == [
        {"produto_id": 1, "quantidade": 2, "opcoes": [[1, 3], [2, 1]], "observacoes": "Feliz aniversário"}
    ]


def test_carrinho_calcula_o_preco_de_cada_item_com_as_opcoes(navegador, templates):
    adicionar(navegador, quantidade="2", opcoes=["1", "2"], qtd_opcao_1="3")

    navegador.get("/loja/carrinho")

    carrinho = templates[-1][1]["carrinho"]
    item = carrinho["itens"][0]
    assert item["produto"].id == 1
    assert item["quantidade"] == 2
    assert item["opcoes"] == [
        {"nome": "Brigadeiros em cima", "quantidade": 3, "custo": Decimal("9.00")},
        {"nome": "Nozes no recheio", "quantidade": 1, "custo": Decimal("15.00")},
    ]
    # Unidade: 98 + 3 x 3 + 15 = 122. Duas unidades: 244
    assert item["subtotal"] == Decimal("244.00")
    assert carrinho["subtotal"] == Decimal("244.00")


def test_carrinho_soma_os_itens(navegador, templates):
    adicionar(navegador)  # bolo, 98
    adicionar(navegador, produto_id="18", quantidade="10")  # 10 brigadeiros de 3,50

    navegador.get("/loja/carrinho")

    assert templates[-1][1]["carrinho"]["subtotal"] == Decimal("133.00")


def test_carrinho_usa_o_preco_atual_e_nao_o_da_hora_que_adicionou(navegador, templates, banco):
    # Os preços nunca ficam na sessão: são recalculados cada vez que o carrinho abre
    adicionar(navegador)
    banco.execute("UPDATE produto SET preco_base = 110 WHERE id_produto = 1")

    navegador.get("/loja/carrinho")

    assert templates[-1][1]["carrinho"]["subtotal"] == Decimal("110.00")


def test_cliente_logado_ve_os_enderecos_dele_no_carrinho(navegador, como_cliente, templates):
    navegador.get("/loja/carrinho")

    assert [endereco.id for endereco in templates[-1][1]["enderecos"]] == [1, 2]


@pytest.mark.parametrize(
    "campos, mensagem",
    [
        ({"quantidade": "0"}, "O campo 'quantidade' deve ser maior que zero"),
        ({"quantidade": ""}, "O campo 'quantidade' deve ser um número inteiro"),
        # A opção 6 é do bolo de cenoura
        ({"opcoes": ["6"]}, "Uma das opções escolhidas não é deste produto."),
        ({"opcoes": ["1"], "qtd_opcao_1": "0"}, "O campo 'quantidade da opção' deve ser maior que zero"),
        # A opção 10 (Topo de bolo de papel) do produto 2 está desligada
        ({"produto_id": "2", "opcoes": ["10"]}, "A opção 'Topo de bolo de papel' está indisponível"),
    ],
    ids=["quantidade_zero", "sem_quantidade", "opcao_de_outro_produto", "opcao_com_zero", "opcao_desligada"],
)
def test_adicionar_com_problema_volta_para_o_produto(navegador, templates, mensagens, campos, mensagem):
    resposta = adicionar(navegador, **campos)

    assert resposta.status_code == 400
    assert templates[-1][0] == "loja/produto.html"
    assert mensagens == [("erro", mensagem)]
    assert linhas_do_carrinho(navegador) == []


@pytest.mark.parametrize("produto_id", ["17", "999", ""], ids=["inativo", "inexistente", "sem_produto"])
def test_adicionar_produto_que_nao_esta_a_venda_da_404(navegador, produto_id):
    resposta = adicionar(navegador, produto_id=produto_id)

    assert resposta.status_code == 404
    assert linhas_do_carrinho(navegador) == []


@pytest.mark.xfail(
    strict=True,
    raises=ValidacaoError,
    reason="carrinhoAdicionar valida as observações FORA do try: com mais de 255 caracteres "
           "o ValidacaoError não é tratado e a loja dá erro 500 em vez de mostrar a mensagem",
)
def test_observacoes_longas_demais_voltam_com_mensagem(navegador, mensagens):
    resposta = adicionar(navegador, observacoes="a" * 256)

    assert resposta.status_code == 400
    assert mensagens == [("erro", "O campo 'observacoes' deve ter no máximo 255 caracteres")]


def test_atualizar_muda_a_quantidade_da_linha(navegador):
    adicionar(navegador)

    resposta = navegador.post("/loja/carrinho/0/atualizar", data={"quantidade": "4"})

    assert resposta.headers["Location"] == "/loja/carrinho"
    assert linhas_do_carrinho(navegador)[0]["quantidade"] == 4


def test_atualizar_para_zero_tira_a_linha(navegador):
    adicionar(navegador)
    adicionar(navegador, produto_id="18")

    navegador.post("/loja/carrinho/0/atualizar", data={"quantidade": "0"})

    assert [linha["produto_id"] for linha in linhas_do_carrinho(navegador)] == [18]


@pytest.mark.parametrize(
    "quantidade, mensagem",
    [("-1", "O campo 'quantidade' não pode ser negativo"), ("", "O campo 'quantidade' deve ser um número inteiro")],
    ids=["negativa", "vazia"],
)
def test_atualizar_com_quantidade_invalida_nao_muda_nada(navegador, mensagens, quantidade, mensagem):
    adicionar(navegador, quantidade="2")

    resposta = navegador.post("/loja/carrinho/0/atualizar", data={"quantidade": quantidade})

    assert resposta.headers["Location"] == "/loja/carrinho"
    assert mensagens[-1] == ("erro", mensagem)
    assert linhas_do_carrinho(navegador)[0]["quantidade"] == 2


def test_remover_tira_so_aquela_linha(navegador):
    adicionar(navegador)
    adicionar(navegador, produto_id="18")
    adicionar(navegador, produto_id="19")

    resposta = navegador.post("/loja/carrinho/1/remover")

    assert resposta.headers["Location"] == "/loja/carrinho"
    assert [linha["produto_id"] for linha in linhas_do_carrinho(navegador)] == [1, 19]


@pytest.mark.parametrize("acao", ["atualizar", "remover"])
def test_linha_que_nao_existe_da_404(navegador, acao):
    adicionar(navegador)

    assert navegador.post(f"/loja/carrinho/5/{acao}", data={"quantidade": "1"}).status_code == 404


@pytest.mark.xfail(
    strict=True,
    raises=AttributeError,
    reason="Carrinho.montarCarrinho não trata produto que saiu do cardápio: buscarAtivo devolve "
           "None e `produto.opcoes` quebra. Quem tinha o produto no carrinho não consegue mais abrir o carrinho",
)
def test_carrinho_abre_mesmo_se_um_produto_saiu_do_cardapio(navegador, banco):
    adicionar(navegador)
    banco.execute("UPDATE produto SET ativo = false WHERE id_produto = 1")

    assert navegador.get("/loja/carrinho").status_code == 200


@pytest.mark.xfail(
    strict=True,
    raises=ValidacaoError,
    reason="Carrinho.montarCarrinho não trata opção desligada depois de ir para o carrinho: "
           "o calcularPreco recusa a opção e o carrinho dá erro 500",
)
def test_carrinho_abre_mesmo_se_uma_opcao_foi_desligada(navegador, banco):
    adicionar(navegador, opcoes=["2"])
    banco.execute("UPDATE opcao_personalizacao SET ativo = false WHERE id_opcao = 2")

    assert navegador.get("/loja/carrinho").status_code == 200
