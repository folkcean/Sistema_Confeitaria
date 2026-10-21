from datetime import date, datetime, timedelta

import pytest

from app.exceptions import SenhaFracaError, ValidacaoError
from app.models.cliente import Cliente
from app.models.enums import Perfil
from app.models.usuario import Usuario


def novo_cliente(**kwargs):
    """Cliente mínimo para os testes de construção (só o que é obrigatório)"""
    return Cliente("Ana Souza", None, "22999990001", None, **kwargs)


# Usuario e construção do Cliente
def test_usuario_nao_pode_ser_instanciado_diretamente():
    with pytest.raises(TypeError, match="abstract"):
        Usuario("Ana Souza", None, "22999990001", None)  # type: ignore


def test_telefone_formatado_vira_so_digitos_e_email_vira_minusculo():
    cliente = Cliente("Ana Souza", "ANA@X.COM", "(22) 99999-0001", None)

    assert cliente.telefone == "22999990001"
    assert cliente.email == "ana@x.com"


def test_apelido_vazio_usa_o_nome():
    assert novo_cliente().apelido == "Ana Souza"


def test_valores_padrao_do_cliente():
    cliente = novo_cliente()

    assert cliente.instagram is None
    assert cliente.cliente_vip is False
    assert cliente.ativo is True


def test_data_cadastro_fica_entre_antes_e_depois():
    antes = datetime.now()
    cliente = novo_cliente()
    depois = datetime.now()

    assert antes <= cliente.data_cadastro <= depois


def test_observacoes_aceita_10000_caracteres_e_recusa_10001():
    assert novo_cliente(observacoes="a" * 10_000).observacoes == "a" * 10_000

    with pytest.raises(ValidacaoError, match="no máximo 10000"):
        novo_cliente(observacoes="a" * 10_001)


def test_cliente_tem_perfil_cliente_e_nao_acessa_dados_sensiveis():
    cliente = novo_cliente()

    assert cliente.perfil is Perfil.CLIENTE
    assert cliente.acessa_dados_sensiveis is False


# Setters
def test_nome_vazio_levanta_erro_e_mantem_o_nome_antigo(cliente):
    with pytest.raises(ValidacaoError, match="obrigatório"):
        cliente.nome = ""

    assert cliente.nome == "Ana Souza"


def test_email_none_e_aceito(cliente):
    cliente.email = None

    assert cliente.email is None


def test_telefone_invalido_levanta_erro(cliente):
    with pytest.raises(ValidacaoError, match="DDD"):
        cliente.telefone = "123"

    assert cliente.telefone == "22999990001"


def test_data_nascimento_no_futuro_levanta_erro(cliente):
    amanha = date.today() + timedelta(days=1)

    with pytest.raises(ValidacaoError, match="futuro"):
        cliente.data_nascimento = amanha

    assert cliente.data_nascimento is None


# Senha pelo usuário
def test_cliente_sem_senha_nao_confere_nenhuma_senha(outro_cliente):
    assert outro_cliente.verificarSenha("Bolo@2026") is False
    assert outro_cliente.senha_hash is None


def test_definir_senha_fraca_levanta_erro(cliente):
    with pytest.raises(SenhaFracaError):
        cliente.definirSenha("fraca")


def test_definir_senha_nova_substitui_a_antiga(cliente, senha_forte):
    cliente.definirSenha("Nova#Senha9")

    assert cliente.verificarSenha("Nova#Senha9") is True
    assert cliente.verificarSenha(senha_forte) is False


def test_senha_hash_nao_e_none_nem_a_senha_em_texto(cliente, senha_forte):
    hash_gerado = cliente.senha_hash

    assert hash_gerado is not None
    assert hash_gerado != senha_forte
    assert senha_forte not in hash_gerado


# CPF e estado
def test_cliente_nao_expoe_cpf_como_atributo_publico(cliente):
    assert hasattr(cliente, "cpf") is False
    assert hasattr(cliente, "__cpf") is False


def test_cpf_persistencia_e_obter_cpf_do_proprio_dono_devolvem_o_cpf(cliente):
    assert cliente.cpf_persistencia == "52998224725"
    assert cliente.obterCpf(cliente) == "52998224725"


def test_promover_e_remover_vip(cliente):
    assert cliente.cliente_vip is False

    cliente.promoverVip()
    assert cliente.cliente_vip is True

    cliente.removerVip()
    assert cliente.cliente_vip is False


def test_desativar_e_ativar(cliente):
    cliente.desativar()
    assert cliente.ativo is False

    cliente.ativar()
    assert cliente.ativo is True
