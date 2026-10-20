"""
app/models/__init__.py
Índice do pacote: lista os modelos na ordem lógica do domínio (não na ordem alfabética dos arquivos).
Permite escrever `from app.models import Cliente` em vez do caminho completo.
"""

# Base
from .administrador import Administrador
from .base import Entidade
from .cliente import Cliente
from .endereco import Endereco
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
from .funcionario import Funcionario
from .opcao_personalizacao import OpcaoPersonalizacao

# Produtos
from .produto import Produto
from .senha import Senha, SenhaAusente

# Usuários
from .usuario import Usuario

# Pedidos, estoque, receitas e compras: adicionar aqui conforme forem criados
