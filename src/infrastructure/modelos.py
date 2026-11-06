"""Modelos de tabla (ORM). Son detalles de infraestructura: el dominio no los conoce."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db import Base


class ActorRow(Base):
    __tablename__ = "actores"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    es_preferente: Mapped[bool] = mapped_column(Boolean, default=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    ciudad: Mapped[str] = mapped_column(String(80), default="")


class PlatilloRow(Base):
    __tablename__ = "platillos"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    descripcion: Mapped[str] = mapped_column(String(160))
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    stock: Mapped[int] = mapped_column(Integer)
    habilitado: Mapped[bool] = mapped_column(Boolean, default=True)
    stock_critico: Mapped[int] = mapped_column(Integer, default=5)


class PedidoRow(Base):
    __tablename__ = "pedidos"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(40), ForeignKey("actores.id"))
    estado: Mapped[str] = mapped_column(String(20))
    fecha_solicitud: Mapped[date] = mapped_column(Date)
    promocion_activa: Mapped[bool] = mapped_column(Boolean, default=False)
    autorizado: Mapped[bool] = mapped_column(Boolean, default=True)
    referencia: Mapped[str | None] = mapped_column(String(80), nullable=True)
    motivo_cancelacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    lineas: Mapped[list["LineaRow"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan", order_by="LineaRow.id")


class LineaRow(Base):
    __tablename__ = "lineas_pedido"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pedido_id: Mapped[str] = mapped_column(String(40), ForeignKey("pedidos.id"))
    platillo_id: Mapped[str] = mapped_column(String(40), ForeignKey("platillos.id"))
    cantidad: Mapped[int] = mapped_column(Integer)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    modificaciones: Mapped[str] = mapped_column(Text, default="[]")
    pedido: Mapped["PedidoRow"] = relationship(back_populates="lineas")


class AuditoriaRow(Base):
    """Tabla de solo anexado (ADR-005)."""

    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pedido_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    accion: Mapped[str] = mapped_column(String(60))
    usuario: Mapped[str] = mapped_column(String(80))
    rol: Mapped[str] = mapped_column(String(40), default="")
    detalle: Mapped[str] = mapped_column(Text, default="")
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True))
