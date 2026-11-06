"""Máquina de estados del pedido (NB-06). Es la única fuente de las transiciones válidas."""
from src.domain.errores import DatosInvalidos, TransicionInvalida
from src.domain.valores import EstadoPedido as E

TRANSICIONES = {
    E.REGISTRADO: {"iniciar_preparacion": E.EN_PREPARACION, "cancelar": E.CANCELADO},
    E.EN_PREPARACION: {"marcar_listo": E.LISTO, "cancelar": E.CANCELADO},
    E.LISTO: {"entregar": E.ENTREGADO, "cancelar": E.CANCELADO},
    E.ENTREGADO: {},
    E.CANCELADO: {},
}

_DESTINO = {
    "iniciar_preparacion": E.EN_PREPARACION,
    "marcar_listo": E.LISTO,
    "entregar": E.ENTREGADO,
    "cancelar": E.CANCELADO,
}
_ETIQUETA = {
    "iniciar_preparacion": "iniciar la preparación de",
    "marcar_listo": "marcar como listo",
    "entregar": "entregar",
}


class MaquinaEstados:
    @staticmethod
    def acciones_permitidas(estado):
        return sorted(TRANSICIONES[estado])

    @staticmethod
    def siguiente(estado, accion):
        if accion not in _DESTINO:
            raise DatosInvalidos(f"La acción «{accion}» no existe.")
        destino = TRANSICIONES[estado].get(accion)
        if destino is not None:
            return destino
        if accion == "cancelar":
            if estado == E.ENTREGADO:
                raise TransicionInvalida("Un pedido entregado ya no se puede cancelar.")
            raise TransicionInvalida("El pedido ya fue cancelado anteriormente.")
        if estado == _DESTINO[accion]:
            raise TransicionInvalida(f"El pedido ya está «{estado.value}».")
        raise TransicionInvalida(
            f"No es posible {_ETIQUETA[accion]} un pedido que está «{estado.value}»."
        )
