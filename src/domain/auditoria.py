from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RegistroAuditoria:
    """Registro de solo anexado (ADR-005): nunca se actualiza ni se borra."""

    pedido_id: str
    accion: str
    usuario: str
    rol: str
    detalle: str
    fecha: datetime
