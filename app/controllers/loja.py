"""
app / controllers / loja.py

Área do cliente: cardápio, carrinho, pedidos e perfil
"""

from flask import Blueprint, render_template

loja = Blueprint("loja", __name__, url_prefix="/loja")


# Vitrine (Tarefa 4)
@loja.get("")
def home():
    """Início da loja: pronta entrega e encomendas"""
    return render_template("loja/home.html")


@loja.get("/cardapio")
def catalogo():
    """Cardápio com filtro por disponibilidade e busca"""
    return render_template("loja/catalogo.html")


@loja.get("/produtos/<int:id>")
def produto(id):
    """Detalhe do produto com as opções de personalização"""
    return render_template("loja/produto.html")


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
def perfil():
    """Menu do perfil do cliente"""
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
