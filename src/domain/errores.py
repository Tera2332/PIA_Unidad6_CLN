"""Errores del dominio. str(error) siempre es texto claro, apto para mostrarse al cliente."""


class ErrorDeNegocio(Exception):
    codigo = "ERROR_DE_NEGOCIO"


class DatosInvalidos(ErrorDeNegocio):
    codigo = "DATOS_INVALIDOS"


class ReglaNoCumplida(ErrorDeNegocio):
    codigo = "REGLA_NO_CUMPLIDA"


class TransicionInvalida(ErrorDeNegocio):
    codigo = "TRANSICION_INVALIDA"


class ProductoNoDisponible(ErrorDeNegocio):
    codigo = "PRODUCTO_NO_DISPONIBLE"


class StockInsuficiente(ErrorDeNegocio):
    codigo = "STOCK_INSUFICIENTE"


class AccesoDenegado(ErrorDeNegocio):
    codigo = "ACCESO_DENEGADO"


class NoEncontrado(ErrorDeNegocio):
    codigo = "NO_ENCONTRADO"
