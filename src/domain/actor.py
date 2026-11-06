from dataclasses import dataclass


@dataclass
class Actor:
    id: str
    nombre: str
    es_preferente: bool = False
    activo: bool = True
    ciudad: str = ""
