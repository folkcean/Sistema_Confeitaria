"""
app / models / __init__.py

Índice do pacote: lista os modelos na ordem lógica do domínio (não na ordem alfabética dos arquivos)

Permite escrever `from app.models import Cliente` em vez do caminho completo
"""

from .administrador import Administrador
# Base
from .base import Entidade
from .cliente import Cliente
from .endereco import Endereco
from .enums import (FormaPagamento,
                    Perfil,
                    StatusCompra,
                    StatusPagamento,
                    StatusPedido,
                    TipoEntrega,
                    TipoInsumo,
                    TipoMovimentacao)
from .estoque import Estoque
from .funcionario import Funcionario
# Estoque  <- NOVO (incremento/modulo-estoque)
from .insumo import Insumo
from .movimentacao_estoque import MovimentacaoEstoque
from .opcao_personalizacao import OpcaoPersonalizacao
# Pedidos
from .pedido import ItemPedido, ItemPedidoOpcao, Pagamento, Pedido
# Produtos
from .produto import Produto
# Receitas
from .receita import ItemReceita, Receita
from .senha import Senha, SenhaAusente
# Usuários
from .usuario import Usuario
