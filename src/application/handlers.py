"""Manejadores de eventos. Cada uno corre en su propia transacción (ADR-002 y ADR-005)."""
from src.domain.auditoria import RegistroAuditoria
from src.domain.errores import ErrorDeNegocio, NoEncontrado
from src.domain.eventos import (
    InventarioAjustado,
    PedidoCancelado,
    PedidoEnPreparacion,
    PedidoEntregado,
    PedidoListo,
    PedidoRegistrado,
    StockCriticoAlcanzado,
)


def _a_registro(evento):
    if isinstance(evento, PedidoRegistrado):
        return RegistroAuditoria(evento.pedido_id, "REGISTRAR_PEDIDO", evento.usuario, "",
                                 f"Total {evento.total} MXN. {evento.detalle}", evento.fecha)
    if isinstance(evento, PedidoEnPreparacion):
        return RegistroAuditoria(evento.pedido_id, "INICIAR_PREPARACION", evento.usuario, "",
                                 "El pedido pasó a «En preparación».", evento.fecha)
    if isinstance(evento, PedidoListo):
        return RegistroAuditoria(evento.pedido_id, "MARCAR_LISTO", evento.usuario, "",
                                 "El pedido pasó a «Listo».", evento.fecha)
    if isinstance(evento, PedidoEntregado):
        return RegistroAuditoria(evento.pedido_id, "ENTREGAR_PEDIDO", evento.usuario, "",
                                 "El pedido fue entregado.", evento.fecha)
    if isinstance(evento, PedidoCancelado):
        return RegistroAuditoria(evento.pedido_id, "CANCELAR_PEDIDO", evento.usuario, evento.rol,
                                 evento.motivo, evento.fecha)
    if isinstance(evento, StockCriticoAlcanzado):
        return RegistroAuditoria(None, "STOCK_CRITICO", evento.usuario, "",
                                 f"«{evento.platillo_id}» quedó con {evento.stock} unidades.",
                                 evento.fecha)
    if isinstance(evento, InventarioAjustado):
        return RegistroAuditoria(None, "AJUSTE_INVENTARIO", evento.usuario, "",
                                 f"{evento.tipo} de {evento.cantidad} en «{evento.platillo_id}». "
                                 f"{evento.motivo}".strip(), evento.fecha)
    return None


class RegistroDeAuditoria:
    """Escribe en la tabla de solo anexado cada acción trazable (NB-04, NB-05)."""

    def __init__(self, uow_factory):
        self._uow_factory = uow_factory

    def __call__(self, evento):
        registro = _a_registro(evento)
        if registro is None:
            return
        with self._uow_factory() as uow:
            uow.auditoria.agregar(registro)
            uow.commit()


class DescuentoDeInventario:
    """Al entregar un pedido descuenta existencias en otra transacción (NB-07)."""

    def __init__(self, uow_factory, despachador):
        self._uow_factory = uow_factory
        self._despachador = despachador

    def __call__(self, evento):
        platillos = []
        try:
            with self._uow_factory() as uow:
                for platillo_id, cantidad in evento.lineas:
                    platillo = uow.platillos.obtener(platillo_id)
                    if platillo is None:
                        raise NoEncontrado(f"El platillo «{platillo_id}» no existe.")
                    platillo.descontar(cantidad, evento.usuario, evento.fecha)
                    uow.platillos.guardar(platillo)
                    platillos.append(platillo)
                uow.commit()
        except ErrorDeNegocio as error:
            # Compensación: no se pierde el pedido entregado; se avisa al encargado en la bitácora.
            with self._uow_factory() as uow:
                uow.auditoria.agregar(RegistroAuditoria(
                    evento.pedido_id, "DESCUENTO_INVENTARIO_FALLIDO", evento.usuario, "",
                    str(error), evento.fecha))
                uow.commit()
            return
        for platillo in platillos:
            self._despachador.despachar(platillo.eventos)
            platillo.limpiar_eventos()
