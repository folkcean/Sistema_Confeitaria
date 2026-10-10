"""
models / produto.py
Catálogo de produtos da confeitaria

DER: Produto (tabela PRODUTO)  1:N  OpcaoPersonalizacao (tabela OPCAO_PERSONALIZACAO)
"""
from __future__ import annotations

from decimal import Decimal

from .base import (
    Entidade, ValidacaoError, exigirTexto, textoOpcional,
    validarDinheiro, validarPercentual
)

class OpcaoPersonalizacao(Entidade):
    """
    Variação/adicional que o cliente pode escolher num produto
    DER: ID_opcao (PK), PRODUTOID_produto (FK), nome, descricao (nulo), custo_adicional numeric(10,2), ativo bool
    """

    def __init__(self, nome: str, custo_adicional=0, descricao: str = "",
                 ativo: bool = True, id_opcao: int | None = None):
        super().__init__(id_opcao)
        self._nome = exigirTexto(nome, "nome da opção")
        self._descricao = textoOpcional(descricao, "descrição da opção")
        self._custo_adicional = validarDinheiro(custo_adicional, "custo adicional")
        self._ativo = bool(ativo)
        self._produto: "Produto | None" = None

    @property
    def nome(self) -> str: return self._nome
    @property
    def descricao(self) -> str | None: return self._descricao
    @property
    def custo_adicional(self) -> Decimal: return self._custo_adicional
    @property
    def ativo(self) -> bool: return self._ativo

    @property
    def produto_id(self) -> int | None:
        """Valor da FK PRODUTOID_produto"""
        return self._produto.id if self._produto else None

    def _vincular(self, produto: "Produto | None") -> None:
        """Uso interno: chamado por Produto.adicionar/removerOpcao"""
        self._produto = produto

    def alterar_custo(self, novo_custo) -> None:
        self._custo_adicional = validarDinheiro(novo_custo, "custo adicional")

    def alternar_ativo(self) -> None:
        self._ativo = not self._ativo

    def __repr__(self) -> str:
        return f"<OpcaoPersonalizacao id={self.id} {self._nome!r} +R$ {self._custo_adicional}>"

class Produto(Entidade):
    """
    Item do catálogo
    DER: ID_produto, nome, descricao, disponibilidade (varchar), preco_base, custo_mao_de_obra, margem_lucro, 
    tamanho (nulo), caminho_foto (nulo), ativo (bool), antecedencia_horas, custo_embalagem, custo_indireto, percentual_perda
    """

    def __init__(self, nome: str, preco_base, descricao: str = "", disponibilidade: str = "Sob encomenda", ativo: bool = True, custo_mao_de_obra=0, margem_lucro=0,          
        custo_embalagem=0, custo_indireto=0, percentual_perda=0, antecedencia_horas: int = 0, tamanho: str = "", caminho_foto: str = "", id_produto: int | None = None):
       
        super().__init__(id_produto)
        self._nome = exigirTexto(nome, "nome do produto")
        # DER: descricao é NOT NULL (pode ser texto vazio, mas nunca None)
        self._descricao = exigirTexto(descricao, "descrição") if descricao and descricao.strip() else ""
        self._disponibilidade = exigirTexto(disponibilidade, "disponibilidade")
        self._ativo = bool(ativo)
        self._preco_base = validarDinheiro(preco_base, "preço base")
        self._custo_mao_de_obra = validarDinheiro(custo_mao_de_obra, "custo de mão de obra")
        self._margem_lucro = validarDinheiro(margem_lucro, "margem de lucro")
        self._custo_embalagem = validarDinheiro(custo_embalagem, "custo de embalagem")
        self._custo_indireto = validarDinheiro(custo_indireto, "custo indireto")
        self._percentual_perda = validarPercentual(percentual_perda, "percentual de perda")

        self._antecedencia_horas = self._validar_horas(antecedencia_horas)
        self._tamanho = textoOpcional(tamanho, "tamanho")            
        self._caminho_foto = textoOpcional(caminho_foto, "caminho da foto")

        self._opcoes: list[OpcaoPersonalizacao] = []

    @staticmethod
    def _validarHoras(horas) -> int:
        """DER: antecedencia_horas int4 -> inteiro >= 0 (horas mínimas para encomendar)"""
        if isinstance(horas, bool):
            raise ValidacaoError("A antecedência deve ser um número inteiro (em horas)")

        if not isinstance(horas, int):
            raise ValidacaoError("A antecedência deve ser um número inteiro (em horas)")

        if horas<0:
            raise ValidacaoError("A antecedência não pode ser negativa")

        return horas

    @property
    def nome(self) -> str: return self._nome
    @property
    def descricao(self) -> str: return self._descricao
    @property
    def disponibilidade(self) -> str: return self._disponibilidade
    @property
    def ativo(self) -> bool: return self._ativo
    @property
    def preco_base(self) -> Decimal: return self._preco_base
    @property
    def custo_mao_de_obra(self) -> Decimal: return self._custo_mao_de_obra
    @property
    def margem_lucro(self) -> Decimal: return self._margem_lucro
    @property
    def custo_embalagem(self) -> Decimal: return self._custo_embalagem
    @property
    def custo_indireto(self) -> Decimal: return self._custo_indireto
    @property
    def percentual_perda(self) -> Decimal: return self._percentual_perda
    @property
    def antecedencia_horas(self) -> int: return self._antecedencia_horas
    @property
    def tamanho(self) -> str | None: return self._tamanho
    @property
    def caminho_foto(self) -> str | None: return self._caminho_foto
    @property
    def preco(self) -> Decimal: return self._preco_base
    @property
    def disponivel(self) -> bool: return self._ativo

    @property
    def opcoes(self) -> tuple[OpcaoPersonalizacao, ...]:
        return tuple(self._opcoes)   # cópia imutável: a lista interna fica protegida

    # Alterações
    def alterarPreco(self, novo_preco) -> None:
        """Atualiza o preço base (ação da administração)."""
        self._preco_base = validarDinheiro(novo_preco, "novo preço")

    def alterarNome(self, v: str) -> None: self._nome = exigirTexto(v, "nome do produto")
    def alterarDescricao(self, v: str) -> None: self._descricao = (v or "").strip()
    def alterarDisponibilidade(self, v: str) -> None:
        self._disponibilidade = exigirTexto(v, "disponibilidade")
    def alterarTamanho(self, v: str) -> None: self._tamanho = textoOpcional(v, "tamanho")
    def alterarFoto(self, v: str) -> None: self._caminho_foto = textoOpcional(v, "caminho da foto")
    def alterarAntecedencia(self, horas) -> None: self._antecedencia_horas = self._validar_horas(horas)

    def alterarCustos(self, *, mao_de_obra=None, embalagem=None, indireto=None,
                       margem_lucro=None, percentual_perda=None) -> None:
        """Atualiza só os campos informados (os demais ficam como estão)."""
        if mao_de_obra is not None:
            self._custo_mao_de_obra = validarDinheiro(mao_de_obra, "custo de mão de obra")
        if embalagem is not None:
            self._custo_embalagem = validarDinheiro(embalagem, "custo de embalagem")
        if indireto is not None:
            self._custo_indireto = validarDinheiro(indireto, "custo indireto")
        if margem_lucro is not None:
            self._margem_lucro = validarDinheiro(margem_lucro, "margem de lucro")
        if percentual_perda is not None:
            self._percentual_perda = validarPercentual(percentual_perda, "percentual de perda")

    def alternar_disponibilidade(self) -> None:
        """Ativa/desativa o produto no catálogo (DER: coluna `ativo`)"""
        self._ativo = not self._ativo

    # Personalização
    def adicionar_opcao(self, opcao: OpcaoPersonalizacao) -> None:
        if opcao in self._opcoes:
            raise ValidacaoError("Esta opção já pertence a este produto")

        if opcao._produto is not None:
            raise ValidacaoError("Esta opção já pertence a outro produto")

        opcao._vincular(self)
        self._opcoes.append(opcao)

    def remover_opcao(self, opcao: OpcaoPersonalizacao) -> None:
        if opcao not in self._opcoes:
            raise ValidacaoError("Esta opção não pertence a este produto")
        self._opcoes.remove(opcao)
        opcao._vincular(None)

    #Calculos
    def calcular_preco(self, opcoes_escolhidas=()) -> Decimal:
        """Preço final = preco_base + custo_adicional de cada opção escolhida
        Valida que a opção é deste produto e está ativa"""
        total = self._preco_base
        for op in opcoes_escolhidas:
            if op not in self._opcoes:
                raise ValidacaoError(f"A opção {op.nome!r} não pertence a este produto.")
            if not op.ativo:
                raise ValidacaoError(f"A opção {op.nome!r} está indisponível.")
            total += op.custo_adicional
        return total

    def custo_total(self, custo_ingredientes=0) -> Decimal:
        """
        Custo de produção
        """
        ingredientes = validarDinheiro(custo_ingredientes, "custo dos ingredientes")
        ingredientes *= (1 + self._percentual_perda / 100)
        return (ingredientes + self._custo_mao_de_obra
                + self._custo_embalagem + self._custo_indireto).quantize(Decimal("0.01"))

    def preco_sugerido(self, custo_ingredientes=0) -> Decimal:
        """Custo total + margem de lucro (tratando margem_lucro como valor em R$ (DER))"""
        return self.custo_total(custo_ingredientes) + self._margem_lucro

    def __repr__(self) -> str:
        status = "Ativo" if self._ativo else "Inativo"
        return f"<Produto id={self.id} nome={self._nome!r} R$ {self._preco_base} ({status})>"