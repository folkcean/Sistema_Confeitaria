"""
app / services / recomendador_ia.py

O conhecimento  fica em reposicao.md, fora do código
Aqui só se junta as instruções do .md + o retrato do banco em JSON + o formato da resposta (esquema)
"""
from __future__ import annotations

import json

from app.exceptions import GatewayIAError, ValidacaoError
from app.validators.campos import garantir

TAREFA_RECOMENDAR = "Gere as recomendações de reposição seguindo as regras."

# Formato da resposta (JSON Schema no modo strict: todo campo em required e additionalProperties false)
# "Vazio" é "" e não null, para o mesmo esquema servir em mais provedores
_RECOMENDACAO = {
    "type": "object",
    "properties": {
        "insumo": {"type": "string"},
        "prioridade": {"type": "string", "enum": ["alta", "media"]},
        "comprar": {"type": "number"},
        "unidade": {"type": "string"},
        "pedir_ate": {"type": "string"},
        "fornecedor": {"type": "string"},
        "motivo": {"type": "string"},
        "fatores": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["insumo", "prioridade", "comprar", "unidade", "pedir_ate", "fornecedor", "motivo", "fatores"],
    "additionalProperties": False,
}
ESQUEMA_RECOMENDACOES = {
    "type": "object",
    "properties": {
        "resumo": {"type": "string"},
        "recomendacoes": {"type": "array", "items": _RECOMENDACAO},
        "avisos": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["resumo", "recomendacoes", "avisos"],
    "additionalProperties": False,
}


class RecomendadorIA:
    """Implementa o contrato Recomendador usando um ModeloLinguagem"""

    def __init__(self, modelo, instrucoes: str):
        # modelo: GatewayIA no app, ModeloFalso nos testes (contrato ModeloLinguagem)
        self._modelo = modelo
        self._instrucoes = instrucoes

    # Operação do contrato Recomendador
    def recomendar(self, contexto: dict) -> dict:
        """Recomendações de reposição: {"resumo", "recomendacoes", "avisos"}"""
        texto = self._modelo.responder(self._instrucoes, self._mensagem(contexto, TAREFA_RECOMENDAR),
                                       ESQUEMA_RECOMENDACOES)
        try:
            dados = json.loads(texto)
        except ValueError as erro:
            raise GatewayIAError("A IA respondeu fora do formato combinado. Tente de novo.") from erro
        garantir(isinstance(dados.get("recomendacoes"), list),
                 GatewayIAError("A IA respondeu sem a lista de recomendações. Tente de novo."))
        return dados

    def perguntar(self, contexto: dict, pergunta: str) -> str:
        """Pergunta livre da dona sobre os dados, respondida em texto"""
        pergunta = (pergunta or "").strip()
        garantir(pergunta, ValidacaoError("Escreva a pergunta antes de enviar."))
        garantir(len(pergunta) <= 500, ValidacaoError("A pergunta pode ter até 500 caracteres."))
        return self._modelo.responder(self._instrucoes, self._mensagem(contexto, pergunta))

    @staticmethod
    def _mensagem(contexto: dict, tarefa: str) -> str:
        """Os dados em JSON (Decimal e date viram texto) e, depois, o pedido"""
        dados = json.dumps(contexto, default=str, ensure_ascii=False, separators=(",", ":"))
        return f"Dados do sistema:\n{dados}\n\n{tarefa}"
