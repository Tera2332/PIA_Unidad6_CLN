"""Domain Events. Se publican después del commit (consistencia eventual, ADR-002)."""
from dataclasses import dataclass
from datetime import datetime


class EventoDominio:
    @property
    def nombre(self):
        return type(self).__name__


@dataclass(frozen=True)
class PedidoRegistrado(EventoDominio):
    pedido_id: str
    actor_id: str
    total: str
    detalle: str
    usuario: str
    fecha: datetime


@dataclass(frozen=True)
class PedidoEnPreparacion(EventoDominio):
    pedido_id: str
    usuario: str
    fecha: datetime


@dataclass(frozen=True)
class PedidoListo(EventoDominio):
    pedido_id: str
    usuario: str
    fecha: datetime


@dataclass(frozen=True)
class PedidoEntregado(EventoDominio):
    pedido_id: str
    lineas: tuple
    usuario: str
    fecha: datetime


@dataclass(frozen=True)
class PedidoCancelado(EventoDominio):
    pedido_id: str
    motivo: str
    usuario: str
    rol: str
    fecha: datetime


@dataclass(frozen=True)
class StockCriticoAlcanzado(EventoDominio):
    platillo_id: str
    stock: int
    usuario: str
    fecha: datetime


@dataclass(frozen=True)
class InventarioAjustado(EventoDominio):
    platillo_id: str
    tipo: str
    cantidad: int
    motivo: str
    usuario: str
    fecha: datetime
