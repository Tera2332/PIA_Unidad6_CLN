import os

import pytest
from fastapi.testclient import TestClient
from src.api.main import crear_app
from src.infrastructure.db import crear_fabrica_sesiones, crear_motor, reiniciar_tablas
from src.infrastructure.repositorios_sql import SqlUnitOfWork
from src.infrastructure.seed import cargar_datos

URL_PRUEBAS = os.getenv("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")


@pytest.fixture
def uow_factory():
    """Base de datos limpia por prueba (SQLite en memoria, o PostgreSQL con TEST_DATABASE_URL)."""
    motor = crear_motor(URL_PRUEBAS)
    reiniciar_tablas(motor)
    fabrica = crear_fabrica_sesiones(motor)

    def crear():
        return SqlUnitOfWork(fabrica)

    yield crear
    motor.dispose()


@pytest.fixture
def uow_sembrada(uow_factory):
    cargar_datos(uow_factory, "data")
    return uow_factory


@pytest.fixture
def cliente(uow_sembrada):
    return TestClient(crear_app(uow_factory=uow_sembrada))
