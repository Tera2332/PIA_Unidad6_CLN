"""Aggregate Root Pedido."""
from dataclasses import dataclass

from src.domain.base import RaizAgregado, ahora_utc
from src.domain.errores import DatosInvalidos
from src.domain.eventos import (
    PedidoCancelado,
    PedidoEnPreparacion,
    PedidoEntregado,
    PedidoListo,
    PedidoRegistrado,
)
from src.domain.maquina_estados import MaquinaEstados
from src.domain.valores import Dinero, EstadoPedido


@dataclass(frozen=True)
class LineaPedido:
    platillo_id: str
    cantidad: int
    precio_unitario: Dinero
    modificaciones: tuple = ()

    @property
    def subtotal(self):
        return self.precio_unitario.por(self.cantidad)


class Pedido(RaizAgregado):
    def __init__(self, id, actor_id, lineas, fecha_solicitud, promocion_activa=False,
                 autorizado=True, referencia=None, estado=EstadoPedido.REGISTRADO,
                 motivo_cancelacion=None):
        super().__init__()
        self.id = id
        self.actor_id = actor_id
        self.lineas = tuple(lineas)
        self.fecha_solicitud = fecha_solicitud
        self.promocion_activa = promocion_activa
        self.autorizado = autorizado
        self.referencia = referencia
        self.estado = estado
        self.motivo_cancelacion = motivo_cancelacion

    @classmethod
    def reconstruir(cls, *args, **kwargs):
        """Rehidrata un pedido existente (base de datos o CSV) sin validar ni emitir eventos."""
        return cls(*args, **kwargs)

    @classmethod
    def registrar(cls, id, actor_id, lineas, promocion_activa=False, autorizado=True,
                  referencia=None, usuario="sistema", ahora=None):
        lineas = tuple(lineas)
        if not lineas:
            raise DatosInvalidos("El pedido debe incluir al menos un producto.")
        for linea in lineas:
            cantidad = linea.cantidad
            if isinstance(cantidad, bool) or not isinstance(cantidad, int) or cantidad <= 0:
                raise DatosInvalidos(
                    f"La cantidad de «{linea.platillo_id}» debe ser un número entero mayor a cero."
                )
        ahora = ahora_utc(ahora)
        pedido = cls(id, actor_id, lineas, ahora.date(), promocion_activa, autorizado, referencia)
        detalle = "; ".join(
            f"{x.platillo_id} x{x.cantidad}"
            + (f" ({', '.join(x.modificaciones)})" if x.modificaciones else "")
            for x in lineas
        )
        pedido._registrar(
            PedidoRegistrado(id, actor_id, str(pedido.total), detalle, usuario, ahora)
        )
        return pedido

    @property
    def total(self):
        total = Dinero.cero()
        for linea in self.lineas:
            total = total + linea.subtotal
        return total

    def iniciar_preparacion(self, usuario="sistema", ahora=None):
        self.estado = MaquinaEstados.siguiente(self.estado, "iniciar_preparacion")
        self._registrar(PedidoEnPreparacion(self.id, usuario, ahora_utc(ahora)))

    def marcar_listo(self, usuario="sistema", ahora=None):
        self.estado = MaquinaEstados.siguiente(self.estado, "marcar_listo")
        self._registrar(PedidoListo(self.id, usuario, ahora_utc(ahora)))

    def entregar(self, usuario="sistema", ahora=None):
        self.estado = MaquinaEstados.siguiente(self.estado, "entregar")
        resumen = tuple((x.platillo_id, x.cantidad) for x in self.lineas)
        self._registrar(PedidoEntregado(self.id, resumen, usuario, ahora_utc(ahora)))

    def cancelar(self, motivo, usuario, rol, ahora=None):
        motivo = (motivo or "").strip()
        if not motivo:
            raise DatosInvalidos("Para cancelar un pedido debes indicar el motivo.")
        self.estado = MaquinaEstados.siguiente(self.estado, "cancelar")
        self.motivo_cancelacion = motivo
        self._registrar(PedidoCancelado(self.id, motivo, usuario, rol, ahora_utc(ahora)))
