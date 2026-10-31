"""
app / controllers / loja.py

Área do cliente: cardápio, carrinho, pedidos e perfil
"""

from flask import Blueprint, render_template, request, abort, session, redirect, url_for, flash

from app import usuarioLogado
from app.controllers.sessao import soCliente
from app.exceptions import ValidacaoError
from app.repositories.conexao_rep import obterConexao
from app.repositories.produtos_rep import RepositorioProdutos
from app.services.carrinho import Carrinho
from app.validators.campos import Validador, garantir

loja = Blueprint("loja", __name__, url_prefix="/loja")

repo_produtos = RepositorioProdutos(obterConexao)


# Vitrine (Tarefa 4)
@loja.get("")
def home():
    """Início da loja: o que tem pronto hoje e uma seleção de encomendas"""
    pronta_entrega = repo_produtos.listar(disponibilidade="pronta_entrega")
    encomendas = repo_produtos.listar(disponibilidade="encomenda")
    return render_template(
        "loja/home.html",
        pronta_entrega=pronta_entrega,
        encomendas=encomendas,
    )


@loja.get("/cardapio")
def catalogo():
    """Cardápio com filtro por disponibilidade e busca"""
    disponibilidade = request.args.get("disponibilidade")
    busca = request.args.get("q", "")

    produtos = repo_produtos.listar(disponibilidade, busca)

    return render_template("loja/catalogo.html", produtos=produtos, disponibilidade=disponibilidade, busca=busca)


@loja.get("/produtos/<int:id>")
def produto(id):
    """Detalhe do produto com as opções de personalização"""
    produto_buscado = repo_produtos.buscarAtivo(id) or abort(404)

    return render_template("loja/produto.html", produto=produto_buscado)


# Carrinho (Tarefa 5)
@loja.get("/carrinho")
def carrinho():
    """Itens do carrinho e formulário de envio do pedido"""
    dados_carrinho = Carrinho(session).montarCarrinho(repo_produtos)
    enderecos = getattr(usuarioLogado(), "enderecos", [])
    return render_template(
        "loja/carrinho.html",
        carrinho=dados_carrinho,
        enderecos=enderecos,
    )


@loja.post("/carrinho/adicionar")
def carrinhoAdicionar():
    """Põe um produto (com opções) no carrinho"""
    produto_id = request.form.get("produto_id", type=int)
    quantidade = request.form.get("quantidade", type=int)
    ids_das_opcoes = request.form.getlist("opcoes", type=int)
    observacoes = request.form.get("observacoes", "")

    produto = repo_produtos.buscarAtivo(produto_id) or abort(404)
    Validador.textoOpcional(observacoes, "observacoes")

    opcoes = []
    for id_op in ids_das_opcoes:
        quantidade_opcao = request.form.get(f"qtd_opcao_{id_op}", 1, type=int)
        opcoes.append([id_op, quantidade_opcao])

    try:
        Validador.inteiroPositivo(quantidade, "quantidade")
        _validarOpcoes(produto, opcoes)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        pagina = render_template("loja/produto.html", produto=produto)
        return pagina, 400

    Carrinho(session).adicionar(produto_id, quantidade, opcoes, observacoes)
    flash(f"{produto.nome} foi para o carrinho.", "sucesso")
    return redirect(url_for("loja.carrinho"))


def _validarOpcoes(produto, opcoes):
    """
    Confere as opções antes de irem para a sessão:
    cada id precisa ser deste produto, cada quantidade >= 1, e a opção precisa estar ativa
    """
    opcoes_por_id = {}
    for opcao in produto.opcoes:
        opcoes_por_id[opcao.id] = opcao

    opcoes_para_preco = []
    for id_opcao, quantidade_opcao in opcoes:
        garantir(
            id_opcao in opcoes_por_id,
            ValidacaoError("Uma das opções escolhidas não é deste produto."),
        )
        Validador.inteiroPositivo(quantidade_opcao, "quantidade da opção")
        opcoes_para_preco = opcoes_para_preco + [opcoes_por_id[id_opcao]] * quantidade_opcao

    # O calcularPreco recusa opção desligada: se passar aqui, a tela do carrinho também vai passar
    produto.calcularPreco(opcoes_para_preco)


@loja.post("/carrinho/<int:indice>/atualizar")
def carrinhoAtualizar(indice):
    """Muda a quantidade de uma linha do carrinho (0 remove a linha)"""
    quantidade = request.form.get("quantidade", type=int)
    try:
        # 0 é permitido aqui: é o botão "−" no último item
        Validador.inteiroNaoNegativo(quantidade, "quantidade")
        Validador.quantidade(quantidade, "quantidade")
        Carrinho(session).atualizar(indice, quantidade)

    except ValidacaoError as erro:
        flash(str(erro), "erro")
    except IndexError:
        abort(404)
    return redirect(url_for("loja.carrinho"))


@loja.post("/carrinho/<int:indice>/remover")
def carrinhoRemover(indice):
    """Tira uma linha do carrinho"""
    try:
        Carrinho(session).remover(indice)
    except IndexError:
        abort(404)
    return redirect(url_for("loja.carrinho"))


# Pedidos (Tarefa 10)
@loja.post("/carrinho/enviar")
def pedidoEnviar():
    """Transforma o carrinho em pedido"""
    return "em construção"


@loja.get("/pedidos")
def pedidos():
    """Pedidos do cliente logado"""
    return render_template("loja/pedidos.html")


@loja.get("/pedidos/<int:id>")
def pedido(id):
    """Acompanhamento de um pedido do cliente"""
    return "em construção"


# Perfil (Tarefa 6)
@loja.get("/perfil")
@soCliente
def perfil():
    return render_template("loja/perfil.html")


@loja.get("/perfil/dados")
def meusDados():
    """Formulário com os dados do cliente"""
    return render_template("loja/meus_dados.html")


@loja.post("/perfil/dados")
def meusDadosSalvar():
    """Salva os dados do cliente"""
    return "em construção"


@loja.post("/perfil/senha")
def alterarSenha():
    """Troca a senha do cliente"""
    return "em construção"


@loja.get("/perfil/enderecos")
def enderecos():
    """Endereços do cliente"""
    return render_template("loja/enderecos.html")


@loja.post("/perfil/enderecos/novo")
def enderecoAdicionar():
    """Cadastra um endereço novo"""
    return "em construção"


@loja.get("/perfil/enderecos/<int:id>/remover")
def enderecoRemover(id):
    """Pergunta antes de remover o endereço"""
    return "em construção"


@loja.post("/perfil/enderecos/<int:id>/remover")
def enderecoRemoverConfirmado(id):
    """Remove o endereço depois da confirmação"""
    return "em construção"
