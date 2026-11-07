from datetime import datetime, timezone

from src.application.casos_uso import LineaSolicitada
from src.application.contenedor import construir_aplicacion
from src.domain.actor import Actor
from src.domain.catalogo import Platillo
from src.domain.valores import Dinero
from src.infrastructure.memoria import AlmacenMemoria, fabrica_memoria

AHORA = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)


def entorno():
    almacen = AlmacenMemoria()
    almacen.actores.update({
        "C1": Actor("C1", "Ana", False, True, "Monterrey"),
        "C2": Actor("C2", "Beto", True, True, "Monterrey"),
        "C3": Actor("C3", "Inactivo", False, False, "Monterrey"),
    })
    almacen.platillos.update({
        "P1": Platillo("P1", "Taco", Dinero("100"), 20, True, 5),
        "P2": Platillo("P2", "Sopa", Dinero("200"), 6, True, 5),
        "P3": Platillo("P3", "Agotado", Dinero("50"), 0, True, 5),
        "P4": Platillo("P4", "Deshabilitado", Dinero("80"), 10, False, 5),
    })
    contador = iter(range(1, 1000))

    def generador():
        return f"PED-{next(contador):03d}"

    return construir_aplicacion(fabrica_memoria(almacen), generador), almacen


def lineas(*pares):
    return [LineaSolicitada(p, c) for p, c in pares]
