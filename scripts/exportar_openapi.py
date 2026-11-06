"""Genera docs/api/openapi.json a partir de la aplicación (sin necesidad de base de datos)."""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.api.main import crear_app  # noqa: E402
from src.infrastructure.memoria import AlmacenMemoria, fabrica_memoria  # noqa: E402

if __name__ == "__main__":
    app = crear_app(uow_factory=fabrica_memoria(AlmacenMemoria()))
    destino = RAIZ / "docs" / "api" / "openapi.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
    print("OpenAPI generado en", destino)
