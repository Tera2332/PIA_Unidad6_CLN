"""Composición de la aplicación: conecta casos de uso, despachador y manejadores de eventos."""
from dataclasses import dataclass

from src.application.casos_uso import (
    AjustarInventario,
    CancelarPedido,
    ConsultarAuditoria,
    ConsultarCancelaciones,
    ConsultarClientes,
    ConsultarDisponibilidad,
    ConsultarPedido,
    EntregarPedido,
    EvaluarPedido,
    IniciarPreparacion,
    ListarPedidos,
    MarcarListo,
    RegistrarPedido,
    ReporteResumen,
    generar_id_pedido,
)
from src.application.despachador import DespachadorEventos
from src.application.handlers import DescuentoDeInventario, RegistroDeAuditoria
from src.application.seguridad import ControlAccesoRBAC
from src.domain.eventos import PedidoEntregado


@dataclass
class Aplicacion:
    despachador: object
    registrar_pedido: object
    iniciar_preparacion: object
    marcar_listo: object
    entregar_pedido: object
    cancelar_pedido: object
    ajustar_inventario: object
    consultar_pedido: object
    listar_pedidos: object
    evaluar_pedido: object
    consultar_disponibilidad: object
    consultar_cancelaciones: object
    consultar_clientes: object
    consultar_auditoria: object
    reporte: object


def construir_aplicacion(uow_factory, generador_id=generar_id_pedido):
    despachador = DespachadorEventos()
    despachador.suscribir_todos(RegistroDeAuditoria(uow_factory))
    despachador.suscribir(PedidoEntregado, DescuentoDeInventario(uow_factory, despachador))
    acceso = ControlAccesoRBAC()
    return Aplicacion(
        despachador=despachador,
        registrar_pedido=RegistrarPedido(uow_factory, despachador, generador_id),
        iniciar_preparacion=IniciarPreparacion(uow_factory, despachador),
        marcar_listo=MarcarListo(uow_factory, despachador),
        entregar_pedido=EntregarPedido(uow_factory, despachador),
        cancelar_pedido=CancelarPedido(uow_factory, despachador, acceso),
        ajustar_inventario=AjustarInventario(uow_factory, despachador),
        consultar_pedido=ConsultarPedido(uow_factory),
        listar_pedidos=ListarPedidos(uow_factory),
        evaluar_pedido=EvaluarPedido(uow_factory),
        consultar_disponibilidad=ConsultarDisponibilidad(uow_factory),
        consultar_cancelaciones=ConsultarCancelaciones(uow_factory),
        consultar_clientes=ConsultarClientes(uow_factory),
        consultar_auditoria=ConsultarAuditoria(uow_factory),
        reporte=ReporteResumen(uow_factory),
    )
