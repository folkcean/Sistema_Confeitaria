"""
tests / rotas / test_painel_estoque.py

controllers/painel.py, estoque: abas, cadastro e edição de insumos, ajuste manual com desfazer,
desativar e reativar, e a lista de compras

"""

from decimal import Decimal

import pytest

from app.repositories.insumos_rep import RepositorioInsumos

ATIVOS_EM_ORDEM = [
    "Acucar refinado",
    "Cacau em po 50%",
    "Caixa para bolo 25cm",
    "Cenoura",
    "Chocolate meio amargo",
    "Coco ralado",
    "Creme de leite (200g)",
    "Farinha de trigo",
    "Fermento quimico",
    "Forminha de papel n.4",
    "Granulado de chocolate",
    "Leite condensado (395g)",
    "Leite integral",
    "Manteiga sem sal",
    "Oleo de soja",
    "Ovo",
]


@pytest.fixture
def insumos(conexao, seed):
    """Repositório para conferir no banco o que as rotas gravaram"""
    return RepositorioInsumos(lambda: conexao)


def nomes(lista):
    """Só os nomes, na ordem em que vieram"""
    return [item.nome for item in lista]


def formulario_do_insumo(**trocas):
    """Formulário de insumo novo preenchido certo; `trocas` muda algum campo"""
    dados = {
        "nome": "Morango",
        "tipo": "ingrediente",
        "unidade_medida": "kg",
        "unidade_receita": "g",
        "fator_conversao": "1000",
        "quantidade_atual": "2",
        "estoque_minimo": "1",
        "custo_por_unidade": "25.9",
    }
    return dados | trocas


def movimentacoes_da_caixa(banco):
    """(tipo, quantidade, motivo) de cada movimentação da Caixa para bolo (22), em ordem"""
    banco.execute(
        "SELECT tipo, quantidade, motivo FROM movimentacao_estoque "
        "WHERE id_insumo = 22 ORDER BY id_movimentacao_estoque"
    )
    return banco.fetchall()


def id_do_ajuste_do_seed(banco):
    """Id da movimentação de ajuste que o DB_fill.sql cria (-2 caixas)"""
    banco.execute("SELECT id_movimentacao_estoque FROM movimentacao_estoque WHERE tipo = 'ajuste'")
    return banco.fetchone()[0]


def test_estoque_mostra_os_insumos_ativos(navegador, como_funcionario, templates):
    resposta = navegador.get("/painel/estoque")

    assert resposta.status_code == 200
    nome, variaveis = templates[-1]
    assert nome == "painel/estoque.html"
    assert nomes(variaveis["insumos"]) == ATIVOS_EM_ORDEM


@pytest.mark.parametrize(
    "filtro, esperados",
    [
        ("embalagem", ["Caixa para bolo 25cm", "Forminha de papel n.4"]),
        ("decoracao", ["Granulado de chocolate"]),
        ("baixo", ["Acucar refinado", "Leite condensado (395g)"]),
        ("inativos", ["Fita de cetim"]),
        ("aba-que-nao-existe", ATIVOS_EM_ORDEM),
    ],
)
def test_cada_aba_mostra_os_seus_insumos(navegador, como_admin, templates, filtro, esperados):
    navegador.get(f"/painel/estoque?filtro={filtro}")

    variaveis = templates[-1][1]
    assert nomes(variaveis["insumos"]) == esperados
    assert variaveis["filtro"] == filtro


def test_busca_pelo_nome(navegador, como_funcionario, templates):
    navegador.get("/painel/estoque?q=leite")

    variaveis = templates[-1][1]
    assert nomes(variaveis["insumos"]) == ["Creme de leite (200g)", "Leite condensado (395g)", "Leite integral"]
    assert variaveis["busca"] == "leite"


def test_funcionario_nao_ve_a_aba_de_inativos(navegador, como_funcionario, templates):
    resposta = navegador.get("/painel/estoque?filtro=inativos")

    assert resposta.status_code == 403
    assert templates[-1][1]["mensagem"] == "Só a administração vê os insumos inativos."


def test_formulario_de_insumo_novo(navegador, como_admin, templates):
    navegador.get("/painel/estoque/novo")

    assert templates[-1][0] == "painel/insumo_form.html"
    assert templates[-1][1]["insumo"] is None


def test_cadastrar_insumo_grava_e_volta_para_o_estoque(navegador, como_admin, mensagens, insumos):
    resposta = navegador.post("/painel/estoque/novo", data=formulario_do_insumo())

    assert resposta.headers["Location"] == "/painel/estoque"
    assert mensagens == [("sucesso", "Morango cadastrado no estoque.")]
    morango = insumos.listarComFiltro(busca="Morango")[0]
    assert morango.unidade_medida == "kg"
    assert morango.fator_conversao == Decimal("1000")
    assert morango.quantidade_atual == Decimal("2")
    assert morango.custo_por_unidade == Decimal("25.9")


def test_custo_em_branco_fica_como_nao_informado(navegador, como_admin, insumos):
    navegador.post("/painel/estoque/novo", data=formulario_do_insumo(custo_por_unidade=""))

    assert insumos.listarComFiltro(busca="Morango")[0].custo_por_unidade is None


@pytest.mark.parametrize(
    "trocas, mensagem",
    [
        ({"nome": ""}, "O campo 'nome do insumo' é obrigatório"),
        ({"tipo": "bebida"}, "O campo 'tipo'  tem um valor inválido: 'bebida'"),
        ({"fator_conversao": "0"}, "O campo 'fator de conversão' deve ser maior que zero"),
        ({"quantidade_atual": "-1"}, "O campo 'quantidade atual' não pode ser negativo"),
    ],
    ids=["sem_nome", "tipo_desconhecido", "fator_zero", "saldo_negativo"],
)
def test_cadastrar_com_problema_volta_para_o_formulario(navegador, como_admin, templates, mensagens, insumos,
                                                        trocas, mensagem):
    resposta = navegador.post("/painel/estoque/novo", data=formulario_do_insumo(**trocas))

    assert resposta.status_code == 400
    assert templates[-1][0] == "painel/insumo_form.html"
    assert mensagens == [("erro", mensagem)]
    assert len(insumos.listar()) == 17


def test_cadastrar_insumo_com_nome_repetido(navegador, como_admin, mensagens):
    resposta = navegador.post("/painel/estoque/novo", data=formulario_do_insumo(nome="Ovo"))

    assert resposta.status_code == 400
    assert mensagens == [("erro", "Já existe um insumo com este nome.")]
    # O banco recusou o INSERT (UNIQUE): depois desse erro o PostgreSQL recusa comandos até o
    # rollback do fim do teste, então este teste não confere mais nada no banco


def test_formulario_de_edicao_traz_o_insumo(navegador, como_admin, templates):
    navegador.get("/painel/estoque/1/editar")

    assert templates[-1][1]["insumo"].nome == "Farinha de trigo"


def test_editar_grava_minimo_e_custo_sem_mexer_no_saldo(navegador, como_admin, mensagens, insumos):
    resposta = navegador.post("/painel/estoque/1/editar", data={"estoque_minimo": "12000", "custo_por_unidade": "5.5"})

    assert resposta.headers["Location"] == "/painel/estoque"
    assert mensagens == [("sucesso", "Farinha de trigo atualizado.")]
    farinha = insumos.buscarPorId(1)
    assert farinha.estoque_minimo == Decimal("12000")
    assert farinha.custo_por_unidade == Decimal("5.5")
    assert farinha.quantidade_atual == Decimal("11268.19")


def test_editar_com_minimo_negativo_nao_grava(navegador, como_admin, templates, mensagens, insumos):
    resposta = navegador.post("/painel/estoque/1/editar", data={"estoque_minimo": "-1", "custo_por_unidade": ""})

    assert resposta.status_code == 400
    assert templates[-1][1]["insumo"].id == 1
    assert mensagens == [("erro", "O campo 'estoque mínimo' não pode ser negativo")]
    assert insumos.buscarPorId(1).estoque_minimo == Decimal("10000")


@pytest.mark.parametrize(
    "metodo, url",
    [
        ("GET", "/painel/estoque/999/editar"),
        ("POST", "/painel/estoque/999/editar"),
        ("GET", "/painel/estoque/999/ajustar"),
        ("POST", "/painel/estoque/999/ajustar"),
        ("GET", "/painel/estoque/999/desativar"),
        ("POST", "/painel/estoque/999/desativar"),
        ("POST", "/painel/estoque/999/reativar"),
        ("POST", "/painel/estoque/ajustes/99999/desfazer"),
    ],
)
def test_insumo_ou_ajuste_inexistente_da_404(navegador, como_admin, metodo, url):
    assert navegador.open(url, method=metodo).status_code == 404


def test_formulario_de_ajuste(navegador, como_admin, templates):
    navegador.get("/painel/estoque/22/ajustar")

    nome, variaveis = templates[-1]
    assert nome == "painel/insumo_ajuste.html"
    assert variaveis["insumo"].id == 22


def test_ajustar_grava_o_saldo_novo_e_a_movimentacao(navegador, como_admin, insumos, banco):
    resposta = navegador.post(
        "/painel/estoque/22/ajustar",
        data={"nova_quantidade": "20", "motivo": "Contagem do fim do mês", "confirmo": "on"},
    )

    assert resposta.headers["Location"] == "/painel/estoque"
    assert insumos.buscarPorId(22).quantidade_atual == Decimal("20")
    # Contei 20, tinha 17: o ajuste registrado é de +3
    assert movimentacoes_da_caixa(banco)[-1] == ("ajuste", Decimal("3.000"), "Contagem do fim do mês")


def test_ajustar_oferece_desfazer_aquele_ajuste(navegador, como_admin, mensagens, banco):
    navegador.post(
        "/painel/estoque/22/ajustar", data={"nova_quantidade": "20", "motivo": "Contagem", "confirmo": "on"}
    )

    banco.execute("SELECT max(id_movimentacao_estoque) FROM movimentacao_estoque")
    id_novo = banco.fetchone()[0]
    assert mensagens == [
        (f"desfazer:/painel/estoque/ajustes/{id_novo}/desfazer", "Estoque de Caixa para bolo 25cm ajustado.")]


@pytest.mark.parametrize(
    "formulario, mensagem",
    [
        # A caixa de confirmação é "required" no HTML, mas a rota confere de novo
        ({"nova_quantidade": "20", "motivo": "Contagem"}, "Marque a caixa de confirmação para ajustar o estoque."),
        ({"nova_quantidade": "20", "motivo": "", "confirmo": "on"}, "Movimentações do tipo 'ajuste' exigem um motivo"),
        ({"nova_quantidade": "17", "motivo": "Contagem", "confirmo": "on"},
         "A nova quantidade é igual à quantidade atual"),
        ({"nova_quantidade": "-5", "motivo": "Contagem", "confirmo": "on"},
         "O campo 'nova quantidade' não pode ser negativo"),
    ],
    ids=["sem_confirmar", "sem_motivo", "quantidade_igual", "quantidade_negativa"],
)
def test_ajuste_com_problema_nao_muda_o_saldo(navegador, como_admin, templates, mensagens, insumos, banco,
                                              formulario, mensagem):
    antes = movimentacoes_da_caixa(banco)

    resposta = navegador.post("/painel/estoque/22/ajustar", data=formulario)

    assert resposta.status_code == 400
    assert templates[-1][0] == "painel/insumo_ajuste.html"
    assert mensagens == [("erro", mensagem)]
    assert insumos.buscarPorId(22).quantidade_atual == Decimal("17")
    assert movimentacoes_da_caixa(banco) == antes


def test_desfazer_registra_um_ajuste_contrario_sem_apagar_o_historico(navegador, como_admin, mensagens,
                                                                      insumos, banco):
    resposta = navegador.post(f"/painel/estoque/ajustes/{id_do_ajuste_do_seed(banco)}/desfazer")

    assert resposta.headers["Location"] == "/painel/estoque"
    assert mensagens == [("sucesso", "Ajuste de Caixa para bolo 25cm desfeito.")]
    # Tinha tirado 2 (17); desfazer devolve as 2 (19)
    assert insumos.buscarPorId(22).quantidade_atual == Decimal("19")
    original, contrario = movimentacoes_da_caixa(banco)
    assert original == ("ajuste", Decimal("-2.000"), "Caixas amassadas na contagem")
    assert contrario[:2] == ("ajuste", Decimal("2.000"))
    assert contrario[2].startswith("Desfaz o ajuste de ")


def test_so_ajuste_manual_pode_ser_desfeito(navegador, como_admin, mensagens, insumos, banco):
    banco.execute("SELECT min(id_movimentacao_estoque) FROM movimentacao_estoque WHERE tipo = 'consumo'")
    id_consumo = banco.fetchone()[0]

    navegador.post(f"/painel/estoque/ajustes/{id_consumo}/desfazer")

    assert mensagens == [("erro", "Somente ajustes manuais podem ser desfeitos")]
    assert insumos.buscarPorId(1).quantidade_atual == Decimal("11268.19")


@pytest.mark.xfail(
    strict=True,
    reason="Nada impede desfazer o MESMO ajuste duas vezes (dois cliques, voltar e reenviar): "
           "cada vez entra mais um ajuste contrário e o saldo fica errado. Precisa de uma regra para "
           "saber se o ajuste já foi desfeito",
)
def test_desfazer_o_mesmo_ajuste_duas_vezes_nao_devolve_duas_vezes(navegador, como_admin, insumos, banco):
    url = f"/painel/estoque/ajustes/{id_do_ajuste_do_seed(banco)}/desfazer"

    navegador.post(url)
    navegador.post(url)

    assert insumos.buscarPorId(22).quantidade_atual == Decimal("19")


def test_desativar_pergunta_antes(navegador, como_admin, templates):
    navegador.get("/painel/estoque/1/desativar")

    nome, variaveis = templates[-1]
    assert nome == "confirmar.html"
    assert variaveis["titulo"] == "Desativar Farinha de trigo?"
    assert variaveis["acao"] == "/painel/estoque/1/desativar"


def test_desativar_insumo_oferece_desfazer(navegador, como_admin, mensagens, insumos):
    resposta = navegador.post("/painel/estoque/1/desativar")

    assert resposta.headers["Location"] == "/painel/estoque"
    assert insumos.buscarPorId(1).ativo is False
    assert mensagens == [("desfazer:/painel/estoque/1/reativar", "Farinha de trigo desativado.")]


def test_desativar_insumo_que_ja_esta_inativo_nao_o_reativa(navegador, como_admin, mensagens, insumos):
    navegador.post("/painel/estoque/26/desativar")

    assert mensagens == [("erro", "Fita de cetim já está inativo.")]
    assert insumos.buscarPorId(26).ativo is False


def test_reativar_insumo(navegador, como_admin, mensagens, insumos):
    resposta = navegador.post("/painel/estoque/26/reativar")

    assert resposta.headers["Location"] == "/painel/estoque"
    assert insumos.buscarPorId(26).ativo is True
    assert mensagens == [("desfazer:/painel/estoque/26/desativar", "Fita de cetim reativado.")]


def test_reativar_insumo_que_ja_esta_ativo_nao_o_desativa(navegador, como_admin, insumos):
    navegador.post("/painel/estoque/1/reativar")

    assert insumos.buscarPorId(1).ativo is True


@pytest.mark.xfail(
    strict=True,
    reason="insumoReativar monta a mensagem sem o f da f-string: aparece \"O {insumo.nome} já "
           "está reativado.\" em vez do nome do insumo",
)
def test_reativar_insumo_ativo_avisa_com_o_nome_dele(navegador, como_admin, mensagens):
    navegador.post("/painel/estoque/1/reativar")

    categoria, texto = mensagens[0]
    assert categoria == "erro"
    assert "Farinha de trigo" in texto


def test_lista_de_compras_traz_o_que_esta_no_minimo_com_o_custo(navegador, como_funcionario, templates):
    resposta = navegador.get("/painel/estoque/lista-de-compras")

    assert resposta.status_code == 200
    nome, variaveis = templates[-1]
    assert nome == "painel/lista_compras.html"
    # Na unidade de COMPRA: açúcar faltam 1268,96 g = 1,27 kg x R$ 4,69; leite faltam 16 latas x R$ 7,03
    assert [(item["insumo"].nome, item["comprar"], item["custo_estimado"]) for item in variaveis["itens"]] == [
        ("Acucar refinado", Decimal("1.27"), Decimal("5.96")),
        ("Leite condensado (395g)", Decimal("16.00"), Decimal("112.48")),
    ]
    assert variaveis["total_estimado"] == Decimal("118.44")


def test_insumo_sem_custo_entra_na_lista_com_custo_zero(navegador, como_funcionario, templates, banco):
    banco.execute("UPDATE insumo SET custo_por_unidade = NULL WHERE id_insumo = 4")

    navegador.get("/painel/estoque/lista-de-compras")

    variaveis = templates[-1][1]
    assert variaveis["itens"][1]["custo_estimado"] == Decimal("0.00")
    assert variaveis["total_estimado"] == Decimal("5.96")
