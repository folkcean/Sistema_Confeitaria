"""
app / controllers / loja.py

Área do cliente: cardápio, carrinho, pedidos e perfil
"""

from flask import Blueprint, render_template, request, abort, session, redirect, url_for, flash

from app import usuarioLogado
from app.controllers.sessao import soCliente, repositorioUsuarios
from app.exceptions import ValidacaoError
from app.models import Endereco
from app.repositories.conexao_rep import obterConexao
from app.repositories.produtos_rep import RepositorioProdutos
from app.services.carrinho import Carrinho
from app.validators.campos import Validador, garantir
from app.validators.senha import ValidadorSenha

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
# Campos do formulário "Meus dados": os nomes são os mesmos dos setters do Cliente
CAMPOS_MEUS_DADOS = (
    "nome",
    "apelido",
    "telefone",
    "email",
    "data_nascimento",
    "instagram",
    "restricoes_alimentares",
    "preferencias",
)


@loja.get("/perfil")
@soCliente
def perfil():
    """Meu perfil (o usuario_atual já chega no template pelo context_processor)"""
    return render_template("loja/perfil.html")


@loja.get("/perfil/dados")
@soCliente
def meusDados():
    """Formulário para editar os dados do cliente e trocar a senha"""
    return _telaMeusDados()


@loja.post("/perfil/dados")
@soCliente
def meusDadosSalvar():
    """Aplica os campos do formulário pelos setters e grava"""
    cliente = usuarioLogado()
    try:
        # No model o e-mail é opcional, mas o login depende dele
        Validador.email(request.form.get("email"))
        # Cada setter valida o próprio campo (e levanta ValidacaoError se não servir)
        for nome_do_campo in CAMPOS_MEUS_DADOS:
            setattr(cliente, nome_do_campo, request.form.get(nome_do_campo))
        repositorioUsuarios().atualizarCliente(cliente)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return _telaMeusDados(), 400

    flash("Dados atualizados.", "sucesso")
    return redirect(url_for("loja.perfil"))


@loja.post("/perfil/senha")
@soCliente
def alterarSenha():
    """Troca a senha: confere a atual, a confirmação e a força da nova"""
    cliente = usuarioLogado()
    senha_atual = request.form.get("senha_atual", "")
    nova_senha = request.form.get("nova_senha", "")
    confirmar_senha = request.form.get("confirmar_senha", "")
    try:
        garantir(cliente.verificarSenha(senha_atual), ValidacaoError("A senha atual não confere."))
        garantir(nova_senha == confirmar_senha, ValidacaoError("As senhas novas não conferem."))
        # definirSenha valida a força (SenhaFracaError) e gera o hash novo
        cliente.definirSenha(nova_senha)
        repositorioUsuarios().atualizarSenha(cliente)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return _telaMeusDados(), 400

    flash("Senha alterada.", "sucesso")
    return redirect(url_for("loja.perfil"))


@loja.get("/perfil/enderecos")
@soCliente
def enderecos():
    """Endereços do cliente, com o formulário para cadastrar outro"""
    return render_template("loja/enderecos.html", enderecos=usuarioLogado().enderecos)


@loja.post("/perfil/enderecos/novo")
@soCliente
def enderecoAdicionar():
    """Cadastra um endereço novo para o cliente"""
    cliente = usuarioLogado()
    try:
        endereco = Endereco(
            logradouro=request.form.get("logradouro"),
            numero=request.form.get("numero"),
            bairro=request.form.get("bairro"),
            cidade=request.form.get("cidade"),
            cep=request.form.get("cep"),
            complemento=request.form.get("complemento", ""),
            apelido=request.form.get("apelido", ""),
        )
        # Vincula ao cliente (é isso que preenche endereco.id_cliente) e grava
        cliente.adicionarEndereco(endereco)
        repositorioUsuarios().salvarEndereco(endereco)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        pagina = render_template("loja/enderecos.html", enderecos=cliente.enderecos)
        return pagina, 400

    flash("Endereço cadastrado.", "sucesso")
    return redirect(url_for("loja.enderecos"))


@loja.get("/perfil/enderecos/<int:id>/remover")
@soCliente
def enderecoRemover(id):
    """Pergunta antes de remover o endereço"""
    endereco = _enderecoDoCliente(usuarioLogado(), id)
    return render_template(
        "confirmar.html",
        titulo="Remover endereço?",
        mensagem=endereco.formatado(),
        acao=url_for("loja.enderecoRemover", id=id),
        voltar=url_for("loja.enderecos"),
        rotulo_botao="Remover",
        perigo=True,
    )


@loja.post("/perfil/enderecos/<int:id>/remover")
@soCliente
def enderecoRemoverConfirmado(id):
    """Remove o endereço (só se for do cliente logado)"""
    cliente = usuarioLogado()
    endereco = _enderecoDoCliente(cliente, id)
    try:
        # Primeiro o banco: se um pedido usou o endereço, ele recusa e nada muda
        repositorioUsuarios().removerEndereco(endereco)
        cliente.removerEndereco(endereco)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("loja.enderecos"))

    flash("Endereço removido.", "sucesso")
    return redirect(url_for("loja.enderecos"))


def _telaMeusDados():
    """O formulário de meus dados (usado no GET e na volta dos erros)"""
    return render_template(
        "loja/meus_dados.html",
        cliente=usuarioLogado(),
        regras_senha=_regrasSenha(),
    )


def _regrasSenha():
    """Os textos das regras de senha, para a tela mostrar o que o validador cobra"""
    regras_senha = []
    for regra in ValidadorSenha.REGRAS:
        regras_senha.append(regra.descricao)
    return regras_senha


def _enderecoDoCliente(cliente, id_endereco):
    """
    O endereço com esse id, se for do cliente; senão 404.
    Procurar só nos endereços DELE é o que impede alguém de remover o endereço de outro
    pelo número na URL
    """
    enderecos_por_id = {}
    for endereco in cliente.enderecos:
        enderecos_por_id[endereco.id] = endereco
    return enderecos_por_id.get(id_endereco) or abort(404)
