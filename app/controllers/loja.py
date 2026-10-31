"""
app / controllers / loja.py

Área do cliente: cardápio, carrinho, pedidos e perfil
"""

from flask import Blueprint, render_template, request, abort

from app.controllers.sessao import soCliente
from app.repositories.conexao_rep import obterConexao
from app.repositories.produtos_rep import RepositorioProdutos

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
    return render_template("loja/carrinho.html")


@loja.post("/carrinho/adicionar")
def carrinhoAdicionar():
    """Põe um produto (com opções) no carrinho"""
    return "em construção"


@loja.post("/carrinho/<int:indice>/atualizar")
def carrinhoAtualizar(indice):
    """Muda a quantidade de uma linha do carrinho (0 remove)"""
    return "em construção"


@loja.post("/carrinho/<int:indice>/remover")
def carrinhoRemover(indice):
    """Tira uma linha do carrinho"""
    return "em construção"


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
