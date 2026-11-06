"""Repositorios y Unit of Work sobre SQLAlchemy. Convierten filas a objetos del dominio."""
import json

from sqlalchemy import select

from src.domain.actor import Actor
from src.domain.auditoria import RegistroAuditoria
from src.domain.catalogo import Platillo
from src.domain.pedido import LineaPedido, Pedido
from src.domain.valores import Dinero, EstadoPedido
from src.infrastructure.modelos import (
    ActorRow,
    AuditoriaRow,
    LineaRow,
    PedidoRow,
    PlatilloRow,
)


def _a_pedido(fila):
    lineas = tuple(
        LineaPedido(x.platillo_id, x.cantidad, Dinero(x.precio_unitario),
                    tuple(json.loads(x.modificaciones or "[]")))
        for x in fila.lineas
    )
    return Pedido.reconstruir(
        fila.id, fila.actor_id, lineas, fila.fecha_solicitud, fila.promocion_activa,
        fila.autorizado, fila.referencia, EstadoPedido[fila.estado], fila.motivo_cancelacion)


def _a_platillo(fila):
    return Platillo(fila.id, fila.descripcion, Dinero(fila.precio), fila.stock,
                    fila.habilitado, fila.stock_critico)


class PedidoSql:
    def __init__(self, sesion):
        self._s = sesion

    def obtener(self, id):
        fila = self._s.get(PedidoRow, id)
        return None if fila is None else _a_pedido(fila)

    def guardar(self, pedido):
        fila = self._s.get(PedidoRow, pedido.id)
        if fila is None:
            fila = PedidoRow(id=pedido.id)
            self._s.add(fila)
        fila.actor_id = pedido.actor_id
        fila.estado = pedido.estado.name
        fila.fecha_solicitud = pedido.fecha_solicitud
        fila.promocion_activa = pedido.promocion_activa
        fila.autorizado = pedido.autorizado
        fila.referencia = pedido.referencia
        fila.motivo_cancelacion = pedido.motivo_cancelacion
        fila.lineas = [
            LineaRow(platillo_id=x.platillo_id, cantidad=x.cantidad,
                     precio_unitario=x.precio_unitario.monto,
                     modificaciones=json.dumps(list(x.modificaciones), ensure_ascii=False))
            for x in pedido.lineas
        ]

    def listar(self, estado=None):
        consulta = select(PedidoRow).order_by(PedidoRow.id)
        if estado is not None:
            consulta = consulta.where(PedidoRow.estado == estado.name)
        return [_a_pedido(fila) for fila in self._s.scalars(consulta)]


class PlatilloSql:
    def __init__(self, sesion):
        self._s = sesion

    def obtener(self, id):
        fila = self._s.get(PlatilloRow, id)
        return None if fila is None else _a_platillo(fila)

    def obtener_varios(self, ids):
        consulta = select(PlatilloRow).where(PlatilloRow.id.in_(list(ids)))
        return {fila.id: _a_platillo(fila) for fila in self._s.scalars(consulta)}

    def listar(self):
        return [_a_platillo(f) for f in self._s.scalars(select(PlatilloRow).order_by(PlatilloRow.id))]

    def guardar(self, platillo):
        fila = self._s.get(PlatilloRow, platillo.id)
        if fila is None:
            fila = PlatilloRow(id=platillo.id)
            self._s.add(fila)
        fila.descripcion = platillo.descripcion
        fila.precio = platillo.precio.monto
        fila.stock = platillo.stock
        fila.habilitado = platillo.habilitado
        fila.stock_critico = platillo.stock_critico


class ActorSql:
    def __init__(self, sesion):
        self._s = sesion

    @staticmethod
    def _a_actor(fila):
        return Actor(fila.id, fila.nombre, fila.es_preferente, fila.activo, fila.ciudad)

    def obtener(self, id):
        fila = self._s.get(ActorRow, id)
        return None if fila is None else self._a_actor(fila)

    def listar(self):
        return [self._a_actor(f) for f in self._s.scalars(select(ActorRow).order_by(ActorRow.id))]

    def guardar(self, actor):
        fila = self._s.get(ActorRow, actor.id)
        if fila is None:
            fila = ActorRow(id=actor.id)
            self._s.add(fila)
        fila.nombre = actor.nombre
        fila.es_preferente = actor.es_preferente
        fila.activo = actor.activo
        fila.ciudad = actor.ciudad


class AuditoriaSql:
    """Solo agregar y consultar: no hay operaciones de actualizar ni borrar (ADR-005)."""

    def __init__(self, sesion):
        self._s = sesion

    def agregar(self, registro):
        self._s.add(AuditoriaRow(
            pedido_id=registro.pedido_id, accion=registro.accion, usuario=registro.usuario,
            rol=registro.rol or "", detalle=registro.detalle, fecha=registro.fecha))

    def listar(self, pedido_id=None, accion=None):
        consulta = select(AuditoriaRow).order_by(AuditoriaRow.id)
        if pedido_id is not None:
            consulta = consulta.where(AuditoriaRow.pedido_id == pedido_id)
        if accion is not None:
            consulta = consulta.where(AuditoriaRow.accion == accion)
        return [
            RegistroAuditoria(f.pedido_id, f.accion, f.usuario, f.rol, f.detalle, f.fecha)
            for f in self._s.scalars(consulta)
        ]


class SqlUnitOfWork:
    """Una transacción por bloque `with`: sin commit explícito todo se revierte."""

    def __init__(self, fabrica_sesiones):
        self._fabrica = fabrica_sesiones

    def __enter__(self):
        self._sesion = self._fabrica()
        self.pedidos = PedidoSql(self._sesion)
        self.platillos = PlatilloSql(self._sesion)
        self.actores = ActorSql(self._sesion)
        self.auditoria = AuditoriaSql(self._sesion)
        return self

    def __exit__(self, tipo, error, traza):
        try:
            self._sesion.rollback()  # no hace nada si ya se confirmó
        finally:
            self._sesion.close()
        return False

    def commit(self):
        self._sesion.commit()

    def rollback(self):
        self._sesion.rollback()
