"""Pruebas de integración de la API REST con base de datos real (SQLite o PostgreSQL)."""
from fastapi.testclient import TestClient
from src.api.main import crear_app
from src.infrastructure.evidencias import ejecutar_casos
from src.infrastructure.seed import leer_csv

CLIENTE_ACTIVO = "PED-C001"
PLATILLO = "PED-P001"
PLATILLO_DESHABILITADO = "PED-P011"


def _pedido_nuevo(cliente, cantidad=2, actor=CLIENTE_ACTIVO, platillo=PLATILLO):
    return cliente.post("/pedidos", json={
        "actor_id": actor, "lineas": [{"platillo_id": platillo, "cantidad": cantidad,
                                       "modificaciones": ["sin cebolla"]}]})


def _stock(cliente, platillo=PLATILLO):
    return [p for p in cliente.get("/platillos").json() if p["id"] == platillo][0]["stock"]


def _operacion(tipo, resultado):
    return [f["operacion_id"] for f in ejecutar_casos("data")
            if f["tipo_prueba"] == tipo and f["resultado_alumno"] == resultado][0]


def test_salud_y_documentacion_openapi(cliente):
    assert cliente.get("/salud").json() == {"estado": "ok"}
    especificacion = cliente.get("/openapi.json").json()
    assert especificacion["info"]["title"].startswith("Sazón Urbano")
    for ruta in ("/pedidos", "/pedidos/{pedido_id}/cancelacion", "/platillos", "/reportes/resumen"):
        assert ruta in especificacion["paths"]
    assert cliente.get("/docs").status_code == 200


def test_registrar_pedido_devuelve_201_y_total(cliente):
    respuesta = _pedido_nuevo(cliente)
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "Registrado" and cuerpo["id"].startswith("PED-")
    assert cuerpo["lineas"][0]["modificaciones"] == ["sin cebolla"]
    assert float(cuerpo["total"]) == 2 * float(cuerpo["lineas"][0]["precio_unitario"])


def test_validacion_de_datos_responde_en_espanol(cliente):
    respuesta = cliente.post("/pedidos", json={"actor_id": CLIENTE_ACTIVO})
    assert respuesta.status_code == 422
    assert "Revisa: lineas" in respuesta.json()["detail"]


def test_reglas_de_registro_con_mensajes_claros(cliente):
    inactivo = [a for a in leer_csv("data/actores.csv") if a["activo"] == "0"][0]["actor_id"]
    caso = _pedido_nuevo(cliente, actor=inactivo)
    assert caso.status_code == 409 and "no está activo" in caso.json()["detail"]
    assert _pedido_nuevo(cliente, actor="NADIE").status_code == 404
    agotado = _pedido_nuevo(cliente, platillo=PLATILLO_DESHABILITADO)
    assert agotado.status_code == 409
    assert agotado.json()["detail"] == "Producto no disponible por falta de ingredientes"
    assert _pedido_nuevo(cliente, cantidad=0).status_code == 422
    assert _pedido_nuevo(cliente, cantidad=10_000).status_code == 409


def test_flujo_completo_descuenta_inventario_y_deja_bitacora(cliente):
    antes = _stock(cliente)
    pedido_id = _pedido_nuevo(cliente, cantidad=3).json()["id"]
    for ruta, estado in (("preparacion", "En preparación"), ("listo", "Listo"),
                         ("entrega", "Entregado")):
        respuesta = cliente.post(f"/pedidos/{pedido_id}/{ruta}")
        assert respuesta.status_code == 200 and respuesta.json()["estado"] == estado
    assert _stock(cliente) == antes - 3
    acciones = [r["accion"] for r in cliente.get("/auditoria", params={"pedido_id": pedido_id}).json()]
    assert acciones == ["REGISTRAR_PEDIDO", "INICIAR_PREPARACION", "MARCAR_LISTO", "ENTREGAR_PEDIDO"]
    assert cliente.get(f"/pedidos/{pedido_id}").json()["estado"] == "Entregado"


def test_transiciones_invalidas_responden_409(cliente):
    pedido_id = _pedido_nuevo(cliente).json()["id"]
    respuesta = cliente.post(f"/pedidos/{pedido_id}/entrega")
    assert respuesta.status_code == 409
    assert "No es posible entregar un pedido que está «Registrado»" in respuesta.json()["detail"]
    cliente.post(f"/pedidos/{pedido_id}/preparacion")
    assert cliente.post(f"/pedidos/{pedido_id}/preparacion").status_code == 409


def test_cancelacion_solo_para_encargado_o_gerente(cliente):
    pedido_id = _pedido_nuevo(cliente).json()["id"]
    cuerpo = {"motivo": "El cliente se fue", "usuario": "u1", "rol": "Mesero"}
    denegada = cliente.post(f"/pedidos/{pedido_id}/cancelacion", json=cuerpo)
    assert denegada.status_code == 403
    assert denegada.json()["detail"].startswith("Solo el Encargado o el Gerente")
    sin_motivo = cliente.post(f"/pedidos/{pedido_id}/cancelacion",
                              json={**cuerpo, "rol": "Gerente", "motivo": " "})
    assert sin_motivo.status_code == 422 and "motivo" in sin_motivo.json()["detail"]
    aceptada = cliente.post(f"/pedidos/{pedido_id}/cancelacion", json={**cuerpo, "rol": "Encargado"})
    assert aceptada.status_code == 200 and aceptada.json()["estado"] == "Cancelado"
    cancelaciones = cliente.get("/cancelaciones").json()
    assert cancelaciones[-1]["pedido_id"] == pedido_id and cancelaciones[-1]["rol"] == "Encargado"


def test_iniciar_preparacion_aplica_las_specifications(cliente):
    sin_autorizar = [f["operacion_id"] for f in ejecutar_casos("data")
                     if f["tipo_prueba"] == "validar_operacion"
                     and "no está autorizado" in f["motivos_de_falla"]][0]
    respuesta = cliente.post(f"/pedidos/{sin_autorizar}/preparacion")
    assert respuesta.status_code == 409 and "no puede procesarse" in respuesta.json()["detail"]
    valida = _operacion("validar_operacion", "CUMPLE")
    assert cliente.post(f"/pedidos/{valida}/preparacion").status_code == 200


def test_consultas_filtros_y_evaluacion(cliente):
    assert cliente.get("/pedidos/NO-EXISTE").status_code == 404
    assert cliente.get("/pedidos", params={"estado": "volando"}).status_code == 422
    assert len(cliente.get("/pedidos", params={"estado": "registrado"}).json()) == 60
    evaluacion = cliente.get("/pedidos/PED-O001/evaluacion").json()
    assert evaluacion["puede_procesarse"] is True
    assert set(evaluacion) >= {"beneficio_referencia", "motivos_beneficio_referencia"}
    assert len(cliente.get("/platillos", params={"q": "hamburguesa"}).json()) >= 1


def test_ajustes_de_inventario_y_reporte(cliente):
    antes = _stock(cliente)
    entrada = cliente.post("/inventario/ajustes", json={
        "platillo_id": PLATILLO, "tipo": "entrada", "cantidad": 4})
    assert entrada.status_code == 200 and entrada.json()["stock"] == antes + 4
    sin_motivo = cliente.post("/inventario/ajustes", json={
        "platillo_id": PLATILLO, "tipo": "merma", "cantidad": 1})
    assert sin_motivo.status_code == 422
    merma = cliente.post("/inventario/ajustes", json={
        "platillo_id": PLATILLO, "tipo": "merma", "cantidad": 1, "motivo": "Se cayó"})
    assert merma.json()["stock"] == antes + 3
    resumen = cliente.get("/reportes/resumen").json()
    assert resumen["pedidos_por_estado"]["Registrado"] == 60
    assert len(resumen["inventario"]) == 20


def test_un_error_inesperado_no_expone_detalles_tecnicos():
    def uow_roto():
        raise RuntimeError("password=secreto; traceback interno")

    cliente = TestClient(crear_app(uow_factory=uow_roto), raise_server_exceptions=False)
    respuesta = cliente.get("/platillos")
    assert respuesta.status_code == 500
    assert respuesta.json()["detail"] == "No pudimos procesar tu solicitud. Inténtalo de nuevo más tarde."
    assert "secreto" not in respuesta.text
