from mapf.plano import Plano


def _construir_init() -> dict:
    """Escenario con 3 nodos prima (1, 3, 5) y 6 agentes, para probar el apilado de nodos sombra."""
    return {
        'nodos': [
            {'id': 1, 'es_prima': True},
            {'id': 2, 'es_prima': False},
            {'id': 3, 'es_prima': True},
            {'id': 4, 'es_prima': False},
            {'id': 5, 'es_prima': True},
            {'id': 6, 'es_prima': False},
            {'id': 7, 'es_prima': False},
            {'id': 8, 'es_prima': False},
            {'id': 9, 'es_prima': False},
        ],
        'conexiones': [
            [1, 2], [1, 4], [1, 7],
            [2, 3], [2, 5],
            [3, 6], [3, 8],
            [4, 5], [4, 8],
            [5, 6], [5, 9],
            [6, 7], [7, 8], [8, 9],
            [2, 8], [3, 9], [1, 5], [5, 3],
        ],
        'agentes': [
            {'id': 1, 'nodo_inicio': 1},
            {'id': 2, 'nodo_inicio': 2},
            {'id': 3, 'nodo_inicio': 3},
            {'id': 4, 'nodo_inicio': 4},
            {'id': 5, 'nodo_inicio': 5},
            {'id': 6, 'nodo_inicio': 6},
        ],
    }


def test_apilado_de_nodos_sombra(config_minimo):
    plano = Plano(_construir_init(), config=config_minimo)
    nodo1 = plano.nodos[1]
    nodo3 = plano.nodos[3]

    # Nodo prima 1: los agentes 2 y luego 4 llegan mientras ya hay alguien -> se apilan sombras
    plano.mover(nodo_id=1, agente_id=2)
    assert len(nodo1.nodos_sombra) == 1

    plano.mover(nodo_id=1, agente_id=4)
    assert len(nodo1.nodos_sombra) == 2

    ids_sombra_nodo1 = {sombra.id for sombra in nodo1.nodos_sombra}
    assert len(ids_sombra_nodo1) == 2

    # Nodo prima 3 también acumula sombras (agentes 6 y luego 4)
    plano.mover(nodo_id=3, agente_id=6)
    plano.mover(nodo_id=5, agente_id=4)
    plano.mover(nodo_id=3, agente_id=4)
    assert len(nodo3.nodos_sombra) == 2

    sombra_agente_1 = next(s for s in nodo1.nodos_sombra if s.agente is not None and s.agente.id == 1)
    sombra_agente_2 = next(s for s in nodo1.nodos_sombra if s.agente is not None and s.agente.id == 2)

    # El agente 2 regresa desde su nodo sombra hacia el nodo prima, ahora libre
    plano.mover(nodo_id=1, agente_id=2)

    assert sombra_agente_2 not in nodo1.nodos_sombra
    assert nodo1.nodos_sombra == {sombra_agente_1}
    assert plano.agentes[2].posicion is nodo1

    ids_restantes = (
        [s.id for s in nodo1.nodos_sombra]
        + [s.id for s in nodo3.nodos_sombra]
        + [s.id for s in plano.nodos[5].nodos_sombra]
    )
    assert len(ids_restantes) == len(set(ids_restantes))
