"""
app / models / insumo.py

INSUMO: no DER atualizado a tabela se chama INGREDIENTE, o código usa 'insumo' como o banco de dados

'Insumo' é qualquer item que a confeitaria guarda em estoque, o campo 'tipo' diz qual é
    ingredientes
    embalagens
    decoração
Todos têm saldo/estoque mínimo e movimentações

Unidades:
    unidade_medida
    unidade_receita
    fator_conversao

O saldo não fica negativo, se faltar insumo a operação é recusada com EstoqueInsuficienteError
"""

from __future__ import annotations
 
from datetime import datetime
# ROUND_UP = arredonda sempre "para longe do zero" (0,0004 vira 0,001); ROUND_HALF_UP = arredondamento padrão
from decimal import ROUND_HALF_UP, ROUND_UP, Decimal
 
from app.exceptions import EstoqueInsuficienteError, ValidacaoError
from app.validators.campos import Validador, garantir
 
from .base import Entidade
from .enums import TipoInsumo, TipoMovimentacao
from .movimentacao_estoque import MovimentacaoEstoque


class Insumo(Entidade):
    """
    DER: ID, nome (único), unidade_medida, quantidade_atual numeric(10,3) default 0,
    estoque_minimo numeric(10,3) default 0, custo_por_unidade numeric(10,4) (nulo), data_atualizacao,
    unidade_receita varchar(20), fator_conversao numeric(10,3) default 1, tipo default 'ingrediente', ativo
    """
 
    _MILESIMOS = Decimal("0.001")
    _DECIMILESIMOS = Decimal("0.0001")
 
    def __init__(
            self, 
            nome: str, 
            unidade_medida: str, 
            unidade_receita: str, 
            fator_conversao=1,
            quantidade_atual=0, 
            estoque_minimo=0, 
            custo_por_unidade=None,
            tipo: TipoInsumo = TipoInsumo.INGREDIENTE, 
            ativo: bool = True,
            data_atualizacao: datetime | None = None, 
            id_insumo: int | None = None
    ):
        """Valida e normaliza os campos. Só os três primeiros são obrigatórios; o resto tem o default do DER"""
        super().__init__(id_insumo)
        self._nome = Validador.texto(nome, "nome do insumo")
        self._unidade_medida = Validador.texto(unidade_medida, "unidade de medida")
        self._unidade_receita = Validador.texto(unidade_receita, "unidade da receita", max_len=20)
        self._fator_conversao = Validador.quantidadePositiva(fator_conversao, "fator de conversão")
        self._quantidade_atual = Validador.quantidade(quantidade_atual, "quantidade atual")
        self._estoque_minimo = Validador.quantidade(estoque_minimo, "estoque mínimo")
        # custo é anulável: None = "ainda não informado"; 0 é um custo válido (R$ 0,00).
        self._custo_por_unidade = Validador.opcionalSeInformado(Validador.custoUnitario, custo_por_unidade, "custo por unidade")
        # Aceita TipoInsumo.EMBALAGEM ou o texto "embalagem" (vindo do banco); qualquer outro valor é erro
        self._tipo = Validador.opcaoDe(TipoInsumo, tipo, "tipo")
        self._ativo = bool(ativo)
        self._data_atualizacao = data_atualizacao or datetime.now()
 
    # Leitura dos campos
    @property
    def nome(self) -> str: 
        return self._nome
    @property
    def unidade_medida(self) -> str: 
        return self._unidade_medida
    @property
    def unidade_receita(self) -> str: 
        return self._unidade_receita
    @property
    def fator_conversao(self) -> Decimal: 
        return self._fator_conversao
    @property
    def quantidade_atual(self) -> Decimal: 
        return self._quantidade_atual
    @property
    def estoque_minimo(self) -> Decimal: 
        return self._estoque_minimo
    @property
    def custo_por_unidade(self) -> Decimal | None: 
        return self._custo_por_unidade
    @property
    def tipo(self) -> TipoInsumo: 
        return self._tipo
    @property
    def ativo(self) -> bool: 
        return self._ativo
    @property
    def data_atualizacao(self) -> datetime: 
        return self._data_atualizacao
 
    # Conversão de unidades
    def paraUnidadeEstoque(self, quantidade_receita) -> Decimal:
        """
        Converte uma quantidade escrita na unidade da receita para a unidade do estoque
 
        Exemplo: farinha (kg/g, fator 1000): 300 g -> 0,300 kg 
        Arredonda PARA CIMA em 3 casas (limite do DER): assim o sistema nunca desconta MENOS do que foi usado
        """
        quantidade = Validador.quantidade(quantidade_receita, "quantidade na unidade da receita")
        return (quantidade / self._fator_conversao).quantize(self._MILESIMOS, rounding=ROUND_UP)
 
    def paraUnidadeReceita(self, quantidade_estoque) -> Decimal:
        """
        Converte uma quantidade do estoque para a unidade da receita

        Exemplo: 1,5 kg de farinha -> 1500 g
        """
        quantidade = Validador.quantidade(quantidade_estoque, "quantidade na unidade de estoque")
        return (quantidade * self._fator_conversao).quantize(self._MILESIMOS, rounding=ROUND_HALF_UP)
 
    # Alerta de estoque mínimo
    @property
    def abaixo_do_minimo(self) -> bool:
        """
        True quando o saldo atingiu ou passou do limite mínimo
        """
        return self._quantidade_atual <= self._estoque_minimo
 
    @property
    def falta_para_minimo(self) -> Decimal:
        """
        Quanto falta para voltar ao mínimo (0 se já está acima)
        
        Base da sugestão de compra
 
        max(a, b) devolve o maior dos dois: nunca devolve negativo
        """
        return max(self._estoque_minimo - self._quantidade_atual, Decimal("0"))
 
    # Custo
    def custoDe(self, quantidade_receita) -> Decimal:
        """
        Custo de uma quantidade escrita na unidade da receita
        
        Exemplo: R$ 8,00/kg e 300 g -> R$ 2,40
        """
        garantir(
            self._custo_por_unidade is not None,
            ValidacaoError(f"O insumo {self._nome!r} não tem custo por unidade cadastrado")
        )
        quantidade = Validador.quantidade(quantidade_receita, "quantidade na unidade da receita")
        custo = quantidade / self._fator_conversao * self._custo_por_unidade
        return custo.quantize(self._DECIMILESIMOS, rounding=ROUND_HALF_UP)
 
    # Alterações cadastrais
    def alterarEstoqueMinimo(self, valor) -> None:
        """
        Altera o limite mínimo (na unidade de estoque)
        """
        self._estoque_minimo = Validador.quantidade(valor, "estoque mínimo")
 
    def alterarCustoPorUnidade(self, valor) -> None:
        """
        Altera o custo por unidade de medida (None apaga o custo)
        """
        self._custo_por_unidade = Validador.opcionalSeInformado(Validador.custoUnitario, valor, "custo por unidade")
 
    def alternarAtivo(self) -> None:
        """Ativa/desativa o insumo. Inativo não aparece no resumo nem nos alertas (fica guardado no histórico)."""
        self._ativo = not self._ativo
 
    # Movimentações (todas mudam o saldo E devolvem o registro da movimentação)
    def _movimentar(
            self, 
            tipo: TipoMovimentacao, 
            quantidade, 
            motivo: str,
            id_pedido: int | None, 
            id_compra: int | None
    ) -> MovimentacaoEstoque:
        
        """
        Núcleo de todas as operações
        Ordem importa: 1) cria e valida a movimentação, 2) confere que o saldo não ficaria negativo, 3) só então altera o saldo
        Se algo falhar nos passos 1 ou 2, nada muda
        """
        movimentacao = MovimentacaoEstoque(
            self,
            tipo, 
            quantidade, 
            motivo=motivo, 
            id_pedido=id_pedido, 
            id_compra=id_compra
        )
        novo_saldo = self._quantidade_atual + movimentacao.variacao
        # `novo_saldo` troca o sinal: se o saldo ficaria em -0,5, faltam 0,5.
        garantir(
            novo_saldo >= 0,
            EstoqueInsuficienteError([
                {"insumo": self._nome, "unidade": self._unidade_medida, "faltam": -novo_saldo}
            ]),
        )
        self._quantidade_atual = novo_saldo
        self._data_atualizacao = movimentacao.data
        return movimentacao
 
    def registrarEntrada(self, quantidade, motivo: str = "", id_compra: int | None = None) -> MovimentacaoEstoque:
        """
        Soma ao saldo (exemplo: compra recebida)
        `quantidade` na unidade de estoque
        """
        return self._movimentar(TipoMovimentacao.ENTRADA, quantidade, motivo, None, id_compra)
 
    def registrarConsumo(self, quantidade, id_pedido: int | None = None, motivo: str = "") -> MovimentacaoEstoque:
        """
        Subtrai do saldo (produção de um pedido)
        Levanta EstoqueInsuficienteError se não houver saldo
        """
        return self._movimentar(TipoMovimentacao.CONSUMO, quantidade, motivo, id_pedido, None)
 
    def registrarPerda(self, quantidade, motivo: str) -> MovimentacaoEstoque:
        """
        Subtrai do saldo por desperdício.
        Exige motivo
        """
        return self._movimentar(TipoMovimentacao.PERDA, quantidade, motivo, None, None)
 
    def ajustar(self, variacao, motivo: str) -> MovimentacaoEstoque:
        """
        Correção manual por DIFERENÇA: +2 acrescenta 2, -2 retira 2
        Exige motivo
        """
        return self._movimentar(TipoMovimentacao.AJUSTE, variacao, motivo, None, None)
 
    def ajustarPara(self, nova_quantidade, motivo: str) -> MovimentacaoEstoque:
        """
        Correção manual por VALOR FINAL ("contei e tenho 8 kg"): calcula a diferença e registra um ajuste
        """
        nova = Validador.quantidade(nova_quantidade, "nova quantidade")
        garantir(
            nova != self._quantidade_atual,
            ValidacaoError("A nova quantidade é igual à quantidade atual")
        )
        return self.ajustar(nova - self._quantidade_atual, motivo)
 
    def __repr__(self) -> str:
        """
        Texto exibido ao imprimir o objeto
        """
        return f"<Insumo id={self.id} {self._nome!r} {self._quantidade_atual} {self._unidade_medida}>"
 