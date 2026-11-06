"""Objetos de valor del dominio."""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import Enum

from src.domain.errores import DatosInvalidos

CENTAVOS = Decimal("0.01")


@dataclass(frozen=True, order=True)
class Dinero:
    """Importe en pesos mexicanos, siempre con Decimal y dos decimales."""

    monto: Decimal
    moneda: str = "MXN"

    def __post_init__(self):
        try:
            valor = Decimal(str(self.monto))
            negativo = valor < 0
        except InvalidOperation:
            raise DatosInvalidos("El importe no es válido.") from None
        if negativo:
            raise DatosInvalidos("El importe no puede ser negativo.")
        object.__setattr__(self, "monto", valor.quantize(CENTAVOS, rounding=ROUND_HALF_UP))

    @classmethod
    def cero(cls):
        return cls(Decimal("0"))

    def __add__(self, otro):
        return Dinero(self.monto + otro.monto, self.moneda)

    def por(self, cantidad):
        return Dinero(self.monto * cantidad, self.moneda)

    def __str__(self):
        return f"{self.monto:.2f}"


class EstadoPedido(str, Enum):
    REGISTRADO = "Registrado"
    EN_PREPARACION = "En preparación"
    LISTO = "Listo"
    ENTREGADO = "Entregado"
    CANCELADO = "Cancelado"
