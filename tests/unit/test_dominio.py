import pytest
from src.domain.catalogo import Platillo
from src.domain.errores import (
    DatosInvalidos,
    ProductoNoDisponible,
    StockInsuficiente,
    TransicionInvalida,
)
from src.domain.eventos import PedidoCancelado, PedidoRegistrado, StockCriticoAlcanzado
from src.domain.maquina_estados import MaquinaEstados
from src.domain.pedido import LineaPedido, Pedido
from src.domain.valores import Dinero, EstadoPedido

E = EstadoPedido


def _pedido(cantidad=2):
    return Pedido.registrar("PED-1", "C1", [LineaPedido("P1", cantidad, Dinero("100"))])


# ---- Dinero ----
def test_dinero_redondea_a_centavos():
    assert str(Dinero("10.005")) == "10.01"
    assert str(Dinero(3)) == "3.00"


def test_dinero_no_acepta_negativos_ni_texto():
    with pytest.raises(DatosInvalidos, match="negativo"):
        Dinero("-1")
    with pytest.raises(DatosInvalidos, match="no es válido"):
        Dinero("abc")


def test_dinero_suma_y_compara():
    assert Dinero("1500") >= Dinero("1500")
    assert Dinero("1499.99") < Dinero("1500")
    assert str(Dinero("10") + Dinero("5.50")) == "15.50"
    assert str(Dinero("2.50").por(3)) == "7.50"


# ---- Máquina de estados ----
@pytest.mark.parametrize("estado, accion, esperado", [
    (E.REGISTRADO, "iniciar_preparacion", E.EN_PREPARACION),
    (E.EN_PREPARACION, "marcar_listo", E.LISTO),
    (E.LISTO, "entregar", E.ENTREGADO),
    (E.REGISTRADO, "cancelar", E.CANCELADO),
    (E.EN_PREPARACION, "cancelar", E.CANCELADO),
    (E.LISTO, "cancelar", E.CANCELADO),
])
def test_transiciones_validas(estado, accion, esperado):
    assert MaquinaEstados.siguiente(estado, accion) == esperado


@pytest.mark.parametrize("estado, accion, mensaje", [
    (E.REGISTRADO, "entregar", "No es posible entregar un pedido que está «Registrado»"),
    (E.REGISTRADO, "marcar_listo", "No es posible marcar como listo"),
    (E.EN_PREPARACION, "iniciar_preparacion", "ya está «En preparación»"),
    (E.ENTREGADO, "entregar", "ya está «Entregado»"),
    (E.ENTREGADO, "cancelar", "ya no se puede cancelar"),
    (E.CANCELADO, "cancelar", "ya fue cancelado"),
    (E.CANCELADO, "iniciar_preparacion", "No es posible iniciar la preparación"),
])
def test_transiciones_invalidas_con_mensaje_para_el_cliente(estado, accion, mensaje):
    with pytest.raises(TransicionInvalida, match=mensaje):
        MaquinaEstados.siguiente(estado, accion)


def test_accion_inexistente_y_acciones_permitidas():
    with pytest.raises(DatosInvalidos, match="no existe"):
        MaquinaEstados.siguiente(E.REGISTRADO, "volar")
    assert MaquinaEstados.acciones_permitidas(E.REGISTRADO) == ["cancelar", "iniciar_preparacion"]
    assert MaquinaEstados.acciones_permitidas(E.ENTREGADO) == []


# ---- Pedido ----
def test_registrar_pedido_calcula_total_y_emite_evento():
    pedido = _pedido(3)
    assert pedido.estado == E.REGISTRADO
    assert str(pedido.total) == "300.00"
    assert isinstance(pedido.eventos[0], PedidoRegistrado)
    pedido.limpiar_eventos()
    assert pedido.eventos == ()


@pytest.mark.parametrize("cantidad", [0, -1, True, 1.5])
def test_registrar_rechaza_cantidades_invalidas(cantidad):
    with pytest.raises(DatosInvalidos, match="entero mayor a cero"):
        _pedido(cantidad)


def test_registrar_rechaza_pedido_sin_productos():
    with pytest.raises(DatosInvalidos, match="al menos un producto"):
        Pedido.registrar("PED-1", "C1", [])


def test_flujo_completo_emite_un_evento_por_paso():
    pedido = _pedido()
    pedido.limpiar_eventos()
    pedido.iniciar_preparacion()
    pedido.marcar_listo()
    pedido.entregar()
    assert [e.nombre for e in pedido.eventos] == [
        "PedidoEnPreparacion", "PedidoListo", "PedidoEntregado"]
    assert pedido.eventos[-1].lineas == (("P1", 2),)


def test_cancelar_exige_motivo_y_registra_evento():
    pedido = _pedido()
    with pytest.raises(DatosInvalidos, match="indicar el motivo"):
        pedido.cancelar("   ", "u1", "Encargado")
    assert pedido.estado == E.REGISTRADO
    pedido.cancelar("  Se retrasó  ", "u1", "Encargado")
    assert pedido.estado == E.CANCELADO and pedido.motivo_cancelacion == "Se retrasó"
    assert isinstance(pedido.eventos[-1], PedidoCancelado)


def test_reconstruir_permite_pedido_vacio_sin_eventos():
    pedido = Pedido.reconstruir("PED-X", "C1", [], None)
    assert pedido.eventos == () and str(pedido.total) == "0.00"


# ---- Platillo ----
def _platillo(stock=10, habilitado=True):
    return Platillo("P1", "Taco", Dinero("100"), stock, habilitado, 5)


def test_platillo_agotado_o_deshabilitado_usa_el_mensaje_de_la_historia_us05():
    for platillo in (_platillo(0), _platillo(10, False)):
        with pytest.raises(ProductoNoDisponible) as error:
            platillo.verificar_disponible(1)
        assert str(error.value) == "Producto no disponible por falta de ingredientes"


def test_platillo_stock_insuficiente():
    with pytest.raises(StockInsuficiente, match="Solo quedan 10 unidades"):
        _platillo(10).verificar_disponible(11)
    _platillo(10).verificar_disponible(10)


def test_descontar_alerta_cuando_el_stock_llega_al_critico():
    platillo = _platillo(10)
    platillo.descontar(4)
    assert platillo.eventos == ()
    platillo.descontar(1)  # queda en 5 = stock crítico (límite)
    assert platillo.en_stock_critico
    assert isinstance(platillo.eventos[0], StockCriticoAlcanzado)


def test_descontar_no_permite_mas_de_lo_que_hay_ni_cantidades_invalidas():
    with pytest.raises(StockInsuficiente):
        _platillo(3).descontar(4)
    with pytest.raises(DatosInvalidos):
        _platillo(3).descontar(0)


def test_entrada_y_merma():
    platillo = _platillo(10)
    platillo.registrar_entrada(5)
    assert platillo.stock == 15
    with pytest.raises(DatosInvalidos, match="indicar el motivo"):
        platillo.registrar_merma(1, "")
    platillo.registrar_merma(2, "Se cayó")
    assert platillo.stock == 13
    with pytest.raises(DatosInvalidos):
        platillo.registrar_entrada(0)
