"""Patrón Specification: reglas de negocio combinables con AND (&), OR (|) y NOT (~)."""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.domain.valores import Dinero


@dataclass
class Contexto:
    pedido: object = None
    actor: object = None
    catalogo: object = None  # dict id -> Platillo
    rol: str = None


class Especificacion(ABC):
    descripcion = ""
    motivo = ""
    motivo_inverso = ""

    @abstractmethod
    def es_satisfecha_por(self, contexto):
        ...

    def y(self, otra):
        return EspecificacionY(self, otra)

    def o(self, otra):
        return EspecificacionO(self, otra)

    def no(self):
        return EspecificacionNo(self)

    __and__ = y
    __or__ = o
    __invert__ = no

    def motivos_de_falla(self, contexto):
        return [] if self.es_satisfecha_por(contexto) else [self.motivo]

    def explicar(self, contexto):
        return [(self.descripcion, self.es_satisfecha_por(contexto))]


class EspecificacionY(Especificacion):
    def __init__(self, izquierda, derecha):
        self.izq, self.der = izquierda, derecha

    @property
    def descripcion(self):
        return f"({self.izq.descripcion} Y {self.der.descripcion})"

    def es_satisfecha_por(self, contexto):
        return self.izq.es_satisfecha_por(contexto) and self.der.es_satisfecha_por(contexto)

    def motivos_de_falla(self, contexto):
        return self.izq.motivos_de_falla(contexto) + self.der.motivos_de_falla(contexto)

    def explicar(self, contexto):
        return self.izq.explicar(contexto) + self.der.explicar(contexto)


class EspecificacionO(Especificacion):
    def __init__(self, izquierda, derecha):
        self.izq, self.der = izquierda, derecha

    @property
    def descripcion(self):
        return f"({self.izq.descripcion} O {self.der.descripcion})"

    def es_satisfecha_por(self, contexto):
        return self.izq.es_satisfecha_por(contexto) or self.der.es_satisfecha_por(contexto)

    def motivos_de_falla(self, contexto):
        if self.es_satisfecha_por(contexto):
            return []
        return self.izq.motivos_de_falla(contexto) + self.der.motivos_de_falla(contexto)

    def explicar(self, contexto):
        return self.izq.explicar(contexto) + self.der.explicar(contexto)


class EspecificacionNo(Especificacion):
    def __init__(self, interna):
        self.interna = interna

    @property
    def descripcion(self):
        return f"NO ({self.interna.descripcion})"

    def es_satisfecha_por(self, contexto):
        return not self.interna.es_satisfecha_por(contexto)

    def motivos_de_falla(self, contexto):
        return [] if self.es_satisfecha_por(contexto) else [self.interna.motivo_inverso]

    def explicar(self, contexto):
        return [(self.descripcion, self.es_satisfecha_por(contexto))]


class ActorActivo(Especificacion):
    descripcion = "El cliente está activo"
    motivo = "el cliente no está activo"

    def es_satisfecha_por(self, c):
        return c.actor is not None and bool(c.actor.activo)


class ActorPreferente(Especificacion):
    descripcion = "El cliente es preferente"
    motivo = "el cliente no es preferente"

    def es_satisfecha_por(self, c):
        return c.actor is not None and bool(c.actor.es_preferente)


class PedidoConLineas(Especificacion):
    descripcion = "El pedido tiene al menos un producto"
    motivo = "el pedido no tiene productos"

    def es_satisfecha_por(self, c):
        return c.pedido is not None and len(c.pedido.lineas) > 0


class PedidoAutorizado(Especificacion):
    descripcion = "El pedido está autorizado"
    motivo = "el pedido no está autorizado"

    def es_satisfecha_por(self, c):
        return c.pedido is not None and bool(c.pedido.autorizado)


class PromocionActiva(Especificacion):
    descripcion = "El pedido tiene una promoción activa"
    motivo = "el pedido no tiene promoción activa"
    motivo_inverso = "el pedido ya tiene una promoción activa"

    def es_satisfecha_por(self, c):
        return c.pedido is not None and bool(c.pedido.promocion_activa)


class TotalMinimo(Especificacion):
    def __init__(self, minimo):
        self.minimo = minimo
        self.descripcion = f"El total es de al menos {minimo} MXN"
        self.motivo = f"el total es menor a {minimo} MXN"

    def es_satisfecha_por(self, c):
        return c.pedido is not None and c.pedido.total >= self.minimo


class ExistenciasSuficientes(Especificacion):
    descripcion = "Hay existencias suficientes de todos los productos"
    motivo = "no hay existencias suficientes de algún producto"

    def es_satisfecha_por(self, c):
        catalogo = c.catalogo or {}
        for linea in c.pedido.lineas:
            platillo = catalogo.get(linea.platillo_id)
            if platillo is None or not platillo.habilitado or platillo.stock < linea.cantidad:
                return False
        return True


class RolEn(Especificacion):
    def __init__(self, *roles):
        self.roles = roles
        self.descripcion = f"El rol es {' o '.join(roles)}"
        self.motivo = f"el rol no es {' ni '.join(roles)}"

    def es_satisfecha_por(self, c):
        return c.rol in self.roles


MINIMO_BENEFICIO = Dinero("1500")


def puede_procesarse():
    return ActorActivo() & PedidoConLineas() & PedidoAutorizado()


def beneficio_referencia(minimo=MINIMO_BENEFICIO):
    return ActorPreferente() & TotalMinimo(minimo) & ~PromocionActiva()


def puede_autorizar_cancelacion():
    return RolEn("Encargado") | RolEn("Gerente")


def puede_venderse():
    return PedidoConLineas() & ExistenciasSuficientes()
