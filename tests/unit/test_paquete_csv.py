"""Pruebas sobre el paquete de datos del PIA: carga, 120 casos y 20 transiciones."""
from collections import Counter

from src.domain.valores import EstadoPedido
from src.infrastructure.evidencias import (
    crear_entorno,
    ejecutar_casos,
    ejecutar_transiciones,
)

DATA = "data"


def test_carga_el_paquete_completo():
    _, fabrica = crear_entorno(DATA)
    with fabrica() as uow:
        assert len(uow.actores.listar()) == 40
        assert len(uow.platillos.listar()) == 20
        pedidos = uow.pedidos.listar()
        assert len(pedidos) == 60
        assert all(p.estado == EstadoPedido.REGISTRADO for p in pedidos)  # CREADO = Registrado
        vacios = sorted(p.id for p in pedidos if not p.lineas)
        assert vacios == ["PED-O013", "PED-O039"]
        assert [p.id for p in uow.platillos.listar() if not p.habilitado] == ["PED-P011"]


def test_los_120_casos_producen_resultado_y_evidencia():
    filas = ejecutar_casos(DATA)
    assert len(filas) == 120
    assert {f["resultado_alumno"] for f in filas} == {"CUMPLE", "NO CUMPLE"}
    assert all(f["evidencia"] for f in filas)
    por_tipo = Counter(f["tipo_prueba"] for f in filas)
    assert set(por_tipo) == {"validar_operacion", "evaluar_beneficio"}


def test_operaciones_sin_detalle_no_se_pueden_procesar():
    filas = [f for f in ejecutar_casos(DATA) if f["tipo_prueba"] == "validar_operacion"]
    vacias = [f for f in filas if f["operacion_id"] in ("PED-O013", "PED-O039")]
    assert vacias, "el paquete debe incluir casos sobre operaciones sin detalle"
    assert all(f["resultado_alumno"] == "NO CUMPLE" for f in vacias)
    assert all("el pedido no tiene productos" in f["motivos_de_falla"] for f in vacias)


def test_coherencia_entre_resultado_y_motivos():
    for fila in ejecutar_casos(DATA):
        assert (fila["resultado_alumno"] == "CUMPLE") == (fila["motivos_de_falla"] == "")


def test_las_20_transiciones_se_ejecutan_con_el_resultado_esperado():
    filas = ejecutar_transiciones(DATA)
    assert len(filas) == 20
    for fila in filas:
        accion, resultado = fila["accion_sugerida"], fila["resultado_alumno"]
        assert resultado in ("OK", "RECHAZADO")
        if accion == "cancelar":
            assert resultado == "OK" and fila["estado_final"] == "Cancelado"
        elif accion in ("repetir_aprobacion", "saltar_estado"):
            assert resultado == "RECHAZADO" and fila["mensaje"]
        elif resultado == "OK" and accion == "aprobar":
            assert fila["estado_final"] == "En preparación"
        elif resultado == "OK" and accion == "completar":
            assert fila["estado_final"] == "Entregado"
            assert fila["eventos"].startswith("PedidoEnPreparacion > PedidoListo")
        else:
            assert fila["excepcion"] == "ReglaNoCumplida"
