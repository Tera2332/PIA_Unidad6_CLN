"""Configuración leída de variables de entorno (ver .env.example). Nada de secretos en el código."""
import os
from dataclasses import dataclass


def normalizar_url(url):
    """Render y otros proveedores entregan postgres:// o postgresql://; SQLAlchemy necesita el driver."""
    for prefijo in ("postgres://", "postgresql://"):
        if url.startswith(prefijo):
            return "postgresql+psycopg2://" + url[len(prefijo):]
    return url


@dataclass(frozen=True)
class Configuracion:
    database_url: str = "sqlite:///./sazon.db"
    stock_critico: int = 5
    seed_on_start: bool = False
    data_dir: str = "data"

    @classmethod
    def desde_entorno(cls):
        return cls(
            database_url=normalizar_url(os.getenv("DATABASE_URL", "sqlite:///./sazon.db")),
            stock_critico=int(os.getenv("STOCK_CRITICO", "5")),
            seed_on_start=os.getenv("SEED_ON_START", "false").strip().lower()
            in ("1", "true", "si", "sí", "yes"),
            data_dir=os.getenv("DATA_DIR", "data"),
        )
