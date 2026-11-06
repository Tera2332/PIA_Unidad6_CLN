"""Conversión de objetos del dominio a diccionarios simples (modelo de lectura)."""
from src.domain.errores import DatosInvalidos
from src.domain.valores import EstadoPedido


def pedido_a_dict(pedido):
    return {
        "id": pedido.id,
        "actor_id": pedido.actor_id,
        "estado": pedido.estado.value,
        "total": str(pedido.total),
        "moneda": "MXN",
        "fecha_solicitud": pedido.fecha_solicitud.isoformat(),
        "promocion_activa": pedido.promocion_activa,
        "autorizado": pedido.autorizado,
        "referencia": pedido.referencia,
        "motivo_cancelacion": pedido.motivo_cancelacion,
        "lineas": [
            {
                "platillo_id": x.platillo_id,
                "cantidad": x.cantidad,
                "precio_unitario": str(x.precio_unitario),
                "subtotal": str(x.subtotal),
                "modificaciones": list(x.modificaciones),
            }
            for x in pedido.lineas
        ],
    }


def platillo_a_dict(platillo):
    return {
        "id": platillo.id,
        "descripcion": platillo.descripcion,
        "precio": str(platillo.precio),
        "stock": platillo.stock,
        "habilitado": platillo.habilitado,
        "disponible": platillo.disponible,
        "stock_critico": platillo.en_stock_critico,
    }


def registro_a_dict(registro):
    return {
        "pedido_id": registro.pedido_id,
        "accion": registro.accion,
        "usuario": registro.usuario,
        "rol": registro.rol,
        "detalle": registro.detalle,
        "fecha": registro.fecha.isoformat(),
    }


def parsear_estado(texto):
    if texto is None or texto == "":
        return None
    clave = texto.strip().upper().replace(" ", "_").replace("Ó", "O")
    try:
        return EstadoPedido[clave]
    except KeyError:
        validos = ", ".join(e.name for e in EstadoPedido)
        raise DatosInvalidos(f"El estado «{texto}» no existe. Usa uno de: {validos}.") from None
