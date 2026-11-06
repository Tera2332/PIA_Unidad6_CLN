"""Aggregate Root Platillo: existencias del catálogo (el inventario se modela por platillo)."""
from src.domain.base import RaizAgregado, ahora_utc
from src.domain.errores import DatosInvalidos, ProductoNoDisponible, StockInsuficiente
from src.domain.eventos import InventarioAjustado, StockCriticoAlcanzado

MENSAJE_AGOTADO = "Producto no disponible por falta de ingredientes"


class Platillo(RaizAgregado):
    def __init__(self, id, descripcion, precio, stock, habilitado=True, stock_critico=5):
        super().__init__()
        self.id = id
        self.descripcion = descripcion
        self.precio = precio
        self.stock = stock
        self.habilitado = habilitado
        self.stock_critico = stock_critico

    @property
    def disponible(self):
        return self.habilitado and self.stock > 0

    @property
    def en_stock_critico(self):
        return self.stock <= self.stock_critico

    def verificar_disponible(self, cantidad):
        if not self.disponible:
            raise ProductoNoDisponible(MENSAJE_AGOTADO)
        if cantidad > self.stock:
            raise StockInsuficiente(f"Solo quedan {self.stock} unidades de «{self.descripcion}».")

    def _restar(self, cantidad, usuario, ahora):
        if cantidad <= 0:
            raise DatosInvalidos("La cantidad debe ser mayor a cero.")
        if cantidad > self.stock:
            raise StockInsuficiente(
                f"No hay suficiente existencia de «{self.descripcion}» (quedan {self.stock})."
            )
        self.stock -= cantidad
        if self.en_stock_critico:
            self._registrar(StockCriticoAlcanzado(self.id, self.stock, usuario, ahora))

    def descontar(self, cantidad, usuario="sistema", ahora=None):
        self._restar(cantidad, usuario, ahora_utc(ahora))

    def registrar_entrada(self, cantidad, usuario="sistema", ahora=None):
        if cantidad <= 0:
            raise DatosInvalidos("La cantidad debe ser mayor a cero.")
        self.stock += cantidad
        self._registrar(InventarioAjustado(self.id, "entrada", cantidad, "", usuario, ahora_utc(ahora)))

    def registrar_merma(self, cantidad, motivo, usuario="sistema", ahora=None):
        motivo = (motivo or "").strip()
        if not motivo:
            raise DatosInvalidos("Para registrar una merma debes indicar el motivo.")
        ahora = ahora_utc(ahora)
        self._restar(cantidad, usuario, ahora)
        self._registrar(InventarioAjustado(self.id, "merma", cantidad, motivo, usuario, ahora))
