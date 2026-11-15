"""
app / services / alerta_estoque.py

ALERTAS DE ESTOQUE (s5)

Dois serviços para a dona:
    1) ALERTA DE MÍNIMO: quais insumos chegaram ao estoque mínimo (com mensagem pronta para a tela)
    2) LISTA DE COMPRAS SUGERIDA: o que comprar e quanto falta para voltar ao mínimo

Reaproveita Estoque.insumosAbaixoDoMinimo e Estoque.sugerirCompras (s3): aqui só monta as mensagens e
descobre quais insumos entram no mínimo depois de uma baixa
"""
from __future__ import annotations

from collections.abc import Iterable

from app.models.estoque import Estoque
from app.models.insumo import Insumo
from app.models.movimentacao_estoque import MovimentacaoEstoque


class AlertaEstoque:
    """Gera alertas e lista de compras a partir de um Estoque"""

    def __init__(self, estoque: Estoque):
        self._estoque = estoque

    @staticmethod
    def mensagem(insumo: Insumo) -> str:
        """Texto do alerta de UM insumo. Ex.: 'Farinha: 2.000 kg em estoque (mínimo 3.000 kg)'"""
        return (f"{insumo.nome}: {insumo.quantidade_atual} {insumo.unidade_medida} em estoque "
                f"(mínimo {insumo.estoque_minimo} {insumo.unidade_medida})")

    def alertas(self) -> list[str]:
        """Mensagens de todos os insumos ativos que estão no mínimo ou abaixo dele"""
        return [self.mensagem(insumo) for insumo in self._estoque.insumosAbaixoDoMinimo()]

    def listaDeCompras(self) -> list[dict]:
        """Lista de compras sugerida (insumo, tipo, unidade, quantidade atual, mínimo e quanto falta)"""
        return self._estoque.sugerirCompras()

    def novosAlertas(self, movimentacoes: Iterable[MovimentacaoEstoque]) -> list[str]:
        """Mensagens só dos insumos alcançados pelas movimentações que estão no mínimo ou abaixo dele

        Útil logo depois de confirmar um pedido: avisa o que acabou de ficar baixo.
        O dicionário `por_nome` evita repetir o mesmo insumo caso ele tenha várias movimentações:
        a chave é o nome, então a segunda aparição só sobrescreve a primeira
        """
        por_nome = {movimentacao.insumo.nome: movimentacao.insumo for movimentacao in movimentacoes}
        baixos = filter(lambda insumo: insumo.abaixo_do_minimo, por_nome.values())
        return [self.mensagem(insumo) for insumo in baixos]