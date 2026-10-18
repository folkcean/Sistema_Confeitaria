"""
app/models/__init__.py
Índice do pacote: lista os modelos na ordem lógica do domínio (não na ordem alfabética dos arquivos).
Permite escrever `from app.models import Cliente` em vez do caminho completo.
"""
# Base
from .base import Entidade
from .enums import (FormaPagamento, Perfil, StatusCompra, StatusPagamento, StatusPedido, TipoEntrega,
                    TipoInsumo, TipoMovimentacao)
from .senha import Senha, SenhaAusente

# Usuários
from .usuario import Usuario
from .cliente import Cliente
from .endereco import Endereco
from .funcionario import Funcionario
from .administrador import Administrador

# Produtos
from .produto import Produto
from .opcao_personalizacao import OpcaoPersonalizacao

# Pedidos, estoque, receitas e compras: adicionar aqui conforme forem criados