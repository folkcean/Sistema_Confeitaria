"""
app / controllers / painel.py

Área interna (funcionário e administrador): pedidos, estoque, receitas, produtos e gestão
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, current_app

from app.controllers.sessao import conferirEquipe, soAdmin, usuarioLogado
from app.exceptions import ValidacaoError, AcessoNegadoError, EstoqueInsuficienteError
from app.models import Insumo, Estoque, Perfil, Produto, OpcaoPersonalizacao, Cliente, Senha, Receita, \
    ItemReceita, Funcionario, StatusPedido
from app.repositories.clientes_rep import RepositorioClientes
from app.repositories.conexao_rep import obterConexao
from app.repositories.funcionarios_rep import RepositorioFuncionarios
from app.repositories.insumos_rep import RepositorioInsumos
from app.repositories.pedidos_rep import RepositorioPedidos
from app.repositories.produtos_rep import RepositorioProdutos
from app.repositories.receitas_rep import RepositorioReceita
from app.repositories.relatorios_rep import RepositorioRelatorios
from app.repositories.usuarios_rep import RepositorioUsuarios
from app.services.pedidos import valoresDoPedido
from app.services.precificacao import CalculadoraPreco
from app.validators.campos import garantir, Validador
from app.validators.senha import ValidadorSenha

painel = Blueprint("painel", __name__, url_prefix="/painel")

painel.before_request(conferirEquipe)


# Início
@painel.get("")
def inicio():
    """Resumo do dia: contadores, próximas entregas (7 dias) e vendas de hoje (só administradora)"""
    hoje = date.today()
    proximas = repo_pedidos.listarEntregasEntre(hoje, hoje + timedelta(days=7))

    # Faturamento é dado financeiro: só a administradora recebe (como o custo da receita)
    eh_admin = usuarioLogado().perfil is Perfil.ADMINISTRADOR
    vendas_hoje = {
        True: lambda: repo_relatorios.resumoVendas(hoje, hoje)["faturamento"],
        False: lambda: None,
    }[eh_admin]()

    resumo = {
        "pedidos_hoje": len(repo_pedidos.listarEntregasEntre(hoje, hoje)),
        "em_producao": len(repo_pedidos.listar(status="em_producao")),
        "abaixo_minimo": len(repo_estoque.listarComFiltro(filtro="baixo", busca="")),
        "vendas_hoje": vendas_hoje,
    }

    # alertas e aniversariantes dependem de regras que ainda não existem: listas vazias
    return render_template("painel/inicio.html", hoje=hoje, resumo=resumo, alertas=[],
                           proximas_entregas=proximas, aniversariantes=[])


# Pedidos
def _pedidoOu404(id_pedido):
    """O pedido com essa PK, com itens e opções, ou 404"""
    return repo_pedidos.buscarPorId(id_pedido) or abort(404)


@painel.get("/pedidos")
def pedidos():
    """Lista de pedidos com filtros (?q= nome ou telefone, ?status=, ?data=AAAA-MM-DD)"""
    busca = request.args.get("q", "")
    status = request.args.get("status", "")
    data_texto = request.args.get("data", "")
    try:
        # Vazio vira None; preenchido vira date ou levanta erro
        data = Validador.opcional(Validador.data, data_texto, "data")
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        # A lista sai sem o filtro de data
        data = None

    # Status inválido só devolve lista vazia, sem erro
    pedidos = repo_pedidos.listar(busca, status, data)
    return render_template("painel/pedidos.html", pedidos=pedidos, busca=busca,
                           status_filtro=status, data_filtro=data_texto)


@painel.get("/pedidos/<int:id>")
def pedido(id):
    """Detalhe do pedido"""
    pedido = _pedidoOu404(id)
    # Funcionário recebe os dados operacionais; administradora, os completos (a política é do model)
    cliente_dados = usuarioLogado().consultarCliente(pedido.cliente)
    proximos_status = [status.value for status in pedido.status.proximos()]
    return render_template("painel/pedido.html", pedido=pedido, cliente_dados=cliente_dados,
                           valores=valoresDoPedido(pedido), proximos_status=proximos_status)


def _definirTaxaDoFormulario(pedido):
    """
    Antes de ir para orçamento: define a taxa de entrega (depois do orçamento o pedido trava)
    Na retirada o campo não vem, e a taxa continua a que estava (0)
    """
    pedido.definirTaxaEntrega(request.form.get("taxa_entrega") or pedido.taxa_entrega)


def _semPreparo(pedido):
    """Os outros destinos não precisam de nada antes de mudar o status"""
    pass


def _gravarConfirmacao(pedido):
    """Confirmação: dá baixa nos insumos e grava o status, numa transação só"""
    estoque = _estoqueAtual()

    # Pelo cache do repositório já é um objeto por id: o dicionário só tira as repetições da lista
    produtos = {item.produto.id: item.produto for item in pedido.itens}
    repo_produtos.carregarReceitas(list(produtos.values()), repo_receitas, estoque)

    # Uma lista única de pares (insumo, quantidade) de todos os itens; o Estoque soma por insumo sozinho
    necessidades = [par for item in pedido.itens for par in item.produto.necessidades(item.quantidade)]

    # Tudo ou nada: se faltar algum insumo, levanta EstoqueInsuficienteError e nada é descontado
    movimentacoes = estoque.consumir(necessidades, id_pedido=pedido.id)
    repo_pedidos.atualizarComMovimentacoes(pedido, movimentacoes, repo_estoque)


@painel.post("/pedidos/<int:id>/status")
def pedidoStatus(id):
    """Avança o pedido para o próximo status"""
    pedido = _pedidoOu404(id)
    try:
        destino = Validador.opcaoDe(StatusPedido, request.form.get("novo_status"), "novo status")

        # Orçamento define a taxa antes de mudar; os outros não fazem nada
        {StatusPedido.ORCAMENTO: _definirTaxaDoFormulario}.get(destino, _semPreparo)(pedido)

        # O model recusa transição proibida, confirmação sem sinal, finalização sem pagamento
        # integral e cancelamento sem motivo
        pedido.avancarStatus(destino)

        # Confirmado dá baixa no estoque ao gravar; os outros só gravam o pedido
        {StatusPedido.CONFIRMADO: _gravarConfirmacao}.get(destino, repo_pedidos.atualizar)(pedido)
    except (ValidacaoError, EstoqueInsuficienteError) as erro:
        # EstoqueInsuficienteError não é ValidacaoError (os dois são filhos de ConfeitariaError)
        flash(str(erro), "erro")
        return redirect(url_for("painel.pedido", id=id))

    flash(f"Pedido #{id} agora está em {destino.value.replace('_', ' ')}.", "sucesso")
    return redirect(url_for("painel.pedido", id=id))


@painel.post("/pedidos/<int:id>/pagamento")
@soAdmin
def pedidoPagamento(id):
    """Registra o sinal ou o restante (não confirma o pedido sozinho)"""
    pedido = _pedidoOu404(id)
    try:
        registros = {"sinal_pago": pedido.registrarSinal, "pago": pedido.registrarPagamentoRestante}
        registrar = registros.get(request.form.get("status_pagamento"))
        garantir(registrar is not None, ValidacaoError("Escolha qual pagamento registrar."))
        # O model confere a forma e o momento (sinal só em orçamento; restante de confirmado até entregue)
        registrar(request.form.get("forma_pagamento"))
        repo_pedidos.atualizar(pedido)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("painel.pedido", id=id))

    flash(f"Pagamento registrado no pedido #{id}.", "sucesso")
    return redirect(url_for("painel.pedido", id=id))


@painel.get("/pedidos/<int:id>/cancelar")
@soAdmin
def pedidoCancelar(id):
    """Formulário de cancelamento com o motivo (a própria página já é a confirmação)"""
    return render_template("painel/pedido_cancelar.html", pedido=_pedidoOu404(id))


@painel.post("/pedidos/<int:id>/cancelar")
@soAdmin
def pedidoCancelarConfirmado(id):
    """Cancela o pedido. Não devolve o sinal nem os insumos"""
    pedido = _pedidoOu404(id)
    try:
        # Motivo vazio e pedido que ainda não foi confirmado são recusados pelo model
        pedido.avancarStatus(StatusPedido.CANCELADO, request.form.get("motivo_cancelamento", ""))
        repo_pedidos.atualizar(pedido)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        # A página volta com o que foi digitado
        return render_template("painel/pedido_cancelar.html", pedido=pedido), 400

    flash(f"Pedido #{id} cancelado. O sinal não é devolvido.", "sucesso")
    return redirect(url_for("painel.pedido", id=id))


# Produtos
repo_produtos = RepositorioProdutos(obterConexao)


@painel.get("/produtos")
def produtos():
    """Lista de produtos"""
    filtro = request.args.get("filtro", "")
    busca = request.args.get("q", "")

    abas = {
        "": (None, True),
        "pronta_entrega": ("pronta_entrega", True),
        "encomenda": ("encomenda", True),
        "inativos": (None, False),
    }

    disponibilidade, ativos = abas.get(filtro, abas[""])

    produtos = repo_produtos.listar_ativo_exclusivo(disponibilidade, busca, ativos)

    return render_template("painel/produtos.html", produtos=produtos, filtro=filtro, busca=busca)


@painel.get("/produtos/novo")
@soAdmin
def produtoNovo():
    """Formulário de produto novo"""
    return render_template("painel/produto_form.html", produto=None)


@painel.post("/produtos/novo")
@soAdmin
def produtoNovoSalvar():
    """Cadastra o produto"""
    foto = request.files.get("foto")
    try:
        caminho_foto = _caminhoDaFoto(foto)
        produto = Produto(
            nome=request.form.get("nome"),
            preco_base=request.form.get("preco_base"),
            descricao=request.form.get("descricao", ""),
            disponibilidade=request.form.get("disponibilidade"),
            custo_mao_de_obra=request.form.get("custo_mao_de_obra"),
            margem_lucro=request.form.get("margem_lucro"),
            custo_embalagem=request.form.get("custo_embalagem"),
            custo_indireto=request.form.get("custo_indireto"),
            percentual_perda=request.form.get("percentual_perda"),
            antecedencia_horas=request.form.get("antecedencia_horas", type=int),
            tamanho=request.form.get("tamanho", ""),
            caminho_foto=caminho_foto,
        )
        repo_produtos.salvar(produto)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return render_template("painel/produto_form.html", produto=None), 400

    _salvarFoto(foto, caminho_foto)
    flash(f"{produto.nome} cadastrado.", "sucesso")
    return redirect(url_for("painel.produtoEditar", id=produto.id))


@painel.get("/produtos/<int:id>")
@soAdmin
def produtoEditar(id):
    """Formulário de edição do produto (com as opções de personalização e as receitas ligadas)"""
    estoque = _estoqueAtual()
    produto = _produtoComReceitas(id, estoque)
    return render_template(
        "painel/produto_form.html",
        produto=produto,
        preco_sugerido=_precoSugerido(produto),
        receitas_disponiveis=_receitasDisponiveis(produto, estoque),
    )


@painel.post("/produtos/<int:id>")
@soAdmin
def produtoEditarSalvar(id):
    """Salva a edição do produto (e troca a foto, se vier uma nova)"""
    produto = repo_produtos.buscarPorId(id) or abort(404)
    foto = request.files.get("foto")
    try:
        # Cada alterar* do model valida o próprio campo
        produto.alterarNome(request.form.get("nome"))
        produto.alterarDescricao(request.form.get("descricao", ""))
        produto.alterarDisponibilidade(request.form.get("disponibilidade"))
        produto.alterarTamanho(request.form.get("tamanho", ""))
        produto.alterarAntecedencia(request.form.get("antecedencia_horas", type=int))
        produto.alterarPreco(request.form.get("preco_base"))
        produto.alterarCustoMaoDeObra(request.form.get("custo_mao_de_obra"))
        produto.alterarCustoEmbalagem(request.form.get("custo_embalagem"))
        produto.alterarCustoIndireto(request.form.get("custo_indireto"))
        produto.alterarPercentualPerda(request.form.get("percentual_perda"))
        produto.alterarMargemLucro(request.form.get("margem_lucro"))
        # Caminho da foto NOVA ("" se não veio arquivo); sem foto nova, fica a que já estava
        caminho_foto_nova = _caminhoDaFoto(foto)
        produto.alterarFoto(caminho_foto_nova or produto.caminho_foto)
        repo_produtos.salvar(produto)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return render_template("painel/produto_form.html", produto=produto), 400

    _salvarFoto(foto, caminho_foto_nova)
    flash(f"{produto.nome} atualizado.", "sucesso")
    return redirect(url_for("painel.produtoEditar", id=id))


@painel.get("/produtos/<int:id>/desativar")
@soAdmin
def produtoDesativar(id):
    """Pergunta antes de tirar o produto do cardápio"""
    produto = repo_produtos.buscarPorId(id) or abort(404)
    return render_template(
        "confirmar.html",
        titulo=f"Tirar {produto.nome} do cardápio?",
        mensagem="O produto some da loja, mas continua no histórico dos pedidos.",
        acao=url_for("painel.produtoDesativar", id=id),
        voltar=url_for("painel.produtos"),
        rotulo_botao="Tirar do cardápio",
        perigo=True,
    )


@painel.post("/produtos/<int:id>/desativar")
@soAdmin
def produtoDesativarConfirmado(id):
    """Tira o produto do cardápio e oferece desfazer (que reativa)"""
    produto = repo_produtos.buscarPorId(id) or abort(404)
    try:
        # alternarAtivo INVERTE: sem esta conferência, "desativar" um inativo o reativaria
        garantir(produto.ativo, ValidacaoError(f"{produto.nome} já está fora do cardápio."))
        produto.alternarAtivo()
        repo_produtos.salvar(produto)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("painel.produtos"))

    url_desfazer = url_for("painel.produtoReativar", id=id)
    flash(f"{produto.nome} saiu do cardápio.", "desfazer:" + url_desfazer)
    return redirect(url_for("painel.produtos"))


@painel.post("/produtos/<int:id>/reativar")
@soAdmin
def produtoReativar(id):
    """Volta o produto para o cardápio (aba Inativos e o "desfazer" da desativação)"""
    produto = repo_produtos.buscarPorId(id) or abort(404)
    try:
        garantir(not produto.ativo, ValidacaoError(f"{produto.nome} já está no cardápio."))
        produto.alternarAtivo()
        repo_produtos.salvar(produto)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("painel.produtos"))

    flash(f"{produto.nome} voltou ao cardápio.", "sucesso")
    return redirect(url_for("painel.produtos"))


@painel.post("/produtos/<int:id>/opcoes")
@soAdmin
def opcaoAdicionar(id):
    """Acrescenta uma opção de personalização ao produto"""
    produto = repo_produtos.buscarPorId(id) or abort(404)
    try:
        opcao = OpcaoPersonalizacao(
            nome=request.form.get("nome"),
            custo_adicional=request.form.get("custo_adicional"),
            descricao=request.form.get("descricao", ""),
        )
        # Vincula ao produto (é isso que preenche opcao.produto_id) e grava
        produto.adicionarOpcao(opcao)
        repo_produtos.salvarOpcao(opcao)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return render_template("painel/produto_form.html", produto=produto), 400

    flash(f"Opção {opcao.nome} adicionada.", "sucesso")
    return redirect(url_for("painel.produtoEditar", id=id))


def _opcaoDoProduto(produto, id):
    def _opcaoDoProduto(produto, id_opcao):
        """A opção com esse id dentro do produto, ou 404"""
        opcoes_por_id = {}
        for opcao in produto.opcoes:
            opcoes_por_id[opcao.id] = opcao
        return opcoes_por_id.get(id_opcao) or abort(404)

    pass


@painel.post("/opcoes/<int:id>/alternar")
@soAdmin
def opcaoAlternar(id):
    """Liga ou desliga uma opção (o botão mostra "Ligar" ou "Desligar" conforme o estado)"""
    # O id da URL é o da OPÇÃO: o repositório acha o produto dono, já com as opções
    produto = repo_produtos.buscarPorOpcao(id) or abort(404)
    opcao = _opcaoDoProduto(produto, id)

    opcao.alternarAtivo()
    repo_produtos.salvarOpcao(opcao)

    estado = {True: "ligada", False: "desligada"}[opcao.ativo]
    flash(f"Opção {opcao.nome} {estado}.", "sucesso")
    return redirect(url_for("painel.produtoEditar", id=produto.id))


def _produtoComReceitas(id_produto, estoque):
    """O produto com essa PK, já com as opções e as receitas (insumos do `estoque`), ou 404"""
    produto = repo_produtos.buscarPorId(id_produto) or abort(404)
    repo_produtos.carregarReceitas([produto], repo_receitas, estoque)
    return produto


def _precoSugerido(produto):
    """Preço sugerido do produto, ou None se não dá para calcular (receita desativada ou insumo sem custo)"""
    try:
        return produto.precoSugerido(CalculadoraPreco().custoIngredientes(produto))
    except ValidacaoError:
        return None


def _receitasDisponiveis(produto, estoque):
    """Receitas ativas que ainda não estão ligadas ao produto (o <select> de "ligar receita")"""
    # Compara por id: as receitas do listar são outros objetos, `is` nunca acharia as ligadas
    ligadas = {ligacao.receita.id for ligacao in produto.receitas}
    # listar sem filtro já traz só as ativas
    return list(filter(lambda receita: receita.id not in ligadas, repo_receitas.listar(estoque)))


@painel.post("/produtos/<int:id>/receitas")
@soAdmin
def produtoReceitaAdicionar(id):
    """Liga uma receita ao produto"""
    estoque = _estoqueAtual()
    produto = _produtoComReceitas(id, estoque)
    try:
        # Com type=int, um valor inválido vira None, e o validador recusa
        id_receita = Validador.inteiroPositivo(request.form.get("receita_id", type=int), "receita")
        receita = repo_receitas.buscarPorId(id_receita, estoque)
        garantir(receita is not None, ValidacaoError("Receita não encontrada."))
        # Só roda se a de cima passou: receita.nome nunca é lido de um None
        garantir(receita.ativa, ValidacaoError(f"A receita {receita.nome} está fora de uso."))
        # O model valida a quantidade. Receita repetida passa aqui (é outro objeto); quem barra é o banco
        ligacao = produto.adicionarReceita(receita, request.form.get("quantidade"))
        repo_produtos.salvarLigacaoReceita(produto, ligacao)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("painel.produtoEditar", id=id))

    flash(f"Receita {receita.nome} ligada a {produto.nome}.", "sucesso")
    return redirect(url_for("painel.produtoEditar", id=id))


@painel.post("/produtos/<int:id>/receitas/<int:id_receita>/remover")
@soAdmin
def produtoReceitaRemover(id, id_receita):
    """Desliga uma receita do produto"""
    produto = repo_produtos.buscarPorId(id) or abort(404)
    # Ligação inexistente: removerLigacaoReceita devolve False, e o `or` cai no 404
    repo_produtos.removerLigacaoReceita(id, id_receita) or abort(404)
    flash(f"Receita desligada de {produto.nome}.", "sucesso")
    return redirect(url_for("painel.produtoEditar", id=id))


repo_receitas = RepositorioReceita(obterConexao)


# Receitas (Tarefa 12)
def _estoqueAtual():
    """
    Estoque com todos os insumos (ativos e inativos), lido do banco agora.
    """
    return Estoque(repo_estoque.listar())


def _receitaOu404(id_receita, estoque):
    """A receita com essa PK, já com os ingredientes tirados do `estoque`, ou 404"""
    return repo_receitas.buscarPorId(id_receita, estoque) or abort(404)


def _insumosAtivos():
    """Insumos ativos, em ordem de nome, para o <select> de ingrediente do formulário de receita"""
    # A aba "" do estoque já é "só ativos" (RepositorioInsumos.FILTROS)
    return repo_estoque.listarComFiltro(filtro="", busca="")


def _custoDos(escalados):
    """Custo dos insumos escalados, em reais (2 casas), ou None se algum insumo não tem custo cadastrado"""
    try:
        total = sum((insumo.custoDe(quantidade) for insumo, quantidade in escalados), Decimal("0"))
        return total.quantize(Decimal("0.01"))
    except ValidacaoError:
        return None


def _itensDoFormulario(estoque):
    """
    ItemReceita NOVOS a partir das três listas do formulário (uma posição = uma linha da tabela)
    Linhas com o insumo em branco são ignoradas. Os insumos são os objetos de dentro do `estoque`
    """
    # Sem type=int: com type o Flask descarta os inválidos e as três listas ficam desalinhadas
    ids = request.form.getlist("insumo_id")
    quantidades = request.form.getlist("quantidade_necessaria")
    observacoes = request.form.getlist("observacoes")

    # Chave em texto para comparar direto com o que veio do formulário
    insumos_por_texto = {}
    for insumo in estoque.insumos:
        insumos_por_texto[str(insumo.id)] = insumo

    linhas = filter(lambda linha: linha[0], zip(ids, quantidades, observacoes))

    itens = []
    for id_texto, quantidade, observacao in linhas:
        insumo = insumos_por_texto.get(id_texto)
        garantir(insumo is not None, ValidacaoError("Um dos insumos escolhidos não existe."))
        itens.append(ItemReceita(insumo, quantidade, observacao))

    garantir(itens, ValidacaoError("Informe pelo menos um ingrediente."))
    return itens


@painel.get("/receitas")
def receitas():
    """Lista de receitas"""
    filtro = request.args.get("filtro", "")
    busca = request.args.get("q", "")
    receitas = repo_receitas.listar(_estoqueAtual(), filtro, busca)
    return render_template("painel/receitas.html", receitas=receitas, filtro=filtro, busca=busca)


@painel.get("/receitas/<int:id>")
def receita(id):
    """Receita com a regra de 3 (?quantidade=)"""
    estoque = _estoqueAtual()
    receita = _receitaOu404(id, estoque)

    texto = request.args.get("quantidade", "")
    try:
        # Vazio vira None; preenchido vira Decimal ou levanta erro
        quantidade = Validador.opcional(Validador.quantidadePositiva, texto, "quantidade")
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        quantidade = None

    # Sem quantidade, mostra a receita na quantidade original
    escalados = receita.escalar(quantidade or receita.rendimento_qtd)

    # escalar percorre os itens na mesma ordem de receita.itens: zip junta cada item com o seu par
    itens = []
    for item, (insumo, quantidade_escalada) in zip(receita.itens, escalados):
        itens.append({"insumo": insumo, "quantidade": quantidade_escalada, "observacoes": item.observacoes})

    # Custo é dado financeiro: só a administradora recebe (esconder no template não protege nada)
    eh_admin = usuarioLogado().perfil is Perfil.ADMINISTRADOR
    custo = {True: lambda: _custoDos(escalados),
             False: lambda: None}[eh_admin]()

    produtos = repo_produtos.listarPorReceita(id)

    return render_template("painel/receita.html", receita=receita, quantidade=quantidade, itens=itens,
                           custo=custo, produtos=produtos)


@painel.get("/receitas/nova")
@soAdmin
def receitaNova():
    """Formulário de receita nova"""
    return render_template("painel/receita_form.html", receita=None, insumos=_insumosAtivos())


@painel.post("/receitas/nova")
@soAdmin
def receitaNovaSalvar():
    """Cadastra a receita (ou só acrescenta linhas)"""
    # "Mais linhas" só redesenha o formulário; qualquer outra ação salva
    caminhos = {"mais_linhas": _formularioDeReceitaNova}
    return caminhos.get(request.form.get("acao"), _salvarReceitaNova)()


def _formularioDeReceitaNova():
    """Redesenha o formulário vazio. O template relê o que foi digitado e põe 3 linhas a mais"""
    return render_template("painel/receita_form.html", receita=None, insumos=_insumosAtivos())


def _salvarReceitaNova():
    """Monta a receita com o que veio do formulário e grava"""
    try:
        estoque = _estoqueAtual()
        receita = Receita(
            rendimento_qtd=request.form.get("rendimento_qtd"),
            rendimento_un=request.form.get("rendimento_un"),
            # Com type=int, um tempo vazio ou inválido vira 0
            tempo_preparo=request.form.get("tempo_preparo", 0, type=int),
            modo_preparo=request.form.get("modo_preparo", ""),
            complexidade=request.form.get("complexidade", ""),
        )
        # alterarNome é quem recusa o nome vazio
        receita.alterarNome(request.form.get("nome"))
        for item in _itensDoFormulario(estoque):
            receita.adicionarItem(item)
        repo_receitas.salvar(receita)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return render_template("painel/receita_form.html", receita=None, insumos=_insumosAtivos()), 400

    flash(f"Receita {receita.nome} cadastrada.", "sucesso")
    return redirect(url_for("painel.receita", id=receita.id))


@painel.get("/receitas/<int:id>/editar")
@soAdmin
def receitaEditar(id):
    """Formulário de edição da receita"""
    return _formularioDeEdicao(id)


@painel.post("/receitas/<int:id>/editar")
@soAdmin
def receitaEditarSalvar(id):
    """Salva a edição da receita (ou só acrescenta linhas)"""
    caminhos = {"mais_linhas": lambda: _formularioDeEdicao(id)}
    return caminhos.get(request.form.get("acao"), lambda: _salvarEdicao(id))()


def _formularioDeEdicao(id):
    """Formulário com a receita carregada do banco"""
    receita = _receitaOu404(id, _estoqueAtual())
    return render_template("painel/receita_form.html", receita=receita, insumos=_insumosAtivos())


def _salvarEdicao(id):
    """Aplica o formulário na receita e grava (os ingredientes são substituídos todos)"""
    estoque = _estoqueAtual()
    receita = _receitaOu404(id, estoque)
    try:
        receita.alterarNome(request.form.get("nome"))
        receita.alterarRendimento(request.form.get("rendimento_qtd"), request.form.get("rendimento_un"))
        receita.alterarTempoPreparo(request.form.get("tempo_preparo", 0, type=int))
        receita.alterarModoPreparo(request.form.get("modo_preparo", ""))
        receita.alterarComplexidade(request.form.get("complexidade", ""))

        # Lê antes de remover: se o formulário estiver errado, os itens antigos ainda estão lá
        novos = _itensDoFormulario(estoque)
        # receita.itens é uma cópia (tupla): dá para remover enquanto percorre
        for item in receita.itens:
            receita.removerItem(item)
        for item in novos:
            receita.adicionarItem(item)

        repo_receitas.salvar(receita)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return render_template("painel/receita_form.html", receita=receita, insumos=_insumosAtivos()), 400

    flash(f"Receita {receita.nome} atualizada.", "sucesso")
    return redirect(url_for("painel.receita", id=id))


@painel.get("/receitas/<int:id>/desativar")
@soAdmin
def receitaDesativar(id):
    """Pergunta antes de tirar a receita de uso"""
    receita = _receitaOu404(id, _estoqueAtual())
    nomes = ", ".join(produto.nome for produto in repo_produtos.listarPorReceita(id)) or "nenhum produto"
    return render_template(
        "confirmar.html",
        titulo=f"Tirar a receita {receita.nome} de uso?",
        mensagem="Ela continua no histórico, mas os produtos que a usam ficam sem custo calculado "
                 "e não podem ter pedidos confirmados até ela voltar.",
        detalhe=f"Usada em: {nomes}.",
        acao=url_for("painel.receitaDesativar", id=id),
        voltar=url_for("painel.receita", id=id),
        rotulo_botao="Tirar de uso",
        perigo=True,
    )


@painel.post("/receitas/<int:id>/desativar")
@soAdmin
def receitaDesativarConfirmado(id):
    """Tira a receita de uso e oferece desfazer (que reativa)"""
    receita = _receitaOu404(id, _estoqueAtual())
    try:
        garantir(receita.ativa, ValidacaoError(f"A receita {receita.nome} já está fora de uso."))
        receita.alternarAtiva()
        repo_receitas.salvar(receita)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("painel.receitas"))

    url_desfazer = url_for("painel.receitaReativar", id=id)
    flash(f"Receita {receita.nome} fora de uso.", "desfazer:" + url_desfazer)
    return redirect(url_for("painel.receitas"))


@painel.post("/receitas/<int:id>/reativar")
@soAdmin
def receitaReativar(id):
    """Volta a receita para uso (aba Fora de uso e o "desfazer" da desativação)"""
    receita = _receitaOu404(id, _estoqueAtual())
    try:
        garantir(not receita.ativa, ValidacaoError(f"A receita {receita.nome} já está em uso."))
        receita.alternarAtiva()
        repo_receitas.salvar(receita)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("painel.receitas"))

    flash(f"Receita {receita.nome} voltou a ser usada.", "sucesso")
    return redirect(url_for("painel.receitas"))


repo_estoque = RepositorioInsumos(obterConexao)


# Estoque
@painel.get("/estoque")
def estoque():
    """Lista de insumos com filtros"""
    busca = request.args.get("q", "")
    filtro = request.args.get("filtro", "") or None

    garantir(
        filtro != "inativos" or usuarioLogado().perfil is Perfil.ADMINISTRADOR,
        AcessoNegadoError("Só a administração vê os insumos inativos."),
    )

    insumos = repo_estoque.listarComFiltro(filtro=filtro, busca=busca)
    return render_template("painel/estoque.html", insumos=insumos, filtro=filtro, busca=busca)


@painel.get("/estoque/novo")
@soAdmin
def insumoNovo():
    """Formulário de insumo novo"""
    return render_template("painel/insumo_form.html", insumo=None)


@painel.post("/estoque/novo")
@soAdmin
def insumoNovoSalvar():
    """Cadastra o insumo"""
    try:
        insumo = Insumo(
            nome=request.form.get("nome"),
            tipo=request.form.get("tipo"),
            unidade_medida=request.form.get("unidade_medida"),
            unidade_receita=request.form.get("unidade_receita"),
            fator_conversao=request.form.get("fator_conversao"),
            quantidade_atual=request.form.get("quantidade_atual"),
            estoque_minimo=request.form.get("estoque_minimo"),
            custo_por_unidade=request.form.get("custo_por_unidade") or None,
        )
        repo_estoque.salvar(insumo)
    except ValidacaoError as error:
        flash(str(error), "erro")
        return render_template("painel/insumo_form.html", insumo=None), 400

    flash(f"{insumo.nome} cadastrado no estoque.", "sucesso")
    return redirect(url_for("painel.estoque"))


@painel.get("/estoque/<int:id>/editar")
@soAdmin
def insumoEditar(id):
    """Formulário de edição do insumo"""
    insumo = repo_estoque.buscarPorId(id) or abort(404)
    return render_template("painel/insumo_form.html", insumo=insumo)


@painel.post("/estoque/<int:id>/editar")
@soAdmin
def insumoEditarSalvar(id):
    """
    Salva o estoque mínimo e o custo. O model ainda não tem como alterar nome, tipo
    e unidades depois de criado; quando tiver, esses campos entram aqui
    """
    insumo = repo_estoque.buscarPorId(id) or abort(404)

    estoque_minimo = request.form.get("estoque_minimo")
    # Custo vazio = "ainda não informado" (None)
    custo_por_unidade = request.form.get("custo_por_unidade") or None

    try:
        insumo.alterarEstoqueMinimo(estoque_minimo)
        insumo.alterarCustoPorUnidade(custo_por_unidade)
        repo_estoque.salvar(insumo)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return render_template("painel/insumo_form.html", insumo=insumo), 400

    flash(f"{insumo.nome} atualizado.", "sucesso")
    return redirect(url_for("painel.estoque"))


@painel.get("/estoque/<int:id>/ajustar")
@soAdmin
def insumoAjustar(id):
    """Formulário de ajuste manual do estoque"""
    insumo = repo_estoque.buscarPorId(id) or abort(404)
    return render_template("painel/insumo_ajuste.html", insumo=insumo)


@painel.post("/estoque/<int:id>/ajustar")
@soAdmin
def insumoAjustarSalvar(id):
    """Registra o ajuste manual (movimentação do tipo "ajuste") e oferece desfazer"""
    # 1) O Estoque com todos os insumos, e o insumo que está DENTRO dele
    estoque = Estoque(repo_estoque.listar())
    insumo = _insumoDoEstoque(estoque, id)

    nova_quantidade = request.form.get("nova_quantidade")
    motivo = request.form.get("motivo", "")

    try:
        # 2) O required da caixa é só HTML: a rota confere de novo
        garantir(
            "confirmo" in request.form,
            ValidacaoError("Marque a caixa de confirmação para ajustar o estoque."),
        )
        # 3) Só o Administrador tem ajustarEstoque. Igual à atual e sem motivo já vêm recusados pelo model
        movimentacao = usuarioLogado().ajustarEstoque(estoque, insumo, nova_quantidade, motivo)
        # 4) Grava o saldo novo e a movimentação juntos (transação)
        repo_estoque.registrarMovimentacao(insumo, movimentacao)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return render_template("painel/insumo_ajuste.html", insumo=insumo), 400

    # 5) O flash com botão "Desfazer", que faz POST nesta URL
    url_desfazer = url_for("painel.ajusteDesfazer", id=movimentacao.id)
    flash(f"Estoque de {insumo.nome} ajustado.", "desfazer:" + url_desfazer)
    return redirect(url_for("painel.estoque"))


def _insumoDoEstoque(estoque, id_insumo):
    """
    O objeto Insumo que está DENTRO do estoque (o model confere com `is`), ou 404.
    Buscar à parte com buscarPorId daria outro objeto, e o Estoque recusaria
    """
    insumos_por_id = {}
    for insumo in estoque.insumos:
        insumos_por_id[insumo.id] = insumo
    return insumos_por_id.get(id_insumo) or abort(404)


@painel.post("/estoque/ajustes/<int:id>/desfazer")
@soAdmin
def ajusteDesfazer(id):
    """Desfaz um ajuste registrando outro de sinal contrário (o histórico não é apagado)"""
    estoque = Estoque(repo_estoque.listar())
    movimentacao = repo_estoque.buscarMovimentacao(id, estoque) or abort(404)
    try:
        contrario = usuarioLogado().desfazerAjusteEstoque(estoque, movimentacao)
        repo_estoque.registrarMovimentacao(movimentacao.insumo, contrario)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("painel.estoque"))

    flash(f"Ajuste de {movimentacao.insumo.nome} desfeito.", "sucesso")
    return redirect(url_for("painel.estoque"))


@painel.get("/estoque/<int:id>/desativar")
@soAdmin
def insumoDesativar(id):
    """Pergunta antes de desativar o insumo"""
    insumo = repo_estoque.buscarPorId(id) or abort(404)
    return render_template(
        "confirmar.html",
        titulo=f"Desativar {insumo.nome}?",
        mensagem="O insumo sai da lista porém continua no histórico.",
        acao=url_for("painel.insumoDesativar", id=id),
        voltar=url_for("painel.estoque"),
        rotulo_botao="Desativar",
        perigo=True,
    )


@painel.post("/estoque/<int:id>/desativar")
@soAdmin
def insumoDesativarConfirmado(id):
    """Desativa o insumo e oferece desfazer (que reativa)"""
    insumo = repo_estoque.buscarPorId(id) or abort(404)
    try:
        # alternarAtivo INVERTE: sem esta conferência, "desativar" um inativo o reativaria
        garantir(insumo.ativo, ValidacaoError(f"{insumo.nome} já está inativo."))
        insumo.alternarAtivo()
        repo_estoque.salvar(insumo)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("painel.estoque"))

    url_desfazer = url_for("painel.insumoReativar", id=id)
    flash(f"{insumo.nome} desativado.", "desfazer:" + url_desfazer)
    return redirect(url_for("painel.estoque"))


@painel.post("/estoque/<int:id>/reativar")
@soAdmin
def insumoReativar(id):
    insumo = repo_estoque.buscarPorId(id) or abort(404)
    try:
        garantir(not insumo.ativo, ValidacaoError("O {insumo.nome} já está reativado."))
        insumo.alternarAtivo()
        repo_estoque.salvar(insumo)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("painel.estoque"))

    url_desfazer = url_for("painel.insumoDesativar", id=id)
    flash(f"{insumo.nome} reativado.", "desfazer:" + url_desfazer)
    return redirect(url_for("painel.estoque"))


@painel.get("/estoque/lista-de-compras")
def listaCompras():
    """Insumos no mínimo e quanto comprar, com o custo estimado"""
    insumos_no_minimo = repo_estoque.listarComFiltro(filtro="baixo", busca="")

    itens = []
    total_estimado = Decimal("0")
    for insumo in insumos_no_minimo:
        comprar = (insumo.falta_para_minimo / insumo.fator_conversao).quantize(Decimal("0.01"))
        custo_unitario = insumo.custo_por_unidade or Decimal("0")
        custo_estimado = (comprar * custo_unitario).quantize(Decimal("0.01"))
        itens.append({
            "insumo": insumo,
            "comprar": comprar,
            "custo_estimado": custo_estimado,
            "fornecedor": None,
        })
        total_estimado = total_estimado + custo_estimado

    return render_template("painel/lista_compras.html", itens=itens, total_estimado=total_estimado)


# Compras
@painel.get("/compras")
@soAdmin
def compras():
    """Lista de compras de insumos"""
    return render_template("painel/compras.html")


@painel.get("/compras/nova")
@soAdmin
def compraNova():
    """Formulário de compra nova"""
    return render_template("painel/compra_form.html")


@painel.post("/compras/nova")
@soAdmin
def compraNovaSalvar():
    """Registra a compra (ou só acrescenta dicionarios)"""
    return "em construção"


@painel.get("/compras/<int:id>/receber")
@soAdmin
def compraReceber(id):
    """Pergunta antes de dar entrada da compra no estoque"""
    return "em construção"


@painel.post("/compras/<int:id>/receber")
@soAdmin
def compraReceberConfirmado(id):
    """Marca como recebida e dá entrada no estoque"""
    return "em construção"


@painel.get("/compras/<int:id>/cancelar")
@soAdmin
def compraCancelar(id):
    """Pergunta antes de cancelar a compra"""
    return "em construção"


@painel.post("/compras/<int:id>/cancelar")
@soAdmin
def compraCancelarConfirmado(id):
    """Cancela a compra"""
    return "em construção"


# Fornecedores
@painel.get("/fornecedores")
@soAdmin
def fornecedores():
    """Lista de fornecedores"""
    return render_template("painel/fornecedores.html")


@painel.get("/fornecedores/novo")
@soAdmin
def fornecedorNovo():
    """Formulário de fornecedor novo"""
    return render_template("painel/fornecedor_form.html", fornecedor=None)


@painel.post("/fornecedores/novo")
@soAdmin
def fornecedorNovoSalvar():
    """Cadastra o fornecedor"""
    return "em construção"


@painel.get("/fornecedores/<int:id>/editar")
@soAdmin
def fornecedorEditar(id):
    """Formulário de edição do fornecedor"""
    return "em construção"


@painel.post("/fornecedores/<int:id>/editar")
@soAdmin
def fornecedorEditarSalvar(id):
    """Salva a edição do fornecedor"""
    return "em construção"


@painel.get("/fornecedores/<int:id>/desativar")
@soAdmin
def fornecedorDesativar(id):
    """Pergunta antes de desativar o fornecedor"""
    return "em construção"


@painel.post("/fornecedores/<int:id>/desativar")
@soAdmin
def fornecedorDesativarConfirmado(id):
    """Desativa o fornecedor"""
    return "em construção"


@painel.post("/fornecedores/<int:id>/reativar")
@soAdmin
def fornecedorReativar(id):
    """Reativa o fornecedor"""
    return "em construção"


# Clientes (Tarefa 9)
repo_usuarios = RepositorioUsuarios(obterConexao)
repo_clientes = RepositorioClientes(obterConexao)
repo_pedidos = RepositorioPedidos(obterConexao, repo_usuarios, repo_produtos)


def _buscarUsuario(id_usuario, perfil):
    """O usuário com esse id, se for do perfil pedido; senão 404"""
    usuario = repo_usuarios.buscarPorId(id_usuario) or abort(404)
    # `and`: se o perfil confere, o resultado é o próprio usuário; se não, False, e o `or` chama o abort
    return (usuario.perfil is perfil and usuario) or abort(404)


def _clienteDoFormulario(**extras):
    """
    Monta um Cliente com os campos do cliente_form.html (o construtor valida todos).
    `extras` são os parâmetros que não vêm da tela (na edição: id, ativo, data de cadastro)
    """
    return Cliente(
        nome=request.form.get("nome"),
        apelido=request.form.get("apelido", ""),
        telefone=request.form.get("telefone"),
        email=request.form.get("email"),
        cpf=request.form.get("cpf"),
        data_nascimento=request.form.get("data_nascimento"),
        instagram=request.form.get("instagram", ""),
        restricoes_alimentares=request.form.get("restricoes_alimentares", ""),
        preferencias=request.form.get("preferencias", ""),
        observacoes=request.form.get("observacoes", ""),
        cliente_vip="cliente_vip" in request.form,
        **extras,
    )


@painel.get("/clientes")
@soAdmin
def clientes():
    """Lista de clientes com abas (ativos, VIP, inativos) e busca por nome ou telefone"""
    filtro = request.args.get("filtro", "")
    busca = request.args.get("q", "")
    lista = repo_clientes.listarClientes(filtro=filtro, busca=busca)
    return render_template("painel/clientes.html", clientes=lista, filtro=filtro, busca=busca)


@painel.get("/clientes/<int:id>")
@soAdmin
def cliente(id):
    """Ficha do cliente"""
    cliente_atual = _buscarUsuario(id, Perfil.CLIENTE)
    # consultarCliente: o administrador recebe os dados completos (o CPF passa pelo obterCpf)
    dados = usuarioLogado().consultarCliente(cliente_atual)
    # pedidos: histórico do cliente, quando o Pedido existir (Tarefa 10)
    return render_template("painel/cliente.html", cliente=cliente_atual, dados=dados,
                           pedidos=repo_pedidos.listarDoCliente(id))


@painel.get("/clientes/novo")
@soAdmin
def clienteNovo():
    """Formulário de cliente novo (ex.: quem pede pelo WhatsApp)"""
    return render_template("painel/cliente_form.html", cliente=None, dados=None)


@painel.post("/clientes/novo")
@soAdmin
def clienteNovoSalvar():
    """Cadastra o cliente. Sem senha: ele pode criar a conta depois, se quiser"""
    try:
        novo = _clienteDoFormulario()
        repo_clientes.cadastrarCliente(novo)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return render_template("painel/cliente_form.html", cliente=None, dados=None), 400

    flash(f"{novo.nome} cadastrado.", "sucesso")
    return redirect(url_for("painel.cliente", id=novo.id))


@painel.get("/clientes/<int:id>/editar")
@soAdmin
def clienteEditar(id):
    """Formulário de edição, preenchido com os dados completos"""
    cliente_atual = _buscarUsuario(id, Perfil.CLIENTE)
    dados = usuarioLogado().consultarCliente(cliente_atual)
    return render_template("painel/cliente_form.html", cliente=cliente_atual, dados=dados)


@painel.post("/clientes/<int:id>/editar")
@soAdmin
def clienteEditarSalvar(id):
    """
    Salva a edição. O CPF não tem setter no model, então o cliente é montado de novo com os
    dados do formulário, mantendo o que não vem da tela (id, ativo, data de cadastro)
    """
    cliente_atual = _buscarUsuario(id, Perfil.CLIENTE)
    try:
        editado = _clienteDoFormulario(
            id_usuario=cliente_atual.id,
            ativo=cliente_atual.ativo,
            data_cadastro=cliente_atual.data_cadastro,
        )
        # O atualizarCliente não mexe na senha: ela continua a que estava no banco
        repo_clientes.atualizarCliente(editado)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        dados = usuarioLogado().consultarCliente(cliente_atual)
        return render_template("painel/cliente_form.html", cliente=cliente_atual, dados=dados), 400

    flash(f"{editado.nome} atualizado.", "sucesso")
    return redirect(url_for("painel.cliente", id=id))


@painel.post("/clientes/<int:id>/vip")
@soAdmin
def clienteVip(id):
    """Marca ou desmarca o cliente como VIP"""
    cliente_atual = _buscarUsuario(id, Perfil.CLIENTE)
    # O método escolhido depende do estado atual (sem if): VIP perde, não VIP ganha
    alternar = {
        True: cliente_atual.removerVip,
        False: cliente_atual.promoverVip,
    }
    alternar[cliente_atual.cliente_vip]()
    repo_clientes.atualizarCliente(cliente_atual)

    mensagem = {True: "agora é VIP", False: "não é mais VIP"}[cliente_atual.cliente_vip]
    flash(f"{cliente_atual.nome} {mensagem}.", "sucesso")
    return redirect(url_for("painel.cliente", id=id))


@painel.get("/clientes/<int:id>/desativar")
@soAdmin
def clienteDesativar(id):
    """Pergunta antes de desativar o cliente"""
    cliente_atual = _buscarUsuario(id, Perfil.CLIENTE)
    return render_template(
        "confirmar.html",
        titulo=f"Desativar {cliente_atual.nome}?",
        mensagem="O cliente não consegue mais entrar na loja, mas o histórico de pedidos continua.",
        acao=url_for("painel.clienteDesativar", id=id),
        voltar=url_for("painel.cliente", id=id),
        rotulo_botao="Desativar",
        perigo=True,
    )


@painel.post("/clientes/<int:id>/desativar")
@soAdmin
def clienteDesativarConfirmado(id):
    """Desativa o cliente e oferece desfazer (que reativa)"""
    cliente_atual = _buscarUsuario(id, Perfil.CLIENTE)
    try:
        garantir(cliente_atual.ativo, ValidacaoError(f"{cliente_atual.nome} já está inativo."))
        cliente_atual.desativar()
        repo_clientes.atualizarCliente(cliente_atual)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("painel.cliente", id=id))

    url_desfazer = url_for("painel.clienteReativar", id=id)
    flash(f"{cliente_atual.nome} desativado.", "desfazer:" + url_desfazer)
    return redirect(url_for("painel.cliente", id=id))


@painel.post("/clientes/<int:id>/reativar")
@soAdmin
def clienteReativar(id):
    """Reativa o cliente"""
    cliente_atual = _buscarUsuario(id, Perfil.CLIENTE)
    try:
        garantir(not cliente_atual.ativo, ValidacaoError(f"{cliente_atual.nome} já está ativo."))
        cliente_atual.ativar()
        repo_clientes.atualizarCliente(cliente_atual)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("painel.cliente", id=id))

    flash(f"{cliente_atual.nome} reativado.", "sucesso")
    return redirect(url_for("painel.cliente", id=id))


# Funcionários
repo_funcionarios = RepositorioFuncionarios(obterConexao)


@painel.get("/funcionarios")
@soAdmin
def funcionarios():
    """Lista da equipe"""
    lista = repo_funcionarios.listarFuncionarios()
    return render_template("painel/funcionarios.html", funcionarios=lista)


@painel.get("/funcionarios/novo")
@soAdmin
def funcionarioNovo():
    """Formulário de funcionário novo"""
    return _telaFuncionario(None)


@painel.post("/funcionarios/novo")
@soAdmin
def funcionarioNovoSalvar():
    """Cadastra o funcionário (a senha inicial é obrigatória: é com ela que ele entra no painel)"""
    try:
        # Senha.criar valida a força; vazia também é recusada (não tem 8 caracteres)
        senha = Senha.criar(request.form.get("senha", ""))
        novo = _funcionarioDoFormulario(senha=senha)
        repo_funcionarios.cadastrarFuncionario(novo)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return _telaFuncionario(None), 400

    flash(f"{novo.nome} entrou para a equipe.", "sucesso")
    return redirect(url_for("painel.funcionarios"))


@painel.get("/funcionarios/<int:id>/editar")
@soAdmin
def funcionarioEditar(id):
    """Formulário de edição do funcionário"""
    funcionario = _buscarUsuario(id, Perfil.FUNCIONARIO)
    return _telaFuncionario(funcionario)


@painel.post("/funcionarios/<int:id>/editar")
@soAdmin
def funcionarioEditarSalvar(id):
    """
    Salva a edição. CPF e data de contratação não têm setter, então o funcionário é montado
    de novo com os dados do formulário (mantendo id, ativo e data de cadastro).
    Senha em branco = mantém a atual
    """
    atual = _buscarUsuario(id, Perfil.FUNCIONARIO)
    nova_senha = request.form.get("senha", "")
    try:
        editado = _funcionarioDoFormulario(
            id_usuario=atual.id,
            ativo=atual.ativo,
            data_cadastro=atual.data_cadastro,
        )
        # Valida a senha nova ANTES de gravar qualquer coisa (sem senha nova, não faz nada)
        nova_senha and editado.definirSenha(nova_senha)
        repo_funcionarios.atualizarFuncionario(editado)
        nova_senha and repo_funcionarios.atualizarSenha(editado)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return _telaFuncionario(atual), 400

    flash(f"{editado.nome} atualizado.", "sucesso")
    return redirect(url_for("painel.funcionarios"))


@painel.get("/funcionarios/<int:id>/desativar")
@soAdmin
def funcionarioDesativar(id):
    """Pergunta antes de desligar o funcionário"""
    funcionario = _buscarUsuario(id, Perfil.FUNCIONARIO)
    return render_template(
        "confirmar.html",
        titulo=f"Desligar {funcionario.nome}?",
        mensagem="A pessoa deixa de entrar no painel, mas o histórico continua.",
        acao=url_for("painel.funcionarioDesativar", id=id),
        voltar=url_for("painel.funcionarios"),
        rotulo_botao="Desligar",
        perigo=True,
    )


@painel.post("/funcionarios/<int:id>/desativar")
@soAdmin
def funcionarioDesativarConfirmado(id):
    """Desliga o funcionário e oferece desfazer (que reativa)"""
    funcionario = _buscarUsuario(id, Perfil.FUNCIONARIO)
    try:
        garantir(funcionario.ativo, ValidacaoError(f"{funcionario.nome} já está desligado."))
        funcionario.desativar()
        repo_funcionarios.atualizarFuncionario(funcionario)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("painel.funcionarios"))

    url_desfazer = url_for("painel.funcionarioReativar", id=id)
    flash(f"{funcionario.nome} desligado.", "desfazer:" + url_desfazer)
    return redirect(url_for("painel.funcionarios"))


@painel.post("/funcionarios/<int:id>/reativar")
@soAdmin
def funcionarioReativar(id):
    """Reativa o funcionário"""
    funcionario = _buscarUsuario(id, Perfil.FUNCIONARIO)
    try:
        garantir(not funcionario.ativo, ValidacaoError(f"{funcionario.nome} já está ativo."))
        funcionario.ativar()
        repo_funcionarios.atualizarFuncionario(funcionario)
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("painel.funcionarios"))

    flash(f"{funcionario.nome} voltou para a equipe.", "sucesso")
    return redirect(url_for("painel.funcionarios"))


def _funcionarioDoFormulario(**extras):
    """
    Monta um Funcionario com os campos do funcionario_form.html (o construtor valida todos).
    `extras`: o que não vem da tela (na edição: id, ativo, data de cadastro; no cadastro: a senha)
    """
    return Funcionario(
        nome=request.form.get("nome"),
        email=request.form.get("email"),
        telefone=request.form.get("telefone"),
        cpf=request.form.get("cpf"),
        cargo=request.form.get("cargo"),
        data_nascimento=request.form.get("data_nascimento"),
        data_contratacao=request.form.get("data_contratacao"),
        **extras,
    )


def _telaFuncionario(funcionario):
    """O formulário de funcionário (novo quando `funcionario` é None), com o CPF e as regras de senha"""
    cpf = funcionario and funcionario.obterCpf(usuarioLogado())
    regras_senha = []
    for regra in ValidadorSenha.REGRAS:
        regras_senha.append(regra.descricao)
    return render_template(
        "painel/funcionario_form.html",
        funcionario=funcionario,
        cpf=cpf,
        regras_senha=regras_senha,
    )


# Relatórios
repo_relatorios = RepositorioRelatorios(obterConexao)


@painel.get("/relatorios")
@soAdmin
def relatorios():
    """Relatórios de vendas, produtos e insumos"""
    _exigirAcessoFinanceiro()
    aba = _abaEscolhida()
    periodo = request.args.get("periodo", "")
    inicio, fim = _periodoDoRelatorio()

    # Cada aba devolve só as variáveis dela
    variaveis = ABAS_RELATORIO[aba](inicio, fim)

    return render_template(
        "painel/relatorios.html",
        aba=aba,
        periodo=periodo,
        inicio=inicio,
        fim=fim,
        **variaveis,
    )


@painel.get("/relatorios/exportar")
@soAdmin
def relatorioExportar():
    return "Em construcao"


def _abaEscolhida():
    """A aba pedida na URL; aba desconhecida vira "vendas" (o template também usa este nome)"""
    aba = request.args.get("aba", "vendas")
    # `and`/`or`: se a aba existe, fica ela; senão, "vendas"
    return (aba in ABAS_RELATORIO and aba) or "vendas"


def _exigirAcessoFinanceiro():
    """Faturamento é dado financeiro: só administrador com acesso_financeiro"""
    garantir(
        usuarioLogado().acesso_financeiro,
        AcessoNegadoError("Seu usuário não tem acesso aos relatórios financeiros."),
    )


def _estaSemana(hoje):
    """Segunda a domingo da semana de hoje (weekday(): segunda = 0 ... domingo = 6)"""
    inicio = hoje - timedelta(days=hoje.weekday())
    return inicio, inicio + timedelta(days=6)


def _semanaPassada(hoje):
    """A semana anterior à de hoje"""
    inicio, fim = _estaSemana(hoje)
    return inicio - timedelta(days=7), fim - timedelta(days=7)


def _esteMes(hoje):
    """Do dia 1 ao último dia do mês de hoje"""
    inicio = hoje.replace(day=1)
    # Dia 1 + 32 dias sempre cai no mês seguinte; o dia 1 dele menos um dia é o último deste mês
    primeiro_do_proximo = (inicio + timedelta(days=32)).replace(day=1)
    return inicio, primeiro_do_proximo - timedelta(days=1)


def _periodoLivre(hoje):
    """As datas do formulário (inicio e fim, AAAA-MM-DD)"""
    inicio = Validador.data(request.args.get("inicio"), "início")
    fim = Validador.data(request.args.get("fim"), "fim")
    garantir(inicio <= fim, ValidacaoError("A data de início precisa ser antes da data de fim."))
    return inicio, fim


ATALHOS_DE_PERIODO = {
    "semana": _estaSemana,
    "semana_passada": _semanaPassada,
    "mes": _esteMes,
}


def _periodoDoRelatorio():
    """
    (inicio, fim) do relatório: o atalho escolhido; sem atalho, as datas do formulário;
    sem nada, esta semana. Datas inválidas viram mensagem e caem em "esta semana"
    """
    periodo = request.args.get("periodo", "")
    tem_datas = bool(request.args.get("inicio") and request.args.get("fim"))
    # `or` em cadeia, sem if: o primeiro que não for falso é o escolhido
    escolher = ATALHOS_DE_PERIODO.get(periodo) or (tem_datas and _periodoLivre) or _estaSemana
    try:
        return escolher(date.today())
    except ValidacaoError as erro:
        flash(str(erro), "erro")
        return _estaSemana(date.today())


def _abaVendas(inicio, fim):
    """resumo e vendas_por_dia"""
    resumo = repo_relatorios.resumoVendas(inicio, fim)
    # Sem nenhum pedido no período, a lista vai vazia e a tela mostra "Sem vendas no período"
    vendas_por_dia = (resumo["pedidos"] and repo_relatorios.vendasPorDia(inicio, fim)) or []
    return {"resumo": resumo, "vendas_por_dia": vendas_por_dia}


def _abaProdutos(inicio, fim):
    """mais_vendidos, menos_vendidos e maior_faturamento"""
    produtos = repo_relatorios.vendasPorProduto(inicio, fim)
    vendidos = list(filter(lambda produto: produto["quantidade"] > 0, produtos))
    return {
        "mais_vendidos": sorted(vendidos, key=lambda produto: produto["quantidade"], reverse=True)[:10],
        "menos_vendidos": sorted(produtos, key=lambda produto: produto["quantidade"])[:10],
        "maior_faturamento": sorted(vendidos, key=lambda produto: produto["faturamento"], reverse=True)[:10],
    }


def _abaInsumos(inicio, fim):
    """insumos_consumidos"""
    return {"insumos_consumidos": repo_relatorios.insumosConsumidos(inicio, fim)}


ABAS_RELATORIO = {
    "vendas": _abaVendas,
    "produtos": _abaProdutos,
    "insumos": _abaInsumos,
}

EXTENSOES_FOTO = (".jpg", ".jpeg", ".png", ".webp")


def _caminhoDaFoto(arquivo):
    """
    Caminho (relativo a static/) onde a foto vai ser salva, ou "" se não veio foto.
    Recusa extensão que não seja de imagem
    """
    # FileStorage sem arquivo escolhido é falso: o `and` devolve ele mesmo e o `or` troca por ""
    return (arquivo and _nomeNovoDaFoto(arquivo)) or ""


def _nomeNovoDaFoto(arquivo):
    """Gera um nome único para a foto, mantendo a extensão"""
    extensao = Path(arquivo.filename).suffix.lower()
    garantir(
        extensao in EXTENSOES_FOTO,
        ValidacaoError("A foto precisa ser JPG, PNG ou WEBP."),
    )
    return f"fotos/{uuid.uuid4().hex}{extensao}"


def _salvarFoto(arquivo, caminho):
    """Grava o arquivo em static/<caminho> (não faz nada se não veio foto)"""
    destino = Path(current_app.static_folder) / caminho
    # `caminho and ...`: sem foto (caminho vazio), não grava nada
    caminho and arquivo.save(destino)
