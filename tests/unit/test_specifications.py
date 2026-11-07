import pytest
from src.domain.actor import Actor
from src.domain.catalogo import Platillo
from src.domain.pedido import LineaPedido, Pedido
from src.domain.specifications import (
    ActorActivo,
    Contexto,
    ExistenciasSuficientes,
    PedidoAutorizado,
    PromocionActiva,
    RolEn,
    TotalMinimo,
    beneficio_referencia,
    puede_autorizar_cancelacion,
    puede_procesarse,
    puede_venderse,
)
from src.domain.valores import Dinero


def _ctx(total="2000", preferente=True, activo=True, promo=False, autorizado=True, lineas=True):
    items = [LineaPedido("P1", 1, Dinero(total))] if lineas else []
    pedido = Pedido.reconstruir("PED-1", "C1", items, None, promo, autorizado)
    return Contexto(pedido=pedido, actor=Actor("C1", "Ana", preferente, activo))


def test_hojas_individuales():
    assert ActorActivo().es_satisfecha_por(_ctx())
    assert not ActorActivo().es_satisfecha_por(_ctx(activo=False))
    assert not ActorActivo().es_satisfecha_por(Contexto(pedido=None, actor=None))
    assert PedidoAutorizado().es_satisfecha_por(_ctx())
    assert not PedidoAutorizado().es_satisfecha_por(_ctx(autorizado=False))
    assert PromocionActiva().es_satisfecha_por(_ctx(promo=True))


def test_puede_procesarse_es_un_and_de_tres_reglas():
    assert puede_procesarse().es_satisfecha_por(_ctx())
    regla = puede_procesarse()
    contexto = _ctx(activo=False, autorizado=False, lineas=False)
    assert not regla.es_satisfecha_por(contexto)
    assert regla.motivos_de_falla(contexto) == [
        "el cliente no está activo", "el pedido no tiene productos",
        "el pedido no está autorizado"]


@pytest.mark.parametrize("total, esperado", [("1499.99", False), ("1500", True), ("1500.01", True)])
def test_beneficio_en_el_limite_de_1500(total, esperado):
    assert beneficio_referencia().es_satisfecha_por(_ctx(total=total)) is esperado


def test_beneficio_usa_not_promocion_y_and_preferente():
    assert not beneficio_referencia().es_satisfecha_por(_ctx(promo=True))
    assert not beneficio_referencia().es_satisfecha_por(_ctx(preferente=False))
    assert beneficio_referencia().motivos_de_falla(_ctx(promo=True)) == [
        "el pedido ya tiene una promoción activa"]
    assert "el total es menor a 1500.00 MXN" in beneficio_referencia().motivos_de_falla(
        _ctx(total="100", preferente=False))


def test_or_de_roles_para_cancelar():
    regla = puede_autorizar_cancelacion()
    assert regla.es_satisfecha_por(Contexto(rol="Encargado"))
    assert regla.es_satisfecha_por(Contexto(rol="Gerente"))
    assert not regla.es_satisfecha_por(Contexto(rol="Mesero"))
    assert regla.motivos_de_falla(Contexto(rol="Mesero")) != []
    assert regla.motivos_de_falla(Contexto(rol="Gerente")) == []


def test_operadores_y_metodos_son_equivalentes():
    a, b = ActorActivo(), PedidoAutorizado()
    contexto = _ctx(autorizado=False)
    assert (a & b).es_satisfecha_por(contexto) == a.y(b).es_satisfecha_por(contexto) is False
    assert (a | b).es_satisfecha_por(contexto) == a.o(b).es_satisfecha_por(contexto) is True
    assert (~b).es_satisfecha_por(contexto) == b.no().es_satisfecha_por(contexto) is True


def test_explicar_lista_cada_condicion():
    explicacion = beneficio_referencia().explicar(_ctx(promo=True))
    assert len(explicacion) == 3
    assert [ok for _, ok in explicacion] == [True, True, False]


def test_descripciones_compuestas_y_total_minimo():
    assert "Y" in puede_procesarse().descripcion
    assert "O" in puede_autorizar_cancelacion().descripcion
    assert beneficio_referencia().descripcion.startswith("((El cliente es preferente")
    assert TotalMinimo(Dinero("10")).es_satisfecha_por(_ctx(total="10"))
    assert RolEn("A", "B").descripcion == "El rol es A o B"


def test_existencias_suficientes_y_puede_venderse():
    catalogo = {"P1": Platillo("P1", "Taco", Dinero("100"), 2, True, 5)}
    contexto = _ctx(total="100")
    contexto.catalogo = catalogo
    assert ExistenciasSuficientes().es_satisfecha_por(contexto)
    assert puede_venderse().es_satisfecha_por(contexto)
    catalogo["P1"].stock = 0
    assert not puede_venderse().es_satisfecha_por(contexto)
    contexto.catalogo = {}
    assert not ExistenciasSuficientes().es_satisfecha_por(contexto)
    catalogo["P1"].stock, catalogo["P1"].habilitado = 5, False
    contexto.catalogo = catalogo
    assert not ExistenciasSuficientes().es_satisfecha_por(contexto)
