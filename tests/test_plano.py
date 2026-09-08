import pytest

from mapf.plano import Plano


def test_cargar_desde_init_dict(plano_basico):
    assert set(plano_basico.nodos) == {1, 2, 3}
    assert set(plano_basico.agentes) == {1, 2}
    assert plano_basico.nodos[2] in plano_basico.nodos[1].conexiones
    assert plano_basico.agentes[1].posicion is plano_basico.nodos[1]
    assert plano_basico.agentes[2].posicion is plano_basico.nodos[2]


def test_mover_invalido_no_adyacente_lanza_excepcion(plano_basico):
    with pytest.raises(Exception):
        plano_basico.mover(nodo_id=3, agente_id=1)


def test_mover_valido_actualiza_posicion(plano_basico):
    plano_basico.mover(nodo_id=3, agente_id=2)
    assert plano_basico.agentes[2].posicion is plano_basico.nodos[3]
    assert plano_basico.nodos[2].agente is None


def test_estado_actual_to_dict_roundtrip(plano_basico, config_minimo):
    estado = plano_basico.estado_actual_to_dict()
    reconstruido = Plano(estado, config=config_minimo)

    assert set(reconstruido.nodos) == set(plano_basico.nodos)
    assert set(reconstruido.agentes) == set(plano_basico.agentes)
    for agente_id, agente in plano_basico.agentes.items():
        assert reconstruido.agentes[agente_id].posicion.id == agente.posicion.id
