from datetime import datetime, timezone


def ahora_utc(ahora=None):
    return ahora or datetime.now(timezone.utc)


class RaizAgregado:
    """Base de los Aggregate Roots: acumula Domain Events hasta que se despachan."""

    def __init__(self):
        self._eventos = []

    @property
    def eventos(self):
        return tuple(self._eventos)

    def limpiar_eventos(self):
        self._eventos.clear()

    def _registrar(self, evento):
        self._eventos.append(evento)
