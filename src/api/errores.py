"""Traduce los errores del dominio a respuestas HTTP con texto claro para el cliente."""
import logging

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.domain import errores as dominio

logger = logging.getLogger(__name__)

ESTADOS_HTTP = {
    dominio.DatosInvalidos: 422,
    dominio.ReglaNoCumplida: 409,
    dominio.TransicionInvalida: 409,
    dominio.ProductoNoDisponible: 409,
    dominio.StockInsuficiente: 409,
    dominio.AccesoDenegado: 403,
    dominio.NoEncontrado: 404,
}
MENSAJE_GENERICO = "No pudimos procesar tu solicitud. Inténtalo de nuevo más tarde."


def registrar_manejadores(app):
    @app.exception_handler(dominio.ErrorDeNegocio)
    async def _negocio(request, error):
        estado = ESTADOS_HTTP.get(type(error), 400)
        return JSONResponse(status_code=estado, content={"detail": str(error), "codigo": error.codigo})

    @app.exception_handler(RequestValidationError)
    async def _validacion(request, error):
        campos = []
        for detalle in error.errors():
            ubicacion = detalle.get("loc") or ("solicitud",)
            nombre = str(ubicacion[-1])
            if nombre not in campos:
                campos.append(nombre)
        mensaje = ("Los datos enviados están incompletos o no son válidos. Revisa: "
                   + ", ".join(campos) + ".")
        return JSONResponse(status_code=422, content={"detail": mensaje, "codigo": "DATOS_INVALIDOS"})

    @app.exception_handler(Exception)
    async def _inesperado(request, error):
        logger.exception("Error inesperado en %s", request.url.path)
        return JSONResponse(status_code=500,
                            content={"detail": MENSAJE_GENERICO, "codigo": "ERROR_INTERNO"})
