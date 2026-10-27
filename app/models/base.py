"""
app / models / base.py

Classe mãe de tudo que tem identidade no banco de dados
"""

from __future__ import annotations

from app.exceptions import ValidacaoError
from app.validators.campos import garantir


class Entidade:
    """
    Superclasse de todas as entidades com identidade persistível no banco de dados
    Garante que todo objeto tenha um id (pk do DER)
    """

    def __init__(self, id_entidade: int | None = None):
        """
        Construtor: roda quando o objeto é criado
        `id_entidade=None` é um valor padrão
        None = "ainda não foi gravado no banco". Quando o banco gerar a PK, o repositório chama atribuirID()
        """
        # Atributo protegido: subclasses podem ler, mas código externo deve usar property id
        self._id = id_entidade

    @property
    def id(self) -> int | None:
        """
        Leitura do identificador unico da identidade no bd
        """
        # @property: use como `produto.id` (sem parênteses)
        # Não existe setter aqui, o id só entra por atribuirId(), uma única vez
        return self._id

    def atribuirID(self, novo_id: int) -> None:
        """
        Usado logo após o INSERT, quando o banco gera a pk, depois de definido é imutável
        """
        garantir(
            self._id is None,
            ValidacaoError("Esta entidade já possui um ID (não alterável)"),
        )
        self._id = novo_id
