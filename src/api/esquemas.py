"""Esquemas Pydantic de la API (entrada y salida). Alimentan la documentación OpenAPI."""
from typing import Any, Literal

from pydantic import BaseModel, Field


class LineaIn(BaseModel):
    platillo_id: str = Field(..., examples=["PED-P001"], description="Identificador del platillo")
    cantidad: int = Field(..., examples=[2], description="Unidades solicitadas (entero mayor a cero)")
    modificaciones: list[str] = Field(default_factory=list, examples=[["sin cebolla"]])


class PedidoIn(BaseModel):
    actor_id: str = Field(..., examples=["PED-C001"], description="Cliente que hace el pedido")
    lineas: list[LineaIn]
    promocion_activa: bool = False
    autorizado: bool = True
    referencia: str | None = None


class CancelarIn(BaseModel):
    motivo: str = Field(..., examples=["El cliente ya no quiso esperar"])
    usuario: str = Field(..., examples=["encargado1"])
    rol: str = Field(..., examples=["Encargado"], description="Solo Encargado o Gerente pueden cancelar")


class AjusteIn(BaseModel):
    platillo_id: str = Field(..., examples=["PED-P001"])
    tipo: Literal["entrada", "merma"]
    cantidad: int = Field(..., examples=[5])
    motivo: str = Field("", description="Obligatorio cuando el tipo es merma")
    usuario: str = "encargado"


class LineaOut(BaseModel):
    platillo_id: str
    cantidad: int
    precio_unitario: str
    subtotal: str
    modificaciones: list[str]


class PedidoOut(BaseModel):
    id: str
    actor_id: str
    estado: str
    total: str
    moneda: str
    fecha_solicitud: str
    promocion_activa: bool
    autorizado: bool
    referencia: str | None = None
    motivo_cancelacion: str | None = None
    lineas: list[LineaOut]


class PlatilloOut(BaseModel):
    id: str
    descripcion: str
    precio: str
    stock: int
    habilitado: bool
    disponible: bool
    stock_critico: bool


class RegistroOut(BaseModel):
    pedido_id: str | None = None
    accion: str
    usuario: str
    rol: str
    detalle: str
    fecha: str


class ErrorOut(BaseModel):
    detail: str
    codigo: str | None = None


Libre = dict[str, Any]
