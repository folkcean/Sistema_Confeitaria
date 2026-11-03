"""
tests / rotas / test_painel_relatorios.py

controllers/painel.py, relatórios: abas (vendas, produtos, insumos), escolha do período e a
permissão de acesso financeiro

"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

pytestmark = pytest.mark.usefixtures("como_admin")


@pytest.fixture
def passado(hoje_no_banco):
    inicio, fim = hoje_no_banco - timedelta(days=30), hoje_no_banco - timedelta(days=1)
    return f"inicio={inicio}&fim={fim}"


def esta_semana():
    """Segunda a domingo da semana de hoje"""
    segunda = date.today() - timedelta(days=date.today().weekday())
    return segunda, segunda + timedelta(days=6)


def test_sem_nada_na_url_abre_vendas_desta_semana(navegador, templates):
    resposta = navegador.get("/painel/relatorios")

    assert resposta.status_code == 200
    nome, variaveis = templates[-1]
    assert nome == "painel/relatorios.html"
    assert variaveis["aba"] == "vendas"
    assert (variaveis["inicio"], variaveis["fim"]) == esta_semana()


def test_aba_desconhecida_vira_vendas(navegador, templates):
    navegador.get("/painel/relatorios?aba=financeiro")

    assert templates[-1][1]["aba"] == "vendas"


def test_atalho_semana_passada(navegador, templates):
    navegador.get("/painel/relatorios?periodo=semana_passada")

    segunda, domingo = esta_semana()
    variaveis = templates[-1][1]
    assert (variaveis["inicio"], variaveis["fim"]) == (segunda - timedelta(days=7), domingo - timedelta(days=7))
    assert variaveis["periodo"] == "semana_passada"


def test_atalho_este_mes_vai_do_dia_1_ao_ultimo_dia(navegador, templates):
    navegador.get("/painel/relatorios?periodo=mes")

    variaveis = templates[-1][1]
    primeiro = date.today().replace(day=1)
    assert variaveis["inicio"] == primeiro
    # O último dia: o dia seguinte já é de outro mês
    assert variaveis["fim"].month == primeiro.month
    assert (variaveis["fim"] + timedelta(days=1)).day == 1


def test_datas_do_formulario(navegador, templates, hoje_no_banco, passado):
    navegador.get(f"/painel/relatorios?{passado}")

    variaveis = templates[-1][1]
    assert variaveis["inicio"] == hoje_no_banco - timedelta(days=30)
    assert variaveis["fim"] == hoje_no_banco - timedelta(days=1)


def test_atalho_vale_mais_que_as_datas(navegador, templates, passado):
    navegador.get(f"/painel/relatorios?periodo=mes&{passado}")

    assert templates[-1][1]["inicio"] == date.today().replace(day=1)


@pytest.mark.parametrize(
    "consulta, mensagem",
    [
        ("inicio=2026-10-31&fim=2026-10-01", "A data de início precisa ser antes da data de fim."),
        ("inicio=31/10/2026&fim=2026-11-01", "O campo 'início' deve estar no formato AAAA-MM-DD"),
    ],
    ids=["invertidas", "formato_errado"],
)
def test_datas_com_problema_avisam_e_mostram_esta_semana(navegador, templates, mensagens, consulta, mensagem):
    resposta = navegador.get(f"/painel/relatorios?{consulta}")

    assert resposta.status_code == 200
    assert mensagens == [("erro", mensagem)]
    variaveis = templates[-1][1]
    assert (variaveis["inicio"], variaveis["fim"]) == esta_semana()


def test_so_uma_das_datas_mostra_esta_semana_sem_aviso(navegador, templates, mensagens):
    navegador.get("/painel/relatorios?inicio=2026-10-01")

    assert mensagens == []
    variaveis = templates[-1][1]
    assert (variaveis["inicio"], variaveis["fim"]) == esta_semana()


def test_vendas_traz_o_resumo_e_um_total_por_dia(navegador, templates, passado):
    navegador.get(f"/painel/relatorios?{passado}")

    variaveis = templates[-1][1]
    assert variaveis["resumo"] == {
        "faturamento": Decimal("251.00"),
        "pedidos": 2,
        "ticket_medio": Decimal("125.50"),
        "lucro_estimado": Decimal("107.15"),
    }
    # 30 dias no período, um item por dia (com ou sem venda)
    assert len(variaveis["vendas_por_dia"]) == 30
    assert sum(dia["total"] for dia in variaveis["vendas_por_dia"]) == Decimal("251.00")


def test_periodo_sem_vendas_manda_a_lista_de_dias_vazia(navegador, templates):
    # A tela mostra "Sem vendas no período" quando a lista vem vazia
    navegador.get("/painel/relatorios?inicio=2020-01-01&fim=2020-01-31")

    variaveis = templates[-1][1]
    assert variaveis["resumo"]["pedidos"] == 0
    assert variaveis["vendas_por_dia"] == []


def test_produtos_separa_mais_vendidos_menos_vendidos_e_maior_faturamento(navegador, templates, passado):
    navegador.get(f"/painel/relatorios?aba=produtos&{passado}")

    variaveis = templates[-1][1]
    # Mais vendidos e maior faturamento: só quem vendeu alguma coisa
    assert [produto["nome"] for produto in variaveis["mais_vendidos"]] == [
        "Bolo de chocolate com brigadeiro",
        "Cento de brigadeiro",
    ]
    assert [produto["nome"] for produto in variaveis["maior_faturamento"]] == [
        "Cento de brigadeiro",  # 135,00
        "Bolo de chocolate com brigadeiro",  # 108,00
    ]
    # Menos vendidos: os que não venderam vêm primeiro
    quantidades = [produto["quantidade"] for produto in variaveis["menos_vendidos"]]
    assert quantidades == [0, 0, 0, 0, 0, 0, 0, 1, 1]


def test_cada_lista_de_produtos_tem_no_maximo_10(navegador, templates, banco, passado):
    # Mais dois produtos ativos (sem venda): agora são 11
    banco.execute(
        "INSERT INTO produto (nome, descricao, disponibilidade, preco_base, custo_mao_de_obra, margem_lucro) "
        "VALUES ('Pudim', '', 'encomenda', 50, 10, 2), ('Mousse', '', 'encomenda', 40, 8, 2)"
    )

    navegador.get(f"/painel/relatorios?aba=produtos&{passado}")

    assert len(templates[-1][1]["menos_vendidos"]) == 10


def test_insumos_traz_o_consumo_do_periodo(navegador, templates, hoje_no_banco):
    inicio, fim = hoje_no_banco - timedelta(days=5), hoje_no_banco - timedelta(days=1)

    navegador.get(f"/painel/relatorios?aba=insumos&inicio={inicio}&fim={fim}")

    consumidos = templates[-1][1]["insumos_consumidos"]
    assert [insumo["nome"] for insumo in consumidos] == [
        "Leite condensado (395g)",
        "Granulado de chocolate",
        "Forminha de papel n.4",
        "Chocolate meio amargo",
        "Manteiga sem sal",
    ]


def test_administrador_sem_acesso_financeiro_nao_ve_os_relatorios(navegador, templates, banco):
    banco.execute("UPDATE administrador SET acesso_financeiro = false WHERE id_usuario = 1")

    resposta = navegador.get("/painel/relatorios")

    assert resposta.status_code == 403
    assert templates[-1][1]["mensagem"] == "Seu usuário não tem acesso aos relatórios financeiros."
