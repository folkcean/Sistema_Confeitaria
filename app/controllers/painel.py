"""
app / controllers / painel.py

Área interna (funcionário e administrador): pedidos, estoque, receitas, produtos e gestão
"""

from flask import Blueprint, render_template

painel = Blueprint("painel", __name__, url_prefix="/painel")


# Início (Tarefa 11)
@painel.get("")
def inicio():
    """Resumo do dia"""
    return render_template("painel/inicio.html")


# Pedidos (Tarefa 10)
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
def pedidoPagamento(id):
    """Registra o sinal ou o restante"""
    return "em construção"


@painel.get("/pedidos/<int:id>/cancelar")
def pedidoCancelar(id):
    """Formulário de cancelamento com o motivo"""
    return "em construção"


@painel.post("/pedidos/<int:id>/cancelar")
def pedidoCancelarConfirmado(id):
    """Cancela o pedido"""
    return "em construção"


# Produtos (Tarefa 8)
@painel.get("/produtos")
def produtos():
    """Lista de produtos"""
    return render_template("painel/produtos.html")


@painel.get("/produtos/novo")
def produtoNovo():
    """Formulário de produto novo"""
    return render_template("painel/produto_form.html")


@painel.post("/produtos/novo")
def produtoNovoSalvar():
    """Cadastra o produto"""
    return "em construção"


@painel.get("/produtos/<int:id>")
def produtoEditar(id):
    """Formulário de edição do produto"""
    return "em construção"


@painel.post("/produtos/<int:id>")
def produtoEditarSalvar(id):
    """Salva a edição do produto"""
    return "em construção"


@painel.get("/produtos/<int:id>/desativar")
def produtoDesativar(id):
    """Pergunta antes de tirar o produto do cardápio"""
    return "em construção"


@painel.post("/produtos/<int:id>/desativar")
def produtoDesativarConfirmado(id):
    """Tira o produto do cardápio"""
    return "em construção"


@painel.post("/produtos/<int:id>/reativar")
def produtoReativar(id):
    """Volta o produto para o cardápio"""
    return "em construção"


@painel.post("/produtos/<int:id>/opcoes")
def opcaoAdicionar(id):
    """Acrescenta uma opção de personalização ao produto"""
    return "em construção"


@painel.post("/opcoes/<int:id>/alternar")
def opcaoAlternar(id):
    """Liga ou desliga uma opção"""
    return "em construção"


@painel.post("/produtos/<int:id>/receitas")
def produtoReceitaAdicionar(id):
    """Liga uma receita ao produto"""
    return "em construção"


@painel.post("/produtos/<int:id>/receitas/<int:id_receita>/remover")
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
def receitaNova():
    """Formulário de receita nova"""
    return render_template("painel/receita_form.html")


@painel.post("/receitas/nova")
def receitaNovaSalvar():
    """Cadastra a receita (ou só acrescenta dicionarios)"""
    return "em construção"


@painel.get("/receitas/<int:id>/editar")
def receitaEditar(id):
    """Formulário de edição da receita"""
    return "em construção"


@painel.post("/receitas/<int:id>/editar")
def receitaEditarSalvar(id):
    """Salva a edição da receita (ou só acrescenta dicionarios)"""
    return "em construção"


@painel.get("/receitas/<int:id>/desativar")
def receitaDesativar(id):
    """Pergunta antes de tirar a receita de uso"""
    return "em construção"


@painel.post("/receitas/<int:id>/desativar")
def receitaDesativarConfirmado(id):
    """Tira a receita de uso"""
    return "em construção"


@painel.post("/receitas/<int:id>/reativar")
def receitaReativar(id):
    """Volta a receita para uso"""
    return "em construção"


# Estoque (Tarefa 7)
@painel.get("/estoque")
def estoque():
    """Lista de insumos com filtros"""
    return render_template("painel/estoque.html")


@painel.get("/estoque/novo")
def insumoNovo():
    """Formulário de insumo novo"""
    return render_template("painel/insumo_form.html")


@painel.post("/estoque/novo")
def insumoNovoSalvar():
    """Cadastra o insumo"""
    return "em construção"


@painel.get("/estoque/<int:id>/editar")
def insumoEditar(id):
    """Formulário de edição do insumo"""
    return "em construção"


@painel.post("/estoque/<int:id>/editar")
def insumoEditarSalvar(id):
    """Salva a edição do insumo"""
    return "em construção"


@painel.get("/estoque/<int:id>/ajustar")
def insumoAjustar(id):
    """Formulário de ajuste manual do estoque"""
    return "em construção"


@painel.post("/estoque/<int:id>/ajustar")
def insumoAjustarSalvar(id):
    """Registra o ajuste manual"""
    return "em construção"


@painel.get("/estoque/<int:id>/desativar")
def insumoDesativar(id):
    """Pergunta antes de desativar o insumo"""
    return "em construção"


@painel.post("/estoque/<int:id>/desativar")
def insumoDesativarConfirmado(id):
    """Desativa o insumo"""
    return "em construção"


@painel.post("/estoque/<int:id>/reativar")
def insumoReativar(id):
    """Reativa o insumo"""
    return "em construção"


@painel.get("/estoque/lista-de-compras")
def listaCompras():
    """Insumos no mínimo e quanto comprar"""
    return render_template("painel/lista_compras.html")


# Compras (Tarefa 13)
@painel.get("/compras")
def compras():
    """Lista de compras de insumos"""
    return render_template("painel/compras.html")


@painel.get("/compras/nova")
def compraNova():
    """Formulário de compra nova"""
    return render_template("painel/compra_form.html")


@painel.post("/compras/nova")
def compraNovaSalvar():
    """Registra a compra (ou só acrescenta dicionarios)"""
    return "em construção"


@painel.get("/compras/<int:id>/receber")
def compraReceber(id):
    """Pergunta antes de dar entrada da compra no estoque"""
    return "em construção"


@painel.post("/compras/<int:id>/receber")
def compraReceberConfirmado(id):
    """Marca como recebida e dá entrada no estoque"""
    return "em construção"


@painel.get("/compras/<int:id>/cancelar")
def compraCancelar(id):
    """Pergunta antes de cancelar a compra"""
    return "em construção"


@painel.post("/compras/<int:id>/cancelar")
def compraCancelarConfirmado(id):
    """Cancela a compra"""
    return "em construção"


# Fornecedores (Tarefa 13)
@painel.get("/fornecedores")
def fornecedores():
    """Lista de fornecedores"""
    return render_template("painel/fornecedores.html")


@painel.get("/fornecedores/novo")
def fornecedorNovo():
    """Formulário de fornecedor novo"""
    return render_template("painel/fornecedores.html")


@painel.post("/fornecedores/novo")
def fornecedorNovoSalvar():
    """Cadastra o fornecedor"""
    return "em construção"


@painel.get("/fornecedores/<int:id>/editar")
def fornecedorEditar(id):
    """Formulário de edição do fornecedor"""
    return "em construção"


@painel.post("/fornecedores/<int:id>/editar")
def fornecedorEditarSalvar(id):
    """Salva a edição do fornecedor"""
    return "em construção"


@painel.get("/fornecedores/<int:id>/desativar")
def fornecedorDesativar(id):
    """Pergunta antes de desativar o fornecedor"""
    return "em construção"


@painel.post("/fornecedores/<int:id>/desativar")
def fornecedorDesativarConfirmado(id):
    """Desativa o fornecedor"""
    return "em construção"


@painel.post("/fornecedores/<int:id>/reativar")
def fornecedorReativar(id):
    """Reativa o fornecedor"""
    return "em construção"


# Clientes (Tarefa 9)
@painel.get("/clientes")
def clientes():
    """Lista de clientes"""
    return "em construção"


@painel.get("/clientes/<int:id>")
def cliente(id):
    """Ficha do cliente"""
    return "em construção"


@painel.get("/clientes/novo")
def clienteNovo():
    """Formulário de cliente novo"""
    return render_template("painel/cliente_form.html")


@painel.post("/clientes/novo")
def clienteNovoSalvar():
    """Cadastra o cliente"""
    return "em construção"


@painel.get("/clientes/<int:id>/editar")
def clienteEditar(id):
    """Formulário de edição do cliente"""
    return "em construção"


@painel.post("/clientes/<int:id>/editar")
def clienteEditarSalvar(id):
    """Salva a edição do cliente"""
    return "em construção"


@painel.post("/clientes/<int:id>/vip")
def clienteVip(id):
    """Marca ou desmarca o cliente como VIP"""
    return "em construção"


@painel.get("/clientes/<int:id>/desativar")
def clienteDesativar(id):
    """Pergunta antes de desativar o cliente"""
    return "em construção"


@painel.post("/clientes/<int:id>/desativar")
def clienteDesativarConfirmado(id):
    """Desativa o cliente"""
    return "em construção"


@painel.post("/clientes/<int:id>/reativar")
def clienteReativar(id):
    """Reativa o cliente"""
    return "em construção"


# Funcionários (Tarefa 9)
@painel.get("/funcionarios")
def funcionarios():
    """Lista da equipe"""
    return render_template("painel/funcionarios.html")


@painel.get("/funcionarios/novo")
def funcionarioNovo():
    """Formulário de funcionário novo"""
    return render_template("painel/funcionario_form.html")


@painel.post("/funcionarios/novo")
def funcionarioNovoSalvar():
    """Cadastra o funcionário"""
    return "em construção"


@painel.get("/funcionarios/<int:id>/editar")
def funcionarioEditar(id):
    """Formulário de edição do funcionário"""
    return "em construção"


@painel.post("/funcionarios/<int:id>/editar")
def funcionarioEditarSalvar(id):
    """Salva a edição do funcionário"""
    return "em construção"


@painel.get("/funcionarios/<int:id>/desativar")
def funcionarioDesativar(id):
    """Pergunta antes de desligar o funcionário"""
    return "em construção"


@painel.post("/funcionarios/<int:id>/desativar")
def funcionarioDesativarConfirmado(id):
    """Desliga o funcionário"""
    return "em construção"


@painel.post("/funcionarios/<int:id>/reativar")
def funcionarioReativar(id):
    """Reativa o funcionário"""
    return "em construção"


# Relatórios (Tarefa 14)
@painel.get("/relatorios")
def relatorios():
    """Relatórios de vendas, produtos e insumos"""
    return render_template("painel/relatorios.html")


@painel.get("/relatorios/exportar")
def relatorioExportar():
    """Os mesmos relatórios em CSV"""
    return "em construção"
