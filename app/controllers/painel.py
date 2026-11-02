"""
app / controllers / painel.py

Área interna (funcionário e administrador): pedidos, estoque, receitas, produtos e gestão
"""
from decimal import Decimal

from flask import Blueprint, render_template, request, flash, redirect, url_for, abort

from app.controllers.sessao import conferirEquipe, soAdmin, usuarioLogado
from app.exceptions import ValidacaoError, AcessoNegadoError
from app.models import Insumo, Estoque, Perfil
from app.repositories.conexao_rep import obterConexao
from app.repositories.insumos_rep import RepositorioInsumos
from app.validators.campos import garantir

painel = Blueprint("painel", __name__, url_prefix="/painel")

painel.before_request(conferirEquipe)

# Início
@painel.get("")
def inicio():
    """Resumo do dia"""
    return render_template("painel/inicio.html")


# Pedidos
@painel.get("/pedidos")
def pedidos():
    """Lista de pedidos com filtros"""
    return render_template("painel/pedidos.html")


@painel.get("/pedidos/<int:id>")
def pedido(id):
    """Detalhe do pedido"""
    return "em construção"


@painel.post("/pedidos/<int:id>/status")
def pedidoStatus(id):
    """Avança o pedido para o próximo status"""
    return "em construção"


@painel.post("/pedidos/<int:id>/pagamento")
@soAdmin
def pedidoPagamento(id):
    """Registra o sinal ou o restante"""
    return "em construção"


@painel.get("/pedidos/<int:id>/cancelar")
@soAdmin
def pedidoCancelar(id):
    """Formulário de cancelamento com o motivo"""
    return "em construção"


@painel.post("/pedidos/<int:id>/cancelar")
@soAdmin
def pedidoCancelarConfirmado(id):
    """Cancela o pedido"""
    return "em construção"


# Produtos
@painel.get("/produtos")
def produtos():
    """Lista de produtos"""
    return render_template("painel/produtos.html")


@painel.get("/produtos/novo")
@soAdmin
def produtoNovo():
    """Formulário de produto novo"""
    return render_template("painel/produto_form.html")


@painel.post("/produtos/novo")
@soAdmin
def produtoNovoSalvar():
    """Cadastra o produto"""
    return "em construção"


@painel.get("/produtos/<int:id>")
@soAdmin
def produtoEditar(id):
    """Formulário de edição do produto"""
    return "em construção"


@painel.post("/produtos/<int:id>")
@soAdmin
def produtoEditarSalvar(id):
    """Salva a edição do produto"""
    return "em construção"


@painel.get("/produtos/<int:id>/desativar")
@soAdmin
def produtoDesativar(id):
    """Pergunta antes de tirar o produto do cardápio"""
    return "em construção"


@painel.post("/produtos/<int:id>/desativar")
@soAdmin
def produtoDesativarConfirmado(id):
    """Tira o produto do cardápio"""
    return "em construção"


@painel.post("/produtos/<int:id>/reativar")
@soAdmin
def produtoReativar(id):
    """Volta o produto para o cardápio"""
    return "em construção"


@painel.post("/produtos/<int:id>/opcoes")
@soAdmin
def opcaoAdicionar(id):
    """Acrescenta uma opção de personalização ao produto"""
    return "em construção"


@painel.post("/opcoes/<int:id>/alternar")
@soAdmin
def opcaoAlternar(id):
    """Liga ou desliga uma opção"""
    return "em construção"


@painel.post("/produtos/<int:id>/receitas")
@soAdmin
def produtoReceitaAdicionar(id):
    """Liga uma receita ao produto"""
    return "em construção"


@painel.post("/produtos/<int:id>/receitas/<int:id_receita>/remover")
@soAdmin
def produtoReceitaRemover(id, id_receita):
    """Desliga uma receita do produto"""
    return "em construção"


# Receitas (Tarefa 12)
@painel.get("/receitas")
def receitas():
    """Lista de receitas"""
    return render_template("painel/receitas.html")


@painel.get("/receitas/<int:id>")
def receita(id):
    """Receita com a regra de 3 (?quantidade=)"""
    return "em construção"


@painel.get("/receitas/nova")
@soAdmin
def receitaNova():
    """Formulário de receita nova"""
    return render_template("painel/receita_form.html")


@painel.post("/receitas/nova")
@soAdmin
def receitaNovaSalvar():
    """Cadastra a receita (ou só acrescenta dicionarios)"""
    return "em construção"


@painel.get("/receitas/<int:id>/editar")
@soAdmin
def receitaEditar(id):
    """Formulário de edição da receita"""
    return "em construção"


@painel.post("/receitas/<int:id>/editar")
@soAdmin
def receitaEditarSalvar(id):
    """Salva a edição da receita (ou só acrescenta dicionarios)"""
    return "em construção"


@painel.get("/receitas/<int:id>/desativar")
@soAdmin
def receitaDesativar(id):
    """Pergunta antes de tirar a receita de uso"""
    return "em construção"


@painel.post("/receitas/<int:id>/desativar")
@soAdmin
def receitaDesativarConfirmado(id):
    """Tira a receita de uso"""
    return "em construção"


@painel.post("/receitas/<int:id>/reativar")
@soAdmin
def receitaReativar(id):
    """Volta a receita para uso"""
    return "em construção"


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
    insumo = repo_estoque.buscarPorId(id)
    try:
        garantir(not insumo.ativo, f"O {insumo.nome} já está reativado.")
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
    return render_template("painel/fornecedores.html")


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
@painel.get("/clientes")
@soAdmin
def clientes():
    """Lista de clientes"""
    return "em construção"


@painel.get("/clientes/<int:id>")
@soAdmin
def cliente(id):
    """Ficha do cliente"""
    return "em construção"


@painel.get("/clientes/novo")
@soAdmin
def clienteNovo():
    """Formulário de cliente novo"""
    return render_template("painel/cliente_form.html")


@painel.post("/clientes/novo")
@soAdmin
def clienteNovoSalvar():
    """Cadastra o cliente"""
    return "em construção"


@painel.get("/clientes/<int:id>/editar")
@soAdmin
def clienteEditar(id):
    """Formulário de edição do cliente"""
    return "em construção"


@painel.post("/clientes/<int:id>/editar")
@soAdmin
def clienteEditarSalvar(id):
    """Salva a edição do cliente"""
    return "em construção"


@painel.post("/clientes/<int:id>/vip")
@soAdmin
def clienteVip(id):
    """Marca ou desmarca o cliente como VIP"""
    return "em construção"


@painel.get("/clientes/<int:id>/desativar")
@soAdmin
def clienteDesativar(id):
    """Pergunta antes de desativar o cliente"""
    return "em construção"


@painel.post("/clientes/<int:id>/desativar")
@soAdmin
def clienteDesativarConfirmado(id):
    """Desativa o cliente"""
    return "em construção"


@painel.post("/clientes/<int:id>/reativar")
@soAdmin
def clienteReativar(id):
    """Reativa o cliente"""
    return "em construção"


# Funcionários
@painel.get("/funcionarios")
@soAdmin
def funcionarios():
    """Lista da equipe"""
    return render_template("painel/funcionarios.html")


@painel.get("/funcionarios/novo")
@soAdmin
def funcionarioNovo():
    """Formulário de funcionário novo"""
    return render_template("painel/funcionario_form.html")


@painel.post("/funcionarios/novo")
@soAdmin
def funcionarioNovoSalvar():
    """Cadastra o funcionário"""
    return "em construção"


@painel.get("/funcionarios/<int:id>/editar")
@soAdmin
def funcionarioEditar(id):
    """Formulário de edição do funcionário"""
    return "em construção"


@painel.post("/funcionarios/<int:id>/editar")
@soAdmin
def funcionarioEditarSalvar(id):
    """Salva a edição do funcionário"""
    return "em construção"


@painel.get("/funcionarios/<int:id>/desativar")
@soAdmin
def funcionarioDesativar(id):
    """Pergunta antes de desligar o funcionário"""
    return "em construção"


@painel.post("/funcionarios/<int:id>/desativar")
@soAdmin
def funcionarioDesativarConfirmado(id):
    """Desliga o funcionário"""
    return "em construção"


@painel.post("/funcionarios/<int:id>/reativar")
@soAdmin
def funcionarioReativar(id):
    """Reativa o funcionário"""
    return "em construção"


# Relatórios
@painel.get("/relatorios")
@soAdmin
def relatorios():
    """Relatórios de vendas, produtos e insumos"""
    return render_template("painel/relatorios.html")


@painel.get("/relatorios/exportar")
@soAdmin
def relatorioExportar():
    """Os mesmos relatórios em CSV"""
    return "em construção"
