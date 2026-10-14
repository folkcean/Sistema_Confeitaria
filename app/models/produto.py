"""
app / models / produto.py

Catálogo de produtos da confeitaria (tabela PRODUTO)
Suas opções ficam em opcao_personalizacao.py.
"""
from __future__ import annotations
 
from decimal import Decimal
 
from app.exceptions import ValidacaoError
from app.validators.campos import Validador, garantir
 
from .base import Entidade
from .opcao_personalizacao import OpcaoPersonalizacao


class Produto(Entidade):
    """
    Item do catálogo
    DER: ID_produto, nome, descricao (NOT NULL), disponibilidade, preco_base, custo_mao_de_obra, margem_lucro,
    tamanho (nulo), caminho_foto (nulo), ativo, antecedencia_horas (default 48), custo_embalagem,
    custo_indireto, percentual_perda
    """

    def __init__(self, nome: str, preco_base, descricao: str = "", disponibilidade: str = "Sob encomenda",
                 ativo: bool = True, custo_mao_de_obra=0, margem_lucro=0, custo_embalagem=0, custo_indireto=0,
                 percentual_perda=0, antecedencia_horas: int = 48, tamanho: str = "", caminho_foto: str = "",
                 id_produto: int | None = None):
        
        super().__init__(id_produto)
        self._nome = Validador.texto(nome, "nome do produto")
        # DER: descricao é NOT NULL, então vazio vira "" (nunca None)
        # textoOpcional devolve None quando vazio; `or ""` troca esse None por texto vazio
        self._descricao = Validador.textoOpcional(descricao, "descrição") or ""
        self._disponibilidade = Validador.texto(disponibilidade, "disponibilidade")
        self._ativo = bool(ativo)
        # Todos os valores em R$ passam por Validador.dinheiro (Decimal, >= 0, 2 casas)
        self._preco_base = Validador.dinheiro(preco_base, "preço base")
        self._custo_mao_de_obra = Validador.dinheiro(custo_mao_de_obra, "custo de mão de obra")
        self._margem_lucro = Validador.dinheiro(margem_lucro, "margem de lucro")
        self._custo_embalagem = Validador.dinheiro(custo_embalagem, "custo de embalagem")
        self._custo_indireto = Validador.dinheiro(custo_indireto, "custo indireto")
        self._percentual_perda = Validador.percentual(percentual_perda, "percentual de perda")
        self._antecedencia_horas = Validador.inteiroNaoNegativo(antecedencia_horas, "antecedência (horas)")
        self._tamanho = Validador.textoOpcional(tamanho, "tamanho")
        self._caminho_foto = Validador.textoOpcional(caminho_foto, "caminho da foto")
        # Lista das opções de personalização deste produto (relação 1:N). Começa vazia
        self._opcoes: list[OpcaoPersonalizacao] = []

    # Leitura simples dos campos
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
    def opcoes(self) -> tuple[OpcaoPersonalizacao, ...]:
        """
        Cópia imutável da lista: ninguém altera a lista interna por fora
        """
        return tuple(self._opcoes)

    # Alterações (cada uma revalida só o campo que muda)
    def alterarNome(self, valor: str) -> None:
        """Altera o nome"""
        self._nome = Validador.texto(valor, "nome do produto")

    def alterarDescricao(self, valor: str) -> None:
        """Altera a descrição; vazio vira '' porque a coluna é NOT NULL"""
        self._descricao = Validador.textoOpcional(valor, "descrição") or ""

    def alterarDisponibilidade(self, valor: str) -> None:
        """Altera o texto de disponibilidade (ex.: 'Sob encomenda', 'Pronta entrega')"""
        self._disponibilidade = Validador.texto(valor, "disponibilidade")

    def alterarTamanho(self, valor: str) -> None:
        """Altera o tamanho (vazio vira None)"""
        self._tamanho = Validador.textoOpcional(valor, "tamanho")

    def alterarFoto(self, valor: str) -> None:
        """Altera o caminho da foto (vazio vira None)"""
        self._caminho_foto = Validador.textoOpcional(valor, "caminho da foto")

    def alterarAntecedencia(self, horas: int) -> None:
        """Altera as horas mínimas de antecedência para encomendar (inteiro >= 0)"""
        self._antecedencia_horas = Validador.inteiroNaoNegativo(horas, "antecedência (horas)")

    def alterarPreco(self, novo_preco) -> None:
        """Altera o preço base (ação da administração)"""
        self._preco_base = Validador.dinheiro(novo_preco, "preço base")

    def alterarCustoMaoDeObra(self, valor) -> None:
        """Altera o custo de mão de obra"""
        self._custo_mao_de_obra = Validador.dinheiro(valor, "custo de mão de obra")

    def alterarCustoEmbalagem(self, valor) -> None:
        """Altera o custo de embalagem"""
        self._custo_embalagem = Validador.dinheiro(valor, "custo de embalagem")

    def alterarCustoIndireto(self, valor) -> None:
        """Altera o custo indireto (energia, gás, etc.)"""
        self._custo_indireto = Validador.dinheiro(valor, "custo indireto")

    def alterarMargemLucro(self, valor) -> None:
        """Altera a margem de lucro (valor em R$, conforme o DER numeric(10,2))"""
        self._margem_lucro = Validador.dinheiro(valor, "margem de lucro")

    def alterarPercentualPerda(self, valor) -> None:
        """Altera o percentual de perda dos ingredientes (0 a 100)"""
        self._percentual_perda = Validador.percentual(valor, "percentual de perda")

    def alternarAtivo(self) -> None:
        """Mostra/esconde o produto no catálogo (coluna `ativo`)"""
        self._ativo = not self._ativo

    # Personalização (1:N)
    def adicionarOpcao(self, opcao: OpcaoPersonalizacao) -> None:
        """
        Vincula a opção a este produto. Uma opção só pode ter UM produto (este ou outro)
        LÓGICA: confere que a opção ainda não tem dono; avisa a opção quem é o dono; guarda na lista
        """
        garantir(opcao.produto is None, ValidacaoError("Esta opção já pertence a um produto"))
        opcao._vincular(self)
        self._opcoes.append(opcao)

    def removerOpcao(self, opcao: OpcaoPersonalizacao) -> None:
        """Remove a opção deste produto e desfaz o vínculo"""
        garantir(opcao in self._opcoes, ValidacaoError("Esta opção não pertence a este produto"))
        self._opcoes.remove(opcao)
        opcao._vincular(None)

    # Cálculos
    def _exigirOpcaoEscolhivel(self, opcao: OpcaoPersonalizacao) -> None:
        """A opção precisa ser deste produto e estar ativa"""
        garantir(opcao in self._opcoes, ValidacaoError(f"A opção {opcao.nome!r} não pertence a este produto"))
        garantir(opcao.ativo, ValidacaoError(f"A opção {opcao.nome!r} está indisponível"))

    def calcularPreco(self, opcoes_escolhidas=()) -> Decimal:
        """Preço final = preço base + custo adicional de cada opção escolhida (valida cada opção antes de somar)"""
        total = self._preco_base
        for opcao in opcoes_escolhidas:
            self._exigirOpcaoEscolhivel(opcao)
            total += opcao.custo_adicional
        return total

    def custoTotal(self, custo_ingredientes=0) -> Decimal:
        """
        Custo de produção = ingredientes (já com a perda) + mão de obra + embalagem + custo indireto
        O percentual de perda incide apenas sobre os ingredientes
        """
        ingredientes = Validador.dinheiro(custo_ingredientes, "custo dos ingredientes")
        ingredientes_com_perda = ingredientes * (1 + self._percentual_perda / 100)
        soma = ingredientes_com_perda + self._custo_mao_de_obra + self._custo_embalagem + self._custo_indireto
        return soma.quantize(Decimal("0.01"))

    def precoSugerido(self, custo_ingredientes=0) -> Decimal:
        """Custo total + margem de lucro (margem tratada como valor em R$ (DER))"""
        return self.custoTotal(custo_ingredientes) + self._margem_lucro

    def __repr__(self) -> str:
        """Texto exibido ao imprimir o objeto"""
        status = {True: "Ativo", False: "Inativo"}[self._ativo]
        return f"<Produto id={self.id} nome={self._nome!r} R$ {self._preco_base} ({status})>"