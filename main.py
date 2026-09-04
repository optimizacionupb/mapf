import json
from pathlib import Path

from plano import Plano


def main():
    base = Path(__file__).resolve().parent
    init_path = base / 'data' / 'init.json'
    temp_dir = base / 'temp'
    temp_dir.mkdir(exist_ok=True)

    with init_path.open('r', encoding='utf-8') as f:
        init = json.load(f)

    plano = Plano(init)
    print('Plano inicial cargado.')
    for agente in plano.agentes.values():
        print(f'  Agente {agente.id}: nodo {agente.posicion.id}')

    initial_snapshot = temp_dir / 'estado_inicial.png'
    plano.visualizar_plano(output_path=initial_snapshot)
    print(f'Visualización inicial guardada en: {initial_snapshot}')

    print('\n--- Movimientos legales ---')
    for agente_id, nodo_id in [(3, 2), (2, 6)]:
        try:
            plano.mover(nodo_id, agente_id)
            print(f'  Movimiento legal: agente {agente_id} -> nodo {nodo_id}')
        except Exception as exc:
            print(f'  Movimiento legal fallido: agente {agente_id} -> nodo {nodo_id}: {type(exc).__name__}: {exc}')

    estado_1 = plano.estado_actual_to_dict()
    estado_1_path = temp_dir / 'estado_1.json'
    with estado_1_path.open('w', encoding='utf-8') as f:
        json.dump(estado_1, f, indent=2)
    print(f'JSON del estado 1 guardado en: {estado_1_path}')

    estado_1_plot = temp_dir / 'estado_1.png'
    plano.visualizar_plano(output_path=estado_1_plot)
    print(f'Visualización del estado 1 guardada en: {estado_1_plot}')

    print('\n--- Movimientos ilegales ---')
    for agente_id, nodo_id in [(1, 4), (2, 1), (2, 4)]:
        try:
            plano.mover(nodo_id, agente_id)
            print(f'  Movimiento ilegal permitido: agente {agente_id} -> nodo {nodo_id}')
        except Exception as exc:
            print(f'  Movimiento ilegal rechazado: agente {agente_id} -> nodo {nodo_id}: {type(exc).__name__}: {exc}')

    estado_2 = plano.estado_actual_to_dict()
    estado_2_path = temp_dir / 'estado_2.json'
    with estado_2_path.open('w', encoding='utf-8') as f:
        json.dump(estado_2, f, indent=2)
    print(f'JSON del estado final guardado en: {estado_2_path}')

    estado_2_plot = temp_dir / 'estado_2.png'
    plano.visualizar_plano(output_path=estado_2_plot)
    print(f'Visualización del estado final guardada en: {estado_2_plot}')

    print('\n--- Movimientos legales ---')
    for agente_id, nodo_id in [(1, 1), (1, 5), (3,1)]:
        try:
            plano.mover(nodo_id, agente_id)
            print(f'  Movimiento legal: agente {agente_id} -> nodo {nodo_id}')
        except Exception as exc:
            print(f'  Movimiento legal fallido: agente {agente_id} -> nodo {nodo_id}: {type(exc).__name__}: {exc}')

    estado_3 = plano.estado_actual_to_dict()
    estado_3_path = temp_dir / 'estado_3.json'
    with estado_3_path.open('w', encoding='utf-8') as f:
        json.dump(estado_3, f, indent=2)
    print(f'JSON del estado 3 guardado en: {estado_3_path}')

    estado_3_plot = temp_dir / 'estado_3.png'
    plano.visualizar_plano(output_path=estado_3_plot)
    print(f'Visualización del estado 3 guardada en: {estado_3_plot}')

    print('\n--- Movimientos legales ---')
    for agente_id, nodo_id in [(2, 2), (2, 1)]:
        try:
            plano.mover(nodo_id, agente_id)
            print(f'  Movimiento legal: agente {agente_id} -> nodo {nodo_id}')
        except Exception as exc:
            print(f'  Movimiento legal fallido: agente {agente_id} -> nodo {nodo_id}: {type(exc).__name__}: {exc}')

    estado_4 = plano.estado_actual_to_dict()
    estado_4_path = temp_dir / 'estado_4.json'
    with estado_4_path.open('w', encoding='utf-8') as f:
        json.dump(estado_4, f, indent=2)
    print(f'JSON del estado 4 guardado en: {estado_4_path}')

    estado_4_plot = temp_dir / 'estado_4.png'
    plano.visualizar_plano(output_path=estado_4_plot)
    print(f'Visualización del estado 4 guardada en: {estado_4_plot}')


if __name__ == '__main__':
    main()
