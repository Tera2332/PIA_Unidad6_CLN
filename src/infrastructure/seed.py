"""Carga el paquete de datos del PIA (CSV) a través de los puertos de persistencia."""
import csv
from datetime import date
from pathlib import Path

from src.domain.actor import Actor
from src.domain.catalogo import Platillo
from src.domain.pedido import LineaPedido, Pedido
from src.domain.valores import Dinero, EstadoPedido


def leer_csv(ruta):
    with open(ruta, newline="", encoding="utf-8-sig") as archivo:
        return list(csv.DictReader(archivo))


def cargar_datos(uow_factory, data_dir="data", stock_critico=5):
    """Idempotente: si ya hay actores no vuelve a cargar. CREADO del paquete = Registrado."""
    base = Path(data_dir)
    with uow_factory() as uow:
        if uow.actores.listar():
            return {"cargado": False}
        for fila in leer_csv(base / "actores.csv"):
            uow.actores.guardar(Actor(
                fila["actor_id"], fila["nombre"], fila["es_preferente"] == "1",
                fila["activo"] == "1", fila["ciudad"]))
        catalogo = {}
        for fila in leer_csv(base / "catalogo.csv"):
            platillo = Platillo(
                fila["recurso_id"], fila["descripcion"], Dinero(fila["precio_mxn"]),
                int(fila["capacidad_o_stock"]), fila["habilitado"] == "1", stock_critico)
            catalogo[platillo.id] = platillo
            uow.platillos.guardar(platillo)
        lineas = {}
        for fila in leer_csv(base / "detalle_operaciones.csv"):
            platillo = catalogo[fila["recurso_id"]]
            lineas.setdefault(fila["operacion_id"], []).append(
                LineaPedido(platillo.id, int(fila["cantidad"]), platillo.precio))
        operaciones = leer_csv(base / "operaciones.csv")
        for fila in operaciones:
            uow.pedidos.guardar(Pedido.reconstruir(
                fila["operacion_id"], fila["actor_id"], lineas.get(fila["operacion_id"], []),
                date.fromisoformat(fila["fecha_solicitud"]), fila["promocion_activa"] == "1",
                fila["autorizado"] == "1", fila["referencia"], EstadoPedido.REGISTRADO))
        uow.commit()
        return {"cargado": True, "actores": len(uow.actores.listar()),
                "platillos": len(catalogo), "pedidos": len(operaciones)}
