import pytest

from app.exceptions import ValidacaoError
from app.models.cliente import Cliente
from app.models.endereco import Endereco

FORMATADO = (
    "Rua Barão de Miracema, 100, Apto 2 - Centro, Campos dos Goytacazes - CEP 28035-000"
)


def test_cep_com_traco_vira_8_digitos_e_complemento_vazio_vira_none():
    endereco = Endereco("Rua A", "10", "Centro", "Campos", "28035-000", complemento="")

    assert endereco.cep == "28035000"
    assert endereco.complemento is None


def test_formatado_devolve_o_endereco_por_extenso(endereco):
    assert endereco.formatado() == FORMATADO


def test_formatado_sem_complemento_nao_deixa_virgula_sobrando():
    endereco = Endereco("Rua A", "10", "Centro", "Campos", "28000-000")

    assert endereco.formatado() == "Rua A, 10 - Centro, Campos - CEP 28000-000"


def test_endereco_sem_dono_tem_cliente_e_id_cliente_none(endereco):
    assert endereco.cliente is None
    assert endereco.id_cliente is None


def test_endereco_e_imutavel(endereco):
    with pytest.raises(AttributeError):
        endereco.cidade = "x"  # type: ignore


# Cliente <-> Endereço
def test_adicionar_endereco_liga_os_dois_lados_e_id_cliente_e_o_do_dono(
    cliente, endereco
):
    cliente.adicionarEndereco(endereco)

    assert endereco.cliente is cliente
    assert endereco in cliente.enderecos
    assert endereco.id_cliente == 10


def test_endereco_que_ja_tem_dono_nao_vai_para_outro_cliente(
    cliente, outro_cliente, endereco
):
    cliente.adicionarEndereco(endereco)

    with pytest.raises(ValidacaoError, match="já pertence a um cliente"):
        outro_cliente.adicionarEndereco(endereco)

    assert endereco.cliente is cliente
    assert outro_cliente.enderecos == ()


def test_remover_endereco_de_outro_cliente_levanta_erro(outro_cliente, endereco):
    with pytest.raises(ValidacaoError, match="não pertence a este cliente"):
        outro_cliente.removerEndereco(endereco)


def test_remover_endereco_desfaz_os_dois_lados(cliente, endereco):
    cliente.adicionarEndereco(endereco)

    cliente.removerEndereco(endereco)

    assert endereco.cliente is None
    assert cliente.enderecos == ()


def test_lista_de_enderecos_do_cliente_nao_aceita_append(cliente, endereco):
    with pytest.raises(AttributeError):
        cliente.enderecos.append(endereco)  # type: ignore

    assert cliente.enderecos == ()


def test_id_cliente_do_endereco_e_none_quando_o_cliente_ainda_nao_tem_id(endereco):
    cliente_sem_id = Cliente("Ana Souza", None, "22999990001", None)

    cliente_sem_id.adicionarEndereco(endereco)

    assert endereco.cliente is cliente_sem_id
    assert endereco.id_cliente is None


def test_dados_operacionais_trazem_o_endereco_formatado(cliente, endereco):
    cliente.adicionarEndereco(endereco)

    dados = cliente.dadosOperacionais()

    assert dados["enderecos"] == [FORMATADO]
