"""
app / models / __init__.py

Índice do pacote: lista os modelos na ordem lógica do domínio (não na ordem alfabética dos arquivos)

Permite escrever `from app.models import Cliente` em vez do caminho completo
"""

# Base
from .base import Entidade
from .senha import Senha, SenhaAusente
from .enums import (
    FormaPagamento,
    Perfil,
    StatusCompra,
    StatusPagamento,
    StatusPedido,
    TipoEntrega,
    TipoInsumo,
    TipoMovimentacao,
)

# Produtos
from .produto import Produto
from .opcao_personalizacao import OpcaoPersonalizacao

# Usuários
from .usuario import Usuario
from .cliente import Cliente
from .endereco import Endereco
from .funcionario import Funcionario
from .administrador import Administrador

# Estoque
from .insumo import Insumo
from .movimentacao_estoque import MovimentacaoEstoque
from .estoque import Estoque

# Pedidos, rreceitas e compras: adicionar aqui conforme forem criados
