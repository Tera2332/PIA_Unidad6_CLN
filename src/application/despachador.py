"""Despachador de eventos en proceso: entrega los Domain Events a sus manejadores tras el commit."""
import logging

logger = logging.getLogger(__name__)


class DespachadorEventos:
    def __init__(self):
        self._por_tipo = {}
        self._globales = []
        self.errores = []

    def suscribir(self, tipo_evento, manejador):
        self._por_tipo.setdefault(tipo_evento, []).append(manejador)

    def suscribir_todos(self, manejador):
        self._globales.append(manejador)

    def despachar(self, eventos):
        for evento in eventos:
            for manejador in self._globales + self._por_tipo.get(type(evento), []):
                try:
                    manejador(evento)
                except Exception as error:  # noqa: BLE001
                    # El commit ya ocurrió: una falla de un manejador no revierte el pedido.
                    self.errores.append((evento, error))
                    logger.exception("Falló el manejador de %s", evento.nombre)
