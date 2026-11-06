"""Control de acceso por roles (ADR-004). Vive en la aplicación: el dominio no conoce sesiones."""
from src.domain.errores import AccesoDenegado
from src.domain.specifications import Contexto, puede_autorizar_cancelacion


class ControlAccesoRBAC:
    def __init__(self):
        self._regla = puede_autorizar_cancelacion()

    def verificar_cancelacion(self, rol):
        if not self._regla.es_satisfecha_por(Contexto(rol=rol)):
            raise AccesoDenegado(
                "Solo el Encargado o el Gerente pueden autorizar la cancelación de un pedido."
            )
