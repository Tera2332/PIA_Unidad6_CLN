"""Punto de entrada: `uvicorn src.api.main:crear_app --factory`."""
import logging

from fastapi import FastAPI

from src.api.errores import registrar_manejadores
from src.api.rutas import router
from src.application.contenedor import construir_aplicacion
from src.infrastructure.config import Configuracion
from src.infrastructure.db import crear_fabrica_sesiones, crear_motor, crear_tablas
from src.infrastructure.repositorios_sql import SqlUnitOfWork
from src.infrastructure.seed import cargar_datos

logger = logging.getLogger(__name__)

DESCRIPCION = (
    "API REST de **Sazón Urbano**: registro de pedidos, máquina de estados, control de inventario, "
    "cancelaciones autorizadas y trazabilidad. Los errores se devuelven siempre como texto claro "
    "en el campo `detail`."
)


def crear_app(uow_factory=None, configuracion=None):
    config = configuracion or Configuracion.desde_entorno()
    if uow_factory is None:
        motor = crear_motor(config.database_url)
        crear_tablas(motor)
        fabrica = crear_fabrica_sesiones(motor)

        def crear_uow():
            return SqlUnitOfWork(fabrica)

        uow_factory = crear_uow
        if config.seed_on_start:
            resultado = cargar_datos(uow_factory, config.data_dir, config.stock_critico)
            logger.info("Carga inicial de datos: %s", resultado)
    app = FastAPI(title="Sazón Urbano – API de pedidos", version="1.0.0", description=DESCRIPCION)
    app.state.aplicacion = construir_aplicacion(uow_factory)
    app.include_router(router)
    registrar_manejadores(app)
    return app
