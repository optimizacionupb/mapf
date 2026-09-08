import pytest


@pytest.fixture
def config_minimo() -> dict:
    """Config mínima para pruebas, sin tocar disco."""
    return {
        'ids': {'sombra_id_inicio': -1},
        'salida': {'directorio': 'temp'},
        'visualizacion': {
            'figsize': [4, 4],
            'dpi': 72,
            'seed_layout': 1,
            'ancho_arista': 1.0,
            'alpha_arista': 1.0,
            'tamano_fuente': 8,
            'color_fuente': 'black',
            'tamano_fuente_etiqueta_agente': 8,
            'nodo_normal': {'color': 'lightblue', 'tamano': 100},
            'nodo_prima': {'color': 'tomato', 'tamano': 100},
            'nodo_sombra': {'color': 'silver', 'tamano': 100},
        },
    }


@pytest.fixture
def init_basico() -> dict:
    """Grafo pequeño: nodo 1 es prima, agentes en 1 y 2."""
    return {
        'nodos': [
            {'id': 1, 'es_prima': True},
            {'id': 2, 'es_prima': False},
            {'id': 3, 'es_prima': False},
        ],
        'conexiones': [[1, 2], [2, 3]],
        'agentes': [
            {'id': 1, 'nodo_inicio': 1},
            {'id': 2, 'nodo_inicio': 2},
        ],
    }


@pytest.fixture
def plano_basico(init_basico, config_minimo):
    """Plano construido a partir de init_basico."""
    from mapf.plano import Plano

    return Plano(init_basico, config=config_minimo)
