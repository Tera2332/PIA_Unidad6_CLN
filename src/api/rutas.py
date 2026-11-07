"""Rutas REST. Solo traducen HTTP a casos de uso: no contienen reglas de negocio."""
from fastapi import APIRouter, Depends, Request

from src.api.esquemas import (
    AjusteIn,
    CancelarIn,
    ErrorOut,
    Libre,
    PedidoIn,
    PedidoOut,
    PlatilloOut,
    RegistroOut,
)
from src.application.casos_uso import LineaSolicitada
from src.application.dtos import parsear_estado, pedido_a_dict, platillo_a_dict

router = APIRouter()

ERRORES = {
    403: {"model": ErrorOut, "description": "Rol sin permiso"},
    404: {"model": ErrorOut, "description": "No existe el recurso"},
    409: {"model": ErrorOut, "description": "La regla de negocio no se cumple"},
    422: {"model": ErrorOut, "description": "Datos inválidos"},
}


def servicios(request: Request):
    return request.app.state.aplicacion


@router.get("/salud", tags=["Sistema"], summary="Estado del servicio")
def salud():
    return {"estado": "ok"}


@router.post("/pedidos", status_code=201, response_model=PedidoOut, tags=["Pedidos"],
             summary="Registrar un pedido (US-08, US-09)", responses=ERRORES)
def registrar_pedido(datos: PedidoIn, usuario: str = "mesero", casos=Depends(servicios)):
    lineas = [LineaSolicitada(x.platillo_id, x.cantidad, tuple(x.modificaciones))
              for x in datos.lineas]
    pedido = casos.registrar_pedido.ejecutar(
        datos.actor_id, lineas, datos.promocion_activa, datos.autorizado, datos.referencia, usuario)
    return pedido_a_dict(pedido)


@router.get("/pedidos", response_model=list[PedidoOut], tags=["Pedidos"],
            summary="Listar pedidos, opcionalmente por estado (US-01)", responses=ERRORES)
def listar_pedidos(estado: str | None = None, casos=Depends(servicios)):
    return casos.listar_pedidos.ejecutar(parsear_estado(estado))


@router.get("/pedidos/{pedido_id}", response_model=PedidoOut, tags=["Pedidos"],
            summary="Consultar un pedido y su estado (US-07)", responses=ERRORES)
def consultar_pedido(pedido_id: str, casos=Depends(servicios)):
    return casos.consultar_pedido.ejecutar(pedido_id)


@router.get("/pedidos/{pedido_id}/evaluacion", response_model=Libre, tags=["Pedidos"],
            summary="Evaluar las Specifications del pedido", responses=ERRORES)
def evaluar_pedido(pedido_id: str, casos=Depends(servicios)):
    return casos.evaluar_pedido.ejecutar(pedido_id)


@router.post("/pedidos/{pedido_id}/preparacion", response_model=PedidoOut, tags=["Estados"],
             summary="Pasar a «En preparación» (US-06)", responses=ERRORES)
def iniciar_preparacion(pedido_id: str, usuario: str = "cocina", casos=Depends(servicios)):
    return pedido_a_dict(casos.iniciar_preparacion.ejecutar(pedido_id, usuario))


@router.post("/pedidos/{pedido_id}/listo", response_model=PedidoOut, tags=["Estados"],
             summary="Pasar a «Listo» (US-06)", responses=ERRORES)
def marcar_listo(pedido_id: str, usuario: str = "cocina", casos=Depends(servicios)):
    return pedido_a_dict(casos.marcar_listo.ejecutar(pedido_id, usuario))


@router.post("/pedidos/{pedido_id}/entrega", response_model=PedidoOut, tags=["Estados"],
             summary="Registrar la entrega y descontar inventario (US-12)", responses=ERRORES)
def entregar_pedido(pedido_id: str, usuario: str = "repartidor", casos=Depends(servicios)):
    return pedido_a_dict(casos.entregar_pedido.ejecutar(pedido_id, usuario))


@router.post("/pedidos/{pedido_id}/cancelacion", response_model=PedidoOut, tags=["Estados"],
             summary="Cancelar un pedido (US-10)", responses=ERRORES)
def cancelar_pedido(pedido_id: str, datos: CancelarIn, casos=Depends(servicios)):
    pedido = casos.cancelar_pedido.ejecutar(pedido_id, datos.motivo, datos.usuario, datos.rol)
    return pedido_a_dict(pedido)


@router.get("/platillos", response_model=list[PlatilloOut], tags=["Inventario"],
            summary="Consultar disponibilidad de platillos (US-02)")
def consultar_disponibilidad(q: str | None = None, casos=Depends(servicios)):
    return casos.consultar_disponibilidad.ejecutar(q)


@router.post("/inventario/ajustes", response_model=PlatilloOut, tags=["Inventario"],
             summary="Registrar una entrada o una merma (US-03)", responses=ERRORES)
def ajustar_inventario(datos: AjusteIn, casos=Depends(servicios)):
    if datos.tipo == "entrada":
        platillo = casos.ajustar_inventario.entrada(datos.platillo_id, datos.cantidad, datos.usuario)
    else:
        platillo = casos.ajustar_inventario.merma(
            datos.platillo_id, datos.cantidad, datos.motivo, datos.usuario)
    return platillo_a_dict(platillo)


@router.get("/cancelaciones", response_model=list[RegistroOut], tags=["Trazabilidad"],
            summary="Consultar cancelaciones (US-11)")
def consultar_cancelaciones(casos=Depends(servicios)):
    return casos.consultar_cancelaciones.ejecutar()


@router.get("/auditoria", response_model=list[RegistroOut], tags=["Trazabilidad"],
            summary="Historial de acciones, opcionalmente por pedido (US-13)")
def consultar_auditoria(pedido_id: str | None = None, casos=Depends(servicios)):
    return casos.consultar_auditoria.ejecutar(pedido_id)


@router.get("/reportes/resumen", response_model=Libre, tags=["Reportes"],
            summary="Ventas contra inventario (US-14, US-15)")
def reporte_resumen(casos=Depends(servicios)):
    return casos.reporte.ejecutar()
