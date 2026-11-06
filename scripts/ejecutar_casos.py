"""Ejecuta los 120 casos y las 20 transiciones del paquete y guarda las evidencias en evidencias/."""
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.infrastructure.evidencias import (  # noqa: E402
    ejecutar_casos,
    ejecutar_transiciones,
    escribir_csv,
)

if __name__ == "__main__":
    data = RAIZ / "data"
    casos = ejecutar_casos(data)
    transiciones = ejecutar_transiciones(data)
    escribir_csv(RAIZ / "evidencias" / "casos_prueba_resultados.csv", casos)
    escribir_csv(RAIZ / "evidencias" / "transiciones_prueba_resultados.csv", transiciones)
    print("Casos:", len(casos), dict(Counter(f["resultado_alumno"] for f in casos)))
    print("Transiciones:", len(transiciones), dict(Counter(f["resultado_alumno"] for f in transiciones)))
