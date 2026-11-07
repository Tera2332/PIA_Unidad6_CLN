"""Casos de uso. Los comandos orquestan; las reglas viven en el dominio (ADR-003)."""
from dataclasses import dataclass
from uuid import uuid4

from src.application.dtos import (
    pedido_a_dict,
    platillo_a_dict,
    registro_a_dict,
)
from src.domain.errores import NoEncontrado, ReglaNoCumplida
from src.domain.pedido import LineaPedido, Pedido
from src.domain.specifications import (
    Contexto,
    beneficio_referencia,
    puede_procesarse,
)
from src.domain.valores import Dinero, EstadoPedido


def generar_id_pedido():
    return "PED-" + uuid4().hex[:8].upper()


@dataclass(frozen=True)
class LineaSolicitada:
    platillo_id: str
    cantidad: int
    modificaciones: tuple = ()


def _pedido_o_error(uow, pedido_id):
    pedido = uow.pedidos.obtener(pedido_id)
    if pedido is None:
        raise NoEncontrado("El pedido solicitado no existe.")
    return pedido


class _CasoDeUso:
    def __init__(self, uow_factory, despachador):
        self._uow_factory = uow_factory
        self._despachador = despachador

    def _publicar(self, agregado):
        self._despachador.despachar(agregado.eventos)
        agregado.limpiar_eventos()


# ---------------- Comandos ----------------
class RegistrarPedido(_CasoDeUso):
    def __init__(self, uow_factory, despachador, generador_id=generar_id_pedido):
        super().__init__(uow_factory, despachador)
        self._generador_id = generador_id

    def ejecutar(self, actor_id, lineas, promocion_activa=False, autorizado=True,
                 referencia=None, usuario="sistema", ahora=None):
        with self._uow_factory() as uow:
            actor = uow.actores.obtener(actor_id)
            if actor is None:
                raise NoEncontrado("El cliente indicado no existe.")
            if not actor.activo:
                raise ReglaNoCumplida("El cliente no está activo y no puede realizar pedidos.")
            catalogo = uow.platillos.obtener_varios([x.platillo_id for x in lineas])
            lineas_dominio = []
            for solicitada in lineas:
                platillo = catalogo.get(solicitada.platillo_id)
                if platillo is None:
                    raise NoEncontrado(f"El platillo «{solicitada.platillo_id}» no existe.")
                if isinstance(solicitada.cantidad, int) and solicitada.cantidad > 0:
                    platillo.verificar_disponible(solicitada.cantidad)
                lineas_dominio.append(LineaPedido(
                    platillo.id, solicitada.cantidad, platillo.precio,
                    tuple(solicitada.modificaciones)))
            pedido = Pedido.registrar(
                self._generador_id(), actor_id, lineas_dominio, promocion_activa, autorizado,
                referencia, usuario, ahora)
            uow.pedidos.guardar(pedido)
            uow.commit()
        self._publicar(pedido)
        return pedido


class _CambioDeEstado(_CasoDeUso):
    accion = ""

    def _verificar(self, uow, pedido):
        """Punto de extensión para reglas previas (Specifications)."""

    def ejecutar(self, pedido_id, usuario="sistema", ahora=None):
        with self._uow_factory() as uow:
            pedido = _pedido_o_error(uow, pedido_id)
            self._verificar(uow, pedido)
            getattr(pedido, self.accion)(usuario=usuario, ahora=ahora)
            uow.pedidos.guardar(pedido)
            uow.commit()
        self._publicar(pedido)
        return pedido


class IniciarPreparacion(_CambioDeEstado):
    accion = "iniciar_preparacion"

    def _verificar(self, uow, pedido):
        contexto = Contexto(pedido=pedido, actor=uow.actores.obtener(pedido.actor_id))
        regla = puede_procesarse()
        if not regla.es_satisfecha_por(contexto):
            motivos = "; ".join(regla.motivos_de_falla(contexto))
            raise ReglaNoCumplida(f"El pedido no puede procesarse: {motivos}.")


class MarcarListo(_CambioDeEstado):
    accion = "marcar_listo"


class EntregarPedido(_CambioDeEstado):
    accion = "entregar"


class CancelarPedido(_CasoDeUso):
    def __init__(self, uow_factory, despachador, control_acceso):
        super().__init__(uow_factory, despachador)
        self._control = control_acceso

    def ejecutar(self, pedido_id, motivo, usuario, rol, ahora=None):
        self._control.verificar_cancelacion(rol)  # interceptor RBAC antes del dominio
        with self._uow_factory() as uow:
            pedido = _pedido_o_error(uow, pedido_id)
            pedido.cancelar(motivo, usuario, rol, ahora)
            uow.pedidos.guardar(pedido)
            uow.commit()
        self._publicar(pedido)
        return pedido


class AjustarInventario(_CasoDeUso):
    def _ajustar(self, platillo_id, operacion):
        with self._uow_factory() as uow:
            platillo = uow.platillos.obtener(platillo_id)
            if platillo is None:
                raise NoEncontrado(f"El platillo «{platillo_id}» no existe.")
            operacion(platillo)
            uow.platillos.guardar(platillo)
            uow.commit()
        self._publicar(platillo)
        return platillo

    def entrada(self, platillo_id, cantidad, usuario="sistema", ahora=None):
        return self._ajustar(
            platillo_id, lambda p: p.registrar_entrada(cantidad, usuario, ahora))

    def merma(self, platillo_id, cantidad, motivo, usuario="sistema", ahora=None):
        return self._ajustar(
            platillo_id, lambda p: p.registrar_merma(cantidad, motivo, usuario, ahora))


# ---------------- Consultas (modelo de lectura) ----------------
class _Consulta:
    def __init__(self, uow_factory):
        self._uow_factory = uow_factory


class ConsultarPedido(_Consulta):
    def ejecutar(self, pedido_id):
        with self._uow_factory() as uow:
            return pedido_a_dict(_pedido_o_error(uow, pedido_id))


class ListarPedidos(_Consulta):
    def ejecutar(self, estado=None):
        with self._uow_factory() as uow:
            return [pedido_a_dict(p) for p in uow.pedidos.listar(estado)]


class EvaluarPedido(_Consulta):
    """Aplica las Specifications al pedido y explica el resultado (ver docs/architecture)."""

    def ejecutar(self, pedido_id):
        with self._uow_factory() as uow:
            pedido = _pedido_o_error(uow, pedido_id)
            contexto = Contexto(pedido=pedido, actor=uow.actores.obtener(pedido.actor_id))
        reglas = {"puede_procesarse": puede_procesarse(),
                  "beneficio_referencia": beneficio_referencia()}
        resultado = {"pedido_id": pedido.id, "total": str(pedido.total)}
        for nombre, regla in reglas.items():
            resultado[nombre] = regla.es_satisfecha_por(contexto)
            resultado["motivos_" + nombre] = regla.motivos_de_falla(contexto)
        return resultado


class ConsultarDisponibilidad(_Consulta):
    def ejecutar(self, texto=None):
        with self._uow_factory() as uow:
            platillos = uow.platillos.listar()
        if texto:
            platillos = [p for p in platillos if texto.lower() in p.descripcion.lower()]
        return [platillo_a_dict(p) for p in platillos]


class ConsultarCancelaciones(_Consulta):
    def ejecutar(self):
        with self._uow_factory() as uow:
            return [registro_a_dict(r) for r in uow.auditoria.listar(accion="CANCELAR_PEDIDO")]


class ConsultarAuditoria(_Consulta):
    def ejecutar(self, pedido_id=None):
        with self._uow_factory() as uow:
            return [registro_a_dict(r) for r in uow.auditoria.listar(pedido_id=pedido_id)]


class ReporteResumen(_Consulta):
    """US-14 y US-15: compara lo vendido con lo que queda en inventario."""

    def ejecutar(self):
        with self._uow_factory() as uow:
            pedidos = uow.pedidos.listar()
            platillos = uow.platillos.listar()
        por_estado = {e.value: 0 for e in EstadoPedido}
        vendidas = {}
        ventas = Dinero.cero()
        for pedido in pedidos:
            por_estado[pedido.estado.value] += 1
            if pedido.estado == EstadoPedido.ENTREGADO:
                ventas = ventas + pedido.total
                for linea in pedido.lineas:
                    vendidas[linea.platillo_id] = vendidas.get(linea.platillo_id, 0) + linea.cantidad
        return {
            "ventas": {"pedidos_entregados": por_estado[EstadoPedido.ENTREGADO.value],
                       "total_mxn": str(ventas)},
            "pedidos_por_estado": por_estado,
            "inventario": [
                {"platillo_id": p.id, "descripcion": p.descripcion, "stock": p.stock,
                 "unidades_vendidas": vendidas.get(p.id, 0), "stock_critico": p.en_stock_critico}
                for p in platillos
            ],
        }
