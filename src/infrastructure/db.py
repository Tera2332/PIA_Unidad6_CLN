"""Conexión a la base de datos con SQLAlchemy 2.0."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def crear_motor(url):
    if url.startswith("sqlite"):
        opciones = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url or url in ("sqlite://", "sqlite+pysqlite://"):
            opciones["poolclass"] = StaticPool  # una sola conexión compartida en memoria
        return create_engine(url, **opciones)
    return create_engine(url, pool_pre_ping=True)


def crear_fabrica_sesiones(motor):
    return sessionmaker(bind=motor, expire_on_commit=False)


def crear_tablas(motor):
    from src.infrastructure import modelos  # noqa: F401  (registra las tablas en Base)

    Base.metadata.create_all(motor)


def reiniciar_tablas(motor):
    from src.infrastructure import modelos  # noqa: F401

    Base.metadata.drop_all(motor)
    Base.metadata.create_all(motor)
