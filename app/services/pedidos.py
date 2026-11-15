"""
app / services / pedidos.py

Valores de um pedido já prontos para as telas (loja/pedido.html e painel/pedido.html)
A conta é do model: aqui só se juntam os números num lugar, para as duas áreas mostrarem igual
"""


def valoresDoPedido(pedido) -> dict:
    """Subtotal, taxa, total, sinal, quanto já foi pago e quanto falta"""
    return {
        "subtotal": pedido.subtotal_itens,
        "taxa_entrega": pedido.taxa_entrega,
        "total": pedido.valor_total,
        "sinal": pedido.valor_sinal,
        "pago": pedido.valor_total - pedido.valor_em_aberto,
        "restante": pedido.valor_em_aberto,
    }
