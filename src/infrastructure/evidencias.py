"""Ejecuta los casos y transiciones del paquete del PIA y produce las evidencias en CSV."""
import csv
from pathlib import Path

from src.application.contenedor import construir_aplicacion
from src.domain.errores import DatosInvalidos, ErrorDeNegocio
from src.domain.specifications import Contexto, beneficio_referencia, puede_procesarse
from src.infrastructure.memoria import AlmacenMemoria, fabrica_memoria
from src.infrastructure.seed import cargar_datos, leer_csv

REGLAS = {"validar_operacion": puede_procesarse, "evaluar_beneficio": beneficio_referencia}


def crear_entorno(data_dir="data"):
    almacen = AlmacenMemoria()
    fabrica = fabrica_memoria(almacen)
    cargar_datos(fabrica, data_dir)
    return construir_aplicacion(fabrica), fabrica


def ejecutar_casos(data_dir="data"):
    _, fabrica = crear_entorno(data_dir)
    filas = []
    for caso in leer_csv(Path(data_dir) / "casos_prueba.csv"):
        with fabrica() as uow:
            pedido = uow.pedidos.obtener(caso["operacion_id"])
            actor = uow.actores.obtener(pedido.actor_id)
        contexto = Contexto(pedido=pedido, actor=actor)
        if caso["tipo_prueba"] not in REGLAS:
            raise DatosInvalidos(f"Tipo de prueba no soportado: {caso['tipo_prueba']}")
        regla = REGLAS[caso["tipo_prueba"]]()
        cumple = regla.es_satisfecha_por(contexto)
        fila = dict(caso)
        fila["resultado_alumno"] = "CUMPLE" if cumple else "NO CUMPLE"
        fila["total_mxn"] = str(pedido.total)
        fila["evidencia"] = "; ".join(
            f"{descripcion}: {'sí' if ok else 'no'}" for descripcion, ok in regla.explicar(contexto))
        fila["motivos_de_falla"] = "; ".join(regla.motivos_de_falla(contexto))
        filas.append(fila)
    return filas


def _aplicar(app, accion, pedido_id):
    if accion == "aprobar":
        app.iniciar_preparacion.ejecutar(pedido_id, usuario="cocina-demo")
    elif accion == "completar":
        app.iniciar_preparacion.ejecutar(pedido_id, usuario="cocina-demo")
        app.marcar_listo.ejecutar(pedido_id, usuario="cocina-demo")
        app.entregar_pedido.ejecutar(pedido_id, usuario="repartidor-demo")
    elif accion == "cancelar":
        app.cancelar_pedido.ejecutar(
            pedido_id, "Cancelación solicitada en caso de prueba", "encargado-demo", "Encargado")
    elif accion == "repetir_aprobacion":
        app.iniciar_preparacion.ejecutar(pedido_id, usuario="cocina-demo")
        app.iniciar_preparacion.ejecutar(pedido_id, usuario="cocina-demo")
    elif accion == "saltar_estado":
        app.entregar_pedido.ejecutar(pedido_id, usuario="repartidor-demo")
    else:
        raise DatosInvalidos(f"La acción «{accion}» no existe.")


def ejecutar_transiciones(data_dir="data"):
    filas = []
    for caso in leer_csv(Path(data_dir) / "transiciones_prueba.csv"):
        app, _ = crear_entorno(data_dir)
        eventos = []

        def registrar(evento, destino=eventos):
            destino.append(evento.nombre)

        app.despachador.suscribir_todos(registrar)
        resultado, excepcion, mensaje = "OK", "", ""
        try:
            _aplicar(app, caso["accion_sugerida"], caso["operacion_id"])
        except ErrorDeNegocio as error:
            resultado, excepcion, mensaje = "RECHAZADO", type(error).__name__, str(error)
        fila = dict(caso)
        fila["resultado_alumno"] = resultado
        fila["estado_final"] = app.consultar_pedido.ejecutar(caso["operacion_id"])["estado"]
        fila["eventos"] = " > ".join(eventos)
        fila["excepcion"] = excepcion
        fila["mensaje"] = mensaje
        filas.append(fila)
    return filas


def escribir_csv(ruta, filas):
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    columnas = list(filas[0].keys())
    with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()
        escritor.writerows(filas)
