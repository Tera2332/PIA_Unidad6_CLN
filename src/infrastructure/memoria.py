"""Implementación en memoria de los puertos: se usa en las pruebas unitarias y en los scripts."""
import copy


class AlmacenMemoria:
    def __init__(self):
        self.actores = {}
        self.platillos = {}
        self.pedidos = {}
        self.auditoria = []

    def instantanea(self):
        return copy.deepcopy((self.actores, self.platillos, self.pedidos, self.auditoria))

    def restaurar(self, instantanea):
        self.actores, self.platillos, self.pedidos, self.auditoria = instantanea


class _PedidosMemoria:
    def __init__(self, almacen):
        self._a = almacen

    def obtener(self, id):
        return self._a.pedidos.get(id)

    def guardar(self, pedido):
        self._a.pedidos[pedido.id] = pedido

    def listar(self, estado=None):
        pedidos = sorted(self._a.pedidos.values(), key=lambda p: p.id)
        return [p for p in pedidos if estado is None or p.estado == estado]


class _PlatillosMemoria:
    def __init__(self, almacen):
        self._a = almacen

    def obtener(self, id):
        return self._a.platillos.get(id)

    def obtener_varios(self, ids):
        return {i: self._a.platillos[i] for i in ids if i in self._a.platillos}

    def listar(self):
        return sorted(self._a.platillos.values(), key=lambda p: p.id)

    def guardar(self, platillo):
        self._a.platillos[platillo.id] = platillo


class _ActoresMemoria:
    def __init__(self, almacen):
        self._a = almacen

    def obtener(self, id):
        return self._a.actores.get(id)

    def listar(self):
        return sorted(self._a.actores.values(), key=lambda x: x.id)

    def guardar(self, actor):
        self._a.actores[actor.id] = actor


class _AuditoriaMemoria:
    def __init__(self, almacen):
        self._a = almacen

    def agregar(self, registro):
        self._a.auditoria.append(registro)

    def listar(self, pedido_id=None, accion=None):
        return [r for r in self._a.auditoria
                if (pedido_id is None or r.pedido_id == pedido_id)
                and (accion is None or r.accion == accion)]


class MemoriaUnitOfWork:
    """Si el bloque termina sin commit (o con error) se restaura el estado anterior."""

    def __init__(self, almacen):
        self._almacen = almacen
        self._confirmado = False
        self.pedidos = _PedidosMemoria(almacen)
        self.platillos = _PlatillosMemoria(almacen)
        self.actores = _ActoresMemoria(almacen)
        self.auditoria = _AuditoriaMemoria(almacen)

    def __enter__(self):
        self._instantanea = self._almacen.instantanea()
        self._confirmado = False
        return self

    def __exit__(self, tipo, error, traza):
        if not self._confirmado:
            self._almacen.restaurar(self._instantanea)
        return False

    def commit(self):
        self._confirmado = True


def fabrica_memoria(almacen):
    def crear():
        return MemoriaUnitOfWork(almacen)

    return crear
