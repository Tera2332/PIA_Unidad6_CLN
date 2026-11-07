import pytest
from src.application.despachador import DespachadorEventos
from src.application.dtos import parsear_estado
from src.domain.errores import (
    AccesoDenegado,
    DatosInvalidos,
    NoEncontrado,
    ProductoNoDisponible,
    ReglaNoCumplida,
    StockInsuficiente,
    TransicionInvalida,
)
from src.domain.eventos import PedidoListo
from src.domain.valores import EstadoPedido
from src.infrastructure.memoria import AlmacenMemoria, MemoriaUnitOfWork
from tests.unit.helpers import AHORA, entorno, lineas


def _registrar(app, pares=(("P1", 2),), actor="C1", **extra):
    return app.registrar_pedido.ejecutar(actor, lineas(*pares), usuario="mesero1", ahora=AHORA, **extra)


def _acciones(almacen):
    return [r.accion for r in almacen.auditoria]


def test_registrar_pedido_guarda_audita_y_calcula_total():
    app, almacen = entorno()
    pedido = _registrar(app)
    assert pedido.id == "PED-001" and str(pedido.total) == "200.00"
    assert almacen.pedidos["PED-001"].estado == EstadoPedido.REGISTRADO
    assert _acciones(almacen) == ["REGISTRAR_PEDIDO"]
    assert pedido.eventos == ()  # los eventos ya se despacharon


def test_registrar_guarda_modificaciones_en_la_bitacora():
    app, almacen = entorno()
    from src.application.casos_uso import LineaSolicitada
    app.registrar_pedido.ejecutar("C1", [LineaSolicitada("P1", 1, ("sin cebolla",))], ahora=AHORA)
    assert "sin cebolla" in almacen.auditoria[0].detalle


@pytest.mark.parametrize("actor, pares, error, mensaje", [
    ("C9", (("P1", 1),), NoEncontrado, "cliente indicado no existe"),
    ("C3", (("P1", 1),), ReglaNoCumplida, "no está activo"),
    ("C1", (("P9", 1),), NoEncontrado, "platillo «P9» no existe"),
    ("C1", (("P3", 1),), ProductoNoDisponible, "Producto no disponible por falta de ingredientes"),
    ("C1", (("P4", 1),), ProductoNoDisponible, "Producto no disponible por falta de ingredientes"),
    ("C1", (("P2", 7),), StockInsuficiente, "Solo quedan 6 unidades"),
    ("C1", (("P1", 0),), DatosInvalidos, "entero mayor a cero"),
    ("C1", (), DatosInvalidos, "al menos un producto"),
])
def test_registrar_pedido_rechazos_con_mensaje_claro(actor, pares, error, mensaje):
    app, almacen = entorno()
    with pytest.raises(error, match=mensaje):
        _registrar(app, pares, actor)
    assert almacen.pedidos == {} and almacen.auditoria == []


def test_flujo_completo_descuenta_inventario_y_deja_bitacora():
    app, almacen = entorno()
    _registrar(app, (("P2", 2), ("P1", 3)))
    app.iniciar_preparacion.ejecutar("PED-001", "cocina1", AHORA)
    app.marcar_listo.ejecutar("PED-001", "cocina1", AHORA)
    pedido = app.entregar_pedido.ejecutar("PED-001", "repartidor1", AHORA)
    assert pedido.estado == EstadoPedido.ENTREGADO
    assert almacen.platillos["P2"].stock == 4 and almacen.platillos["P1"].stock == 17
    assert _acciones(almacen) == [
        "REGISTRAR_PEDIDO", "INICIAR_PREPARACION", "MARCAR_LISTO", "ENTREGAR_PEDIDO",
        "STOCK_CRITICO"]  # la sopa quedó con 4 unidades, por debajo del mínimo de 5


def test_alerta_de_stock_critico_queda_en_la_bitacora():
    app, almacen = entorno()
    _registrar(app, (("P2", 1),))
    for caso in (app.iniciar_preparacion, app.marcar_listo, app.entregar_pedido):
        caso.ejecutar("PED-001", "u1", AHORA)
    assert almacen.platillos["P2"].stock == 5  # 6 - 1 = stock crítico
    assert "STOCK_CRITICO" in _acciones(almacen)


def test_descuento_fallido_no_revierte_el_pedido_y_deja_incidencia():
    app, almacen = entorno()
    _registrar(app, (("P2", 5),))
    almacen.platillos["P2"].stock = 2  # se agotó antes de entregar
    for caso in (app.iniciar_preparacion, app.marcar_listo, app.entregar_pedido):
        caso.ejecutar("PED-001", "u1", AHORA)
    assert almacen.pedidos["PED-001"].estado == EstadoPedido.ENTREGADO
    assert almacen.platillos["P2"].stock == 2
    assert "DESCUENTO_INVENTARIO_FALLIDO" in _acciones(almacen)


def test_iniciar_preparacion_exige_las_specifications():
    app, _ = entorno()
    _registrar(app, autorizado=False)
    with pytest.raises(ReglaNoCumplida, match="el pedido no está autorizado"):
        app.iniciar_preparacion.ejecutar("PED-001")


def test_transiciones_invalidas_por_caso_de_uso():
    app, _ = entorno()
    _registrar(app)
    with pytest.raises(TransicionInvalida, match="No es posible entregar"):
        app.entregar_pedido.ejecutar("PED-001")
    app.iniciar_preparacion.ejecutar("PED-001")
    with pytest.raises(TransicionInvalida, match="ya está «En preparación»"):
        app.iniciar_preparacion.ejecutar("PED-001")
    with pytest.raises(NoEncontrado, match="pedido solicitado no existe"):
        app.marcar_listo.ejecutar("PED-999")


def test_cancelar_requiere_encargado_o_gerente():
    app, almacen = entorno()
    _registrar(app)
    with pytest.raises(AccesoDenegado, match="Solo el Encargado o el Gerente"):
        app.cancelar_pedido.ejecutar("PED-001", "Ya no lo quiero", "mesero1", "Mesero")
    assert almacen.pedidos["PED-001"].estado == EstadoPedido.REGISTRADO
    pedido = app.cancelar_pedido.ejecutar("PED-001", "Ya no lo quiero", "enc1", "Encargado", AHORA)
    assert pedido.estado == EstadoPedido.CANCELADO
    registro = almacen.auditoria[-1]
    assert (registro.accion, registro.usuario, registro.rol) == ("CANCELAR_PEDIDO", "enc1", "Encargado")
    with pytest.raises(TransicionInvalida, match="ya fue cancelado"):
        app.cancelar_pedido.ejecutar("PED-001", "Otra vez", "ger1", "Gerente")


def test_cancelar_exige_motivo_y_no_aplica_a_entregados():
    app, _ = entorno()
    _registrar(app)
    with pytest.raises(DatosInvalidos, match="indicar el motivo"):
        app.cancelar_pedido.ejecutar("PED-001", " ", "ger1", "Gerente")
    for caso in (app.iniciar_preparacion, app.marcar_listo, app.entregar_pedido):
        caso.ejecutar("PED-001")
    with pytest.raises(TransicionInvalida, match="entregado ya no se puede cancelar"):
        app.cancelar_pedido.ejecutar("PED-001", "Tarde", "ger1", "Gerente")


def test_ajustes_de_inventario_y_bitacora():
    app, almacen = entorno()
    app.ajustar_inventario.entrada("P1", 5, "enc1", AHORA)
    app.ajustar_inventario.merma("P1", 2, "Se cayó", "enc1", AHORA)
    assert almacen.platillos["P1"].stock == 23
    assert _acciones(almacen) == ["AJUSTE_INVENTARIO", "AJUSTE_INVENTARIO"]
    with pytest.raises(NoEncontrado):
        app.ajustar_inventario.entrada("P9", 1)
    with pytest.raises(DatosInvalidos, match="motivo"):
        app.ajustar_inventario.merma("P1", 1, "")


def test_consultas():
    app, _ = entorno()
    _registrar(app, (("P1", 1),), "C2")
    _registrar(app)
    app.cancelar_pedido.ejecutar("PED-002", "Cambio de planes", "ger1", "Gerente", AHORA)
    assert app.consultar_pedido.ejecutar("PED-001")["total"] == "100.00"
    assert [p["id"] for p in app.listar_pedidos.ejecutar(EstadoPedido.CANCELADO)] == ["PED-002"]
    assert len(app.listar_pedidos.ejecutar()) == 2
    assert [p["id"] for p in app.consultar_disponibilidad.ejecutar("sop")] == ["P2"]
    assert len(app.consultar_disponibilidad.ejecutar()) == 4
    cancelaciones = app.consultar_cancelaciones.ejecutar()
    assert [c["detalle"] for c in cancelaciones] == ["Cambio de planes"]
    assert len(app.consultar_auditoria.ejecutar("PED-001")) == 1
    evaluacion = app.evaluar_pedido.ejecutar("PED-001")
    assert evaluacion["puede_procesarse"] is True and evaluacion["beneficio_referencia"] is False


def test_reporte_resumen_compara_ventas_con_inventario():
    app, _ = entorno()
    _registrar(app, (("P1", 4),))
    for caso in (app.iniciar_preparacion, app.marcar_listo, app.entregar_pedido):
        caso.ejecutar("PED-001")
    reporte = app.reporte.ejecutar()
    assert reporte["ventas"] == {"pedidos_entregados": 1, "total_mxn": "400.00"}
    assert reporte["pedidos_por_estado"]["Entregado"] == 1
    taco = [i for i in reporte["inventario"] if i["platillo_id"] == "P1"][0]
    assert taco["unidades_vendidas"] == 4 and taco["stock"] == 16


def test_parsear_estado():
    assert parsear_estado("en preparacion") == EstadoPedido.EN_PREPARACION
    assert parsear_estado("LISTO") == EstadoPedido.LISTO
    assert parsear_estado("") is None
    with pytest.raises(DatosInvalidos, match="no existe"):
        parsear_estado("volando")


def test_unit_of_work_restaura_el_estado_si_hay_error_o_falta_commit():
    almacen = AlmacenMemoria()
    with pytest.raises(RuntimeError):
        with MemoriaUnitOfWork(almacen) as uow:
            almacen.auditoria.append("x")
            uow.commit()
            raise RuntimeError("falla")
    assert almacen.auditoria == ["x"]  # con commit previo se conserva
    with MemoriaUnitOfWork(almacen):
        almacen.auditoria.append("y")
    assert almacen.auditoria == ["x"]  # sin commit se revierte


def test_despachador_aisla_las_fallas_de_los_manejadores():
    despachador = DespachadorEventos()
    recibidos = []

    def falla(evento):
        raise RuntimeError("boom")

    despachador.suscribir_todos(falla)
    despachador.suscribir_todos(recibidos.append)
    evento = PedidoListo("PED-1", "cocina1", AHORA)
    despachador.despachar([evento])
    assert len(despachador.errores) == 1 and recibidos == [evento]
