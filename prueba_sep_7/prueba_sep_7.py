import json
from pathlib import Path

from plano import Plano


def construir_estado_inicial() -> dict:
    return {
        "nodos": [
            {"id": 1, "es_prima": True},
            {"id": 2, "es_prima": False},
            {"id": 3, "es_prima": True},
            {"id": 4, "es_prima": False},
            {"id": 5, "es_prima": True},
            {"id": 6, "es_prima": False},
            {"id": 7, "es_prima": False},
            {"id": 8, "es_prima": False},
            {"id": 9, "es_prima": False},
        ],
        "conexiones": [
            [1, 2], [1, 4], [1, 7],
            [2, 3], [2, 5],
            [3, 6], [3, 8],
            [4, 5], [4, 8],
            [5, 6], [5, 9],
            [6, 7], [7, 8], [8, 9],
            [2, 8], [3, 9], [1, 5], [5, 3],
        ],
        "agentes": [
            {"id": 1, "nodo_inicio": 1},
            {"id": 2, "nodo_inicio": 2},
            {"id": 3, "nodo_inicio": 3},
            {"id": 4, "nodo_inicio": 4},
            {"id": 5, "nodo_inicio": 5},
            {"id": 6, "nodo_inicio": 6},
        ],
    }


def guardar_json(ruta: Path, contenido: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(contenido, f, indent=2)


def mover_y_guardar(
    plano: Plano,
    output_dir: Path,
    prefijo: str,
    indice: int,
    agente_id: int,
    nodo_id: int,
) -> int:
    plano.mover(nodo_id=nodo_id, agente_id=agente_id)
    nombre = f"{prefijo}_{indice:02d}"
    guardar_json(output_dir / f"{nombre}.json", plano.estado_actual_to_dict())
    plano.visualizar_plano(output_path=output_dir / f"{nombre}.png")
    return indice + 1


def ejecutar_prueba(plano: Plano, output_dir: Path) -> None:
    i = 1

    # Nodo prima 1 con múltiples sombras (agentes 2 y 4 entran secuencialmente a 1)
    i = mover_y_guardar(plano, output_dir, "paso", i, agente_id=2, nodo_id=1)
    i = mover_y_guardar(plano, output_dir, "paso", i, agente_id=4, nodo_id=1)

    # Nodo prima 3 también acumula sombras
    i = mover_y_guardar(plano, output_dir, "paso", i, agente_id=6, nodo_id=3)
    i = mover_y_guardar(plano, output_dir, "paso", i, agente_id=4, nodo_id=5)
    i = mover_y_guardar(plano, output_dir, "paso", i, agente_id=4, nodo_id=3)
    i = mover_y_guardar(plano, output_dir, "paso", i, agente_id=2, nodo_id=1)


def main() -> None:
    base = Path(__file__).resolve().parent
    data_path = base / "data" / "init.json"
    output_dir = base / "output"

    init = construir_estado_inicial()
    guardar_json(data_path, init)

    plano = Plano(init)
    guardar_json(output_dir / "estado_00_inicial.json", plano.estado_actual_to_dict())
    plano.visualizar_plano(output_path=output_dir / "estado_00_inicial.png")

    ejecutar_prueba(plano, output_dir)


if __name__ == "__main__":
    main()
