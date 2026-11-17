"""
app / models / cobranca.py

Fica em models porque é como o resto do sistema enxerga a cobrança, sem saber qual gateway a criou
Quem traduz o JSON do gateway para Cobranca é o adaptador (app / services / gateway_abacatepay.py)

"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Cobranca:
    """
    Uma cobrança no gateway. 'frozen=True' deixa o objeto imutável, como todo objeto-valor

    status: o gateway do abacate pay retorna esses status: ('PENDING', 'PAID', 'EXPIRED', 'CANCELLED', ...)
    br_code: o "Pix copia e cola"
    br_code_base64: a imagem do QR Code (vai direto no <img src>)
    """
    id: str
    status: str
    br_code: str | None = None
    br_code_base64: str | None = None
    expira_em: datetime | None = None
    dev_mode: bool = False

    @property
    def paga(self) -> bool:
        """O Pix só conta como pago quando o gateway diz 'PAID'"""
        return self.status == "PAID"
