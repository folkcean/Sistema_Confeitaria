from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app.exceptions import ValidacaoError
from app.validators.campos import Validador, garantir

VALORES_VERDADEIROS = [True, 1, "abc", [0]]
VALORES_FALSOS = [False, 0, "", [], None]


# garantir
@pytest.mark.parametrize("condicao", VALORES_VERDADEIROS, ids=repr)
def test_condicao_verdadeira_nao_levanta(condicao):
    garantir(condicao, ValueError("Esse erro não é lançado"))


@pytest.mark.parametrize("condicao", VALORES_FALSOS, ids=repr)
def test_condicao_falsa_levanta_o_erro_passado(condicao):
    erro = ValueError("Esse erro é lançado")

    # Inverte a lógica do teste para que ele passe quando volte um erro.

    with pytest.raises(ValueError) as erro_levantado:
        garantir(condicao, erro)

    assert erro_levantado.value is erro


# Texto:
def test_texto_remove_espaco_das_pontas():
    resultado = Validador.texto(" palavra ", "nome")
    assert resultado == "palavra"


@pytest.mark.parametrize("palavra", ["", None, "     "], ids=repr)
def test_texto_invalido(palavra):
    with pytest.raises(ValidacaoError, match="obrigatório"):
        Validador.texto(palavra, "teste")


def test_texto_limite_max():
    assert Validador.texto("a" * 255, "teste") == "a" * 255

    with pytest.raises(ValidacaoError, match="no máximo 255"):
        Validador.texto("a" * 256, "teste")


def test_texto_respeita_max_len_personalizado():
    with pytest.raises(ValidacaoError, match="no máximo 3"):
        Validador.texto("abcd", "teste", max_len=3)


# Texto_Opcional:
@pytest.mark.parametrize("palavra", ["", None, "     "], ids=repr)
def test_texto_opcional_invalido(palavra):
    assert Validador.textoOpcional(palavra, "teste") is None


def test_texto_opcional_remove_espaco_das_pontas():
    assert Validador.textoOpcional("   x   ", "teste") == "x"


# Opcional
def test_opcional_devolve_none_quando_vazio_ou_none():
    assert Validador.opcional(Validador.email, "") is None


def test_opcional_aplica_validador_quando_ha_valor():
    assert Validador.opcional(Validador.email, "PESSOA@X.COM") == "pessoa@x.com"


def test_opcional_repassa_argumentos_extras_ao_validador():
    assert Validador.opcional(Validador.texto, "   oi   ", "campoDeTeste") == "oi"


@pytest.mark.skip(reason="Ent, email é obrigatório ou não ?")
def test_opcional_so_espacos_deveria_devolver_none():
    assert Validador.opcional(Validador.email, "       ") is None


@pytest.mark.parametrize(
    "email_invalido", ["teste", "teste@", "teste@x", "@x.com", "a b@x.com"]
)
def test_email_invalido_levanta_erro(email_invalido):
    with pytest.raises(ValidacaoError, match="E-mail inválido"):
        Validador.email(email_invalido)


def test_telefone_celular_formatado_devolve_so_digitos():
    assert Validador.telefone("(22) 99999-0001") == "22999990001"


@pytest.mark.parametrize("telefone_invalido", ["999990001", "229999900011"], ids=repr)
def test_telefone_com_digitos_fora_do_padrao_levanta_erro_de_ddd(telefone_invalido):
    with pytest.raises(ValidacaoError, match="Telefone inválido"):
        Validador.telefone(telefone_invalido)


def test_cpf_valido_devolve_so_digitos():
    assert Validador.cpf("529.982.247-25") == "52998224725"


@pytest.mark.parametrize(
    "cpf_invalido",
    ["111.111.111-11", "529.982.247-24", "123"],
    ids=["repetido", "digito_errado", "curto"],
)
def test_cpf_invalido_levanta_erro(cpf_invalido):
    with pytest.raises(ValidacaoError, match="CPF inválido"):
        Validador.cpf(cpf_invalido)


def test_digito_verificador_cpf_da_docstring():
    assert Validador._digitoVerificadorCpf("529982247") == 2


def test_cep_valido_devolve_so_digitos():
    assert Validador.cep("28035-000") == "28035000"


@pytest.mark.parametrize("cep_invalido", ["2800000", None], ids=repr)
def test_cep_invalido_levanta_erro_de_8_digitos(cep_invalido):
    with pytest.raises(ValidacaoError, match="8 dígitos"):
        Validador.cep(cep_invalido)


def test_data_aceita_date():
    assert Validador.data(date(2026, 10, 20), "teste") == date(2026, 10, 20)


def test_data_converte_datetime_para_date():
    resultado = Validador.data(datetime(2026, 10, 20, 15, 30), "teste")

    assert resultado == date(2026, 10, 20)
    assert type(resultado) is date


def test_data_converte_texto_iso_para_date():
    assert Validador.data("2026-10-20", "teste") == date(2026, 10, 20)


@pytest.mark.parametrize("data_invalida", ["20/10/2026", "2026-13-01"], ids=repr)
def test_data_com_formato_invalido_levanta_erro_de_formato(data_invalida):
    with pytest.raises(ValidacaoError, match="AAAA-MM-DD"):
        Validador.data(data_invalida, "teste")


def test_data_com_inteiro_levanta_erro_de_data_valida():
    with pytest.raises(ValidacaoError, match="data válida"):
        Validador.data(20261020, "teste")


def test_data_nascimento_aceita_hoje():
    hoje = date.today()

    assert Validador.dataNascimento(hoje) == hoje


def test_data_nascimento_recusa_amanha():
    amanha = date.today() + timedelta(days=1)

    with pytest.raises(ValidacaoError, match="futuro"):
        Validador.dataNascimento(amanha)


# dinheiro
def test_dinheiro_arredonda_meio_para_cima():
    resultado = Validador.dinheiro("10.005", "x")

    assert str(resultado) == "10.01"


def test_dinheiro_inteiro_ganha_duas_casas():
    resultado = Validador.dinheiro(5, "x")

    assert str(resultado) == "5.00"


def test_dinheiro_float_impreciso_vira_decimal_limpo():
    resultado = Validador.dinheiro(0.1 + 0.2, "x")

    assert resultado == Decimal("0.30")


def test_dinheiro_negativo_levanta_erro():
    with pytest.raises(ValidacaoError, match="negativo"):
        Validador.dinheiro(-1, "x")


@pytest.mark.parametrize("valor_invalido", ["abc", "NaN", "Infinity", None], ids=repr)
def test_dinheiro_nao_numerico_levanta_erro(valor_invalido):
    with pytest.raises(ValidacaoError, match="deve ser um número"):
        Validador.dinheiro(valor_invalido, "x")


def test_dinheiro_aceita_valor_maximo():
    resultado = Validador.dinheiro("99999999.99", "x")

    assert resultado == Decimal("99999999.99")


@pytest.mark.parametrize("valor_acima", ["100000000", "99999999.995"], ids=repr)
def test_dinheiro_acima_do_limite_levanta_erro(valor_acima):
    with pytest.raises(ValidacaoError, match="excede"):
        Validador.dinheiro(valor_acima, "x")


# percentual
def test_percentual_aceita_zero_e_cem():
    assert Validador.percentual("0", "x") == Decimal("0.00")
    assert Validador.percentual("100", "x") == Decimal("100.00")


def test_percentual_acima_de_cem_levanta_erro():
    with pytest.raises(ValidacaoError, match="entre 0 e 100"):
        Validador.percentual("100.01", "x")


def test_percentual_arredonda_para_duas_casas():
    resultado = Validador.percentual("12.345", "x")

    assert str(resultado) == "12.35"


# inteiroNaoNegativo
def test_inteiro_nao_negativo_aceita_zero():
    assert Validador.inteiroNaoNegativo(0, "x") == 0


@pytest.mark.parametrize("valor_invalido", [2.5, "3", True], ids=repr)
def test_inteiro_nao_negativo_tipo_invalido_levanta_erro(valor_invalido):
    with pytest.raises(ValidacaoError, match="inteiro"):
        Validador.inteiroNaoNegativo(valor_invalido, "x")


def test_inteiro_nao_negativo_negativo_levanta_erro():
    with pytest.raises(ValidacaoError, match="negativo"):
        Validador.inteiroNaoNegativo(-1, "x")
