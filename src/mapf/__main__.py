from __future__ import annotations

import json
from pathlib import Path

from mapf.config import cargar_config
from mapf.plano import Plano


def main() -> None:
    """Corre una demostración: carga un plano, mueve agentes y guarda capturas."""
    config = cargar_config()
    init_path = Path(config['datos']['init_path'])
    output_dir = Path(config['salida']['directorio'])
    output_dir.mkdir(parents=True, exist_ok=True)

    with init_path.open('r', encoding='utf-8') as f:
        init = json.load(f)

    plano = Plano(init, config=config)
    print('Plano inicial cargado.')
    for agente in plano.agentes.values():
        print(f'  Agente {agente.id}: nodo {agente.posicion.id}')

    plano.visualizar_plano(output_path=output_dir / 'estado_inicial.png')

    print('\n--- Movimientos legales ---')
    for agente_id, nodo_id in [(3, 2), (2, 6)]:
        try:
            plano.mover(nodo_id, agente_id)
            print(f'  Movimiento legal: agente {agente_id} -> nodo {nodo_id}')
        except Exception as exc:
            print(f'  Movimiento fallido: agente {agente_id} -> nodo {nodo_id}: {exc}')

    plano.visualizar_plano(output_path=output_dir / 'estado_1.png')

    print('\n--- Movimientos ilegales ---')
    for agente_id, nodo_id in [(1, 4), (2, 1), (2, 4)]:
        try:
            plano.mover(nodo_id, agente_id)
            print(f'  Movimiento ilegal permitido (inesperado): agente {agente_id} -> nodo {nodo_id}')
        except Exception as exc:
            print(f'  Movimiento ilegal rechazado: agente {agente_id} -> nodo {nodo_id}: {exc}')

    plano.visualizar_plano(output_path=output_dir / 'estado_final.png')
    print(f'Salida guardada en: {output_dir}')


if __name__ == '__main__':
    main()
