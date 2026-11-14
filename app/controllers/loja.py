"""
app / controllers / loja.py

Área do cliente: cardápio, carrinho, pedidos e perfil
"""
from datetime import datetime

from flask import Blueprint, render_template, request, abort, session, redirect, url_for, flash

from app import usuarioLogado
from app.controllers.sessao import soCliente, repositorioUsuarios
from app.exceptions import ValidacaoError
from app.models import Endereco, ItemPedido, Pedido, Estoque, Pagamento
from app.repositories.clientes_rep import RepositorioClientes
from app.repositories.conexao_rep import obterConexao
from app.repositories.insumos_rep import RepositorioInsumos
from app.repositories.pedidos_rep import RepositorioPedidos
from app.repositories.produtos_rep import RepositorioProdutos
from app.repositories.receitas_rep import RepositorioReceita
from app.services.carrinho import Carrinho
from app.services.precificacao import CalculadoraPreco
from app.validators.campos import Validador, garantir
from app.validators.senha import ValidadorSenha

loja = Blueprint("loja", __name__, url_prefix="/loja")
repo_clientes = RepositorioClientes(obterConexao)

repo_produtos = RepositorioProdutos(obterConexao)
repo_estoque = RepositorioInsumos(obterConexao)
repo_receitas = RepositorioReceita(obterConexao)
repo_pedidos = RepositorioPedidos(obterConexao, repo_clientes, repo_produtos)


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
    opcoes = []
    ids_das_opcoes = request.form.getlist("opcoes", type=int)
    for id_op in ids_das_opcoes:
        quantidade_opcao = request.form.get(f"qtd_opcao_{id_op}", 1, type=int)
        opcoes.append([id_op, quantidade_opcao])

    try:
        produto_id = request.form.get("produto_id", type=int)
        quantidade = request.form.get("quantidade", type=int)
        observacoes = request.form.get("observacoes", "")

        produto = repo_produtos.buscarAtivo(produto_id) or abort(404)
        Validador.textoOpcional(observacoes, "observacoes")

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
def _dataHoraDoFormulario(texto):
    """
    O texto do <input type="datetime-local"> (AAAA-MM-DDTHH:MM) como datetime
    Campo ausente (None) dá TypeError; vazio ou mal escrito dá ValueError: os dois viram a mesma mensagem
    """
    try:
        return datetime.fromisoformat(texto)
    except (TypeError, ValueError):
        raise ValidacaoError("Informe a data e a hora da entrega ou da retirada.")


def _enderecoEscolhido(cliente, tipo_entrega, id_endereco):
    """
    O endereço do cliente com esse id, só na entrega. Na retirada (ou tipo inválido) devolve None
    Entrega sem endereço válido também dá None, e o Pedido recusa com a mensagem dele
    """
    # Tem que ser o objeto de dentro de cliente.enderecos: o Pedido confere com `in`
    enderecos_por_id = {}
    for endereco in cliente.enderecos:
        enderecos_por_id[endereco.id] = endereco
    # Só a chave "entrega" existe: qualquer outro tipo cai no None do .get
    return {"entrega": enderecos_por_id.get(id_endereco)}.get(tipo_entrega)


def _produtosDoCarrinho(linhas, estoque):
    """
    {produto_id: Produto} com um objeto por id, já com opções e receitas (insumos do `estoque`)
    Produto que saiu do cardápio depois de ir para o carrinho é recusado
    """
    # Conjunto: o mesmo bolo em duas linhas vira um id só (carregarReceitas exige um objeto por id)
    ids = {linha["produto_id"] for linha in linhas}

    produtos = {}
    for id_produto in ids:
        produto = repo_produtos.buscarAtivo(id_produto)
        garantir(
            produto is not None,
            ValidacaoError("Um produto do carrinho saiu do cardápio. Remova-o e envie de novo."),
        )
        produtos[id_produto] = produto

    # O custo do item depende das receitas
    repo_produtos.carregarReceitas(list(produtos.values()), repo_receitas, estoque)
    return produtos


def _itemDaLinha(linha, produto, calculadora):
    """Transforma uma linha do carrinho num ItemPedido (decisões da Tarefa 0.6)"""
    item = ItemPedido(
        produto,
        linha["quantidade"],
        preco_unitario=produto.preco_base,
        custo_unitario=calculadora.custoUnitario(produto),
        observacoes=linha["observacoes"],
    )

    opcoes_por_id = {}
    for opcao in produto.opcoes:
        opcoes_por_id[opcao.id] = opcao

    for id_opcao, quantidade_opcao in linha["opcoes"]:
        opcao = opcoes_por_id.get(id_opcao)
        # Sem isso, o adicionarOpcao quebraria com AttributeError ao ler opcao.nome de um None
        garantir(
            opcao is not None,
            ValidacaoError("Uma opção escolhida não existe mais. Remova o item e adicione de novo."),
        )
        # No carrinho a opção é por unidade do produto; no item ela é da linha inteira
        item.adicionarOpcao(opcao, quantidade_opcao * linha["quantidade"])

    return item


@loja.post("/carrinho/enviar")
@soCliente
def pedidoEnviar():
    """Transforma o carrinho em pedido"""
    carrinho = Carrinho(session)
    cliente = usuarioLogado()
    try:
        garantir(carrinho.linhas, ValidacaoError("Seu carrinho está vazio."))

        tipo_entrega = request.form.get("tipo_entrega", "")
        pedido = Pedido(
            cliente,
            tipo_entrega,
            _dataHoraDoFormulario(request.form.get("data_entrega_ou_retirada")),
            endereco=_enderecoEscolhido(cliente, tipo_entrega, request.form.get("id_endereco_entrega", type=int)),
            nome_recebedor=request.form.get("nome_recebedor", ""),
            observacoes=request.form.get("observacoes", ""),
            # Nasce com a forma do sinal escolhida, mas aguardando o sinal (quem marca como pago é a dona)
            pagamento=Pagamento(forma_sinal=request.form.get("forma_pagamento_sinal") or None),
        )

        estoque = Estoque(repo_estoque.listar())
        produtos = _produtosDoCarrinho(carrinho.linhas, estoque)
        calculadora = CalculadoraPreco()
        for linha in carrinho.linhas:
            pedido.adicionarItem(_itemDaLinha(linha, produtos[linha["produto_id"]], calculadora))

        # Recusa a data antes da antecedência dos produtos (ex.: 48 h para o bolo)
        pedido.validarPrazo()
        repo_pedidos.salvarNovo(pedido)
    except ValidacaoError as erro:
        # O carrinho continua na sessão: só os campos do formulário se perdem
        flash(str(erro), "erro")
        return redirect(url_for("loja.carrinho"))

    carrinho.esvaziar()
    flash(f"Pedido #{pedido.id} enviado. A confeitaria vai mandar o orçamento com o valor final.", "sucesso")
    return redirect(url_for("loja.pedido", id=pedido.id))


@loja.get("/pedidos")
@soCliente
def pedidos():
    """Pedidos do cliente logado, do mais recente para o mais antigo"""
    return render_template("loja/pedidos.html", pedidos=repo_pedidos.listarDoCliente(usuarioLogado().id))


def valoresDoPedido(pedido):
    pass


@loja.get("/pedidos/<int:id>")
@soCliente
def pedido(id):
    """Acompanhamento de um pedido do cliente"""
    pedido = repo_pedidos.buscarPorId(id)
    # Só o dono abre. Pedido de outro cliente dá 404 (não revela que o número existe)
    # Se pedido for None, o `and` já dá falso e cai no abort
    (pedido and pedido.cliente_id == usuarioLogado().id) or abort(404)
    return render_template("loja/pedido.html", pedido=pedido, valores=valoresDoPedido(pedido))


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
        repo_clientes.atualizarCliente(cliente)
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
        repo_clientes.salvarEndereco(endereco)
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
        repo_clientes.removerEndereco(endereco)
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
