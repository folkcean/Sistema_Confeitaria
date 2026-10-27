"""
app / models / estoque.py

ESTOQUE não é uma entidade: não existe tabela ESTOQUE no DER

O saldo de cada item mora em Ingrediente e o histórico em MovimentacaoEstoque
Esta classe cuida do que envolve múltiplos ingredientes ao mesmo tempo, o que nenhum ingrediente
sozinho consegue fazer:
    - conferir e descontar todos os ingredientes de um pedido de uma vez (RF: baixa na confirmação)
    - dar entrada em vários itens de uma compra
    - listar o que atingiu o mínimo e montar a sugestão de compra (RF: alerta com lista)
    - resumo para consulta (funcionário e administrador) e ajuste manual com possibilidade de desfazer

Ela não acessa o banco
Não herda de Entidade e não tem `id`
"""
from __future__ import annotations
 
# defaultdict = dicionário que cria o valor inicial sozinho quando a chave ainda não existe.
from collections import defaultdict
# Iterable = "qualquer coisa que dá para percorrer com for" (lista, tupla, gerador...). Só dica de tipo.
from collections.abc import Iterable
from decimal import Decimal
 
from app.exceptions import EstoqueInsuficienteError, ValidacaoError
from app.validators.campos import Validador, garantir
 
from .enums import TipoInsumo, TipoMovimentacao
from .insumo import Insumo
from .movimentacao_estoque import MovimentacaoEstoque


class Estoque:
    """
    Conjunto de insumos e as operações que envolvem mais de um deles
 
    FORMATO DAS NECESSIDADES: uma lista de pares (insumo, quantidade na UNIDADE DA RECEITA), como
    [(farinha, 300), (leite_condensado, 395)] 
    É o formato que as receitas vão produzir quando forem implementadas
    """
 
    def __init__(self, insumos: Iterable[Insumo] = ()):
        """
        Começa com os insumos informados (ou vazio). Dicionário: nome do insumo -> objeto
        O nome serve de chave porque é UNIQUE no DER
        """
        self._insumos: dict[str, Insumo] = {}
        for insumo in insumos:
            self.adicionar(insumo)
 
    # Cadastro dos insumos
    def adicionar(self, insumo: Insumo) -> None:
        """
        Inclui o insumo no estoque. Dois insumos não podem ter o mesmo nome
        """
        garantir(
            insumo.nome not in self._insumos,
            ValidacaoError(f"Já existe um insumo chamado {insumo.nome!r} no estoque")
        )
        self._insumos[insumo.nome] = insumo
 
    @property
    def insumos(self) -> tuple[Insumo, ...]:
        """
        Cópia imutável de todos os insumos (ativos e inativos)
        """
        return tuple(self._insumos.values())
 
    def _exigirPertencente(self, insumo: Insumo) -> None:
        """
        Garante que o insumo informado é mesmo um dos que estão neste estoque (e não um desconhecido)
 
        `.get(nome)` devolve o objeto guardado ou None; `is` confere que é exatamente o mesmo objeto
        """
        garantir(
            self._insumos.get(insumo.nome) is insumo,
            ValidacaoError(f"O insumo {insumo.nome!r} não faz parte deste estoque"),
        )
 
    def _ativosOrdenados(self) -> list[Insumo]:
        """
        Só os insumos ativos, agrupados por tipo e, dentro de cada tipo, em ordem alfabética
 
        filter(função, itens) mantém só os itens para os quais a função devolve verdadeiro.
        sorted(itens, key=função) ordena pelo valor que a função devolve; devolver uma TUPLA (tipo, nome)
        ordena primeiro pelo tipo e, em caso de empate, pelo nome.
        """
        ativos = filter(lambda insumo: insumo.ativo, self._insumos.values())
        return sorted(ativos, key=lambda insumo: (insumo.tipo.value, insumo.nome.lower()))
 
    # Consulta, filtro por tipo e alertas
    def porTipo(self, tipo: TipoInsumo) -> list[Insumo]:
        """
        Só os insumos ativos de um tipo
        Exemplo: estoque.porTipo(TipoInsumo.EMBALAGEM) -> as embalagens
        Aceita TipoInsumo.EMBALAGEM ou o texto "embalagem"; um tipo inexistente levanta ValidacaoError
        """
        tipo = Validador.opcaoDe(TipoInsumo, tipo, "tipo")
        return list(filter(lambda insumo: insumo.tipo is tipo, self._ativosOrdenados()))
 
    def resumo(self) -> list[dict]:
        """
        Situação de cada insumo ativo (para a tela de estoque de funcionário e administrador)
        """
        return [
            {
                "nome": insumo.nome,
                "tipo": insumo.tipo.value,
                "unidade": insumo.unidade_medida,
                "quantidade_atual": insumo.quantidade_atual,
                "estoque_minimo": insumo.estoque_minimo,
                "abaixo_do_minimo": insumo.abaixo_do_minimo,
            }
            for insumo in self._ativosOrdenados()
        ]
 
    def insumosAbaixoDoMinimo(self) -> list[Insumo]:
        """
        Insumos ativos que atingiram (ou passaram do) estoque mínimo
        """
        return list(filter(lambda insumo: insumo.abaixo_do_minimo, self._ativosOrdenados()))
 
    def sugerirCompras(self) -> list[dict]:
        """
        Lista de compras sugerida: um item para cada insumo no mínimo, com quanto falta para voltar ao mínimo
 
        Vem agrupada por tipo (decoração, embalagem, ingrediente). Quanto comprar além disso (margem, fornecedor
        mais barato, previsão de demanda) fica para o módulo de recomendação (prox semanas)
        """
        return [
            {
                "insumo": insumo.nome,
                "tipo": insumo.tipo.value,
                "unidade": insumo.unidade_medida,
                "quantidade_atual": insumo.quantidade_atual,
                "estoque_minimo": insumo.estoque_minimo,
                "falta_para_minimo": insumo.falta_para_minimo,
            }
            for insumo in self.insumosAbaixoDoMinimo()
        ]
 
    # Consumo por pedidos
    def _totaisPorInsumo(self, necessidades: Iterable[tuple[Insumo, Decimal]]) -> dict[str, Decimal]:
        """
        Converte cada necessidade para a unidade de ESTOQUE e SOMA por insumo
 
        Somar antes de conferir é essencial: se o mesmo insumo aparece duas vezes, a conferência precisa
        considerar o total, e não cada pedaço separado (senão 2 consumos "cabem" e juntos estouram)
        """
        # defaultdict(Decimal): ao somar numa chave nova, começa de Decimal() = 0, sem precisar de if.
        totais: dict[str, Decimal] = defaultdict(Decimal)
        # `for insumo, quantidade in ...` desempacota cada par da lista em duas variáveis.
        for insumo, quantidade_receita in necessidades:
            self._exigirPertencente(insumo)
            totais[insumo.nome] += insumo.paraUnidadeEstoque(quantidade_receita)
        return totais
 
    def _faltas(self, totais: dict[str, Decimal]) -> list[dict]:
        """
        Do que foi pedido (totais), devolve só o que NÃO há em estoque, com quanto falta
        """
        linhas = [
            {
                "insumo": nome,
                "unidade": self._insumos[nome].unidade_medida,
                "faltam": total - self._insumos[nome].quantidade_atual,
            }
            for nome, total in totais.items()
        ]
        # Fica só quem tem falta positiva (total pedido maior que o saldo).
        return list(filter(lambda linha: linha["faltam"] > 0, linhas))
 
    def verificarDisponibilidade(self, necessidades: Iterable[tuple[Insumo, Decimal]]) -> list[dict]:
        """
        Diz o que faltaria para atender às necessidades, SEM alterar o estoque. Lista vazia = tudo disponível
 
        Útil para avisar o cliente/dona antes de confirmar um pedido
        """
        return self._faltas(self._totaisPorInsumo(necessidades))
 
    def consumir(self, necessidades: Iterable[tuple[Insumo, Decimal]],
                 id_pedido: int | None = None) -> list[MovimentacaoEstoque]:
        """ 
        Desconta TODOS os insumos das necessidades, ou NÃO desconta NADA (tudo ou nada)
 
        LÓGICA: 
        1) soma por insumo
        2) confere se há saldo para todos; se faltar algum, levanta EstoqueInsuficienteError com a lista do que falta (a sugestão de compra) e nada é alterado
        3) só então registra um consumo por insumo (que não pode mais falhar por falta de saldo)
        Chamado quando o pedido passa para "Confirmado" (regra de negócio de baixa de estoque)
        """
        totais = self._totaisPorInsumo(necessidades)
        faltas = self._faltas(totais)
        garantir(not faltas, EstoqueInsuficienteError(faltas))
        return [
            self._insumos[nome].registrarConsumo(total, id_pedido=id_pedido)
            for nome, total in totais.items()
        ]
 
    # Entradas, perdas, ajustes 
    def receber(self, itens: Iterable[tuple[Insumo, Decimal]], id_compra: int | None = None) -> list[MovimentacaoEstoque]:
        """
        Dá entrada em vários insumos (ex.: itens de uma compra recebida, quando o módulo de compras existir)
 
        Cada item é (insumo, quantidade na UNIDADE DE ESTOQUE, a mesma em que se compra: kg, lata...)
        Valida TODOS antes de aplicar, para não ficar uma entrada pela metade
        """
        # list(itens) guarda os pares numa lista, porque percorreremos duas vezes (um gerador só vale uma vez)
        itens = list(itens)
        for insumo, quantidade in itens:
            self._exigirPertencente(insumo)
            Validador.quantidadePositiva(quantidade, "quantidade recebida")
        return [insumo.registrarEntrada(quantidade, id_compra=id_compra) for insumo, quantidade in itens]
 
    def registrarPerda(self, insumo: Insumo, quantidade, motivo: str) -> MovimentacaoEstoque:
        """
        Registra desperdício de um insumo (exige motivo)
        """
        self._exigirPertencente(insumo)
        return insumo.registrarPerda(quantidade, motivo)
 
    def ajustarManual(self, insumo: Insumo, nova_quantidade, motivo: str) -> MovimentacaoEstoque:
        """
        Ajuste manual pelo valor final ("contei e tenho X")
        Quem pode fazer: só o administrador
        """
        self._exigirPertencente(insumo)
        return insumo.ajustarPara(nova_quantidade, motivo)
 
    def desfazerAjuste(self, movimentacao: MovimentacaoEstoque) -> MovimentacaoEstoque:
        """
        Desfaz um ajuste manual (requisito: permitir desfazer alterações manuais de estoque)
 
        Não apaga nada: registra um NOVO ajuste de sinal contrário, e o histórico fica completo.
        `-movimentacao.quantidade` troca o sinal (+2 vira -2).
        """
        garantir(
            movimentacao.tipo is TipoMovimentacao.AJUSTE,
            ValidacaoError("Somente ajustes manuais podem ser desfeitos"),
        )
        self._exigirPertencente(movimentacao.insumo)
        # {movimentacao.data:%d/%m/%Y %H:%M} formata a data como 20/10/2026 14:30 dentro da f-string.
        return movimentacao.insumo.ajustar(
            -movimentacao.quantidade,
            f"Desfaz o ajuste de {movimentacao.data:%d/%m/%Y %H:%M}",
        )
 
    def __repr__(self) -> str:
        """
        Texto exibido ao imprimir o objeto 
        """
        return f"<Estoque com {len(self._insumos)} insumos>"
 