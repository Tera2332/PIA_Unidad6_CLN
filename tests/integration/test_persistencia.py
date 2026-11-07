"""Integración con SQLAlchemy: repositorios, Unit of Work, commit, rollback y carga del paquete."""
from datetime import date

from src.application.casos_uso import LineaSolicitada
from src.application.contenedor import construir_aplicacion
from src.domain.actor import Actor
from src.domain.auditoria import RegistroAuditoria
from src.domain.catalogo import Platillo
from src.domain.pedido import LineaPedido, Pedido
from src.domain.valores import Dinero, EstadoPedido
from src.infrastructure.seed import cargar_datos
from tests.unit.helpers import AHORA


def _preparar(uow_factory):
    with uow_factory() as uow:
        uow.actores.guardar(Actor("C1", "Ana", True, True, "Monterrey"))
        uow.platillos.guardar(Platillo("P1", "Taco", Dinero("100"), 10, True, 5))
        uow.commit()


def _pedido():
    return Pedido.reconstruir(
        "PED-1", "C1", [LineaPedido("P1", 2, Dinero("100"), ("sin cebolla", "extra queso"))],
        date(2026, 11, 4), True, True, "REF-1")


def test_guardar_y_recuperar_un_pedido_conserva_todo(uow_factory):
    _preparar(uow_factory)
    with uow_factory() as uow:
        uow.pedidos.guardar(_pedido())
        uow.commit()
    with uow_factory() as uow:
        pedido = uow.pedidos.obtener("PED-1")
    assert pedido.estado == EstadoPedido.REGISTRADO and pedido.promocion_activa is True
    assert pedido.lineas[0].modificaciones == ("sin cebolla", "extra queso")
    assert str(pedido.total) == "200.00" and pedido.referencia == "REF-1"


def test_sin_commit_todo_se_revierte(uow_factory):
    _preparar(uow_factory)
    with uow_factory() as uow:
        uow.pedidos.guardar(_pedido())  # sin commit
    with uow_factory() as uow:
        assert uow.pedidos.obtener("PED-1") is None


def test_actualizar_pedido_y_platillo(uow_factory):
    _preparar(uow_factory)
    with uow_factory() as uow:
        uow.pedidos.guardar(_pedido())
        uow.commit()
    with uow_factory() as uow:
        pedido = uow.pedidos.obtener("PED-1")
        pedido.cancelar("Cambio de planes", "enc1", "Encargado", AHORA)
        uow.pedidos.guardar(pedido)
        platillo = uow.platillos.obtener("P1")
        platillo.descontar(4)
        uow.platillos.guardar(platillo)
        uow.commit()
    with uow_factory() as uow:
        assert uow.pedidos.obtener("PED-1").estado == EstadoPedido.CANCELADO
        assert uow.pedidos.obtener("PED-1").motivo_cancelacion == "Cambio de planes"
        assert len(uow.pedidos.listar(EstadoPedido.CANCELADO)) == 1
        assert uow.pedidos.listar(EstadoPedido.LISTO) == []
        assert uow.platillos.obtener("P1").stock == 6
        assert list(uow.platillos.obtener_varios(["P1", "P9"])) == ["P1"]


def test_auditoria_solo_agrega_y_filtra(uow_factory):
    with uow_factory() as uow:
        uow.auditoria.agregar(RegistroAuditoria("PED-1", "CANCELAR_PEDIDO", "u1", "Gerente", "m", AHORA))
        uow.auditoria.agregar(RegistroAuditoria("PED-2", "REGISTRAR_PEDIDO", "u2", "", "d", AHORA))
        uow.commit()
        assert not hasattr(uow.auditoria, "actualizar") and not hasattr(uow.auditoria, "borrar")
    with uow_factory() as uow:
        assert len(uow.auditoria.listar()) == 2
        assert [r.accion for r in uow.auditoria.listar(pedido_id="PED-1")] == ["CANCELAR_PEDIDO"]
        assert len(uow.auditoria.listar(accion="REGISTRAR_PEDIDO")) == 1


def test_carga_del_paquete_es_idempotente(uow_factory):
    resultado = cargar_datos(uow_factory, "data")
    assert resultado == {"cargado": True, "actores": 40, "platillos": 20, "pedidos": 60}
    assert cargar_datos(uow_factory, "data") == {"cargado": False}
    with uow_factory() as uow:
        assert len(uow.pedidos.listar()) == 60
        assert uow.pedidos.obtener("PED-O013").lineas == ()


def test_casos_de_uso_con_base_de_datos_real(uow_sembrada):
    app = construir_aplicacion(uow_sembrada)
    with uow_sembrada() as uow:
        antes = uow.platillos.obtener("PED-P001").stock
    pedido = app.registrar_pedido.ejecutar(
        "PED-C001", [LineaSolicitada("PED-P001", 2)], usuario="mesero1", ahora=AHORA)
    for caso in (app.iniciar_preparacion, app.marcar_listo, app.entregar_pedido):
        caso.ejecutar(pedido.id, "u1", AHORA)
    with uow_sembrada() as uow:
        assert uow.platillos.obtener("PED-P001").stock == antes - 2
        acciones = [r.accion for r in uow.auditoria.listar(pedido_id=pedido.id)]
    assert acciones == ["REGISTRAR_PEDIDO", "INICIAR_PREPARACION", "MARCAR_LISTO", "ENTREGAR_PEDIDO"]
