import os

from src.infrastructure.config import Configuracion, normalizar_url


def test_normaliza_las_urls_de_postgres():
    assert normalizar_url("postgres://u:p@h/db") == "postgresql+psycopg2://u:p@h/db"
    assert normalizar_url("postgresql://u:p@h/db") == "postgresql+psycopg2://u:p@h/db"
    assert normalizar_url("sqlite:///x.db") == "sqlite:///x.db"


def test_configuracion_desde_variables_de_entorno():
    anteriores = {k: os.environ.get(k) for k in ("DATABASE_URL", "STOCK_CRITICO", "SEED_ON_START")}
    try:
        os.environ.update({"DATABASE_URL": "postgres://a:b@c/d", "STOCK_CRITICO": "8",
                           "SEED_ON_START": "TRUE"})
        config = Configuracion.desde_entorno()
        assert config.database_url == "postgresql+psycopg2://a:b@c/d"
        assert config.stock_critico == 8 and config.seed_on_start is True
        os.environ["SEED_ON_START"] = "no"
        assert Configuracion.desde_entorno().seed_on_start is False
    finally:
        for clave, valor in anteriores.items():
            if valor is None:
                os.environ.pop(clave, None)
            else:
                os.environ[clave] = valor
